import re


INJECTION_PATTERNS = (
    re.compile(
        (
            r"\b(ignore|forget|override)\b.*"
            r"\b(instruction|instructions|prompt|rules)\b"
        ),
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(system prompt|developer message|hidden instructions)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(jailbreak|prompt injection)\b",
        re.IGNORECASE,
    ),
    re.compile(
        (
            r"\b(reveal|show|display|print)\b.*"
            r"\b(prompt|instructions|system message)\b"
        ),
        re.IGNORECASE,
    ),
)


class PromptInjectionDetector:
    def is_injection(
        self,
        message: str,
    ) -> bool:
        return any(
            pattern.search(message)
            is not None
            for pattern in INJECTION_PATTERNS
        )