"""File for API routes in the application"""

import json

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from fhir.resources.R4B.operationoutcome import OperationOutcome
from pydantic import ValidationError

from helpers import operation_outcome, operation_outcome_response
from logging_config import logger
from models import JWKS
from resourceHandler import return_patient

api_router: APIRouter = APIRouter()


@api_router.get("/")
def return_root() -> dict:
    """Root function of the API"""
    logger.info("Retrieved root of API")
    return operation_outcome(
        "This is the base URL of server. Unable to handle this request, as it does not contain a resource type or operation name."
    ).model_dump(exclude_none=True)


@api_router.get("/favicon.ico")
def return_favicon() -> None:
    return None


@api_router.get("/health")
def return_health_check() -> dict:
    return {"status": "FHIR Proxy is ready to receive requests"}


@api_router.get("/get_resource_health", response_model=None)
def return_home_data() -> OperationOutcome | JSONResponse | dict:
    """Testing function to get a Patient"""
    return return_patient("e63wRTbPfr1p8UW81d8Seiw3")


@api_router.get("/jwks", response_model=JWKS)
def return_jwks() -> JWKS | JSONResponse:
    try:
        with open("jwks.json", "r") as fo:
            jwks_obj: dict = json.load(fo)
        return JWKS(**jwks_obj)
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        logger.bind(operation="loading JWKS").opt(exception=exc).error("Unable to load JWKS configuration")
        return operation_outcome_response("The server key configuration is unavailable.", status_code=500)
