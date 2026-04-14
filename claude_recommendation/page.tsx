'use client';

import { useState, useCallback } from 'react';

/* ============================================================
   TYPE DEFINITIONS
   ============================================================ */
type PhasePreset = {
  df: number;
  gt: number;
  cb: number;
  label: string;
  note: string;
};

const PHASE_PRESETS: Record<string, PhasePreset> = {
  managed_tension: {
    df: 40, gt: 30, cb: 30,
    label: 'Managed tension',
    note: 'Structural forces dominate. Driving forces 40% — structural pressures explain most variance. Game theory and chessboard balanced at 30% each.',
  },
  maritime_pressure: {
    df: 30, gt: 30, cb: 40,
    label: 'Maritime pressure',
    note: 'Chessboard dominant. Force positioning and chokepoint control determine outcomes. Driving forces reduced as geography becomes the binding constraint.',
  },
  pre_war: {
    df: 25, gt: 40, cb: 35,
    label: 'Pre-war transition',
    note: 'Game theory dominant. Actor rational choice is the marginal variable. Structural forces are baked in — what matters now is who moves first.',
  },
  hybrid_escalation: {
    df: 35, gt: 35, cb: 30,
    label: 'Hybrid escalation',
    note: 'Balanced. Structural and game-theoretic forces equally weighted. Chessboard reduced as positioning is less decisive than signaling.',
  },
  stabilization: {
    df: 45, gt: 25, cb: 30,
    label: 'Negotiated stabilization',
    note: 'Structural forces dominant. Deals are constrained by underlying dependencies, not game moves. Chessboard recedes as kinetics diminish.',
  },
};

/* ============================================================
   WEIGHT RESOLVER
   Derives method weights from system state + force type.
   Mirrors weight_resolver.py in /packages/scenarios/
   ============================================================ */
function resolveWeights(df: number, gt: number, cb: number) {
  const total = df + gt + cb;
  const ndf = Math.round((df / total) * 100);
  const ngt = Math.round((gt / total) * 100);
  const ncb = 100 - ndf - ngt;
  const di = ((Math.abs(ndf - ngt) * 0.0015) + (Math.abs(ngt - ncb) * 0.001)).toFixed(3);
  return { df: ndf, gt: ngt, cb: ncb, di };
}

/* ============================================================
   DATA (replace with API calls in production)
   ============================================================ */
const SCENARIOS = [
  { name: 'Managed confrontation', pct: 17, delta: '+3.1%', dir: 'rise' as const, top: true },
  { name: 'Regional war escalation', pct: 17, delta: '+2.3%', dir: 'rise' as const },
  { name: 'Maritime / infrastructure shock', pct: 17, delta: '+2.2%', dir: 'rise' as const },
  { name: 'Hybrid pressure equilibrium', pct: 16, delta: '+2.1%', dir: 'blue' as const },
  { name: 'Internal fragmentation / rupture', pct: 12, delta: '−2.3%', dir: 'fall' as const },
  { name: 'Controlled partial reopening', pct: 11, delta: '−3.0%', dir: 'fall' as const },
  { name: 'Negotiated stabilization', pct: 10, delta: '−4.4%', dir: 'fall' as const },
];

const ACTORS = [
  { name: 'United States', move: 'Force projection',       conf: 51 },
  { name: 'Iran',          move: 'Coercive signaling',     conf: 54 },
  { name: 'Israel',        move: 'Deterrence maintenance', conf: 64, highlight: true },
  { name: 'Reg. proxies',  move: 'Coercive signaling',     conf: 54 },
  { name: 'Major importers', move: 'Watchful balancing',   conf: 60 },
];

const TAPE = [
  { source: 'Jerusalem Post', text: 'IMF warns Strait of Hormuz might never return to normal traffic levels', time: '23:48', sev: 'high' as const },
  { source: 'Reuters',        text: 'Western powers unable to secure Red Sea — Hormuz will be harder', time: '11:00', sev: 'high' as const },
  { source: 'Moneycontrol',   text: 'US Hormuz blockade to tighten global supply, raise costs for India', time: '12:39', sev: 'high' as const },
  { source: 'Al Jazeera',     text: 'Iran threatens Bab al-Mandeb closure — world trade impact assessed', time: '15:54', sev: 'medium' as const },
  { source: 'Fox News',       text: 'Second chokepoint crisis looms as Houthis threaten Red Sea lane', time: '23:59', sev: 'medium' as const },
  { source: 'Time',           text: 'Bab El-Mandeb: Iran threatens additional trade passage restrictions', time: '16:24', sev: 'medium' as const },
  { source: 'CryptoRank',     text: 'Iran–Israel peace talks unreasonable amid Lebanon strike escalation', time: '05:52', sev: 'medium' as const },
  { source: 'Decode39',       text: 'Italy and Greece drill in Red Sea as Houthi threat looms', time: '12:23', sev: 'low' as const },
];

