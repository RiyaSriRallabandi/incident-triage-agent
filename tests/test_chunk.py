import pytest

from triage.rag.chunk import chunk_corpus, chunk_markdown

SAMPLE = """# Connection pool exhaustion

## Symptoms

Errors stating the pool is exhausted. Throughput collapses.

## Likely causes

- A slow downstream holding connections.
- A connection leak.

## Mitigation

Isolate pools per dependency and add acquisition timeouts.
"""


def test_chunk_markdown_splits_by_section(tmp_path):
    path = tmp_path / "connection-pool-exhaustion.md"
    path.write_text(SAMPLE)

    chunks = chunk_markdown(path)

    assert [c.section_title for c in chunks] == ["Symptoms", "Likely causes", "Mitigation"]
    assert all(c.doc_title == "Connection pool exhaustion" for c in chunks)
    assert all(c.source == "connection-pool-exhaustion.md" for c in chunks)
    assert "connection leak" in chunks[1].text
    assert "## " not in chunks[0].text  # heading line excluded from body
    assert chunks[0].chunk_id == "connection-pool-exhaustion.md::symptoms"
    assert chunks[0].doc_title in chunks[0].embedding_text()


def test_chunk_markdown_requires_title_and_sections(tmp_path):
    no_title = tmp_path / "x.md"
    no_title.write_text("## Symptoms\n\nsomething\n")
    with pytest.raises(ValueError, match="missing '# Title'"):
        chunk_markdown(no_title)

    no_sections = tmp_path / "y.md"
    no_sections.write_text("# Title\n\njust prose, no sections\n")
    with pytest.raises(ValueError, match="no '## Section'"):
        chunk_markdown(no_sections)


def test_real_corpus_chunks_cleanly():
    chunks = chunk_corpus()
    assert len(chunks) >= 40
    assert len({c.source for c in chunks}) >= 10
    assert all(c.text.strip() for c in chunks)
    assert len({c.chunk_id for c in chunks}) == len(chunks)  # ids unique
