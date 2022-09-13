'''File for helper functions'''

from json import JSONDecodeError
import logging
import jwt
import uuid
import time
import requests

from fhir.resources.capabilitystatement import CapabilityStatement

from util import fhir_url, private_key_file, client_id

logger: logging.Logger = logging.getLogger('main.helpers')


def get_token() -> dict | None:

    request_jwt: str = create_jwt()

    request_json = {
        'grant_type': 'client_credentials',
        'client_assertion_type': 'urn:ietf:params:oauth:client-assertion-type:jwt-bearer',
        'client_assertion': request_jwt
    }
    logger.debug(f'Requesting token using body: {request_json}')

    resp: requests.Response = requests.post(get_token_url(), data=request_json)

    try:
        resp: dict = resp.json()
    except JSONDecodeError:
        logger.error(f'The response from trying to request a token was not a JSON object with status code {resp.status_code}. This is the text that was returned:')
        logger.error(resp.text)
        return None

    logger.info(f'Got token response from server: {resp}')
    if 'error' in resp:
        logger.error('There was an error when requesting a token')
        return None

    resp['expires'] = time.time() + resp['expires_in'] - 10
    return resp


def create_jwt() -> str:

    with open(private_key_file, 'r') as fo:
        private_key: str = fo.read()

    exp_time: float = time.time() + 300

    token_url: str = get_token_url()

    jwt_payload = {
        'iss': client_id,
        'sub': client_id,
        'aud': token_url,
        'jti': str(uuid.uuid4()),
        'exp': int(exp_time)
    }
    logger.debug(f'Using JWT Payload of: {jwt_payload}')
    encoded: str = jwt.encode(payload=jwt_payload, key=private_key, algorithm='RS384', headers={'alg': 'RS384', 'typ': 'JWT'})
    logger.debug(f'Created JWT of: {encoded}')
    return encoded


def get_token_url() -> str:
    cap_state: dict = requests.get(fhir_url+'metadata', headers={'Accept': 'application/json'}).json()
    cap_state: CapabilityStatement = CapabilityStatement(**cap_state)
    logger.info(f'Got CapabilityStatement for URL {fhir_url}')

    oauth_extension: dict = list(filter(lambda x: x.url == 'http://fhir-registry.smarthealthit.org/StructureDefinition/oauth-uris', cap_state.rest[0].security.extension))[0]

    token_url: str = list(filter(lambda x: x.url == 'token', oauth_extension.extension))[0]
    token_url: str = token_url.valueUri
    logger.info(f'Found token_url of {token_url}')

    return token_url
