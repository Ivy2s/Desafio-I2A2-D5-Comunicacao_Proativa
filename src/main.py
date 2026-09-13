from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.agents.message_agent import (
    GrokMessageGenerator,
    ResilientMessageGenerator,
    TemplateMessageGenerator,
)
from src.api.routes.evaluate import build_evaluate_router
from src.api.routes.notify import build_meta_router, build_notify_router
from src.api.routes.weather import build_weather_router
from src.config.settings import get_settings
from src.domain.insurance.location_matcher import CoordinateRadiusMatcher
from src.domain.insurance.rules_engine import InsuranceRulesEngine
from src.providers.weather.inmet import INMETWeatherProvider
from src.repositories.insured_repository import (
    InsuredRepository,
    JsonInsuredRepository,
)
from src.services.notification_service import NotificationService
from src.services.weather_service import WeatherService
from src.services.weather_notification_orchestrator import (
    WeatherNotificationOrchestrator,
)


def build_message_generator(settings) -> ResilientMessageGenerator:
    primary = None
    if settings.grok_api_key:
        primary = GrokMessageGenerator(
            api_key=settings.grok_api_key,
            model=settings.grok_model,
            base_url=settings.grok_base_url,
            timeout_seconds=max(settings.http_timeout_seconds, 30.0),
        )
    return ResilientMessageGenerator(
        primary=primary,
        fallback=TemplateMessageGenerator(),
    )


def create_app(
    service: WeatherService | None = None,
    orchestrator: WeatherNotificationOrchestrator | None = None,
    insured_repository: InsuredRepository | None = None,
    notification_service: NotificationService | None = None,
) -> FastAPI:
    settings = get_settings()
    weather_service = service or WeatherService(INMETWeatherProvider(settings), settings)
    repository = insured_repository or JsonInsuredRepository(settings.insured_dataset_path)
    notification_orchestrator = orchestrator or WeatherNotificationOrchestrator(
        location_matcher=CoordinateRadiusMatcher(settings.weather_exposure_radius_km),
        rules_engine=InsuranceRulesEngine(),
        insured_repository=repository,
    )
    notification_svc = notification_service or NotificationService(
        location_matcher=CoordinateRadiusMatcher(settings.weather_exposure_radius_km),
        rules_engine=InsuranceRulesEngine(),
        message_generator=build_message_generator(settings),
        insured_repository=repository,
        persistence_path=settings.sent_notifications_path,
    )
    app = FastAPI(
        title="Desafio 5 — Comunicação Proativa com o Segurado",
        version="0.2.0",
        description=(
            "Monitora eventos climáticos, aplica regras de negócio, gera mensagens "
            "personalizadas com LLM e simula o envio das notificações."
        ),
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(build_weather_router(weather_service))
    app.include_router(build_evaluate_router(notification_orchestrator))
    app.include_router(build_notify_router(notification_svc))
    app.include_router(build_meta_router(repository))

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    frontend_dist = Path("frontend/dist")
    if frontend_dist.is_dir():
        app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")

    return app


app = create_app()
