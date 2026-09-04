from datetime import datetime, timezone

import pytest

from src.domain.insurance.enums import NotificationPriority, PolicyStatus, PolicyType
from src.domain.insurance.models import Insured, Policy
from src.domain.insurance.rules_engine import InsuranceRulesEngine, RULES
from src.domain.location import Location
from src.domain.weather.enums import EventType, EvidenceType, Severity
from src.domain.weather.models import Measurements, WeatherEvent


def make_event(
    event_type: EventType,
    evidence_type: EvidenceType,
) -> WeatherEvent:
    return WeatherEvent(
        event_id="event-1",
        event_type=event_type,
        evidence_type=evidence_type,
        severity=Severity.HIGH,
        timestamp=datetime(2026, 9, 2, 13, tzinfo=timezone.utc),
        location=Location(latitude=-15.79, longitude=-47.93),
        measurements=Measurements(),
        source="test",
        source_reference="source-1",
        description="Evento de teste",
    )


def make_insured(*policy_types: PolicyType, inactive: set[PolicyType] | None = None) -> Insured:
    inactive = inactive or set()
    policies = [
        Policy(
            policy_id=f"policy-{policy_type.value.lower()}",
            policy_type=policy_type,
            status=(
                PolicyStatus.INACTIVE
                if policy_type in inactive
                else PolicyStatus.ACTIVE
            ),
        )
        for policy_type in policy_types
    ]
    return Insured(
        insured_id="insured-1",
        name="Pessoa Fictícia",
        location=Location(latitude=-15.79, longitude=-47.93),
        policies=policies,
    )


@pytest.mark.parametrize(
    ("event_type", "evidence_type", "policy_type", "priority"),
    [
        (EventType.HEAVY_RAIN, EvidenceType.ALERT, PolicyType.HOME, NotificationPriority.HIGH),
        (EventType.HEAVY_RAIN, EvidenceType.OBSERVATION, PolicyType.HOME, NotificationPriority.HIGH),
        (EventType.HAIL, EvidenceType.ALERT, PolicyType.AUTO, NotificationPriority.HIGH),
        (EventType.HAIL, EvidenceType.ALERT, PolicyType.HOME, NotificationPriority.MEDIUM),
        (EventType.STRONG_WIND, EvidenceType.ALERT, PolicyType.HOME, NotificationPriority.HIGH),
        (EventType.STRONG_WIND, EvidenceType.OBSERVATION, PolicyType.HOME, NotificationPriority.MEDIUM),
        (EventType.STRONG_WIND, EvidenceType.ALERT, PolicyType.AUTO, NotificationPriority.HIGH),
        (EventType.STRONG_WIND, EvidenceType.OBSERVATION, PolicyType.AUTO, NotificationPriority.MEDIUM),
    ],
)
def test_mvp_rule_matrix_positive(event_type, evidence_type, policy_type, priority):
    decision = InsuranceRulesEngine().evaluate(
        make_event(event_type, evidence_type),
        make_insured(policy_type),
    )

    assert decision.eligible is True
    assert decision.priority is priority
    assert len(decision.matched_rules) == 1


def test_heavy_rain_with_only_auto_is_not_eligible():
    decision = InsuranceRulesEngine().evaluate(
        make_event(EventType.HEAVY_RAIN, EvidenceType.ALERT),
        make_insured(PolicyType.AUTO),
    )

    assert decision.eligible is False
    assert decision.priority is NotificationPriority.LOW
    assert decision.matched_rules == []


def test_hail_with_only_inactive_policy_is_not_eligible():
    decision = InsuranceRulesEngine().evaluate(
        make_event(EventType.HAIL, EvidenceType.ALERT),
        make_insured(PolicyType.AUTO, inactive={PolicyType.AUTO}),
    )

    assert decision.eligible is False


def test_event_without_registered_rule_is_not_eligible():
    decision = InsuranceRulesEngine().evaluate(
        make_event(EventType.HAIL, EvidenceType.OBSERVATION),
        make_insured(PolicyType.HOME, PolicyType.AUTO),
    )

    assert decision.eligible is False
    assert decision.matched_rules == []


def test_inactive_and_incompatible_policies_are_not_eligible():
    decision = InsuranceRulesEngine().evaluate(
        make_event(EventType.HEAVY_RAIN, EvidenceType.ALERT),
        make_insured(PolicyType.AUTO, PolicyType.HOME, inactive={PolicyType.HOME}),
    )

    assert decision.eligible is False


def test_multiple_active_policies_match_without_duplicate_rules():
    decision = InsuranceRulesEngine().evaluate(
        make_event(EventType.STRONG_WIND, EvidenceType.ALERT),
        make_insured(PolicyType.HOME, PolicyType.AUTO),
    )

    assert decision.eligible is True
    assert decision.matched_rules == [
        "STRONG_WIND_HOME_ALERT",
        "STRONG_WIND_AUTO_ALERT",
    ]
    assert decision.priority is NotificationPriority.HIGH
    assert decision.reason == "Segurado possui apólices ativas compatíveis com o evento STRONG_WIND."


def test_priority_uses_highest_matching_rule():
    decision = InsuranceRulesEngine().evaluate(
        make_event(EventType.HAIL, EvidenceType.ALERT),
        make_insured(PolicyType.HOME, PolicyType.AUTO),
    )

    assert decision.matched_rules == ["HAIL_AUTO_ALERT", "HAIL_HOME_ALERT"]
    assert decision.priority is NotificationPriority.HIGH


def test_reason_and_matched_rules_are_deterministic():
    engine = InsuranceRulesEngine()
    event = make_event(EventType.HEAVY_RAIN, EvidenceType.ALERT)
    insured = make_insured(PolicyType.HOME)

    first = engine.evaluate(event, insured)
    second = engine.evaluate(event, insured)

    assert first == second
    assert first.reason == "Segurado possui apólice HOME ativa compatível com evento HEAVY_RAIN."
    assert first.matched_rules == ["HEAVY_RAIN_HOME_ALERT"]


def test_rule_table_contains_only_declared_mvp_matrix():
    assert len(RULES) == 8
    assert {rule.policy_type for rule in RULES} == {PolicyType.HOME, PolicyType.AUTO}
