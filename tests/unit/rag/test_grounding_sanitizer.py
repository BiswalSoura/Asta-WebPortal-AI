from app.rag.grounding_sanitizer import (
    GroundingSanitizer,
)


def test_removes_unsupported_acronym_expansion() -> None:
    sanitizer = GroundingSanitizer()

    result = sanitizer.sanitize(
        answer=(
            "Select APN "
            "(Assessor's Parcel Number) "
            "for the location."
        ),
        context=(
            "The APN / Parcel Number option "
            "can be used as a project "
            "location method."
        ),
    )

    assert result == (
        "Select APN for the location."
    )


def test_preserves_supported_acronym_expansion() -> None:
    sanitizer = GroundingSanitizer()

    result = sanitizer.sanitize(
        answer=(
            "Select APN "
            "(Assessor's Parcel Number) "
            "for the location."
        ),
        context=(
            "APN stands for "
            "Assessor's Parcel Number."
        ),
    )

    assert result == (
        "Select APN "
        "(Assessor's Parcel Number) "
        "for the location."
    )