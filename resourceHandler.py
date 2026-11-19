"""File for FHIR Resource-based API routes in the application"""

import typing

import httpx
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, Response
from fastapi_utils.tasks import repeat_every
from fhir.resources.R4B.bundle import Bundle
from fhir.resources.R4B.operationoutcome import OperationOutcome
from fhir.resources.R4B.patient import Patient
from fhirsearchhelper import run_fhir_query
from fhirsearchhelper.helpers.conditionhelper import expand_single_condition_onset
from fhirsearchhelper.helpers.documenthelper import expand_single_document_reference_content
from fhirsearchhelper.helpers.medicationhelper import expand_single_medication_reference
from pydantic.error_wrappers import ValidationError

from helpers import check_response, create_query_string, forward_raw_request, get_token_object, json_response_without_none, operation_outcome_response, parse_json_response, request_response
from logging_config import logger
from models import ConditionSearchParams, EpicTokenResponse, MedicationRequestSearchParams, ObservationSearchParams, PatientSearchParams
from util import capability_statement_file, fhir_url

accept_header_value: typing.Literal["application/fhir+json"] = "application/fhir+json"

resource_router: APIRouter = APIRouter()

cached_resources = {}


def log_cache_clear_exception(exc: Exception) -> None:
    logger.opt(exception=exc).error("Scheduled cache cleanup failed")

@resource_router.on_event("startup")
@repeat_every(seconds=60 * 5, on_exception=log_cache_clear_exception)
def clear_cached_resources():
    logger.info("Clearing cached resources array...")
    global cached_resources
    del cached_resources
    cached_resources = {}  # noqa: F841
    logger.info("Finished clearing cached resources!")


@resource_router.api_route(
    "/raw/{raw_path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
    response_model=None,
)
async def return_raw_request(raw_path: str, request: Request) -> Response:
    return await forward_raw_request(request, raw_path)


@resource_router.get("/{resource_type}/{id}", response_model_exclude_none=True, response_model=dict)
def return_resource_by_id(resource_type: str, id: str) -> OperationOutcome | JSONResponse | dict:
    """Function for reading a resource given its id"""

    cache_key = f"{resource_type}/{id}"
    if cache_key in cached_resources:
        return cached_resources[cache_key]

    token_object: EpicTokenResponse | OperationOutcome = get_token_object()
    if isinstance(token_object, OperationOutcome):
        return operation_outcome_response("There was an issue getting a token for authorization.", status_code=401)

    query_headers = {"Authorization": f"{token_object.token_type} {token_object.access_token}", "Accept": accept_header_value}
    resource_read = request_response(
        url=fhir_url + cache_key,
        method="GET",
        resource_type=resource_type,
        operation="reading resource",
        headers=query_headers,
    )
    if resource_read is None:
        return operation_outcome_response("Unable to reach the FHIR server while reading the resource.")

    check_output: OperationOutcome | None = check_response(resource_type=resource_type, resp=resource_read)
    if check_output:
        return JSONResponse(check_output.model_dump(exclude_none=True), status_code=resource_read.status_code)

    resource_obj = parse_json_response(resource_read, resource_type=resource_type, operation="reading resource")
    if resource_obj is None:
        return operation_outcome_response("The FHIR server returned an invalid JSON resource.")

    try:
        match resource_type:
            case "DocumentReference":
                return_resource_obj = expand_single_document_reference_content(resource=resource_obj, base_url=fhir_url, query_headers=query_headers)
                if return_resource_obj is None:
                    logger.warning("Unable to expand DocumentReference resource")
                    return_resource_obj = resource_obj
            case "MedicationRequest":
                med_req_output = expand_single_medication_reference(resource=resource_obj, base_url=fhir_url, query_headers=query_headers)
                if med_req_output:
                    return_resource_obj = med_req_output
                else:
                    logger.warning("Unable to expand Medication reference")
                    return_resource_obj = resource_obj
            case "Condition":
                condition_output = expand_single_condition_onset(resource=resource_obj, base_url=fhir_url, query_headers=query_headers)
                if condition_output:
                    return_resource_obj = condition_output
                else:
                    logger.warning("Unable to add onsetDateTime to resource")
                    return_resource_obj = resource_obj
            case _:
                return_resource_obj = resource_obj
    except (AttributeError, IndexError, KeyError, TypeError, ValueError, httpx.HTTPError, ValidationError) as exc:
        logger.bind(resource_type=resource_type, operation="normalizing resource").opt(exception=exc).error("Unable to normalize FHIR resource")
        return operation_outcome_response("The FHIR server returned an invalid resource.")

    return_output = json_response_without_none(return_resource_obj, status_code=resource_read.status_code)
    cached_resources[cache_key] = return_output
    return return_output

