"""A thin read-oriented web layer over the cached evaluation runs.

The deployed demo does not run the agent per request: investigation is slow and
spends free-tier LLM quota. Instead it serves the runs already recorded under
``data/eval/`` for the shipped config -- the plan/act/conclude trace, the
diagnosis, the post-hoc citation report, and the judge's verdict.

Live investigation is available at ``POST /investigate`` only when
``ALLOW_LIVE_RUNS=true``; the public instance leaves it off.
"""

from __future__ import annotations

import html
import json
from functools import lru_cache
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from triage.agent.state import AgentResult
from triage.agent.verify import verify_result
from triage.config import get_settings
from triage.dataset import REPO_ROOT, load_scenarios
from triage.eval.judge import Judgement
from triage.eval.runner import CachedRun, load_runs
from triage.eval.summary import EvalSummary
from triage.schema import Scenario

EVAL_DIR = REPO_ROOT / "data" / "eval"
HELDOUT_SCENARIOS_DIR = EVAL_DIR / "heldout" / "scenarios"

DEV_TAG = "dev-baseline"
HELDOUT_TAG = "heldout-dev-baseline"


class ScenarioView(BaseModel):
    """A scenario paired with its cached shipped-config run and judge verdict."""

    group: Literal["dev", "heldout"]
    scenario: Scenario
    run: CachedRun | None
    judgement: Judgement | None


@lru_cache(maxsize=1)
def _catalog() -> dict[str, ScenarioView]:
    views: dict[str, ScenarioView] = {}
    for group, sdir, tag in (
        ("dev", None, DEV_TAG),
        ("heldout", HELDOUT_SCENARIOS_DIR, HELDOUT_TAG),
    ):
        scenarios = load_scenarios(sdir) if sdir else load_scenarios()
        runs = {r.scenario_id: r for r in load_runs(tag)}
        judgements = _load_judgements(tag)
        for s in scenarios:
            run = runs.get(s.id)
            if run and run.result is not None:
                # Older cached runs predate post-hoc verification; apply it now so
                # the page shows what the shipped agent would deliver today.
                run = run.model_copy(update={"result": verify_result(run.result)})
            key = f"{s.id}__run{run.run_index}" if run else None
            views[s.id] = ScenarioView(
                group=group,  # type: ignore[arg-type]
                scenario=s,
                run=run,
                judgement=judgements.get(key) if key else None,
            )
    return views


def _load_judgements(tag: str) -> dict[str, Judgement]:
    path = EVAL_DIR / f"judgements__{tag}.json"
    if not path.exists():
        return {}
    items = [Judgement.model_validate(d) for d in json.loads(path.read_text())]
    return {j.key: j for j in items}


@lru_cache(maxsize=1)
def _heldout_summary() -> EvalSummary | None:
    path = EVAL_DIR / f"summary__{HELDOUT_TAG}.json"
    if not path.exists():
        return None
    return EvalSummary.model_validate_json(path.read_text())


