'use client';

import { ArrowRight, Check, CircleSlash, Eye, LockKeyhole, ShieldCheck, ShieldOff, TerminalSquare } from 'lucide-react';
import type { Run, Scenario } from '@/lib/types';
import { AirlockMark } from './shell';
import { endpointNames, humanReason, numberLabel, StatusBadge } from './ui';

export function SecurityPipeline({ run, scenario }: { run: Run | null; scenario: Scenario }) {
  const steps = [
    { endpoint: 'injection', icon: ShieldCheck, description: 'Prompt injection' },
    { endpoint: 'pii', icon: Eye, description: 'Personal data' },
    { endpoint: 'script', icon: TerminalSquare, description: 'Script safety' },
  ];
  return <div className="pipeline"><div className="pipeline-label"><span><LockKeyhole size={12} /> TRUSTED ENFORCEMENT GATEWAY</span><span>Fail closed</span></div><div className="pipeline-steps">{steps.map((step, index) => {
    const check = run?.checks.find((entry) => entry.endpoint === step.endpoint);
    const needed = scenario.endpoints.includes(step.endpoint);
    const label = check ? (check.outcome ?? (check.status === 'error' ? 'HOLD' : 'Received')) : run?.completed_at ? (needed ? 'Not reached' : 'Not required') : (needed ? 'Awaiting check' : 'Not required');
    return <div className="pipeline-step-wrap" key={step.endpoint}><div className={`pipeline-step ${check ? `step-${check.outcome?.toLowerCase() ?? 'received'}` : ''} ${!needed ? 'step-optional' : ''}`}><span className="pipeline-icon"><step.icon size={18} /></span><strong>{endpointNames[step.endpoint]}</strong><span className="pipeline-description">{step.description}</span><span className="pipeline-status">{check?.outcome === 'ALLOW' || check?.outcome === 'REDACT' ? <Check size={10} /> : check?.outcome === 'BLOCK' ? <CircleSlash size={10} /> : <span className="tiny-dot" />}{label}</span></div>{index < steps.length - 1 && <ArrowRight size={14} className="pipeline-arrow" />}</div>;
  })}</div></div>;
}

export function ComparisonView({ baseline, protectedRun, scenario }: { baseline: Run | null; protectedRun: Run | null; scenario: Scenario }) {
  return <div className="comparison-area"><SecurityPipeline run={protectedRun} scenario={scenario} /><div className="comparison-grid">
    <article className="comparison-card baseline-card"><div className="comparison-heading"><span><ShieldOff size={15} />Without Airlock</span><span className="micro-tag">BASELINE</span></div><div className="comparison-result"><StatusBadge status={baseline?.status ?? null} /><h3>{baseline ? 'Unscreened agent context' : 'No security checkpoint'}</h3><p>{baseline ? scenario.baseline_consequence : 'The original content reaches the simulated agent without security screening.'}</p></div><div className="comparison-action"><TerminalSquare size={14} /><span>{baseline ? (baseline.action_executed ? 'Simulated tool action recorded' : 'No tool action recorded') : 'Waiting for comparison'}</span></div><div className="simulation-label">Deterministic simulation · no real side effects</div></article>
    <article className={`comparison-card protected-card result-${protectedRun?.status.toLowerCase() ?? 'pending'}`}><div className="comparison-heading"><span><AirlockMark small />With Airlock</span><span className="micro-tag mint-tag">PROTECTED</span></div><div className="comparison-result"><StatusBadge status={protectedRun?.status ?? null} /><h3>{protectedRun ? protectedRun.status === 'RUNNING' ? 'Checks in progress' : humanReason(protectedRun.reason) : 'Inspect. Decide. Enforce.'}</h3><p>{protectedRun ? protectedRun.status === 'RUNNING' ? 'The gateway is waiting for real security results before authorizing any action.' : protectedRun.status === 'BLOCK' ? 'The gateway denied this run. No simulated tool action was authorized.' : protectedRun.status === 'HOLD' ? 'Execution is held. A missing or uncertain security result cannot authorize an action.' : protectedRun.status === 'REDACT' ? 'The agent received the anonymized copy. The authorized action was simulated.' : 'The checks passed and the gateway permitted the authorized simulated action.' : 'Clocked classifications determine whether content and tool actions can continue.'}</p></div><div className="comparison-action"><LockKeyhole size={14} /><span>{protectedRun ? protectedRun.action_executed ? 'Authorized tool action recorded' : 'No tool action executed' : 'Execution awaits classification'}</span></div><div className="simulation-label">{protectedRun?.latency_ms != null ? `${numberLabel(protectedRun.latency_ms)} ms total · ` : ''}Real checks · simulated tools</div></article>
  </div><div className="boundary-caption"><ShieldCheck size={13} /><span>The browser and agent cannot authorize their own actions.</span></div></div>;
}
