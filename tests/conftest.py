import json
from pathlib import Path
from typing import Any

import httpx
import pytest

from src.config.settings import Settings
from src.providers.weather.inmet import INMETWeatherProvider


FIXTURES = Path(__file__).parent / "fixtures" / "weather"


def load_fixture(name: str) -> Any:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


@pytest.fixture
def settings() -> Settings:
    return Settings(
        inmet_alerts_url="https://test.local/avisos/ativos",
        wis2_synop_url="https://test.local/synop",
        station_search_delta_degrees=0.5,
    )


def provider_for(alert_fixture: str, settings: Settings) -> INMETWeatherProvider:
    alerts = load_fixture(alert_fixture)
    synop_name = (
        "synop_no_event.json"
        if alert_fixture == "alerts_no_relevant_event.json"
        else "synop_observations.json"
    )
    synop = load_fixture(synop_name)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/avisos/ativos":
            return httpx.Response(200, json=alerts)
        if request.url.path == "/synop":
            return httpx.Response(200, json=synop)
        return httpx.Response(404)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    return INMETWeatherProvider(settings=settings, client=client)
