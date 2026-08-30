"""Split runbook markdown into retrievable passages.

Runbooks are structured by ``##`` section headings ("Symptoms", "Likely causes",
"How to confirm", ...). Each section becomes one chunk, which keeps every passage
self-contained. The ``#`` title is carried on every chunk for context.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

from triage.dataset import REPO_ROOT

RUNBOOKS_DIR = REPO_ROOT / "data" / "runbooks"


class RunbookChunk(BaseModel):
    source: str  # file name, e.g. "cpu-saturation.md"
    doc_title: str  # the "# ..." heading
    section_title: str  # the "## ..." heading
    text: str  # section body, heading excluded

    @property
    def chunk_id(self) -> str:
        slug = self.section_title.lower().replace(" ", "-").replace("/", "-")
        return f"{self.source}::{slug}"

    def embedding_text(self) -> str:
        """What actually gets embedded: title + section give the body context."""
        return f"{self.doc_title} - {self.section_title}\n\n{self.text}"


def chunk_markdown(path: Path) -> list[RunbookChunk]:
    lines = path.read_text().splitlines()

    doc_title = ""
    section_title = ""
    body: list[str] = []
    chunks: list[RunbookChunk] = []

    def flush() -> None:
        text = "\n".join(body).strip()
        if section_title and text:
            chunks.append(
                RunbookChunk(
                    source=path.name,
                    doc_title=doc_title,
                    section_title=section_title,
                    text=text,
                )
            )

    for line in lines:
        if line.startswith("# "):
            doc_title = line[2:].strip()
        elif line.startswith("## "):
            flush()
            section_title = line[3:].strip()
            body = []
        else:
            body.append(line)
    flush()

    if not doc_title:
        raise ValueError(f"{path.name}: missing '# Title' heading")
    if not chunks:
        raise ValueError(f"{path.name}: no '## Section' headings found")
    return chunks


def chunk_corpus(runbooks_dir: Path = RUNBOOKS_DIR) -> list[RunbookChunk]:
    chunks: list[RunbookChunk] = []
    for path in sorted(runbooks_dir.glob("*.md")):
        if path.name.lower() == "readme.md":
            continue
        chunks.extend(chunk_markdown(path))
    if not chunks:
        raise ValueError(f"no runbook chunks found in {runbooks_dir}")
    return chunks
