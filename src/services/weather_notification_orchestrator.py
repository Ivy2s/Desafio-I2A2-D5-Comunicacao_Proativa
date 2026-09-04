from collections.abc import Iterable

from src.domain.insurance.location_matcher import LocationMatcher
from src.domain.insurance.models import Insured, NotificationDecision
from src.domain.insurance.rules_engine import InsuranceRulesEngine
from src.domain.weather.models import WeatherEvent
from src.repositories.insured_repository import InsuredRepository


class WeatherNotificationOrchestrator:
    """Coordena exposição geográfica e avaliação determinística de seguros."""

    def __init__(
        self,
        location_matcher: LocationMatcher,
        rules_engine: InsuranceRulesEngine,
        insured_repository: InsuredRepository | None = None,
    ) -> None:
        self.location_matcher = location_matcher
        self.rules_engine = rules_engine
        self.insured_repository = insured_repository

    def evaluate_event(
        self,
        weather_event: WeatherEvent,
        insureds: Iterable[Insured] | None = None,
    ) -> list[NotificationDecision]:
        """Avalia um evento em uma ordem determinística, sem modificar decisões."""
        candidates = self._resolve_insureds(insureds)
        decisions: list[NotificationDecision] = []
        for insured in candidates:
            if not self.location_matcher.matches(weather_event, insured):
                continue
            decisions.append(self.rules_engine.evaluate(weather_event, insured))
        return decisions

    def _resolve_insureds(
        self,
        insureds: Iterable[Insured] | None,
    ) -> list[Insured]:
        if insureds is not None:
            return list(insureds)
        if self.insured_repository is None:
            raise ValueError(
                "insureds deve ser informado quando não há InsuredRepository injetado"
            )
        return self.insured_repository.list_all()
