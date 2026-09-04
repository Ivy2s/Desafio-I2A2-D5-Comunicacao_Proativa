from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.domain.insurance.models import NotificationDecision
from src.domain.weather.enums import EventType, EvidenceType, Severity
from src.domain.weather.models import Measurements, WeatherEvent
from src.domain.location import Location
from src.repositories.insured_repository import InsuredRepositoryError
from src.services.weather_notification_orchestrator import (
    WeatherNotificationOrchestrator,
)


class EvaluateEventRequest(BaseModel):
    """DTO HTTP que aceita o evento mínimo e o converte para WeatherEvent."""

    model_config = ConfigDict(extra="forbid")

    event_id: str = Field(default_factory=lambda: f"api-{uuid4().hex}", min_length=1)
    event_type: EventType
    evidence_type: EvidenceType
    severity: Severity
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    location: Location
    measurements: Measurements = Field(default_factory=Measurements)
    source: str = Field(default="api", min_length=1)
    source_reference: str | None = None
    description: str | None = None

    @field_validator("timestamp")
    @classmethod
    def timestamp_must_be_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp deve ser timezone-aware")
        return value

    def to_weather_event(self) -> WeatherEvent:
        return WeatherEvent(**self.model_dump())


def build_evaluate_router(
    orchestrator: WeatherNotificationOrchestrator,
) -> APIRouter:
    router = APIRouter()

    @router.post("/evaluate", response_model=list[NotificationDecision])
    def evaluate_event(request: EvaluateEventRequest) -> list[NotificationDecision]:
        try:
            return orchestrator.evaluate_event(request.to_weather_event())
        except InsuredRepositoryError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    return router
