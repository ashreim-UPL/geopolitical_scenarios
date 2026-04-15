"use client";

import Link from "next/link";
import Image from "next/image";
import dynamic from "next/dynamic";
import { useEffect, useMemo, useRef, useState } from "react";

const ImpactMap = dynamic(() => import("../components/impact-map"), { ssr: false });
const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

type IssueItem = { slug: string; label: string };
type ScenarioRow = { name: string; probability: number; delta_pct: number };
type SourceRow = { name: string; type: string; description: string };
type ThemeRow = { name: string; type: string; description: string; percent: number; band: string };
type SignalRow = {
  title: string;
  source: string;
  link: string;
  issue: string;
  published_utc: string | null;
  intelligence_metadata?: { provider: string };
};

type Snapshot = {
  generated_utc: string;
  mode: string;
  lens: { type: "global" | "region" | "country"; focus: string | null };
  overall_criticality: { percent: number; band: string };
  conflict_escalation: { percent: number; band: string };
  scenarios: ScenarioRow[];
  impacts: {
    countries: { label: string; severity: number; directness?: string }[];
    regions_world: { label: string; severity: number }[];
    country_focus_options: string[];
  };
  alternative_intelligence?: { disclaimer: string; sources: SourceRow[]; themes?: ThemeRow[] };
  scenario_visual?: {
    image_data_url: string | null;
    provider: string;
    model: string;
    generated: boolean;
  };
  creative_prediction?: {
    story_text: string;
    visual_prompt: string;
    scenarios_payload: Record<string, unknown>;
    provider: string;
    model: string;
    generated: boolean;
  };
  update_policy?: {
    recommended_interval_seconds: number;
    rationale: string;
    next_refresh_utc: string;
  };
  cache?: {
    cache_hit: boolean;
    cached_at_utc: string;
    stale_fallback?: boolean;
    warning?: string | null;
  };
  source_health?: {
    source: string;
    status: string;
    last_success_utc: string | null;
    last_error_utc: string | null;
    last_error: string | null;
  }[];
  snapshot_history?: {
    generated_utc: string;
    mode: string;
    top_scenario: string;
    overall_criticality: number;
    conflict_escalation: number;
  }[];
  analysis_provenance?: {
    active_provider?: string;
    model_version?: string;
    llm_enabled?: boolean;
  };
  signals: SignalRow[];
  expert_review: { consensus_brief: string };
  prediction: string;
};

const DEFAULT_COUNTRIES = ["Iran", "Israel", "Saudi Arabia", "UAE", "Iraq", "Lebanon", "Turkey", "France"];
const DEFAULT_REGIONS = ["Gulf", "Levant", "Europe", "MENA", "East Asia"];
const COUNTRY_COORDS: Record<string, { lat: number; lon: number }> = {
  Iran: { lat: 32.4, lon: 53.7 },
  Israel: { lat: 31.0, lon: 35.0 },
  "Saudi Arabia": { lat: 23.9, lon: 45.1 },
  UAE: { lat: 23.4, lon: 53.8 },
  Iraq: { lat: 33.2, lon: 43.7 },
  Lebanon: { lat: 33.9, lon: 35.9 },
  Turkey: { lat: 39.0, lon: 35.2 },
  France: { lat: 46.2, lon: 2.2 },
  Germany: { lat: 51.2, lon: 10.4 },
  Russia: { lat: 61.5, lon: 105.3 },
  Ukraine: { lat: 49.0, lon: 31.4 },
  China: { lat: 35.9, lon: 104.2 },
  India: { lat: 20.6, lon: 78.9 },
  Yemen: { lat: 15.6, lon: 47.6 },
};

function severityColor(value: number): string {
  if (value >= 0.8) return "#ef4444";
  if (value >= 0.6) return "#f97316";
  if (value >= 0.4) return "#f59e0b";
  if (value >= 0.2) return "#60a5fa";
  return "#22c55e";
}

