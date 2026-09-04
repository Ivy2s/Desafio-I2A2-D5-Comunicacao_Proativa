from src.config.settings import Settings, get_settings
from src.domain.weather.detector import WeatherDetector
from src.domain.weather.models import WeatherSnapshot
from src.providers.weather.base import WeatherProvider


class WeatherService:
    def __init__(
        self,
        provider: WeatherProvider,
        settings: Settings | None = None,
    ) -> None:
        self.provider = provider
        self.settings = settings or get_settings()
        self.detector = WeatherDetector(self.settings.weather_thresholds)

    def get_weather(self, latitude: float, longitude: float) -> WeatherSnapshot:
        weather = self.provider.get_weather(latitude, longitude)
        events = self.detector.detect(weather)
        return WeatherSnapshot(
            location=weather.location,
            observed_at=weather.observed_at,
            measurements=weather.measurements,
            events=events,
            source=weather.source,
        )
