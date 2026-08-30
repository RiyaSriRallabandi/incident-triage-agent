"""One real end-to-end run. Checks the pipeline produces a valid contract -
not whether the answer is correct (that is Task 8's job).
"""

import pytest

from triage.agent.run import investigate
from triage.config import Settings
from triage.dataset import load_scenarios

SC = {s.id: s for s in load_scenarios()}
_HAS_KEY = bool(Settings().groq_api_key)


@pytest.mark.skipif(not _HAS_KEY, reason="GROQ_API_KEY not set")
@pytest.mark.parametrize("scenario_id", ["scn_001", "scn_004"])
def test_investigate_end_to_end(scenario_id, runbook_index):
    result = investigate(SC[scenario_id], budget=6, runbook_index_dir=runbook_index)

    assert result.scenario_id == scenario_id
    assert result.outcome in {"diagnosis", "escalate"}
    assert 1 <= result.tool_calls_used <= 6
    assert len(result.evidence) == result.tool_calls_used
    assert all(e.tool for e in result.evidence)

    if result.outcome == "diagnosis":
        assert result.diagnosis is not None
        assert result.diagnosis.root_cause.strip()
        assert result.diagnosis.evidence
        assert 0.0 <= result.diagnosis.confidence <= 1.0
    else:
        assert result.escalation is not None
        assert result.escalation.reason.strip()
