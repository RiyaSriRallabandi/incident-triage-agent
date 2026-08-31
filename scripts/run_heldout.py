"""Run the shipped config ONCE on the sealed held-out test set.

    uv run python scripts/run_heldout.py

The held-out scenarios (data/eval/heldout/) were never used for prompt iteration
or ablations, so these numbers are the honest headline. The dev-set ablations
rejected every prompt variant (each improved one axis but regressed another), so
the shipped config is ``dev-baseline``. Results cache with a ``heldout-`` tag.
"""

from __future__ import annotations

import argparse

from triage.dataset import REPO_ROOT, load_scenarios
from triage.eval.pipeline import evaluate_variant
from triage.eval.variants import VARIANTS

HELDOUT_SCENARIOS_DIR = REPO_ROOT / "data" / "eval" / "heldout" / "scenarios"


def _pct(x: float | None) -> str:
    return "  n/a" if x is None else f"{x * 100:5.1f}%"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="dev-baseline", choices=list(VARIANTS))
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    by_id = {s.id: s for s in load_scenarios(HELDOUT_SCENARIOS_DIR)}
    print(f"held-out test set: {len(by_id)} scenarios (config: {args.config})\n")

    variant = VARIANTS[args.config].model_copy(update={"tag": f"heldout-{args.config}"})
    ev = evaluate_variant(variant, by_id, force=args.force, calibrate_judge=False)
    s = ev.summary

    print(f"=== held-out: {args.config} ({s.n_runs} runs) ===")
    print(f"  root-cause accuracy (correct)   {_pct(s.root_cause_accuracy)}")
    print(f"  root-cause partial              {_pct(s.root_cause_partial_rate)}")
    print(f"  escalation decision accuracy    {_pct(s.escalation_decision_accuracy)}")
    print(f"  false-confident-wrong rate      {_pct(s.false_confident_wrong_rate)}")
    print(f"  citation grounding rate         {_pct(s.citation_grounding_rate)}")
    print(f"  mean tool calls                 {s.mean_tool_calls}")
    print(f"  budget-cap rate                 {_pct(s.budget_cap_rate)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
