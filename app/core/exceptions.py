class AstaError(Exception):
    """Base exception for application-level Asta errors."""

    def __init__(
        self,
        message: str,
        *,
        error_code: str = "ASTA_ERROR",
    ) -> None:
        super().__init__(message)

        self.message = message
        self.error_code = error_code


class ConfigurationError(AstaError):
    """Raised when required application configuration is invalid."""

    def __init__(self, message: str) -> None:
        super().__init__(
            message,
            error_code="CONFIGURATION_ERROR",
        )