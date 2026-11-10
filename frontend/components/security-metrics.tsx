import { Activity, Clock3, ScanFace, ShieldBan } from 'lucide-react';
import type { Metrics } from '@/lib/types';
import { numberLabel } from './ui';

export function SecurityMetrics({ metrics }: { metrics: Metrics | null }) {
  const started = metrics && metrics.protected_runs > 0;
  const cards = [
    { label: 'SECURITY CHECKS', value: started ? numberLabel(metrics.checks) : '—', icon: Activity, detail: 'Recorded gateway checks', accent: 'neutral', hint: 'Guard · Protect · Inspect' },
    { label: 'THREATS BLOCKED', value: started ? numberLabel(metrics.blocked) : '—', icon: ShieldBan, detail: 'Protected runs denied', accent: 'rose', hint: 'Enforced by the gateway' },
    { label: 'PRIVACY PROTECTED', value: started ? numberLabel(metrics.redacted) : '—', icon: ScanFace, detail: 'Runs with content redacted', accent: 'mint', hint: 'Only safe text forwarded' },
    { label: 'AVG. CHECK LATENCY', value: metrics?.avg_latency_ms == null ? '—' : numberLabel(metrics.avg_latency_ms), unit: metrics?.avg_latency_ms != null ? 'ms' : '', icon: Clock3, detail: 'Successful API round trips', accent: 'blue', hint: 'Measured, not estimated' },
  ];
  return <section className="metrics-grid" aria-label="Live security metrics">{cards.map((card) => <div className={`metric-card accent-${card.accent}`} key={card.label}><div className="metric-label">{card.label}<card.icon size={16} strokeWidth={1.5} /></div><div className="metric-value">{card.value}<span>{card.unit}</span></div><div className="metric-detail">{card.detail}</div><div className="metric-hint"><span />{card.hint}</div></div>)}</section>;
}