app = FastAPI(
    title="IncidentTriage Agent",
    description="Cached investigation traces and evaluation results for the shipped config.",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/scenarios")
def list_scenarios() -> list[dict[str, str | None]]:
    out: list[dict[str, str | None]] = []
    for sid, view in _catalog().items():
        s = view.scenario
        out.append(
            {
                "id": sid,
                "group": view.group,
                "title": s.title,
                "category": s.category.value,
                "difficulty": s.difficulty.value,
                "outcome": view.run.result.outcome if view.run and view.run.result else None,
                "root_cause_grade": view.judgement.root_cause_grade if view.judgement else None,
            }
        )
    return out


class InvestigateRequest(BaseModel):
    scenario_id: str


@app.post("/investigate")
def investigate_endpoint(req: InvestigateRequest) -> AgentResult:
    if not get_settings().allow_live_runs:
        raise HTTPException(
            status_code=503,
            detail=(
                "Live investigation is disabled on this instance. It calls a hosted LLM "
                "on every request and this demo runs on a free tier. Browse the cached "
                "runs instead, or run the agent locally (see the README)."
            ),
        )
    view = _catalog().get(req.scenario_id)
    if view is None:
        raise HTTPException(status_code=404, detail=f"unknown scenario {req.scenario_id!r}")

    from triage.agent.run import investigate

    return investigate(view.scenario)


# --- HTML views ----------------------------------------------------------------

_STYLE = """
:root { color-scheme: light dark; }
* { box-sizing: border-box; }
body { font: 15px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
       max-width: 820px; margin: 0 auto; padding: 2rem 1.2rem 4rem; }
h1 { font-size: 1.5rem; margin: 0 0 .3rem; }
h2 { font-size: 1.1rem; margin: 2rem 0 .6rem; border-bottom: 1px solid #8884;
     padding-bottom: .3rem; }
a { color: inherit; }
.muted { opacity: .7; }
.lede { opacity: .8; margin: .2rem 0 1.4rem; }
table { border-collapse: collapse; width: 100%; margin: .5rem 0; }
td, th { text-align: left; padding: .35rem .6rem; border-bottom: 1px solid #8883; }
th { font-weight: 600; }
ul.scn { list-style: none; padding: 0; }
ul.scn li { padding: .4rem 0; border-bottom: 1px solid #8883; }
pre { white-space: pre-wrap; word-wrap: break-word; background: #8881; padding: .8rem;
      border-radius: 6px; font-size: 13px; overflow-x: auto; }
.step { border-left: 3px solid #8886; padding: .2rem 0 .2rem .9rem; margin: .9rem 0; }
.tag { display: inline-block; font-size: 12px; padding: .05rem .45rem; border-radius: 10px;
       background: #8882; margin-left: .3rem; }
.grade-correct { background: #2e7d3244; }
.grade-partial { background: #f9a82544; }
.grade-incorrect { background: #c6282844; }
details { margin: .6rem 0; }
summary { cursor: pointer; }
footer { margin-top: 3rem; font-size: 13px; opacity: .6; }
"""


def _page(title: str, body: str) -> HTMLResponse:
    return HTMLResponse(
        f"<!doctype html><meta charset=utf-8>"
        f"<meta name=viewport content='width=device-width,initial-scale=1'>"
        f"<title>{html.escape(title)}</title><style>{_STYLE}</style>{body}"
        f"<footer>All incident data is synthetic. Live investigation is disabled on this "
        f"instance; it serves evaluation runs recorded for the shipped config.</footer>"
    )


def _grade_badge(grade: str | None) -> str:
    if grade in (None, "n/a"):
        return ""
    return f"<span class='tag grade-{html.escape(grade)}'>{html.escape(grade)}</span>"


def _esc(text: str) -> str:
    return html.escape(text)


@app.get("/", response_class=HTMLResponse)
def index() -> HTMLResponse:
    catalog = _catalog()
    summary = _heldout_summary()

    head_table = ""
    if summary:
        rows = [
            ("Root-cause correct (mechanism identified)", summary.root_cause_accuracy),
            ("Escalation decision accuracy", summary.escalation_decision_accuracy),
            ("False-confident-wrong rate", summary.false_confident_wrong_rate),
            ("Citation grounding (raw agent output)", summary.citation_grounding_rate),
        ]
        cells = "".join(
            f"<tr><td>{_esc(label)}</td><td>{'' if v is None else f'{v:.0%}'}</td></tr>"
            for label, v in rows
        )
        head_table = (
            "<h2>Held-out test set &mdash; 10 scenarios, run once</h2>"
            f"<table>{cells}</table>"
            "<p class='muted'>Delivered citations are 100% grounded by construction: a "
            "deterministic post-hoc step drops any citation that does not trace back to "
            "retrieved evidence.</p>"
        )

    def _list(group: str) -> str:
        items = []
        for sid, view in catalog.items():
            if view.group != group:
                continue
            s = view.scenario
            grade = view.judgement.root_cause_grade if view.judgement else None
            items.append(
                f"<li><a href='/scenarios/{sid}'>{_esc(sid)} &mdash; {_esc(s.title)}</a>"
                f"<span class='tag'>{_esc(s.category.value)}</span>"
                f"<span class='tag'>{_esc(s.difficulty.value)}</span>{_grade_badge(grade)}</li>"
            )
        return f"<ul class='scn'>{''.join(items)}</ul>"

    body = (
        "<h1>IncidentTriage Agent</h1>"
        "<p class='lede'>A multi-step agent that investigates an on-call incident &mdash; "
        "queries logs, metrics, deploys and a runbook corpus, then produces a cited "
        "root-cause hypothesis or escalates. Each page below is a recorded run of the "
        "shipped config, with the agent's trace and the LLM judge's verdict.</p>"
        f"{head_table}"
        "<h2>Dev set &mdash; 30 scenarios (prompt iteration + ablations)</h2>"
        f"{_list('dev')}"
        "<h2>Held-out set &mdash; 10 scenarios (sealed, used once)</h2>"
        f"{_list('heldout')}"
    )
    return _page("IncidentTriage Agent", body)


def _render_trace(result: AgentResult) -> str:
    if not result.evidence:
        return "<p class='muted'>(no evidence gathered)</p>"
    steps = []
    for e in result.evidence:
        args = _esc(json.dumps(e.args))
        err = " <span class='tag'>error</span>" if e.error else ""
        steps.append(
            f"<div class='step'><strong>Step {e.step}</strong>{err}"
            f"<p>{_esc(e.plan_reasoning)}</p>"
            f"<p class='muted'><code>{_esc(e.tool)}({args})</code></p>"
            f"<details><summary>result</summary><pre>{_esc(e.result)}</pre></details></div>"
        )
    return "".join(steps)


def _render_answer(result: AgentResult) -> str:
    if result.diagnosis is not None:
        d = result.diagnosis
        cites = "".join(f"<li>{_esc(c)}</li>" for c in d.evidence) or "<li class='muted'>none</li>"
        return (
            "<h2>Diagnosis</h2>"
            f"<p><strong>Root cause.</strong> {_esc(d.root_cause)}</p>"
            f"<p><strong>Confidence.</strong> {d.confidence:.2f}</p>"
            f"<p><strong>Recommended fix.</strong> {_esc(d.recommended_fix)}</p>"
            f"<p><strong>Cited evidence (verified).</strong></p><ul>{cites}</ul>"
        )
    if result.escalation is not None:
        e = result.escalation
        got = "".join(f"<li>{_esc(c)}</li>" for c in e.evidence_gathered)
        got = got or "<li class='muted'>none</li>"
        steps = "".join(f"<li>{_esc(s)}</li>" for s in e.suggested_next_steps)
        return (
            "<h2>Escalation</h2>"
            f"<p><strong>Reason.</strong> {_esc(e.reason)}</p>"
            f"<p><strong>Evidence gathered (verified).</strong></p><ul>{got}</ul>"
            f"<p><strong>Suggested next steps.</strong></p><ul>{steps}</ul>"
        )
    return ""


def _render_citation_report(result: AgentResult) -> str:
    report = result.citation_report
    if report is None:
        return ""
    dropped = "".join(f"<li>{_esc(c)}</li>" for c in report.dropped)
    dropped_block = (
        f"<p class='muted'>Dropped as ungrounded:</p><ul>{dropped}</ul>" if report.dropped else ""
    )
    rate = report.fabrication_rate
    return (
        "<h2>Citation verification</h2>"
        f"<p>{report.checked} generated, {report.kept} kept"
        f"{'' if rate is None else f', fabrication rate {rate:.0%}'}.</p>"
        f"{dropped_block}"
    )


@app.get("/scenarios/{scenario_id}", response_class=HTMLResponse)
def scenario_detail(scenario_id: str) -> HTMLResponse:
    view = _catalog().get(scenario_id)
    if view is None:
        raise HTTPException(status_code=404, detail=f"unknown scenario {scenario_id!r}")
    s = view.scenario
    gt = s.ground_truth

    trace_section = "<p class='muted'>No cached run for this scenario.</p>"
    answer_section = ""
    citation_section = ""
    if view.run and view.run.result:
        trace_section = _render_trace(view.run.result)
        answer_section = _render_answer(view.run.result)
        citation_section = _render_citation_report(view.run.result)
    elif view.run and view.run.error:
        trace_section = f"<pre>{_esc(view.run.error)}</pre>"

    judge_section = ""
    if view.judgement:
        j = view.judgement
        grade = _grade_badge(j.root_cause_grade) or _esc(j.root_cause_grade)
        judge_section = (
            "<h2>Judge verdict</h2>"
            f"<p><strong>Root cause:</strong> {grade} &nbsp; "
            f"<strong>Escalation call:</strong> {_esc(j.escalation_call or 'n/a')}</p>"
            f"<p>{_esc(j.reasoning)}</p>"
        )

    body = (
        "<p><a href='/'>&larr; all scenarios</a></p>"
        f"<h1>{_esc(s.id)} &mdash; {_esc(s.title)}</h1>"
        f"<p class='muted'>{_esc(s.category.value)} &middot; {_esc(s.difficulty.value)} &middot; "
        f"<a href='{_esc(s.source_url)}'>source postmortem</a></p>"
        "<h2>Incident report</h2>"
        f"<pre>{_esc(s.incident_report)}</pre>"
        "<h2>Investigation trace</h2>"
        f"{trace_section}"
        f"{answer_section}"
        f"{citation_section}"
        f"{judge_section}"
        "<h2>Ground truth</h2>"
        "<details><summary>reveal</summary>"
        f"<p><strong>Root cause.</strong> {_esc(gt.root_cause)}</p>"
        f"<p><strong>Fix.</strong> {_esc(gt.fix)}</p>"
        f"<p><strong>Should escalate.</strong> {gt.should_escalate}</p></details>"
    )
    return _page(f"{s.id} — {s.title}", body)


@app.exception_handler(HTTPException)
def _http_exc(_request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
