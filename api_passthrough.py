"""File for API routes in the application"""

import json
import time

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response
from fhir.resources.R4B.bundle import Bundle
from fhir.resources.R4B.operationoutcome import OperationOutcome
from pydantic import ValidationError

from helpers import check_response, forward_raw_request, json_response_without_none, operation_outcome, operation_outcome_response, parse_json_response, request_response
from logging_config import logger
from models import JWKS
from util import fhir_auth, fhir_url

api_passthrough_router: APIRouter = APIRouter()


@api_passthrough_router.get("/favicon.ico")
def return_favicon():
    return None


@api_passthrough_router.get("/health")
def return_health_check() -> dict:
    return {"status": "FHIR Proxy is ready to receive requests"}


@api_passthrough_router.get("/")
def return_root() -> dict:
    """Root function of the API"""
    logger.info("Retrieved root of API")
    return operation_outcome(
        "This is the base URL of server. Unable to handle this request, as it does not contain a resource type or operation name."
    ).model_dump(exclude_none=True)


@api_passthrough_router.get("/jwks", response_model=JWKS)
def return_jwks() -> JWKS | JSONResponse:
    try:
        with open("jwks.json", "r") as fo:
            jwks_obj: dict = json.load(fo)
        return JWKS(**jwks_obj)
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        logger.bind(operation="loading JWKS").opt(exception=exc).error("Unable to load JWKS configuration")
        return operation_outcome_response("The server key configuration is unavailable.", status_code=500)


@api_passthrough_router.api_route(
    "/raw/{raw_path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
    response_model=None,
)
async def return_raw_request(raw_path: str, request: Request) -> Response:
    return await forward_raw_request(request, raw_path)


@api_passthrough_router.get("/{resource_type}/{id}", response_model_exclude_none=True, response_model=dict)
def return_resource_by_id(resource_type: str, id: str) -> OperationOutcome | JSONResponse | dict:
    """Function for reading a resource given its id"""

    start_time = time.perf_counter()
    logger.info("Reading {} resource", resource_type)
    query_headers = {"Accept": "application/fhir+json"}
    if fhir_auth:
        query_headers["Authorization"] = fhir_auth

    resource_read = request_response(
        url=fhir_url + f"{resource_type}/{id}",
        method="GET",
        resource_type=resource_type,
        operation="reading passthrough resource",
        headers=query_headers,
    )
    if resource_read is None:
        return operation_outcome_response("Unable to reach the FHIR server while reading the resource.")

    check_output: OperationOutcome | None = check_response(resource_type=resource_type, resp=resource_read)
    if check_output:
        return JSONResponse(check_output.model_dump(exclude_none=True), status_code=resource_read.status_code)

    response_data = parse_json_response(resource_read, resource_type=resource_type, operation="reading passthrough resource")
    if response_data is None:
        return operation_outcome_response("The FHIR server returned an invalid JSON resource.")

    logger.debug("Passthrough resource request took {:.4f} seconds", time.perf_counter() - start_time)
    return json_response_without_none(response_data, status_code=resource_read.status_code)

@api_passthrough_router.get("/{resource_type}", response_model_exclude_none=True, response_model=dict)
def return_resource(resource_type: str, req: Request) -> OperationOutcome | JSONResponse | Bundle:
    start_time = time.perf_counter()
    query_string = resource_type + "?" + req.url.query
    logger.info("Searching {} resource", resource_type)
    query_headers = {"Accept": "application/fhir+json"}

    if fhir_auth:
        query_headers["Authorization"] = fhir_auth

    response = request_response(
        url=fhir_url + query_string,
        method="GET",
        resource_type=resource_type,
        operation="searching passthrough resource",
        headers=query_headers,
    )
    if response is None:
        return operation_outcome_response("Unable to reach the FHIR server while searching.")

    check_output: OperationOutcome | None = check_response(resource_type=resource_type, resp=response)
    if check_output:
        return JSONResponse(check_output.model_dump(exclude_none=True), status_code=response.status_code)

    response_data = parse_json_response(response, resource_type=resource_type, operation="searching passthrough resource")
    if response_data is None:
        return operation_outcome_response("The FHIR server returned an invalid search response.")

    entries = response_data.get("entry", [])
    if not isinstance(entries, list):
        logger.bind(resource_type=resource_type, operation="searching passthrough resource").error("FHIR search response contained an invalid entry collection")
        return operation_outcome_response("The FHIR server returned an invalid search response.")

    logger.info("Found {} {} resources and returning a Bundle of {} resources", response_data.get("total", "unknown"), resource_type, len(entries))
    logger.debug("Passthrough search request took {:.4f} seconds", time.perf_counter() - start_time)
    return json_response_without_none(response_data, status_code=response.status_code)
