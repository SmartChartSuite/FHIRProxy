'''File for FHIR Resource-based API routes in the application'''

from fastapi import APIRouter, Depends, Request

import logging
import requests
import typing
from fhirsearchhelper import run_fhir_query

from fhir.resources.R4B.operationoutcome import OperationOutcome
from fhir.resources.R4B.patient import Patient
from fhir.resources.R4B.bundle import Bundle

from helpers import get_token_object, create_query_string, check_response
from util import fhir_url, capability_statement_file
from models import PatientSearchParams, ConditionSearchParams, ObservationSearchParams, MedicationRequestSearchParams, EpicTokenResponse

logger: logging.Logger = logging.getLogger('main.resourceHandler')

accept_header_value: typing.Literal['application/json'] = 'application/json'

resource_router: APIRouter = APIRouter()


@resource_router.get('/{resource_type}/{id}', response_model=dict)
def return_resource_by_id(resource_type: str, id: str) -> OperationOutcome | dict:
    '''Function for reading a resource given its id'''

    token_object: EpicTokenResponse | OperationOutcome = get_token_object()

    if isinstance(token_object, OperationOutcome):
        return token_object

    resource_read: requests.Response = requests.get(fhir_url+f'{resource_type}/{id}', headers={'Authorization': f'{token_object.token_type} {token_object.access_token}',
                                                                                               'Accept': accept_header_value})

    check_output: OperationOutcome | None = check_response(resource_type=resource_type, resp=resource_read)
    if check_output:
        return check_output.dict()

    return resource_read.json()


@resource_router.get('/{resource_type}', response_model_exclude_none=True)
def return_resource(resource_type: str, req: Request) -> OperationOutcome | Bundle | None:
    search_params = dict(req.query_params)
    query_string = resource_type+'?'+req.url.query

    logger.info(f'Searching {resource_type} with Parameters: {search_params}')

    token_object: EpicTokenResponse | OperationOutcome = get_token_object()

    if isinstance(token_object, OperationOutcome):
        return token_object

    query_headers = {'Authorization': f'{token_object.token_type} {token_object.access_token}', 'Accept': accept_header_value}

    output_search: Bundle | OperationOutcome | None = run_fhir_query(query=fhir_url+query_string,
                                                                     query_headers=query_headers,
                                                                     capability_statement_file=capability_statement_file,
                                                                     debug=True)

    return output_search


@resource_router.get('/Patient/{id}', response_model=dict)
def return_patient(id: str) -> OperationOutcome | dict:
    '''Function for reading a patient given an id'''

    resource_type: typing.Literal['Patient'] = 'Patient'
    token_object: EpicTokenResponse | OperationOutcome = get_token_object()

    if isinstance(token_object, OperationOutcome):
        return token_object

    patient_read: requests.Response = requests.get(fhir_url+f'{resource_type}/{id}', headers={'Authorization': f'{token_object.token_type} {token_object.access_token}', 'Accept': accept_header_value})

    check_output: OperationOutcome | None = check_response(resource_type=resource_type, resp=patient_read)
    if check_output:
        return check_output.dict()

    return Patient(**patient_read.json()).dict()


@resource_router.get('/Patient', response_model_exclude_none=True)
def search_patient(search_params: PatientSearchParams = Depends(PatientSearchParams)) -> OperationOutcome | Bundle | None:
    '''
    Function to search Patient resources

    From Epic Documentation, you must have one of these sets of things for a search to return results:

    * FHIR ID (_id)
    * <ID Type>|<ID> (identifier = system|value)
    * SSN Identifier (identifier = value where system = http://hl7.org/fhir/sid/us-ssn)
    * Given name, family name, birthdate (given & family & birthdate)
    * Given name, family name, legal sex, phone number/email (given & family & legal-sex [Epic extension] & birthdate)

    '''

    logger.info(f'Searching Patient with Parameters: {search_params}')

    token_object: EpicTokenResponse | OperationOutcome = get_token_object()

    if isinstance(token_object, OperationOutcome):
        return token_object

    query_headers = {'Authorization': f'{token_object.token_type} {token_object.access_token}', 'Accept': accept_header_value}

    query_string: str = create_query_string(resource_type='Patient', search_params=search_params)

    patient_search: Bundle | OperationOutcome | None = run_fhir_query(query=fhir_url+query_string,
                                                   query_headers=query_headers,
                                                   capability_statement_file=capability_statement_file,
                                                   debug=True)

    #patient_search: requests.Response = requests.get(fhir_url+query_string, headers=query_headers)

    # check_output: OperationOutcome | None = check_response(resource_type=resource_type, resp=patient_search)
    # if check_output:
    #     return check_output
    return patient_search


