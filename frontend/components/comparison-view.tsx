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
  return <div className="pipeline"><div className="pipeline-label"><span><LockKeyhole size={14} /> Enforcement Pipeline</span><span>Fail-closed</span></div><div className="pipeline-steps">{steps.map((step, index) => {
    const check = run?.checks.find((entry) => entry.endpoint === step.endpoint);
    const needed = scenario.endpoints.includes(step.endpoint);
    const label = check ? (check.outcome ?? (check.status === 'error' ? 'HOLD' : 'Received')) : run?.completed_at ? (needed ? 'Not reached' : 'Not required') : (needed ? 'Awaiting check' : 'Not required');
    return <div className="pipeline-step-wrap" key={step.endpoint}><div className={`pipeline-step ${check ? `step-${check.outcome?.toLowerCase() ?? 'received'}` : ''} ${!needed ? 'step-optional' : ''}`}><span className="pipeline-icon"><step.icon size={20} /></span><strong>{endpointNames[step.endpoint]}</strong><span className="pipeline-description">{step.description}</span><span className="pipeline-status">{check?.outcome === 'ALLOW' || check?.outcome === 'REDACT' ? <Check size={12} /> : check?.outcome === 'BLOCK' ? <CircleSlash size={12} /> : <span className="tiny-dot" />}{label}</span></div>{index < steps.length - 1 && <ArrowRight size={14} className="pipeline-arrow" />}</div>;
  })}</div></div>;
}

export function ComparisonView({ baseline, protectedRun, scenario }: { baseline: Run | null; protectedRun: Run | null; scenario: Scenario }) {
  const baselineEffect = (baseline?.tool_result?.effect as string) || (baseline?.action_executed ? 'Unshielded action executed' : 'Waiting for comparison');
  const protectedEffect = (protectedRun?.tool_result?.effect as string) || (protectedRun?.action_executed ? 'Authorized action executed' : protectedRun ? 'Execution prevented at security boundary' : 'Execution awaits classification');

  return <div className="comparison-area"><SecurityPipeline run={protectedRun} scenario={scenario} /><div className="comparison-grid">
    <article className="comparison-card baseline-card"><div className="comparison-heading"><span><ShieldOff size={16} />Without Airlock</span><span className="micro-tag">Baseline</span></div><div className="comparison-result"><StatusBadge status={baseline?.status ?? null} /><h3>{baseline ? 'Unscreened agent context' : 'No security checkpoint'}</h3><p>{baseline ? scenario.baseline_consequence : 'Untrusted external content reaches the agent directly without security screening.'}</p></div><div className="comparison-action"><TerminalSquare size={15} /><span>{baselineEffect}</span></div><div className="simulation-label">Unshielded agent execution · direct tool invocation</div></article>
    <article className={`comparison-card protected-card result-${protectedRun?.status.toLowerCase() ?? 'pending'}`}><div className="comparison-heading"><span><AirlockMark small />With Airlock</span><span className="micro-tag mint-tag">Protected</span></div><div className="comparison-result"><StatusBadge status={protectedRun?.status ?? null} /><h3>{protectedRun ? protectedRun.status === 'RUNNING' ? 'Checks in progress' : humanReason(protectedRun.reason) : 'Inspect. Decide. Enforce.'}</h3><p>{protectedRun ? protectedRun.status === 'RUNNING' ? 'The gateway is running live Clocked checks before authorizing any tool action.' : protectedRun.status === 'BLOCK' ? 'The gateway blocked this run. Zero tool actions authorized; exfiltration and malicious execution prevented.' : protectedRun.status === 'HOLD' ? 'Execution is held. A missing or uncertain security result cannot authorize an action.' : protectedRun.status === 'REDACT' ? 'The agent received the anonymized copy. The sanitized record was committed to the database.' : 'The checks passed and the gateway authorized the tool action in the isolated execution environment.' : 'Clocked classifications determine whether content and tool actions can continue.'}</p></div><div className="comparison-action"><LockKeyhole size={15} /><span>{protectedEffect}</span></div><div className="simulation-label">{protectedRun?.latency_ms != null ? `${numberLabel(protectedRun.latency_ms)} ms total · ` : ''}Live Clocked checks · Real tool execution</div></article>
  </div><div className="boundary-caption"><ShieldCheck size={15} /><span>The browser and agent cannot authorize their own actions.</span></div></div>;
}
