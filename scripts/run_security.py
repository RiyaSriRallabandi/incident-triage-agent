"""Run the prompt-injection slice: inject each attack, run the agent, score.

    uv run python scripts/run_security.py

Results are cached to data/security/results.json (resumable). Needs an LLM key.
"""

from __future__ import annotations

import json
import time

from triage.agent.run import investigate
from triage.dataset import REPO_ROOT
from triage.eval.variants import BASELINE
from triage.security.injection import (
    AttackResult,
    build_injected_scenario,
    load_attacks,
    score_attack,
)

RESULTS_PATH = REPO_ROOT / "data" / "security" / "results.json"


def main() -> int:
    attacks = load_attacks()
    cached: dict[str, AttackResult] = {}
    if RESULTS_PATH.exists():
        cached = {
            r["id"]: AttackResult.model_validate(r) for r in json.loads(RESULTS_PATH.read_text())
        }

    results: list[AttackResult] = []
    for attack in attacks:
        if attack.id in cached:
            results.append(cached[attack.id])
            continue
        print(f"running {attack.id} ({attack.attack_type}) ...")
        scenario = build_injected_scenario(attack)
        result = investigate(
            scenario,
            budget=BASELINE.budget,
            provider=BASELINE.provider,  # type: ignore[arg-type]
            conclude_prompt=BASELINE.conclude_prompt,
            plan_prompt=BASELINE.plan_prompt,
        )
        scored = score_attack(attack, result)
        results.append(scored)
        RESULTS_PATH.write_text(json.dumps([r.model_dump() for r in results], indent=2) + "\n")
        time.sleep(4)

    passed = sum(r.passed for r in results)
    print(f"\n=== prompt-injection resistance: {passed}/{len(results)} passed ===\n")
    for r in results:
        mark = "PASS" if r.passed else "FAIL"
        flag = "  (flagged anomaly)" if r.flagged_anomaly else ""
        print(f"  [{mark}] {r.id:8s} {r.attack_type:40s} {r.notes}{flag}")
    print(f"\nwritten: {RESULTS_PATH.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
