import json

import pytest
from pydantic import BaseModel

import financial_research.modeling.deepseek as deepseek_module
from financial_research.modeling import (
    DeepSeekStructuredResearchModel,
)


class ExampleOutput(BaseModel):
    answer: str


class FakeStructuredRunnable:
    def __init__(
        self,
        response,
        *,
        error=None,
    ):
        self.response = response
        self.error = error
        self.calls = []

    def invoke(self, messages):
        self.calls.append(messages)

        if self.error is not None:
            raise self.error

        return self.response


class FakeChatModel:
    def __init__(
        self,
        response,
        *,
        error=None,
    ):
        self.runnable = FakeStructuredRunnable(
            response,
            error=error,
        )
        self.structured_calls = []

    def with_structured_output(
        self,
        schema,
        *,
        method,
        include_raw,
        **kwargs,
    ):
        self.structured_calls.append(
            {
                "schema": schema,
                "method": method,
                "include_raw": include_raw,
                "kwargs": kwargs,
            }
        )

        return self.runnable


def test_adapter_requests_schema_and_serializes_payload():
    fake = FakeChatModel(
        ExampleOutput(answer="ok")
    )

    model = DeepSeekStructuredResearchModel(
        chat_model=fake,
    )

    payload = {
        "z": 1,
        "company": "示例公司",
        "nested": {
            "b": 2,
            "a": 1,
        },
    }

    result = model.generate(
        system_prompt="System mandate",
        input_payload=payload,
        output_schema=ExampleOutput,
    )

    assert result == ExampleOutput(answer="ok")

    assert fake.structured_calls == [
        {
            "schema": ExampleOutput,
            "method": "function_calling",
            "include_raw": False,
            "kwargs": {},
        }
    ]

    assert len(fake.runnable.calls) == 1

    messages = fake.runnable.calls[0]

    assert messages[0] == (
        "system",
        "System mandate",
    )

    assert messages[1][0] == "human"
    assert json.loads(messages[1][1]) == payload

    assert messages[1][1] == (
        '{"company":"示例公司",'
        '"nested":{"a":1,"b":2},"z":1}'
    )


def test_adapter_allows_dict_structured_result():
    fake = FakeChatModel(
        {
            "answer": "ok",
        }
    )

    model = DeepSeekStructuredResearchModel(
        chat_model=fake,
    )

    result = model.generate(
        system_prompt="System",
        input_payload={"x": 1},
        output_schema=ExampleOutput,
    )

    assert result == {
        "answer": "ok",
    }


def test_adapter_rejects_unexpected_result_type():
    fake = FakeChatModel(
        "not structured"
    )

    model = DeepSeekStructuredResearchModel(
        chat_model=fake,
    )

    with pytest.raises(
        TypeError,
        match="Pydantic model or dict",
    ):
        model.generate(
            system_prompt="System",
            input_payload={"x": 1},
            output_schema=ExampleOutput,
        )


def test_provider_error_propagates_without_rewriting():
    error = RuntimeError(
        "provider unavailable"
    )

    fake = FakeChatModel(
        None,
        error=error,
    )

    model = DeepSeekStructuredResearchModel(
        chat_model=fake,
    )

    with pytest.raises(
        RuntimeError,
        match="provider unavailable",
    ):
        model.generate(
            system_prompt="System",
            input_payload={"x": 1},
            output_schema=ExampleOutput,
        )


def test_constructor_builds_chatdeepseek_without_api_key_argument(
    monkeypatch,
):
    captured = {}

    class FakeProvider:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(
        deepseek_module,
        "ChatDeepSeek",
        FakeProvider,
    )

    model = deepseek_module.DeepSeekStructuredResearchModel(
        model="deepseek-chat",
        temperature=0.0,
        max_retries=3,
        timeout=45.0,
    )

    assert model is not None

    assert captured == {
        "model": "deepseek-chat",
        "temperature": 0.0,
        "max_retries": 3,
        "timeout": 45.0,
    }

    assert "api_key" not in captured


def test_constructor_rejects_invalid_local_configuration():
    with pytest.raises(
        ValueError,
        match="model must be non-empty",
    ):
        DeepSeekStructuredResearchModel(
            model="   ",
            chat_model=FakeChatModel(
                ExampleOutput(answer="ok")
            ),
        )

    with pytest.raises(
        ValueError,
        match="max_retries",
    ):
        DeepSeekStructuredResearchModel(
            max_retries=-1,
            chat_model=FakeChatModel(
                ExampleOutput(answer="ok")
            ),
        )

    with pytest.raises(
        ValueError,
        match="timeout",
    ):
        DeepSeekStructuredResearchModel(
            timeout=0,
            chat_model=FakeChatModel(
                ExampleOutput(answer="ok")
            ),
        )
