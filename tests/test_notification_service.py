import json
from datetime import datetime, timezone

from src.agents.message_agent import TemplateMessageGenerator
from src.domain.insurance.enums import PolicyStatus, PolicyType
from src.domain.insurance.location_matcher import CoordinateRadiusMatcher
from src.domain.insurance.models import Insured, Policy
from src.domain.insurance.rules_engine import InsuranceRulesEngine
from src.domain.location import Location
from src.domain.weather.enums import EventType, EvidenceType, Severity
from src.domain.weather.models import Measurements, WeatherEvent
from src.services.notification_service import (
    STATUS_NOT_SENT,
    STATUS_SENT,
    NotificationService,
)


def make_event() -> WeatherEvent:
    return WeatherEvent(
        event_id="event-1",
        event_type=EventType.HEAVY_RAIN,
        evidence_type=EvidenceType.ALERT,
        severity=Severity.HIGH,
        timestamp=datetime(2026, 9, 2, 13, tzinfo=timezone.utc),
        location=Location(latitude=-15.79, longitude=-47.93),
        measurements=Measurements(),
        source="test",
    )


class Repository:
    def list_all(self):
        return [
            Insured(
                insured_id="insured-1",
                name="Ana Martins",
                location=Location(latitude=-15.79, longitude=-47.93, municipality="Brasília"),
                policies=[
                    Policy(
                        policy_id="p1",
                        policy_type=PolicyType.HOME,
                        status=PolicyStatus.ACTIVE,
                    )
                ],
            ),
            Insured(
                insured_id="insured-2",
                name="Bruno Almeida",
                location=Location(latitude=-25.42, longitude=-49.27),
                policies=[
                    Policy(
                        policy_id="p2",
                        policy_type=PolicyType.HOME,
                        status=PolicyStatus.ACTIVE,
                    )
                ],
            ),
            Insured(
                insured_id="insured-3",
                name="Carla Souza",
                location=Location(latitude=-15.80, longitude=-47.92, municipality="Brasília"),
                policies=[
                    Policy(
                        policy_id="p3",
                        policy_type=PolicyType.HOME,
                        status=PolicyStatus.INACTIVE,
                    )
                ],
            ),
        ]


def build_service(persistence_path: str | None) -> NotificationService:
    return NotificationService(
        location_matcher=CoordinateRadiusMatcher(25),
        rules_engine=InsuranceRulesEngine(),
        message_generator=TemplateMessageGenerator(),
        insured_repository=Repository(),
        persistence_path=persistence_path,
    )


def test_notify_event_returns_only_exposed_insureds_with_status():
    notifications = build_service(None).notify_event(make_event())

    assert [item.insured_id for item in notifications] == ["insured-1", "insured-3"]
    assert notifications[0].status == STATUS_SENT
    assert notifications[0].message is not None
    assert notifications[0].message.text
    assert notifications[0].sent_at is not None
    assert notifications[1].status == STATUS_NOT_SENT
    assert notifications[1].message is None


def test_notify_event_persists_eligible_notifications(tmp_path):
    path = tmp_path / "sent_notifications.json"
    service = build_service(str(path))

    service.notify_event(make_event())
    service.notify_event(make_event())

    persisted = json.loads(path.read_text(encoding="utf-8"))
    assert len(persisted) == 2
    assert persisted[0]["insured_id"] == "insured-1"
    assert persisted[0]["status"] == STATUS_SENT