@resource_router.get("/{resource_type}", response_model=None)
def return_resource(resource_type: str, req: Request) -> OperationOutcome | Bundle | JSONResponse | None:
    query_string = resource_type + "?" + req.url.query
    logger.info("Searching {} resource", resource_type)

    token_object: EpicTokenResponse | OperationOutcome = get_token_object()
    if isinstance(token_object, OperationOutcome):
        return operation_outcome_response("There was an issue getting a token for authorization.", status_code=401)

    query_headers = {"Authorization": f"{token_object.token_type} {token_object.access_token}", "Accept": accept_header_value}
    try:
        output_search: Bundle | OperationOutcome | None = run_fhir_query(
            query=fhir_url + query_string,
            query_headers=query_headers,
            capability_statement_file=capability_statement_file,
            debug=False,
        )
    except ValidationError as exc:
        logger.bind(resource_type=resource_type, operation="running FHIR query").opt(exception=exc).error("FHIR query returned invalid data")
        return operation_outcome_response("The FHIR server returned invalid data.")
    except (AttributeError, KeyError, TypeError, ValueError, httpx.HTTPError) as exc:
        logger.bind(resource_type=resource_type, operation="running FHIR query").opt(exception=exc).error("FHIR query failed")
        return operation_outcome_response("Unable to complete the FHIR query.")

    if output_search is None:
        return operation_outcome_response("The FHIR query returned no usable response.")
    return json_response_without_none(output_search)

@resource_router.get("/Patient/{id}", response_model_exclude_none=True, response_model=dict)
def return_patient(id: str) -> OperationOutcome | JSONResponse | dict:
    """Function for reading a patient given an id"""

    resource_type: typing.Literal["Patient"] = "Patient"
    token_object: EpicTokenResponse | OperationOutcome = get_token_object()
    if isinstance(token_object, OperationOutcome):
        return operation_outcome_response("There was an issue getting a token for authorization.", status_code=401)

    patient_read = request_response(
        url=fhir_url + f"{resource_type}/{id}",
        method="GET",
        resource_type=resource_type,
        operation="reading patient",
        headers={"Authorization": f"{token_object.token_type} {token_object.access_token}", "Accept": accept_header_value},
    )
    if patient_read is None:
        return operation_outcome_response("Unable to reach the FHIR server while reading the patient.")

    check_output: OperationOutcome | None = check_response(resource_type=resource_type, resp=patient_read)
    if check_output:
        return JSONResponse(check_output.model_dump(exclude_none=True), status_code=patient_read.status_code)

    patient_data = parse_json_response(patient_read, resource_type=resource_type, operation="reading patient")
    if patient_data is None:
        return operation_outcome_response("The FHIR server returned an invalid patient response.")

    try:
        return Patient(**patient_data).model_dump(exclude_none=True)
    except ValidationError as exc:
        logger.bind(resource_type=resource_type, operation="validating patient").opt(exception=exc).error("FHIR patient response failed validation")
        return operation_outcome_response("The FHIR server returned an invalid patient resource.")


