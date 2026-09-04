from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

from src.domain.insurance.enums import (
    NotificationPriority,
    PolicyStatus,
    PolicyType,
)
from src.domain.location import Location


class Policy(BaseModel):
    """Dados estruturais de uma apólice, sem regras de notificação."""

    model_config = ConfigDict(extra="forbid")

    policy_id: str = Field(min_length=1)
    policy_type: PolicyType
    status: PolicyStatus

    @computed_field
    @property
    def active(self) -> bool:
        """Compatibilidade do contrato: status ativo expõe active=True."""
        return self.status is PolicyStatus.ACTIVE


class Insured(BaseModel):
    """Segurado e suas apólices, sem comportamento de decisão."""

    model_config = ConfigDict(extra="forbid")

    insured_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    location: Location
    policies: list[Policy] = Field(min_length=1)

    @field_validator("insured_id", "name")
    @classmethod
    def text_fields_must_not_be_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("campo não pode ser vazio")
        return stripped


class NotificationDecision(BaseModel):
    """Contrato de saída futuro do Rules Engine."""

    model_config = ConfigDict(extra="forbid")

    insured_id: str = Field(min_length=1)
    eligible: bool
    reason: str = Field(min_length=1)
    priority: NotificationPriority
    matched_rules: list[str] = Field(default_factory=list)

    @field_validator("insured_id", "reason")
    @classmethod
    def decision_text_fields_must_not_be_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("campo não pode ser vazio")
        return stripped
