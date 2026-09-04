from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.domain.weather.detector import WeatherThresholds


class Settings(BaseSettings):
    """Configuração externa, sem credenciais embutidas no código."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    inmet_alerts_url: str = "https://apiprevmet3.inmet.gov.br/avisos/ativos"
    wis2_synop_url: str = (
        "https://wis2bra.inmet.gov.br/oapi/collections/"
        "urn:wmo:md:br-inmet:synop/items"
    )
    http_timeout_seconds: float = Field(default=10.0, gt=0)
    station_search_delta_degrees: float = Field(default=0.5, gt=0)
    insured_dataset_path: str = "data/insureds.json"
    weather_exposure_radius_km: float = Field(default=25.0, gt=0)

    heavy_rain_rate_mm_per_hour: float = Field(default=20.0, gt=0)
    heavy_rain_daily_mm: float = Field(default=50.0, gt=0)
    heavy_rain_high_rate_mm_per_hour: float = Field(default=50.0, gt=0)
    heavy_rain_extreme_rate_mm_per_hour: float = Field(default=80.0, gt=0)
    heavy_rain_high_daily_mm: float = Field(default=100.0, gt=0)
    heavy_rain_extreme_daily_mm: float = Field(default=150.0, gt=0)
    strong_wind_speed_kmh: float = Field(default=60.0, gt=0)
    strong_wind_high_kmh: float = Field(default=80.0, gt=0)
    strong_wind_extreme_kmh: float = Field(default=100.0, gt=0)

    @property
    def weather_thresholds(self) -> WeatherThresholds:
        return WeatherThresholds(
            heavy_rain_rate_mm_per_hour=self.heavy_rain_rate_mm_per_hour,
            heavy_rain_daily_mm=self.heavy_rain_daily_mm,
            heavy_rain_high_rate_mm_per_hour=self.heavy_rain_high_rate_mm_per_hour,
            heavy_rain_extreme_rate_mm_per_hour=self.heavy_rain_extreme_rate_mm_per_hour,
            heavy_rain_high_daily_mm=self.heavy_rain_high_daily_mm,
            heavy_rain_extreme_daily_mm=self.heavy_rain_extreme_daily_mm,
            strong_wind_speed_kmh=self.strong_wind_speed_kmh,
            strong_wind_high_kmh=self.strong_wind_high_kmh,
            strong_wind_extreme_kmh=self.strong_wind_extreme_kmh,
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
