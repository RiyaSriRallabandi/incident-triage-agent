You are grading an incident-triage agent's root-cause statement against the
verified ground truth. Grade only whether the agent identified the correct cause
and the underlying mechanism - not its wording, length, confidence, or fix.

INCIDENT REPORT
$incident_report

GROUND-TRUTH ROOT CAUSE
$ground_truth_cause

GROUND-TRUTH EVIDENCE PATH
$ground_truth_path

AGENT'S ROOT CAUSE
$agent_cause

The test for "correct": would an on-call engineer, acting only on the agent's
statement, be led to the same fix as the ground truth? Identifying the right
service and the right chain of symptoms is NOT enough if the agent misses or
misstates the *mechanism* that a fix must address.

- "correct": names the same underlying mechanism as the ground truth (e.g.
  "retry amplification exhausted the pool", "a pathological regex saturated CPU",
  "the index subsystem dropped below quorum"), even if briefer or missing a
  cause-of-the-cause detail.
- "partial": right service and right symptom chain, but the mechanism is missing,
  vague, or wrong - so the implied fix would differ from the ground truth. Also
  use this when the agent stops at the symptom ("the service was slow / erroring")
  or blames a plausible-but-incorrect mechanism.
- "incorrect": wrong service, wrong direction of causation, or a mechanism the
  evidence does not support.

Examples of the partial/correct boundary:
- GT: un-budgeted retries amplified load ~5x and exhausted the connection pool.
  "payments latency caused checkout's pool to exhaust" -> partial (no retry
  amplification; implies 'scale the pool' rather than 'add backoff').
  "checkout retried payments with no backoff, ~5x'ing load until the pool
  exhausted" -> correct.
- GT: a deployed WAF rule's backtracking regex saturated CPU.
  "the WAF ruleset deploy caused CPU exhaustion and 502s" -> partial (no regex
  mechanism).
  "a rule in the deployed WAF ruleset had a pathological regex that pinned CPU"
  -> correct.

Give one or two sentences of reasoning, then the grade.
