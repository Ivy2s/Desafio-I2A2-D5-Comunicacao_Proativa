import pytest

from src.domain.weather.detector import WeatherDetector
from src.domain.weather.enums import EventType, EvidenceType, Severity
from src.domain.weather.models import Measurements, WeatherAlert
from tests.conftest import provider_for


@pytest.mark.parametrize(
    ("fixture", "expected_type"),
    [
        ("alerts_heavy_rain.json", EventType.HEAVY_RAIN),
        ("alerts_hail.json", EventType.HAIL),
        ("alerts_strong_wind.json", EventType.STRONG_WIND),
    ],
)
def test_detects_supported_alert_events(fixture, expected_type, settings):
    weather = provider_for(fixture, settings).get_weather(-15.79, -47.93)
    events = WeatherDetector(settings.weather_thresholds).detect(weather)

    assert expected_type in {event.event_type for event in events}
    assert all(event.source == "INMET/WIS2" for event in events)
    assert all(event.evidence_type is EvidenceType.ALERT for event in events)


def test_hail_uses_explicit_inmet_signal(settings):
    weather = provider_for("alerts_hail.json", settings).get_weather(-15.79, -47.93)
    event = next(
        event
        for event in WeatherDetector(settings.weather_thresholds).detect(weather)
        if event.event_type is EventType.HAIL
    )

    assert event.severity is Severity.HIGH
    assert "granizo" in event.description.lower()


def test_no_relevant_event_returns_empty_list(settings):
    weather = provider_for("alerts_no_relevant_event.json", settings).get_weather(
        -15.79, -47.93
    )

    assert WeatherDetector(settings.weather_thresholds).detect(weather) == []


def test_observation_thresholds_detect_rain_and_wind(settings):
    weather = provider_for("alerts_no_relevant_event.json", settings).get_weather(
        -15.79, -47.93
    )
    measurement_values = weather.measurements.model_dump()
    measurement_values["precipitation_rate_mm_per_hour"] = 25.0
    measurement_values["wind_speed_kmh"] = 90.0
    measurements = Measurements(**measurement_values)
    events = WeatherDetector(settings.weather_thresholds).detect(
        weather.model_copy(update={"alerts": [], "measurements": measurements})
    )

    assert {event.event_type for event in events} == {
        EventType.HEAVY_RAIN,
        EventType.STRONG_WIND,
    }
    assert next(event for event in events if event.event_type is EventType.STRONG_WIND).severity is Severity.HIGH


def test_thresholds_include_the_boundary_and_reject_values_below(settings):
    weather = provider_for("alerts_no_relevant_event.json", settings).get_weather(
        -15.79, -47.93
    )
    detector = WeatherDetector(settings.weather_thresholds)

    exact_values = Measurements(
        temperature_celsius=22.0,
        precipitation_rate_mm_per_hour=20.0,
        wind_speed_kmh=60.0,
    )
    exact_events = detector.detect(
        weather.model_copy(update={"alerts": [], "measurements": exact_values})
    )
    below_values = Measurements(
        temperature_celsius=22.0,
        precipitation_rate_mm_per_hour=19.99,
        wind_speed_kmh=59.99,
    )
    below_events = detector.detect(
        weather.model_copy(update={"alerts": [], "measurements": below_values})
    )

    assert {event.event_type for event in exact_events} == {
        EventType.HEAVY_RAIN,
        EventType.STRONG_WIND,
    }
    assert below_events == []
    assert all(event.evidence_type is EvidenceType.OBSERVATION for event in exact_events)


def test_observation_wind_gust_alone_can_trigger_strong_wind(settings):
    weather = provider_for("alerts_no_relevant_event.json", settings).get_weather(
        -15.79, -47.93
    )
    measurements = Measurements(wind_gust_kmh=60.0)

    events = WeatherDetector(settings.weather_thresholds).detect(
        weather.model_copy(update={"alerts": [], "measurements": measurements})
    )

    assert [event.event_type for event in events] == [EventType.STRONG_WIND]
    assert events[0].severity is Severity.MEDIUM


def test_hail_requires_explicit_alert_signal_and_is_not_inferred_from_measurements(settings):
    weather = provider_for("alerts_no_relevant_event.json", settings).get_weather(
        -15.79, -47.93
    )
    alert_without_hail = WeatherAlert(
        alert_id="alert-no-hail",
        phenomenon="Chuvas intensas",
        severity="Perigo",
        starts_at=weather.observed_at,
        description="Chuva e vento sem indicação de outro fenômeno.",
    )
    weather_with_non_hail_alert = weather.model_copy(
        update={
            "alerts": [alert_without_hail],
            "measurements": Measurements(
                temperature_celsius=20,
                precipitation_rate_mm_per_hour=40,
                wind_speed_kmh=70,
            ),
        }
    )

    events = WeatherDetector(settings.weather_thresholds).detect(
        weather_with_non_hail_alert
    )

    assert EventType.HAIL not in {event.event_type for event in events}
    assert EventType.HEAVY_RAIN in {event.event_type for event in events}
