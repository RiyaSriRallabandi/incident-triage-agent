"""Build the runbook vector index from data/runbooks/*.md.

Usage:
    uv run python scripts/build_runbook_index.py

Downloads the embedding model on first run (~80 MB, cached afterwards). The index
is written to data/runbook_index/ and is gitignored - it is rebuildable from the
markdown sources.
"""

from __future__ import annotations

from triage.rag.chunk import RUNBOOKS_DIR
from triage.rag.index import INDEX_DIR, build_index


def main() -> int:
    print(f"building index from {RUNBOOKS_DIR.relative_to(RUNBOOKS_DIR.parents[2])}/ ...")
    count = build_index()
    print(f"indexed {count} runbook sections -> {INDEX_DIR.relative_to(INDEX_DIR.parents[2])}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
