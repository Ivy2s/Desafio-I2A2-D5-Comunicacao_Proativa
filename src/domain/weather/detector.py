import re
import unicodedata
from dataclasses import dataclass

from src.domain.weather.enums import EventType, EvidenceType, Severity
from src.domain.weather.models import (
    Measurements,
    WeatherAlert,
    WeatherEvent,
    WeatherInput,
)


@dataclass(frozen=True)
class WeatherThresholds:
    """Thresholds de observação; sinais oficiais de alerta têm precedência."""

    heavy_rain_rate_mm_per_hour: float = 20.0
    heavy_rain_daily_mm: float = 50.0
    heavy_rain_high_rate_mm_per_hour: float = 50.0
    heavy_rain_extreme_rate_mm_per_hour: float = 80.0
    heavy_rain_high_daily_mm: float = 100.0
    heavy_rain_extreme_daily_mm: float = 150.0
    strong_wind_speed_kmh: float = 60.0
    strong_wind_high_kmh: float = 80.0
    strong_wind_extreme_kmh: float = 100.0

    def __post_init__(self) -> None:
        values = (
            self.heavy_rain_rate_mm_per_hour,
            self.heavy_rain_daily_mm,
            self.heavy_rain_high_rate_mm_per_hour,
            self.heavy_rain_extreme_rate_mm_per_hour,
            self.heavy_rain_high_daily_mm,
            self.heavy_rain_extreme_daily_mm,
            self.strong_wind_speed_kmh,
            self.strong_wind_high_kmh,
            self.strong_wind_extreme_kmh,
        )
        if any(value <= 0 for value in values):
            raise ValueError("thresholds meteorológicos devem ser positivos")
        if not (
            self.heavy_rain_rate_mm_per_hour
            <= self.heavy_rain_high_rate_mm_per_hour
            <= self.heavy_rain_extreme_rate_mm_per_hour
        ):
            raise ValueError("thresholds horários de chuva devem estar ordenados")
        if not (
            self.heavy_rain_daily_mm
            <= self.heavy_rain_high_daily_mm
            <= self.heavy_rain_extreme_daily_mm
        ):
            raise ValueError("thresholds diários de chuva devem estar ordenados")
        if not (
            self.strong_wind_speed_kmh
            <= self.strong_wind_high_kmh
            <= self.strong_wind_extreme_kmh
        ):
            raise ValueError("thresholds de vento devem estar ordenados")


