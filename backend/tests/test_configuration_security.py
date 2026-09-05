from pathlib import Path

import pytest

from app.config import get_settings
from app.providers.groq_provider import GroqProvider


def test_settings_load_and_environment_override(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-only-key")
    monkeypatch.setenv("GROQ_MODEL", "test-model")

    settings = get_settings()

    assert settings.groq_api_key == "test-only-key"
    assert settings.groq_model == "test-model"


def test_missing_provider_configuration_is_safe(monkeypatch):
    # Explicitly override the local dotenv file for this negative-path test.
    monkeypatch.setenv("GROQ_API_KEY", "")

    with pytest.raises(ValueError, match="AI provider is not configured") as error:
        GroqProvider()

    assert "GROQ_API_KEY" not in str(error.value)


def test_template_contains_no_credential():
    template = Path(__file__).parents[1] / ".env.example"
    contents = template.read_text(encoding="utf-8")

    assert "GROQ_API_KEY=" in contents
    assert "gsk_" not in contents
    assert "your_groq_api_key" not in contents
