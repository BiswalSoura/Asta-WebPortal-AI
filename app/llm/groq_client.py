import groq
from groq import AsyncGroq

from app.llm.exceptions import (
    EmptyLLMResponseError,
    LLMRequestError,
)
from app.llm.models import LLMResponse


class GroqLLMClient:
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        temperature: float,
        max_tokens: int,
        timeout_seconds: float,
        max_retries: int,
        client: AsyncGroq | None = None,
    ) -> None:
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

        self._client = (
            client
            or AsyncGroq(
                api_key=api_key,
                timeout=timeout_seconds,
                max_retries=max_retries,
            )
        )

    async def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> LLMResponse:
        try:
            completion = (
                await self._client
                .chat
                .completions
                .create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": system_prompt,
                        },
                        {
                            "role": "user",
                            "content": user_prompt,
                        },
                    ],
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    stream=False,
                )
            )

        except groq.APIConnectionError as exc:
            raise LLMRequestError(
                "Unable to connect to the Groq API."
            ) from exc

        except groq.APITimeoutError as exc:
            raise LLMRequestError(
                "The Groq API request timed out."
            ) from exc

        except groq.RateLimitError as exc:
            raise LLMRequestError(
                "The Groq API rate limit was reached."
            ) from exc

        except groq.APIStatusError as exc:
            raise LLMRequestError(
                (
                    "Groq API returned an error "
                    f"with status {exc.status_code}."
                )
            ) from exc

        except groq.APIError as exc:
            raise LLMRequestError(
                "Groq API request failed."
            ) from exc

        content = (
            completion
            .choices[0]
            .message
            .content
        )

        if content is None or not content.strip():
            raise EmptyLLMResponseError()

        usage = completion.usage

        return LLMResponse(
            content=content.strip(),
            model=completion.model,
            prompt_tokens=(
                usage.prompt_tokens
                if usage is not None
                else None
            ),
            completion_tokens=(
                usage.completion_tokens
                if usage is not None
                else None
            ),
            total_tokens=(
                usage.total_tokens
                if usage is not None
                else None
            ),
        )