"""Load and validate the golden scenario set."""

from __future__ import annotations

import json
from pathlib import Path

from triage.schema import Scenario

REPO_ROOT = Path(__file__).resolve().parents[2]
SCENARIOS_DIR = REPO_ROOT / "data" / "eval" / "scenarios"


def load_scenario(path: str | Path) -> Scenario:
    """Load and validate a single scenario JSON file."""
    path = Path(path)
    data = json.loads(path.read_text())
    scenario = Scenario.model_validate(data)
    if scenario.id != path.stem:
        raise ValueError(f"{path.name}: id {scenario.id!r} does not match filename")
    return scenario


def load_scenarios(directory: str | Path = SCENARIOS_DIR) -> list[Scenario]:
    """Load every ``scn_*.json`` in ``directory``, sorted by id.

    Raises on any invalid file or duplicate id.
    """
    directory = Path(directory)
    scenarios = [load_scenario(p) for p in sorted(directory.glob("scn_*.json"))]

    ids = [s.id for s in scenarios]
    duplicates = {i for i in ids if ids.count(i) > 1}
    if duplicates:
        raise ValueError(f"duplicate scenario ids: {sorted(duplicates)}")

    return scenarios
