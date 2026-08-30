from pathlib import Path

import pytest

from triage.rag.embed import EMBED_DIM, embed_texts
from triage.tools.runbook import RunbookHit, retrieve_runbook


def test_embed_shape_and_normalisation():
    [vec] = embed_texts(["connection pool exhausted"])
    assert len(vec) == EMBED_DIM
    norm = sum(x * x for x in vec) ** 0.5
    assert norm == pytest.approx(1.0, abs=1e-3)


def test_open_missing_index_raises(tmp_path):
    with pytest.raises(FileNotFoundError, match="build_runbook_index"):
        retrieve_runbook("anything", index_dir=tmp_path / "does-not-exist")


def test_empty_query_rejected(runbook_index):
    with pytest.raises(ValueError, match="empty"):
        retrieve_runbook("   ", index_dir=runbook_index)


@pytest.mark.parametrize(
    ("query", "expected_source"),
    [
        (
            "DB connection pool exhausted, many waiters, slow downstream",
            "connection-pool-exhaustion.md",
        ),
        (
            "TLS certificate expired, authentication failures across services",
            "certificate-and-config-expiry.md",
        ),
        (
            "storage index dropped below quorum, cluster in recovery",
            "quorum-loss-distributed-system.md",
        ),
        (
            "mild intermittent errors, no deploy, downstream healthy, flat resources",
            "when-to-escalate-inconclusive-evidence.md",
        ),
    ],
)
def test_retrieval_finds_the_right_runbook(runbook_index: Path, query: str, expected_source: str):
    hits = retrieve_runbook(query, k=3, index_dir=runbook_index)

    assert len(hits) == 3
    assert all(isinstance(h, RunbookHit) for h in hits)
    assert hits[0].source == expected_source, [h.citation() for h in hits]
    assert hits[0].score >= hits[1].score >= hits[2].score
    assert hits[0].citation() == f"{expected_source} > {hits[0].section_title}"
