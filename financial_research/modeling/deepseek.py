from __future__ import annotations

import json
from typing import Any, Literal

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_deepseek import ChatDeepSeek
from pydantic import BaseModel


StructuredOutputMethod = Literal[
    "function_calling",
    "json_mode",
    "json_schema",
]


class DeepSeekStructuredResearchModel:
    """DeepSeek implementation of the shared structured research model port."""

    def __init__(
        self,
        *,
        model: str = "deepseek-chat",
        temperature: float | None = 0.0,
        max_retries: int = 2,
        timeout: float | None = 60.0,
        structured_method: StructuredOutputMethod = "function_calling",
        chat_model: BaseChatModel | None = None,
    ) -> None:
        if not model.strip():
            raise ValueError("model must be non-empty")

        if max_retries < 0:
            raise ValueError("max_retries must be >= 0")

        if timeout is not None and timeout <= 0:
            raise ValueError("timeout must be > 0 when provided")

        self._structured_method = structured_method

        if chat_model is not None:
            self._chat_model = chat_model
        else:
            self._chat_model = ChatDeepSeek(
                model=model,
                temperature=temperature,
                max_retries=max_retries,
                timeout=timeout,
            )

    def generate(
        self,
        *,
        system_prompt: str,
        input_payload: dict[str, Any],
        output_schema: type[BaseModel],
    ) -> BaseModel | dict[str, Any]:
        structured_model = self._chat_model.with_structured_output(
            output_schema,
            method=self._structured_method,
            include_raw=False,
        )

        serialized_payload = json.dumps(
            input_payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

        result = structured_model.invoke(
            [
                ("system", system_prompt),
                ("human", serialized_payload),
            ]
        )

        if isinstance(result, BaseModel):
            return result

        if isinstance(result, dict):
            return result

        raise TypeError(
            "DeepSeek structured output must be a Pydantic model or dict; "
            f"got {type(result).__name__}"
        )
