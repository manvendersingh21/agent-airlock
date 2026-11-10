'use client';

import { useState } from 'react';
import { Activity, ArrowDownToLine, Check, ChevronDown, Code2, FileInput, LoaderCircle, LockKeyhole, ShieldCheck, TerminalSquare } from 'lucide-react';
import type { Check as SecurityCheck, Run, TraceEvent } from '@/lib/types';
import { downloadRun } from '@/lib/api';
import { EvidenceViewer } from './evidence-viewer';
import { EmptyState, endpointNames, StatusBadge, timeLabel } from './ui';

function EventIcon({ type }: { type: TraceEvent['type'] }) {
  const Icon = type === 'received' ? FileInput : type === 'tool' ? TerminalSquare : type === 'policy' ? LockKeyhole : type === 'check_started' ? LoaderCircle : type === 'completed' ? Check : ShieldCheck;
  return <Icon size={15} className={type === 'check_started' ? '' : undefined} />;
}

export function TraceTimeline({ run, compact = false }: { run: Run | null; compact?: boolean }) {
  const [selectedEndpoint, setSelectedEndpoint] = useState<string | null>(null);
  const checks = run?.checks ?? [];
  const selected = checks.find((check) => check.endpoint === selectedEndpoint) ?? checks[checks.length - 1];
  return <section className={`trace-panel panel ${compact ? 'compact' : ''}`}>
    <div className="panel-header"><div><Activity size={16} /><h2>Execution trace</h2>{run && <span className="count-pill">{run.events.length} events</span>}{run?.status === 'RUNNING' && <span className="streaming-label"><span /> Streaming</span>}</div>{run && <button className="text-button" onClick={() => downloadRun(run)}><ArrowDownToLine size={13} /> Export JSON</button>}</div>
    {!run ? <EmptyState title="Every decision leaves a trail" icon={Activity}>Run a scenario to follow the live checks, policy decisions, and actual tool outcome.</EmptyState> : <div className="trace-body"><div className="timeline-list">{run.events.map((event, index) => <details key={event.id} className={`timeline-event type-${event.type}`}><summary><span className="timeline-icon"><EventIcon type={event.type} /></span><span className="event-text"><strong>{event.title}</strong><span>{event.detail}</span></span><time>{timeLabel(event.timestamp)}</time><ChevronDown size={13} /></summary><div className="event-expanded"><div className="mini-label">EVENT {String(index + 1).padStart(2, '0')} <span>{event.type}</span></div><pre>{JSON.stringify(event.data, null, 2)}</pre></div></details>)}{run.status === 'RUNNING' && <div className="timeline-pending"><LoaderCircle size={14} className="spin" /> Awaiting the next gateway event…</div>}</div>
      <aside className="trace-inspector">{checks.length > 0 ? <><div className="inspector-tabs">{checks.map((check: SecurityCheck, index) => <button key={`${check.endpoint}-${index}`} onClick={() => setSelectedEndpoint(check.endpoint)} className={selected === check ? 'selected' : ''}>{endpointNames[check.endpoint]}<span className={`tiny-dot dot-${check.outcome?.toLowerCase() ?? 'pending'}`} /></button>)}</div>{selected && <EvidenceViewer check={selected} />}</> : <div className="inspector-empty"><Code2 size={24} /><strong>{run.mode === 'baseline' ? 'No security checks' : 'Evidence appears here'}</strong><p>{run.mode === 'baseline' ? 'This baseline is a deterministic simulation with no Clocked calls.' : 'Inspect exact endpoint responses as the gateway records them.'}</p></div>}</aside></div>}
    {run && <div className="trace-footer"><span><span className="tiny-dot" />{run.run_id}</span><span>{run.mode === 'baseline' ? 'DETERMINISTIC SIMULATION' : 'GATEWAY AUDIT RECORD'}<StatusBadge status={run.status} small /></span></div>}
  </section>;
}
