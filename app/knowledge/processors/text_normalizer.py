import re
import unicodedata


MULTIPLE_SPACES = re.compile(
    r"[ \t]+"
)

EXCESS_BLANK_LINES = re.compile(
    r"\n{3,}"
)


def normalize_text(
    text: str,
) -> str:
    normalized = unicodedata.normalize(
        "NFKC",
        text,
    )

    normalized = normalized.replace(
        "\r\n",
        "\n",
    ).replace(
        "\r",
        "\n",
    )

    lines = [
        MULTIPLE_SPACES.sub(
            " ",
            line,
        ).strip()
        for line in normalized.splitlines()
    ]

    normalized = "\n".join(lines)

    normalized = EXCESS_BLANK_LINES.sub(
        "\n\n",
        normalized,
    )

    return normalized.strip()