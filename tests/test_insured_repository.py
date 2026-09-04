import json

import pytest

from src.domain.insurance.enums import PolicyStatus, PolicyType
from src.repositories.insured_repository import (
    InsuredRepositoryError,
    JsonInsuredRepository,
)


def insured_payload(insured_id: str = "insured-1") -> dict:
    return {
        "insured_id": insured_id,
        "name": "Pessoa Fictícia",
        "location": {
            "latitude": -15.79,
            "longitude": -47.93,
            "municipality": "Brasília",
        },
        "policies": [
            {
                "policy_id": "policy-1",
                "policy_type": "HOME",
                "status": "ACTIVE",
            }
        ],
    }


def write_json(path, payload) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_valid_json_dataset_is_loaded_as_domain_models(tmp_path):
    path = tmp_path / "insureds.json"
    write_json(path, [insured_payload()])

    insureds = JsonInsuredRepository(path).list_all()

    assert len(insureds) == 1
    assert insureds[0].insured_id == "insured-1"
    assert insureds[0].policies[0].policy_type is PolicyType.HOME
    assert insureds[0].policies[0].status is PolicyStatus.ACTIVE


def test_empty_dataset_is_valid(tmp_path):
    path = tmp_path / "insureds.json"
    write_json(path, [])

    assert JsonInsuredRepository(path).list_all() == []


@pytest.mark.parametrize(
    "payload",
    [
        {"insured_id": "not-a-list"},
        "invalid-json-structure",
    ],
)
def test_invalid_dataset_structure_raises_error(tmp_path, payload):
    path = tmp_path / "insureds.json"
    if isinstance(payload, str):
        path.write_text(payload, encoding="utf-8")
    else:
        write_json(path, payload)

    with pytest.raises(InsuredRepositoryError):
        JsonInsuredRepository(path).list_all()


def test_invalid_record_raises_error(tmp_path):
    path = tmp_path / "insureds.json"
    invalid_record = insured_payload()
    invalid_record["policies"] = []
    write_json(path, [invalid_record])

    with pytest.raises(InsuredRepositoryError):
        JsonInsuredRepository(path).list_all()


def test_missing_dataset_raises_error(tmp_path):
    with pytest.raises(InsuredRepositoryError):
        JsonInsuredRepository(tmp_path / "missing.json").list_all()
