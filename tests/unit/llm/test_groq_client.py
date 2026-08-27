import pytest

from app.llm.groq_client import (
    GroqLLMClient,
)


class FakeUsage:
    prompt_tokens = 10
    completion_tokens = 5
    total_tokens = 15


class FakeMessage:
    content = "Use the Create New Project page."


class FakeChoice:
    message = FakeMessage()


class FakeCompletion:
    choices = [
        FakeChoice()
    ]

    model = "fake-groq-model"

    usage = FakeUsage()


class FakeCompletions:
    async def create(
        self,
        **kwargs,
    ):
        assert kwargs["model"] == (
            "fake-groq-model"
        )

        return FakeCompletion()


class FakeChat:
    completions = FakeCompletions()


class FakeGroqClient:
    chat = FakeChat()


@pytest.mark.asyncio
async def test_groq_client_returns_llm_response() -> None:
    client = GroqLLMClient(
        api_key="fake-key",
        model="fake-groq-model",
        temperature=0.2,
        max_tokens=600,
        timeout_seconds=30,
        max_retries=2,
        client=FakeGroqClient(),
    )

    result = await client.generate(
        system_prompt="System",
        user_prompt="Question",
    )

    assert result.content == (
        "Use the Create New Project page."
    )

    assert result.model == (
        "fake-groq-model"
    )

    assert result.total_tokens == 15