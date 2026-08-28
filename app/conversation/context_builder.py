import re

from app.guardrails import (
    PromptInjectionDetector,
)
from app.intent import (
    IntentClassifier,
    IntentType,
)
from app.conversation.models import (
    ConversationHistoryMessage,
)


FOLLOW_UP_PATTERNS = (
    re.compile(
        r"\bwhat about\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bhow about\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\btell me more\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bwhat next\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bwhat happens next\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bthis option\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bthat option\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bexplain this\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bexplain that\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bhow does it\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bdoes it\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bwhere is it\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bhow do i do that\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bwhat does that\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bsame page\b",
        re.IGNORECASE,
    ),
)


class ConversationContextBuilder:
    def __init__(
        self,
        *,
        max_chars: int,
        intent_classifier: (
            IntentClassifier | None
        ) = None,
        injection_detector: (
            PromptInjectionDetector | None
        ) = None,
    ) -> None:
        self.max_chars = max_chars

        self.intent_classifier = (
            intent_classifier
            or IntentClassifier()
        )

        self.injection_detector = (
            injection_detector
            or PromptInjectionDetector()
        )

    def build_query(
        self,
        *,
        current_message: str,
        history: list[
            ConversationHistoryMessage
        ],
    ) -> tuple[str, bool]:
        current = current_message.strip()

        if not history:
            return current, False

        if (
            self.injection_detector
            .is_injection(current)
        ):
            return current, False

        intent = (
            self.intent_classifier
            .classify(current)
        )

        if intent != IntentType.UNKNOWN:
            return current, False

        if not self._is_follow_up(current):
            return current, False

        history_text = self._format_history(
            history
        )

        contextual_query = (
            "RECENT CONVERSATION CONTEXT:\n"
            f"{history_text}\n\n"
            "CURRENT USER QUESTION:\n"
            f"{current}"
        )

        return contextual_query, True

    def _is_follow_up(
        self,
        message: str,
    ) -> bool:
        return any(
            pattern.search(message)
            is not None
            for pattern in FOLLOW_UP_PATTERNS
        )

    def _format_history(
        self,
        history: list[
            ConversationHistoryMessage
        ],
    ) -> str:
        lines = [
            (
                f"{message.role.upper()}: "
                f"{message.content}"
            )
            for message in history
        ]

        text = "\n".join(lines)

        if len(text) <= self.max_chars:
            return text

        return text[-self.max_chars:]