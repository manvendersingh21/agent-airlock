'use client';

import { ChevronDown, Code2, FileSearch } from 'lucide-react';
import type { Check } from '@/lib/types';
import { evidenceParts, verifiedSpans } from '@/lib/evidence';
import { endpointNames, numberLabel, StatusBadge } from './ui';

export function EvidenceViewer({ check }: { check: Check }) {
  const verified = verifiedSpans(check.input_text, check.evidence);
  return <div className="evidence-viewer"><div className="evidence-heading"><span><FileSearch size={16} />{endpointNames[check.endpoint]} evidence</span><StatusBadge status={check.outcome} small /></div>
    <dl className="check-facts"><div><dt>Endpoint</dt><dd>/{check.endpoint}</dd></div><div><dt>Raw verdict</dt><dd>{check.verdict ?? (check.endpoint === 'pii' && check.status === 'ok' ? 'Anonymized text returned' : 'Not returned')}</dd></div><div><dt>Round trip</dt><dd>{numberLabel(check.latency_ms)} ms</dd></div><div><dt>Model time</dt><dd>{check.model_ms == null ? 'Not supplied' : `${numberLabel(check.model_ms, 1)} ms`}</dd></div><div><dt>Credits</dt><dd>{numberLabel(check.credits)}</dd></div><div><dt>Cost basis</dt><dd>{check.cost_basis ?? 'Not supplied'}</dd></div></dl>
    {check.error && <div className="evidence-error">{check.error}</div>}
    <div className="mini-label">INSPECTED INPUT {verified.length > 0 && <span>{verified.length} verified span{verified.length === 1 ? '' : 's'}</span>}</div>
    <pre className="evidence-text">{evidenceParts(check.input_text, check.evidence).map((part, index) => part.highlighted ? <mark key={index} title={part.label}>{part.text}</mark> : <span key={index}>{part.text}</span>)}</pre>
    {check.evidence.length > verified.length && <p className="micro-note">Some reported spans do not align with the input. Their original offsets are preserved below without highlights.</p>}
    {check.safe_text != null && <><div className="mini-label">CLOCKED ANONYMIZED OUTPUT</div><pre className="safe-text">{check.safe_text}</pre></>}
    <details className="raw-details"><summary><Code2 size={13} /> Raw Clocked response <ChevronDown size={13} /></summary><pre>{JSON.stringify(check.raw, null, 2)}</pre></details>
  </div>;
}
