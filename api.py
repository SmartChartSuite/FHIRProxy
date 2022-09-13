'''File for API routes in the application'''

from fastapi import APIRouter

import logging
import requests
import time
import json

from fhir.resources.operationoutcome import OperationOutcome
from fhir.resources.patient import Patient

from helpers import get_token
from util import fhir_url
from models import JWKS

logger: logging.Logger = logging.getLogger('main.api')

app_router: APIRouter = APIRouter()

token_object: dict | None = {}

@app_router.get('/')
def return_root() -> OperationOutcome:
    '''Root function of the API'''
    logger.info('Retrieved root of API')
    return OperationOutcome(issue=[{'severity': 'error','code': 'processing', 'diagnostics': 'This is the base URL of server. Unable to handle this request, as it does not contain a resource type or operation name.'}])


@app_router.get('/home')
def return_home_data() -> dict:
    '''Testing function to get a Patient'''


@app_router.get('/Patient/{id}')
def return_patient(id: str) -> OperationOutcome | Patient:
    '''Function for reading a patient given an id'''

    global token_object
    if not token_object or time.time() > token_object['expires']:
        token_object = get_token()
        if not token_object:
            return OperationOutcome(issue=[{'severity': 'error','code': 'processing', 'diagnostics': 'There was an issue getting a token for authorization'}])

    patient_read: requests.Response = requests.get(fhir_url+f'Patient/{id}', headers={'Authorization': f'{token_object["token_type"]} {token_object["access_token"]}', 'Accept': 'application/json'})
    if patient_read.status_code == 401:
        logger.error(f'Something went wrong when trying to request a Patient. The response returned with a status code of {patient_read.status_code} and a body of {patient_read.text}')
        return OperationOutcome(issue=[{'severity': 'error','code': 'processing', 'diagnostics': 'There was an issue with authorization'}])
    elif patient_read.status_code != 200:
        logger.error(f'Something went wrong when trying to request a Patient. The response returned with a status code of {patient_read.status_code} and a body of {patient_read.text}')
        return OperationOutcome(issue=[{'severity': 'error','code': 'processing', 'diagnostics': 'There was an issue with something'}])

    return Patient(**patient_read.json())

@app_router.get('/jwks', response_model=JWKS)
def return_jwks() -> JWKS:

    with open('jwks.json', 'r') as fo:
        jwks_obj: dict = json.load(fo)

    return JWKS(**jwks_obj)