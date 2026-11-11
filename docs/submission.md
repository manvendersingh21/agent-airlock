# Agent Airlock — Hackathon Video & Project Submission

**Clocked Build Challenge Submission**

- **Project Name:** Agent Airlock
- **Video File:** `agent-airlock-demo.mp4` (Duration: 1m 23s | Size: 5.1 MB | Format: 720p HD MP4 | Audio: 48kHz Stereo AAC Ambient Score)
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

## 2. Second-by-Second Video Walkthrough & Voiceover Script

> **Audio Note:** The video file (`agent-airlock-demo.mp4`) is muxed with an integrated calm ambient soundscape (48kHz stereo, lush Rhodes & analog pad progression) balanced at a subtle background level so voiceovers or live presentations remain crystal clear over top.

This script matches the exact timing of `agent-airlock-demo.mp4`:

| Timestamp | Screen Action | Voiceover Script |
|:---|:---|:---|
| **0:00 - 0:10** | Camera opens on dashboard hero: "Attack Lab — LIVE CLOCKED INTEGRATION". | *"This is Agent Airlock — the security enforcement gateway between AI agents and the outside world. Autonomous agents shouldn't have unrestricted access to execute tools, leak data, or run arbitrary scripts."* |
| **0:10 - 0:25** | Clicks **Poisoned document** scenario. Document shows hidden prompt injection instructing agent to exfiltrate records to `audit-drop@example.invalid`. Clicks **Run comparison**. | *"Here, an untrusted vendor document contains an indirect prompt injection trying to exfiltrate employee records. Without Airlock, the unshielded agent falls for it and dispatches the message. But with Airlock, Clocked Guard intercepts it in 380 milliseconds, extracts the evidence quotes, and blocks the run."* |
| **0:25 - 0:35** | Scrolls down to **Live Environment State** panel showing SQLite Outbox. | *"Look at our live system outbox: the unshielded baseline leak is logged, while under Airlock protection, zero outbound messages were dispatched. Exfiltration is prevented at the boundary."* |
| **0:35 - 0:50** | Clicks **Privacy leak** scenario (Maya Chen ticket). Clicks **Run comparison**. Toggles **Agent received** tab. | *"Next, a customer support ticket contains raw personal phone numbers and emails. Clocked Protect evaluates the document, strips all customer PII, and replaces them with cryptographic tokens before the agent ever sees it. In our live database, only scrubbed tokens are stored."* |
| **0:50 - 1:00** | Clicks **Legitimate request** scenario (`Get-Date`). Clicks **Run comparison**. | *"Airlock doesn't just block everything. For a legitimate operations check, Guard, Protect, and Inspect all verify safety. Airlock authorizes execution, spawns an isolated subprocess, and returns the real date and timestamp output."* |
| **1:00 - 1:15** | Scrolls to **Interactive Attack Sandbox**. Clicks **DAN / Developer Mode Jailbreak** preset. Clicks **Screen & Enforce**. | *"Judges and developers don't have to take our word for it. In our Interactive Attack Sandbox, you can test any custom prompt. Testing a DAN jailbreak, Clocked Guard catches the persona override and triggers an instant block with exact quote evidence."* |
| **1:15 - 1:20** | Clicks **Support Ticket PII Exposure** preset. Clicks **Screen & Enforce**. | *"Testing sensitive support tickets with SSNs and credit cards, Clocked Protect produces a live visual diff showing deleted PII and sanitized replacement badges."* |
| **1:20 - 1:23** | Scrolls to **Drop-in Agent Reverse Proxy** panel. Shows Python SDK and cURL tabs. | *"Best of all, Airlock provides a drop-in OpenAI-compatible reverse proxy at localhost:8000/v1. Wrap any LangChain or OpenAI agent in two lines of code, and you're instantly protected by Clocked."* |

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
