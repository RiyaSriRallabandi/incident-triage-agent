An incident-triage agent reached a wrong conclusion. Given its full investigation
trace and the ground truth, identify the single stage where the investigation
first went wrong.

INCIDENT REPORT
$incident_report

GROUND-TRUTH ROOT CAUSE
$ground_truth_cause

GROUND-TRUTH EVIDENCE PATH
$ground_truth_path

AGENT TRACE (each step: reasoning, tool call, result)
$trace

AGENT'S CONCLUSION
$conclusion

Classify the first failure stage:
- "missing_tool_call": the agent never gathered a piece of evidence it needed
  (e.g. never checked deploys, never looked at the key service's logs).
- "wrong_tool_args": it called the right tool but with arguments that missed the
  relevant data (wrong service, wrong time window, wrong query terms).
- "misread_evidence": it had the right evidence in hand but drew the wrong
  conclusion from it.
- "wrong_synthesis": it gathered enough evidence but combined it into the wrong
  overall story.
- "premature_conclusion": it concluded before gathering enough evidence, when
  more was available and within budget.
- "other": none of the above fits.

Give one or two sentences of reasoning, then the stage.
