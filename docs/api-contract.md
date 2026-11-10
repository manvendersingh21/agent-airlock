# Agent Airlock v1 contract

Canonical models: `backend/airlock/models.py` and `frontend/lib/types.ts`.
Use these without inventing response envelopes. All data is synthetic. All tools
are deterministic in-memory simulations. Protected checks always use live Clocked.

| Route | Response |
|---|---|
| GET /healthz | `{status: "ok", clocked_configured: boolean, mode: "live"}` |
| GET /api/scenarios | `Scenario[]`, server-owned fixtures |
| POST /api/runs | `Run`, HTTP 202; starts asynchronous processing |
| GET /api/runs | `Run[]`, most recent first, at most 100 |
| GET /api/runs/{id} | `Run` |
| GET /api/runs/{id}/events | SSE: `event: trace`, `id: <integer>`, JSON TraceEvent; then `event: complete`, JSON Run; replay persisted events on connection, honor Last-Event-ID |
| GET /api/metrics | `Metrics`; no fabricated counters, absent measurements are null |
| GET /api/reviews | `Run[]` in HOLD; requires `Authorization: Bearer <AIRLOCK_REVIEW_TOKEN>` |
| POST /api/reviews/{id}/resolve | `Run`; authenticated; body ReviewResolution; revalidate action digest and live checks before any approval can execute |

POST /api/runs accepts only `{scenario_id, mode}`. Unknown fields return 422.
Unknown IDs return 404. No public direct tool endpoint. Never accept an approved
verdict or proposed action from the browser. Unsupported modes never enable mocks.
An additional `security_unavailable` fixture deliberately injects an unavailable
adapter; both trace and UI label it a failure drill, not an observed API outage.

Adapter contract: `ClockedAdapter()` loads backend environment; async
`check_injection(text) -> Check`, `redact_personal_data(text) -> Check`,
`inspect_script(script) -> Check`, and `aclose()`. The adapter validates response
shape, records exact raw JSON (no headers/secrets), and returns errors as Check
with status='error', error='security_check_unavailable' or
'invalid_security_response'. It does not invent verdicts. The policy sets outcome.
Export `UnavailableAdapter` with the same interface for the explicit failure drill.

Policy: only exact verified benign labels allow continuation. A missing/unknown
verdict or failed check is HOLD. Malicious labels BLOCK. PII must have a string
anonymized_text; only that text reaches the protected agent. Capabilities and tool
arguments must pass a separate allowlist. Bind authorization to canonical action
digest immediately before simulation. No subprocess, eval, exec, or real outbound
message APIs in runtime. Review is never a bypass for a failed security check.

Evidence is only extracted from API-reported spans; preserve original offsets.
Browser uses Array.from(text) for Unicode code-point indexing. Raw response is
always expandable if no safe structured spans are recognized.

Metric average is measured wall-clock latency per successful API check; count
checks actually attempted; aggregate credits/cost only when supplied by Clocked.
Baseline runs do not contribute to protected outcome or Clocked usage metrics.
