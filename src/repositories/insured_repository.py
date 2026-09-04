import json
from pathlib import Path
from typing import Protocol

from pydantic import TypeAdapter, ValidationError

from src.domain.insurance.models import Insured


class InsuredRepositoryError(RuntimeError):
    """Erro ao carregar ou validar o dataset de segurados."""


class InsuredRepository(Protocol):
    """Contrato de leitura dos segurados disponíveis para avaliação."""

    def list_all(self) -> list[Insured]:
        """Retorna todos os segurados em uma ordem estável."""


class JsonInsuredRepository:
    """Repositório local que valida cada registro contra o domínio de seguros."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def list_all(self) -> list[Insured]:
        try:
            raw_content = self.path.read_text(encoding="utf-8")
        except OSError as exc:
            raise InsuredRepositoryError(
                f"não foi possível ler o dataset de segurados: {self.path}"
            ) from exc

        try:
            payload = json.loads(raw_content)
        except json.JSONDecodeError as exc:
            raise InsuredRepositoryError(
                f"dataset de segurados contém JSON inválido: {self.path}"
            ) from exc

        if not isinstance(payload, list):
            raise InsuredRepositoryError(
                "dataset de segurados deve conter uma lista de registros"
            )

        try:
            return TypeAdapter(list[Insured]).validate_python(payload)
        except ValidationError as exc:
            raise InsuredRepositoryError(
                "dataset de segurados contém registro inválido"
            ) from exc
