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

def test_greeting_exchange_does_not_change_knowledge_follow_up_query():
    builder = ConversationContextBuilder(max_chars=4000)
    topic = [
        ConversationHistoryMessage(role="user", content="Where can I enter parcel information?"),
        ConversationHistoryMessage(role="assistant", content="Use the APN / Parcel Number option."),
    ]
    greeting = [
        ConversationHistoryMessage(role="user", content="Hello"),
        ConversationHistoryMessage(role="assistant", content="Hi, I'm Asta. I can help with WebPortal."),
    ]
    current = "Can you explain that option?"
    expected = builder.build_query(current_message=current, history=topic)
    actual = builder.build_query(current_message=current, history=greeting + topic)
    assert actual == expected


def test_greeting_only_history_does_not_supply_a_follow_up_topic():
    builder = ConversationContextBuilder(max_chars=4000)
    history = [
        ConversationHistoryMessage(role="user", content="Hello"),
        ConversationHistoryMessage(role="assistant", content="Hi, I'm Asta. I can help with WebPortal."),
    ]
    question = "Can you explain that option?"
    assert builder.build_query(current_message=question, history=history) == (question, False)
