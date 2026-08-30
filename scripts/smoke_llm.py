"""Manual check that the configured LLM providers respond.

Usage:
    uv run python scripts/smoke_llm.py            # all providers with keys set
    uv run python scripts/smoke_llm.py groq       # one provider

Requires real API keys in .env. Not run in CI.
"""

from __future__ import annotations

import sys

from triage.config import get_settings
from triage.llm import Provider, get_chat_model

PROMPT = "In one short sentence, say what an on-call engineer does."


def check(provider: Provider) -> bool:
    print(f"\n=== {provider} ===")
    try:
        model = get_chat_model(provider)
        reply = model.invoke(PROMPT)
    except Exception as exc:  # noqa: BLE001 - surface any failure to the operator
        print(f"FAILED: {exc}")
        return False
    print(f"model: {getattr(model, 'model_name', '?')}")
    print(f"reply: {reply.text.strip()}")
    return True


def main() -> int:
    settings = get_settings()
    keyed = (("groq", settings.groq_api_key), ("gemini", settings.gemini_api_key))
    requested = sys.argv[1:] or [p for p, key in keyed if key]
    if not requested:
        print("No API keys configured. Add GROQ_API_KEY and/or GEMINI_API_KEY to .env.")
        return 1

    results = {p: check(p) for p in requested}  # type: ignore[arg-type]
    print("\n" + ", ".join(f"{p}: {'ok' if ok else 'FAIL'}" for p, ok in results.items()))
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
