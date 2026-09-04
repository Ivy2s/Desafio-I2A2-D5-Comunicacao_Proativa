from datetime import datetime, timezone
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, field_validator

from src.domain.location import Location
from src.domain.weather.enums import EventType, EvidenceType, Severity


NonNegativeMeasurement = Annotated[FiniteFloat, Field(ge=0)]


def _require_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("datetime deve ser timezone-aware e informado em UTC")
    return value.astimezone(timezone.utc)


class Measurements(BaseModel):
    """Medições internas, sempre expressas nas unidades do contrato."""

    model_config = ConfigDict(extra="forbid")

    temperature_celsius: FiniteFloat | None = None
    precipitation_mm: NonNegativeMeasurement | None = None
    precipitation_rate_mm_per_hour: NonNegativeMeasurement | None = None
    wind_speed_kmh: NonNegativeMeasurement | None = None
    wind_gust_kmh: NonNegativeMeasurement | None = None


class WeatherAlert(BaseModel):
    """Alerta já normalizado pelo provider, sem o payload original do INMET."""

    model_config = ConfigDict(extra="forbid")

    alert_id: str
    phenomenon: str
    severity: str | None = None
    starts_at: datetime
    ends_at: datetime | None = None
    description: str = ""
    risks: list[str] = Field(default_factory=list)
    measurements: Measurements = Field(default_factory=Measurements)
    source_reference: str | None = None

    @field_validator("starts_at", "ends_at")
    @classmethod
    def timestamps_must_be_utc(cls, value: datetime | None) -> datetime | None:
        return _require_utc(value) if value is not None else None


class WeatherInput(BaseModel):
    """Entrada normalizada que o provider entrega ao detector."""

    model_config = ConfigDict(extra="forbid")

    location: Location
    observed_at: datetime
    measurements: Measurements = Field(default_factory=Measurements)
    alerts: list[WeatherAlert] = Field(default_factory=list)
    source: str = Field(min_length=1)

    @field_validator("observed_at")
    @classmethod
    def observed_at_must_be_utc(cls, value: datetime) -> datetime:
        return _require_utc(value)


class WeatherEvent(BaseModel):
    """Contrato canônico de evento meteorológico do sistema."""

    model_config = ConfigDict(extra="forbid")

    event_id: str
    event_type: EventType
    evidence_type: EvidenceType
    severity: Severity
    timestamp: datetime
    location: Location
    measurements: Measurements
    source: str = Field(min_length=1)
    source_reference: str | None = None
    description: str | None = None

    @field_validator("timestamp")
    @classmethod
    def timestamp_must_be_utc(cls, value: datetime) -> datetime:
        return _require_utc(value)


class WeatherSnapshot(BaseModel):
    """Estado meteorológico normalizado exposto pela API da aplicação."""

    model_config = ConfigDict(extra="forbid")

    location: Location
    observed_at: datetime
    measurements: Measurements
    events: list[WeatherEvent]
    source: str = Field(min_length=1)

    @field_validator("observed_at")
    @classmethod
    def snapshot_observed_at_must_be_utc(cls, value: datetime) -> datetime:
        return _require_utc(value)