class WeatherDetector:
    """Converte sinais meteorológicos normalizados em eventos determinísticos."""

    def __init__(self, thresholds: WeatherThresholds | None = None) -> None:
        self.thresholds = thresholds or WeatherThresholds()

    def detect(self, weather: WeatherInput) -> list[WeatherEvent]:
        events: list[WeatherEvent] = []
        relevant_alert_found = False

        for alert in weather.alerts:
            event_types = self._event_types_from_alert(alert)
            if event_types:
                relevant_alert_found = True
            for event_type in event_types:
                events.append(
                    self._event_from_alert(weather, alert, event_type)
                )

        # Observações são usadas quando não há um aviso oficial correspondente.
        # Isso mantém o detector útil mesmo fora da janela de publicação de avisos.
        if not relevant_alert_found:
            events.extend(self._events_from_measurements(weather))

        return events

    def _event_types_from_alert(self, alert: WeatherAlert) -> list[EventType]:
        text = _normalized_text(
            " ".join([alert.phenomenon, alert.description, *alert.risks])
        )
        event_types: list[EventType] = []

        if (
            "chuvas intensas" in text
            or "chuva intensa" in text
            or ("chuva" in text and re.search(r"\bmm\s*/?\s*h", text))
        ):
            event_types.append(EventType.HEAVY_RAIN)
        # Granizo só é reconhecido quando o próprio aviso do INMET o informa.
        if "granizo" in text:
            event_types.append(EventType.HAIL)
        if (
            "vendaval" in text
            or "ventos intensos" in text
            or "rajadas de vento" in text
        ):
            event_types.append(EventType.STRONG_WIND)

        return event_types

    def _event_from_alert(
        self,
        weather: WeatherInput,
        alert: WeatherAlert,
        event_type: EventType,
    ) -> WeatherEvent:
        return WeatherEvent(
            event_id=f"{alert.alert_id}:{event_type.value}",
            event_type=event_type,
            evidence_type=EvidenceType.ALERT,
            severity=_severity_from_alert(alert.severity),
            timestamp=alert.starts_at,
            location=weather.location,
            measurements=_merge_measurements(
                weather.measurements, alert.measurements
            ),
            source=weather.source,
            source_reference=alert.source_reference or alert.alert_id,
            description=alert.description or alert.phenomenon,
        )

    def _events_from_measurements(self, weather: WeatherInput) -> list[WeatherEvent]:
        measurements = weather.measurements
        events: list[WeatherEvent] = []

        if (
            (measurements.precipitation_rate_mm_per_hour or 0.0)
            >= self.thresholds.heavy_rain_rate_mm_per_hour
            or (measurements.precipitation_mm or 0.0)
            >= self.thresholds.heavy_rain_daily_mm
        ):
            events.append(
                self._event_from_measurements(
                    weather,
                    EventType.HEAVY_RAIN,
                    self._rain_severity(measurements),
                )
            )

        wind_value = max(
            value
            for value in (
                measurements.wind_speed_kmh or 0.0,
                measurements.wind_gust_kmh or 0.0,
            )
        )
        if wind_value >= self.thresholds.strong_wind_speed_kmh:
            events.append(
                self._event_from_measurements(
                    weather,
                    EventType.STRONG_WIND,
                    self._wind_severity(wind_value),
                )
            )

        return events

    def _event_from_measurements(
        self,
        weather: WeatherInput,
        event_type: EventType,
        severity: Severity,
    ) -> WeatherEvent:
        return WeatherEvent(
            event_id=f"observation:{event_type.value}:{weather.observed_at.isoformat()}",
            event_type=event_type,
            evidence_type=EvidenceType.OBSERVATION,
            severity=severity,
            timestamp=weather.observed_at,
            location=weather.location,
            measurements=weather.measurements,
            source=weather.source,
            description="Evento identificado a partir de observação meteorológica.",
        )

    def _rain_severity(self, measurements: Measurements) -> Severity:
        rate = measurements.precipitation_rate_mm_per_hour or 0.0
        daily = measurements.precipitation_mm or 0.0
        if (
            rate >= self.thresholds.heavy_rain_extreme_rate_mm_per_hour
            or daily >= self.thresholds.heavy_rain_extreme_daily_mm
        ):
            return Severity.EXTREME
        if (
            rate >= self.thresholds.heavy_rain_high_rate_mm_per_hour
            or daily >= self.thresholds.heavy_rain_high_daily_mm
        ):
            return Severity.HIGH
        return Severity.MEDIUM

    def _wind_severity(self, value: float) -> Severity:
        if value >= self.thresholds.strong_wind_extreme_kmh:
            return Severity.EXTREME
        if value >= self.thresholds.strong_wind_high_kmh:
            return Severity.HIGH
        return Severity.MEDIUM


def _normalized_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(char for char in normalized if not unicodedata.combining(char)).lower()


def _severity_from_alert(value: str | None) -> Severity:
    normalized = _normalized_text(value or "")
    if "grande perigo" in normalized:
        return Severity.EXTREME
    if normalized == "perigo" or normalized.endswith(" perigo"):
        return Severity.HIGH
    if "perigo potencial" in normalized:
        return Severity.MEDIUM
    return Severity.LOW


def _merge_measurements(base: Measurements, extra: Measurements) -> Measurements:
    values: dict[str, float | None] = {}
    for field in Measurements.model_fields:
        base_value = getattr(base, field)
        extra_value = getattr(extra, field)
        values[field] = extra_value if extra_value is not None else base_value
    return Measurements(**values)
