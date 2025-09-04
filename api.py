'''File for API routes in the application'''

from fastapi import APIRouter

import logging
import json

from fhir.resources.R4B.operationoutcome import OperationOutcome

from models import JWKS
from resourceHandler import return_patient

logger: logging.Logger = logging.getLogger('main.api')

api_router: APIRouter = APIRouter()


@api_router.get('/')
def return_root() -> dict:
    '''Root function of the API'''
    logger.info('Retrieved root of API')
    return OperationOutcome(issue=[{'severity': 'error',
                                    'code': 'processing',
                                    'diagnostics': 'This is the base URL of server. Unable to handle this request, as it does not contain a resource type or operation name.'}]).model_dump(exclude_none=True)


@api_router.get('/favicon.ico')
def return_favicon() -> None:
    return None


@api_router.get('/health')
def return_health_check() -> dict:
    return {'status': 'FHIR Proxy is ready to receive requests'}


@api_router.get('/get_resource_health')
def return_home_data() -> OperationOutcome | dict:
    '''Testing function to get a Patient'''
    return return_patient('e63wRTbPfr1p8UW81d8Seiw3')


@api_router.get('/jwks', response_model=JWKS)
def return_jwks() -> JWKS:

    with open('jwks.json', 'r') as fo:
        jwks_obj: dict = json.load(fo)

    return JWKS(**jwks_obj)