from app.core.exceptions import AstaError


class KnowledgeError(AstaError):
    """Base exception for Asta knowledge processing."""


class UnsupportedDocumentTypeError(KnowledgeError):
    def __init__(self, extension: str) -> None:
        super().__init__(
            f"Unsupported document type: {extension}",
            error_code="UNSUPPORTED_DOCUMENT_TYPE",
        )


class DocumentNotFoundError(KnowledgeError):
    def __init__(self, path: str) -> None:
        super().__init__(
            f"Document not found: {path}",
            error_code="DOCUMENT_NOT_FOUND",
        )


class DocumentTooLargeError(KnowledgeError):
    def __init__(self, max_size_bytes: int) -> None:
        super().__init__(
            (
                "Document exceeds the maximum supported size "
                f"of {max_size_bytes} bytes."
            ),
            error_code="DOCUMENT_TOO_LARGE",
        )


class EmptyDocumentError(KnowledgeError):
    def __init__(self) -> None:
        super().__init__(
            "Document contains no usable text.",
            error_code="EMPTY_DOCUMENT",
        )


class DocumentLoadError(KnowledgeError):
    def __init__(self, message: str) -> None:
        super().__init__(
            message,
            error_code="DOCUMENT_LOAD_ERROR",
        )