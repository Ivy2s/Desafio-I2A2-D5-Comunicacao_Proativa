from fastapi import FastAPI

from src.api.routes.evaluate import build_evaluate_router
from src.api.routes.weather import build_weather_router
from src.config.settings import get_settings
from src.domain.insurance.location_matcher import CoordinateRadiusMatcher
from src.domain.insurance.rules_engine import InsuranceRulesEngine
from src.providers.weather.inmet import INMETWeatherProvider
from src.repositories.insured_repository import (
    InsuredRepository,
    JsonInsuredRepository,
)
from src.services.weather_service import WeatherService
from src.services.weather_notification_orchestrator import (
    WeatherNotificationOrchestrator,
)


def create_app(
    service: WeatherService | None = None,
    orchestrator: WeatherNotificationOrchestrator | None = None,
    insured_repository: InsuredRepository | None = None,
) -> FastAPI:
    settings = get_settings()
    weather_service = service or WeatherService(INMETWeatherProvider(settings), settings)
    repository = insured_repository or JsonInsuredRepository(settings.insured_dataset_path)
    notification_orchestrator = orchestrator or WeatherNotificationOrchestrator(
        location_matcher=CoordinateRadiusMatcher(settings.weather_exposure_radius_km),
        rules_engine=InsuranceRulesEngine(),
        insured_repository=repository,
    )
    app = FastAPI(
        title="Desafio 5 — Agente do Tempo",
        version="0.1.0",
        description="API de dados meteorológicos normalizados e eventos climáticos.",
    )
    app.include_router(build_weather_router(weather_service))
    app.include_router(build_evaluate_router(notification_orchestrator))

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
