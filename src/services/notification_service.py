"""Serviço de notificação: aplica exposição + regras, gera mensagens e simula o envio."""

import json
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from src.agents.message_agent import GeneratedMessage, MessageGenerator
from src.domain.insurance.location_matcher import LocationMatcher
from src.domain.insurance.models import Insured, NotificationDecision
from src.domain.insurance.rules_engine import InsuranceRulesEngine
from src.domain.weather.models import WeatherEvent
from src.repositories.insured_repository import InsuredRepository

STATUS_SENT = "SIMULATED_SENT"
STATUS_NOT_SENT = "NOT_SENT"


class ProactiveNotification(BaseModel):
    """Resultado consolidado de uma etapa completa de comunicação proativa."""

    model_config = ConfigDict(extra="forbid")

    insured_id: str = Field(min_length=1)
    insured_name: str = Field(min_length=1)
    municipality: str | None = None
    event: WeatherEvent
    decision: NotificationDecision
    message: GeneratedMessage | None = None
    status: str = Field(min_length=1)
    sent_at: datetime | None = None


class NotificationService:
    """Coordena exposição geográfica, regras de negócio, mensagem e envio simulado."""

    def __init__(
        self,
        location_matcher: LocationMatcher,
        rules_engine: InsuranceRulesEngine,
        message_generator: MessageGenerator,
        insured_repository: InsuredRepository,
        persistence_path: str | None = None,
    ) -> None:
        self.location_matcher = location_matcher
        self.rules_engine = rules_engine
        self.message_generator = message_generator
        self.insured_repository = insured_repository
        self.persistence_path = persistence_path

    def notify_event(self, weather_event: WeatherEvent) -> list[ProactiveNotification]:
        notifications: list[ProactiveNotification] = []
        sent_at = datetime.now(timezone.utc)
        for insured in self.insured_repository.list_all():
            if not self.location_matcher.matches(weather_event, insured):
                continue
            decision = self.rules_engine.evaluate(weather_event, insured)
            notification = self._build_notification(insured, weather_event, decision, sent_at)
            notifications.append(notification)

        if any(item.decision.eligible for item in notifications):
            self._persist(notifications)
        return notifications

    def _build_notification(
        self,
        insured: Insured,
        weather_event: WeatherEvent,
        decision: NotificationDecision,
        sent_at: datetime,
    ) -> ProactiveNotification:
        base = {
            "insured_id": insured.insured_id,
            "insured_name": insured.name,
            "municipality": insured.location.municipality,
            "event": weather_event,
            "decision": decision,
        }
        if not decision.eligible:
            return ProactiveNotification(status=STATUS_NOT_SENT, **base)

        message = self.message_generator.generate(insured, weather_event, decision)
        return ProactiveNotification(
            message=message,
            status=STATUS_SENT,
            sent_at=sent_at,
            **base,
        )

    def _persist(self, notifications: list[ProactiveNotification]) -> None:
        if self.persistence_path is None:
            return
        path = Path(self.persistence_path)
        existing: list[dict] = []
        if path.exists():
            try:
                loaded = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(loaded, list):
                    existing = loaded
            except (json.JSONDecodeError, OSError):
                existing = []
        existing.extend(
            item.model_dump(mode="json") for item in notifications if item.decision.eligible
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(existing, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
