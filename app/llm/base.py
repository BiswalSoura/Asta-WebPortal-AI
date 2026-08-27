from typing import Protocol

from app.llm.models import LLMResponse


class LLMClient(Protocol):
    async def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> LLMResponse:
        ...