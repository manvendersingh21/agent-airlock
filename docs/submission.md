# Agent Airlock — Hackathon Video & Project Submission

**Clocked Build Challenge Submission**

- **Project Name:** Agent Airlock
- **Video File:** `agent-airlock-demo.mp4` (Duration: 1m 23s | Size: 5.1 MB | Format: 720p HD MP4 | Audio: 48kHz Stereo AAC Spoken Voiceover Narration + Calm Ambient Bed)
- **GitHub Repository:** [github.com/manvendersingh21/agent-airlock](https://github.com/manvendersingh21/agent-airlock)
- **Live Server:** `http://127.0.0.1:8000` (FastAPI backend + Next.js console + OpenAI Reverse Proxy)

---

## 1. Quick Copy-Paste Submission Fields

### Short Tagline (under 50 characters)
> The security checkpoint for autonomous AI agents.

### Elevator Pitch (under 200 words)
Autonomous AI agents read untrusted documents, handle sensitive user data, call external APIs, and execute scripts. When an agent is compromised by indirect prompt injection or instructed to run malicious shell commands, existing frameworks fail silently.

**Agent Airlock** is an active security enforcement gateway and interactive attack-replay workbench. Powered by the official Clocked Python SDK (`clocked-sdk==0.7.0`), Airlock sits between agents and external tools. It evaluates interactions in real time using **Clocked Guard** (prompt injection), **Clocked Protect** (PII sanitization), and **Clocked Inspect** (script safety), deterministically applying strict security policies before any unsafe action can execute.

Airlock features a drop-in OpenAI-compatible reverse proxy (`/v1/chat/completions`) that shields any agent framework (LangChain, AutoGen, CrewAI, OpenAI SDK) in two lines of code, an interactive attack sandbox with live token redaction diffs, and real-time verification against a live SQLite outbox and production database.

### Target Prizes
1. **Best Use of Protect, Guard, or Inspect** ($400)
2. **Best Overall App** ($600)

### Built With
`Python`, `FastAPI`, `Clocked SDK (clocked-sdk==0.7.0)`, `Next.js 16`, `React 19`, `TypeScript`, `Tailwind CSS`, `SQLite`, `Playwright`, `Pytest`.

---

## 2. Second-by-Second Video Walkthrough & Spoken Voiceover Narration

> **Audio Note:** `agent-airlock-demo.mp4` features professional, calm neural voiceover narration mixed with sidechain-ducked ambient audio (48kHz stereo AAC). The voiceover is crisp and front-and-center, while the ambient bed rises gently during pauses.

This script matches the exact timing and spoken words in `agent-airlock-demo.mp4`:

| Timestamp | Screen Action | Exact Spoken Voiceover Narration |
|:---|:---|:---|
| **0:00 - 0:07** | Camera opens on dashboard hero: "Attack Lab — LIVE CLOCKED INTEGRATION". | *"This is Agent Airlock, the security enforcement gateway between AI agents and the outside world."* |
| **0:10 - 0:20** | Clicks **Poisoned document** scenario. Document shows hidden prompt injection. Clicks **Run comparison**. | *"When an untrusted document contains an indirect prompt injection, Clocked Guard intercepts it in milliseconds, extracts quote evidence, and enforces a hard block."* |
| **0:24 - 0:32** | Scrolls down to **Live Environment State** panel showing SQLite Outbox. | *"In our live SQLite outbox, the unshielded baseline leaked, while under Airlock protection, zero outbound messages were sent."* |
| **0:34 - 0:45** | Clicks **Privacy leak** scenario (Maya Chen ticket). Clicks **Run comparison**. Toggles **Agent received** tab. | *"Next, a customer ticket contains sensitive contact details. Clocked Protect strips all PII and injects cryptographic tokens before the agent ever sees it."* |
| **0:48 - 0:58** | Clicks **Legitimate request** scenario (`Get-Date`). Clicks **Run comparison**. | *"For legitimate diagnostic requests, Guard, Protect, and Inspect confirm safety, authorizing an isolated sandbox subprocess to return real output."* |
| **0:58 - 1:07** | Scrolls to **Interactive Attack Sandbox**. Clicks **DAN Jailbreak** preset. Clicks **Screen & Enforce**. | *"In our Interactive Attack Sandbox, test any prompt. Testing a DAN jailbreak, Clocked Guard catches the persona override instantly."* |
| **1:08 - 1:15** | Clicks **Support Ticket PII Exposure** preset. Clicks **Screen & Enforce**. | *"Testing sensitive support tickets, Clocked Protect renders a live visual token diff of all scrubbed data."* |
| **1:15 - 1:21** | Scrolls to **Drop-in Agent Reverse Proxy** panel. Shows Python SDK and cURL tabs, then navigates Policies, Event Stream, and Audit views. | *"With a drop-in OpenAI proxy and full audit streaming, this is Agent Airlock."* |

---

## 3. How We Hit Every Judging Rubric Criterion

### Criterion 1: Integration Depth (40 Points)
- **Not a toy wrapper:** Built directly on official `clocked-sdk==0.7.0` using `AsyncClocked`.
- **Drop-in Reverse Proxy (`/v1/chat/completions`):** Real OpenAI-compatible proxy that intercepts requests, enforces Guard/Protect/Inspect, redacts PII before upstream forwarding, and blocks malicious tool calls with standard HTTP 400 error envelopes.
- **Fail-Closed Boundary:** Deterministic policy engine where timeouts, 401/403/429 errors, or unverified classifications automatically hold or block execution—never fail-open.
- **SHA-256 Action Digest:** Tool authorizations are cryptographically bound to the screened content, preventing argument mutation after approval.

### Criterion 2: Meaningful Breadth Across All Three Endpoints (30 Points)
- **Clocked Guard (`AsyncClocked.injection`):** Scans untrusted documents and prompts for indirect prompt injection, persona jailbreaks, and system overrides with `source="content"` and `evidence=True`.
- **Clocked Protect (`AsyncClocked.pii`):** Automatically redacts Names, Emails, Phones, SSNs, and Addresses, outputting `safe_text` and entity offsets.
- **Clocked Inspect (`AsyncClocked.script`):** Screens proposed PowerShell and Bash diagnostic commands, detecting evasive commands (e.g. disabling Windows Defender) before process creation.

### Criterion 3: Practical Usefulness & Execution (20 Points)
- **100% Real E2E System Verification:** Real SQLite Outbox (`outbox_messages`), Real Support Database (`support_tickets`), and Real Subprocess Sandbox Runner (`Get-Date`). Zero synthetic mocks.
- **Interactive Playground:** Live custom prompt scratchpad with 7 attack presets and visual token diffs.
- **Impeccable Design System:** Zero anti-patterns audited by `npx -y impeccable detect` (WCAG AA contrast, clean single-elevation hierarchy, high-contrast typography).

### Criterion 4: Explanation & Reproducibility (10 Points)
- **162 Automated Backend Tests:** `pytest backend/tests` passing in 0.60s.
- **Full Live Benchmark Suite:** 14/14 detector tests and 8/8 gateway expectations passing live on Clocked API (`evals/evaluate.py --live`).
- **Complete Video:** Ready-to-upload `agent-airlock-demo.mp4`.
- **Single-Command Docker Run:** `docker build -t agent-airlock . && docker run -p 8000:8000 -e CLOCKED_API_KEY="..." agent-airlock`.
