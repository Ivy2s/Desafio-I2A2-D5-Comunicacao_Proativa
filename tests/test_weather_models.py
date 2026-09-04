from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from src.domain.weather.models import Location, Measurements, WeatherAlert, WeatherInput


def test_domain_rejects_naive_datetimes():
    naive = datetime(2026, 9, 2, 13)

    with pytest.raises(ValidationError, match="timezone-aware"):
        WeatherInput(
            location=Location(latitude=-15.79, longitude=-47.93),
            observed_at=naive,
            source="test",
        )
    with pytest.raises(ValidationError, match="timezone-aware"):
        WeatherAlert(
            alert_id="alert-1",
            phenomenon="Chuvas Intensas",
            starts_at=naive,
        )


def test_domain_normalizes_aware_datetimes_to_utc():
    local_offset = timezone(timedelta(hours=-3))
    weather = WeatherInput(
        location=Location(latitude=-15.79, longitude=-47.93),
        observed_at=datetime(2026, 9, 2, 10, tzinfo=local_offset),
        measurements=Measurements(temperature_celsius=20),
        source="test",
    )

    assert weather.observed_at == datetime(2026, 9, 2, 13, tzinfo=timezone.utc)
    assert weather.observed_at.tzinfo is timezone.utc
