"""Cohen's kappa between hand grades and judge grades.

Hand labels live in ``data/eval/hand_labels.json``:
    {"scn_001__run1": {"grade": "partial", "note": "..."}, ...}
where grade is one of correct / partial / incorrect (the unified 3-way label).
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel
from sklearn.metrics import cohen_kappa_score

from triage.dataset import REPO_ROOT
from triage.eval.judge import Judgement

HAND_LABELS_PATH = REPO_ROOT / "data" / "eval" / "hand_labels.json"

_LEVELS = ["correct", "partial", "incorrect"]


class Calibration(BaseModel):
    n: int
    raw_agreement: float
    cohen_kappa: float
    disagreements: list[tuple[str, str, str]]  # (run key, hand grade, judge grade)


def load_hand_labels(path: Path = HAND_LABELS_PATH) -> dict[str, str]:
    if not path.exists():
        return {}
    raw = json.loads(path.read_text())
    return {key: entry["grade"] for key, entry in raw.items()}


def calibrate(judgements: list[Judgement], hand: dict[str, str] | None = None) -> Calibration:
    hand = hand if hand is not None else load_hand_labels()
    judge = {j.key: j.unified_label() for j in judgements}

    keys = sorted(set(hand) & set(judge))
    if not keys:
        raise ValueError("no overlap between hand labels and judged runs")

    h = [hand[k] for k in keys]
    j = [judge[k] for k in keys]

    kappa = cohen_kappa_score(h, j, labels=_LEVELS)
    return Calibration(
        n=len(keys),
        raw_agreement=sum(a == b for a, b in zip(h, j, strict=True)) / len(keys),
        cohen_kappa=float(kappa),
        disagreements=[(k, hand[k], judge[k]) for k in keys if hand[k] != judge[k]],
    )
