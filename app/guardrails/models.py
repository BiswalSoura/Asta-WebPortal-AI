from dataclasses import dataclass

from app.intent import IntentType


@dataclass(frozen=True)
class GuardrailDecision:
    intent: IntentType
    allowed: bool
    response: str | None = None