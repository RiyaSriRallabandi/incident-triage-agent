"""Write a human-readable grading sheet for the cached agent runs.

    uv run python scripts/make_grading_sheet.py --tag baseline

For each run it shows the incident, the ground-truth cause, and the agent's
conclusion, so a person can grade correct / partial / incorrect. Fill grades into
data/eval/hand_labels.json.
"""

from __future__ import annotations

import argparse

from triage.dataset import REPO_ROOT, load_scenarios
from triage.eval.runner import load_runs

EVAL_DIR = REPO_ROOT / "data" / "eval"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", default="baseline")
    args = parser.parse_args()

    by_id = {s.id: s for s in load_scenarios()}
    runs = load_runs(args.tag)

    lines = [f"# Grading sheet - {args.tag}\n"]
    for r in runs:
        s = by_id[r.scenario_id]
        lines.append(f"\n## {r.scenario_id}__run{r.run_index}\n")
        lines.append(f"**Incident:** {s.incident_report}\n")
        lines.append(f"**Ground-truth cause:** {s.ground_truth.root_cause}\n")
        lines.append(f"**Ground-truth should_escalate:** {s.ground_truth.should_escalate}\n")

        if r.result is None:
            lines.append("**Agent:** CRASHED\n")
        elif r.result.diagnosis:
            d = r.result.diagnosis
            lines.append(
                f"**Agent (diagnosis, confidence {d.confidence}, "
                f"{r.result.tool_calls_used} tool calls):** {d.root_cause}\n"
            )
            lines.append(f"**Agent citations:** {d.evidence}\n")
        else:
            e = r.result.escalation
            lines.append(
                f"**Agent (escalate, {r.result.tool_calls_used} tool calls):** {e.reason}\n"
            )

        lines.append("**Grade (correct / partial / incorrect):** ____\n")

    out = EVAL_DIR / f"grading_sheet__{args.tag}.md"
    out.write_text("\n".join(lines) + "\n")
    print(f"written: {out.relative_to(REPO_ROOT)}  ({len(runs)} runs)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
