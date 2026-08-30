"""Produce and cache agent runs over the golden set.

Runs are slow and non-deterministic, so each ``AgentResult`` is written to
``data/eval/runs/`` and reused on subsequent analysis. The report cites a
specific cached set.
"""

from __future__ import annotations

import traceback
from pathlib import Path

from pydantic import BaseModel

from triage.agent.run import DEFAULT_BUDGET, investigate
from triage.agent.state import AgentResult
from triage.dataset import REPO_ROOT, load_scenarios
from triage.rag.index import INDEX_DIR
from triage.schema import Scenario

RUNS_DIR = REPO_ROOT / "data" / "eval" / "runs"


class CachedRun(BaseModel):
    tag: str
    scenario_id: str
    run_index: int
    budget: int
    result: AgentResult | None = None
    error: str | None = None

    @property
    def key(self) -> str:
        return f"{self.scenario_id}__run{self.run_index}"


def run_path(tag: str, scenario_id: str, run_index: int, runs_dir: Path = RUNS_DIR) -> Path:
    return runs_dir / f"{tag}__{scenario_id}__run{run_index}.json"


def produce_runs(
    scenarios: list[Scenario] | None = None,
    *,
    repeats: int = 3,
    budget: int = DEFAULT_BUDGET,
    tag: str = "baseline",
    runbook_index_dir: Path = INDEX_DIR,
    runs_dir: Path = RUNS_DIR,
    force: bool = False,
) -> list[CachedRun]:
    """Run every scenario ``repeats`` times, caching each result. Reuses the cache."""
    scenarios = scenarios or load_scenarios()
    runs_dir.mkdir(parents=True, exist_ok=True)
    out: list[CachedRun] = []

    for scenario in scenarios:
        for i in range(1, repeats + 1):
            path = run_path(tag, scenario.id, i, runs_dir)
            if path.exists() and not force:
                out.append(CachedRun.model_validate_json(path.read_text()))
                continue

            try:
                result = investigate(scenario, budget=budget, runbook_index_dir=runbook_index_dir)
                cached = CachedRun(
                    tag=tag,
                    scenario_id=scenario.id,
                    run_index=i,
                    budget=budget,
                    result=result,
                )
            except Exception:  # noqa: BLE001 - a crashed run is a data point, not a stop
                cached = CachedRun(
                    tag=tag,
                    scenario_id=scenario.id,
                    run_index=i,
                    budget=budget,
                    error=traceback.format_exc(limit=3),
                )

            path.write_text(cached.model_dump_json(indent=2) + "\n")
            out.append(cached)

    return out


def load_runs(tag: str = "baseline", runs_dir: Path = RUNS_DIR) -> list[CachedRun]:
    paths = sorted(runs_dir.glob(f"{tag}__*.json"))
    return [CachedRun.model_validate_json(p.read_text()) for p in paths]
