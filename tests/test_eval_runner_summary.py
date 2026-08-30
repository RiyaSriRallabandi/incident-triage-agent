import triage.eval.runner as runner_mod
from triage.dataset import load_scenarios
from triage.eval.judge import Judgement
from triage.eval.metrics import RunMetrics
from triage.eval.runner import CachedRun, load_runs, produce_runs, run_path
from triage.eval.summary import summarize

SC = {s.id: s for s in load_scenarios()}


def test_run_path_naming(tmp_path):
    p = run_path("baseline", "scn_001", 2, tmp_path)
    assert p.name == "baseline__scn_001__run2.json"


def test_produce_runs_uses_cache_without_calling_investigate(tmp_path, monkeypatch):
    scenario = SC["scn_001"]
    cached = CachedRun(tag="baseline", scenario_id="scn_001", run_index=1, budget=6, error="stub")
    run_path("baseline", "scn_001", 1, tmp_path).write_text(cached.model_dump_json())

    def _boom(*a, **k):
        raise AssertionError("investigate() called despite a cache hit")

    monkeypatch.setattr(runner_mod, "investigate", _boom)

    runs = produce_runs([scenario], repeats=1, tag="baseline", runs_dir=tmp_path)
    assert len(runs) == 1 and runs[0].error == "stub"
    assert len(load_runs("baseline", tmp_path)) == 1


def _metric(sid, run, **kw) -> RunMetrics:
    base = dict(
        scenario_id=sid,
        run_index=run,
        crashed=False,
        outcome="diagnosis",
        confidence=0.8,
        tool_calls_used=3,
        hit_budget_cap=False,
        error_steps=0,
        n_citations=2,
        n_grounded=1,
        ungrounded_citations=["x"],
        escalation_decision_correct=True,
    )
    base.update(kw)
    return RunMetrics(**base)


def _judgement(sid, run, grade, **kw) -> Judgement:
    base = dict(
        scenario_id=sid,
        run_index=run,
        agent_outcome="diagnosis",
        root_cause_grade=grade,
        escalation_call="correct",
        false_confident_wrong=False,
        failure_stage=None,
        reasoning="",
    )
    base.update(kw)
    return Judgement(**base)


def test_summarize_computes_rates():
    metrics = [
        _metric("scn_001", 1),
        _metric("scn_001", 2),
        _metric("scn_002", 1, hit_budget_cap=True),
    ]
    judgements = [
        _judgement("scn_001", 1, "correct"),
        _judgement("scn_001", 2, "partial"),
        _judgement(
            "scn_002", 1, "incorrect", false_confident_wrong=True, failure_stage="misread_evidence"
        ),
    ]
    s = summarize("baseline", metrics, judgements)

    assert s.n_runs == 3
    assert s.root_cause_accuracy == round(1 / 3, 3)
    assert s.root_cause_partial_rate == round(1 / 3, 3)
    assert s.false_confident_wrong_rate == round(1 / 3, 3)
    assert s.budget_cap_rate == round(1 / 3, 3)
    assert s.citation_grounding_rate == round(3 / 6, 3)  # 3 grounded of 6 citations
    assert s.fabricated_citation_rate == round(3 / 6, 3)
    assert s.failure_stages == {"misread_evidence": 1}
    assert {b.scenario_id for b in s.per_scenario} == {"scn_001", "scn_002"}
