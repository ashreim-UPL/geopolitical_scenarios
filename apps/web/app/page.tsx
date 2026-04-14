"use client";

import Image from "next/image";
import dynamic from "next/dynamic";
import { useEffect, useMemo, useState } from "react";

type IssueItem = {
  slug: string;
  label: string;
};

type ScenarioRow = {
  name: string;
  probability: number;
  delta_pct: number;
};

type ScenarioClusterKey = "escalation" | "maritime_shock" | "hybrid_fragmentation" | "stabilization";
type LeadStrength = "Fragmented field" | "Contested lead" | "Moderate lead" | "Strong lead";

type SignalRow = {
  title: string;
  source: string;
  link: string;
  issue: string;
  published_utc: string | null;
};

type Snapshot = {
  generated_utc: string;
  mode: "live" | "demo";
  selected_issues: string[];
  lens: { type: "global" | "region" | "country"; focus: string | null };
  current_state: { label: string; confidence: number };
  trend: string;
  forces: { name: string; score: number }[];
  scenarios: ScenarioRow[];
  scenario_methods: {
    driving_forces: ScenarioRow[];
    game_theory: ScenarioRow[];
    chessboard: ScenarioRow[];
    consensus: {
      rows: ScenarioRow[];
      weights: { driving_forces: number; game_theory: number; chessboard: number };
      disagreement_index: number;
      derived_from?: string;
      analyst_panel_consensus?: string;
      analyst_override?: boolean;
    };
  };
  next_scenario_forecast: {
    scenario: string;
    probability: number;
    horizon_steps: number;
    actor_moves: { actor: string; move: string; confidence: number }[];
    rationale: string;
  };
  overall_criticality: {
    score: number;
    percent: number;
    band: "Low" | "Guarded" | "Elevated" | "High" | "Critical";
    band_range: string;
    formula: Record<string, number>;
    meaning: string;
  };
  conflict_escalation: {
    score: number;
    percent: number;
    band: "Low" | "Guarded" | "Elevated" | "High" | "Critical";
    meaning: string;
  };
  consistency_notes: string[];
  expert_review: {
    panel: { role: string; region: string; view: string }[];
    consensus: string;
    consensus_brief: string;
  };
  impacts: {
    prediction: {
      most_likely_scenario: string;
      probability: number;
      brief: string;
    };
    regions_world: { label: string; severity: number; summary: string }[];
    countries: { label: string; severity: number; summary: string; directness?: string }[];
    countries_by_region: { region: string; countries: { name: string; directness: string }[] }[];
    country_focus_options: string[];
    sectors: { label: string; severity: number; summary: string }[];
    indicators: { label: string; severity: number; summary: string }[];
    three_sector_model: { label: string; severity: number; summary: string; band: string; percent: number }[];
    maslow_hierarchy: {
      levels: { name: string; score: number; weight: number; percent: number; band: string }[];
      weighted_score: number;
      dominant_score: number;
      hierarchy_score: number;
      percent: number;
      band: string;
      explanation: string;
    };
  };
  signals: SignalRow[];
  explanation: string;
  prediction: string;
};

const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

const FORCE_LABELS: Record<string, string> = {
  military: "Military",
  economic: "Economic",
  diplomatic: "Diplomatic",
  narrative: "Narrative",
  ideological: "Ideological/Perception",
  cyber: "Cyber",
};

const DEFAULT_REGION_FOCUS_OPTIONS = ["Gulf", "MENA", "Europe", "East Asia", "Global shipping lanes"];
const DEFAULT_COUNTRY_FOCUS_OPTIONS = ["United States", "China", "India"];
const ImpactMap = dynamic(() => import("./components/impact-map"), { ssr: false });
const COUNTRY_COORDS: Record<string, { lat: number; lon: number }> = {
  "United States": { lat: 39.8, lon: -98.6 },
  China: { lat: 35.9, lon: 104.2 },
  India: { lat: 20.6, lon: 78.9 },
  UAE: { lat: 23.4, lon: 53.8 },
  Iran: { lat: 32.4, lon: 53.7 },
  Israel: { lat: 31.0, lon: 35.0 },
  Lebanon: { lat: 33.9, lon: 35.9 },
  Syria: { lat: 34.8, lon: 38.9 },
  Iraq: { lat: 33.2, lon: 43.7 },
  "Saudi Arabia": { lat: 23.9, lon: 45.1 },
  Qatar: { lat: 25.3, lon: 51.2 },
  Kuwait: { lat: 29.3, lon: 47.5 },
  Oman: { lat: 21.5, lon: 55.9 },
  Jordan: { lat: 31.2, lon: 36.3 },
  Egypt: { lat: 26.8, lon: 30.8 },
  Turkey: { lat: 39.0, lon: 35.2 },
  Russia: { lat: 61.5, lon: 105.3 },
  Ukraine: { lat: 49.0, lon: 31.4 },
  Germany: { lat: 51.2, lon: 10.4 },
  France: { lat: 46.2, lon: 2.2 },
  "United Kingdom": { lat: 55.4, lon: -3.4 },
  Japan: { lat: 36.2, lon: 138.3 },
};

