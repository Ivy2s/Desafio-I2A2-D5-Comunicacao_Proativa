"""Deprecado: o agente de comunicação foi substituído pelo Message Agent.

A responsabilidade de gerar as mensagens proativas agora está em
``src.agents.message_agent`` (Grok + template determinístico) e o envio
simulado em ``src.services.notification_service``.
"""

from src.agents.message_agent import (  # noqa: F401
    GeneratedMessage,
    MessageGenerationError,
    MessageGenerator,
)
