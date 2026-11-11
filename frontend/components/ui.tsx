'use client';

import { AlertTriangle, ArrowRight, Check, Circle, LoaderCircle, OctagonX, Pause, RefreshCw, ShieldCheck } from 'lucide-react';
import type { RunStatus } from '@/lib/types';
import type { ReactNode } from 'react';

export const endpointNames: Record<string, string> = { injection: 'Guard', pii: 'Protect', script: 'Inspect' };
export function StatusBadge({ status, small = false }: { status: RunStatus | 'PENDING' | null; small?: boolean }) {
  const normalized = status || 'PENDING';
  const Icon = normalized === 'BLOCK' ? OctagonX : normalized === 'HOLD' ? Pause : normalized === 'RUNNING' ? LoaderCircle : normalized === 'ALLOW' || normalized === 'REDACT' ? Check : Circle;
  const labels: Record<string, string> = { ALLOW: 'Allowed', BLOCK: 'Blocked', HOLD: 'Held', REDACT: 'Redacted', BASELINE: 'Simulation', RUNNING: 'Checking', PENDING: 'Ready' };
  return <span className={`status-badge status-${normalized.toLowerCase()} ${small ? 'small' : ''}`}><Icon size={small ? 11 : 13} className={normalized === 'RUNNING' ? 'spin' : ''} />{labels[normalized]}</span>;
}

export function ConnectionNotice({ message, retry }: { message: string | null; retry: () => void }) {
  if (!message) return null;
  return <div className="notice notice-warning" role="alert"><AlertTriangle size={18} /><div><strong>Gateway connection unavailable</strong><p>{message}</p></div><button className="button button-ghost" onClick={retry}><RefreshCw size={14} /> Reconnect</button></div>;
}

export function EmptyState({ title, children, icon: Icon = ShieldCheck }: { title: string; children: ReactNode; icon?: typeof ShieldCheck }) {
  return <div className="empty-state"><Icon size={32} strokeWidth={1.5} className="empty-icon-inline" /><h3>{title}</h3><p>{children}</p></div>;
}

export function SectionTitle({ eyebrow, title, children, aside }: { eyebrow?: string; title: string; children?: ReactNode; aside?: ReactNode }) {
  return <div className="page-heading"><div><h1>{title}</h1>{children && <p>{children}</p>}</div>{aside}</div>;
}

export function timeLabel(value: string) { return new Date(value).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }); }
export function numberLabel(value: number | null | undefined, digits = 0) { return value == null ? '—' : value.toLocaleString(undefined, { maximumFractionDigits: digits }); }
export function humanReason(value: string) { return value.replace(/_/g, ' ').replace(/^./, (character) => character.toUpperCase()); }
export function SmallArrow() { return <ArrowRight size={14} className="muted" />; }