function severityColor(value: number): string {
  if (value >= 0.8) {
    return "#ef4444";
  }
  if (value >= 0.6) {
    return "#f97316";
  }
  if (value >= 0.4) {
    return "#f59e0b";
  }
  if (value >= 0.2) {
    return "#84cc16";
  }
  return "#22c55e";
}

function bandFromPercent(percent: number): string {
  if (percent <= 20) {
    return "Low";
  }
  if (percent <= 40) {
    return "Guarded";
  }
  if (percent <= 60) {
    return "Elevated";
  }
  if (percent <= 80) {
    return "High";
  }
  return "Critical";
}

function severityBandFromScore(score: number): string {
  return bandFromPercent(Math.round(score * 100));
}

function impactLevel(score: number): "Low" | "Medium" | "High" {
  if (score >= 0.55) {
    return "High";
  }
  if (score >= 0.25) {
    return "Medium";
  }
  return "Low";
}

function confidenceLabel(score: number): "Low" | "Medium" | "High" {
  if (score >= 0.67) {
    return "High";
  }
  if (score >= 0.34) {
    return "Medium";
  }
  return "Low";
}

function weightRole(weight: number): "Dominant" | "Major" | "Supporting" | "Minor" {
  if (weight >= 0.35) {
    return "Dominant";
  }
  if (weight >= 0.2) {
    return "Major";
  }
  if (weight >= 0.1) {
    return "Supporting";
  }
  return "Minor";
}

function disagreementBand(value: number): "Low" | "Medium" | "High" {
  if (value >= 0.67) {
    return "High";
  }
  if (value >= 0.34) {
    return "Medium";
  }
  return "Low";
}

function trendMeaning(stateLabel: string, trend: string): string {
  if (trend === "stable" && stateLabel.toLowerCase().includes("pre-war")) {
    return "Stable means high-tension plateau, not de-escalation.";
  }
  if (trend === "rising") {
    return "Signal velocity is accelerating.";
  }
  if (trend === "cooling") {
    return "Signal velocity is slowing, but risk may still remain high.";
  }
  return "Signal velocity is flat.";
}

function mapScenarioCluster(name: string): ScenarioClusterKey {
  const n = name.toLowerCase();
  if (n.includes("negotiated") || n.includes("reopening") || n.includes("corridor") || n.includes("stabil")) {
    return "stabilization";
  }
  if (n.includes("maritime") || n.includes("infrastructure") || n.includes("shipping") || n.includes("chokepoint")) {
    return "maritime_shock";
  }
  if (n.includes("fragmentation") || n.includes("rupture") || n.includes("hybrid")) {
    return "hybrid_fragmentation";
  }
  return "escalation";
}

function leadStrength(topProbability: number, secondProbability: number): LeadStrength {
  const gap = topProbability - secondProbability;
  if (topProbability < 0.34) {
    return "Fragmented field";
  }
  if (gap < 0.05) {
    return "Contested lead";
  }
  if (topProbability >= 0.5 && gap >= 0.12) {
    return "Strong lead";
  }
  return "Moderate lead";
}

function normalizedCountryName(name: string): string {
  if (name === "United Arab Emirates") {
    return "UAE";
  }
  return name;
}

const CLUSTER_META: Record<ScenarioClusterKey, { title: string; subtitle: string }> = {
  escalation: {
    title: "Escalation Path",
    subtitle: "Direct conflict expansion and coercive signaling",
  },
  maritime_shock: {
    title: "Maritime / Infrastructure Shock",
    subtitle: "Shipping, corridors, chokepoints, and energy transit disruption",
  },
  hybrid_fragmentation: {
    title: "Hybrid / Internal Fragmentation",
    subtitle: "Proxy pressure, political fracture, and internal system stress",
  },
  stabilization: {
    title: "Managed Stabilization",
    subtitle: "Negotiation, containment, and partial reopening dynamics",
  },
};

function buildForceSvg(forces: { name: string; score: number }[]): string {
  const width = 740;
  const height = 320;
  const marginLeft = 220;
  const rows = forces.slice(0, 6);
  const rowHeight = 42;
  const bars = rows
    .map((force, idx) => {
      const y = 40 + idx * rowHeight;
      const barWidth = Math.round(420 * force.score);
      const color = severityColor(force.score);
      const label = FORCE_LABELS[force.name] ?? force.name;
      return [
        `<text x="20" y="${y + 17}" fill="#e5e7eb" font-size="14">${label}</text>`,
        `<rect x="${marginLeft}" y="${y}" width="420" height="16" rx="5" fill="#1f2937" />`,
        `<rect x="${marginLeft}" y="${y}" width="${barWidth}" height="16" rx="5" fill="${color}" />`,
        `<text x="${marginLeft + 430}" y="${y + 13}" fill="#cbd5e1" font-size="12">${impactLevel(force.score)} impact</text>`,
      ].join("");
    })
    .join("");
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}">
<rect width="100%" height="100%" fill="#0f1723"/>
<text x="20" y="24" fill="#d1fae5" font-size="16">Force Buckets (Probability Split)</text>
${bars}
</svg>`;
  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`;
}

