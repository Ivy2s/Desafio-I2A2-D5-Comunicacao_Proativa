from fastapi import APIRouter, HTTPException, Query

from src.domain.weather.models import WeatherSnapshot
from src.providers.weather.base import WeatherProviderError
from src.services.weather_service import WeatherService


def build_weather_router(service: WeatherService) -> APIRouter:
    router = APIRouter()

    @router.get("/weather", response_model=WeatherSnapshot)
    def get_weather(
        latitude: float = Query(..., ge=-90, le=90),
        longitude: float = Query(..., ge=-180, le=180),
    ) -> WeatherSnapshot:
        try:
            return service.get_weather(latitude, longitude)
        except WeatherProviderError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    return router
