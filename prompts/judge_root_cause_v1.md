You are grading an incident-triage agent's root-cause statement against the
verified ground truth. Grade only whether the agent identified the correct cause
and mechanism - not its wording, length, or the fix it proposed.

INCIDENT REPORT
$incident_report

GROUND-TRUTH ROOT CAUSE
$ground_truth_cause

GROUND-TRUTH EVIDENCE PATH
$ground_truth_path

AGENT'S ROOT CAUSE
$agent_cause

Grade:
- "correct": the agent names the same underlying cause and the key mechanism,
  even if briefer or differently worded. Missing minor detail is fine.
- "partial": the agent is on the right track (right service, right symptom, or
  right area) but misses or misstates the actual mechanism, or stops at the
  symptom instead of the cause.
- "incorrect": the agent names a different cause, or a mechanism the evidence
  does not support.

Give one or two sentences of reasoning, then the grade.
