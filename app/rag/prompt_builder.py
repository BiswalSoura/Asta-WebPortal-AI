class RAGPromptBuilder:
    def build(
        self,
        *,
        question: str,
        context: str,
    ) -> str:
        return (
            "USER QUESTION:\n"
            f"{question.strip()}\n\n"
            "APPROVED WEBPORTAL CONTEXT:\n"
            f"{context}\n\n"
            "ANSWER REQUIREMENTS:\n"
            "- Answer only from the approved context above.\n"
            "- Do not infer missing WebPortal details.\n"
            "- Do not invent fields, buttons, links, page locations, "
            "navigation steps, validation rules, or workflow behavior.\n"
            "- Do not complete partial procedures using general software "
            "knowledge.\n"
            "- If the context supports only part of the answer, explain "
            "only that part.\n"
            "- If the context is insufficient, clearly say so.\n"
            "- Keep the answer concise and natural."
        )