# Agent Airlock build rules

Use docs/api-contract.md and shared models exactly. This is a fresh project for
the November 10, 2026 Clocked Build Challenge. Deadline: 20:59 Pacific.
Work only within assigned files in your worktree; commit your branch.
Never print or commit credentials. backend/.env is local and ignored.
Never execute proposed scripts or send actual messages. No mocked results in live mode.
Unknown verdicts, failed security checks, and malformed outputs fail closed.
Do not claim detector accuracy or live results without running and recording them.
Run appropriate tests; report changed files, validation, and blockers.

File ownership: orchestrator owns contracts, fixtures, evals, docs, deployment;
Clocked specialist owns clocked_adapter.py, smoke_clocked.py and adapter tests;
gateway engineer owns other backend runtime and policy/gateway/API tests;
frontend designer owns frontend except the frozen lib/types.ts contract.
