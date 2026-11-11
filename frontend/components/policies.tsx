'use client';

import { ArrowRight, Check, CircleSlash, Eye, Fingerprint, KeyRound, LockKeyhole, Pause, ShieldCheck, TerminalSquare } from 'lucide-react';
import { useConsoleData } from '@/lib/use-console';
import { Shell } from './shell';
import { ConnectionNotice, SectionTitle } from './ui';

const rules = [
  { number: '01', name: 'Screen untrusted instructions', endpoint: 'Guard / injection', icon: ShieldCheck, text: 'An explicitly benign verdict continues to privacy screening. Detected injection is blocked. Unknown, missing, or malformed results hold the run.', decision: 'BLOCK / HOLD', tone: 'rose' },
  { number: '02', name: 'Minimize the agent’s context', endpoint: 'Protect / pii', icon: Eye, text: 'Only the anonymized text returned by Clocked is forwarded. If that output is absent or invalid, the original document is withheld.', decision: 'REDACT / HOLD', tone: 'mint' },
  { number: '03', name: 'Inspect proposed scripts', endpoint: 'Inspect / script', icon: TerminalSquare, text: 'A malicious script is blocked. Suspicious or unknown results are held. A benign classification still requires an authorized, allowlisted action.', decision: 'BLOCK / HOLD', tone: 'rose' },
  { number: '04', name: 'Authorize at the tool boundary', endpoint: 'Trusted backend / policy', icon: KeyRound, text: 'The gateway validates capabilities and tool arguments independently. Only allowlisted simulations exist, and authorization is bound to the original action content.', decision: 'ALLOW / BLOCK', tone: 'blue' },
];

export function Policies() {
  const data = useConsoleData();
  return <Shell health={data.health} loading={data.loading}><SectionTitle title="Enforcement policies" aside={<span className="policy-readonly"><LockKeyhole size={14} />Server enforced · Read only</span>}>Classifications inform the decision. The trusted gateway controls execution.</SectionTitle><ConnectionNotice message={data.error} retry={() => { void data.refresh(); }} />
    <div className="policy-banner"><div className="policy-banner-icon"><ShieldCheck size={28} /></div><div><h2>No result is never an approval</h2><p>If a security check fails, times out, or returns an unknown verdict, execution is held. The agent and browser cannot override this boundary.</p></div><span><LockKeyhole size={15} /> Fail-closed</span></div>
    <div className="policy-rule-list">{rules.map((rule) => <article key={rule.number} className="policy-rule panel"><span className={`policy-icon accent-${rule.tone}`}><rule.icon size={22} /></span><div className="policy-rule-content"><span className="mini-label">{rule.endpoint}</span><h2>{rule.name}</h2><p>{rule.text}</p></div><span className={`policy-decision accent-${rule.tone}`}>{rule.decision}</span></article>)}</div>
    <div className="policy-bottom-grid"><section className="panel policy-reference"><div className="panel-header"><div><LockKeyhole size={16} /><h2>Decision reference</h2></div></div><div className="decision-reference-row"><span className="decision-icon mint"><Check size={16} /></span><strong>Allow</strong><p>Checks passed and the tool is authorized.</p></div><div className="decision-reference-row"><span className="decision-icon mint"><Eye size={16} /></span><strong>Redact</strong><p>Only the returned anonymized copy continues.</p></div><div className="decision-reference-row"><span className="decision-icon rose"><CircleSlash size={16} /></span><strong>Block</strong><p>A threat or unauthorized action was denied.</p></div><div className="decision-reference-row"><span className="decision-icon amber"><Pause size={16} /></span><strong>Hold</strong><p>Execution awaits a valid security decision.</p></div></section><section className="panel policy-boundaries"><Fingerprint size={24} /><h2>Deliberately bounded.</h2><p>Airlock is an enforcement workbench for synthetic scenarios. Agents and tools are deterministic simulations; security checks call Clocked live.</p><ul><li><Check size={13} /> Server-owned inputs and capability allowlists</li><li><Check size={13} /> No shell execution or external messages</li><li><Check size={13} /> API credentials stay in the backend</li><li><Check size={13} /> Audit trails preserve actual outcomes</li></ul><div className="policy-limitation">Detectors can make mistakes. A benign result does not grant unrestricted permissions.</div></section></div>
  </Shell>;
}
