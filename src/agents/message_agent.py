"""Agente de Mensagens: gera o texto da comunicação proativa com o segurado.

O LLM (Grok) é usado exclusivamente para redigir/personalizar o texto a partir
de uma `NotificationDecision` já produzida pelo Rules Engine. Ele não seleciona
segurados, não avalia apólices e não calcula prioridade. Sem chave de API ou em
caso de falha, um gerador determinístico de templates garante o fluxo completo.
"""

import httpx
from pydantic import BaseModel, ConfigDict, Field

from src.domain.insurance.enums import NotificationPriority, PolicyType
from src.domain.insurance.models import Insured, NotificationDecision
from src.domain.weather.models import WeatherEvent

GENERATED_BY_LLM = "grok"
GENERATED_BY_TEMPLATE = "template"


class GeneratedMessage(BaseModel):
    """Texto final da comunicação e o gerador que o produziu."""

    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1)
    generated_by: str = Field(min_length=1)


class MessageGenerationError(RuntimeError):
    """Falha na geração da mensagem pelo provedor de LLM."""


class MessageGenerator:
    """Contrato de geração de mensagem para um evento e decisão já avaliados."""

    def generate(
        self,
        insured: Insured,
        event: WeatherEvent,
        decision: NotificationDecision,
    ) -> GeneratedMessage:
        raise NotImplementedError


class GrokMessageGenerator(MessageGenerator):
    """Gera a mensagem via API compatível OpenAI do Grok (x.ai)."""

    def __init__(
        self,
        api_key: str,
        model: str = "grok-4-fast-non-reasoning",
        base_url: str = "https://api.x.ai/v1",
        timeout_seconds: float = 30.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self._client = httpx.Client(
            timeout=timeout_seconds,
            transport=transport,
        )

    def generate(
        self,
        insured: Insured,
        event: WeatherEvent,
        decision: NotificationDecision,
    ) -> GeneratedMessage:
        prompt = build_message_prompt(insured, event, decision)
        try:
            response = self._client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "Você é o agente de comunicação proativa de uma "
                                "seguradora brasileira. Redija mensagens curtas, "
                                "empáticas e objetivas em português do Brasil. "
                                "Nunca invente coberturas, valores ou sinistros."
                            ),
                        },
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.7,
                },
            )
            response.raise_for_status()
            payload = response.json()
            text = payload["choices"][0]["message"]["content"].strip()
        except (httpx.HTTPError, KeyError, IndexError, TypeError) as exc:
            raise MessageGenerationError(f"Falha ao consultar o Grok: {exc}") from exc

        if not text:
            raise MessageGenerationError("Grok retornou mensagem vazia.")
        return GeneratedMessage(text=text, generated_by=GENERATED_BY_LLM)


class TemplateMessageGenerator(MessageGenerator):
    """Gerador determinístico em português, usado como fallback do MVP."""

    EVENT_LABELS = {
        "HEAVY_RAIN": "chuva intensa",
        "HAIL": "granizo",
        "STRONG_WIND": "ventos fortes",
    }

    EVENT_TIPS: dict[str, dict[str, list[str]]] = {
        "HEAVY_RAIN": {
            "HOME": [
                "verifique calhas, ralos e a vedação de janelas",
                "afaste documentos e eletrônicos do piso e retire veículos de áreas alagáveis",
            ],
            "AUTO": [
                "evite atravessar ruas alagadas e estacione longe de encostas e árvores",
            ],
        },
        "HAIL": {
            "AUTO": [
                "se possível, deixe o veículo em cobertura ou proteja-o com lona",
                "evite dirigir durante a queda de granizo",
            ],
            "HOME": [
                "recolha objetos de áreas externas e proteja janelas e vidros",
            ],
        },
        "STRONG_WIND": {
            "HOME": [
                "recolha móveis, vasos e toldos de áreas externas",
                "afaste-se de janelas, árvores e estruturas provisórias",
            ],
            "AUTO": [
                "prefira estacionar em locais fechados e longe de árvores e placas",
            ],
        },
    }

    PRIORITY_LABELS = {
        NotificationPriority.HIGH: "atenção imediata",
        NotificationPriority.MEDIUM: "atenção",
    }

    def generate(
        self,
        insured: Insured,
        event: WeatherEvent,
        decision: NotificationDecision,
    ) -> GeneratedMessage:
        event_label = self.EVENT_LABELS.get(event.event_type.value, event.event_type.value)
        city = insured.location.municipality or "sua região"
        policy_types = sorted(
            {policy.policy_type.value for policy in insured.policies if policy.active}
        )
        tips: list[str] = []
        for policy_type in policy_types:
            tips.extend(
                self.EVENT_TIPS.get(event.event_type.value, {}).get(policy_type, [])
            )
        if not tips:
            tips = ["mantenha-se em local seguro e acompanhe os avisos oficiais"]

        urgency = self.PRIORITY_LABELS.get(
            decision.priority, "seguimos acompanhando a situação"
        )
        policy_text = " e ".join(policy_types) if policy_types else "seu seguro"
        tips_text = "; ".join(tips) + "."

        text = (
            f"Olá, {insured.name}! Detectamos {event_label} na região de {city} "
            f"e a sua situação requer {urgency}. Como você possui apólice "
            f"{policy_text} ativa, recomendamos: {tips_text} "
            f"Sua assistência 24h está à disposição caso precise de apoio — "
            f"não é necessário aguardar a ocorrência de um sinistro para falar "
            f"conosco."
        )
        return GeneratedMessage(text=text, generated_by=GENERATED_BY_TEMPLATE)


class ResilientMessageGenerator(MessageGenerator):
    """Tenta o Grok primeiro; em falha ou ausência de chave usa o template."""

    def __init__(
        self,
        primary: MessageGenerator | None,
        fallback: MessageGenerator,
    ) -> None:
        self.primary = primary
        self.fallback = fallback

    def generate(
        self,
        insured: Insured,
        event: WeatherEvent,
        decision: NotificationDecision,
    ) -> GeneratedMessage:
        if self.primary is not None:
            try:
                return self.primary.generate(insured, event, decision)
            except MessageGenerationError:
                pass
        return self.fallback.generate(insured, event, decision)


def build_message_prompt(
    insured: Insured,
    event: WeatherEvent,
    decision: NotificationDecision,
) -> str:
    city = insured.location.municipality or "região não informada"
    policies = ", ".join(
        f"{policy.policy_type.value} ({policy.status.value})"
        for policy in insured.policies
    )
    measurements = event.measurements.model_dump(exclude_none=True)
    return (
        "Redija a mensagem proativa de alerta para o segurado abaixo.\n\n"
        f"Segurado: {insured.name}\n"
        f"Cidade: {city}\n"
        f"Apólices: {policies}\n\n"
        f"Evento climático: {event.event_type.value}\n"
        f"Evidência: {event.evidence_type.value}\n"
        f"Severidade: {event.severity.value}\n"
        f"Prioridade da notificação: {decision.priority.value}\n"
        f"Regras aplicadas: {', '.join(decision.matched_rules) or 'nenhuma'}\n"
        f"Motivo da decisão: {decision.reason}\n"
        f"Medições: {measurements or 'não disponíveis'}\n\n"
        "Requisitos:\n"
        "1. Cumprimente o segurado pelo nome e informe o evento climático na cidade.\n"
        "2. Dê de 1 a 3 orientações preventivas coerentes com o tipo de apólice ativa.\n"
        "3. Mencione que a assistência 24h está à disposição.\n"
        "4. Tom empático e objetivo, no máximo 4 frases, sem inventar coberturas."
    )
