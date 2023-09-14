'''File for API routes in the application'''

from fastapi import APIRouter, Request

import logging
import json
import requests
import time

from fhir.resources.R4B.operationoutcome import OperationOutcome
from fhir.resources.R4B.bundle import Bundle

from models import JWKS
from util import fhir_auth, fhir_url
from helpers import check_response

logger: logging.Logger = logging.getLogger('main.api_passthrough')

api_passthrough_router: APIRouter = APIRouter()


@api_passthrough_router.get('/favicon.ico')
def return_favicon():
    return None


@api_passthrough_router.get('/health')
def return_health_check() -> dict:
    return {'status': 'FHIR Proxy is ready to receive requests'}


@api_passthrough_router.get('/')
def return_root() -> dict:
    '''Root function of the API'''
    logger.info('Retrieved root of API')
    return OperationOutcome(issue=[{'severity': 'error',
                                    'code': 'processing',
                                    'diagnostics': 'This is the base URL of server. Unable to handle this request, as it does not contain a resource type or operation name.'}]).dict() # type: ignore


@api_passthrough_router.get('/jwks', response_model=JWKS)
def return_jwks() -> JWKS:

    with open('jwks.json', 'r') as fo:
        jwks_obj: dict = json.load(fo)

    return JWKS(**jwks_obj)


@api_passthrough_router.get('/{resource_type}/{id}', response_model=dict)
def return_resource_by_id(resource_type: str, id: str) -> OperationOutcome | dict:
    '''Function for reading a resource given its id'''

    start_time = time.time()
    logger.info(f'Reading {resource_type} Resource with ID: {id}')
    query_headers = {'Accept': 'application/json'}

    if fhir_auth:
        query_headers['Authorization'] = fhir_auth

    resource_read = requests.get(fhir_url+f'{resource_type}/{id}', headers=query_headers)

    check_output: OperationOutcome | None = check_response(resource_type=resource_type, resp=resource_read)
    if check_output:
        return check_output

    try:
        logger.debug(f'External call took {round(resource_read.elapsed.total_seconds(), 4)} seconds')
        logger.debug(f'This call took {round(time.time() - start_time, 4)} seconds')
        return resource_read.json()
    except requests.exceptions.JSONDecodeError:
        logger.error(f'Status Code: {resource_read.status_code}')
        logger.error(f'Response Text: {resource_read.text}')
        return OperationOutcome(issue=[{'severity': 'error',
                                        'code': 'processing',
                                        'diagnostics': 'The response returned from the FHIR_URL was not JSON parseable, please see logs for what the server responded'}]) # type: ignore


@api_passthrough_router.get('/{resource_type}', response_model_exclude_none=True)
def return_resource(resource_type: str, req: Request) -> OperationOutcome | Bundle | None:

    start_time = time.time()
    search_params = dict(req.query_params)
    query_string = resource_type+'?'+req.url.query

    logger.info(f'Searching {resource_type} with Parameters: {search_params}')
    query_headers = {'Accept': 'application/json'}

    if fhir_auth:
        query_headers['Authorization'] = fhir_auth

    resp = requests.get(fhir_url+query_string, headers=query_headers)

    check_output: OperationOutcome | None = check_response(resource_type=resource_type, resp=resp)
    if check_output:
        return check_output

    try:
        logger.info(f'Found {resp.json()["total"]} {resource_type} resources and returning a Bundle of {len(resp.json()["entry"]) if "entry" in resp.json() else 0} resources')
        logger.debug(f'External call took {round(resp.elapsed.total_seconds(), 4)} seconds')
        logger.debug(f'This call took {round(time.time() - start_time, 4)} seconds')
        return resp.json()
    except requests.exceptions.JSONDecodeError:
        logger.error(f'Status Code: {resp.status_code}')
        logger.error(f'Response Text: {resp.text}')
        return OperationOutcome(issue=[{'severity': 'error',
                                        'code': 'processing',
                                        'diagnostics': 'The response returned from the FHIR_URL was not JSON parseable, please see logs for what the server responded'}]) # type: ignore