const ANALYSTS = [
  { initials: 'ME', role: 'Political · Middle East',  text: 'Managed tension with active signaling competition — diplomatic channels fragile.', color: 'rgba(245,158,11,0.15)', textColor: '#f59e0b' },
  { initials: 'EU', role: 'Economist · Europe',       text: 'Guarded systemic risk; shipping & logistics transmission likely persistent.', color: 'rgba(0,136,255,0.15)', textColor: '#60a5fa' },
  { initials: 'US', role: 'Military planner · US',    text: 'Escalation elevated — force-posture uncertainty unresolved.', color: 'rgba(239,68,68,0.15)', textColor: '#ef4444' },
  { initials: 'SA', role: 'Academic · South Asia',    text: 'Trend labels = velocity, not peace/war state. A stable high-tension plateau is still dangerous.', color: 'rgba(0,212,170,0.15)', textColor: '#00d4aa' },
  { initials: 'LV', role: 'Ideology · Levant',        text: 'Narrative competition amplifies safety risk even without battlefield expansion.', color: 'rgba(160,100,255,0.15)', textColor: '#a78bfa' },
];

const MASLOW = [
  { label: 'Safety / conflict',        pct: 32, badge: 'Guarded', cls: 'badge-warn' },
  { label: 'Physiological / energy',   pct: 26, badge: 'Guarded', cls: 'badge-warn' },
  { label: 'Legitimacy / political',   pct: 17, badge: 'Low',     cls: 'badge-muted' },
  { label: 'Future capacity',          pct: 16, badge: 'Low',     cls: 'badge-muted' },
  { label: 'Social cohesion',          pct: 15, badge: 'Low',     cls: 'badge-muted' },
];

const COUNTRIES = [
  { name: 'Ukraine',      pct: 30, direct: true,  color: '#ef4444' },
  { name: 'Iran',         pct: 30, direct: true,  color: '#ef4444' },
  { name: 'Israel',       pct: 30, direct: true,  color: '#ef4444' },
  { name: 'Russia',       pct: 30, direct: true,  color: '#ef4444' },
  { name: 'Lebanon',      pct: 29, direct: true,  color: '#ef4444' },
  { name: 'Saudi Arabia', pct: 27, direct: true,  color: '#f59e0b' },
  { name: 'UAE',          pct: 26, direct: true,  color: '#f59e0b' },
  { name: 'India',        pct: 28, direct: false, color: '#f59e0b' },
  { name: 'China',        pct: 25, direct: false, color: '#0088ff' },
  { name: 'Qatar',        pct: 23, direct: false, color: '#0088ff' },
  { name: 'Turkey',       pct: 22, direct: false, color: '#0088ff' },
  { name: 'South Korea',  pct: 22, direct: false, color: '#0088ff' },
];

const SECTORS = [
  { name: 'Shipping & logistics', pct: 20 },
  { name: 'Tourism',              pct: 19 },
  { name: 'Energy',               pct: 17 },
  { name: 'Hospitality',          pct: 15 },
  { name: 'Luxury / real estate', pct: 14 },
  { name: 'Food & agriculture',   pct: 11 },
  { name: 'F&B / nightlife',      pct: 13 },
  { name: 'Technology',           pct: 7  },
];

const ISSUE_BUCKETS = [
  'Red Sea shipping',
  'Gulf energy security',
  'US–China technology',
  'Taiwan Strait',
  'Russia–Ukraine war',
  'Iran–Israel dynamics',
];

/* ============================================================
   PAGE COMPONENT
   ============================================================ */
