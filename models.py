import logging
from typing import ClassVar

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

    FORMATS: ClassVar[dict[int, str]] = {
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
    expires: float
    scope: str


class JWK(BaseModel):
    kid: str
    kty: str = "RSA"
    n: str
    e: str


class JWKS(BaseModel):
    keys: list[JWK]


class CommonSearchParams(BaseModel):
    _content: str | None = None
    _id: str | None = None
    _lastUpdated: str | None = None
    _profile: str | None = None
    _query: str | None = None
    _security: str | None = None
    _source: str | None = None
    _tag: str | None = None
    _text: str | None = None
    _filter: str | None = None

    def not_null(self) -> str:
        not_null_params: list = []
        for prop, value in vars(self).items():
            if value:
                not_null_params.append(f"{prop}={value}")

        return ", ".join(not_null_params)


class PatientSearchParams(CommonSearchParams):
    active: str | None = None
    address: str | None = None
    address_city: str | None = Field(alias="address-city")
    address_country: str | None = Field(alias="address-country")
    address_postalcode: str | None = Field(alias="address-postalcode")
    address_state: str | None = Field(alias="address-state")
    address_use: str | None = Field(alias="address-use")
    birthdate: str | None = None
    death_date: str | None = Field(alias="death-date")
    deceased: str | None = None
    email: str | None = None
    family: str | None = None
    gender: str | None = None
    general_practitioner: str | None = Field(alias="general-practitioner")
    given: str | None = None
    identifier: str | None = None
    language: str | None = None
    link: str | None = None
    name: str | None = None
    organization: str | None = None
    phone: str | None = None
    phoentic: str | None = None
    telecom: str | None = None

    class Config:
        allow_population_by_field_name: bool = True


class ConditionSearchParams(CommonSearchParams):
    abatement_age: str | None = Query(alias="address_city")
    abatement_date: str | None = Query(alias="address_city")
    abatement_string: str | None = Query(alias="address_city")
    asserter: str | None = None
    body_site: str | None = Query(alias="address_city")
    category: str | None = None
    clinical_status: str | None = Query(alias="address_city")
    code: str | None = None
    encounter: str | None = None
    evidence: str | None = None
    evidence_detail: str | None = Query(alias="address_city")
    identifier: str | None = Query(alias="address_city")
    onsert_age: str | None = Query(alias="address_city")
    onset_date: str | None = Query(alias="address_city")
    onset_info: str | None = Query(alias="address_city")
    patient: str | None = None
    recorded_date: str | None = Query(alias="address_city")
    severity: str | None = None
    stage: str | None = None
    subject: str | None = None
    verification_status: str | None = Query(alias="address_city")


class ObservationSearchParams(CommonSearchParams):
    based_on: str | None = None
    category: str | None = None
    code: str | None = None
    code_value_concept: str | None = Query(alias="address_city")
    code_value_date: str | None = Query(alias="address_city")
    code_value_quantity: str | None = Query(alias="address_city")
    code_value_string: str | None = Query(alias="address_city")
    combo_code: str | None = None
    combo_code_value_concept: str | None = Query(alias="address_city")
    combo_code_value_quantity: str | None = Query(alias="address_city")
    combo_data_absent_reason: str | None = Query(alias="address_city")
    combo_value_concept: str | None = Query(alias="address_city")
    combo_value_quantity: str | None = Query(alias="address_city")
    component_code: str | None = Query(alias="address_city")
    component_code_value_concept: str | None = Query(alias="address_city")
    component_code_value_quantity: str | None = Query(alias="address_city")
    component_data_absent_reason: str | None = Query(alias="address_city")
    component_value_concept: str | None = Query(alias="address_city")
    component_value_quantity: str | None = Query(alias="address_city")
    data_absent_reason: str | None = Query(alias="address_city")
    date: str | None = None
    derived_from: str | None = Query(alias="address_city")
    device: str | None = None
    encounter: str | None = None
    focus: str | None = None
    has_member: str | None = Query(alias="address_city")
    identifier: str | None = None
    method: str | None = None
    part_of: str | None = Query(alias="address_city")
    patient: str | None = None
    performer: str | None = None
    specimen: str | None = None
    status: str | None = None
    subject: str | None = None
    value_concept: str | None = Query(alias="address_city")
    value_date: str | None = Query(alias="address_city")
    value_quantity: str | None = Query(alias="address_city")
    value_string: str | None = Query(alias="address_city")


class MedicationRequestSearchParams(CommonSearchParams):
    authoredon: str | None = None
    category: str | None = None
    code: str | None = None
    date: str | None = None
    encounter: str | None = None
    identifier: str | None = None
    intended_dispenser: str | None = None
    intended_performer: str | None = None
    intender_performertype: str | None = None
    intent: str | None = None
    medication: str | None = None
    patient: str | None = None
    priority: str | None = None
    requester: str | None = None
    reported_boolean: str | None = None
    status: str | None = None
    subject: str | None = None
