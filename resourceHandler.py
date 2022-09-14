'''File for FHIR Resource-based API routes in the application'''

from fastapi import APIRouter, Depends

import logging
import requests

from fhir.resources.operationoutcome import OperationOutcome
from fhir.resources.patient import Patient
from fhir.resources.bundle import Bundle

from helpers import get_token_object
from util import fhir_url
from models import PatientSearchParams, ConditionSearchParams, ObservationSearchParams, EpicTokenResponse

logger: logging.Logger = logging.getLogger('main.resourceHandler')

resource_router: APIRouter = APIRouter()


@resource_router.get('/Patient/{id}', response_model=Patient)
def return_patient(id: str) -> OperationOutcome | Patient:
    '''Function for reading a patient given an id'''

    token_object: dict | OperationOutcome = get_token_object()

    if isinstance(token_object, OperationOutcome):
        return token_object

    patient_read: requests.Response = requests.get(fhir_url+f'Patient/{id}', headers={'Authorization': f'{token_object["token_type"]} {token_object["access_token"]}', 'Accept': 'application/json'})
    if patient_read.status_code == 401:
        logger.error(f'Something went wrong when trying to request a Patient. The response returned with a status code of {patient_read.status_code} and a body of {patient_read.text}')
        return OperationOutcome(issue=[{'severity': 'error','code': 'processing', 'diagnostics': 'There was an issue with authorization'}])
    elif patient_read.status_code != 200:
        logger.error(f'Something went wrong when trying to request a Patient. The response returned with a status code of {patient_read.status_code} and a body of {patient_read.text}')
        return OperationOutcome(issue=[{'severity': 'error','code': 'processing', 'diagnostics': 'There was an issue with retrieving the Patient that was not due to Authorization'}])

    return Patient.parse_obj(patient_read.json())


@resource_router.get('/Patient', response_model=Bundle)
def search_patient(search_params: PatientSearchParams = Depends(PatientSearchParams)) -> OperationOutcome | Bundle:
    '''Function to search Patient resources'''

    logger.info(f'Searching Patient with Parameters: {search_params}')

    token_object: EpicTokenResponse | OperationOutcome = get_token_object()

    if isinstance(token_object, OperationOutcome):
        return token_object

    return Bundle(type='searchset')


@resource_router.get('/Condition', response_model=Bundle)
def search_condition(search_params: ConditionSearchParams = Depends(ConditionSearchParams)) -> OperationOutcome | Bundle:
    '''Function to search Condition resources'''

    logger.info(f'Searching Condition with Parameters: {search_params}')

    token_object: dict | OperationOutcome = get_token_object()

    if isinstance(token_object, OperationOutcome):
        return token_object

    return Bundle(type='searchset')


@resource_router.get('/Observation', response_model=Bundle)
def search_condition(search_params: ObservationSearchParams = Depends(ObservationSearchParams)) -> OperationOutcome | Bundle:
    '''Function to search Observation resources'''

    logger.info(f'Searching Observation with Parameters: {search_params}')

    token_object: dict | OperationOutcome = get_token_object()

    if isinstance(token_object, OperationOutcome):
        return token_object

    return Bundle(type='searchset')