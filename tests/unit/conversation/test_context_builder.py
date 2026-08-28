from app.conversation import (
    ConversationContextBuilder,
    ConversationHistoryMessage,
)


def _history():
    return [
        ConversationHistoryMessage(
            role="user",
            content=(
                "Where can I enter parcel "
                "information?"
            ),
        ),
        ConversationHistoryMessage(
            role="assistant",
            content=(
                "Use the APN / Parcel Number "
                "location option."
            ),
        ),
    ]


def test_explicit_webportal_question_is_not_rewritten() -> None:
    builder = ConversationContextBuilder(
        max_chars=4000
    )

    query, contextualized = (
        builder.build_query(
            current_message=(
                "How does Create New Project work?"
            ),
            history=_history(),
        )
    )

    assert query == (
        "How does Create New Project work?"
    )

    assert contextualized is False


def test_follow_up_uses_recent_history() -> None:
    builder = ConversationContextBuilder(
        max_chars=4000
    )

    query, contextualized = (
        builder.build_query(
            current_message=(
                "Can you explain that option?"
            ),
            history=_history(),
        )
    )

    assert contextualized is True

    assert (
        "APN / Parcel Number"
        in query
    )

    assert (
        "Can you explain that option?"
        in query
    )


def test_greeting_is_not_contextualized() -> None:
    builder = ConversationContextBuilder(
        max_chars=4000
    )

    query, contextualized = (
        builder.build_query(
            current_message="Hello",
            history=_history(),
        )
    )

    assert query == "Hello"
    assert contextualized is False