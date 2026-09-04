import os

import pytest

from src.config.settings import Settings
from src.providers.weather.inmet import INMETWeatherProvider


@pytest.mark.integration
@pytest.mark.skipif(
    os.getenv("RUN_EXTERNAL_INTEGRATION") != "1",
    reason="integração externa desabilitada; use RUN_EXTERNAL_INTEGRATION=1",
)
def test_inmet_provider_can_read_live_public_data():
    weather = INMETWeatherProvider(Settings()).get_weather(-15.79, -47.93)

    assert weather.source == "INMET/WIS2"
    assert weather.location.latitude == pytest.approx(-15.79)
    assert weather.location.longitude == pytest.approx(-47.93)
