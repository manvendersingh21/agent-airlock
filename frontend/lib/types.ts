export type Decision = 'ALLOW' | 'REDACT' | 'BLOCK' | 'HOLD';
export type RunStatus = Decision | 'RUNNING' | 'BASELINE';
export interface Action { tool: 'read_document' | 'send_message' | 'propose_script' | 'record_action'; arguments: Record<string, unknown> }
export interface Check {
  endpoint: 'injection' | 'pii' | 'script'; status: 'ok' | 'error'; verdict: string | null;
  outcome: Decision | null; input_text: string; safe_text: string | null;
  evidence: Record<string, unknown>[]; raw: Record<string, unknown>; latency_ms: number;
  model_ms: number | null; credits: number | null; cost_usd: number | null;
  cost_basis: string | null; error: string | null;
}
export interface Scenario {
  id: string; title: string; subtitle: string; category: 'injection' | 'privacy' | 'script' | 'benign' | 'failure';
  description: string; task: string; source_name: string; content: string; script: string | null;
  capabilities: string[]; proposed_action: Action; baseline_consequence: string; expected_protected: string;
  endpoints: string[]; synthetic: boolean;
}
export interface TraceEvent {
  id: number; run_id: string; timestamp: string;
  type: 'received' | 'check_started' | 'check_completed' | 'policy' | 'agent' | 'tool' | 'completed' | 'error' | 'review';
  title: string; detail: string; data: Record<string, unknown>;
}
export interface Run {
  run_id: string; scenario_id: string; mode: 'baseline' | 'protected'; status: RunStatus;
  reason: string; started_at: string; completed_at: string | null; checks: Check[]; events: TraceEvent[];
  action_executed: boolean; agent_input: string | null; proposed_action: Action | null;
  action_digest: string | null; tool_result: Record<string, unknown> | null; baseline_label: string | null;
  latency_ms: number | null; credits: number | null; cost_usd: number | null;
}
export interface Metrics {
  runs: number; protected_runs: number; checks: number; blocked: number; held: number;
  allowed: number; redacted: number; avg_latency_ms: number | null; credits: number | null; cost_usd: number | null;
}
export interface OutboxMessage {
  message_id: string; run_id: string; mode: string; recipient: string;
  body: string; sent_at: string; blocked: boolean;
}
export interface SupportTicket {
  ticket_id: string; run_id: string; mode: string; customer_name: string;
  email: string; phone: string; issue_summary: string; created_at: string; pii_scrubbed: boolean;
}
