from datetime import datetime, timezone

from src.domain.insurance.enums import NotificationPriority, PolicyStatus, PolicyType
from src.domain.insurance.location_matcher import CoordinateRadiusMatcher
from src.domain.insurance.models import Insured, NotificationDecision, Policy
from src.domain.insurance.rules_engine import InsuranceRulesEngine
from src.domain.location import Location
from src.domain.weather.enums import EventType, EvidenceType, Severity
from src.domain.weather.models import Measurements, WeatherEvent
from src.services.weather_notification_orchestrator import (
    WeatherNotificationOrchestrator,
)


def make_event() -> WeatherEvent:
    return WeatherEvent(
        event_id="event-1",
        event_type=EventType.HEAVY_RAIN,
        evidence_type=EvidenceType.ALERT,
        severity=Severity.HIGH,
        timestamp=datetime(2026, 9, 2, 13, tzinfo=timezone.utc),
        location=Location(latitude=-15.79, longitude=-47.93),
        measurements=Measurements(),
        source="test",
    )


def make_insured(
    insured_id: str,
    latitude: float = -15.79,
    longitude: float = -47.93,
    policy_types: tuple[PolicyType, ...] = (PolicyType.HOME,),
    inactive: bool = False,
) -> Insured:
    return Insured(
        insured_id=insured_id,
        name=f"Nome {insured_id}",
        location=Location(latitude=latitude, longitude=longitude),
        policies=[
            Policy(
                policy_id=f"policy-{insured_id}-{index}",
                policy_type=policy_type,
                status=PolicyStatus.INACTIVE if inactive else PolicyStatus.ACTIVE,
            )
            for index, policy_type in enumerate(policy_types)
        ],
    )


def test_exposed_compatible_insured_gets_positive_decision():
    orchestrator = WeatherNotificationOrchestrator(
        CoordinateRadiusMatcher(25), InsuranceRulesEngine()
    )

    decisions = orchestrator.evaluate_event(make_event(), [make_insured("one")])

    assert decisions[0].eligible is True
    assert decisions[0].priority is NotificationPriority.HIGH


def test_exposed_incompatible_insured_gets_negative_decision():
    orchestrator = WeatherNotificationOrchestrator(
        CoordinateRadiusMatcher(25), InsuranceRulesEngine()
    )

    decisions = orchestrator.evaluate_event(
        make_event(), [make_insured("one", policy_types=(PolicyType.AUTO,))]
    )

    assert decisions[0].eligible is False
    assert decisions[0].matched_rules == []


def test_insured_outside_radius_is_not_evaluated():
    class RecordingRulesEngine:
        def __init__(self):
            self.calls = []

        def evaluate(self, weather_event, insured):
            self.calls.append(insured.insured_id)
            return NotificationDecision(
                insured_id=insured.insured_id,
                eligible=True,
                reason="teste",
                priority=NotificationPriority.LOW,
            )

    rules_engine = RecordingRulesEngine()
    orchestrator = WeatherNotificationOrchestrator(
        CoordinateRadiusMatcher(25), rules_engine  # type: ignore[arg-type]
    )
    exposed = make_insured("exposed")
    outside = make_insured("outside", latitude=-16.50)

    decisions = orchestrator.evaluate_event(make_event(), [exposed, outside])

    assert [decision.insured_id for decision in decisions] == ["exposed"]
    assert rules_engine.calls == ["exposed"]


def test_multiple_insureds_preserve_repository_order():
    orchestrator = WeatherNotificationOrchestrator(
        CoordinateRadiusMatcher(25), InsuranceRulesEngine()
    )
    insureds = [make_insured("second"), make_insured("first")]

    decisions = orchestrator.evaluate_event(make_event(), insureds)

    assert [decision.insured_id for decision in decisions] == ["second", "first"]


def test_multiple_policies_are_delegated_to_rules_engine():
    orchestrator = WeatherNotificationOrchestrator(
        CoordinateRadiusMatcher(25), InsuranceRulesEngine()
    )
    insured = make_insured("one", policy_types=(PolicyType.HOME, PolicyType.AUTO))

    decisions = orchestrator.evaluate_event(make_event(), [insured])

    assert decisions[0].eligible is True
    assert decisions[0].matched_rules == ["HEAVY_RAIN_HOME_ALERT"]


def test_injected_repository_is_used_when_insureds_are_omitted():
    class Repository:
        def list_all(self):
            return [make_insured("from-repository")]

    orchestrator = WeatherNotificationOrchestrator(
        CoordinateRadiusMatcher(25), InsuranceRulesEngine(), Repository()
    )

    decisions = orchestrator.evaluate_event(make_event())

    assert [decision.insured_id for decision in decisions] == ["from-repository"]
