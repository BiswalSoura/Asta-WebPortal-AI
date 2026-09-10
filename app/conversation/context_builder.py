import re
from app.intent.query_understanding import DOMAIN, FOLLOW_UP, normalize_language

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

        current = normalize_language(current).query

        intent = (
            self.intent_classifier
            .classify(current)
        )

        if intent != IntentType.UNKNOWN:
            return current, False

        if DOMAIN.search(current):
            return current, False

        if not self._is_follow_up(current):
            return current, False

        # Greetings provide no knowledge topic and can dilute retrieval/reranking.
        # Keep stored history intact; omit only greeting exchanges from this query.
        relevant_history = []
        greeting_turn = False
        for message in history:
            if message.role == "user":
                greeting_turn = (
                    self.intent_classifier.classify(message.content)
                    == IntentType.GREETING
                )
            if not greeting_turn:
                relevant_history.append(message)

        if not relevant_history:
            return current, False

        # Only a recent explicit domain topic supplies a referent. Discard earlier topics.
        topic_start = None
        for index, message in enumerate(relevant_history):
            if message.role == "user" and not self._is_follow_up(normalize_language(message.content).query):
                if (DOMAIN.search(normalize_language(message.content).query)
                        and not self.injection_detector.is_injection(message.content)):
                    topic_start = index
                else:
                    topic_start = None
        if topic_start is None:
            return current, False
        relevant_history = relevant_history[topic_start:]

        # Do not guess between independent location options or borrow a refused topic.
        topic = normalize_language(relevant_history[0].content).query
        if (re.search(r"\b(?:apn|parcel)\b", topic, re.I)
                and re.search(r"\bbuilding address\b", topic, re.I)):
            return current, False
        from app.guardrails.service import OFF_TOPIC_RESPONSE, PROMPT_INJECTION_RESPONSE
        from app.intent.query_understanding import CLARIFICATION_RESPONSE
        from app.rag.rag_service import INSUFFICIENT_KNOWLEDGE_RESPONSE
        if relevant_history[-1].role == "assistant" and relevant_history[-1].content in {
            OFF_TOPIC_RESPONSE, PROMPT_INJECTION_RESPONSE, CLARIFICATION_RESPONSE,
            INSUFFICIENT_KNOWLEDGE_RESPONSE,
        }:
            return current, False

        history_text = self._format_history(
            relevant_history
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
        return bool(FOLLOW_UP.fullmatch(message)) or any(
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
                f"{normalize_language(message.content).query if message.role == 'user' else message.content}"
            )
            for message in history
        ]

        text = "\n".join(lines)

        if len(text) <= self.max_chars:
            return text

        return text[-self.max_chars:]
