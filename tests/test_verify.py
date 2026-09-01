from triage.agent.state import AgentResult, Diagnosis, Escalation, EvidenceItem
from triage.agent.verify import verify_citations, verify_result


def _ev(*results: str) -> list[EvidenceItem]:
    return [
        EvidenceItem(step=i, plan_reasoning="r", tool="search_logs", args={}, result=t)
        for i, t in enumerate(results, 1)
    ]


EVIDENCE = _ev(
    "2026-05-12T13:42:00Z  edge-proxy  7f3a9c1  roll out WAF managed ruleset 2026.05.12",
    "edge-proxy / cpu_utilization_pct: baseline 35 -> max 101, change +186%",
    "2026-05-12T13:42:45Z  waf-engine  ERROR  regex evaluation exceeded 40ms budget on rule 100417",
)


def test_verify_citations_keeps_grounded_drops_fabricated():
    citations = [
        "deploy 7f3a9c1 rolled out the WAF managed ruleset 2026.05.12",  # grounded
        "edge-proxy cpu_utilization_pct climbed to 101 (+186%)",  # grounded
        "a database migration on the orders table locked the schema",  # fabricated
    ]
    kept, report = verify_citations(citations, EVIDENCE)

    assert len(kept) == 2
    assert report.checked == 3
    assert report.kept == 2
    assert report.dropped == ["a database migration on the orders table locked the schema"]
    assert report.fabrication_rate == round(1 / 3, 3)


def test_verify_result_filters_a_diagnosis_and_attaches_the_report():
    result = AgentResult(
        scenario_id="scn_001",
        outcome="diagnosis",
        diagnosis=Diagnosis(
            root_cause="bad WAF rule",
            confidence=0.9,
            evidence=[
                "waf-engine ERROR: regex evaluation exceeded 40ms budget on rule 100417",
                "payments-api replica lag caused checkout timeouts",  # fabricated
            ],
            recommended_fix="roll back",
        ),
        evidence=EVIDENCE,
        tool_calls_used=3,
        hit_budget_cap=False,
    )
    verified = verify_result(result)

    assert verified.diagnosis.evidence == [
        "waf-engine ERROR: regex evaluation exceeded 40ms budget on rule 100417"
    ]
    assert verified.citation_report.checked == 2
    assert verified.citation_report.dropped == ["payments-api replica lag caused checkout timeouts"]
    # original object is untouched
    assert len(result.diagnosis.evidence) == 2


def test_verify_result_filters_an_escalation():
    result = AgentResult(
        scenario_id="scn_004",
        outcome="escalate",
        escalation=Escalation(
            reason="thin evidence",
            evidence_gathered=[
                "edge-proxy cpu_utilization_pct baseline 35",  # grounded
                "an expired TLS certificate on the auth service",  # fabricated
            ],
            suggested_next_steps=["check per-host breakdown"],
        ),
        evidence=EVIDENCE,
        tool_calls_used=4,
        hit_budget_cap=False,
    )
    verified = verify_result(result)
    assert len(verified.escalation.evidence_gathered) == 1
    assert verified.citation_report.kept == 1


def test_verify_result_with_no_citations():
    result = AgentResult(
        scenario_id="scn_001",
        outcome="diagnosis",
        diagnosis=Diagnosis(root_cause="x", confidence=0.5, evidence=[], recommended_fix="y"),
        evidence=EVIDENCE,
        tool_calls_used=1,
        hit_budget_cap=False,
    )
    verified = verify_result(result)
    assert verified.citation_report.checked == 0
    assert verified.citation_report.fabrication_rate is None
