import { ArrowUpRight, CheckCheck, FileWarning, ScanFace, TerminalSquare, Unplug } from 'lucide-react';
import type { Scenario } from '@/lib/types';

const icons = { injection: FileWarning, privacy: ScanFace, script: TerminalSquare, benign: CheckCheck, failure: Unplug };
const labels = { injection: 'Prompt injection', privacy: 'Personal data', script: 'Unsafe script', benign: 'Safe operation', failure: 'Failure drill' };

export function ScenarioSelector({ scenarios, selected, onSelect, disabled }: { scenarios: Scenario[]; selected: string; onSelect: (id: string) => void; disabled: boolean }) {
  const normal = scenarios.filter((scenario) => scenario.category !== 'failure');
  const failure = scenarios.find((scenario) => scenario.category === 'failure');
  return <section className="scenario-section"><div className="section-caption"><div><h2>Choose a scenario</h2><span className="caption-note">Synthetic data, real security decisions</span></div>{failure && <button disabled={disabled} onClick={() => onSelect(failure.id)} className={`text-button failure-button ${selected === failure.id ? 'selected' : ''}`}><Unplug size={14} /> Test an outage <ArrowUpRight size={13} /></button>}</div>
    <div className="scenario-grid">{normal.map((scenario) => { const Icon = icons[scenario.category]; return <button disabled={disabled} onClick={() => onSelect(scenario.id)} key={scenario.id} className={`scenario-card category-${scenario.category} ${selected === scenario.id ? 'selected' : ''}`} aria-pressed={selected === scenario.id}><div className="scenario-card-top"><span className="scenario-icon"><Icon size={22} strokeWidth={1.6} /></span><span className="radio-indicator">{selected === scenario.id && <span />}</span></div><strong>{scenario.title}</strong><span className="scenario-subtitle">{scenario.subtitle}</span><div className="scenario-card-bottom"><span>{labels[scenario.category]}</span></div></button>; })}</div>
  </section>;
}