function polarToCartesian(cx: number, cy: number, radius: number, angleDeg: number) {
  const rad = ((angleDeg - 90) * Math.PI) / 180;
  return {
    x: cx + radius * Math.cos(rad),
    y: cy + radius * Math.sin(rad),
  };
}

function arcPath(cx: number, cy: number, radius: number, startAngle: number, endAngle: number) {
  const start = polarToCartesian(cx, cy, radius, endAngle);
  const end = polarToCartesian(cx, cy, radius, startAngle);
  const largeArc = endAngle - startAngle <= 180 ? "0" : "1";
  return `M ${start.x} ${start.y} A ${radius} ${radius} 0 ${largeArc} 0 ${end.x} ${end.y}`;
}

function GaugeDial({
  title,
  score,
  percent,
  band,
  emphasis = "secondary",
}: {
  title: string;
  score: number;
  percent: number;
  band: string;
  emphasis?: "primary" | "secondary";
}) {
  const clamped = Math.max(0, Math.min(1, score));
  const startAngle = -140;
  const endAngle = 140;
  const angle = startAngle + (endAngle - startAngle) * clamped;
  const needle = polarToCartesian(88, 88, 56, angle);
  const glow = severityColor(clamped);

  return (
    <article className={`gauge-card ${emphasis}`}>
      <p className="gauge-title mini-label">{title}</p>
      <svg viewBox="0 0 176 128" className="gauge-svg" role="img" aria-label={`${title} gauge`}>
        <defs>
          <linearGradient id={`${title.replace(/\s+/g, "-")}-grad`} x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#22c55e" />
            <stop offset="40%" stopColor="#eab308" />
            <stop offset="70%" stopColor="#f97316" />
            <stop offset="100%" stopColor="#ef4444" />
          </linearGradient>
          <filter id={`${title.replace(/\s+/g, "-")}-blur`}>
            <feGaussianBlur stdDeviation="2" />
          </filter>
        </defs>
        <path d={arcPath(88, 88, 68, startAngle, endAngle)} stroke="#1f2937" strokeWidth="12" fill="none" />
        <path
          d={arcPath(88, 88, 68, startAngle, endAngle)}
          stroke={`url(#${title.replace(/\s+/g, "-")}-grad)`}
          strokeWidth="12"
          fill="none"
          strokeLinecap="round"
        />
        <line x1="88" y1="88" x2={needle.x} y2={needle.y} stroke={glow} strokeWidth="4" strokeLinecap="round" />
        <line
          x1="88"
          y1="88"
          x2={needle.x}
          y2={needle.y}
          stroke={glow}
          strokeWidth="7"
          strokeLinecap="round"
          opacity="0.26"
          filter={`url(#${title.replace(/\s+/g, "-")}-blur)`}
        />
        <circle cx="88" cy="88" r="5.5" fill="#e2e8f0" />
        <text x="88" y="74" textAnchor="middle" className="gauge-percent">{percent}</text>
        <text x="88" y="88" textAnchor="middle" className="gauge-unit">/100</text>
        <text x="88" y="102" textAnchor="middle" className="gauge-band">{band}</text>
        <text x="16" y="120" className="gauge-scale">0</text>
        <text x="84" y="120" className="gauge-scale">50</text>
        <text x="154" y="120" className="gauge-scale">100</text>
      </svg>
    </article>
  );
}

