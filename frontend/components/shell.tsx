'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Activity, ArrowUpRight, BookOpen, ChevronRight, Fingerprint, FlaskConical, Layers3, Menu, PanelLeftClose, Radio, ShieldCheck, SlidersHorizontal, X } from 'lucide-react';
import { useState, type ReactNode } from 'react';
import type { Health } from '@/lib/api';

export function AirlockMark({ small = false }: { small?: boolean }) {
  return <svg aria-hidden="true" width={small ? 22 : 32} height={small ? 22 : 32} viewBox="0 0 32 32" fill="none">
    <path d="M16 2 28 8.5v15L16 30 4 23.5v-15L16 2Z" stroke="currentColor" strokeWidth="1.5" />
    <path d="M11 10v12m10-12v12M11 16h10M16 7v5m0 8v5" stroke="currentColor" strokeWidth="2" />
  </svg>;
}

const links = [
  { path: '/', label: 'Attack Lab', icon: FlaskConical, group: 'workspace' },
  { path: '/events/', label: 'Event Stream', icon: Activity, group: 'workspace' },
  { path: '/investigations/', label: 'Investigations', icon: Fingerprint, group: 'workspace' },
  { path: '/policies/', label: 'Policies', icon: SlidersHorizontal, group: 'configure' },
];

export function Shell({ children, health, loading = false }: { children: ReactNode; health: Health | null; loading?: boolean }) {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);
  const active = links.find((link) => link.path === '/' ? pathname === '/' || pathname.startsWith('/attacks') : pathname.startsWith(link.path.slice(0, -1)));
  return <div className="app-shell">
    {mobileOpen && <button className="sidebar-overlay" aria-label="Close navigation" onClick={() => setMobileOpen(false)} />}
    <aside className={`sidebar ${mobileOpen ? 'open' : ''}`}>
      <Link href="/" className="brand" onClick={() => setMobileOpen(false)}><span className="brand-mark"><AirlockMark /></span><span>AIRLOCK<span className="brand-sub">Agent Security</span></span></Link>
      <button className="icon-button mobile-close" aria-label="Close navigation" onClick={() => setMobileOpen(false)}><X size={18} /></button>
      <div className="workspace-switch"><div className="workspace-icon"><Layers3 size={16} /></div><div>Demo workspace<span>Clocked Build Challenge</span></div><span className="workspace-dot" /></div>
      <div className="nav-label">Workspace</div>
      <nav aria-label="Main navigation">{links.filter((link) => link.group === 'workspace').map((link) => <Link key={link.path} href={link.path} className={`nav-item ${active?.path === link.path ? 'active' : ''}`} onClick={() => setMobileOpen(false)}><link.icon size={18} /><span>{link.label}</span>{active?.path === link.path && <span className="nav-active-dot" />}</Link>)}</nav>
      <div className="nav-label configure-label">Configuration</div>
      <nav aria-label="Configuration">{links.filter((link) => link.group === 'configure').map((link) => <Link key={link.path} href={link.path} className={`nav-item ${active?.path === link.path ? 'active' : ''}`} onClick={() => setMobileOpen(false)}><link.icon size={18} /><span>{link.label}</span></Link>)}</nav>
      <div className="sidebar-bottom">
        <div className="boundary-note"><ShieldCheck size={20} /><strong>Every action has a checkpoint.</strong><p>Real security checks.<br />Simulated tools. Full visibility.</p><Link href="/policies/">Explore the policy <ArrowUpRight size={13} /></Link></div>
        <a className="docs-link" href="https://clocked.rezolve.ai/docs" target="_blank" rel="noreferrer"><BookOpen size={16} /> Clocked documentation <ArrowUpRight size={13} /></a>
        <div className="workspace-user"><span className="user-avatar">AA</span><div>Airlock sandbox<span>Isolated demo environment</span></div></div>
      </div>
    </aside>
    <div className="main-shell">
      <header className="topbar">
        <div className="breadcrumbs"><button className="icon-button mobile-menu" aria-label="Open navigation" onClick={() => setMobileOpen(true)}><Menu size={19} /></button><PanelLeftClose size={17} className="desktop-panel-icon" /><span>Workspace</span><ChevronRight size={13} /><strong>{active?.label ?? 'Security console'}</strong></div>
        <div className="topbar-right"><span className="environment-tag">Sandbox mode</span><span className={`connection-state ${health ? 'connected' : ''}`}><Radio size={13} />{loading ? 'Connecting' : health ? 'Gateway connected' : 'Gateway offline'}</span></div>
      </header>
      <main>{children}</main>
      <footer className="page-footer"><span><AirlockMark small /> The security checkpoint between AI agents and the outside world.</span><span>Powered by <strong>Clocked</strong> <span className="footer-dot">·</span> Guard / Protect / Inspect</span></footer>
    </div>
  </div>;
}
