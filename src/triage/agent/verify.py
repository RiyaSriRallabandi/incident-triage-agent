"""Post-hoc citation verification.

The agent generates citations for its final answer, but ~45% of them do not trace
back to anything it actually retrieved (measured in the ablation report). This
step checks every citation against the evidence trace and drops the ones that
fail, so the delivered output is grounded by construction. The drop is recorded,
not hidden - the number of removed citations *is* the fabrication metric.

Deterministic, no LLM call.
"""

from __future__ import annotations

from triage.agent.state import AgentResult, CitationReport, EvidenceItem
from triage.grounding import GROUNDING_THRESHOLD, grounding_score


def _sources(evidence: list[EvidenceItem]) -> list[str]:
    return [e.result for e in evidence]


def verify_citations(
    citations: list[str], evidence: list[EvidenceItem], *, threshold: float = GROUNDING_THRESHOLD
) -> tuple[list[str], CitationReport]:
    sources = _sources(evidence)
    kept: list[str] = []
    dropped: list[str] = []
    for citation in citations:
        (kept if grounding_score(citation, sources) >= threshold else dropped).append(citation)
    return kept, CitationReport(checked=len(citations), kept=len(kept), dropped=dropped)


def verify_result(result: AgentResult) -> AgentResult:
    """Return a copy of ``result`` with ungrounded citations removed and a report attached."""
    if result.diagnosis is not None:
        kept, report = verify_citations(result.diagnosis.evidence, result.evidence)
        verified = result.model_copy(deep=True)
        verified.diagnosis.evidence = kept
        verified.citation_report = report
        return verified

    if result.escalation is not None:
        kept, report = verify_citations(result.escalation.evidence_gathered, result.evidence)
        verified = result.model_copy(deep=True)
        verified.escalation.evidence_gathered = kept
        verified.citation_report = report
        return verified

    return result
