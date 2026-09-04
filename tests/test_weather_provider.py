import json

import httpx
import pytest

from src.domain.weather.models import WeatherInput
from src.providers.weather.base import (
    WeatherProviderHTTPError,
    WeatherProviderInvalidResponseError,
    WeatherProviderTimeoutError,
)
from src.providers.weather.inmet import INMETWeatherProvider
from tests.conftest import load_fixture, provider_for


def test_inmet_provider_normalizes_alerts_and_synop_measurements(settings):
    weather = provider_for("alerts_heavy_rain.json", settings).get_weather(-15.79, -47.93)

    assert weather.source == "INMET/WIS2"
    assert weather.location.latitude == -15.79
    assert weather.measurements.temperature_celsius == 21.4
    assert weather.measurements.precipitation_mm == 12.5
    assert weather.measurements.wind_speed_kmh == 72.0
    assert weather.measurements.wind_gust_kmh == 90.0
    assert weather.alerts[0].measurements.precipitation_rate_mm_per_hour == 30.0
    assert weather.observed_at.tzinfo.utcoffset(weather.observed_at) is not None
    assert weather.observed_at.tzinfo.tzname(weather.observed_at) == "UTC"
    assert isinstance(weather, WeatherInput)


def test_provider_rejects_invalid_alert(settings):
    alerts = load_fixture("alerts_invalid.json")
    synop = load_fixture("synop_observations.json")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=alerts if request.url.path == "/avisos/ativos" else synop)

    provider = INMETWeatherProvider(
        settings=settings,
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    with pytest.raises(WeatherProviderInvalidResponseError, match="obrigatórios"):
        provider.get_weather(-15.79, -47.93)


def test_provider_rejects_empty_observation_payload(settings):
    alerts = {"hoje": [], "futuro": []}
    synop = {"type": "FeatureCollection", "features": []}

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=alerts if request.url.path == "/avisos/ativos" else synop)

    provider = INMETWeatherProvider(
        settings=settings,
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    with pytest.raises(WeatherProviderInvalidResponseError, match="não contém uma observação"):
        provider.get_weather(-15.79, -47.93)


def test_provider_selects_latest_report_for_stable_station_identity(settings):
    alerts = {"hoje": [], "futuro": []}
    station_id = "0-20000-0-83423"
    reports = [
        ("2026-09-04T09:00:00Z", "27.3", [-49.26389, -16.67306]),
        ("2026-09-04T12:00:00Z", "30.1", [-49.26389, -16.67306]),
        ("2026-09-04T15:00:00Z", "36.4", [-49.23333, -16.65000]),
    ]
    features = [
        {
            "geometry": {"type": "Point", "coordinates": coordinates},
            "properties": {
                "name": name,
                "value": value,
                "units": units,
                "reportTime": report_time,
                "reportId": f"{station_id}-{report_time[0:4]}{report_time[5:7]}{report_time[8:10]}{report_time[11:13]}{report_time[14:16]}",
                "wigos_station_identifier": station_id,
            },
        }
        for report_time, temperature, coordinates in reports
        for name, value, units in [
            ("air_temperature", temperature, "Celsius"),
            ("wind_speed", "2", "m/s"),
        ]
    ]
    synop = {"type": "FeatureCollection", "features": features}

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=alerts if request.url.path == "/avisos/ativos" else synop)

    provider = INMETWeatherProvider(
        settings=settings,
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    weather = provider.get_weather(-16.6869, -49.2648)

    assert weather.observed_at.isoformat() == "2026-09-04T15:00:00+00:00"
    assert weather.measurements.temperature_celsius == 36.4


@pytest.mark.parametrize(
    ("exception", "expected"),
    [
        (httpx.ReadTimeout("timed out"), WeatherProviderTimeoutError),
        (httpx.ConnectError("offline"), WeatherProviderHTTPError),
    ],
)
def test_provider_exposes_network_errors(settings, exception, expected):
    def handler(request: httpx.Request) -> httpx.Response:
        raise exception

    provider = INMETWeatherProvider(
        settings=settings,
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    with pytest.raises(expected):
        provider.get_weather(-15.79, -47.93)


def test_provider_exposes_http_errors(settings):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"error": "unavailable"})

    provider = INMETWeatherProvider(
        settings=settings,
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    with pytest.raises(WeatherProviderHTTPError, match="503"):
        provider.get_weather(-15.79, -47.93)


def test_provider_drops_inmet_missing_value_sentinels(settings):
    alerts = {"hoje": [], "futuro": []}
    synop = {
        "type": "FeatureCollection",
        "features": [
            {
                "geometry": {"type": "Point", "coordinates": [-47.9, -15.8]},
                "properties": {
                    "name": name,
                    "value": value,
                    "units": units,
                    "reportTime": "2026-09-02T13:00:00Z",
                    "reportId": "station-1",
                },
            }
            for name, value, units in [
                ("air_temperature", 9999, "Celsius"),
                ("total_precipitation_or_total_water_equivalent", "Null", "kg m-2"),
                ("wind_speed", "", "m/s"),
                ("maximum_wind_gust_speed", -9999, "m/s"),
                ("air_temperature", 999.9, "Celsius"),
                ("wind_speed", -999.9, "m/s"),
            ]
        ],
    }

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/avisos/ativos":
            return httpx.Response(200, json=alerts)
        return httpx.Response(
            200,
            content=json.dumps(synop, allow_nan=True).encode("utf-8"),
            headers={"content-type": "application/json"},
        )

    provider = INMETWeatherProvider(
        settings=settings,
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    weather = provider.get_weather(-15.79, -47.93)

    assert weather.measurements.model_dump(exclude_none=True) == {}


def test_provider_rejects_non_finite_measurement(settings):
    alerts = {"hoje": [], "futuro": []}
    synop = {
        "type": "FeatureCollection",
        "features": [
            {
                "geometry": {"type": "Point", "coordinates": [-47.9, -15.8]},
                "properties": {
                    "name": "wind_speed",
                    "value": float("nan"),
                    "units": "m/s",
                    "reportTime": "2026-09-02T13:00:00Z",
                    "reportId": "station-1",
                },
            }
        ],
    }

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/avisos/ativos":
            return httpx.Response(200, json=alerts)
        return httpx.Response(
            200,
            content=json.dumps(synop, allow_nan=True).encode("utf-8"),
            headers={"content-type": "application/json"},
        )

    provider = INMETWeatherProvider(
        settings=settings,
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    with pytest.raises(WeatherProviderInvalidResponseError, match="não finito"):
        provider.get_weather(-15.79, -47.93)


def test_provider_rejects_negative_physical_measurement(settings):
    alerts = {"hoje": [], "futuro": []}
    synop = {
        "type": "FeatureCollection",
        "features": [
            {
                "geometry": {"type": "Point", "coordinates": [-47.9, -15.8]},
                "properties": {
                    "name": "wind_speed",
                    "value": -1,
                    "units": "m/s",
                    "reportTime": "2026-09-02T13:00:00Z",
                    "reportId": "station-1",
                },
            }
        ],
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=alerts if request.url.path == "/avisos/ativos" else synop)

    provider = INMETWeatherProvider(
        settings=settings,
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    with pytest.raises(WeatherProviderInvalidResponseError, match="negativa"):
        provider.get_weather(-15.79, -47.93)
