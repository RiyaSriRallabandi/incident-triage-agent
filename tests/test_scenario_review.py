from triage.dataset import REPO_ROOT
from triage.eval.scenario_review import (
    REVIEW_CHECKS,
    ScenarioReview,
    build_review_prompt,
    render_spec_for_review,
)
from triage.ingest.evidence import ScenarioSpec

SPEC_PATHS = sorted((REPO_ROOT / "data" / "eval" / "specs").glob("*.spec.json"))


def _spec(path) -> ScenarioSpec:
    return ScenarioSpec.model_validate_json(path.read_text())


def test_prompt_contains_every_check_and_the_ground_truth():
    spec = _spec(SPEC_PATHS[0])
    prompt = build_review_prompt(spec)
    for check_id, _ in REVIEW_CHECKS:
        assert check_id in prompt
    assert spec.ground_truth.root_cause in prompt
    assert spec.incident_report in prompt


def test_render_marks_signal_vs_distractor_counts():
    spec = _spec(SPEC_PATHS[0])
    rendered = render_spec_for_review(spec)
    assert f"{len(spec.signal_lines)} signal" in rendered


def test_scenario_review_flags_helper():
    review = ScenarioReview(
        scenario_id="scn_001",
        overall="needs_changes",
        summary="s",
        checks=[
            {"check": "a", "verdict": "pass", "reason": "r"},
            {"check": "b", "verdict": "flag", "reason": "r"},
        ],
    )
    assert [c.check for c in review.flags()] == ["b"]
