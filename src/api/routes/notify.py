from fastapi import APIRouter, HTTPException

from src.api.routes.evaluate import EvaluateEventRequest
from src.domain.insurance.rules_engine import RULES
from src.repositories.insured_repository import InsuredRepositoryError
from src.services.notification_service import NotificationService, ProactiveNotification


def build_notify_router(service: NotificationService) -> APIRouter:
    router = APIRouter()

    @router.post("/notify", response_model=list[ProactiveNotification])
    def notify_event(request: EvaluateEventRequest) -> list[ProactiveNotification]:
        try:
            return service.notify_event(request.to_weather_event())
        except InsuredRepositoryError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    return router


def build_meta_router(insured_repository) -> APIRouter:
    router = APIRouter()

    @router.get("/insureds")
    def list_insureds() -> list[dict]:
        try:
            return [
                insured.model_dump(mode="json")
                for insured in insured_repository.list_all()
            ]
        except InsuredRepositoryError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @router.get("/rules")
    def list_rules() -> list[dict]:
        return [
            {
                "rule_id": rule.rule_id,
                "event_type": rule.event_type.value,
                "evidence_type": rule.evidence_type.value,
                "policy_type": rule.policy_type.value,
                "priority": rule.priority.value,
            }
            for rule in RULES
        ]

    return router
