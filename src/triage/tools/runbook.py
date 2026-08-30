"""The ``retrieve_runbook`` tool: semantic search over the runbook corpus.

One of the agent's evidence tools. Given a free-text query it returns the most
relevant runbook sections, each with its source so the agent can cite it.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

from triage.rag.embed import embed_query
from triage.rag.index import INDEX_DIR, open_collection

DEFAULT_K = 5


class RunbookHit(BaseModel):
    source: str  # runbook file name
    doc_title: str
    section_title: str
    text: str
    score: float  # cosine similarity in roughly [0, 1]; higher is closer

    def citation(self) -> str:
        return f"{self.source} > {self.section_title}"


def retrieve_runbook(
    query: str,
    k: int = DEFAULT_K,
    *,
    index_dir: Path = INDEX_DIR,
) -> list[RunbookHit]:
    """Return the top-``k`` runbook sections most relevant to ``query``."""
    if not query.strip():
        raise ValueError("query must not be empty")

    collection = open_collection(index_dir)
    result = collection.query(
        query_embeddings=[embed_query(query)],
        n_results=k,
    )

    docs = result["documents"][0]
    metas = result["metadatas"][0]
    distances = result["distances"][0]

    return [
        RunbookHit(
            source=str(meta["source"]),
            doc_title=str(meta["doc_title"]),
            section_title=str(meta["section_title"]),
            text=doc,
            score=round(1.0 - dist, 4),
        )
        for doc, meta, dist in zip(docs, metas, distances, strict=True)
    ]
