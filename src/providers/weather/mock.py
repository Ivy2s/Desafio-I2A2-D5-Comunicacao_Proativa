from src.domain.weather.models import WeatherInput


class MockWeatherProvider:
    """Provider determinístico para testes e demonstrações locais."""

    def __init__(self, weather: WeatherInput) -> None:
        self.weather = weather
        self.calls: list[tuple[float, float]] = []

    def get_weather(self, latitude: float, longitude: float) -> WeatherInput:
        self.calls.append((latitude, longitude))
        return self.weather.model_copy(deep=True)
