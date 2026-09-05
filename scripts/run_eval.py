"""Evaluate one agent variant on the golden set and print a summary.

    uv run python scripts/run_eval.py                       # dev-baseline
    uv run python scripts/run_eval.py --variant conclude-v2
    uv run python scripts/run_eval.py --force               # re-run agent + judge

Runs and judgements are cached under data/eval/. Needs an LLM key.
"""

from __future__ import annotations

import argparse

from triage.dataset import REPO_ROOT
from triage.eval.pipeline import evaluate_variant
from triage.eval.summary import EvalSummary
from triage.eval.variants import VARIANTS


def _pct(x: float | None) -> str:
    return "  n/a" if x is None else f"{x * 100:5.1f}%"


def print_summary(s: EvalSummary) -> None:
    print(f"\n=== {s.tag}  ({s.n_runs} runs, {s.n_crashed} crashed) ===\n")
    print("OUTCOME")
    print(f"  root-cause accuracy (correct)     {_pct(s.root_cause_accuracy)}")
    print(f"  root-cause partial                {_pct(s.root_cause_partial_rate)}")
    print(f"  escalation decision accuracy      {_pct(s.escalation_decision_accuracy)}")
    print(f"  false-confident-wrong rate        {_pct(s.false_confident_wrong_rate)}")
    print("\nSTEP-LEVEL")
    print(f"  mean tool calls                   {s.mean_tool_calls}")
    print(f"  budget-cap rate                   {_pct(s.budget_cap_rate)}")
    print(f"  citation grounding rate           {_pct(s.citation_grounding_rate)}")
    print(f"  fabricated citation rate          {_pct(s.fabricated_citation_rate)}")
    if s.failure_stages:
        print("\nFAILURE STAGES")
        for stage, count in sorted(s.failure_stages.items(), key=lambda kv: -kv[1]):
            print(f"  {stage:24s} {count}")
    if s.calibration:
        c = s.calibration
        print("\nJUDGE CALIBRATION (vs the manual review)")
        print(f"  n={c.n}  raw agreement {_pct(c.raw_agreement)}  kappa {c.cohen_kappa:.3f}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--variant", default="dev-baseline", choices=list(VARIANTS))
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    variant = VARIANTS[args.variant]
    print(f"evaluating variant '{variant.tag}' (repeats={args.repeats}) ...")
    # Calibration compares judge vs the manual review, which exists only for dev-baseline runs.
    ev = evaluate_variant(
        variant,
        repeats=args.repeats,
        force=args.force,
        calibrate_judge=(variant.tag == "dev-baseline"),
    )
    print_summary(ev.summary)
    out = REPO_ROOT / "data" / "eval" / f"summary__{variant.tag}.json"
    print(f"\nwritten: {out.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