function buildAlternativeScenarioVisualSvg(scenario: string, probability: number): string {
  const pct = Math.round(Math.max(0, Math.min(1, probability)) * 100);
  const color = pct >= 70 ? "#ef4444" : pct >= 45 ? "#f59e0b" : "#22c55e";
  const title = scenario || "Alternative scenario pending";
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="860" height="260">
<defs>
  <linearGradient id="altbg" x1="0%" y1="0%" x2="100%" y2="100%">
    <stop offset="0%" stop-color="#150d1a" />
    <stop offset="100%" stop-color="#2a1536" />
  </linearGradient>
</defs>
<rect width="100%" height="100%" rx="14" fill="url(#altbg)"/>
<circle cx="160" cy="130" r="78" fill="rgba(255,255,255,0.05)" stroke="${color}" stroke-width="3"/>
<circle cx="160" cy="130" r="44" fill="${color}" opacity="0.3"/>
<text x="160" y="138" fill="#f8fafc" font-size="34" font-weight="700" text-anchor="middle">${pct}%</text>
<text x="290" y="90" fill="#f5d0fe" font-size="16" font-weight="600">Alternative forecast narrative</text>
<text x="290" y="122" fill="#f8fafc" font-size="28" font-weight="700">${title}</text>
<text x="290" y="152" fill="#e9d5ff" font-size="15">Generated from low-confidence narrative channels (rumors/gossip/esoteric feeds).</text>
</svg>`;
  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
}

export default function AlternativePage() {
  const [issues, setIssues] = useState<IssueItem[]>([]);
  const [selectedIssues, setSelectedIssues] = useState<string[]>([
    "iran-israel-dynamics",
  ]);
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [lensType, setLensType] = useState<"global" | "region" | "country">("global");
  const [regionFocus, setRegionFocus] = useState("Gulf");
  const [countryFocus, setCountryFocus] = useState("Iran");
  const [localAiEnhancement, setLocalAiEnhancement] = useState(true);
  const liveTapeRef = useRef<HTMLDivElement | null>(null);

  const activeFocus = lensType === "region" ? regionFocus : lensType === "country" ? countryFocus : "";
  const selectedIssueParam = useMemo(() => selectedIssues.join(","), [selectedIssues]);
  const countryOptions = useMemo(
    () => Array.from(new Set([...(snapshot?.impacts.country_focus_options ?? []), ...DEFAULT_COUNTRIES])).sort((a, b) => a.localeCompare(b)),
    [snapshot]
  );

  const countryMapPoints = useMemo(() => {
    return (snapshot?.impacts.countries ?? [])
      .map((row) => {
        const coord = COUNTRY_COORDS[row.label];
        if (!coord) return null;
        return {
          label: row.label,
          severity: row.severity,
          directness: row.directness ?? "indirect",
          lat: coord.lat,
          lon: coord.lon,
        };
      })
      .filter((row): row is { label: string; severity: number; directness: string; lat: number; lon: number } => row !== null);
  }, [snapshot]);
  const topAlternativeScenario = snapshot?.scenarios?.[0];
  const altScenarioVisualDataUrl = useMemo(
    () =>
      snapshot?.scenario_visual?.image_data_url ??
      buildAlternativeScenarioVisualSvg(topAlternativeScenario?.name ?? "Alternative scenario pending", topAlternativeScenario?.probability ?? 0),
    [snapshot?.scenario_visual?.image_data_url, topAlternativeScenario?.name, topAlternativeScenario?.probability]
  );
  const altTimelineText = useMemo(() => {
    const scenario = topAlternativeScenario?.name ?? "Alternative scenario pending";
    const ranked = [...(snapshot?.scenarios ?? [])].sort((a, b) => b.probability - a.probability);
    const top = ranked[0]?.probability ?? 0;
    const second = ranked[1]?.probability ?? 0;
    const lead =
      top < 0.34 ? "Fragmented field" : top - second < 0.05 ? "Contested lead" : top >= 0.5 && top - second >= 0.12 ? "Strong lead" : "Moderate lead";
    return `Most discussed alternative path: ${scenario}. Lead status: ${lead}. Timeline: next 12-48 hours for rumor acceleration checks, and 3-10 days for verification or narrative fade-out.`;
  }, [topAlternativeScenario?.name, snapshot?.scenarios]);
  const altCreativePreview = useMemo(() => {
    const text = (snapshot?.creative_prediction?.story_text ?? "").replace(/\s+/g, " ").trim();
    if (!text) {
      return snapshot?.prediction ?? "Alternative prediction pending.";
    }
    return text;
  }, [snapshot?.creative_prediction?.story_text, snapshot?.prediction]);
  const scenarioImageStatus = useMemo(() => {
    if (snapshot?.scenario_visual?.generated && snapshot?.scenario_visual?.image_data_url) {
      return `AI image generated (${snapshot?.scenario_visual.provider}/${snapshot?.scenario_visual.model})`;
    }
    return "AI image unavailable; showing fallback visual. Check OPENAI_API_KEY and restart API.";
  }, [snapshot?.scenario_visual?.generated, snapshot?.scenario_visual?.image_data_url, snapshot?.scenario_visual?.provider, snapshot?.scenario_visual?.model]);

  useEffect(() => {
    async function loadIssues() {
      const response = await fetch(`${apiBase}/v1/issues`);
      if (!response.ok) throw new Error("Issue catalog unavailable.");
      const data = (await response.json()) as { issues: IssueItem[] };
      setIssues(data.issues);
    }
    void loadIssues().catch(() => setError("Issue catalog unavailable."));
  }, []);

  useEffect(() => {
    async function loadSnapshot() {
      setError(null);
      try {
        const response = await fetch(`${apiBase}/v1/alternative/analyze`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            selected_issues: selectedIssues,
            use_live: true,
            lens: lensType,
            focus: activeFocus || null,
            local_ai_enabled: localAiEnhancement,
          }),
        });
        if (!response.ok) throw new Error(`Alternative analyze failed (${response.status})`);
        setSnapshot((await response.json()) as Snapshot);
      } catch {
        setError("Alternative analysis API unavailable.");
      }
    }
    void loadSnapshot();
  }, [selectedIssueParam, selectedIssues, lensType, activeFocus, localAiEnhancement]);

  useEffect(() => {
    const intervalSeconds = snapshot?.update_policy?.recommended_interval_seconds ?? 1800;
    const timer = setInterval(async () => {
      try {
        const response = await fetch(`${apiBase}/v1/alternative/analyze`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            selected_issues: selectedIssues,
            use_live: true,
            lens: lensType,
            focus: activeFocus || null,
            local_ai_enabled: localAiEnhancement,
          }),
        });
        if (response.ok) {
          setSnapshot((await response.json()) as Snapshot);
        }
      } catch {
        // passive retry on next tick
      }
    }, intervalSeconds * 1000);
    return () => clearInterval(timer);
  }, [snapshot?.update_policy?.recommended_interval_seconds, selectedIssues, lensType, activeFocus, localAiEnhancement]);

  useEffect(() => {
    const node = liveTapeRef.current;
    if (!node) {
      return undefined;
    }
    const timer = setInterval(() => {
      const maxScroll = node.scrollHeight - node.clientHeight;
      if (maxScroll <= 0) {
        return;
      }
      if (node.scrollTop >= maxScroll - 8) {
        node.scrollTop = 0;
        return;
      }
      node.scrollBy({ top: 42, behavior: "smooth" });
    }, 2600);
    return () => clearInterval(timer);
  }, [snapshot?.signals]);

  const toggleIssue = (slug: string) => {
    setSelectedIssues((prev) => (prev.includes(slug) ? prev.filter((x) => x !== slug) : [...prev, slug]));
  };

  return (
    <main className="page-shell visual-heavy">
      <section className="hero">
        <div>
          <p className="eyebrow">Alternative Narrative Engine</p>
          <h1>Rumor, gossip, and esoteric signal dashboard</h1>
          <p className="subcopy">
            {snapshot?.generated_utc ? new Date(snapshot.generated_utc).toLocaleString() : "updating"} | mode: {snapshot?.mode ?? "alternative"}
          </p>
          <p className="muted mini">
            AI engine: {snapshot?.analysis_provenance?.active_provider ?? "deterministic"} ({snapshot?.analysis_provenance?.model_version ?? "heuristic-v1"}) |
            Image engine: {snapshot?.scenario_visual?.provider ?? "none"} ({snapshot?.scenario_visual?.model ?? "none"}) |
            Refresh: every {Math.round((snapshot?.update_policy?.recommended_interval_seconds ?? 1800) / 60)} min
          </p>
          <p className="muted mini">
            Last saved snapshot: {snapshot?.cache?.cached_at_utc ? new Date(snapshot.cache.cached_at_utc).toLocaleString() : "pending"} | Next refresh target: {snapshot?.update_policy?.next_refresh_utc ? new Date(snapshot.update_policy.next_refresh_utc).toLocaleString() : "pending"}
          </p>
          {snapshot?.cache?.stale_fallback && (
            <p className="muted mini">
              Using latest cached alternative snapshot while live refresh retries ({snapshot.cache.warning ?? "refresh warning"}).
            </p>
          )}
          <p className="muted mini">
            <Link href="/">Return to main dashboard</Link>
          </p>
        </div>
        <div className="hero-gauges">
          <div className="impact-grid">
            <div className="impact-card">
              <p>Systemic Criticality</p>
              <div className="mini-battery">
                <div className="mini-battery-fill" style={{ width: `${snapshot?.overall_criticality.percent ?? 0}%`, background: severityColor((snapshot?.overall_criticality.percent ?? 0) / 100) }} />
              </div>
              <strong>{snapshot?.overall_criticality.percent ?? 0}% | {snapshot?.overall_criticality.band ?? "Unknown"}</strong>
            </div>
            <div className="impact-card">
              <p>Conflict Escalation</p>
              <div className="mini-battery">
                <div className="mini-battery-fill" style={{ width: `${snapshot?.conflict_escalation.percent ?? 0}%`, background: severityColor((snapshot?.conflict_escalation.percent ?? 0) / 100) }} />
              </div>
              <strong>{snapshot?.conflict_escalation.percent ?? 0}% | {snapshot?.conflict_escalation.band ?? "Unknown"}</strong>
            </div>
          </div>
        </div>
      </section>

      <section className="panel compact controls-line">
        <div className="control-block">
          <h2>Issue Buckets</h2>
          <div className="chip-grid">
            {issues.map((issue) => (
              <button key={issue.slug} type="button" className={selectedIssues.includes(issue.slug) ? "chip selected" : "chip"} onClick={() => toggleIssue(issue.slug)}>
                {issue.label}
              </button>
            ))}
          </div>
        </div>
        <div className="control-block">
          <h2>Impact Lens</h2>
          <div className="lens-row">
            <div className="chip-grid">
              {(["global", "region", "country"] as const).map((lens) => (
                <button key={lens} type="button" className={lensType === lens ? "chip selected" : "chip"} onClick={() => setLensType(lens)}>
                  {lens}
                </button>
              ))}
            </div>
            {lensType === "region" && (
              <select className="lens-select" value={regionFocus} onChange={(event) => setRegionFocus(event.target.value)}>
                {DEFAULT_REGIONS.map((region) => (
                  <option key={region} value={region}>{region}</option>
                ))}
              </select>
            )}
            {lensType === "country" && (
              <select className="lens-select" value={countryFocus} onChange={(event) => setCountryFocus(event.target.value)}>
                {countryOptions.map((country) => (
                  <option key={country} value={country}>{country}</option>
                ))}
              </select>
            )}
          </div>
          <p className="muted mini">Active lens: {lensType}{activeFocus ? ` (${activeFocus})` : ""}</p>
          <label className="muted mini">
            <input type="checkbox" checked={localAiEnhancement} onChange={(event) => setLocalAiEnhancement(event.target.checked)} /> Local AI Enhancement
          </label>
        </div>
      </section>

      <section className="panel compact">
        <h2>Predicted Scenario Snapshot</h2>
        <p className="muted mini">{scenarioImageStatus}</p>
        <div className="prediction-visual-grid">
          <Image src={altScenarioVisualDataUrl} alt="Alternative predicted scenario visualization" className="viz-image prediction-image" width={860} height={260} unoptimized />
          <div className="prediction-timeline">
            <p className="prediction-summary">{altTimelineText}</p>
            <p className="muted prediction-summary">{altCreativePreview}</p>
          </div>
        </div>
      </section>

      <section className="panel">
        <h2>Alternative Source Sheet</h2>
        <p className="muted mini">{snapshot?.alternative_intelligence?.disclaimer ?? "Loading source disclaimer..."}</p>
        <div className="impact-grid">
          {(snapshot?.alternative_intelligence?.sources ?? []).map((source) => (
            <div key={source.name} className="impact-card">
              <p>{source.name}</p>
              <strong>{source.type}</strong>
              <p className="muted mini">{source.description}</p>
            </div>
          ))}
        </div>
        <h3>Esoteric / Ideological Theme Matrix</h3>
        <div className="impact-grid">
          {(snapshot?.alternative_intelligence?.themes ?? []).map((theme) => (
            <div key={theme.name} className="impact-card">
              <p>{theme.name}</p>
              <strong>{theme.type} | {theme.band} ({theme.percent}%)</strong>
              <p className="muted mini">{theme.description}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="panel">
        <h2>Alternative Narrative Map + Tape</h2>
        <div className="map-live-grid full-width">
          <div className="country-map-wrap">
            <ImpactMap points={countryMapPoints} lensType={lensType} lensFocus={activeFocus} />
            <p className="muted mini">Color and marker size represent modeled narrative risk/exposure in alternative channels.</p>
          </div>
          <div className="live-tape-box">
            <h3>Rumor / Gossip Tape</h3>
            {error && <p className="error">{error}</p>}
            <div className="live-tape-scroll" ref={liveTapeRef}>
              <ul className="signal-list">
                {(snapshot?.signals ?? []).map((signal) => (
                  <li key={`${signal.link}-${signal.title}`}>
                    <a href={signal.link} target="_blank" rel="noreferrer">{signal.title}</a>
                    <p className="muted">
                      {signal.source} | {signal.issue} | {signal.published_utc ? new Date(signal.published_utc).toLocaleTimeString() : "time unknown"} | engine: {signal.intelligence_metadata?.provider ?? "deterministic"}
                    </p>
                  </li>
                ))}
                {(snapshot?.signals ?? []).length === 0 && (
                  <li>
                    <p className="muted mini">No fresh alternative signals yet. Waiting for ingest cycle...</p>
                  </li>
                )}
              </ul>
            </div>
          </div>
        </div>
      </section>

      <section className="grid-2">
        <article className="panel">
          <h2>Scenario Lattice (Alternative)</h2>
          <div className="impact-grid">
            {(snapshot?.scenarios ?? []).slice(0, 4).map((scenario) => (
              <div key={scenario.name} className="impact-card">
                <p>{scenario.name}</p>
                <div className="mini-battery">
                  <div className="mini-battery-fill" style={{ width: `${Math.round(scenario.probability * 100)}%`, background: severityColor(scenario.probability) }} />
                </div>
                <strong>{Math.round(scenario.probability * 100)}% | {scenario.delta_pct >= 0 ? "rising" : "cooling"}</strong>
              </div>
            ))}
          </div>
        </article>
        <article className="panel">
          <h2>Alternative Consensus Brief</h2>
          <p className="muted mini">{snapshot?.expert_review.consensus_brief ?? "Consensus pending..."}</p>
          <p className="muted mini">{snapshot?.prediction ?? ""}</p>
          <h3>Region / Worldwide Impact</h3>
          <ul className="metric-list">
            {(snapshot?.impacts.regions_world ?? []).slice(0, 6).map((row) => (
              <li key={row.label}>
                <span>{row.label}</span>
                <strong>{Math.round(row.severity * 100)}%</strong>
              </li>
            ))}
          </ul>
        </article>
      </section>
    </main>
  );
}
