import type { Metrics, Run, Scenario, TraceEvent } from './types';

export const API_URL = (process.env.NEXT_PUBLIC_API_URL || (process.env.NODE_ENV === 'development' ? 'http://localhost:8000' : '')).replace(/\/$/, '');
export interface Health { status: string; clocked_configured: boolean; mode: string }

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 15000);
  try {
    const response = await fetch(`${API_URL}${path}`, {
      ...init,
      headers: { 'Content-Type': 'application/json', ...init?.headers },
      signal: controller.signal,
      cache: 'no-store',
    });
    if (!response.ok) {
      let detail = `Gateway returned HTTP ${response.status}`;
      try {
        const body = await response.json();
        if (typeof body.detail === 'string') detail = body.detail;
      } catch { /* retain the actual HTTP status */ }
      throw new Error(detail);
    }
    return await response.json() as T;
  } finally { clearTimeout(timer); }
}

export const api = {
  health: () => request<Health>('/healthz'),
  scenarios: () => request<Scenario[]>('/api/scenarios'),
  metrics: () => request<Metrics>('/api/metrics'),
  runs: () => request<Run[]>('/api/runs'),
  run: (id: string) => request<Run>(`/api/runs/${encodeURIComponent(id)}`),
  createRun: (scenario_id: string, mode: 'baseline' | 'protected') => request<Run>('/api/runs', {
    method: 'POST', body: JSON.stringify({ scenario_id, mode }),
  }),
  outbox: () => request<import('./types').OutboxMessage[]>('/api/system/outbox'),
  tickets: () => request<import('./types').SupportTicket[]>('/api/system/tickets'),
  resetSystem: () => request<{ status: string; cleared: boolean }>('/api/system/reset', { method: 'POST' }),
};

/** Follow real SSE events. Polling recovers a dropped stream without fabricating state. */
export function followRun(initial: Run, onRun: (run: Run) => void, onError: (error: string) => void): () => void {
  let current = initial;
  let closed = false;
  let fetching = false;
  let failures = 0;
  let source: EventSource | undefined;
  let timer: ReturnType<typeof setInterval> | undefined;
  const close = () => {
    closed = true;
    source?.close();
    if (timer) clearInterval(timer);
  };
  const update = (run: Run) => {
    if (closed) return;
    current = run;
    onRun(run);
    if (run.status !== 'RUNNING') close();
  };
  const refresh = async () => {
    if (closed || fetching) return;
    fetching = true;
    try {
      const result = await api.run(current.run_id);
      failures = 0;
      update(result);
    } catch {
      failures++;
      if (failures >= 3) {
        onError('The execution stream disconnected. Refresh to retrieve the recorded run.');
        close();
      }
    } finally { fetching = false; }
  };
  if (initial.status !== 'RUNNING') { onRun(initial); return close; }
  source = new EventSource(`${API_URL}/api/runs/${encodeURIComponent(initial.run_id)}/events`);
  source.addEventListener('trace', (message: MessageEvent<string>) => {
    if (closed) return;
    try {
      const event = JSON.parse(message.data) as TraceEvent;
      if (!current.events.some((entry) => entry.id === event.id)) {
        current = { ...current, events: [...current.events, event].sort((a, b) => a.id - b.id) };
        onRun(current);
      }
      if (event.type === 'check_completed' || event.type === 'completed') void refresh();
    } catch { void refresh(); }
  });
  source.addEventListener('complete', (message: MessageEvent<string>) => {
    try { update(JSON.parse(message.data) as Run); } catch { void refresh(); }
  });
  source.onerror = () => { source?.close(); void refresh(); };
  timer = setInterval(() => { void refresh(); }, 1800);
  return close;
}

export function downloadRun(run: Run): void {
  const objectUrl = URL.createObjectURL(new Blob([JSON.stringify(run, null, 2)], { type: 'application/json' }));
  const link = document.createElement('a');
  link.href = objectUrl;
  link.download = `airlock-${run.run_id}.json`;
  link.click();
  URL.revokeObjectURL(objectUrl);
}
