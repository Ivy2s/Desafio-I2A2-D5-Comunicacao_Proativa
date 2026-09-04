import math
from typing import Protocol

from src.domain.insurance.models import Insured
from src.domain.location import Location
from src.domain.weather.models import WeatherEvent


EARTH_RADIUS_KM = 6371.0088


class LocationMatcher(Protocol):
    """Contrato de exposição geográfica entre evento e segurado."""

    def matches(self, weather_event: WeatherEvent, insured: Insured) -> bool:
        """Informa se o segurado está dentro da área simplificada do evento."""


def haversine_distance_km(first: Location, second: Location) -> float:
    """Calcula a distância de grande círculo entre duas coordenadas, em km."""
    first_coordinates = _valid_coordinates(first)
    second_coordinates = _valid_coordinates(second)
    if first_coordinates is None or second_coordinates is None:
        raise ValueError("as duas localizações precisam ter coordenadas válidas")

    first_latitude, first_longitude = map(math.radians, first_coordinates)
    second_latitude, second_longitude = map(math.radians, second_coordinates)
    delta_latitude = second_latitude - first_latitude
    delta_longitude = second_longitude - first_longitude

    haversine = (
        math.sin(delta_latitude / 2) ** 2
        + math.cos(first_latitude)
        * math.cos(second_latitude)
        * math.sin(delta_longitude / 2) ** 2
    )
    central_angle = 2 * math.asin(math.sqrt(min(1.0, haversine)))
    return EARTH_RADIUS_KM * central_angle


class CoordinateRadiusMatcher:
    """Matcher determinístico baseado em um raio configurável em quilômetros."""

    def __init__(self, radius_km: float = 25.0) -> None:
        if not math.isfinite(radius_km) or radius_km <= 0:
            raise ValueError("radius_km deve ser um número finito maior que zero")
        self.radius_km = radius_km

    def matches(self, weather_event: WeatherEvent, insured: Insured) -> bool:
        """Retorna false quando faltam coordenadas ou elas são inválidas."""
        try:
            distance_km = haversine_distance_km(
                weather_event.location,
                insured.location,
            )
        except (AttributeError, TypeError, ValueError):
            return False
        return distance_km <= self.radius_km


def _valid_coordinates(location: Location) -> tuple[float, float] | None:
    try:
        latitude = float(location.latitude)
        longitude = float(location.longitude)
    except (AttributeError, TypeError, ValueError):
        return None

    if (
        not math.isfinite(latitude)
        or not math.isfinite(longitude)
        or not -90 <= latitude <= 90
        or not -180 <= longitude <= 180
    ):
        return None
    return latitude, longitude
