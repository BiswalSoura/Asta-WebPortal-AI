class AstaError(Exception):
    """Base exception for application-level Asta errors."""


class ConfigurationError(AstaError):
    """Raised when required application configuration is invalid."""