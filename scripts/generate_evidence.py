"""Expand scenario specs into full scenario files.

Usage:
    uv run python scripts/generate_evidence.py --all
    uv run python scripts/generate_evidence.py data/eval/specs/scn_001.spec.json

Reads specs from data/eval/specs/*.spec.json and writes scenarios to
data/eval/scenarios/*.json. Deterministic: regenerating overwrites in place with
identical output unless the spec changed.
"""

from __future__ import annotations

import sys
from pathlib import Path

from triage.dataset import REPO_ROOT
from triage.ingest.evidence import ScenarioSpec, generate_scenario

SPECS_DIR = REPO_ROOT / "data" / "eval" / "specs"
SCENARIOS_DIR = REPO_ROOT / "data" / "eval" / "scenarios"


def build(spec_path: Path) -> Path:
    spec = ScenarioSpec.model_validate_json(spec_path.read_text())
    scenario = generate_scenario(spec)
    out = SCENARIOS_DIR / f"{scenario.id}.json"
    out.write_text(scenario.model_dump_json(indent=2) + "\n")
    print(
        f"{spec_path.name} -> {out.relative_to(REPO_ROOT)}  "
        f"({len(scenario.synthetic_logs)} logs, {len(scenario.synthetic_metrics)} metrics)"
    )
    return out


def main(argv: list[str]) -> int:
    SCENARIOS_DIR.mkdir(parents=True, exist_ok=True)

    if argv == ["--all"] or not argv:
        specs = sorted(SPECS_DIR.glob("*.spec.json"))
        if not specs:
            print(f"no specs found in {SPECS_DIR}")
            return 1
    else:
        specs = [Path(a) for a in argv]

    for spec_path in specs:
        build(spec_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
