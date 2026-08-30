"""Produce and cache agent runs over the golden set.

Runs are slow and non-deterministic, so each ``AgentResult`` is written to
``data/eval/runs/`` and reused on subsequent analysis. The report cites a
specific cached set. Caching makes an interrupted run resumable.
"""

from __future__ import annotations

import time
import traceback
from pathlib import Path

from pydantic import BaseModel

from triage.agent.run import investigate
from triage.agent.state import AgentResult
from triage.dataset import REPO_ROOT, load_scenarios
from triage.eval.variants import BASELINE, Variant
from triage.rag.index import INDEX_DIR
from triage.schema import Scenario

RUNS_DIR = REPO_ROOT / "data" / "eval" / "runs"


class CachedRun(BaseModel):
    tag: str
    scenario_id: str
    run_index: int
    budget: int
    provider: str = "groq"
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
    variant: Variant = BASELINE,
    repeats: int = 1,
    runbook_index_dir: Path = INDEX_DIR,
    runs_dir: Path = RUNS_DIR,
    force: bool = False,
    pause_s: float = 4.0,
) -> list[CachedRun]:
    """Run every scenario ``repeats`` times for ``variant``, caching each result."""
    scenarios = scenarios or load_scenarios()
    runs_dir.mkdir(parents=True, exist_ok=True)
    out: list[CachedRun] = []
    ran_any = False

    for scenario in scenarios:
        for i in range(1, repeats + 1):
            path = run_path(variant.tag, scenario.id, i, runs_dir)
            if path.exists() and not force:
                out.append(CachedRun.model_validate_json(path.read_text()))
                continue

            if ran_any and pause_s:
                time.sleep(pause_s)  # stay under per-minute free-tier limits
            ran_any = True

            common = dict(
                tag=variant.tag,
                scenario_id=scenario.id,
                run_index=i,
                budget=variant.budget,
                provider=variant.provider,
            )
            try:
                result = investigate(
                    scenario,
                    budget=variant.budget,
                    provider=variant.provider,  # type: ignore[arg-type]
                    model=variant.model,
                    plan_prompt=variant.plan_prompt,
                    conclude_prompt=variant.conclude_prompt,
                    tools=variant.tools,
                    runbook_index_dir=runbook_index_dir,
                )
                cached = CachedRun(**common, result=result)
            except Exception:  # noqa: BLE001 - a crashed run is a data point, not a stop
                cached = CachedRun(**common, error=traceback.format_exc(limit=3))

            path.write_text(cached.model_dump_json(indent=2) + "\n")
            out.append(cached)

    return out


def load_runs(tag: str = BASELINE.tag, runs_dir: Path = RUNS_DIR) -> list[CachedRun]:
    paths = sorted(runs_dir.glob(f"{tag}__*.json"))
    return [CachedRun.model_validate_json(p.read_text()) for p in paths]
