import json
from pathlib import Path

import pytest
from pydantic import TypeAdapter, ValidationError

from src.domain.insurance.enums import (
    NotificationPriority,
    PolicyStatus,
    PolicyType,
)
from src.domain.insurance.models import Insured, NotificationDecision, Policy
from src.domain.location import Location
from src.domain.weather.models import Location as WeatherLocation


DATASET = Path(__file__).parents[1] / "data" / "insureds.json"


def valid_policy(
    policy_type: PolicyType = PolicyType.HOME,
    status: PolicyStatus = PolicyStatus.ACTIVE,
) -> Policy:
    return Policy(
        policy_id="policy-1",
        policy_type=policy_type,
        status=status,
    )


def valid_insured(policies: list[Policy] | None = None) -> Insured:
    return Insured(
        insured_id="insured-1",
        name="Pessoa Fictícia",
        location=Location(
            latitude=-15.79,
            longitude=-47.93,
            municipality="Brasília",
        ),
        policies=policies or [valid_policy()],
    )


def test_insured_valid_and_supports_multiple_policies():
    insured = valid_insured(
        [
            valid_policy(PolicyType.HOME),
            Policy(
                policy_id="policy-2",
                policy_type=PolicyType.AUTO,
                status=PolicyStatus.INACTIVE,
            ),
        ]
    )

    assert insured.insured_id == "insured-1"
    assert len(insured.policies) == 2
    assert insured.policies[0].policy_type is PolicyType.HOME
    assert insured.policies[1].policy_type is PolicyType.AUTO
    assert insured.policies[0].active is True
    assert insured.policies[1].active is False


@pytest.mark.parametrize(
    "overrides",
    [
        {"name": "   "},
        {"policies": []},
        {"insured_id": ""},
        {"location": {"latitude": 91, "longitude": -47.93}},
    ],
)
def test_insured_invalid(overrides):
    payload = valid_insured().model_dump()
    payload.update(overrides)

    with pytest.raises(ValidationError):
        Insured(**payload)


@pytest.mark.parametrize("policy_type", [PolicyType.HOME, PolicyType.AUTO])
@pytest.mark.parametrize("status", [PolicyStatus.ACTIVE, PolicyStatus.INACTIVE])
def test_policy_types_and_explicit_status(policy_type, status):
    policy = valid_policy(policy_type, status)

    assert policy.policy_type is policy_type
    assert policy.status is status
    assert policy.active is (status is PolicyStatus.ACTIVE)


@pytest.mark.parametrize(
    "payload",
    [
        {"policy_id": "", "policy_type": "HOME", "status": "ACTIVE"},
        {"policy_id": "policy-1", "policy_type": "LIFE", "status": "ACTIVE"},
        {"policy_id": "policy-1", "policy_type": "HOME", "status": "PENDING"},
    ],
)
def test_policy_invalid(payload):
    with pytest.raises(ValidationError):
        Policy(**payload)


def test_location_is_shared_with_weather_domain():
    assert WeatherLocation is Location
    location = Location(latitude=-15.79, longitude=-47.93)

    assert location.latitude == -15.79


@pytest.mark.parametrize(
    "payload",
    [
        {"latitude": 90.1, "longitude": 0},
        {"latitude": 0, "longitude": -180.1},
        {"latitude": float("nan"), "longitude": 0},
        {"latitude": 0, "longitude": float("inf")},
    ],
)
def test_location_invalid(payload):
    with pytest.raises(ValidationError):
        Location(**payload)


def test_notification_decision_contract():
    decision = NotificationDecision(
        insured_id="insured-1",
        eligible=True,
        reason="Apólice ativa compatível com o evento.",
        priority=NotificationPriority.HIGH,
        matched_rules=["active_policy", "event_policy_match"],
    )

    assert decision.eligible is True
    assert decision.priority is NotificationPriority.HIGH
    assert decision.matched_rules == ["active_policy", "event_policy_match"]


def test_notification_decision_requires_explainable_reason():
    with pytest.raises(ValidationError):
        NotificationDecision(
            insured_id="insured-1",
            eligible=False,
            reason="   ",
            priority=NotificationPriority.LOW,
        )


def test_insured_dataset_is_valid_and_covers_demo_scenarios():
    records = json.loads(DATASET.read_text(encoding="utf-8"))
    insureds = TypeAdapter(list[Insured]).validate_python(records)

    assert len(insureds) == 4
    assert any(len(insured.policies) > 1 for insured in insureds)
    assert any(policy.status is PolicyStatus.INACTIVE for insured in insureds for policy in insured.policies)
    assert {policy.policy_type for insured in insureds for policy in insured.policies} == {
        PolicyType.HOME,
        PolicyType.AUTO,
    }
