import asyncio
import json
from io import StringIO

import httpx
from fastapi import Request
from fastapi.responses import JSONResponse, Response

import helpers
import resourceHandler
from helpers import json_response_without_none, parse_json_response
from logging_config import logger
from models import EpicTokenResponse


def _test_token() -> EpicTokenResponse:
    return EpicTokenResponse(access_token="test-token", token_type="Bearer", expires_in=3600, expires=9999999999, scope="test")


def _response(body: str, status_code: int = 200, content_type: str = "text/html") -> httpx.Response:
    request = httpx.Request("GET", "http://fhir.example/Patient/test")
    return httpx.Response(status_code, content=body.encode(), headers={"content-type": content_type}, request=request)


def _request(method: str, target: str, headers: dict[str, str], body: bytes) -> Request:
    path, _, query = target.partition("?")

    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}

    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": query.encode(),
        "headers": [(name.lower().encode(), value.encode()) for name, value in headers.items()],
        "server": ("proxy.example", 80),
        "client": ("testclient", 123),
        "root_path": "",
    }
    return Request(scope, receive)


def test_parse_json_response_rejects_non_json() -> None:
    assert parse_json_response(_response("<html>upstream error</html>"), resource_type="Patient", operation="test") is None


def test_parse_json_response_logs_redacted_body_preview() -> None:
    body = 'Authorization: Bearer secret-token\n<html>upstream error</html>' + ("x" * 600)
    sink = StringIO()
    sink_id = logger.add(sink, level="DEBUG", format="{message}", colorize=False)
    try:
        assert parse_json_response(_response(body), resource_type="Patient", operation="test") is None
    finally:
        logger.remove(sink_id)

    output = sink.getvalue()
    assert "Invalid upstream response body preview:" in output
    assert "<html>upstream error</html>" in output
    assert "[REDACTED]" in output
    assert "secret-token" not in output
    assert "[truncated]" in output


def test_structured_response_excludes_nested_none() -> None:
    response = json_response_without_none(
        {
            "resourceType": "Bundle",
            "total": None,
            "entry": [{"resource": {"resourceType": "DocumentReference", "id": "doc", "subject": None, "content": [{"attachment": {"url": None, "title": "keep"}}]}}],
        }
    )

    assert json.loads(bytes(response.body)) == {
        "resourceType": "Bundle",
        "entry": [{"resource": {"resourceType": "DocumentReference", "id": "doc", "content": [{"attachment": {"title": "keep"}}]}}],
    }


def test_binary_read_requests_fhir_json_and_returns_resource(monkeypatch) -> None:
    monkeypatch.setattr(resourceHandler, "get_token_object", _test_token)
    observed_headers: dict[str, str] = {}

    def request(*args, **kwargs):
        observed_headers.update(kwargs["headers"])
        return _response(
            '{"resourceType":"Binary","id":"document","contentType":"text/plain","data":"aGVsbG8="}',
            content_type="application/fhir+json",
        )

    monkeypatch.setattr(helpers.httpx, "request", request)
    resourceHandler.cached_resources.clear()

    response = resourceHandler.return_resource_by_id("Binary", "document")

    assert isinstance(response, JSONResponse)
    assert json.loads(bytes(response.body)) == {
        "resourceType": "Binary",
        "id": "document",
        "contentType": "text/plain",
        "data": "aGVsbG8=",
    }
    assert observed_headers["Accept"] == "application/fhir+json"


def test_document_reference_search_preserves_repeated_date_params(monkeypatch) -> None:
    monkeypatch.setattr(resourceHandler, "get_token_object", _test_token)
    captured: dict[str, str] = {}

    def fake_run_fhir_query(**kwargs):
        captured["query"] = kwargs["query"]

    monkeypatch.setattr(resourceHandler, "run_fhir_query", fake_run_fhir_query)
    incoming_request = _request(
        "GET",
        "/DocumentReference?patient=123&date=ge%3C2024-01-01&date=le%3C2024-12-31",
        {"Accept": "application/fhir+json"},
        b"",
    )

    resourceHandler.return_resource("DocumentReference", incoming_request)

    assert captured["query"].endswith("DocumentReference?patient=123&date=ge%3C2024-01-01&date=le%3C2024-12-31")


def test_raw_endpoint_forwards_request_and_response(monkeypatch) -> None:
    monkeypatch.setattr(resourceHandler, "get_token_object", _test_token)
    observed: dict[str, object] = {}
    monkeypatch.setattr(helpers, "get_token_object", _test_token)

    def upstream_request(method, url, headers=None, content=None, **kwargs):
        observed.update(method=method, url=url, headers=headers, content=content)
        upstream_response = httpx.Response(
            206,
            content=b"raw-upstream-body",
            headers={"content-type": "application/pdf", "content-disposition": "inline", "x-upstream": "preserved"},
            request=httpx.Request(method, url, headers=headers, content=content),
        )
        upstream_response.headers["content-encoding"] = "gzip"
        upstream_response.headers["content-length"] = "3"
        return upstream_response

    monkeypatch.setattr(helpers.httpx, "request", upstream_request)
    incoming_request = _request(
        "POST",
        "/raw/Binary/document?download=1",
        {
            "Accept": "application/pdf",
            "Content-Type": "application/pdf",
            "Authorization": "Bearer client-token",
            "Host": "proxy.example",
            "X-Client": "preserve-me",
        },
        b"raw-request-body",
    )

    response = asyncio.run(resourceHandler.return_raw_request("Binary/document", incoming_request))

    assert isinstance(response, Response)
    assert response.status_code == 206
    assert bytes(response.body) == b"raw-upstream-body"
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["content-disposition"] == "inline"
    assert response.headers["content-length"] == str(len(b"raw-upstream-body"))
    assert "content-encoding" not in response.headers
    assert response.headers["x-upstream"] == "preserved"
    assert observed["method"] == "POST"
    assert str(observed["url"]).endswith("/Binary/document?download=1")
    assert observed["content"] == b"raw-request-body"
    forwarded_headers = observed["headers"]
    assert isinstance(forwarded_headers, dict)
    assert forwarded_headers["accept"] == "application/pdf"
    assert forwarded_headers["content-type"] == "application/pdf"
    assert forwarded_headers["x-client"] == "preserve-me"
    assert forwarded_headers["Authorization"] == "Bearer test-token"
    assert "host" not in forwarded_headers


def test_resource_read_returns_safe_error_for_non_json(monkeypatch) -> None:
    monkeypatch.setattr(resourceHandler, "get_token_object", _test_token)
    monkeypatch.setattr(helpers.httpx, "request", lambda *args, **kwargs: _response("<html>upstream error</html>"))
    resourceHandler.cached_resources.clear()

    response = resourceHandler.return_resource_by_id("Patient", "not-json")

    assert isinstance(response, JSONResponse)
    assert response.status_code == 502
    assert b"upstream error" not in response.body


def test_resource_read_returns_safe_error_for_request_failure(monkeypatch) -> None:
    monkeypatch.setattr(resourceHandler, "get_token_object", _test_token)
    request = httpx.Request("GET", "http://fhir.example/Patient/offline")

    def raise_request_error(*args, **kwargs):
        raise httpx.ConnectError("offline", request=request)

    monkeypatch.setattr(helpers.httpx, "request", raise_request_error)
    resourceHandler.cached_resources.clear()

    response = resourceHandler.return_resource_by_id("Patient", "offline")

    assert isinstance(response, JSONResponse)
    assert response.status_code == 502