export default function DashboardPage() {
  const now = new Date().toLocaleString();

  // Issue filter state
  const [activeIssues, setActiveIssues] = useState<Set<string>>(
    new Set(['Red Sea shipping', 'Gulf energy security', 'Iran–Israel dynamics'])
  );

  // Weight slider state (raw, unnormalized)
  const [rawDf, setRawDf] = useState(40);
  const [rawGt, setRawGt] = useState(30);
  const [rawCb, setRawCb] = useState(30);
  const [currentPreset, setCurrentPreset] = useState('managed_tension');
  const [wsNote, setWsNote] = useState(PHASE_PRESETS.managed_tension.note);

  const weights = resolveWeights(rawDf, rawGt, rawCb);

  const applyPreset = useCallback((key: string) => {
    const p = PHASE_PRESETS[key];
    if (!p) return;
    setRawDf(p.df);
    setRawGt(p.gt);
    setRawCb(p.cb);
    setCurrentPreset(key);
    setWsNote(p.note);
  }, []);

  const toggleIssue = (bucket: string) => {
    setActiveIssues(prev => {
      const next = new Set(prev);
      next.has(bucket) ? next.delete(bucket) : next.add(bucket);
      return next;
    });
  };

  return (
    <main className="page-shell visual-heavy">

      {/* ── HERO ─────────────────────────────────────────── */}
      <section className="hero">
        <div>
          <p className="eyebrow">Geopolitical State Engine</p>
          <h1>Scenario command dashboard</h1>
          <p className="subcopy">LIVE · {now} · Iran–Israel / Red Sea nexus</p>
        </div>
        <div className="criticality-card">
          <div className="crit-label">Systemic criticality</div>
          <div className="crit-value">36<span>%</span></div>
          <div className="crit-bar-track">
            <div className="crit-bar-fill" style={{ width: '36%' }} />
          </div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span className="badge badge-warn">Guarded</span>
            <span className="crit-meta">Impact: Medium · Severity: Guarded</span>
          </div>
          <details>
            <summary>Formula</summary>
            <p className="crit-meta" style={{ marginTop: '0.5rem' }}>
              Weighted composite of Maslow hierarchy risk (Safety 32%), sector exposure,
              actor posture, and signal velocity. Final: 36%.
            </p>
          </details>
        </div>
      </section>

      {/* ── COMMAND STRIP ────────────────────────────────── */}
      <div className="command-row">
        <div className="cmd-cell">
          <div className="cmd-cell-label">System state</div>
          <div className="cmd-cell-value" style={{ fontSize: '1rem' }}>Managed tension</div>
          <div className="cmd-cell-sub">
            <span className="badge badge-warn" style={{ marginRight: 4 }}>Rising</span>
            Signal velocity accelerating
          </div>
        </div>
        <div className="cmd-cell">
          <div className="cmd-cell-label">Conflict escalation</div>
          <div className="cmd-cell-value" style={{ color: 'var(--warn)' }}>50%</div>
          <div className="cmd-cell-sub delta-pos">▲ Elevated · Rising</div>
        </div>
        <div className="cmd-cell">
          <div className="cmd-cell-label">Disagreement index</div>
          <div className="cmd-cell-value" style={{ color: 'var(--accent)' }}>{weights.di}</div>
          <div className="cmd-cell-sub" style={{ color: 'var(--green)' }}>Low — methods aligned</div>
        </div>
        <div className="cmd-cell">
          <div className="cmd-cell-label">Top scenario</div>
          <div className="cmd-cell-value" style={{ fontSize: '0.9rem' }}>Mgd confrontation</div>
          <div className="cmd-cell-sub"><span className="delta-pos">▲ +3.1%</span> · 17% probability</div>
        </div>
      </div>

      {/* ── ESCALATION BAR ───────────────────────────────── */}
      <div className="full-width-bar">
        <span className="esc-label">Conflict escalation likelihood</span>
        <div className="esc-bar-track">
          <div className="esc-bar-fill" style={{ width: '50%' }} />
        </div>
        <span className="esc-value">50%</span>
        <span className="badge badge-danger">Elevated</span>
      </div>

      {/* ── ISSUE FILTERS ────────────────────────────────── */}
      <div style={{ marginTop: '1rem' }}>
        <div className="issue-pills-label">Active issue filters</div>
        <div className="issue-pills">
          {ISSUE_BUCKETS.map(b => (
            <button
              key={b}
              className={`issue-pill${activeIssues.has(b) ? ' active' : ''}`}
              onClick={() => toggleIssue(b)}
            >
              {b}
            </button>
          ))}
        </div>
      </div>

      {/* ── MAIN 2-COLUMN GRID ───────────────────────────── */}
      <div className="main-grid">

        {/* LEFT COL */}
        <div className="left-col">

          {/* Scenario Lattice */}
          <div className="card">
            <div className="card-title">
              <span>Scenario lattice — probability &amp; momentum</span>
              <span className="badge badge-muted">7 paths tracked</span>
            </div>
            {SCENARIOS.map(s => (
              <div key={s.name} className="scenario-row">
                <div className="scenario-name">
                  {s.name}
                  {s.top && (
                    <span className="badge badge-warn" style={{ marginLeft: 6, fontSize: 8 }}>top</span>
                  )}
                </div>
                <div className="scenario-track">
                  <div
                    className={`scenario-fill sf-${s.dir}`}
                    style={{ width: `${s.pct}%` }}
                  />
                </div>
                <div className="scenario-pct">{s.pct}%</div>
                <span className={s.dir === 'fall' ? 'delta-neg' : 'delta-pos'}>
                  {s.delta}
                </span>
              </div>
            ))}
            <div className="scenario-note">
              Flat distribution (10–17%) signals high uncertainty. No dominant path.
              Read deltas as velocity, not state.
            </div>
          </div>

          {/* Method Weights — Dynamic Fusion Engine */}
          <div className="card">
            <div className="card-title">
              <span>Method weights — dynamic fusion engine</span>
              <span
                className="weight-state-tag"
                id="ws-state-tag"
              >
                state: {PHASE_PRESETS[currentPreset]?.label.toLowerCase()}
              </span>
            </div>
            <p style={{ fontSize: 11, color: 'var(--text3)', marginBottom: '0.75rem', fontFamily: 'var(--font-mono)' }}>
              Weights are derived from system state + dominant force type. Adjust to explore sensitivity.
            </p>
            <div className="weight-method-pills">
              <span className="method-pill">
                Driving forces <b style={{ color: 'var(--accent)' }}>{weights.df}%</b>
              </span>
              <span className="method-pill">
                Game theory <b style={{ color: 'var(--accent)' }}>{weights.gt}%</b>
              </span>
              <span className="method-pill">
                Chessboard <b style={{ color: 'var(--accent)' }}>{weights.cb}%</b>
              </span>
              <span className="method-pill">
                Index <b style={{ color: 'var(--warn)' }}>{weights.di}</b>
              </span>
            </div>
            <div className="weight-sliders">
              <div className="ws-row">
                <span className="ws-label">Driving forces</span>
                <input
                  type="range" className="ws-input"
                  min={10} max={70} step={1} value={rawDf}
                  onChange={e => setRawDf(Number(e.target.value))}
                />
                <span className="ws-value">{weights.df}%</span>
              </div>
              <div className="ws-row">
                <span className="ws-label">Game theory</span>
                <input
                  type="range" className="ws-input"
                  min={10} max={60} step={1} value={rawGt}
                  onChange={e => setRawGt(Number(e.target.value))}
                />
                <span className="ws-value">{weights.gt}%</span>
              </div>
              <div className="ws-row">
                <span className="ws-label">Chessboard</span>
                <input
                  type="range" className="ws-input"
                  min={10} max={60} step={1} value={rawCb}
                  onChange={e => setRawCb(Number(e.target.value))}
                />
                <span className="ws-value">{weights.cb}%</span>
              </div>
            </div>
            <div className="ws-note">
              <b>Model recommendation:</b> {PHASE_PRESETS[currentPreset]?.label} → {weights.df}/{weights.gt}/{weights.cb}
              <br />{wsNote}
            </div>
            <div className="preset-btns">
              {Object.entries(PHASE_PRESETS).map(([key, p]) => (
                <button
                  key={key}
                  className="btn-outline"
                  style={{
                    fontSize: 9,
                    padding: '4px 10px',
                    ...(currentPreset === key ? { borderColor: 'var(--accent)', color: 'var(--accent)' } : {}),
                  }}
                  onClick={() => applyPreset(key)}
                >
                  {p.label}
                </button>
              ))}
            </div>
          </div>

          {/* Live Tape */}
          <div className="card">
            <div className="card-title">
              <span>Live update tape</span>
              <span className="badge badge-danger">8 signals</span>
            </div>
            {TAPE.map((item, i) => (
              <div key={i} className="tape-item">
                <div className={`tape-severity sev-${item.sev}`} />
                <div className="tape-source">{item.source}</div>
                <div className="tape-text">{item.text}</div>
                <div className="tape-time">{item.time}</div>
              </div>
            ))}
          </div>

        </div>

        {/* RIGHT COL */}
        <div className="right-col">

          {/* Actor Next Moves */}
          <div className="card">
            <div className="card-title">
              <span>Actor next moves</span>
              <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--text3)' }}>4-step horizon</span>
            </div>
            {ACTORS.map(a => (
              <div key={a.name} className="actor-row">
                <div className="actor-tag">{a.name}</div>
                <div className="actor-move">{a.move}</div>
                <div className="actor-conf" style={{ color: a.highlight ? 'var(--warn)' : 'var(--text2)' }}>
                  {a.conf}%
                </div>
              </div>
            ))}
            <p style={{ marginTop: '0.75rem', fontSize: 11, color: 'var(--text3)', fontFamily: 'var(--font-mono)', lineHeight: 1.5 }}>
              Israel 64% = highest actor certainty — most predictable posture in current snapshot.
            </p>
          </div>

          {/* Strategic Force Split */}
          <div className="card">
            <div className="card-title"><span>Strategic force split</span></div>
            <div className="force-bar">
              <div className="force-label">Hard (military + cyber)</div>
              <div className="force-track"><div className="force-fill" style={{ width: '45%', background: 'var(--danger)' }} /></div>
              <div className="force-pct">45%</div>
            </div>
            <div className="force-bar">
              <div className="force-label">Soft (diplomatic + narrative)</div>
              <div className="force-track"><div className="force-fill" style={{ width: '30%', background: 'var(--accent2)' }} /></div>
              <div className="force-pct">30%</div>
            </div>
            <div className="force-bar">
              <div className="force-label">Market (economic)</div>
              <div className="force-track"><div className="force-fill" style={{ width: '25%', background: 'var(--warn)' }} /></div>
              <div className="force-pct">25%</div>
            </div>
            <p style={{ marginTop: '0.5rem', fontSize: 11, color: 'var(--text3)', fontFamily: 'var(--font-mono)' }}>
              Military-dominant → weight modifier: chessboard +5, driving forces −5
            </p>
          </div>

          {/* Maslow Risk Hierarchy */}
          <div className="card">
            <div className="card-title"><span>Maslow risk hierarchy</span></div>
            {MASLOW.map(m => (
              <div key={m.label} className="maslow-row">
                <div className="maslow-label">{m.label}</div>
                <div className="maslow-pct">{m.pct}%</div>
                <span className={`badge ${m.cls}`}>{m.badge}</span>
              </div>
            ))}
            <div style={{ marginTop: '0.75rem', padding: '0.5rem 0.75rem', background: 'var(--bg4)', borderRadius: 6, fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--text3)' }}>
              Final hierarchy risk: <b style={{ color: 'var(--warn)' }}>27%</b> · Safety dominant-risk adjusted
            </div>
          </div>

          {/* Country Exposure */}
          <div className="card">
            <div className="card-title">
              <span>Country exposure</span>
              <span className="badge badge-muted">18 countries</span>
            </div>
            <div className="country-scroll">
              {COUNTRIES.map(c => (
                <div key={c.name} className="country-row">
                  <div className="country-dot" style={{ background: c.color }} />
                  <div className="country-name">{c.name}</div>
                  <div className="country-pct">{c.pct}%</div>
                  <span className={`country-exp ${c.direct ? 'exp-direct' : 'exp-indirect'}`}>
                    {c.direct ? 'direct' : 'indirect'}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Analyst Panel */}
          <div className="card">
            <div className="card-title"><span>Analyst panel consensus</span></div>
            {ANALYSTS.map(a => (
              <div key={a.initials} className="analyst-row">
                <div
                  className="analyst-avatar"
                  style={{ background: a.color, color: a.textColor }}
                >
                  {a.initials}
                </div>
                <div>
                  <div className="analyst-role">{a.role}</div>
                  <div className="analyst-text">{a.text}</div>
                </div>
              </div>
            ))}
            <div className="consensus-box">
              Interpret systemic criticality and escalation likelihood separately.
              Prioritize leading indicators over composite scores.
            </div>
          </div>

        </div>
      </div>

      {/* ── SECTOR EXPOSURE ──────────────────────────────── */}
      <div className="section-divider"><span>Sector exposure</span></div>
      <div className="card">
        <div className="card-title"><span>Sector impact</span></div>
        <div className="sector-grid">
          {SECTORS.map(s => (
            <div key={s.name} className="sector-item">
              <div className="sector-name">{s.name}</div>
              <div className="sector-pct">{s.pct}%</div>
              <div className="sector-bar">
                <div className="sector-fill" style={{ width: `${s.pct * 5}%` }} />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* ── PREMIUM BAR ──────────────────────────────────── */}
      <div className="premium-bar">
        <div className="premium-cell">
          <div className="premium-title">Analyst Pro</div>
          <div className="premium-sub">Saved watchlists, custom alerts, and export packs.</div>
          <button className="btn-primary">Start trial</button>
        </div>
        <div className="premium-cell">
          <div className="premium-title">Team Ops</div>
          <div className="premium-sub">Shared boards, consensus workflow, and approvals.</div>
          <button className="btn-outline">Request demo</button>
        </div>
        <div className="premium-cell">
          <div className="premium-title">API Access</div>
          <div className="premium-sub">Programmatic scenarios, risk feeds, and webhooks.</div>
          <button className="btn-outline">Contact sales</button>
        </div>
      </div>

    </main>
  );
}
