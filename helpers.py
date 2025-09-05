"""File for helper functions"""

import logging
import time
import uuid
from json import JSONDecodeError

import httpx
import jwt
from fhir.resources.R4B.capabilitystatement import CapabilityStatement
from fhir.resources.R4B.extension import Extension
from fhir.resources.R4B.operationoutcome import OperationOutcome

from models import EpicTokenResponse
from util import client_id, fhir_auth, fhir_url, private_key

logger: logging.Logger = logging.getLogger("main.helpers")

token_object: EpicTokenResponse | None = None


def get_token_object() -> EpicTokenResponse | OperationOutcome:
    global token_object
    if not token_object or time.time() > token_object.expires:
        # If FHIR auth not an env var
        if not fhir_auth:
            token_object = get_token()
        else:
            if len(fhir_auth.split(" ")) == 2:
                token_object = EpicTokenResponse(access_token=fhir_auth.split(" ")[1], token_type=fhir_auth.split(" ")[0], expires_in=100000000, expires=99999999999, scope="not applicable")
            else:
                logger.error('Your FHIR_AUTH did not have a space in it, ensure your env var is formatted correctly. E.g. "Bearer 1233445"')
                token_object = None
        if not token_object:
            return OperationOutcome(issue=[{"severity": "error", "code": "processing", "diagnostics": "There was an issue getting a token for authorization"}])

    return token_object


def get_token() -> EpicTokenResponse | None:
    request_jwt: str = create_jwt()

    request_json = {"grant_type": "client_credentials", "client_assertion_type": "urn:ietf:params:oauth:client-assertion-type:jwt-bearer", "client_assertion": request_jwt}
    logger.debug(f"Requesting token using body: {request_json}")

    resp: httpx.Response = httpx.post(get_token_url(), data=request_json)

    try:
        resp_dict: dict = resp.json()
    except JSONDecodeError:
        logger.error(f"The response from trying to request a token was not a JSON object with status code {resp.status_code}. This is the text that was returned:")
        logger.error(resp.text)
        return None

    logger.info(f"Got token response from server: {resp}")
    if "error" in resp_dict:
        logger.error("There was an error when requesting a token")
        logger.error(resp_dict)
        return None

    resp_dict["expires"] = time.time() + resp_dict["expires_in"] - 10
    logger.info(f"Proceeding with token {resp_dict}")
    return EpicTokenResponse(**resp_dict)


def create_jwt() -> str:
    exp_time: float = time.time() + 300

    token_url: str = get_token_url()

    jwt_payload = {"iss": client_id, "sub": client_id, "aud": token_url, "jti": str(uuid.uuid4()), "exp": int(exp_time)}
    logger.debug(f"Using JWT Payload of: {jwt_payload}")
    encoded: str = jwt.encode(payload=jwt_payload, key=private_key, algorithm="RS384", headers={"alg": "RS384", "typ": "JWT"})  # type: ignore
    logger.debug(f"Created JWT of: {encoded}")
    return encoded


def get_token_url() -> str:
    resp_cap_state: dict = httpx.get(fhir_url + "metadata", headers={"Accept": "application/json"}).json()
    cap_state: CapabilityStatement = CapabilityStatement(**resp_cap_state)
    logger.info(f"Got CapabilityStatement for URL {fhir_url}")

    oauth_extension: Extension = list(filter(lambda x: x.url == "http://fhir-registry.smarthealthit.org/StructureDefinition/oauth-uris", cap_state.rest[0].security.extension))[0]  # type: ignore

    token_url: str = list(filter(lambda x: x.url == "token", oauth_extension.extension))[0]  # type: ignore
    token_url: str = token_url.valueUri  # type: ignore
    logger.info(f"Found token_url of {token_url}")

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
    """
    Check response from FHIR Server for non-standard status codes and OperationOutcomes
    """

    if resp.status_code == 401:
        logger.error(f"Something went wrong when trying to search {resource_type}. The response returned with a status code of {resp.status_code} and a body of {resp.text}")
        return OperationOutcome(issue=[{"severity": "error", "code": "processing", "diagnostics": "There was an issue with authorization"}])  # type: ignore
    elif resp.status_code != 200:
        try:
            if resp.json()["resourceType"] == "OperationOutcome":
                logger.error(resp.json())
                return OperationOutcome(**resp.json())
        except Exception:
            logger.error(f"Something went wrong when trying to search {resource_type}. The response returned with a status code of {resp.status_code} and a body of {resp.text}")
            if "WWW-Authenticate" in resp.headers:
                logger.error(resp.headers["WWW-Authenticate"])
                return OperationOutcome(issue=[{"severity": "error", "code": "processing", "diagnostics": resp.headers["WWW-Authenticate"]}])  # type: ignore
            return OperationOutcome(issue=[{"severity": "error", "code": "processing", "diagnostics": "There was an issue with something that did not return an OperationOutcome"}])  # type: ignore
