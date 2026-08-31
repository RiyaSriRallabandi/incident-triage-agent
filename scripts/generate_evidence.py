"""Expand scenario specs into full scenario files.

Usage:
    uv run python scripts/generate_evidence.py --all          # dev set
    uv run python scripts/generate_evidence.py --heldout      # held-out test set
    uv run python scripts/generate_evidence.py data/eval/specs/scn_001.spec.json

A spec in a ``.../specs/`` directory writes its scenario to the sibling
``.../scenarios/`` directory. Deterministic: regenerating is idempotent unless the
spec changed.
"""

from __future__ import annotations

import sys
from pathlib import Path

from triage.dataset import REPO_ROOT
from triage.ingest.evidence import ScenarioSpec, generate_scenario

SPECS_DIR = REPO_ROOT / "data" / "eval" / "specs"
HELDOUT_SPECS_DIR = REPO_ROOT / "data" / "eval" / "heldout" / "specs"


def build(spec_path: Path) -> Path:
    spec_path = spec_path.resolve()
    spec = ScenarioSpec.model_validate_json(spec_path.read_text())
    scenario = generate_scenario(spec)
    out_dir = spec_path.parent.parent / "scenarios"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{scenario.id}.json"
    out.write_text(scenario.model_dump_json(indent=2) + "\n")
    print(
        f"{spec_path.name} -> {out.relative_to(REPO_ROOT)}  "
        f"({len(scenario.synthetic_logs)} logs, {len(scenario.synthetic_metrics)} metrics)"
    )
    return out


def main(argv: list[str]) -> int:
    if argv == ["--all"] or not argv:
        specs = sorted(SPECS_DIR.glob("*.spec.json"))
    elif argv == ["--heldout"]:
        specs = sorted(HELDOUT_SPECS_DIR.glob("*.spec.json"))
    else:
        specs = [Path(a) for a in argv]
    if not specs:
        print("no specs found")
        return 1

    for spec_path in specs:
        build(spec_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
