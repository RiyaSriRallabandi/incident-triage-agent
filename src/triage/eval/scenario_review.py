"""Automated first-pass review of scenario specs.

Runs each spec through a skeptical-SRE rubric (the same eight checks a human
reviewer applies) using the Groq judge model, and returns a structured verdict
per check. This is a data-QA gate, not a replacement for human sign-off: it
flags, a person confirms.

The rubric here is also the seed for the Task 8 LLM-judge.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Literal

from langchain_core.language_models import BaseChatModel
from pydantic import BaseModel, Field

from triage.ingest.evidence import METRIC_NOISE, ScenarioSpec, generate_scenario
from triage.llm import get_judge_model, with_structured_output

# (id, description) for each check. Order matches the human review checklist.
REVIEW_CHECKS: list[tuple[str, str]] = [
    (
        "report_realistic",
        "The incident_report reads like a real on-call page and does not itself "
        "give away the root cause.",
    ),
    (
        "signal_points_to_cause",
        "The signal log lines, deploys, and metric shapes together point to the "
        "stated root cause, and nothing essential to reach it is missing.",
    ),
    (
        "deploy_presence_correct",
        "A deploy appears in the evidence if and only if a deploy is actually part "
        "of the root cause - EXCEPT for an ambiguous scenario, where a deploy may "
        "appear as a plausible-but-unconfirmed candidate cause the agent must weigh.",
    ),
    (
        "metrics_match_story",
        "Each metric's baseline, incident value, and timing are consistent with the "
        "incident narrative and the ground truth.",
    ),
    (
        "root_cause_correct",
        "ground_truth.root_cause is technically correct and is the best explanation "
        "of the evidence. For an ambiguous scenario, 'undetermined' is correct only "
        "if the evidence genuinely fails to localize a cause.",
    ),
    (
        "evidence_path_supported",
        "Every item in ground_truth.evidence_path is directly supported by a "
        "specific signal line, deploy, or metric in the scenario.",
    ),
    (
        "fix_sensible",
        "ground_truth.fix is a reasonable remediation and follow-up for the stated root cause.",
    ),
    (
        "escalation_flag_correct",
        "ground_truth.should_escalate is true exactly when the evidence is "
        "insufficient for a confident root cause.",
    ),
]


class CheckResult(BaseModel):
    check: str = Field(description="The check id from the rubric.")
    verdict: Literal["pass", "flag"]
    reason: str = Field(description="One or two sentences justifying the verdict.")


class ScenarioReview(BaseModel):
    scenario_id: str
    overall: Literal["pass", "needs_changes"]
    summary: str = Field(description="Two or three sentences on the scenario's soundness.")
    checks: list[CheckResult]

    def flags(self) -> list[CheckResult]:
        return [c for c in self.checks if c.verdict == "flag"]


def render_spec_for_review(spec: ScenarioSpec) -> str:
    """A compact, readable rendering of everything a reviewer needs to judge."""
    scenario = generate_scenario(spec)
    distractor_count = len(scenario.synthetic_logs) - len(spec.signal_lines)
    start = spec.incident_start

    def at(offset_s: int) -> str:
        return (start + timedelta(seconds=offset_s)).strftime("%H:%M:%S")

    lines = [
        f"id: {spec.id}",
        f"category: {spec.category}   difficulty: {spec.difficulty}",
        f"source_url: {spec.source_url}",
        f"source_note: {spec.source_note}",
        "",
        f"incident_report:\n  {spec.incident_report}",
        "",
        f"incident_start: {start.isoformat()}",
        f"detected: {at(spec.detected_offset_s)} (+{spec.detected_offset_s}s)",
        "",
        "signal_lines (the real evidence; everything else in the logs is noise):",
    ]
    for s in spec.signal_lines:
        lines.append(f"  {at(s.offset_s)}  {s.service:16s} {s.level:8s} {s.msg}")

    lines.append("")
    lines.append(f"deploys ({len(spec.deploys)}):")
    for d in spec.deploys:
        lines.append(f"  {at(d.offset_s)}  {d.service}  {d.commit}  {d.summary}")
    if not spec.deploys:
        lines.append("  (none)")

    lines.append("")
    lines.append(
        f"metrics (each sample carries ~{METRIC_NOISE:.0%} random noise; "
        "judge trend, not sample-to-sample wobble):"
    )
    for m in spec.metrics:
        lines.append(
            f"  {m.service}/{m.name} ({m.unit}): baseline {m.baseline} -> "
            f"incident value {m.spike}, moving at {at(m.spike_at_offset_s)} over {m.ramp_s}s"
        )

    gt = spec.ground_truth
    lines += [
        "",
        f"generated log volume: {len(scenario.synthetic_logs)} lines "
        f"({len(spec.signal_lines)} signal + {distractor_count} distractor)",
        "",
        "GROUND TRUTH",
        f"  root_cause: {gt.root_cause}",
        f"  should_escalate: {gt.should_escalate}",
        "  evidence_path:",
    ]
    lines += [f"    - {step}" for step in gt.evidence_path] or ["    (empty)"]
    lines.append(f"  fix: {gt.fix}")
    return "\n".join(lines)


def build_review_prompt(spec: ScenarioSpec) -> str:
    checklist = "\n".join(f"{i}. [{cid}] {desc}" for i, (cid, desc) in enumerate(REVIEW_CHECKS, 1))
    return (
        "You are a skeptical senior SRE reviewing a synthetic incident scenario that "
        "will be used to evaluate an incident-triage agent. The scenario's ground "
        "truth must be correct and fully supported by its evidence. Be critical: if a "
        "check is only partially satisfied, mark it 'flag' and explain what is off.\n\n"
        "Apply each check and return a verdict of 'pass' or 'flag' with a short reason. "
        "Set overall to 'needs_changes' if any check is flagged, otherwise 'pass'.\n\n"
        f"CHECKS\n{checklist}\n\n"
        f"SCENARIO\n{render_spec_for_review(spec)}\n"
    )


def review_scenario(spec: ScenarioSpec, *, model: BaseChatModel | None = None) -> ScenarioReview:
    model = model or get_judge_model()
    structured = with_structured_output(model, ScenarioReview)
    review = structured.invoke(build_review_prompt(spec))
    review.scenario_id = spec.id
    return review
