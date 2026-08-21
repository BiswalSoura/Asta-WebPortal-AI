SUPPORTED_DOCUMENT_EXTENSIONS = frozenset(
    {
        ".docx",
        ".pdf",
        ".txt",
        ".md",
    }
)

MAX_DOCUMENT_SIZE_BYTES = 20 * 1024 * 1024

DEFAULT_CHUNK_SIZE_CHARS = 2000
DEFAULT_CHUNK_OVERLAP_CHARS = 200