"""Automated first-pass review of scenario specs against the SRE rubric.

Usage:
    uv run python scripts/review_scenarios.py             # review every spec
    uv run python scripts/review_scenarios.py scn_002     # review one

Requires GROQ_API_KEY. Exits non-zero if any scenario is flagged, so it can gate
CI on the golden set later. Human sign-off still required - this only flags.
"""

from __future__ import annotations

import sys

from triage.config import get_settings
from triage.dataset import REPO_ROOT
from triage.eval.scenario_review import review_scenario
from triage.ingest.evidence import ScenarioSpec

SPECS_DIR = REPO_ROOT / "data" / "eval" / "specs"


def main(argv: list[str]) -> int:
    if not get_settings().groq_api_key:
        print("GROQ_API_KEY is not set - cannot run the automated review.")
        return 2

    wanted = set(argv)
    spec_paths = sorted(SPECS_DIR.glob("*.spec.json"))
    if wanted:
        spec_paths = [p for p in spec_paths if p.stem.replace(".spec", "") in wanted]
    if not spec_paths:
        print("no matching specs")
        return 2

    any_flagged = False
    for path in spec_paths:
        spec = ScenarioSpec.model_validate_json(path.read_text())
        review = review_scenario(spec)

        mark = "OK  " if review.overall == "pass" else "FLAG"
        print(f"\n[{mark}] {review.scenario_id} - {review.summary}")
        for check in review.checks:
            symbol = "  ." if check.verdict == "pass" else "  !"
            print(f"{symbol} {check.check}: {check.reason}")
        any_flagged |= review.overall != "pass"

    print()
    print("Some scenarios were flagged - review above." if any_flagged else "All scenarios passed.")
    return 1 if any_flagged else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
