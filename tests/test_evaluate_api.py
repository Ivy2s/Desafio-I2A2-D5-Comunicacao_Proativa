from datetime import datetime, timezone

from fastapi.testclient import TestClient

from src.domain.insurance.models import Insured, Policy
from src.domain.insurance.enums import PolicyStatus, PolicyType
from src.domain.location import Location
from src.domain.weather.enums import EventType, EvidenceType, Severity
from src.domain.weather.models import Measurements, WeatherEvent
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


def event_payload() -> dict:
    return WeatherEvent(
        event_id="event-1",
        event_type=EventType.HEAVY_RAIN,
        evidence_type=EvidenceType.ALERT,
        severity=Severity.HIGH,
        timestamp=datetime(2026, 9, 2, 13, tzinfo=timezone.utc),
        location=Location(latitude=-15.79, longitude=-47.93),
        measurements=Measurements(),
        source="test",
    ).model_dump(mode="json")


class Repository:
    def list_all(self):
        return [make_insured()]


def test_evaluate_endpoint_returns_decisions_from_orchestrator():
    client = TestClient(create_app(insured_repository=Repository()))

    response = client.post("/evaluate", json=event_payload())

    assert response.status_code == 200
    assert response.json()[0]["insured_id"] == "insured-1"
    assert response.json()[0]["eligible"] is True


def test_evaluate_endpoint_validates_weather_event():
    client = TestClient(create_app(insured_repository=Repository()))

    response = client.post(
        "/evaluate",
        json={
            "event_type": "NOT_SUPPORTED",
            "evidence_type": "ALERT",
        },
    )

    assert response.status_code == 422


def test_evaluate_endpoint_accepts_minimal_event_payload():
    client = TestClient(create_app(insured_repository=Repository()))

    response = client.post(
        "/evaluate",
        json={
            "event_type": "HEAVY_RAIN",
            "evidence_type": "ALERT",
            "severity": "HIGH",
            "location": {"latitude": -15.79, "longitude": -47.93},
        },
    )

    assert response.status_code == 200
    assert response.json()[0]["insured_id"] == "insured-1"
