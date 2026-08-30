# Runbook corpus

Short troubleshooting guides the agent can search while investigating an incident.
They provide general operational expertise ("what this pattern usually means, how
to confirm it") to complement the incident-specific evidence from logs, metrics,
and deploy history.

## Provenance

Each runbook is hand-written as paraphrased general SRE knowledge. Nothing is
copied from the sources; the `## References` section of each file cites public
material the failure pattern is informed by (Google SRE Book, AWS Builders'
Library, published postmortems, Microsoft Research).

## Format

Markdown, one failure pattern per file, structured by `##` section headings
(`Symptoms`, `Likely causes`, `How to confirm`, `Mitigation`, `References`). The
index chunks by section, so each section should stand on its own.

## Rebuilding the index

```bash
uv run python scripts/build_runbook_index.py
```

The index (`data/runbook_index/`) is gitignored and rebuilt from these files.
