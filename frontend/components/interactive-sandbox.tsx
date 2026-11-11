'use client';

import { useEffect, useState } from 'react';
import {
  ArrowRight,
  Check,
  CircleSlash,
  Code2,
  Copy,
  Eye,
  FileCode2,
  Fingerprint,
  Info,
  LoaderCircle,
  LockKeyhole,
  Play,
  RotateCcw,
  ShieldAlert,
  ShieldCheck,
  TerminalSquare,
  Zap,
} from 'lucide-react';
import { api } from '@/lib/api';
import type { PresetAttack, ScreenResult } from '@/lib/types';
import { endpointNames, humanReason, numberLabel, StatusBadge } from './ui';

export function InteractiveSandbox() {
  const [presets, setPresets] = useState<PresetAttack[]>([]);
  const [selectedPreset, setSelectedPreset] = useState<string>('dan_override');
  const [text, setText] = useState<string>('');
  const [script, setScript] = useState<string>('');
  const [checkGuard, setCheckGuard] = useState(true);
  const [checkProtect, setCheckProtect] = useState(true);
  const [checkInspect, setCheckInspect] = useState(true);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ScreenResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [proxyTab, setProxyTab] = useState<'python' | 'curl'>('python');
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    async function loadPresets() {
      try {
        const list = await api.presets();
        setPresets(list);
        if (list.length > 0) {
          const first = list[0];
          setSelectedPreset(first.id);
          setText(first.text);
          setScript(first.script || '');
        }
      } catch {
        // fallback presets if backend offline
      }
    }
    void loadPresets();
  }, []);

  function handleSelectPreset(preset: PresetAttack) {
    setSelectedPreset(preset.id);
    setText(preset.text);
    setScript(preset.script || '');
    setResult(null);
    setError(null);
  }

  async function handleScreen() {
    if (!text.trim() && !script.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const res = await api.screen({
        text,
        script: script.trim() ? script : undefined,
        check_guard: checkGuard,
        check_protect: checkProtect,
        check_inspect: checkInspect,
      });
      setResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Screening request failed.');
    } finally {
      setLoading(false);
    }
  }

  function handleCopy(code: string) {
    void navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  const pythonSnippet = `from openai import OpenAI

# Point any agent or SDK to the live Airlock enforcement proxy
client = OpenAI(base_url="http://localhost:8000/v1", api_key="airlock")

try:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": ${JSON.stringify(text || "Your custom prompt or untrusted document")}}],
    )
    print("Airlock Allowed:", response.choices[0].message.content)
except Exception as e:
    print("Airlock Blocked:", e)
`;

  const curlSnippet = `curl -X POST http://localhost:8000/v1/chat/completions \\
  -H "Content-Type: application/json" \\
  -d '{
    "model": "gpt-4o-mini",
    "messages": [
      {"role": "user", "content": ${JSON.stringify(text || "Your custom prompt")}}
    ]
  }'`;

  return (
    <section className="interactive-sandbox-section">
      <div className="sandbox-header">
        <div>
          <h2>Interactive Attack Sandbox</h2>
          <span className="caption-note">
            Test any prompt injection, jailbreak, sensitive PII, or dangerous script live against Clocked.
          </span>
        </div>
      </div>

      <div className="preset-selector">
        <span className="preset-label">Attack presets:</span>
        <div className="preset-chips">
          {presets.map((preset) => (
            <button
              key={preset.id}
              className={`preset-chip ${selectedPreset === preset.id ? 'selected' : ''}`}
              onClick={() => handleSelectPreset(preset)}
            >
              <span>{preset.title}</span>
              <span className={`chip-badge badge-${preset.expected_decision.toLowerCase()}`}>
                {preset.expected_decision}
              </span>
            </button>
          ))}
          <button
            className={`preset-chip ${selectedPreset === 'custom' ? 'selected' : ''}`}
            onClick={() => {
              setSelectedPreset('custom');
              setText('');
              setScript('');
              setResult(null);
            }}
          >
            <span>Custom Scratchpad</span>
          </button>
        </div>
      </div>

      <div className="sandbox-editor-grid">
        <div className="sandbox-input-panel">
          <div className="panel-toolbar">
            <span className="toolbar-title">
              <FileCode2 size={14} /> Content to Inspect
            </span>
            <div className="inspection-toggles">
              <label className="toggle-label">
                <input
                  type="checkbox"
                  checked={checkGuard}
                  onChange={(e) => setCheckGuard(e.target.checked)}
                />
                Guard
              </label>
              <label className="toggle-label">
                <input
                  type="checkbox"
                  checked={checkProtect}
                  onChange={(e) => setCheckProtect(e.target.checked)}
                />
                Protect
              </label>
              <label className="toggle-label">
                <input
                  type="checkbox"
                  checked={checkInspect}
                  onChange={(e) => setCheckInspect(e.target.checked)}
                />
                Inspect
              </label>
            </div>
          </div>

          <textarea
            className="sandbox-textarea"
            rows={7}
            placeholder="Type or paste any prompt, indirect injection, or personal data to screen..."
            value={text}
            onChange={(e) => setText(e.target.value)}
          />

          <div className="script-input-toggle">
            <span className="toolbar-title">
              <TerminalSquare size={14} /> Optional Script Input (PowerShell / Bash)
            </span>
            <input
              type="text"
              className="sandbox-script-input"
              placeholder="e.g. Set-MpPreference -DisableRealtimeMonitoring $true or Get-Date"
              value={script}
              onChange={(e) => setScript(e.target.value)}
            />
          </div>

          <div className="sandbox-actions">
            <button
              className="button button-primary"
              onClick={() => { void handleScreen(); }}
              disabled={loading || (!text.trim() && !script.trim())}
            >
              {loading ? <LoaderCircle size={15} className="spin" /> : <Zap size={14} />}
              {loading ? 'Screening with Clocked…' : 'Screen & Enforce'}
            </button>
            <button
              className="text-button"
              onClick={() => {
                setText('');
                setScript('');
                setResult(null);
              }}
            >
              <RotateCcw size={13} /> Reset
            </button>
          </div>
        </div>

        <div className="sandbox-result-panel">
          <div className="panel-toolbar">
            <span className="toolbar-title">
              <LockKeyhole size={14} /> Airlock Policy Verdict
            </span>
            {result && (
              <span className="latency-pill">
                {numberLabel(result.total_latency_ms)} ms · {result.total_credits} credits
              </span>
            )}
          </div>

          {!result ? (
            <div className="sandbox-empty-result">
              <ShieldCheck size={28} />
              <strong>Awaiting screening</strong>
              <p>Type custom text or select an attack preset on the left, then click Screen & Enforce.</p>
            </div>
          ) : (
            <div className="sandbox-verdict-body">
              <div className={`verdict-banner result-${result.decision.toLowerCase()}`}>
                <div className="verdict-banner-header">
                  <StatusBadge status={result.decision} />
                  <strong>{humanReason(result.reason)}</strong>
                </div>
                <p>
                  {result.decision === 'BLOCK' && 'Threat detected. Gateway withheld the input and aborted execution.'}
                  {result.decision === 'REDACT' && 'Personal data sanitized. Redacted copy authorized for agent forwarding.'}
                  {result.decision === 'ALLOW' && 'All Clocked checks passed. Safe content authorized for execution.'}
                  {result.decision === 'HOLD' && 'Uncertain or missing security classification. Held fail-closed.'}
                </p>
              </div>

              {result.guard && (
                <div className="screen-detail-card">
                  <div className="detail-card-header">
                    <span><ShieldCheck size={14} /> Guard (Prompt Injection)</span>
                    <span className={`mini-badge badge-${result.guard.outcome?.toLowerCase() ?? 'pending'}`}>
                      {result.guard.outcome ?? 'UNKNOWN'}
                    </span>
                  </div>
                  <div className="detail-metric-row">
                    <span>Verdict: <strong>{result.guard.verdict ?? 'none'}</strong></span>
                    <span>Latency: {result.guard.latency_ms.toFixed(1)} ms</span>
                  </div>
                  {result.guard.evidence.length > 0 && (
                    <div className="evidence-quote-box">
                      <span className="mini-label">EVIDENCE QUOTE</span>
                      <p>"{String((result.guard.evidence[0] as { quote?: string }).quote ?? '')}"</p>
                    </div>
                  )}
                </div>
              )}

              {result.protect && (
                <div className="screen-detail-card">
                  <div className="detail-card-header">
                    <span><Eye size={14} /> Protect (PII Sanitization)</span>
                    <span className={`mini-badge badge-${result.protect.outcome?.toLowerCase() ?? 'pending'}`}>
                      {result.protect.outcome ?? 'CLEAN'}
                    </span>
                  </div>
                  {result.redaction_diff.length > 0 ? (
                    <div className="redaction-diff-box">
                      <span className="mini-label">VISUAL REDACTION DIFF</span>
                      <div className="diff-tokens">
                        {result.redaction_diff.map((token, idx) => (
                          <span key={idx} className={`diff-token token-${token.kind}`}>
                            {token.text}{' '}
                          </span>
                        ))}
                      </div>
                    </div>
                  ) : (
                    <div className="detail-metric-row">
                      <span>No unencrypted personal data detected in context.</span>
                    </div>
                  )}
                </div>
              )}

              {result.inspect && (
                <div className="screen-detail-card">
                  <div className="detail-card-header">
                    <span><TerminalSquare size={14} /> Inspect (Script Safety)</span>
                    <span className={`mini-badge badge-${result.inspect.outcome?.toLowerCase() ?? 'pending'}`}>
                      {result.inspect.outcome ?? 'UNKNOWN'}
                    </span>
                  </div>
                  <div className="detail-metric-row">
                    <span>Verdict: <strong>{result.inspect.verdict ?? 'none'}</strong></span>
                    <span>Latency: {result.inspect.latency_ms.toFixed(1)} ms</span>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      <div className="proxy-quickstart-panel">
        <div className="panel-toolbar">
          <div className="quickstart-title">
            <Zap size={15} />
            <strong>Drop-in Agent Reverse Proxy</strong>
            <span className="caption-note">Wrap any LLM agent or framework via localhost:8000/v1</span>
          </div>
          <div className="segmented-control">
            <button
              className={proxyTab === 'python' ? 'selected' : ''}
              onClick={() => setProxyTab('python')}
            >
              Python SDK
            </button>
            <button
              className={proxyTab === 'curl' ? 'selected' : ''}
              onClick={() => setProxyTab('curl')}
            >
              cURL
            </button>
          </div>
        </div>

        <div className="proxy-code-container">
          <pre className="proxy-code-block">
            {proxyTab === 'python' ? pythonSnippet : curlSnippet}
          </pre>
          <button
            className="copy-button"
            onClick={() => handleCopy(proxyTab === 'python' ? pythonSnippet : curlSnippet)}
          >
            {copied ? <Check size={13} /> : <Copy size={13} />}
            {copied ? 'Copied' : 'Copy code'}
          </button>
        </div>
      </div>
    </section>
  );
}
