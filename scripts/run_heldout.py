"""Run baseline and the winning variant ONCE on the sealed held-out test set.

    uv run python scripts/run_heldout.py --winner conclude-v3

The held-out scenarios (data/eval/heldout/) were never used for prompt iteration,
so these numbers are the honest headline. Run this only after the dev-set
ablations have frozen the config. Results cache under data/eval/ with a
``heldout-`` tag prefix.
"""

from __future__ import annotations

import argparse

from triage.dataset import REPO_ROOT, load_scenarios
from triage.eval.pipeline import evaluate_variant
from triage.eval.stats import mcnemar_correct, wilcoxon_paired
from triage.eval.variants import BASELINE, VARIANTS

HELDOUT_SCENARIOS_DIR = REPO_ROOT / "data" / "eval" / "heldout" / "scenarios"


def _pct(x: float | None) -> str:
    return "  n/a" if x is None else f"{x * 100:5.1f}%"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--winner", default="conclude-v3", choices=list(VARIANTS))
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    by_id = {s.id: s for s in load_scenarios(HELDOUT_SCENARIOS_DIR)}
    print(f"held-out test set: {len(by_id)} scenarios\n")

    base = BASELINE.model_copy(update={"tag": "heldout-baseline"})
    winner = VARIANTS[args.winner].model_copy(update={"tag": f"heldout-{args.winner}"})

    base_ev = evaluate_variant(base, by_id, force=args.force)
    winner_ev = evaluate_variant(winner, by_id, force=args.force)

    for tag, ev in [("baseline", base_ev), (args.winner, winner_ev)]:
        s = ev.summary
        print(f"=== held-out: {tag} ({s.n_runs} runs) ===")
        print(f"  root-cause accuracy      {_pct(s.root_cause_accuracy)}")
        print(f"  escalation decision      {_pct(s.escalation_decision_accuracy)}")
        print(f"  false-confident-wrong    {_pct(s.false_confident_wrong_rate)}")
        print(f"  citation grounding       {_pct(s.citation_grounding_rate)}")
        print(f"  mean tool calls          {s.mean_tool_calls}\n")

    mc = mcnemar_correct(base_ev.labels(), winner_ev.labels())
    wg = wilcoxon_paired(
        base_ev.grounding_rate_per_run(),
        winner_ev.grounding_rate_per_run(),
        metric="citation_grounding_rate",
    )
    print("held-out: winner vs baseline")
    print(f"  correct-rate  delta {mc.delta:+}  p(mcnemar) {mc.p_value}  ({mc.note})")
    print(f"  grounding     delta {wg.delta:+}  p(wilcoxon) {wg.p_value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
