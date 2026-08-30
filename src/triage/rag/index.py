"""Build and open the Chroma vector index over the runbook corpus.

We compute embeddings ourselves (via ``triage.rag.embed``) and hand the vectors
to Chroma directly, rather than registering a Chroma embedding function, so the
exact same model is used for indexing and for queries.
"""

from __future__ import annotations

import contextlib
from pathlib import Path

import chromadb

from triage.dataset import REPO_ROOT
from triage.rag.chunk import RUNBOOKS_DIR, chunk_corpus
from triage.rag.embed import embed_texts

INDEX_DIR = REPO_ROOT / "data" / "runbook_index"
COLLECTION = "runbooks"
_SPACE = "cosine"


def build_index(
    runbooks_dir: Path = RUNBOOKS_DIR,
    index_dir: Path = INDEX_DIR,
) -> int:
    """(Re)build the index from the markdown corpus. Returns the chunk count."""
    chunks = chunk_corpus(runbooks_dir)
    embeddings = embed_texts([c.embedding_text() for c in chunks])

    index_dir.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(index_dir))
    with contextlib.suppress(chromadb.errors.NotFoundError, ValueError):
        client.delete_collection(COLLECTION)
    collection = client.create_collection(COLLECTION, metadata={"hnsw:space": _SPACE})

    collection.add(
        ids=[c.chunk_id for c in chunks],
        embeddings=embeddings,
        documents=[c.text for c in chunks],
        metadatas=[
            {
                "source": c.source,
                "doc_title": c.doc_title,
                "section_title": c.section_title,
            }
            for c in chunks
        ],
    )
    return len(chunks)


def open_collection(index_dir: Path = INDEX_DIR) -> chromadb.Collection:
    if not index_dir.exists():
        raise FileNotFoundError(
            f"runbook index not found at {index_dir}. "
            "Build it with: uv run python scripts/build_runbook_index.py"
        )
    client = chromadb.PersistentClient(path=str(index_dir))
    return client.get_collection(COLLECTION)
