import json

import pytest

from triage.dataset import REPO_ROOT
from triage.ingest.evidence import ScenarioSpec, generate_scenario

SPEC_FILES = sorted((REPO_ROOT / "data" / "eval" / "specs").glob("*.spec.json"))


def _load_spec(path) -> ScenarioSpec:
    return ScenarioSpec.model_validate_json(path.read_text())


@pytest.mark.parametrize("path", SPEC_FILES, ids=lambda p: p.stem)
def test_generation_is_deterministic(path):
    spec = _load_spec(path)
    first = generate_scenario(spec).model_dump_json()
    second = generate_scenario(spec).model_dump_json()
    assert first == second


@pytest.mark.parametrize("path", SPEC_FILES, ids=lambda p: p.stem)
def test_signal_lines_survive_generation(path):
    spec = _load_spec(path)
    scenario = generate_scenario(spec)
    log_messages = {line.msg for line in scenario.synthetic_logs}
    for signal in spec.signal_lines:
        assert signal.msg in log_messages


@pytest.mark.parametrize("path", SPEC_FILES, ids=lambda p: p.stem)
def test_checked_in_scenario_matches_regenerated(path):
    """The committed scenario file must be exactly what the spec produces."""
    spec = _load_spec(path)
    regenerated = json.loads(generate_scenario(spec).model_dump_json())
    scenario_path = REPO_ROOT / "data" / "eval" / "scenarios" / f"{spec.id}.json"
    committed = json.loads(scenario_path.read_text())
    assert committed == regenerated, f"{spec.id}.json is stale; rerun scripts/generate_evidence.py"


def test_harder_difficulty_adds_more_distractors():
    spec = _load_spec(SPEC_FILES[0])
    easy = spec.model_copy(update={"difficulty": "easy"})
    hard = spec.model_copy(update={"difficulty": "hard"})
    assert len(generate_scenario(hard).synthetic_logs) > len(generate_scenario(easy).synthetic_logs)
