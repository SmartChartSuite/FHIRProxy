"""File for helper functions"""

import re
import time
import uuid
from collections.abc import Mapping
from json import JSONDecodeError
from typing import Any

import httpx
import jwt
from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, Response
from fhir.resources.R4B.capabilitystatement import CapabilityStatement
from fhir.resources.R4B.extension import Extension
from fhir.resources.R4B.operationoutcome import OperationOutcome, OperationOutcomeIssue
from pydantic import ValidationError

from logging_config import logger
from models import EpicTokenResponse
from util import client_id, fhir_auth, fhir_url, private_key

token_object: EpicTokenResponse | None = None
UPSTREAM_TIMEOUT = httpx.Timeout(timeout=300)

_DEBUG_RESPONSE_BODY_LIMIT = 512
_BEARER_TOKEN_PATTERN = re.compile(r"(?i)\bBearer\s+[^\s<]+")
_RAW_REQUEST_HEADERS_TO_DROP = {"authorization", "content-length", "host", "transfer-encoding"}
_RAW_RESPONSE_HEADERS_TO_DROP = {
    "connection",
    "content-encoding",
    "content-length",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
}
_SENSITIVE_BODY_VALUE_PATTERN = re.compile(
    r"(?i)(\b(?:access_token|authorization|client_assertion|id_token|password|refresh_token|secret|token)\b\s*[:=]\s*[\"']?)[^\"'\s,}&<>]+"
)


def operation_outcome(diagnostics: str) -> OperationOutcome:
    issue = OperationOutcomeIssue(severity="error", code="processing", diagnostics=diagnostics)
    return OperationOutcome(issue=[issue])


def operation_outcome_response(diagnostics: str, *, status_code: int = 502) -> JSONResponse:
    return JSONResponse(content=operation_outcome(diagnostics).model_dump(exclude_none=True), status_code=status_code)


def json_response_without_none(
    content: Any,
    *,
    status_code: int = 200,
    headers: Mapping[str, str] | None = None,
    media_type: str | None = None,
) -> JSONResponse:
    return JSONResponse(
        content=jsonable_encoder(content, exclude_none=True),
        status_code=status_code,
        headers=headers,
        media_type=media_type,
    )


def request_response(
    *,
    url: str,
    method: str,
    resource_type: str,
    operation: str,
    headers: Mapping[str, str] | None = None,
    data: Mapping[str, str] | None = None,
    content: bytes | None = None,
) -> httpx.Response | None:
    context = logger.bind(resource_type=resource_type, operation=operation)
    try:
        response = httpx.request(method, url, headers=headers, data=data, content=content, timeout=UPSTREAM_TIMEOUT)
    except httpx.TimeoutException as exc:
        context.opt(exception=exc).error("Upstream request timed out")
        return None
    except httpx.RequestError as exc:
        context.opt(exception=exc).error("Upstream request failed")
        return None

    context.debug("Upstream request returned status {}", response.status_code)
    return response


async def forward_raw_request(request: Request, raw_path: str) -> Response:
    token_object = get_token_object()
    if isinstance(token_object, OperationOutcome):
        return operation_outcome_response("There was an issue getting a token for authorization.", status_code=401)

    headers = {name: value for name, value in request.headers.items() if name.lower() not in _RAW_REQUEST_HEADERS_TO_DROP}
    headers["Authorization"] = f"{token_object.token_type} {token_object.access_token}"

    upstream_url = f"{fhir_url}{raw_path.lstrip('/')}"
    if request.url.query:
        upstream_url = f"{upstream_url}?{request.url.query}"

    upstream_response = request_response(
        url=upstream_url,
        method=request.method,
        resource_type="raw",
        operation="forwarding raw FHIR request",
        headers=headers,
        content=await request.body(),
    )
    if upstream_response is None:
        return operation_outcome_response("Unable to reach the FHIR server for the raw request.")

    response_headers = {name: value for name, value in upstream_response.headers.items() if name.lower() not in _RAW_RESPONSE_HEADERS_TO_DROP}
    return Response(content=upstream_response.content, status_code=upstream_response.status_code, headers=response_headers)


def _response_body_preview(response: httpx.Response) -> str:
    preview = response.text.replace("\r", "\\r").replace("\n", "\\n")
    preview = _BEARER_TOKEN_PATTERN.sub("Bearer [REDACTED]", preview)
    preview = _SENSITIVE_BODY_VALUE_PATTERN.sub(r"\1[REDACTED]", preview)
    if len(preview) > _DEBUG_RESPONSE_BODY_LIMIT:
        return f"{preview[:_DEBUG_RESPONSE_BODY_LIMIT]}... [truncated]"
    return preview


def parse_json_response(response: httpx.Response, *, resource_type: str, operation: str) -> dict | None:
    context = logger.bind(
        resource_type=resource_type,
        operation=operation,
        status_code=response.status_code,
        content_type=response.headers.get("content-type", "unknown"),
    )
    try:
        payload = response.json()
    except (JSONDecodeError, UnicodeDecodeError) as exc:
        context.debug("Invalid upstream response body preview: {!r}", _response_body_preview(response))
        context.error("Upstream response was not valid JSON: {}", exc)
        return None

    if not isinstance(payload, dict):
        context.error("Upstream response JSON was {}, expected an object", type(payload).__name__)
        return None

    return payload


