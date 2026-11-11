'use client';

import { useEffect, useState } from 'react';
import { Database, Mail, RefreshCw, RotateCcw, ShieldCheck, ShieldAlert, Check } from 'lucide-react';
import { api } from '@/lib/api';
import type { OutboxMessage, SupportTicket } from '@/lib/types';

export function SystemStatePanel() {
  const [outbox, setOutbox] = useState<OutboxMessage[]>([]);
  const [tickets, setTickets] = useState<SupportTicket[]>([]);
  const [activeTab, setActiveTab] = useState<'outbox' | 'tickets'>('outbox');
  const [loading, setLoading] = useState(false);

  async function loadData() {
    setLoading(true);
    try {
      const [o, t] = await Promise.all([api.outbox(), api.tickets()]);
      setOutbox(o);
      setTickets(t);
    } catch {
      // retain state on background poll
    } finally {
      setLoading(false);
    }
  }

  async function clearAll() {
    await api.resetSystem();
    await loadData();
  }

  useEffect(() => {
    void loadData();
    const interval = setInterval(() => { void loadData(); }, 3000);
    return () => clearInterval(interval);
  }, []);

  return (
    <section className="system-state-panel">
      <div className="system-state-header">
        <div className="system-state-title">
          <Database size={16} />
          <div>
            <h3>Live Environment State</h3>
            <span className="caption-note">Real SQLite Outbox & Database verification</span>
          </div>
        </div>
        <div className="system-state-actions">
          <div className="segmented-control">
            <button
              className={activeTab === 'outbox' ? 'selected' : ''}
              onClick={() => setActiveTab('outbox')}
            >
              <Mail size={13} /> Outbox ({outbox.length})
            </button>
            <button
              className={activeTab === 'tickets' ? 'selected' : ''}
              onClick={() => setActiveTab('tickets')}
            >
              <Database size={13} /> Support DB ({tickets.length})
            </button>
          </div>
          <button className="text-button" onClick={() => { void loadData(); }} title="Refresh live records">
            <RefreshCw size={13} className={loading ? 'spin' : ''} />
          </button>
          <button className="text-button" onClick={() => { void clearAll(); }} title="Clear demo records">
            <RotateCcw size={13} /> Clear
          </button>
        </div>
      </div>

      <div className="system-state-body">
        {activeTab === 'outbox' && (
          <div className="system-records-list">
            {outbox.length === 0 ? (
              <div className="system-empty-state">
                <ShieldCheck size={20} />
                <span>Zero messages in outbox. Protected runs prevent unauthorized outbound communication.</span>
              </div>
            ) : (
              outbox.map((msg) => (
                <div key={msg.message_id} className={`system-record-item mode-${msg.mode}`}>
                  <div className="record-header">
                    <span className="record-recipient">
                      <Mail size={13} />
                      <strong>To:</strong> {msg.recipient}
                    </span>
                    <span className={`badge-pill ${msg.mode === 'baseline' ? 'pill-alert' : 'pill-mint'}`}>
                      {msg.mode === 'baseline' ? <ShieldAlert size={12} /> : <Check size={12} />}
                      {msg.mode === 'baseline' ? 'Unshielded Leak' : 'Authorized'}
                    </span>
                  </div>
                  <div className="record-body">{msg.body}</div>
                  <div className="record-meta">
                    <span>Message ID: <code>{msg.message_id}</code></span>
                    <span>{new Date(msg.sent_at).toLocaleTimeString()}</span>
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'tickets' && (
          <div className="system-records-list">
            {tickets.length === 0 ? (
              <div className="system-empty-state">
                <Database size={20} />
                <span>No support tickets recorded yet. Run the Privacy Leak scenario to see live PII scrubbed.</span>
              </div>
            ) : (
              tickets.map((tkt) => (
                <div key={tkt.ticket_id} className={`system-record-item ${tkt.pii_scrubbed ? 'mode-protected' : 'mode-baseline'}`}>
                  <div className="record-header">
                    <span className="record-recipient">
                      <strong>Customer:</strong> {tkt.customer_name}
                    </span>
                    <span className={`badge-pill ${tkt.pii_scrubbed ? 'pill-mint' : 'pill-alert'}`}>
                      {tkt.pii_scrubbed ? <ShieldCheck size={12} /> : <ShieldAlert size={12} />}
                      {tkt.pii_scrubbed ? 'PII Scrubbed' : 'Raw PII Leaked'}
                    </span>
                  </div>
                  <div className="record-details">
                    <div><strong>Email:</strong> {tkt.email}</div>
                    <div><strong>Phone:</strong> {tkt.phone}</div>
                    <div><strong>Issue:</strong> {tkt.issue_summary}</div>
                  </div>
                  <div className="record-meta">
                    <span>Ticket ID: <code>{tkt.ticket_id}</code></span>
                    <span>{new Date(tkt.created_at).toLocaleTimeString()}</span>
                  </div>
                </div>
              ))
            )}
          </div>
        )}
      </div>
    </section>
  );
}
