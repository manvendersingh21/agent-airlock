'use client';

import { useEffect, useRef, useState } from 'react';
import { ArrowDown, ArrowRight, Braces, Check, ChevronRight, FileCode2, FlaskConical, Info, LoaderCircle, Play, RotateCcw, ShieldCheck, Unplug } from 'lucide-react';
import { api, followRun } from '@/lib/api';
import type { Run } from '@/lib/types';
import { useConsoleData } from '@/lib/use-console';
import { Shell } from './shell';
import { ConnectionNotice, EmptyState, SectionTitle } from './ui';
import { SecurityMetrics } from './security-metrics';
import { ScenarioSelector } from './scenario-selector';
import { ComparisonView } from './comparison-view';
import { TraceTimeline } from './trace-timeline';
import { SystemStatePanel } from './system-state';
import { InteractiveSandbox } from './interactive-sandbox';

export function AttackLab() {
  const data = useConsoleData();
  const [selected, setSelected] = useState('poisoned_document');
  const [baseline, setBaseline] = useState<Run | null>(null);
  const [protectedRun, setProtectedRun] = useState<Run | null>(null);
  const [starting, setStarting] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);
  const [streamFailed, setStreamFailed] = useState(false);
  const [inputTab, setInputTab] = useState<'source' | 'agent'>('source');
  const [traceTab, setTraceTab] = useState<'protected' | 'baseline'>('protected');
  const watchers = useRef<(() => void)[]>([]);
  const scenario = data.scenarios.find((entry) => entry.id === selected) ?? data.scenarios[0];
  const busy = starting || (!streamFailed && (baseline?.status === 'RUNNING' || protectedRun?.status === 'RUNNING'));

  useEffect(() => () => { watchers.current.forEach((close) => close()); }, []);

  function choose(id: string) {
    watchers.current.forEach((close) => close()); watchers.current = [];
    setSelected(id); setBaseline(null); setProtectedRun(null); setRunError(null); setStreamFailed(false); setInputTab('source');
  }

  async function launch() {
    if (!scenario || busy) return;
    watchers.current.forEach((close) => close()); watchers.current = [];
    setStarting(true); setBaseline(null); setProtectedRun(null); setRunError(null); setStreamFailed(false); setTraceTab('protected');
    const results = await Promise.allSettled([api.createRun(scenario.id, 'baseline'), api.createRun(scenario.id, 'protected')]);
    results.forEach((result, index) => {
      if (result.status === 'rejected') {
        setRunError(result.reason instanceof Error ? result.reason.message : 'The gateway could not create the run.');
        return;
      }
      const setter = index === 0 ? setBaseline : setProtectedRun;
      setter(result.value);
      watchers.current.push(followRun(result.value, (next) => {
        setter(next);
        if (next.status !== 'RUNNING') void data.refresh();
      }, (message) => { setRunError(message); setStreamFailed(true); }));
    });
    setStarting(false);
  }

  const source = scenario ? (scenario.script && scenario.category === 'script' ? scenario.script : scenario.content) : '';
  const visibleText = inputTab === 'agent' ? protectedRun?.agent_input : source;
  return <Shell health={data.health} loading={data.loading}>
    <SectionTitle title="Attack Lab" aside={<span className="live-checks-tag">LIVE CLOCKED INTEGRATION</span>}>Replay an attack. Watch the gateway change what happens next.</SectionTitle>
    <ConnectionNotice message={data.error} retry={() => { void data.refresh(); }} />
    {data.health && !data.health.clocked_configured && <div className="notice notice-warning"><Info size={17} /><div><strong>Clocked credentials are not configured</strong><p>The gateway will hold protected runs until a server-side API key is available.</p></div></div>}
    <SecurityMetrics metrics={data.metrics} />
    {data.loading ? <div className="loading-panel"><LoaderCircle size={19} className="spin" /> Connecting to the enforcement gateway…</div> : !scenario ? <div className="panel"><EmptyState title="Connect the gateway to start" icon={FlaskConical}>The lab loads scenarios and live test cases from the trusted backend. Reconnect above when the service is available.</EmptyState></div> : <>
      <ScenarioSelector scenarios={data.scenarios} selected={scenario.id} onSelect={choose} disabled={busy} />
      <section className="workbench">
        <div className="workbench-toolbar"><div className="workbench-title"><h2>{scenario.title}</h2><span className="toolbar-separator" /><span className="muted">Attack replay</span></div><button className="button button-primary" onClick={() => { void launch(); }} disabled={busy || !data.health}>{busy ? <LoaderCircle size={15} className="spin" /> : baseline || protectedRun ? <RotateCcw size={14} /> : <Play size={14} fill="currentColor" />}{busy ? 'Running comparison' : baseline || protectedRun ? 'Replay scenario' : 'Run comparison'}{!busy && <span className="button-key"><ArrowRight size={13} /></span>}</button></div>
        {scenario.category === 'failure' && <div className="drill-notice"><Unplug size={15} /><strong>Controlled failure drill</strong><span>This deliberately disables the adapter. It is not a real Clocked outage.</span></div>}
        <div className="task-description"><span className="mini-label">AGENT TASK</span><p>{scenario.task}</p></div>
        <div className="workbench-body"><div className="source-area"><div className="source-tabs" role="tablist" aria-label="Content view"><button role="tab" aria-selected={inputTab === 'source'} className={inputTab === 'source' ? 'selected' : ''} onClick={() => setInputTab('source')}><FileCode2 size={14} />Original input</button><button role="tab" aria-selected={inputTab === 'agent'} className={inputTab === 'agent' ? 'selected' : ''} onClick={() => setInputTab('agent')}><ShieldCheck size={14} />Agent received{protectedRun?.status === 'REDACT' && <span className="tiny-dot dot-redact" />}</button></div><div className="source-document"><div className="source-file"><span><FileCode2 size={13} />{inputTab === 'source' ? scenario.source_name : 'protected-agent-context.txt'}</span><span className="micro-tag">UNTRUSTED INPUT</span></div>{visibleText != null ? <div className="source-code">{visibleText.split('\n').map((line, index) => <div className="code-line" key={index}><span className="line-number" aria-hidden="true">{String(index + 1).padStart(2, '0')}</span><span>{line || '\u00a0'}</span></div>)}</div> : <div className="withheld-input"><ShieldCheck size={26} /><strong>{protectedRun?.status === 'BLOCK' || protectedRun?.status === 'HOLD' ? 'Content withheld' : 'No content forwarded yet'}</strong><p>{protectedRun?.status === 'BLOCK' || protectedRun?.status === 'HOLD' ? 'The gateway stopped before this content could enter the agent context.' : 'This view will show the exact text the protected agent receives.'}</p></div>}</div><div className="source-note"><Info size={13} /><span>{inputTab === 'source' ? 'Untrusted external content enters here before reaching the agent.' : 'Only the sanitized text returned by the gateway is delivered to the agent.'}</span></div><div className="expected-outcome"><span className="mini-label">EXPECTED POLICY OUTCOME</span><p>{scenario.expected_protected}</p></div></div><ComparisonView baseline={baseline} protectedRun={protectedRun} scenario={scenario} /></div>
        <div className="workbench-footer"><span><Braces size={13} />Target fixture <ChevronRight size={11} /><code>{scenario.id}</code></span><span><Check size={12} /> Real Clocked screening and tool interception</span></div>
      </section>
      {runError && <div className="notice notice-warning" role="alert"><Info size={17} /><div><strong>Run interrupted</strong><p>{runError}</p></div></div>}
      <div className="trace-section-heading"><div><h2>Follow the decision</h2><span className="caption-note">Evidence, policy, and execution in one place</span></div><div className="segmented-control"><button className={traceTab === 'protected' ? 'selected' : ''} onClick={() => setTraceTab('protected')}>Protected</button><button className={traceTab === 'baseline' ? 'selected' : ''} onClick={() => setTraceTab('baseline')}>Baseline</button></div></div>
      <TraceTimeline run={traceTab === 'protected' ? protectedRun : baseline} />
      <InteractiveSandbox />
      <SystemStatePanel />
      <div className="lab-footnote"><ShieldCheck size={14} /><p>Clocked Guard, Protect, and Inspect checks are live. Tool actions execute with real system enforcement. Detector classifications feed deterministic policy boundaries.</p></div>
    </>}
  </Shell>;
}
