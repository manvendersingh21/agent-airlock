# Threat model and limitations

## What the demo tests

An attacker can control an external document or a proposed script. A simulated
agent consumes external content and proposes a limited tool action. The trusted
backend validates both the classification and the action's independent authority
before invoking an allowlisted simulation.

| Threat | Enforcement |
|---|---|
| Instructions embedded in a vendor document | Guard classification gates further processing |
| Unnecessary personal data in a support ticket | Only Protect's anonymized result reaches agent context |
| Dangerous PowerShell remediation | Inspect gates simulation; independent script allowlist remains enforced |
| Service timeout, HTTP error, or unknown verdict | HOLD/BLOCK; no implicit permission |
| Browser submits fabricated verdict or action | Run endpoint accepts only scenario ID and mode |
| Action changed after approval | Canonical action digest checked before execution |
| Unauthorized reviewer | Separate bearer credential required; never published in browser configuration |
| Reviewer tries to bypass unavailable checks | Approval revalidates security checks and action content |

## Trust assumptions

The server process, fixture files, policy code, deployment credentials, and SQLite
database are trusted. This is a single-operator demonstration, not a multi-tenant
authorization system. The public demo should only expose fixed synthetic fixtures.
The reviewer token is distinct from the Clocked key. There is no general-purpose
agent endpoint or arbitrary outbound networking tool.

## Limits on claims

Clocked classifications can be wrong. A benign verdict does not establish that a
document or script is safe. This application combines classification with narrow
capabilities; it does not claim universal prevention of prompt injection, perfect
PII coverage, or containment of a compromised backend.

The agent and tools are deterministic simulations. A baseline “compromise” is an
illustrated outcome, not an observed jailbreak of a real agent model. No script
runs and no message leaves the application. Live Clocked calls and their measured
metadata are real. Unit tests use explicit test doubles; the live benchmark does
not replace failed requests with canned successful results.

The original synthetic input and API evidence are visible to the human operator
and retained in audit history. Protect minimizes the **agent's** context; this
demo does not promise deletion or minimization across the entire audit database.
Use no real customer data. Authentication for private audit records, retention,
encryption policy, and organization-level isolation would be required before
expanding beyond these public synthetic fixtures.

Reference cost values from Clocked are labeled as such; they are not proof of a
billed dollar amount. Timing includes network overhead separately from model time.
The public benchmark is small, hand-written, and not representative of all attacks.
