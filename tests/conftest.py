import os
from pathlib import Path

import pytest

from triage.rag.index import build_index

_TRACING_KEYS = (
    "LANGCHAIN_TRACING_V2",
    "LANGSMITH_TRACING",
    "LANGCHAIN_API_KEY",
    "LANGSMITH_API_KEY",
    "LANGCHAIN_PROJECT",
    "LANGSMITH_PROJECT",
)


@pytest.fixture(autouse=True)
def _isolate_tracing_env():
    """Keep every test offline from LangSmith and restore the environment after."""
    saved = {k: os.environ.pop(k, None) for k in _TRACING_KEYS}
    os.environ["LANGCHAIN_TRACING_V2"] = "false"
    try:
        yield
    finally:
        for k in _TRACING_KEYS:
            os.environ.pop(k, None)
        for k, v in saved.items():
            if v is not None:
                os.environ[k] = v


@pytest.fixture(scope="session")
def runbook_index(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Build the real runbook index once per test session, in a temp dir.

    Downloads the embedding model on first run (cached afterwards).
    """
    index_dir = tmp_path_factory.mktemp("runbook_index")
    count = build_index(index_dir=index_dir)
    assert count > 0
    return index_dir