export default function HomePage() {
  const [issues, setIssues] = useState<IssueItem[]>([]);
  const [selectedIssues, setSelectedIssues] = useState<string[]>([
    "red-sea-shipping",
    "iran-israel-dynamics",
    "russia-ukraine-war",
  ]);
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lensType, setLensType] = useState<"global" | "region" | "country">("global");
  const [regionFocus, setRegionFocus] = useState<string>("Gulf");
  const [countryFocus, setCountryFocus] = useState<string>("India");
  const [countryFocusPool, setCountryFocusPool] = useState<string[]>(DEFAULT_COUNTRY_FOCUS_OPTIONS);

  const selectedIssueParam = useMemo(() => selectedIssues.join(","), [selectedIssues]);
  const activeLensFocus = useMemo(() => {
    if (lensType === "region") {
      return regionFocus;
    }
    if (lensType === "country") {
      return countryFocus;
    }
    return "";
  }, [lensType, regionFocus, countryFocus]);
  const forceImageDataUrl = useMemo(() => buildForceSvg(snapshot?.forces ?? []), [snapshot?.forces]);
  const regionFocusOptions = useMemo(() => {
    const fromSnapshot = (snapshot?.impacts.regions_world ?? []).map((item) => item.label);
    const merged = [...DEFAULT_REGION_FOCUS_OPTIONS, ...fromSnapshot];
    return Array.from(new Set(merged));
  }, [snapshot]);
  const countryFocusOptions = useMemo(() => {
    return Array.from(new Set(countryFocusPool)).sort((a, b) => a.localeCompare(b));
  }, [countryFocusPool]);

  useEffect(() => {
    const fromSnapshot = snapshot?.impacts.country_focus_options ?? [];
    if (fromSnapshot.length === 0) {
      return;
    }
    setCountryFocusPool((prev) => Array.from(new Set([...prev, ...fromSnapshot])));
  }, [snapshot]);

  useEffect(() => {
    if (lensType === "region" && !regionFocusOptions.includes(regionFocus)) {
      setRegionFocus(regionFocusOptions[0] ?? "Gulf");
    }
  }, [lensType, regionFocus, regionFocusOptions]);

  useEffect(() => {
    if (lensType === "country" && !countryFocusOptions.includes(countryFocus)) {
      setCountryFocus(countryFocusOptions[0] ?? "India");
    }
  }, [lensType, countryFocus, countryFocusOptions]);

  const overallCriticality = useMemo(() => {
    return snapshot?.overall_criticality.score ?? 0;
  }, [snapshot]);

  const bucketSplit = useMemo(() => {
    if (!snapshot) {
      return { hard: 0, market: 0, soft: 0 };
    }
    const lookup = Object.fromEntries(snapshot.forces.map((f) => [f.name, f.score]));
    const hard = (lookup.military ?? 0) + (lookup.cyber ?? 0);
    const market = lookup.economic ?? 0;
    const soft = (lookup.diplomatic ?? 0) + (lookup.narrative ?? 0) + (lookup.ideological ?? 0);
    const total = hard + market + soft || 1;
    return {
      hard: hard / total,
      market: market / total,
      soft: soft / total,
    };
  }, [snapshot]);

  const methodTopRows = useMemo(() => {
    if (!snapshot) {
      return [];
    }
    return [
      { method: "Driving Forces", row: snapshot.scenario_methods.driving_forces[0] },
      { method: "Game Theory", row: snapshot.scenario_methods.game_theory[0] },
      { method: "Chessboard", row: snapshot.scenario_methods.chessboard[0] },
    ];
  }, [snapshot]);

  const scenarioClusters = useMemo(() => {
    const base: Record<ScenarioClusterKey, ScenarioRow[]> = {
      escalation: [],
      maritime_shock: [],
      hybrid_fragmentation: [],
      stabilization: [],
    };
    (snapshot?.scenarios ?? []).forEach((row) => {
      const cluster = mapScenarioCluster(row.name);
      base[cluster].push(row);
    });

    return (Object.keys(base) as ScenarioClusterKey[]).map((key) => {
      const rows = [...base[key]].sort((a, b) => b.probability - a.probability);
      const totalProbability = rows.reduce((acc, row) => acc + row.probability, 0);
      const avgDelta = rows.length > 0 ? rows.reduce((acc, row) => acc + row.delta_pct, 0) / rows.length : 0;
      return {
        key,
        title: CLUSTER_META[key].title,
        subtitle: CLUSTER_META[key].subtitle,
        rows,
        top: rows[0] ?? null,
        totalProbability,
        avgDelta,
      };
    });
  }, [snapshot]);

  const topScenarioLead = useMemo(() => {
    const ranked = [...(snapshot?.scenarios ?? [])].sort((a, b) => b.probability - a.probability);
    const top = ranked[0];
    const second = ranked[1];
    return {
      topProbability: top?.probability ?? 0,
      secondProbability: second?.probability ?? 0,
      label: leadStrength(top?.probability ?? 0, second?.probability ?? 0),
    };
  }, [snapshot]);

  const visibleCountries = useMemo(() => {
    const all = snapshot?.impacts.countries ?? [];
    if (lensType !== "country") {
      return all;
    }
    const focus = countryFocus.toLowerCase();
    return all.filter((item) => normalizedCountryName(item.label).toLowerCase() === focus);
  }, [snapshot, lensType, countryFocus]);

  const countryMapPoints = useMemo(() => {
    return visibleCountries
      .map((item) => {
        const normalized = normalizedCountryName(item.label);
        const coord = COUNTRY_COORDS[normalized];
        if (!coord) {
          return null;
        }
        return {
          label: item.label,
          severity: item.severity,
          directness: item.directness ?? "indirect",
          lon: coord.lon,
          lat: coord.lat,
        };
      })
      .filter((item): item is { label: string; severity: number; directness: string; lon: number; lat: number } => item !== null);
  }, [visibleCountries]);

  useEffect(() => {
    const loadCatalog = async () => {
      const response = await fetch(`${apiBase}/v1/issues`);
      if (!response.ok) {
        throw new Error("Failed to load issue catalog.");
      }
      const payload = (await response.json()) as { issues: IssueItem[] };
      setIssues(payload.issues);
    };
    void loadCatalog().catch(() => setError("Issue catalog unavailable."));
  }, []);

  useEffect(() => {
    const fetchSnapshot = async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await fetch(`${apiBase}/v1/analyze`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            selected_issues: selectedIssues,
            use_live: true,
            lens: lensType,
            focus: activeLensFocus || null,
          }),
        });
        if (!response.ok) {
          throw new Error(`Analyze failed (${response.status})`);
        }
        const payload = (await response.json()) as Snapshot;
        setSnapshot(payload);
      } catch {
        setError("Live analysis unavailable. API may be down.");
      } finally {
        setLoading(false);
      }
    };
    void fetchSnapshot();
  }, [selectedIssueParam, selectedIssues, lensType, activeLensFocus]);

  useEffect(() => {
    if (!selectedIssueParam) {
      return undefined;
    }
    const source = new EventSource(
      `${apiBase}/v1/analyze/stream?issues=${encodeURIComponent(selectedIssueParam)}&use_live=true&lens=${encodeURIComponent(lensType)}&focus=${encodeURIComponent(activeLensFocus)}&interval_seconds=30`
    );
    source.addEventListener("snapshot", (event) => {
      const parsed = JSON.parse((event as MessageEvent).data) as Snapshot;
      setSnapshot(parsed);
    });
    source.onerror = () => source.close();
    return () => source.close();
  }, [selectedIssueParam, lensType, activeLensFocus]);

  const toggleIssue = (slug: string) => {
    setSelectedIssues((prev) => {
      if (prev.includes(slug)) {
        return prev.filter((s) => s !== slug);
      }
      return [...prev, slug];
    });
  };

  return (
    <main className="page-shell visual-heavy">
      <section className="hero">
        <div>
          <p className="eyebrow">Geopolitical State Engine</p>
          <h1>One-page scenario command dashboard</h1>
          <p className="subcopy">
            <span className="live-dot" /> {snapshot?.mode?.toUpperCase() ?? "LIVE"} feed | {snapshot?.generated_utc ? new Date(snapshot.generated_utc).toLocaleString() : "updating"}
          </p>
        </div>
        <div className="hero-gauges">
          <div className="gauge-row">
            <GaugeDial
              title="Systemic Criticality"
              score={overallCriticality}
              percent={snapshot?.overall_criticality.percent ?? Math.round(overallCriticality * 100)}
              band={snapshot?.overall_criticality.band ?? severityBandFromScore(overallCriticality)}
              emphasis="primary"
            />
            <GaugeDial
              title="Conflict Escalation"
              score={snapshot?.conflict_escalation.score ?? 0}
              percent={snapshot?.conflict_escalation.percent ?? Math.round((snapshot?.conflict_escalation.score ?? 0) * 100)}
              band={snapshot?.conflict_escalation.band ?? "Unknown"}
              emphasis="secondary"
            />
          </div>
          <details>
            <summary>Advanced details</summary>
            <p className="muted mini">
              Systemic: {snapshot?.overall_criticality.meaning ?? "Composite near-term instability score."}
            </p>
            <p className="muted mini">
              Conflict: {snapshot?.conflict_escalation.meaning ?? ""}
            </p>
            <p className="muted mini">
              Formula: regional-war ({weightRole(snapshot?.overall_criticality.formula.regional_war_escalation ?? 0)}), maritime-shock (
              {weightRole(snapshot?.overall_criticality.formula.maritime_infrastructure_shock ?? 0)}), military (
              {weightRole(snapshot?.overall_criticality.formula.military_force ?? 0)}), economic (
              {weightRole(snapshot?.overall_criticality.formula.economic_force ?? 0)})
            </p>
          </details>
        </div>
      </section>

      <section className="panel compact controls-line">
        <div className="control-block">
          <h2>Issue Buckets</h2>
          <p className="muted mini-label">Toggle issue buckets</p>
          <div className="chip-grid">
            {issues.map((issue) => {
              const selected = selectedIssues.includes(issue.slug);
              return (
                <button
                  type="button"
                  key={issue.slug}
                  className={selected ? "chip selected" : "chip"}
                  onClick={() => toggleIssue(issue.slug)}
                >
                  {issue.label}
                </button>
              );
            })}
          </div>
          <p className="muted mini">
            Active: {selectedIssues.length}
          </p>
        </div>
        <div className="control-block">
          <h2>Impact Lens</h2>
          <p className="muted mini-label">Global / region / country scope</p>
          <div className="lens-row">
            <div className="chip-grid">
              {(["global", "region", "country"] as const).map((lens) => (
                <button
                  type="button"
                  key={lens}
                  className={lensType === lens ? "chip selected" : "chip"}
                  onClick={() => setLensType(lens)}
                >
                  {lens}
                </button>
              ))}
            </div>
            {lensType === "region" && (
              <select className="lens-select" value={regionFocus} onChange={(event) => setRegionFocus(event.target.value)}>
                {regionFocusOptions.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            )}
            {lensType === "country" && (
              <select className="lens-select" value={countryFocus} onChange={(event) => setCountryFocus(event.target.value)}>
                {countryFocusOptions.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            )}
          </div>
          <p className="muted mini">
            Active lens: {lensType}
            {activeLensFocus ? ` (${activeLensFocus})` : ""}
          </p>
        </div>
      </section>

      <section className="panel">
        <h2>{lensType === "country" ? "Country Focus Impact Map" : "Country Impact Map"}</h2>
        <div className="map-live-grid full-width">
          <div className="country-map-wrap">
            <ImpactMap points={countryMapPoints} lensType={lensType} lensFocus={activeLensFocus} />
            <p className="muted mini">OpenStreetMap overlay. Color = severity, larger marker = direct exposure.</p>
          </div>
          <div className="live-tape-box">
            <h3>Live Update Tape</h3>
            {loading && <p className="muted mini">Refreshing...</p>}
            {error && <p className="error">{error}</p>}
            <div className="live-tape-scroll">
              <ul className="signal-list">
                {(snapshot?.signals ?? []).map((signal) => (
                  <li key={`${signal.link}-${signal.title}`}>
                    <a href={signal.link} target="_blank" rel="noreferrer">{signal.title}</a>
                    <p className="muted">
                      {signal.source} | {signal.issue} | {signal.published_utc ? new Date(signal.published_utc).toLocaleTimeString() : "time unknown"}
                    </p>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </section>

      <section className="panel">
        <h2>Region / Worldwide Impact</h2>
        <div className="impact-grid">
          {(snapshot?.impacts.regions_world ?? []).map((item) => (
            <div key={item.label} className="impact-card">
              <p>{item.label}</p>
              <div className="mini-battery"><div className="mini-battery-fill" style={{ width: `${Math.round(item.severity * 100)}%`, background: severityColor(item.severity) }} /></div>
              <strong>{impactLevel(item.severity)} impact | {severityBandFromScore(item.severity)} severity</strong>
              <p className="muted mini">{item.summary}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="panel compact">
        <h2>Method Weights (Dynamic Fusion)</h2>
        <p className="muted mini">
          Derived automatically from model state + analyst-panel consensus. Not user-selectable.
        </p>
        <div className="weight-pills">
          <span className="chip selected">Driving forces {Math.round((snapshot?.scenario_methods.consensus.weights.driving_forces ?? 0) * 100)}%</span>
          <span className="chip">Game theory {Math.round((snapshot?.scenario_methods.consensus.weights.game_theory ?? 0) * 100)}%</span>
          <span className="chip">Chessboard {Math.round((snapshot?.scenario_methods.consensus.weights.chessboard ?? 0) * 100)}%</span>
          <span className="chip">Disagreement {(snapshot?.scenario_methods.consensus.disagreement_index ?? 0).toFixed(3)}</span>
        </div>
        <div className="weight-bars">
          <div className="weight-row">
            <span>Driving forces</span>
            <div className="weight-track">
              <div className="weight-fill" style={{ width: `${Math.round((snapshot?.scenario_methods.consensus.weights.driving_forces ?? 0) * 100)}%` }} />
            </div>
          </div>
          <div className="weight-row">
            <span>Game theory</span>
            <div className="weight-track">
              <div className="weight-fill" style={{ width: `${Math.round((snapshot?.scenario_methods.consensus.weights.game_theory ?? 0) * 100)}%` }} />
            </div>
          </div>
          <div className="weight-row">
            <span>Chessboard</span>
            <div className="weight-track">
              <div className="weight-fill" style={{ width: `${Math.round((snapshot?.scenario_methods.consensus.weights.chessboard ?? 0) * 100)}%` }} />
            </div>
          </div>
        </div>
        <p className="muted mini">{snapshot?.scenario_methods.consensus.derived_from ?? "Resolver metadata loading..."}</p>
        <p className="muted mini">{snapshot?.scenario_methods.consensus.analyst_panel_consensus ?? ""}</p>
      </section>

      <section className="grid-3">
        <article className="panel">
          <h2>State + Trend</h2>
          <p className="state">{snapshot?.current_state.label ?? "Loading..."}</p>
          <p className="muted">Confidence: {confidenceLabel(snapshot?.current_state.confidence ?? 0)}</p>
          <p className={`trend-pill trend-${snapshot?.trend ?? "stable"}`}>{(snapshot?.trend ?? "stable").toUpperCase()}</p>
          <p className="muted mini">{trendMeaning(snapshot?.current_state.label ?? "", snapshot?.trend ?? "stable")}</p>
        </article>

        <article className="panel">
          <h2>Strategic Force Split</h2>
          <ul className="metric-list">
            <li><span>Hard power (military + cyber)</span><strong>{impactLevel(bucketSplit.hard)} impact</strong></li>
            <li><span>Market pressure (economic)</span><strong>{impactLevel(bucketSplit.market)} impact</strong></li>
            <li><span>Soft power (diplomatic + narrative + ideological)</span><strong>{impactLevel(bucketSplit.soft)} impact</strong></li>
          </ul>
        </article>

        <article className="panel">
          <h2>Consensus Brief</h2>
          <p className="muted mini">Single consolidated output from the multi-analyst panel.</p>
          <pre className="analysis-box compact">
            {snapshot?.expert_review.consensus_brief ?? "Consensus pending..."}
            {"\n"}
            {`Next likely scenario: ${snapshot?.next_scenario_forecast.scenario ?? "Unknown"} (${impactLevel(snapshot?.next_scenario_forecast.probability ?? 0)} confidence)`}
          </pre>
        </article>
      </section>

      <section className="panel">
        <details>
          <summary>How Scenario Is Built (expand)</summary>
          <p className="muted mini">
            Consensus uses weighted fusion:
            {" "}
            Driving Forces {weightRole(snapshot?.scenario_methods.consensus.weights.driving_forces ?? 0)},
            {" "}
            Game Theory {weightRole(snapshot?.scenario_methods.consensus.weights.game_theory ?? 0)},
            {" "}
            Chessboard {weightRole(snapshot?.scenario_methods.consensus.weights.chessboard ?? 0)}.
          </p>
          <p className="muted mini">
            Method disagreement: {disagreementBand(snapshot?.scenario_methods.consensus.disagreement_index ?? 0)}
          </p>
          <div className="impact-grid">
            {methodTopRows.map((item) => (
              <div key={item.method} className="impact-card">
                <p><strong>{item.method}</strong></p>
                <p className="muted mini">
                  Top scenario: {item.row?.name ?? "Unknown"} ({impactLevel(item.row?.probability ?? 0)} confidence)
                </p>
              </div>
            ))}
          </div>
          <details>
            <summary>Projected next actor moves ({snapshot?.next_scenario_forecast.horizon_steps ?? 0}-step horizon)</summary>
            <ul className="signal-list">
              {(snapshot?.next_scenario_forecast.actor_moves ?? []).map((move) => (
                <li key={`${move.actor}-${move.move}`}>
                  <p>
                    {move.actor}: {move.move} ({impactLevel(move.confidence)} confidence)
                  </p>
                </li>
              ))}
            </ul>
            <p className="muted mini">{snapshot?.next_scenario_forecast.rationale ?? ""}</p>
          </details>
        </details>
      </section>

      <section className="panel">
        <details>
          <summary>Consistency Notes (expand)</summary>
          <ul className="signal-list">
            {(snapshot?.consistency_notes ?? []).length > 0 ? (
              (snapshot?.consistency_notes ?? []).map((note) => (
                <li key={note}>
                  <p>{note}</p>
                </li>
              ))
            ) : (
              <li><p>No contradiction flags detected in current snapshot.</p></li>
            )}
          </ul>
        </details>
      </section>

      <section className="panel">
        <h2>Most Likely Next Move</h2>
        <div className="prediction-strip">
          <div className="prediction-main">
            <p className="muted">Scenario</p>
            <p className="state">{snapshot?.impacts.prediction.most_likely_scenario ?? "Loading..."}</p>
            <p className="muted">Lead strength: {topScenarioLead.label}</p>
            <p className="muted mini">This is the relative leader among tracked paths.</p>
          </div>
          <p className="prediction-brief">{snapshot?.impacts.prediction.brief ?? "Waiting for prediction..."}</p>
        </div>
      </section>

      <section className="panel">
        <h2>Scenario Lattice (Primary 4)</h2>
        <div className="scenario-grid">
          {scenarioClusters.map((cluster) => (
            <div key={cluster.key} className="scenario-card">
              <h3>{cluster.title}</h3>
              <p className="muted mini">{cluster.subtitle}</p>
              <div className="mini-battery">
                <div
                  className="mini-battery-fill"
                  style={{ width: `${Math.round(cluster.totalProbability * 100)}%`, background: severityColor(cluster.totalProbability) }}
                />
              </div>
              <p className="muted mini">
                Likelihood: {impactLevel(cluster.totalProbability)} | Severity: {severityBandFromScore(cluster.totalProbability)}
              </p>
              <p className={cluster.avgDelta >= 0 ? "delta up" : "delta down"}>{cluster.avgDelta >= 0 ? "Rising momentum" : "Cooling momentum"}</p>
              <p className="muted mini">Lead: {cluster.top?.name ?? "No active scenario"}</p>
              <details>
                <summary>Secondary scenarios</summary>
                <ul className="signal-list">
                  {cluster.rows.slice(1).map((row) => (
                    <li key={`${cluster.key}-${row.name}`}>
                      <p>
                        {row.name} | {impactLevel(row.probability)} likelihood | {row.delta_pct >= 0 ? "rising" : "cooling"}
                      </p>
                    </li>
                  ))}
                  {cluster.rows.length <= 1 && <li><p className="muted mini">No secondary scenarios in this group.</p></li>}
                </ul>
              </details>
            </div>
          ))}
        </div>
      </section>

      <section className={lensType === "country" ? "grid-1" : "grid-2"}>
        <article className="panel">
          <h2>Three-Sector Model Impact</h2>
          <div className="impact-grid">
            {(snapshot?.impacts.three_sector_model ?? []).map((item) => (
              <div key={item.label} className="impact-card">
                <p>{item.label}</p>
                <div className="mini-battery"><div className="mini-battery-fill" style={{ width: `${item.percent}%`, background: severityColor(item.severity) }} /></div>
                <strong>{impactLevel(item.severity)} impact | {item.band} severity</strong>
                <p className="muted mini">{item.summary}</p>
              </div>
            ))}
          </div>
        </article>

        <article className="panel">
          <h2>Maslow Risk Hierarchy</h2>
          <p className="muted mini">
            {snapshot?.impacts.maslow_hierarchy.explanation ?? "Hierarchy unavailable."}
          </p>
          <ul className="metric-list">
            {(snapshot?.impacts.maslow_hierarchy.levels ?? []).map((level) => (
              <li key={level.name}>
                <span>{level.name}</span>
                <strong>{impactLevel(level.score)} impact | {level.band}</strong>
              </li>
            ))}
          </ul>
          <p className="muted mini">
            Final hierarchy risk: {impactLevel(snapshot?.impacts.maslow_hierarchy.hierarchy_score ?? 0)} impact (
            {snapshot?.impacts.maslow_hierarchy.band ?? "Unknown"} severity)
          </p>
        </article>
      </section>

      <section className="grid-2">
        <article className="panel">
          <h2>Sector Impact</h2>
          <div className="impact-grid">
            {(snapshot?.impacts.sectors ?? []).map((item) => (
              <div key={item.label} className="impact-card">
                <p>{item.label}</p>
                <div className="mini-battery"><div className="mini-battery-fill" style={{ width: `${Math.round(item.severity * 100)}%`, background: severityColor(item.severity) }} /></div>
                <strong>{impactLevel(item.severity)} impact | {severityBandFromScore(item.severity)} severity</strong>
                <p className="muted mini">{item.summary}</p>
              </div>
            ))}
          </div>
        </article>
        <article className="panel">
          <h2>Economy / Safety / Security / Prices</h2>
          <div className="impact-grid">
            {(snapshot?.impacts.indicators ?? []).map((item) => (
              <div key={item.label} className="impact-card">
                <p>{item.label}</p>
                <div className="mini-battery"><div className="mini-battery-fill" style={{ width: `${Math.round(item.severity * 100)}%`, background: severityColor(item.severity) }} /></div>
                <strong>{impactLevel(item.severity)} impact | {severityBandFromScore(item.severity)} severity</strong>
                <p className="muted mini">{item.summary}</p>
              </div>
            ))}
          </div>
        </article>
      </section>

      <section className="grid-2">
        <article className="panel">
          <h2>Multi-Analyst Review Board</h2>
          <div className="impact-grid">
            {(snapshot?.expert_review.panel ?? []).map((item) => (
              <div key={`${item.role}-${item.region}`} className="impact-card">
                <p>
                  <strong>{item.role}</strong> ({item.region})
                </p>
                <p className="muted mini">{item.view}</p>
              </div>
            ))}
          </div>
          <p className="muted mini">{snapshot?.expert_review.consensus ?? ""}</p>
        </article>

        <article className="panel">
          <h2>Force Heat Buckets</h2>
          <Image src={forceImageDataUrl} alt="Force pressure visualization" className="viz-image" width={740} height={320} unoptimized />
        </article>
      </section>

      <section className="panel">
        <details>
          <summary>Expand underlying explanation and prediction</summary>
          <p>{snapshot?.explanation ?? "No explanation yet."}</p>
          <p>{snapshot?.prediction ?? "No prediction yet."}</p>
        </details>
      </section>
    </main>
  );
}
