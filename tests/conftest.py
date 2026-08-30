from pathlib import Path

import pytest

from triage.rag.index import build_index


@pytest.fixture(scope="session")
def runbook_index(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Build the real runbook index once per test session, in a temp dir.

    Downloads the embedding model on first run (cached afterwards).
    """
    index_dir = tmp_path_factory.mktemp("runbook_index")
    count = build_index(index_dir=index_dir)
    assert count > 0
    return index_dir
