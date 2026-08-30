import pytest

from triage.config import Settings
from triage.llm import DEFAULT_MODELS, GROQ_LARGE_MODEL, get_chat_model, get_judge_model


def _settings(**overrides) -> Settings:
    base = {"groq_api_key": "", "gemini_api_key": ""}
    base.update(overrides)
    return Settings(_env_file=None, **base)


def test_groq_model_built_with_defaults():
    model = get_chat_model("groq", settings=_settings(groq_api_key="k"))
    assert model.__class__.__name__ == "ChatGroq"
    assert model.model_name == DEFAULT_MODELS["groq"]


def test_gemini_model_built_with_defaults():
    model = get_chat_model("gemini", settings=_settings(gemini_api_key="k"))
    assert model.__class__.__name__ == "ChatGoogleGenerativeAI"


def test_explicit_model_and_temperature_passed_through():
    model = get_chat_model(
        "groq", model="openai/gpt-oss-120b", temperature=0.5, settings=_settings(groq_api_key="k")
    )
    assert model.model_name == "openai/gpt-oss-120b"
    assert model.temperature == 0.5


def test_judge_uses_large_groq_model():
    model = get_judge_model(settings=_settings(groq_api_key="k"))
    assert model.model_name == GROQ_LARGE_MODEL


def test_missing_api_key_raises():
    with pytest.raises(ValueError, match="GROQ_API_KEY"):
        get_chat_model("groq", settings=_settings())
    with pytest.raises(ValueError, match="GEMINI_API_KEY"):
        get_chat_model("gemini", settings=_settings())


def test_unknown_provider_raises():
    with pytest.raises(ValueError, match="Unknown provider"):
        get_chat_model("anthropic", settings=_settings())  # type: ignore[arg-type]


# --- Live smoke tests: run only when real keys are present in the environment ---

_live = Settings()


@pytest.mark.skipif(not _live.groq_api_key, reason="GROQ_API_KEY not set")
def test_groq_live_roundtrip():
    model = get_chat_model("groq")
    reply = model.invoke("Reply with the single word: pong")
    assert "pong" in reply.text.lower()


@pytest.mark.skipif(not _live.gemini_api_key, reason="GEMINI_API_KEY not set")
def test_gemini_live_roundtrip():
    model = get_chat_model("gemini")
    reply = model.invoke("Reply with the single word: pong")
    assert "pong" in reply.text.lower()