@resource_router.get('/Condition', response_model=dict)
def search_condition(search_params: ConditionSearchParams = Depends(ConditionSearchParams)) -> OperationOutcome | Bundle:
    '''
    Function to search Condition resources

    From Epic documentation:

    Starting August 2021, category is not required, it will search across all categories

    Must include patient or subject
    '''

    resource_type: typing.Literal['Condition'] = 'Condition'
    logger.info(f'Searching {resource_type} with Parameters: {search_params.not_null()}')

    token_object: EpicTokenResponse | OperationOutcome = get_token_object()

    if isinstance(token_object, OperationOutcome):
        return token_object

    query_string: str = create_query_string(resource_type=resource_type, search_params=search_params)

    condition_search: requests.Response = requests.get(fhir_url+query_string, headers={'Authorization': f'{token_object.token_type} {token_object.access_token}', 'Accept': accept_header_value})

    check_output: OperationOutcome | None = check_response(resource_type=resource_type, resp=condition_search)
    if check_output:
        return check_output

    return condition_search.json()


@resource_router.get('/Observation', response_model=dict)
def search_observation(search_params: ObservationSearchParams = Depends(ObservationSearchParams)) -> OperationOutcome | Bundle:
    '''
    Function to search Observation resources

    From Epic documentation:

    Must contain category or code, code would be a better option for specifics
    '''
    resource_type: typing.Literal['Observation'] = 'Observation'
    logger.info(f'Searching {resource_type} with Parameters: {search_params.not_null()}')

    token_object: EpicTokenResponse | OperationOutcome = get_token_object()

    if isinstance(token_object, OperationOutcome):
        return token_object

    query_string: str = create_query_string(resource_type=resource_type, search_params=search_params)

    observation_search: requests.Response = requests.get(fhir_url+query_string, headers={'Authorization': f'{token_object.token_type} {token_object.access_token}', 'Accept': accept_header_value})

    check_output: OperationOutcome | None = check_response(resource_type=resource_type, resp=observation_search)
    if check_output:
        return check_output

    return observation_search.json()


@resource_router.get('/MedicationRequest', response_model=dict)
def search_medication_request(search_params: MedicationRequestSearchParams = Depends(MedicationRequestSearchParams)) -> OperationOutcome | Bundle:
    '''
    Function to search MedicationRequest resources

    From Epic documentation:

    The R4 version of this resource also returns patient-reported medications.
    Previously, patient-reported medications were not returned by the STU3 version of MedicationRequest and needed to be queried using the STU3 MedicationStatement resource.
    This is no longer the case. The R4 version of this resource returns patient-reported medications with the reportedBoolean element set to True.
    '''
    resource_type: typing.Literal['MedicationRequest'] = 'MedicationRequest'
    logger.info(f'Searching {resource_type} with Parameters: {search_params.not_null()}')

    token_object: EpicTokenResponse | OperationOutcome = get_token_object()

    if isinstance(token_object, OperationOutcome):
        return token_object

    query_string: str = create_query_string(resource_type=resource_type, search_params=search_params)

    mr_search: requests.Response = requests.get(fhir_url+query_string, headers={'Authorization': f'{token_object.token_type} {token_object.access_token}', 'Accept': accept_header_value})

    check_output: OperationOutcome | None = check_response(resource_type=resource_type, resp=mr_search)
    if check_output:
        return check_output

    return mr_search.json()