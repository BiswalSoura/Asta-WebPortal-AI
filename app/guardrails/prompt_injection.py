import re
import unicodedata
from difflib import get_close_matches


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
    re.compile(r"\b(?:reveal|show|display|print)\b.*\b(?:source code|internal configuration)\b", re.I),
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
        text = unicodedata.normalize("NFKC", message).casefold()
        text = "".join(c for c in text if unicodedata.category(c) != "Cf")
        text = text.translate(str.maketrans({"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "@": "a", "$": "s"}))
        vocabulary = ("ignore", "forget", "override", "instruction", "instructions",
                      "reveal", "show", "display", "print", "system", "prompt",
                      "source", "code", "internal", "configuration", "hidden", "developer")
        explicit = {"ignroe": "ignore", "revele": "reveal", "reveel": "reveal", "cod": "code",
                    "instructons": "instructions", "instrctions": "instructions"}

        def correct(match):
            token = match.group()
            if token in explicit:
                return explicit[token]
            if token in vocabulary or len(token) < 4:
                return token
            candidates = get_close_matches(token, vocabulary, n=2, cutoff=0.82)
            return candidates[0] if len(candidates) == 1 else token

        safe = re.sub(r"\b[a-z]+\b", correct, text)
        return any(pattern.search(candidate) is not None
                   for candidate in (message, safe) for pattern in INJECTION_PATTERNS)
