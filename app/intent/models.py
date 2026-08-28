from enum import StrEnum


class IntentType(StrEnum):
    GREETING = "greeting"
    WEBPORTAL = "webportal"
    OFF_TOPIC = "off_topic"
    UNKNOWN = "unknown"
    PROMPT_INJECTION = "prompt_injection"