from datetime import datetime, timezone
from pathlib import Path

from src.domain.insurance.location_matcher import CoordinateRadiusMatcher
from src.domain.insurance.rules_engine import InsuranceRulesEngine
from src.domain.weather.enums import EventType, EvidenceType, Severity
from src.domain.weather.models import Measurements, WeatherEvent
from src.repositories.insured_repository import JsonInsuredRepository
from src.services.weather_notification_orchestrator import WeatherNotificationOrchestrator


DATASET = Path(__file__).parents[1] / "data" / "insureds.json"


def make_event(
    event_type: EventType,
    latitude: float,
    longitude: float,
) -> WeatherEvent:
    return WeatherEvent(
        event_id="audit-event",
        event_type=event_type,
        evidence_type=EvidenceType.ALERT,
        severity=Severity.HIGH,
        timestamp=datetime(2026, 9, 2, 13, tzinfo=timezone.utc),
        location={"latitude": latitude, "longitude": longitude},
        measurements=Measurements(),
        source="audit",
    )


def build_orchestrator() -> WeatherNotificationOrchestrator:
    return WeatherNotificationOrchestrator(
        location_matcher=CoordinateRadiusMatcher(25),
        rules_engine=InsuranceRulesEngine(),
        insured_repository=JsonInsuredRepository(DATASET),
    )


def test_dataset_event_rules_engine_contracts_fit_for_eligible_insured():
    decisions = build_orchestrator().evaluate_event(
        make_event(EventType.HEAVY_RAIN, -15.7939, -47.8828)
    )

    decision = next(item for item in decisions if item.insured_id == "insured-001")
    assert decision.eligible is True
    assert decision.priority.value == "HIGH"


def test_dataset_event_rules_engine_contracts_fit_for_inactive_policy():
    decisions = build_orchestrator().evaluate_event(
        make_event(EventType.HAIL, -19.9167, -43.9345)
    )

    decision = next(item for item in decisions if item.insured_id == "insured-003")
    assert decision.eligible is False
