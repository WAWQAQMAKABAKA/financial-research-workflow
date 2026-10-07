from __future__ import annotations

from typing import Any, Protocol

from pydantic import BaseModel


class StructuredResearchModel(Protocol):
    """Provider-neutral structured generation boundary."""

    def generate(
        self,
        *,
        system_prompt: str,
        input_payload: dict[str, Any],
        output_schema: type[BaseModel],
    ) -> BaseModel | dict[str, Any]:
        ...
