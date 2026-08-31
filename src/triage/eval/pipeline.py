"""One-variant evaluation pipeline: produce runs -> judge -> metrics -> summary.

Everything is cached under data/eval/ keyed by the variant tag, so re-running only
does the missing work.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from triage.dataset import REPO_ROOT, load_scenarios
from triage.eval.calibration import Calibration, calibrate, load_hand_labels
from triage.eval.judge import Judgement, judge_run
from triage.eval.metrics import RunMetrics, run_metrics
from triage.eval.runner import CachedRun, load_runs, produce_runs
from triage.eval.summary import EvalSummary, summarize
from triage.eval.variants import Variant
from triage.schema import Scenario

EVAL_DIR = REPO_ROOT / "data" / "eval"


def _judgements_path(tag: str):
    return EVAL_DIR / f"judgements__{tag}.json"


def load_or_judge(
    runs: list[CachedRun], by_id: dict[str, Scenario], tag: str, *, force: bool = False
) -> list[Judgement]:
    """Judge each run, caching per key. Only un-judged (or newly re-run) keys hit the LLM."""
    path = _judgements_path(tag)
    cached: dict[str, Judgement] = {}
    if path.exists() and not force:
        cached = {
            j["scenario_id"] + f"__run{j['run_index']}": Judgement.model_validate(j)
            for j in json.loads(path.read_text())
        }

    judgements: list[Judgement] = []
    for r in runs:
        j = cached.get(r.key)
        # re-judge if missing, or if a crashed run has since succeeded
        if j is None or (j.agent_outcome == "crashed" and r.result is not None):
            j = judge_run(r, by_id[r.scenario_id])
        judgements.append(j)

    path.write_text(json.dumps([j.model_dump() for j in judgements], indent=2) + "\n")
    return judgements


@dataclass
class VariantEval:
    variant: Variant
    runs: list[CachedRun]
    judgements: list[Judgement]
    metrics: list[RunMetrics]
    summary: EvalSummary

    def labels(self) -> dict[str, str]:
        return {j.key: j.unified_label() for j in self.judgements}

    def per_run(self, attr: str) -> dict[str, float]:
        out: dict[str, float] = {}
        for m in self.metrics:
            value = getattr(m, attr)
            if value is not None:
                out[f"{m.scenario_id}__run{m.run_index}"] = float(value)
        return out

    def grounding_rate_per_run(self) -> dict[str, float]:
        return {
            f"{m.scenario_id}__run{m.run_index}": m.n_grounded / m.n_citations
            for m in self.metrics
            if m.n_citations
        }


def evaluate_variant(
    variant: Variant,
    by_id: dict[str, Scenario] | None = None,
    *,
    repeats: int = 1,
    force: bool = False,
    calibrate_judge: bool = False,
) -> VariantEval:
    by_id = by_id or {s.id: s for s in load_scenarios()}

    produce_runs(list(by_id.values()), variant=variant, repeats=repeats, force=force)
    runs = load_runs(variant.tag)
    judgements = load_or_judge(runs, by_id, variant.tag, force=force)
    metrics = [run_metrics(r, by_id[r.scenario_id]) for r in runs]

    cal: Calibration | None = None
    if calibrate_judge:
        hand = load_hand_labels()
        cal = calibrate(judgements, hand) if hand else None

    summary = summarize(variant.tag, metrics, judgements, calibration=cal)
    (EVAL_DIR / f"summary__{variant.tag}.json").write_text(summary.model_dump_json(indent=2) + "\n")
    return VariantEval(variant, runs, judgements, metrics, summary)
