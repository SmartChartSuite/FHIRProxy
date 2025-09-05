import logging
from typing import Optional

from fastapi import Query
from pydantic import BaseModel, Field


class CustomFormatter(logging.Formatter):
    grey: str = "\x1b[38;21m"
    green: str = "\x1b[32m"
    yellow: str = "\x1b[33m"
    red: str = "\x1b[31m"
    bold_red: str = "\x1b[31;1m"
    reset: str = "\x1b[0m"
    format_str: str = "{asctime}   {levelname:8s} --- {name}: {message}"

    FORMATS: dict[int, str] = {
        logging.DEBUG: grey + format_str + reset,
        logging.INFO: green + format_str + reset,
        logging.WARNING: yellow + format_str + reset,
        logging.ERROR: red + format_str + reset,
        logging.CRITICAL: bold_red + format_str + reset,
    }

    def format(self, record) -> str:
        log_fmt: str | None = self.FORMATS.get(record.levelno)
        formatter: logging.Formatter = logging.Formatter(log_fmt, "%m/%d/%Y %I:%M:%S %p", style="{")
        return formatter.format(record)


class EpicTokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    expires: int
    scope: str


class JWK(BaseModel):
    kid: str
    kty: str = "RSA"
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

    def not_null(self) -> str:
        not_null_params: list = []
        for prop, value in vars(self).items():
            if value:
                not_null_params.append(f"{prop}={value}")

        return ", ".join(not_null_params)


class PatientSearchParams(CommonSearchParams):
    active: Optional[str] = None
    address: Optional[str] = None
    address_city: Optional[str] = Field(alias="address-city")
    address_country: Optional[str] = Field(alias="address-country")
    address_postalcode: Optional[str] = Field(alias="address-postalcode")
    address_state: Optional[str] = Field(alias="address-state")
    address_use: Optional[str] = Field(alias="address-use")
    birthdate: Optional[str] = None
    death_date: Optional[str] = Field(alias="death-date")
    deceased: Optional[str] = None
    email: Optional[str] = None
    family: Optional[str] = None
    gender: Optional[str] = None
    general_practitioner: Optional[str] = Field(alias="general-practitioner")
    given: Optional[str] = None
    identifier: Optional[str] = None
    language: Optional[str] = None
    link: Optional[str] = None
    name: Optional[str] = None
    organization: Optional[str] = None
    phone: Optional[str] = None
    phoentic: Optional[str] = None
    telecom: Optional[str] = None

    class Config:
        allow_population_by_field_name: bool = True


class ConditionSearchParams(CommonSearchParams):
    abatement_age: Optional[str] = Query(alias="address_city")
    abatement_date: Optional[str] = Query(alias="address_city")
    abatement_string: Optional[str] = Query(alias="address_city")
    asserter: Optional[str] = None
    body_site: Optional[str] = Query(alias="address_city")
    category: Optional[str] = None
    clinical_status: Optional[str] = Query(alias="address_city")
    code: Optional[str] = None
    encounter: Optional[str] = None
    evidence: Optional[str] = None
    evidence_detail: Optional[str] = Query(alias="address_city")
    identifier: Optional[str] = Query(alias="address_city")
    onsert_age: Optional[str] = Query(alias="address_city")
    onset_date: Optional[str] = Query(alias="address_city")
    onset_info: Optional[str] = Query(alias="address_city")
    patient: Optional[str] = None
    recorded_date: Optional[str] = Query(alias="address_city")
    severity: Optional[str] = None
    stage: Optional[str] = None
    subject: Optional[str] = None
    verification_status: Optional[str] = Query(alias="address_city")


class ObservationSearchParams(CommonSearchParams):
    based_on: Optional[str] = None
    category: Optional[str] = None
    code: Optional[str] = None
    code_value_concept: Optional[str] = Query(alias="address_city")
    code_value_date: Optional[str] = Query(alias="address_city")
    code_value_quantity: Optional[str] = Query(alias="address_city")
    code_value_string: Optional[str] = Query(alias="address_city")
    combo_code: Optional[str] = None
    combo_code_value_concept: Optional[str] = Query(alias="address_city")
    combo_code_value_quantity: Optional[str] = Query(alias="address_city")
    combo_data_absent_reason: Optional[str] = Query(alias="address_city")
    combo_value_concept: Optional[str] = Query(alias="address_city")
    combo_value_quantity: Optional[str] = Query(alias="address_city")
    component_code: Optional[str] = Query(alias="address_city")
    component_code_value_concept: Optional[str] = Query(alias="address_city")
    component_code_value_quantity: Optional[str] = Query(alias="address_city")
    component_data_absent_reason: Optional[str] = Query(alias="address_city")
    component_value_concept: Optional[str] = Query(alias="address_city")
    component_value_quantity: Optional[str] = Query(alias="address_city")
    data_absent_reason: Optional[str] = Query(alias="address_city")
    date: Optional[str] = None
    derived_from: Optional[str] = Query(alias="address_city")
    device: Optional[str] = None
    encounter: Optional[str] = None
    focus: Optional[str] = None
    has_member: Optional[str] = Query(alias="address_city")
    identifier: Optional[str] = None
    method: Optional[str] = None
    part_of: Optional[str] = Query(alias="address_city")
    patient: Optional[str] = None
    performer: Optional[str] = None
    specimen: Optional[str] = None
    status: Optional[str] = None
    subject: Optional[str] = None
    value_concept: Optional[str] = Query(alias="address_city")
    value_date: Optional[str] = Query(alias="address_city")
    value_quantity: Optional[str] = Query(alias="address_city")
    value_string: Optional[str] = Query(alias="address_city")


class MedicationRequestSearchParams(CommonSearchParams):
    authoredon: Optional[str] = None
    category: Optional[str] = None
    code: Optional[str] = None
    date: Optional[str] = None
    encounter: Optional[str] = None
    identifier: Optional[str] = None
    intended_dispenser: Optional[str] = None
    intended_performer: Optional[str] = None
    intender_performertype: Optional[str] = None
    intent: Optional[str] = None
    medication: Optional[str] = None
    patient: Optional[str] = None
    priority: Optional[str] = None
    requester: Optional[str] = None
    reported_boolean: Optional[str] = None
    status: Optional[str] = None
    subject: Optional[str] = None
