from app.intent import (
    IntentClassifier,
    IntentType,
)


def test_classifier_detects_greeting() -> None:
    classifier = IntentClassifier()

    assert (
        classifier.classify("Hello")
        == IntentType.GREETING
    )


def test_classifier_detects_webportal_question() -> None:
    classifier = IntentClassifier()

    assert (
        classifier.classify(
            "How does Create New Project work?"
        )
        == IntentType.WEBPORTAL
    )


def test_classifier_detects_obvious_off_topic() -> None:
    classifier = IntentClassifier()

    assert (
        classifier.classify(
            "Tell me a joke."
        )
        == IntentType.OFF_TOPIC
    )


def test_classifier_leaves_unknown_for_rag() -> None:
    classifier = IntentClassifier()

    assert (
        classifier.classify(
            "Can you explain this option?"
        )
        == IntentType.UNKNOWN
    )