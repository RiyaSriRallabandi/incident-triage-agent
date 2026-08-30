from triage.config import Settings


def test_settings_load_from_env(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")
    monkeypatch.setenv("LANGCHAIN_TRACING_V2", "true")

    settings = Settings(_env_file=None)

    assert settings.groq_api_key == "test-groq-key"
    assert settings.langchain_tracing_v2 is True
    assert settings.langchain_project == "incident-triage-agent"


def test_settings_defaults_when_unset(monkeypatch):
    for key in ("GROQ_API_KEY", "GEMINI_API_KEY", "LANGCHAIN_API_KEY", "LANGCHAIN_TRACING_V2"):
        monkeypatch.delenv(key, raising=False)

    settings = Settings(_env_file=None)

    assert settings.groq_api_key == ""
    assert settings.gemini_api_key == ""
    assert settings.langchain_tracing_v2 is False