def get_token_object() -> EpicTokenResponse | OperationOutcome:
    global token_object
    if not token_object or time.time() > token_object.expires:
        if not fhir_auth:
            token_object = get_token()
        else:
            auth_parts = fhir_auth.split()
            if len(auth_parts) == 2 and all(auth_parts):
                token_object = EpicTokenResponse(access_token=auth_parts[1], token_type=auth_parts[0], expires_in=100000000, expires=99999999999, scope="not applicable")
            else:
                logger.error("FHIR_AUTH must contain an authentication scheme and token")
                token_object = None
        if not token_object:
            return operation_outcome("There was an issue getting a token for authorization.")

    return token_object


def get_token() -> EpicTokenResponse | None:
    token_url = get_token_url()
    if token_url is None:
        return None

    request_jwt = create_jwt(token_url)
    if request_jwt is None:
        return None

    request_data = {
        "grant_type": "client_credentials",
        "client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer",
        "client_assertion": request_jwt,
    }
    response = request_response(
        url=token_url,
        method="POST",
        resource_type="OAuth",
        operation="requesting access token",
        data=request_data,
    )
    if response is None:
        return None

    response_data = parse_json_response(response, resource_type="OAuth", operation="requesting access token")
    if response_data is None:
        return None

    logger.info("Received access-token response with status {}", response.status_code)
    if "error" in response_data:
        logger.error("Token endpoint returned an OAuth error")
        return None

    try:
        response_data["expires"] = time.time() + response_data["expires_in"] - 10
        return EpicTokenResponse(**response_data)
    except (KeyError, TypeError, ValidationError) as exc:
        logger.bind(resource_type="OAuth", operation="parsing access-token response").opt(exception=exc).error("Token response was missing expected fields")
        return None


def create_jwt(token_url: str | None = None) -> str | None:
    exp_time: float = time.time() + 300

    if token_url is None:
        token_url = get_token_url()
    if token_url is None:
        return None

    jwt_payload = {"iss": client_id, "sub": client_id, "aud": token_url, "jti": str(uuid.uuid4()), "exp": int(exp_time)}
    logger.debug("Creating JWT client assertion")
    try:
        encoded: str = jwt.encode(payload=jwt_payload, key=private_key, algorithm="RS256", headers={"alg": "RS256", "typ": "JWT"})  # type: ignore
    except (TypeError, ValueError, jwt.PyJWTError) as exc:
        logger.bind(operation="creating client assertion").opt(exception=exc).error("Unable to create JWT")
        return None

    return encoded

def get_token_url() -> str | None:
    response = request_response(
        url=fhir_url + "metadata",
        method="GET",
        resource_type="CapabilityStatement",
        operation="reading capability statement",
        headers={"Accept": "application/fhir+json"},
    )
    if response is None:
        return None

    response_data = parse_json_response(response, resource_type="CapabilityStatement", operation="reading capability statement")
    if response_data is None:
        return None

    try:
        cap_state: CapabilityStatement = CapabilityStatement(**response_data)
        oauth_extension: Extension = next(filter(lambda x: x.url == "http://fhir-registry.smarthealthit.org/StructureDefinition/oauth-uris", cap_state.rest[0].security.extension))  # type: ignore
        token_extension = next(filter(lambda x: x.url == "token", oauth_extension.extension))  # type: ignore
        token_url = token_extension.valueUri  # type: ignore
    except (AttributeError, IndexError, StopIteration, TypeError, ValidationError) as exc:
        logger.bind(resource_type="CapabilityStatement", operation="finding OAuth token URL").opt(exception=exc).error("Capability statement did not contain a usable token URL")
        return None

    if not isinstance(token_url, str) or not token_url:
        logger.error("Capability statement contained an empty token URL")
        return None

    logger.info("Read capability statement and found OAuth token URL")
    return token_url


def create_query_string(resource_type: str, search_params) -> str:
    """Helper function to create a full query string"""

    query_string: str = f"{resource_type.capitalize()}?"
    for prop, value in vars(search_params).items():
        if not value:
            continue
        if query_string == f"{resource_type.capitalize()}?":
            query_string += f"{prop}={value}"
        else:
            query_string += f"&{prop}={value}"

    return query_string


def check_response(resource_type: str, resp: httpx.Response) -> OperationOutcome | None:
    context = logger.bind(resource_type=resource_type, status_code=resp.status_code)
    if 200 <= resp.status_code < 300:
        return None

    if resp.status_code == 401:
        context.error("FHIR request was unauthorized")
        return operation_outcome("The FHIR server rejected authorization.")

    response_data = parse_json_response(resp, resource_type=resource_type, operation="reading upstream error response")
    if response_data is not None and response_data.get("resourceType") == "OperationOutcome":
        try:
            return OperationOutcome(**response_data)
        except ValidationError as exc:
            context.opt(exception=exc).error("FHIR server returned an invalid OperationOutcome")

    if "WWW-Authenticate" in resp.headers:
        context.warning("FHIR server supplied an authorization challenge")
        return operation_outcome("The FHIR server rejected authorization.")

    context.error("FHIR request returned an unexpected status or response")
    return operation_outcome("The FHIR server returned an unexpected response.")
