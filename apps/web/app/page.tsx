"use client";

import Image from "next/image";
import { useEffect, useMemo, useState, type ChangeEvent } from "react";

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

  const mapPlotPoints = useMemo(() => {
    if (countryMapPoints.length === 0) {
      return [];
    }
    const lons = countryMapPoints.map((p) => p.lon);
    const lats = countryMapPoints.map((p) => p.lat);
    let minLon = Math.min(...lons);
    let maxLon = Math.max(...lons);
    let minLat = Math.min(...lats);
    let maxLat = Math.max(...lats);

    const lonSpan = Math.max(maxLon - minLon, 20);
    const latSpan = Math.max(maxLat - minLat, 12);
    const lonPad = lonSpan * 0.35;
    const latPad = latSpan * 0.35;
    minLon -= lonPad;
    maxLon += lonPad;
    minLat -= latPad;
    maxLat += latPad;

    const width = 880;
    const height = 360;
    const innerPad = 24;
    const plotWidth = width - innerPad * 2;
    const plotHeight = height - innerPad * 2;

    return countryMapPoints.map((p, idx) => {
      const x = innerPad + ((p.lon - minLon) / (maxLon - minLon)) * plotWidth;
      const y = innerPad + ((maxLat - p.lat) / (maxLat - minLat)) * plotHeight;
      return {
        ...p,
        x,
        y,
        labelDx: 10,
        labelDy: idx % 2 === 0 ? -10 : 14,
      };
    });
  }, [countryMapPoints]);

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

  const handleIssueMultiSelect = (event: ChangeEvent<HTMLSelectElement>) => {
    const values = Array.from(event.target.selectedOptions).map((option) => option.value);
    setSelectedIssues(values);
  };

  return (
    <main className="page-shell visual-heavy">
      <section className="hero">
        <div>
          <p className="eyebrow">Geopolitical State Engine</p>
          <h1>One-page scenario command dashboard</h1>
          <p className="subcopy">
            {snapshot?.mode?.toUpperCase() ?? "LIVE"} feed | {snapshot?.generated_utc ? new Date(snapshot.generated_utc).toLocaleString() : "updating"}
          </p>
        </div>
        <div className="criticality-card">
          <p>Systemic Criticality</p>
          <div className="battery-shell">
            <div
              className="battery-fill"
              style={{ width: `${Math.round(overallCriticality * 100)}%`, background: severityColor(overallCriticality) }}
            />
          </div>
          <strong style={{ color: severityColor(overallCriticality) }}>
            {snapshot?.overall_criticality.band ?? severityBandFromScore(overallCriticality)}
          </strong>
          <p className="muted mini">
            Impact: {impactLevel(overallCriticality)} | Severity:{" "}
            {snapshot?.overall_criticality.band ?? severityBandFromScore(overallCriticality)}
          </p>
          <p className="muted mini">
            Meaning: {snapshot?.overall_criticality.meaning ?? "Composite near-term instability score."}
          </p>
          <details>
            <summary>Formula</summary>
            <p className="muted mini">
              Regional-war scenario ({weightRole(snapshot?.overall_criticality.formula.regional_war_escalation ?? 0)}), maritime-shock
              ({weightRole(snapshot?.overall_criticality.formula.maritime_infrastructure_shock ?? 0)}), military force (
              {weightRole(snapshot?.overall_criticality.formula.military_force ?? 0)}), economic force (
              {weightRole(snapshot?.overall_criticality.formula.economic_force ?? 0)})
            </p>
          </details>
        </div>
      </section>

      <section className="panel compact compact-risk">
        <h2>Conflict Escalation Likelihood</h2>
        <div className="battery-shell">
          <div
            className="battery-fill"
            style={{ width: `${snapshot?.conflict_escalation.percent ?? 0}%`, background: severityColor((snapshot?.conflict_escalation.score ?? 0)) }}
          />
        </div>
        <p className="muted mini">
          Impact: {impactLevel(snapshot?.conflict_escalation.score ?? 0)} | Severity: {snapshot?.conflict_escalation.band ?? "Unknown"} |{" "}
          {snapshot?.conflict_escalation.meaning ?? ""}
        </p>
      </section>

      <section className="panel compact">
        <h2>Issue Buckets</h2>
        <p className="muted mini">Multi-select list (Ctrl/Cmd + Click)</p>
        <select className="multi-select" size={4} multiple value={selectedIssues} onChange={handleIssueMultiSelect}>
          {issues.map((issue) => (
            <option key={issue.slug} value={issue.slug}>
              {issue.label}
            </option>
          ))}
        </select>
        <p className="muted mini">Selected: {selectedIssues.length}</p>
      </section>

      <section className="panel compact">
        <h2>Impact Lens</h2>
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
      </section>

      <section className="panel compact monetization-panel">
        <h2>Premium Intelligence Modules</h2>
        <div className="monetization-grid">
          <div className="impact-card">
            <p><strong>Analyst Pro</strong></p>
            <p className="muted mini">Saved watchlists, custom alerts, and export packs.</p>
            <button type="button" className="chip selected">Start trial</button>
          </div>
          <div className="impact-card">
            <p><strong>Team Ops</strong></p>
            <p className="muted mini">Shared boards, consensus workflow, and approvals.</p>
            <button type="button" className="chip">Request demo</button>
          </div>
          <div className="impact-card">
            <p><strong>API Access</strong></p>
            <p className="muted mini">Programmatic scenarios, risk feeds, and webhooks.</p>
            <button type="button" className="chip">Contact sales</button>
          </div>
        </div>
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
        {lensType !== "country" && (
          <article className="panel">
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
          </article>
        )}
        <article className="panel">
          <h2>{lensType === "country" ? "Country Focus Impact" : "Country Impact"}</h2>
          <div className="country-map-wrap">
            <svg viewBox="0 0 880 360" className="country-map" role="img" aria-label="Country impact map">
              <rect x="0" y="0" width="880" height="360" rx="10" fill="#0f1723" />
              <g opacity="0.18" stroke="#9fb3cc" strokeWidth="1">
                <line x1="0" y1="90" x2="880" y2="90" />
                <line x1="0" y1="180" x2="880" y2="180" />
                <line x1="0" y1="270" x2="880" y2="270" />
                <line x1="220" y1="0" x2="220" y2="360" />
                <line x1="440" y1="0" x2="440" y2="360" />
                <line x1="660" y1="0" x2="660" y2="360" />
              </g>
              {mapPlotPoints.map((point) => (
                <g key={`map-${point.label}`} transform={`translate(${point.x}, ${point.y})`}>
                  <circle r={point.directness === "direct" ? 8 : 6} fill={severityColor(point.severity)} stroke="#e2e8f0" strokeWidth="1" />
                  <text x={point.labelDx} y={point.labelDy} fill="#e2e8f0" fontSize="12">
                    {point.label}
                  </text>
                </g>
              ))}
            </svg>
            <p className="muted mini">Auto-focused view. Color = severity, larger marker = direct exposure.</p>
          </div>
          <ul className="map-legend-list">
            {[...visibleCountries]
              .sort((a, b) => b.severity - a.severity)
              .map((item) => (
                <li key={`legend-${item.label}`}>
                  <span className="legend-dot" style={{ background: severityColor(item.severity) }} />
                  <span className="legend-name">{item.label}</span>
                  <span className="legend-meta">{impactLevel(item.severity)} | {severityBandFromScore(item.severity)} | {item.directness ?? "indirect"}</span>
                </li>
              ))}
          </ul>
          {visibleCountries.length === 0 && <p className="muted mini">No mapped country impact data for the current selection.</p>}
          <details>
            <summary>{lensType === "country" ? "Focused Country In Active Regions" : "Countries In Active Regions"}</summary>
            <div className="region-country-list">
              {(snapshot?.impacts.countries_by_region ?? []).map((group) => (
                <div key={group.region} className="region-country-group">
                  <p><strong>{group.region}</strong></p>
                  <p className="muted mini">
                    {group.countries.map((row) => `${row.name} (${row.directness})`).join(", ")}
                  </p>
                </div>
              ))}
            </div>
          </details>
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

      <section className="grid-2">
        <article className="panel">
          <h2>Live Update Tape</h2>
          {loading && <p className="muted">Refreshing...</p>}
          {error && <p className="error">{error}</p>}
          <ul className="signal-list">
            {(snapshot?.signals ?? []).slice(0, 8).map((signal) => (
              <li key={`${signal.link}-${signal.title}`}>
                <a href={signal.link} target="_blank" rel="noreferrer">{signal.title}</a>
                <p className="muted">
                  {signal.source} | {signal.issue} | {signal.published_utc ? new Date(signal.published_utc).toLocaleTimeString() : "time unknown"}
                </p>
              </li>
            ))}
          </ul>
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
