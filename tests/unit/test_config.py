from app.core.config import get_settings


def test_default_application_name() -> None:
    settings = get_settings()

    assert settings.app_name == "Asta"


def test_default_api_prefix() -> None:
    settings = get_settings()

    assert settings.api_v1_prefix == "/api/v1"