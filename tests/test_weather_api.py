from datetime import datetime, timezone

from fastapi.testclient import TestClient

from src.api.routes.weather import build_weather_router
from src.domain.weather.models import Location, Measurements, WeatherInput
from src.main import create_app
from src.providers.weather.mock import MockWeatherProvider
from src.services.weather_service import WeatherService


def test_health_endpoint():
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_weather_endpoint_returns_normalized_snapshot_without_internet():
    weather = WeatherInput(
        location=Location(latitude=-15.79, longitude=-47.93),
        observed_at=datetime(2026, 9, 2, 13, tzinfo=timezone.utc),
        measurements=Measurements(temperature_celsius=22.0),
        source="mock",
    )
    provider = MockWeatherProvider(weather)
    service = WeatherService(provider)
    client = TestClient(create_app(service))

    response = client.get("/weather?latitude=-15.79&longitude=-47.93")

    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "mock"
    assert body["measurements"]["temperature_celsius"] == 22.0
    assert body["events"] == []
    assert provider.calls == [(-15.79, -47.93)]


def test_weather_endpoint_validates_coordinates():
    client = TestClient(create_app())

    response = client.get("/weather?latitude=95&longitude=-47.93")

    assert response.status_code == 422
