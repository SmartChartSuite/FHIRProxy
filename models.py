import logging
from re import L
from pydantic import BaseModel
from typing import Optional


class CustomFormatter(logging.Formatter):

    grey: str = "\x1b[38;21m"
    green: str = "\x1b[32m"
    yellow: str = "\x1b[33m"
    red: str = "\x1b[31m"
    bold_red: str = "\x1b[31;1m"
    reset: str = "\x1b[0m"
    format: str = '{asctime}   {levelname:8s} --- {name}: {message}'

    FORMATS: dict[int, str] = {
        logging.DEBUG: grey + format + reset,
        logging.INFO: green + format + reset,
        logging.WARNING: yellow + format + reset,
        logging.ERROR: red + format + reset,
        logging.CRITICAL: bold_red + format + reset
    }

    def format(self, record) -> str:
        log_fmt: str = self.FORMATS.get(record.levelno)
        formatter: logging.Formatter = logging.Formatter(log_fmt, '%m/%d/%Y %I:%M:%S %p', style='{')
        return formatter.format(record)


class EpicTokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    expires: int
    scope: str

class JWK(BaseModel):
    kid: str
    kty: str = 'RSA'
    n: str
    e: str


class JWKS(BaseModel):
    keys: list[JWK]


class CommonSearchParams(BaseModel):
    _content: Optional[str] = None
    _id: Optional[str] = None
    _lastUpdated: Optional[str] = None
    _profile: Optional[str] = None
    _query: Optional[str] = None
    _security: Optional[str] = None
    _source: Optional[str] = None
    _tag: Optional[str] = None
    _text: Optional[str] = None
    _filter: Optional[str] = None


class PatientSearchParams(CommonSearchParams):
    active: Optional[str] = None
    address: Optional[str] = None
    address_city: Optional[str] = None
    address_country: Optional[str] = None
    address_postalcode: Optional[str] = None
    address_state: Optional[str] = None
    address_use: Optional[str] = None
    birthdate: Optional[str] = None
    death_date: Optional[str] = None
    deceased: Optional[str] = None
    email: Optional[str] = None
    family: Optional[str] = None
    gender: Optional[str] = None
    general_practitioner: Optional[str] = None
    given: Optional[str] = None
    identifier: Optional[str] = None
    language: Optional[str] = None
    link: Optional[str] = None
    name: Optional[str] = None
    organization: Optional[str] = None
    phone: Optional[str] = None
    phoentic: Optional[str] = None
    telecom: Optional[str] = None


class ConditionSearchParams(CommonSearchParams):
    abatement_age: Optional[str] = None
    abatement_date: Optional[str] = None
    abatement_string: Optional[str] = None
    asserter: Optional[str] = None
    body_site: Optional[str] = None
    category: Optional[str] = None
    clinical_status: Optional[str] = None
    code: Optional[str] = None
    encounter: Optional[str] = None
    evidence: Optional[str] = None
    evidence_detail: Optional[str] = None
    identifier: Optional[str] = None
    onsert_age: Optional[str] = None
    onset_date: Optional[str] = None
    onset_info: Optional[str] = None
    patient: Optional[str] = None
    recorded_date: Optional[str] = None
    severity: Optional[str] = None
    stage: Optional[str] = None
    subject: Optional[str] = None
    verification_status: Optional[str] = None


class ObservationSearchParams(CommonSearchParams):
    based_on: Optional[str] = None
    category: Optional[str] = None
    code: Optional[str] = None
    code_value_concept: Optional[str] = None
    code_value_date: Optional[str] = None
    code_value_quantity: Optional[str] = None
    code_value_string: Optional[str] = None
    combo_code: Optional[str] = None
    combo_code_value_concept: Optional[str] = None
    combo_code_value_quantity: Optional[str] = None
    combo_data_absent_reason: Optional[str] = None
    combo_value_concept: Optional[str] = None
    combo_value_quantity: Optional[str] = None
    component_code: Optional[str] = None
    component_code_value_concept: Optional[str] = None
    component_code_value_quantity: Optional[str] = None
    component_data_absent_reason: Optional[str] = None
    component_value_concept: Optional[str] = None
    component_value_quantity: Optional[str] = None
    data_absent_reason: Optional[str] = None
    date: Optional[str] = None
    derived_from: Optional[str] = None
    device: Optional[str] = None
    encounter: Optional[str] = None
    focus: Optional[str] = None
    has_member: Optional[str] = None
    identifier: Optional[str] = None
    method: Optional[str] = None
    part_of: Optional[str] = None
    patient: Optional[str] = None
    performer: Optional[str] = None
    specimen: Optional[str] = None
    status: Optional[str] = None
    subject: Optional[str] = None
    value_concept: Optional[str] = None
    value_date: Optional[str] = None
    value_quantity: Optional[str] = None
    value_string: Optional[str] = None