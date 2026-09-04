from dataclasses import dataclass

from src.domain.insurance.enums import (
    NotificationPriority,
    PolicyType,
)
from src.domain.insurance.models import Insured, NotificationDecision
from src.domain.weather.enums import EventType, EvidenceType
from src.domain.weather.models import WeatherEvent


@dataclass(frozen=True)
class InsuranceRule:
    """Regra declarativa do MVP, sem efeitos colaterais."""

    rule_id: str
    event_type: EventType
    evidence_type: EvidenceType
    policy_type: PolicyType
    priority: NotificationPriority


RULES: tuple[InsuranceRule, ...] = (
    InsuranceRule(
        "HEAVY_RAIN_HOME_ALERT",
        EventType.HEAVY_RAIN,
        EvidenceType.ALERT,
        PolicyType.HOME,
        NotificationPriority.HIGH,
    ),
    InsuranceRule(
        "HEAVY_RAIN_HOME_OBSERVATION",
        EventType.HEAVY_RAIN,
        EvidenceType.OBSERVATION,
        PolicyType.HOME,
        NotificationPriority.HIGH,
    ),
    InsuranceRule(
        "HAIL_AUTO_ALERT",
        EventType.HAIL,
        EvidenceType.ALERT,
        PolicyType.AUTO,
        NotificationPriority.HIGH,
    ),
    InsuranceRule(
        "HAIL_HOME_ALERT",
        EventType.HAIL,
        EvidenceType.ALERT,
        PolicyType.HOME,
        NotificationPriority.MEDIUM,
    ),
    InsuranceRule(
        "STRONG_WIND_HOME_ALERT",
        EventType.STRONG_WIND,
        EvidenceType.ALERT,
        PolicyType.HOME,
        NotificationPriority.HIGH,
    ),
    InsuranceRule(
        "STRONG_WIND_HOME_OBSERVATION",
        EventType.STRONG_WIND,
        EvidenceType.OBSERVATION,
        PolicyType.HOME,
        NotificationPriority.MEDIUM,
    ),
    InsuranceRule(
        "STRONG_WIND_AUTO_ALERT",
        EventType.STRONG_WIND,
        EvidenceType.ALERT,
        PolicyType.AUTO,
        NotificationPriority.HIGH,
    ),
    InsuranceRule(
        "STRONG_WIND_AUTO_OBSERVATION",
        EventType.STRONG_WIND,
        EvidenceType.OBSERVATION,
        PolicyType.AUTO,
        NotificationPriority.MEDIUM,
    ),
)


PRIORITY_ORDER: dict[NotificationPriority, int] = {
    NotificationPriority.LOW: 0,
    NotificationPriority.MEDIUM: 1,
    NotificationPriority.HIGH: 2,
}


class InsuranceRulesEngine:
    """Avalia compatibilidade entre um evento e as apólices de um segurado."""

    def __init__(self, rules: tuple[InsuranceRule, ...] = RULES) -> None:
        self.rules = rules

    def evaluate(
        self,
        weather_event: WeatherEvent,
        insured: Insured,
    ) -> NotificationDecision:
        matched_rules = [
            rule
            for rule in self.rules
            if self._rule_matches_event(rule, weather_event)
            and any(
                policy.active and policy.policy_type is rule.policy_type
                for policy in insured.policies
            )
        ]
        matched_rule_ids = [rule.rule_id for rule in matched_rules]

        if not matched_rules:
            return NotificationDecision(
                insured_id=insured.insured_id,
                eligible=False,
                reason="Nenhuma apólice ativa é compatível com o evento meteorológico.",
                priority=NotificationPriority.LOW,
                matched_rules=[],
            )

        priority = max(
            (rule.priority for rule in matched_rules),
            key=PRIORITY_ORDER.__getitem__,
        )
        return NotificationDecision(
            insured_id=insured.insured_id,
            eligible=True,
            reason=self._positive_reason(weather_event, matched_rules),
            priority=priority,
            matched_rules=matched_rule_ids,
        )

    @staticmethod
    def _rule_matches_event(rule: InsuranceRule, event: WeatherEvent) -> bool:
        return (
            rule.event_type is event.event_type
            and rule.evidence_type is event.evidence_type
        )

    @staticmethod
    def _positive_reason(
        event: WeatherEvent,
        rules: list[InsuranceRule],
    ) -> str:
        if len(rules) == 1:
            policy_type = rules[0].policy_type.value
            return (
                f"Segurado possui apólice {policy_type} ativa compatível "
                f"com evento {event.event_type.value}."
            )
        return (
            f"Segurado possui apólices ativas compatíveis com o evento "
            f"{event.event_type.value}."
        )
