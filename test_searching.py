from fastapi.testclient import TestClient
from httpx import Response
import json
from importlib.resources import files
import fhirsearchhelper.resources

from main import app

client = TestClient(app)

epic_r4_search_supported_resources: list[str] = [
    "Account",
    "AdverseEvent",
    "AllergyIntolerance",
    "Appointment",
    "BodyStructure",
    "CarePlan",
    "CareTeam",
    "Condition",
    "Consent",
    "Coverage",
    "Device",
    "DeviceRequest",
    "DeviceUseStatement",
    "DiagnosticReport",
    "DocumentReference",
    "Encounter",
    "EpisodeOfCare",
    "ExplanationOfBenefit",
    "FamilyMemberHistory",
    "Flag",
    "Goal",
    "Group",
    "Immunization",
    "List",
    "Location",
    "Medication",
    "MedicationRequest",
    "NutritionOrder",
    "Observation",
    "Patient",
    "Practitioner",
    "Procedure",
    "Questionnaire",
    "QuestionnaireResponse",
    "RequestGroup",
    "ResearchStudy",
    "ResearchSubject",
    "ServiceRequest",
    "Specimen",
    "Substance",
    "Task",
]

with files(fhirsearchhelper.resources).joinpath("fhir_r4_search_params.json").open('r') as fin:
    data: dict[str, dict[str, dict[str, str]]] = json.load(fin)


def test_patient_search() -> None:
    query_dict: dict[str, str] = {
        "address": "123 Main St.",
        "family": "Mychart",
        "gender": "female",
        "given": "Allison",
        "telecom": "608-123-4567",
    }

    query_str: str = "/Patient?" + "&".join(
        [key + "=" + value for key, value in query_dict.items()]
    )
    resp: Response = client.get(query_str)

    assert resp.status_code == 200
    assert resp.json()
    assert resp.json()["total"] == 1

    resource = resp.json()["entry"][0]["resource"]

    assert query_dict["gender"] == resource["gender"]
    assert query_dict["address"] in [add["line"][0] for add in resource["address"]]
    assert query_dict["family"] in [item["family"] for item in resource["name"]]
    assert query_dict["given"] in [item["given"][0] for item in resource["name"]]
    assert query_dict["telecom"] in [item["value"] for item in resource["telecom"]]


def test_condition_search() -> None:
    query_dict: dict[str, str] = {
        "patient": "eovSKnwDlsv-8MsEzCJO3BA3",
        "clinical-status": "active,inactive,resolved",
        "category": "problem-list-item",
        "code": "http://snomed.info/sct|21522001",
    }

    query_str_full: str = "/Condition?" + "&".join(
        [key + "=" + value for key, value in query_dict.items()]
    )
    query_str_supported: str = "&".join(query_str_full.split("&")[:-1])

    resp_supported: Response = client.get(query_str_supported)
    resp_full: Response = client.get(query_str_full)

    assert resp_supported.status_code == 200
    assert resp_supported.status_code == 200

    assert resp_full.json()
    assert resp_full.json()

    entries_all = resp_supported.json()["entry"]
    entries_filtered = resp_full.json()["entry"]

    for entry in entries_all + entries_filtered:
        assert (
            query_dict["patient"]
            == entry["resource"]["subject"]["reference"].split("/")[1]
        )
        assert any(
            [
                clin_stat == entry["resource"]["clinicalStatus"]["coding"][0]["code"]
                for clin_stat in query_dict["clinical-status"].split(",")
            ]
        )
        assert query_dict["category"] in [
            cat["coding"][0]["code"] for cat in entry["resource"]["category"]
        ]

    assert any(
        [
            query_dict["code"].split("|")[1] == coding["code"]
            for entry in entries_filtered
            for coding in entry["resource"]["code"]["coding"]
        ]
    )


def test_observation_search():
    query_dict: dict[str, str] = {
        "patient": "e63wRTbPfr1p8UW81d8Seiw3",
        "category": "laboratory",
        "code": "http://loinc.org|4548-4",
    }

    query_str_supported: str = f'/Observation?patient={query_dict["patient"]}&category={query_dict["category"]}'
    query_str_full: str = query_str_supported + f'&code={query_dict["code"]}'

    resp_supported: Response = client.get(query_str_supported)
    resp_full: Response = client.get(query_str_full)

    assert resp_supported.status_code == 200
    assert resp_full.status_code == 200

    assert resp_supported.json()
    assert resp_full.json()

    all_entries = resp_supported.json()["entry"]
    filtered_entries = resp_full.json()["entry"]

    assert len(filtered_entries) < len(all_entries)

    for entry in all_entries + filtered_entries:
        assert (
            query_dict["patient"]
            == entry["resource"]["subject"]["reference"].split("/")[1]
        )
        assert query_dict["category"] in [
            cat["coding"][0]["code"] for cat in entry["resource"]["category"]
        ]

    assert all(
        [
            entry["resource"]["code"]["coding"][0]["system"]
            == query_dict["code"].split("|")[0]
            for entry in filtered_entries
        ]
    )
    assert all(
        [
            entry["resource"]["code"]["coding"][0]["code"]
            == query_dict["code"].split("|")[1]
            for entry in filtered_entries
        ]
    )


def test_medication_request_search() -> None:
    query_dict: dict[str, str] = {
        "patient": "e.Rxkbv0HmfyDyboA-LtyRQ3",
        "code": "http://www.nlm.nih.gov/research/umls/rxnorm|2418",
    }

    query_str_supported: str = f'/MedicationRequest?patient={query_dict["patient"]}'
    query_str_full: str = query_str_supported + f'&code={query_dict["code"]}'

    resp_supported: Response = client.get(query_str_supported)
    resp_full: Response = client.get(query_str_full)

    assert resp_supported.status_code == 200
    assert resp_full.status_code == 200

    assert resp_supported.json()
    assert resp_full.json()

    all_entries = resp_supported.json()["entry"]
    filtered_entries = resp_full.json()["entry"]

    assert len(filtered_entries) < len(all_entries)

    assert all(
        [
            query_dict["patient"]
            == entry["resource"]["subject"]["reference"].split("/")[1]
            for entry in all_entries + filtered_entries
        ]
    )
    assert any(
        [
            query_dict["code"].split("|")[1] == coding["code"]
            for entry in filtered_entries
            for coding in entry["resource"]["medicationCodeableConcept"]["coding"]
        ]
    )


def test_document_reference_search() -> None:
    query_dict: dict[str, str] = {
        "subject": "e63wRTbPfr1p8UW81d8Seiw3",
        "type": "http://loinc.org|18748-4",
    }

    query_str: str = (
        f'/DocumentReference?subject={query_dict["subject"]}&type={query_dict["type"]}'
    )

    resp: Response = client.get(query_str)

    assert resp.status_code == 200
    assert resp.json()

    entries = resp.json()["entry"]
    print(entries)

    assert all(
        [
            entry["resource"]["subject"]["reference"]
            == f'Patient/{query_dict["subject"]}'
            for entry in entries
        ]
    )
    assert all(
        [
            "data" in content["attachment"]
            for entry in entries
            for content in entry["resource"]["content"]
        ]
    )
