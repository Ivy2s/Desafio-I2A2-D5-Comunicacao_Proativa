import httpx
import pytest

from src.agents.message_agent import (
    GeneratedMessage,
    GrokMessageGenerator,
    MessageGenerationError,
    ResilientMessageGenerator,
    TemplateMessageGenerator,
)
from src.domain.insurance.enums import NotificationPriority, PolicyStatus, PolicyType
from src.domain.insurance.models import Insured, NotificationDecision, Policy
from src.domain.location import Location
from src.domain.weather.enums import EventType, EvidenceType, Severity
from src.domain.weather.models import Measurements, WeatherEvent
from datetime import datetime, timezone


def make_insured() -> Insured:
    return Insured(
        insured_id="insured-1",
        name="Ana Martins",
        location=Location(latitude=-15.79, longitude=-47.93, municipality="Brasília"),
        policies=[
            Policy(
                policy_id="policy-1",
                policy_type=PolicyType.HOME,
                status=PolicyStatus.ACTIVE,
            )
        ],
    )


def make_event() -> WeatherEvent:
    return WeatherEvent(
        event_id="event-1",
        event_type=EventType.HEAVY_RAIN,
        evidence_type=EvidenceType.ALERT,
        severity=Severity.HIGH,
        timestamp=datetime(2026, 9, 2, 13, tzinfo=timezone.utc),
        location=Location(latitude=-15.79, longitude=-47.93),
        measurements=Measurements(precipitation_rate_mm_per_hour=45.0),
        source="test",
)


def make_decision() -> NotificationDecision:
    return NotificationDecision(
        insured_id="insured-1",
        eligible=True,
        reason="Apólice HOME ativa compatível.",
        priority=NotificationPriority.HIGH,
        matched_rules=["HEAVY_RAIN_HOME_ALERT"],
    )


def test_template_generator_mentions_name_city_and_tips():
    message = TemplateMessageGenerator().generate(make_insured(), make_event(), make_decision())

    assert message.generated_by == "template"
    assert "Ana Martins" in message.text
    assert "Brasília" in message.text
    assert "chuva intensa" in message.text
    assert "assistência 24h" in message.text


def test_grok_generator_parses_completion():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/chat/completions"
        assert request.headers["Authorization"] == "Bearer key"
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "  Mensagem do Grok. "}}]},
        )

    generator = GrokMessageGenerator("key", transport=httpx.MockTransport(handler))
    message = generator.generate(make_insured(), make_event(), make_decision())

    assert message == GeneratedMessage(text="Mensagem do Grok.", generated_by="grok")


def test_grok_generator_raises_on_http_error():
    handler = lambda request: httpx.Response(500, json={"error": "boom"})
    generator = GrokMessageGenerator("key", transport=httpx.MockTransport(handler))

    with pytest.raises(MessageGenerationError):
        generator.generate(make_insured(), make_event(), make_decision())


def test_resilient_generator_falls_back_to_template():
    class FailingGenerator:
        def generate(self, insured, event, decision):
            raise MessageGenerationError("indisponível")

    generator = ResilientMessageGenerator(
        primary=FailingGenerator(),
        fallback=TemplateMessageGenerator(),
    )

    message = generator.generate(make_insured(), make_event(), make_decision())

    assert message.generated_by == "template"
