from app.rag.prompt_builder import (
    RAGPromptBuilder,
)


def test_prompt_builder_enforces_grounding() -> None:
    builder = RAGPromptBuilder()

    prompt = builder.build(
        question="How do I create a project?",
        context=(
            "The Create New Project page allows "
            "a user to begin a new project."
        ),
    )

    assert (
        "Do not infer missing WebPortal details."
        in prompt
    )

    assert (
        "Do not invent fields, buttons, links"
        in prompt
    )

    assert (
        "Create New Project"
        in prompt
    )