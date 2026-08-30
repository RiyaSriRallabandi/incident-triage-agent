import json

import pytest

from triage.eval.calibration import calibrate, load_hand_labels
from triage.eval.judge import Judgement


def _judgement(key: str, label: str) -> Judgement:
    sid, run = key.split("__run")
    grade = label if label in ("correct", "partial", "incorrect") else "n/a"
    call = (
        "correct" if label == "correct" else ("false_diagnosis" if label == "incorrect" else None)
    )
    return Judgement(
        scenario_id=sid,
        run_index=int(run),
        agent_outcome="diagnosis",
        root_cause_grade=grade,
        escalation_call=call,
        false_confident_wrong=False,
        failure_stage=None,
        reasoning="",
    )


def test_perfect_agreement_gives_kappa_one():
    labels = {"scn_001__run1": "correct", "scn_002__run1": "partial", "scn_003__run1": "incorrect"}
    judgements = [_judgement(k, v) for k, v in labels.items()]
    cal = calibrate(judgements, hand=labels)
    assert cal.n == 3
    assert cal.raw_agreement == 1.0
    assert cal.cohen_kappa == pytest.approx(1.0)
    assert cal.disagreements == []


def test_disagreements_are_listed():
    hand = {"scn_001__run1": "correct", "scn_002__run1": "correct", "scn_003__run1": "incorrect"}
    judge = {"scn_001__run1": "correct", "scn_002__run1": "partial", "scn_003__run1": "incorrect"}
    judgements = [_judgement(k, v) for k, v in judge.items()]
    cal = calibrate(judgements, hand=hand)
    assert cal.raw_agreement == pytest.approx(2 / 3)
    assert cal.disagreements == [("scn_002__run1", "correct", "partial")]


def test_calibrate_requires_overlap():
    judgements = [_judgement("scn_001__run1", "correct")]
    with pytest.raises(ValueError, match="no overlap"):
        calibrate(judgements, hand={"scn_999__run1": "correct"})


def test_load_hand_labels(tmp_path):
    path = tmp_path / "hand.json"
    path.write_text(json.dumps({"scn_001__run1": {"grade": "partial", "note": "close"}}))
    assert load_hand_labels(path) == {"scn_001__run1": "partial"}
    assert load_hand_labels(tmp_path / "missing.json") == {}
