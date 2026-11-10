import { ArrowUpRight, CheckCheck, FileWarning, ScanFace, TerminalSquare, Unplug } from 'lucide-react';
import type { Scenario } from '@/lib/types';

const icons = { injection: FileWarning, privacy: ScanFace, script: TerminalSquare, benign: CheckCheck, failure: Unplug };
const labels = { injection: 'PROMPT INJECTION', privacy: 'PERSONAL DATA', script: 'UNSAFE SCRIPT', benign: 'SAFE OPERATION', failure: 'FAILURE DRILL' };

export function ScenarioSelector({ scenarios, selected, onSelect, disabled }: { scenarios: Scenario[]; selected: string; onSelect: (id: string) => void; disabled: boolean }) {
  const normal = scenarios.filter((scenario) => scenario.category !== 'failure');
  const failure = scenarios.find((scenario) => scenario.category === 'failure');
  return <section className="scenario-section"><div className="section-caption"><div><span className="step-number">01</span><h2>Choose a scenario</h2><span className="caption-note">Synthetic data. Real security decisions.</span></div>{failure && <button disabled={disabled} onClick={() => onSelect(failure.id)} className={`text-button failure-button ${selected === failure.id ? 'selected' : ''}`}><Unplug size={13} /> Test an outage <ArrowUpRight size={12} /></button>}</div>
    <div className="scenario-grid">{normal.map((scenario, index) => { const Icon = icons[scenario.category]; return <button disabled={disabled} onClick={() => onSelect(scenario.id)} key={scenario.id} className={`scenario-card category-${scenario.category} ${selected === scenario.id ? 'selected' : ''}`} aria-pressed={selected === scenario.id}><div className="scenario-card-top"><span className="scenario-icon"><Icon size={20} strokeWidth={1.6} /></span><span className="scenario-index">0{index + 1}</span></div><strong>{scenario.title}</strong><span className="scenario-subtitle">{scenario.subtitle}</span><div className="scenario-card-bottom"><span>{labels[scenario.category]}</span><span className="radio-indicator">{selected === scenario.id && <span />}</span></div></button>; })}</div>
  </section>;
}
