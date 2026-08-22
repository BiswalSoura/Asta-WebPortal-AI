from app.knowledge.processors import (
    normalize_text,
)


def test_normalize_text_collapses_spaces() -> None:
    result = normalize_text(
        "Hello     WebPortal"
    )

    assert result == "Hello WebPortal"


def test_normalize_text_normalizes_line_endings() -> None:
    result = normalize_text(
        "Line 1\r\nLine 2\rLine 3"
    )

    assert result == (
        "Line 1\nLine 2\nLine 3"
    )


def test_normalize_text_reduces_blank_lines() -> None:
    result = normalize_text(
        "Section 1\n\n\n\nSection 2"
    )

    assert result == (
        "Section 1\n\nSection 2"
    )