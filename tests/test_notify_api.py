from datetime import datetime, timezone

from fastapi.testclient import TestClient

from src.agents.message_agent import TemplateMessageGenerator
from src.domain.insurance.enums import PolicyStatus, PolicyType
from src.domain.insurance.location_matcher import CoordinateRadiusMatcher
from src.domain.insurance.models import Insured, Policy
from src.domain.insurance.rules_engine import InsuranceRulesEngine
from src.domain.location import Location
from src.services.notification_service import NotificationService
from src.main import create_app


def make_insured() -> Insured:
    return Insured(
        insured_id="insured-1",
        name="Pessoa Fictícia",
        location=Location(latitude=-15.79, longitude=-47.93),
        policies=[
            Policy(
                policy_id="policy-1",
                policy_type=PolicyType.HOME,
                status=PolicyStatus.ACTIVE,
            )
        ],
    )


class Repository:
    def list_all(self):
        return [make_insured()]


def build_client() -> TestClient:
    service = NotificationService(
        location_matcher=CoordinateRadiusMatcher(25),
        rules_engine=InsuranceRulesEngine(),
        message_generator=TemplateMessageGenerator(),
        insured_repository=Repository(),
        persistence_path=None,
    )
    return TestClient(create_app(insured_repository=Repository(), notification_service=service))


def event_payload() -> dict:
    return {
        "event_type": "HEAVY_RAIN",
        "evidence_type": "ALERT",
        "severity": "HIGH",
        "timestamp": datetime(2026, 9, 2, 13, tzinfo=timezone.utc).isoformat(),
        "location": {"latitude": -15.79, "longitude": -47.93},
    }


def test_notify_endpoint_returns_notifications():
    client = build_client()

    response = client.post("/notify", json=event_payload())

    assert response.status_code == 200
    body = response.json()
    assert body[0]["insured_id"] == "insured-1"
    assert body[0]["status"] == "SIMULATED_SENT"
    assert body[0]["message"]["generated_by"] == "template"
    assert "Pessoa Fictícia" in body[0]["message"]["text"]


def test_insureds_endpoint_lists_dataset():
    client = build_client()

    response = client.get("/insureds")

    assert response.status_code == 200
    assert response.json()[0]["insured_id"] == "insured-1"


def test_rules_endpoint_lists_rules_matrix():
    client = build_client()

    response = client.get("/rules")

    assert response.status_code == 200
    rule_ids = [rule["rule_id"] for rule in response.json()]
    assert "HAIL_AUTO_ALERT" in rule_ids
