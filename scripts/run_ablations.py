"""Run each variant against the golden set and compare it to dev-baseline.

    uv run python scripts/run_ablations.py                       # all variants
    uv run python scripts/run_ablations.py --only conclude-v2,no-runbook

Everything is cached, so this is resumable across days (free-tier quota).
Writes data/eval/ablations.json.
"""

from __future__ import annotations

import argparse
import json

from triage.dataset import REPO_ROOT, load_scenarios
from triage.eval.pipeline import VariantEval, evaluate_variant
from triage.eval.stats import mcnemar_correct, wilcoxon_paired
from triage.eval.variants import BASELINE, VARIANTS

EVAL_DIR = REPO_ROOT / "data" / "eval"


def _compare(base: VariantEval, var: VariantEval) -> dict:
    tests = [
        mcnemar_correct(base.labels(), var.labels()),
        wilcoxon_paired(base.per_run("confidence"), var.per_run("confidence"), metric="confidence"),
        wilcoxon_paired(
            base.per_run("tool_calls_used"),
            var.per_run("tool_calls_used"),
            metric="tool_calls_used",
        ),
        wilcoxon_paired(
            base.grounding_rate_per_run(),
            var.grounding_rate_per_run(),
            metric="citation_grounding_rate",
        ),
    ]
    return {
        "variant": var.variant.tag,
        "summary": var.summary.model_dump(),
        "tests": [t.model_dump() for t in tests],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", help="comma-separated variant tags")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    by_id = {s.id: s for s in load_scenarios()}
    tags = args.only.split(",") if args.only else [t for t in VARIANTS if t != BASELINE.tag]

    print(f"evaluating {BASELINE.tag} ...")
    base = evaluate_variant(BASELINE, by_id, force=args.force, calibrate_judge=True)

    comparisons = []
    for tag in tags:
        if tag == BASELINE.tag:
            continue
        print(f"evaluating {tag} ...")
        var = evaluate_variant(VARIANTS[tag], by_id, force=args.force)
        comparisons.append(_compare(base, var))

    report = {
        "baseline": base.summary.model_dump(),
        "comparisons": comparisons,
    }
    (EVAL_DIR / "ablations.json").write_text(json.dumps(report, indent=2) + "\n")

    print(f"\n{'variant':<16}{'correct%':>10}{'delta':>8}{'p(mcnemar)':>12}{'mean_calls':>12}")
    b = base.summary
    b_acc = (b.root_cause_accuracy or 0) * 100
    print(f"{'dev-baseline':<16}{b_acc:>9.1f}%{'':>8}{'':>12}{b.mean_tool_calls:>12}")
    for c in comparisons:
        s = c["summary"]
        mc = next(t for t in c["tests"] if t["test"] == "mcnemar_exact")
        acc = (s["root_cause_accuracy"] or 0) * 100
        print(
            f"{c['variant']:<16}{acc:>9.1f}%{mc['delta'] * 100:>+7.0f}%{mc['p_value']:>12}"
            f"{s['mean_tool_calls']:>12}"
        )
    print("\nwritten: data/eval/ablations.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
