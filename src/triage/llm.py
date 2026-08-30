"""Chat-model access layer.

One factory, ``get_chat_model``, returns a configured LangChain chat model for a
given provider. The rest of the project depends only on the LangChain
``BaseChatModel`` interface, so providers stay swappable for later ablations.

Providers (all free tier):
- ``groq``   - Groq API, OpenAI-compatible OSS models. Primary provider.
- ``gemini`` - Google AI Studio (Gemini API). Second provider, used for ablations.
"""

from __future__ import annotations

from typing import Literal

from langchain_core.language_models import BaseChatModel

from triage.config import Settings, get_settings

Provider = Literal["groq", "gemini"]

# Working defaults. Small model for the agent loop; large model reserved for the
# LLM-judge and ablation comparisons.
DEFAULT_MODELS: dict[Provider, str] = {
    "groq": "openai/gpt-oss-20b",
    "gemini": "gemini-3.6-flash",
}

GROQ_LARGE_MODEL = "openai/gpt-oss-120b"

# Retries applied by the provider client on transient errors / rate limits.
DEFAULT_MAX_RETRIES = 3


def get_chat_model(
    provider: Provider = "groq",
    *,
    model: str | None = None,
    temperature: float = 0.0,
    max_retries: int = DEFAULT_MAX_RETRIES,
    settings: Settings | None = None,
    **kwargs: object,
) -> BaseChatModel:
    """Return a configured chat model.

    Args:
        provider: ``"groq"`` or ``"gemini"``.
        model: Model id. Defaults to ``DEFAULT_MODELS[provider]``.
        temperature: Sampling temperature; ``0.0`` for deterministic agent steps.
        max_retries: Client-side retries on transient failures.
        settings: Override settings (mainly for tests). Defaults to ``get_settings()``.
        **kwargs: Passed through to the underlying LangChain chat model.

    Raises:
        ValueError: Unknown provider, or the provider's API key is not configured.
    """
    settings = settings or get_settings()
    model = model or DEFAULT_MODELS.get(provider)
    if model is None:
        raise ValueError(f"Unknown provider: {provider!r}")

    if provider == "groq":
        if not settings.groq_api_key:
            raise ValueError("GROQ_API_KEY is not set (see .env.example).")
        from langchain_groq import ChatGroq

        return ChatGroq(
            model=model,
            api_key=settings.groq_api_key,
            temperature=temperature,
            max_retries=max_retries,
            **kwargs,
        )

    if provider == "gemini":
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is not set (see .env.example).")
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=model,
            google_api_key=settings.gemini_api_key,
            temperature=temperature,
            max_retries=max_retries,
            **kwargs,
        )

    raise ValueError(f"Unknown provider: {provider!r}")


def get_judge_model(settings: Settings | None = None) -> BaseChatModel:
    """Return the larger Groq model used for LLM-as-judge scoring."""
    return get_chat_model("groq", model=GROQ_LARGE_MODEL, temperature=0.0, settings=settings)