def _search_resource(resource_type: str, query_string: str, token_object: EpicTokenResponse) -> dict | JSONResponse:
    query_headers = {"Authorization": f"{token_object.token_type} {token_object.access_token}", "Accept": accept_header_value}
    response = request_response(
        url=fhir_url + query_string,
        method="GET",
        resource_type=resource_type,
        operation="searching resource",
        headers=query_headers,
    )
    if response is None:
        return operation_outcome_response("Unable to reach the FHIR server while searching.")

    check_output: OperationOutcome | None = check_response(resource_type=resource_type, resp=response)
    if check_output:
        return JSONResponse(check_output.model_dump(exclude_none=True), status_code=response.status_code)

    response_data = parse_json_response(response, resource_type=resource_type, operation="searching resource")
    if response_data is None:
        return operation_outcome_response("The FHIR server returned an invalid search response.")

    return json_response_without_none(response_data, status_code=response.status_code)

@resource_router.get("/Patient", response_model=None)
def search_patient(search_params: PatientSearchParams = Depends(PatientSearchParams)) -> OperationOutcome | Bundle | JSONResponse | None:
    """Function to search Patient resources."""
    logger.info("Searching Patient resource")

    token_object: EpicTokenResponse | OperationOutcome = get_token_object()
    if isinstance(token_object, OperationOutcome):
        return operation_outcome_response("There was an issue getting a token for authorization.", status_code=401)

    query_string: str = create_query_string(resource_type="Patient", search_params=search_params)
    query_headers = {"Authorization": f"{token_object.token_type} {token_object.access_token}", "Accept": accept_header_value}
    try:
        patient_search: Bundle | OperationOutcome | None = run_fhir_query(
            query=fhir_url + query_string,
            query_headers=query_headers,
            capability_statement_file=capability_statement_file,
            debug=False,
        )
    except ValidationError as exc:
        logger.bind(resource_type="Patient", operation="searching resource").opt(exception=exc).error("FHIR patient search returned invalid data")
        return operation_outcome_response("The FHIR server returned invalid patient data.")
    except (AttributeError, KeyError, TypeError, ValueError, httpx.HTTPError) as exc:
        logger.bind(resource_type="Patient", operation="searching resource").opt(exception=exc).error("FHIR patient search failed")
        return operation_outcome_response("Unable to complete the patient search.")

    if patient_search is None:
        return operation_outcome_response("The patient search returned no usable response.")
    return json_response_without_none(patient_search)

@resource_router.get("/Condition", response_model_exclude_none=True, response_model=dict)
def search_condition(search_params: ConditionSearchParams = Depends(ConditionSearchParams)) -> dict | JSONResponse:
    logger.info("Searching Condition resource")
    token_object: EpicTokenResponse | OperationOutcome = get_token_object()
    if isinstance(token_object, OperationOutcome):
        return operation_outcome_response("There was an issue getting a token for authorization.", status_code=401)

    query_string = create_query_string(resource_type="Condition", search_params=search_params)
    return _search_resource("Condition", query_string, token_object)


@resource_router.get("/Observation", response_model_exclude_none=True, response_model=dict)
def search_observation(search_params: ObservationSearchParams = Depends(ObservationSearchParams)) -> dict | JSONResponse:
    logger.info("Searching Observation resource")
    token_object: EpicTokenResponse | OperationOutcome = get_token_object()
    if isinstance(token_object, OperationOutcome):
        return operation_outcome_response("There was an issue getting a token for authorization.", status_code=401)

    query_string = create_query_string(resource_type="Observation", search_params=search_params)
    return _search_resource("Observation", query_string, token_object)


@resource_router.get("/MedicationRequest", response_model_exclude_none=True, response_model=dict)
def search_medication_request(search_params: MedicationRequestSearchParams = Depends(MedicationRequestSearchParams)) -> dict | JSONResponse:
    logger.info("Searching MedicationRequest resource")
    token_object: EpicTokenResponse | OperationOutcome = get_token_object()
    if isinstance(token_object, OperationOutcome):
        return operation_outcome_response("There was an issue getting a token for authorization.", status_code=401)

    query_string = create_query_string(resource_type="MedicationRequest", search_params=search_params)
    return _search_resource("MedicationRequest", query_string, token_object)
