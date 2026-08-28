import re

from app.intent.models import IntentType


GREETING_MESSAGES = {
    "hi",
    "hello",
    "hey",
    "good morning",
    "good afternoon",
    "good evening",
}


WEBPORTAL_PATTERNS = (
    re.compile(
        r"\bwebportal\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bcreate new project\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bproject list\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bapn\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bparcel\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bbuilding address\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bproject owner title\b",
        re.IGNORECASE,
    ),
)


OFF_TOPIC_PATTERNS = (
    re.compile(
        r"\b(weather|forecast|temperature)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(recipe|cooking|cook)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(joke|poem|story)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(cricket|football|soccer|basketball|tennis)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(stock price|share price|bitcoin price|crypto price)\b",
        re.IGNORECASE,
    ),
    re.compile(
        (
            r"\b(write|generate|debug|fix)\b.*"
            r"\b(python|javascript|java|c\+\+|code)\b"
        ),
        re.IGNORECASE,
    ),
    re.compile(
        r"\bcapital of\b",
        re.IGNORECASE,
    ),
)


class IntentClassifier:
    def classify(
        self,
        message: str,
    ) -> IntentType:
        normalized = message.strip()

        if not normalized:
            return IntentType.UNKNOWN

        if (
            normalized.lower()
            in GREETING_MESSAGES
        ):
            return IntentType.GREETING

        for pattern in OFF_TOPIC_PATTERNS:
            if pattern.search(normalized):
                return IntentType.OFF_TOPIC

        for pattern in WEBPORTAL_PATTERNS:
            if pattern.search(normalized):
                return IntentType.WEBPORTAL

        return IntentType.UNKNOWN