"""Run (or reuse) the golden-set eval and print a summary.

    uv run python scripts/run_eval.py                 # baseline, 3 runs/scenario
    uv run python scripts/run_eval.py --repeats 5 --tag v2
    uv run python scripts/run_eval.py --force         # re-run the agent, ignore cache

Agent runs and judgements are cached under data/eval/. Needs GROQ_API_KEY.
"""

from __future__ import annotations

import argparse
import json

from triage.dataset import REPO_ROOT, load_scenarios
from triage.eval.calibration import calibrate, load_hand_labels
from triage.eval.judge import Judgement, judge_run
from triage.eval.metrics import run_metrics
from triage.eval.runner import load_runs, produce_runs
from triage.eval.summary import summarize

EVAL_DIR = REPO_ROOT / "data" / "eval"


def _judgements_path(tag: str):
    return EVAL_DIR / f"judgements__{tag}.json"


def _load_or_judge(runs, scenarios_by_id, tag: str, *, force: bool) -> list[Judgement]:
    path = _judgements_path(tag)
    if path.exists() and not force:
        return [Judgement.model_validate(j) for j in json.loads(path.read_text())]

    judgements = [judge_run(r, scenarios_by_id[r.scenario_id]) for r in runs]
    path.write_text(json.dumps([j.model_dump() for j in judgements], indent=2) + "\n")
    return judgements


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--budget", type=int, default=6)
    parser.add_argument("--provider", default="gemini", choices=["groq", "gemini"])
    parser.add_argument("--tag", default="baseline")
    parser.add_argument("--force", action="store_true", help="re-run agent and judge")
    args = parser.parse_args()

    scenarios = load_scenarios()
    by_id = {s.id: s for s in scenarios}

    print(f"producing runs (tag={args.tag}, repeats={args.repeats}, provider={args.provider}) ...")
    produce_runs(
        scenarios,
        repeats=args.repeats,
        budget=args.budget,
        provider=args.provider,
        tag=args.tag,
        force=args.force,
    )
    runs = load_runs(args.tag)

    print("judging ...")
    judgements = _load_or_judge(runs, by_id, args.tag, force=args.force)

    metrics = [run_metrics(r, by_id[r.scenario_id]) for r in runs]

    hand = load_hand_labels()
    cal = calibrate(judgements, hand) if hand else None

    summary = summarize(args.tag, metrics, judgements, calibration=cal)
    out = EVAL_DIR / f"summary__{args.tag}.json"
    out.write_text(summary.model_dump_json(indent=2) + "\n")

    _print_summary(summary)
    print(f"\nwritten: {out.relative_to(REPO_ROOT)}")
    return 0


def _pct(x: float | None) -> str:
    return "  n/a" if x is None else f"{x * 100:5.1f}%"


def _print_summary(s) -> None:
    print(f"\n=== eval summary: {s.tag}  ({s.n_runs} runs, {s.n_crashed} crashed) ===\n")
    print("OUTCOME")
    print(f"  root-cause accuracy (correct)     {_pct(s.root_cause_accuracy)}")
    print(f"  root-cause partial                {_pct(s.root_cause_partial_rate)}")
    print(f"  escalation decision accuracy      {_pct(s.escalation_decision_accuracy)}")
    print(f"  false-confident-wrong rate        {_pct(s.false_confident_wrong_rate)}")
    print("\nSTEP-LEVEL")
    print(f"  mean tool calls                   {s.mean_tool_calls}")
    print(f"  budget-cap rate                   {_pct(s.budget_cap_rate)}")
    print(f"  mean error steps / run            {s.mean_error_steps}")
    print(f"  citation grounding rate           {_pct(s.citation_grounding_rate)}")
    print(f"  fabricated citation rate          {_pct(s.fabricated_citation_rate)}")
    if s.failure_stages:
        print("\nFAILURE STAGES")
        for stage, count in sorted(s.failure_stages.items(), key=lambda kv: -kv[1]):
            print(f"  {stage:24s} {count}")
    if s.calibration:
        c = s.calibration
        print("\nJUDGE CALIBRATION (vs hand labels)")
        print(
            f"  n={c.n}  raw agreement {_pct(c.raw_agreement)}  Cohen's kappa {c.cohen_kappa:.3f}"
        )
        for key, hand_g, judge_g in c.disagreements:
            print(f"    disagree {key}: hand={hand_g} judge={judge_g}")
    print("\nPER SCENARIO")
    for b in s.per_scenario:
        print(
            f"  {b.scenario_id}  grades={b.root_cause_grades}  "
            f"esc={b.escalation_calls}  mean_calls={b.mean_tool_calls}  "
            f"grounded={_pct(b.grounded_citation_rate)}"
        )


if __name__ == "__main__":
    raise SystemExit(main())
