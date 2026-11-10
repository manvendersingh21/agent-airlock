# Three-minute demonstration

Open the app with a reachable live backend. Have the live evaluation report and
source repository ready. Use synthetic inputs only. Verify the expected outcomes
in the current environment before recording; if a detector disagrees, show the
actual result rather than editing the fixture to imply a result that did not occur.

**0:00–0:20 — The boundary.** “Agents read untrusted content and propose actions.
Agent Airlock puts a trusted checkpoint between that content, the agent, and its
tools. The actions here are simulated; the Clocked security calls are live.”

**0:20–1:10 — Poisoned document.** Select the document scenario, show the embedded
instruction, and run the comparison. “The left side illustrates what following
this instruction would do. The right side shows the actual Guard classification
and the policy outcome.” Expand the returned verdict and tool status. “This
classification changes whether processing continues.”

**1:10–1:40 — Privacy.** Run Privacy Leak. Show the original synthetic ticket and
the exact anonymized text delivered to the protected agent. “The technical issue
remains useful, while detected contact details are replaced by Clocked.”

**1:40–2:10 — Script.** Run Dangerous Remediation. Expand Inspect's verdict and
evidence. “The command is inspected before tool simulation. There is no shell
execution path in this application.”

**2:10–2:40 — Useful work and failures.** Run Legitimate Request; show its allowed
read-only simulation. Run Security Unavailable if time permits. “This explicitly
injected outage holds the action. An error never becomes an approval.”

**2:40–3:00 — Proof.** Open the audit history and report. “These are actual response
records, measured timings, and reproducible tests. Detector results and gateway
enforcement are reported separately, including failures and false positives.”

Do not claim a real agent jailbreak, live system modification, universal safety,
or accuracy beyond the included benchmark. Keep the current run visible while
explaining the result; do not substitute screenshots of earlier results.
