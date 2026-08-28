from app.guardrails.models import (
    GuardrailDecision,
)
from app.guardrails.prompt_injection import (
    PromptInjectionDetector,
)
from app.intent import (
    IntentClassifier,
    IntentType,
)


GREETING_RESPONSE = (
    "Hi, I'm Asta. I can help you with "
    "A&A Engineering WebPortal features and usage. "
    "What would you like help with?"
)


OFF_TOPIC_RESPONSE = (
    "I can help with questions about the "
    "A&A Engineering WebPortal and its features. "
    "What would you like to know about WebPortal?"
)


PROMPT_INJECTION_RESPONSE = (
    "I can help with WebPortal features and usage, "
    "but I can't provide or change my internal "
    "instructions. What would you like help with "
    "in WebPortal?"
)


EMPTY_MESSAGE_RESPONSE = (
    "Please ask me a question about the "
    "A&A Engineering WebPortal."
)


class GuardrailService:
    def __init__(
        self,
        *,
        intent_classifier: (
            IntentClassifier | None
        ) = None,
        injection_detector: (
            PromptInjectionDetector | None
        ) = None,
    ) -> None:
        self.intent_classifier = (
            intent_classifier
            or IntentClassifier()
        )

        self.injection_detector = (
            injection_detector
            or PromptInjectionDetector()
        )

    def evaluate(
        self,
        message: str,
    ) -> GuardrailDecision:
        normalized = message.strip()

        if not normalized:
            return GuardrailDecision(
                intent=IntentType.UNKNOWN,
                allowed=False,
                response=EMPTY_MESSAGE_RESPONSE,
            )

        if (
            self.injection_detector
            .is_injection(normalized)
        ):
            return GuardrailDecision(
                intent=(
                    IntentType.PROMPT_INJECTION
                ),
                allowed=False,
                response=(
                    PROMPT_INJECTION_RESPONSE
                ),
            )

        intent = (
            self.intent_classifier
            .classify(normalized)
        )

        if intent == IntentType.GREETING:
            return GuardrailDecision(
                intent=intent,
                allowed=False,
                response=GREETING_RESPONSE,
            )

        if intent == IntentType.OFF_TOPIC:
            return GuardrailDecision(
                intent=intent,
                allowed=False,
                response=OFF_TOPIC_RESPONSE,
            )

        return GuardrailDecision(
            intent=intent,
            allowed=True,
        )