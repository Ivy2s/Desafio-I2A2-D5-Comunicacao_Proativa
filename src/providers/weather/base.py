from typing import Protocol

from src.domain.weather.models import WeatherInput


class WeatherProviderError(RuntimeError):
    """Erro base para falhas de integração meteorológica."""


class WeatherProviderTimeoutError(WeatherProviderError):
    """A fonte externa não respondeu dentro do timeout configurado."""


class WeatherProviderHTTPError(WeatherProviderError):
    """A fonte externa retornou um status HTTP de erro."""


class WeatherProviderInvalidResponseError(WeatherProviderError):
    """A fonte externa retornou payload inválido ou incompleto."""


class WeatherProvider(Protocol):
    def get_weather(self, latitude: float, longitude: float) -> WeatherInput:
        """Retorna dados meteorológicos normalizados para uma localização."""
