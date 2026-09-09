import re


_ACRONYM_EXPANSION_PATTERN = re.compile(
    r"\b([A-Z][A-Z0-9]{1,9})\s*"
    r"\(([^()\n]{2,120})\)"
)


class GroundingSanitizer:
    def sanitize(
        self,
        *,
        answer: str,
        context: str,
    ) -> str:
        return _ACRONYM_EXPANSION_PATTERN.sub(
            lambda match: (
                match.group(0)
                if self._context_defines_expansion(
                    acronym=match.group(1),
                    expansion=match.group(2),
                    context=context,
                )
                else match.group(1)
            ),
            answer,
        )

    def _context_defines_expansion(
        self,
        *,
        acronym: str,
        expansion: str,
        context: str,
    ) -> bool:
        normalized_context = self._normalize(
            context
        )

        normalized_acronym = self._normalize(
            acronym
        )

        normalized_expansion = self._normalize(
            expansion
        )

        supported_forms = (
            (
                f"{normalized_acronym} "
                f"({normalized_expansion})"
            ),
            (
                f"{normalized_expansion} "
                f"({normalized_acronym})"
            ),
            (
                f"{normalized_acronym} "
                f"stands for "
                f"{normalized_expansion}"
            ),
            (
                f"{normalized_acronym} "
                f"means "
                f"{normalized_expansion}"
            ),
        )

        return any(
            form in normalized_context
            for form in supported_forms
        )

    @staticmethod
    def _normalize(
        value: str,
    ) -> str:
        return " ".join(
            value.casefold().split()
        )