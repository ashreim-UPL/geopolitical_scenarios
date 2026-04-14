from __future__ import annotations

import asyncio
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

import httpx

_REPO_ROOT = Path(__file__).resolve().parents[5]
if str(_REPO_ROOT) not in sys.path:
    sys.path.append(str(_REPO_ROOT))

from packages.scenarios.weight_resolver import (  # noqa: E402
    ForceType,
    PhaseVelocity,
    SystemState,
    resolve_method_weights,
)

ISSUE_CATALOG: dict[str, str] = {
    "red-sea-shipping": "Red Sea shipping",
    "gulf-energy-security": "Gulf energy security",
    "us-china-technology": "US China technology",
    "taiwan-strait": "Taiwan Strait",
    "russia-ukraine-war": "Russia Ukraine war",
    "iran-israel-dynamics": "Iran Israel dynamics",
}


ISSUE_QUERIES: dict[str, str] = {
    "red-sea-shipping": "Red Sea shipping attacks OR Bab el-Mandeb OR Suez disruption",
    "gulf-energy-security": "Gulf refinery outage OR LNG disruption OR Hormuz throughput",
    "us-china-technology": "US China semiconductors sanctions export controls",
    "taiwan-strait": "Taiwan Strait military exercise incursion",
    "russia-ukraine-war": "Russia Ukraine missile strike sanctions frontline",
    "iran-israel-dynamics": "Iran Israel strike proxy escalation diplomatic signaling",
}


SCENARIOS: tuple[str, ...] = (
    "Managed confrontation",
    "Hybrid pressure equilibrium",
    "Maritime or infrastructure shock",
    "Controlled partial reopening or corridor deal",
    "Regional war escalation",
    "Internal fragmentation or political rupture",
    "Negotiated stabilization",
)

ACTORS: tuple[str, ...] = ("US", "Iran", "Israel", "Regional proxies", "Major importers")


FORCE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "military": ("strike", "attack", "missile", "drone", "troop", "naval", "incursion"),
    "economic": ("oil", "lng", "freight", "insurance", "sanction", "inflation", "market"),
    "diplomatic": ("summit", "talks", "ceasefire", "envoy", "meeting", "agreement", "deal"),
    "narrative": ("warning", "statement", "rhetoric", "threat", "media", "propaganda"),
    "ideological": (
        "ideology",
        "doctrine",
        "identity",
        "sectarian",
        "religious",
        "faith",
        "legitimacy",
        "narrative supremacy",
    ),
    "cyber": ("cyber", "hack", "malware", "outage", "network", "ransomware"),
}


SCENARIO_WEIGHTS: dict[str, dict[str, float]] = {
    "Managed confrontation": {"diplomatic": 1.2, "military": 0.7, "economic": 0.8},
    "Hybrid pressure equilibrium": {"military": 0.8, "narrative": 1.2, "cyber": 1.0},
    "Maritime or infrastructure shock": {"economic": 1.2, "military": 1.1},
    "Controlled partial reopening or corridor deal": {"diplomatic": 1.3, "economic": 0.9},
    "Regional war escalation": {"military": 1.4, "narrative": 0.8},
    "Internal fragmentation or political rupture": {"ideological": 1.1, "economic": 1.0, "narrative": 0.9},
    "Negotiated stabilization": {"diplomatic": 1.5, "military": 0.3},
}


FORCE_PRIORS: dict[str, float] = {
    "military": 0.19,
    "economic": 0.19,
    "diplomatic": 0.19,
    "narrative": 0.16,
    "ideological": 0.15,
    "cyber": 0.12,
}


ISSUE_REGION_MAPPING: dict[str, tuple[str, ...]] = {
    "red-sea-shipping": ("MENA", "Europe", "Global shipping lanes"),
    "gulf-energy-security": ("GCC", "Asia importers", "Global energy markets"),
    "us-china-technology": ("US", "China", "Global tech supply chains"),
    "taiwan-strait": ("East Asia", "US allies", "Global semiconductor hubs"),
    "russia-ukraine-war": ("Eastern Europe", "EU energy consumers", "Global grain routes"),
    "iran-israel-dynamics": ("Levant", "Gulf region", "Global energy chokepoints"),
}

LENS_TYPES = {"global", "region", "country"}

ISSUE_ESCALATION_PRESSURE: dict[str, float] = {
    "red-sea-shipping": 0.65,
    "gulf-energy-security": 0.7,
    "us-china-technology": 0.5,
    "taiwan-strait": 0.75,
    "russia-ukraine-war": 0.78,
    "iran-israel-dynamics": 0.82,
}

REGION_COUNTRY_EXPOSURE: dict[str, tuple[tuple[str, str, float], ...]] = {
    "Levant": (("Israel", "direct", 1.0), ("Lebanon", "direct", 0.95), ("Jordan", "indirect", 0.72), ("Egypt", "indirect", 0.74)),
    "Gulf region": (("Iran", "direct", 1.0), ("Saudi Arabia", "direct", 0.9), ("UAE", "direct", 0.86), ("Qatar", "indirect", 0.76), ("Bahrain", "indirect", 0.72), ("Kuwait", "indirect", 0.74), ("Oman", "indirect", 0.7)),
    "MENA": (("Turkey", "indirect", 0.73), ("Iraq", "direct", 0.88), ("Syria", "direct", 0.9)),
    "Europe": (("Germany", "indirect", 0.68), ("France", "indirect", 0.66), ("Italy", "indirect", 0.67), ("United Kingdom", "indirect", 0.69)),
    "EU energy consumers": (("Poland", "indirect", 0.65), ("Netherlands", "indirect", 0.62)),
    "Eastern Europe": (("Ukraine", "direct", 1.0), ("Russia", "direct", 0.98), ("Romania", "indirect", 0.71)),
    "East Asia": (("Taiwan", "direct", 1.0), ("Japan", "indirect", 0.74), ("South Korea", "indirect", 0.72)),
    "US allies": (("United States", "indirect", 0.76), ("Australia", "indirect", 0.64)),
    "Asia importers": (("India", "indirect", 0.78), ("Pakistan", "indirect", 0.63), ("Bangladesh", "indirect", 0.58), ("Singapore", "indirect", 0.6)),
    "China": (("China", "indirect", 0.8),),
    "US": (("United States", "indirect", 0.78),),
    "Global shipping lanes": (("Greece", "indirect", 0.62), ("Panama", "indirect", 0.58)),
    "Global energy chokepoints": (("India", "indirect", 0.8), ("China", "indirect", 0.82), ("South Korea", "indirect", 0.72)),
}

REGION_BASE_MULTIPLIER: dict[str, float] = {
    "Levant": 1.15,
    "Gulf region": 1.12,
    "Global energy chokepoints": 1.1,
    "Global shipping lanes": 1.08,
    "MENA": 1.06,
    "Eastern Europe": 1.07,
    "EU energy consumers": 1.0,
    "Europe": 0.98,
    "East Asia": 1.03,
    "US allies": 0.96,
    "Asia importers": 1.02,
    "US": 0.94,
    "China": 0.97,
}

RISK_BANDS: tuple[tuple[int, int, str], ...] = (
    (0, 20, "Low"),
    (21, 40, "Guarded"),
    (41, 60, "Elevated"),
    (61, 80, "High"),
    (81, 100, "Critical"),
)


@dataclass(slots=True)
class SignalItem:
    title: str
    link: str
    source: str
    published_utc: datetime | None
    issue: str
    summary: str = ""


def _to_google_news_rss_url(query: str) -> str:
    encoded = query.replace(" ", "+")
    return f"https://news.google.com/rss/search?q={encoded}&hl=en-US&gl=US&ceid=US:en"


def _safe_parse_datetime(raw_value: str) -> datetime | None:
    if not raw_value:
        return None
    try:
        parsed = parsedate_to_datetime(raw_value)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)
    except (TypeError, ValueError):
        return None


def _extract_text(node: ElementTree.Element | None) -> str:
    return "" if node is None or node.text is None else node.text.strip()


def _score_forces(text: str) -> dict[str, float]:
    lowered = text.lower()
    scores: dict[str, float] = {}
    for force, keywords in FORCE_KEYWORDS.items():
        hit_count = sum(1 for token in keywords if token in lowered)
        scores[force] = round(min(hit_count / 5, 1.0), 3)
    return scores


def _aggregate_forces(items: list[SignalItem]) -> dict[str, float]:
    totals = {force: 0.0 for force in FORCE_KEYWORDS}
    if not items:
        return FORCE_PRIORS.copy()
    for item in items:
        text = f"{item.title} {item.summary}"
        scores = _score_forces(text)
        for force, value in scores.items():
            totals[force] += value

    # Convert keyword-density signals into a probability split with non-zero priors.
    # This guarantees ideology/perception never collapses to zero and no single force reaches 100% alone.
    scaled: dict[str, float] = {}
    for force, prior in FORCE_PRIORS.items():
        scaled[force] = prior + (totals.get(force, 0.0) * 0.45)

    total_mass = sum(scaled.values()) or 1.0
    distribution = {force: round(value / total_mass, 4) for force, value in scaled.items()}

    # Correct rounding drift so percentages sum exactly to 1.0.
    drift = round(1.0 - sum(distribution.values()), 4)
    if drift != 0:
        top_force = max(distribution, key=distribution.get)
        distribution[top_force] = round(distribution[top_force] + drift, 4)
    return distribution


def _compute_scenarios(force_totals: dict[str, float]) -> list[dict[str, Any]]:
    base_prior = 1 / len(SCENARIOS)
    weighted_scores: dict[str, float] = {}
    for scenario in SCENARIOS:
        weight_map = SCENARIO_WEIGHTS[scenario]
        score = base_prior
        for force, weight in weight_map.items():
            score += force_totals.get(force, 0.0) * weight * 0.2
        weighted_scores[scenario] = score

    total = sum(weighted_scores.values()) or 1.0
    probabilities: list[dict[str, Any]] = []
    for name, score in weighted_scores.items():
        probability = score / total
        delta = (probability - base_prior) * 100
        probabilities.append(
            {
                "name": name,
                "probability": round(probability, 4),
                "delta_pct": round(delta, 2),
            }
        )
    probabilities.sort(key=lambda row: row["probability"], reverse=True)
    return probabilities


def _list_to_map(rows: list[dict[str, Any]]) -> dict[str, float]:
    return {row["name"]: float(row["probability"]) for row in rows}


def _map_to_ranked_rows(scores: dict[str, float]) -> list[dict[str, Any]]:
    total = sum(scores.values()) or 1.0
    base_prior = 1 / len(SCENARIOS)
    rows: list[dict[str, Any]] = []
    for scenario in SCENARIOS:
        probability = scores.get(scenario, 0.0) / total
        delta = (probability - base_prior) * 100
        rows.append(
            {
                "name": scenario,
                "probability": round(probability, 4),
                "delta_pct": round(delta, 2),
            }
        )
    rows.sort(key=lambda row: row["probability"], reverse=True)
    return rows


def _driving_forces_method(force_totals: dict[str, float]) -> list[dict[str, Any]]:
    return _compute_scenarios(force_totals)


def _game_theory_method(force_totals: dict[str, float], issue_pressure: float) -> list[dict[str, Any]]:
    # Simplified strategic utility model: actors optimize coercion vs stabilization under mixed constraints.
    aggression = (force_totals.get("military", 0.0) * 0.45) + (force_totals.get("ideological", 0.0) * 0.2) + (issue_pressure * 0.35)
    coordination = (force_totals.get("diplomatic", 0.0) * 0.55) + (0.2 * (1 - issue_pressure))
    economic_stress = force_totals.get("economic", 0.0)
    cyber_disruption = force_totals.get("cyber", 0.0)

    base = {scenario: 1.0 / len(SCENARIOS) for scenario in SCENARIOS}
    base["Regional war escalation"] += aggression * 0.22
    base["Maritime or infrastructure shock"] += (aggression * 0.14) + (economic_stress * 0.2)
    base["Hybrid pressure equilibrium"] += (cyber_disruption * 0.18) + (aggression * 0.08)
    base["Managed confrontation"] += (coordination * 0.11) + (aggression * 0.05)
    base["Negotiated stabilization"] += coordination * 0.16
    base["Controlled partial reopening or corridor deal"] += coordination * 0.12
    base["Internal fragmentation or political rupture"] += (force_totals.get("narrative", 0.0) * 0.1) + (aggression * 0.06)
    return _map_to_ranked_rows(base)


def _best_move_for_actor(actor: str, *, aggression: float, coordination: float, economic_stress: float) -> tuple[str, float]:
    if actor in {"Iran", "Regional proxies"}:
        if aggression > 0.62:
            return ("asymmetric-escalation", min(0.85, aggression))
        return ("coercive-signaling", min(0.75, aggression + 0.08))
    if actor == "Israel":
        if aggression > 0.58:
            return ("preemptive-strike-posture", min(0.84, aggression + 0.06))
        return ("deterrence-maintenance", 0.64)
    if actor == "US":
        if coordination > aggression:
            return ("diplomatic-containment", min(0.82, coordination + 0.1))
        return ("force-projection", min(0.8, aggression + 0.05))
    # Major importers
    if economic_stress > 0.5:
        return ("supply-hedging", min(0.86, economic_stress + 0.12))
    return ("watchful-balancing", 0.6)


def _apply_move_effect(scores: dict[str, float], move: str, strength: float) -> None:
    if move in {"asymmetric-escalation", "preemptive-strike-posture", "force-projection"}:
        scores["Regional war escalation"] += 0.05 * strength
        scores["Maritime or infrastructure shock"] += 0.035 * strength
        scores["Negotiated stabilization"] -= 0.03 * strength
    elif move in {"coercive-signaling", "deterrence-maintenance"}:
        scores["Managed confrontation"] += 0.03 * strength
        scores["Hybrid pressure equilibrium"] += 0.028 * strength
    elif move == "diplomatic-containment":
        scores["Negotiated stabilization"] += 0.04 * strength
        scores["Controlled partial reopening or corridor deal"] += 0.03 * strength
        scores["Regional war escalation"] -= 0.02 * strength
    elif move == "supply-hedging":
        scores["Maritime or infrastructure shock"] += 0.03 * strength
        scores["Managed confrontation"] += 0.012 * strength
    elif move == "watchful-balancing":
        scores["Managed confrontation"] += 0.01 * strength


def _chessboard_method(
    force_totals: dict[str, float],
    issue_pressure: float,
    *,
    iterations: int = 4,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    # Finite-horizon simulation (no recursion): each actor picks one best-response move per step.
    aggression = (force_totals.get("military", 0.0) * 0.48) + (force_totals.get("ideological", 0.0) * 0.2) + (issue_pressure * 0.32)
    coordination = (force_totals.get("diplomatic", 0.0) * 0.56) + (0.18 * (1 - issue_pressure))
    economic_stress = force_totals.get("economic", 0.0)

    scores = {scenario: 1.0 / len(SCENARIOS) for scenario in SCENARIOS}
    last_moves: list[dict[str, Any]] = []
    steps = max(1, min(iterations, 6))
    for _ in range(steps):
        for actor in ACTORS:
            move, confidence = _best_move_for_actor(
                actor,
                aggression=aggression,
                coordination=coordination,
                economic_stress=economic_stress,
            )
            _apply_move_effect(scores, move, confidence)
            last_moves.append({"actor": actor, "move": move, "confidence": round(confidence, 2)})
        aggression = min(1.0, aggression * 1.01)
        coordination = max(0.0, coordination * 0.99)

    return _map_to_ranked_rows(scores), last_moves[-len(ACTORS):]


def _infer_system_state(issue_pressure: float, force_totals: dict[str, float]) -> SystemState:
    military_pressure = force_totals.get("military", 0.0) + force_totals.get("cyber", 0.0)
    diplomatic_pressure = force_totals.get("diplomatic", 0.0)
    if issue_pressure >= 0.8 and military_pressure >= 0.36:
        return SystemState.PRE_WAR_TRANSITION
    if issue_pressure >= 0.88:
        return SystemState.REGIONAL_WAR
    if military_pressure >= 0.42:
        return SystemState.HYBRID_ESCALATION
    if force_totals.get("economic", 0.0) >= 0.32:
        return SystemState.MARITIME_PRESSURE
    if diplomatic_pressure >= 0.3 and issue_pressure <= 0.6:
        return SystemState.NEGOTIATED_STABILIZATION
    return SystemState.CONTROLLED_INSTABILITY


def _infer_phase_velocity(trend: str, issue_pressure: float) -> PhaseVelocity:
    if trend == "rising" or issue_pressure >= 0.78:
        return PhaseVelocity.ACCELERATING
    if trend == "cooling" and issue_pressure <= 0.52:
        return PhaseVelocity.DECELERATING
    return PhaseVelocity.STABLE


def _infer_dominant_force_type(force_totals: dict[str, float]) -> ForceType:
    military_block = force_totals.get("military", 0.0) + force_totals.get("cyber", 0.0)
    economic = force_totals.get("economic", 0.0)
    narrative_block = force_totals.get("narrative", 0.0) + force_totals.get("ideological", 0.0)
    if military_block >= max(economic, narrative_block):
        return ForceType.MILITARY
    if economic >= max(military_block, narrative_block):
        return ForceType.ECONOMIC
    if narrative_block >= max(military_block, economic):
        return ForceType.NARRATIVE
    return ForceType.BALANCED


def _analyst_panel_weight_recommendation(force_totals: dict[str, float], issue_pressure: float) -> dict[str, float]:
    diplomatic = force_totals.get("diplomatic", 0.0)
    narrative = force_totals.get("narrative", 0.0)
    ideological = force_totals.get("ideological", 0.0)
    military = force_totals.get("military", 0.0)
    cyber = force_totals.get("cyber", 0.0)
    economic = force_totals.get("economic", 0.0)

    panel_profiles = [
        (diplomatic + narrative + 0.2, {"driving_forces": 0.25, "game_theory": 0.5, "chessboard": 0.25}),  # Political analyst
        (economic + 0.2, {"driving_forces": 0.6, "game_theory": 0.25, "chessboard": 0.15}),  # Economist
        (military + cyber + 0.2, {"driving_forces": 0.2, "game_theory": 0.25, "chessboard": 0.55}),  # Military planner
        ((1 - issue_pressure) + 0.15, {"driving_forces": 0.55, "game_theory": 0.3, "chessboard": 0.15}),  # Academic
        (ideological + narrative + 0.2, {"driving_forces": 0.3, "game_theory": 0.5, "chessboard": 0.2}),  # Ideology analyst
    ]

    total_vote = sum(weight for weight, _ in panel_profiles) or 1.0
    blended = {"driving_forces": 0.0, "game_theory": 0.0, "chessboard": 0.0}
    for vote_weight, profile in panel_profiles:
        scale = vote_weight / total_vote
        for key in blended:
            blended[key] += profile[key] * scale
    return blended


def _consensus_scenarios(
    driving_rows: list[dict[str, Any]],
    game_rows: list[dict[str, Any]],
    chess_rows: list[dict[str, Any]],
    *,
    force_totals: dict[str, float],
    issue_pressure: float,
    trend: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    driving_map = _list_to_map(driving_rows)
    game_map = _list_to_map(game_rows)
    chess_map = _list_to_map(chess_rows)
    system_state = _infer_system_state(issue_pressure, force_totals)
    phase_velocity = _infer_phase_velocity(trend, issue_pressure)
    dominant_force_type = _infer_dominant_force_type(force_totals)
    base_weights = resolve_method_weights(
        system_state=system_state,
        phase_velocity=phase_velocity,
        dominant_force_type=dominant_force_type,
    )
    analyst_weights = _analyst_panel_weight_recommendation(force_totals, issue_pressure)
    blend_model = 0.65
    blend_panel = 0.35
    weights = {
        "driving_forces": round((base_weights.driving_forces * blend_model) + (analyst_weights["driving_forces"] * blend_panel), 4),
        "game_theory": round((base_weights.game_theory * blend_model) + (analyst_weights["game_theory"] * blend_panel), 4),
        "chessboard": round((base_weights.chessboard * blend_model) + (analyst_weights["chessboard"] * blend_panel), 4),
    }
    weight_total = weights["driving_forces"] + weights["game_theory"] + weights["chessboard"]
    weights = {key: round(value / (weight_total or 1.0), 4) for key, value in weights.items()}

    consensus_scores: dict[str, float] = {}
    disagreement = 0.0
    for scenario in SCENARIOS:
        d = driving_map.get(scenario, 0.0)
        g = game_map.get(scenario, 0.0)
        c = chess_map.get(scenario, 0.0)
        consensus_scores[scenario] = (d * weights["driving_forces"]) + (g * weights["game_theory"]) + (c * weights["chessboard"])
        disagreement += max(d, g, c) - min(d, g, c)
    disagreement /= len(SCENARIOS)
    meta = {
        "weights": weights,
        "disagreement_index": round(disagreement, 4),
        "derived_from": base_weights.derived_from,
        "analyst_panel_consensus": "Five-lens panel recommendation blended with model state resolver (65/35).",
        "analyst_override": False,
    }
    return _map_to_ranked_rows(consensus_scores), meta


def _lens_formula_weights(lens: str) -> dict[str, float]:
    if lens == "region":
        return {
            "regional_war_escalation": 0.35,
            "maritime_infrastructure_shock": 0.35,
            "military_force": 0.15,
            "economic_force": 0.15,
        }
    if lens == "country":
        return {
            "regional_war_escalation": 0.3,
            "maritime_infrastructure_shock": 0.2,
            "military_force": 0.3,
            "economic_force": 0.2,
        }
    return {
        "regional_war_escalation": 0.4,
        "maritime_infrastructure_shock": 0.25,
        "military_force": 0.2,
        "economic_force": 0.15,
    }


def _issue_pressure(selected_issues: list[str]) -> float:
    if not selected_issues:
        return 0.55
    values = [ISSUE_ESCALATION_PRESSURE.get(issue, 0.55) for issue in selected_issues]
    return round(sum(values) / len(values), 4)


def _risk_band(score_0_to_1: float) -> dict[str, Any]:
    pct = int(round(max(0.0, min(1.0, score_0_to_1)) * 100))
    for low, high, label in RISK_BANDS:
        if low <= pct <= high:
            return {"label": label, "range": f"{low}-{high}", "percent": pct}
    return {"label": "Critical", "range": "81-100", "percent": pct}


def _band_rank(label: str) -> int:
    order = {"Low": 0, "Guarded": 1, "Elevated": 2, "High": 3, "Critical": 4}
    return order.get(label, 0)


def _calculate_overall_criticality(
    scenarios: list[dict[str, Any]],
    force_scores: dict[str, float],
    lens: str,
    issue_pressure: float,
    conflict_score: float | None = None,
) -> dict[str, Any]:
    scenario_lookup = {item["name"]: item["probability"] for item in scenarios}
    regional_war = scenario_lookup.get("Regional war escalation", 0.0)
    maritime_shock = scenario_lookup.get("Maritime or infrastructure shock", 0.0)
    military = force_scores.get("military", 0.0)
    economy = force_scores.get("economic", 0.0)
    formula = _lens_formula_weights(lens)
    weighted = (
        (regional_war * formula["regional_war_escalation"])
        + (maritime_shock * formula["maritime_infrastructure_shock"])
        + (military * formula["military_force"])
        + (economy * formula["economic_force"])
    )
    weighted = (weighted * 0.75) + (issue_pressure * 0.25)
    if conflict_score is not None:
        weighted = max(weighted, conflict_score * 0.6)
    clipped = max(0.0, min(1.0, weighted))
    band = _risk_band(clipped)
    return {
        "score": round(clipped, 4),
        "percent": band["percent"],
        "band": band["label"],
        "band_range": band["range"],
        "formula": formula,
        "meaning": "Higher means higher near-term instability and wider spillover risk.",
    }


def _calculate_conflict_escalation(
    scenarios: list[dict[str, Any]],
    force_scores: dict[str, float],
    issue_pressure: float,
) -> dict[str, Any]:
    scenario_lookup = {item["name"]: item["probability"] for item in scenarios}
    regional_war = scenario_lookup.get("Regional war escalation", 0.0)
    managed_confrontation = scenario_lookup.get("Managed confrontation", 0.0)
    military = force_scores.get("military", 0.0)
    ideological = force_scores.get("ideological", 0.0)
    score = (regional_war * 0.55) + (managed_confrontation * 0.1) + (military * 0.25) + (ideological * 0.1)
    score = (score * 0.65) + (issue_pressure * 0.35)
    if issue_pressure >= 0.75 and military >= 0.3:
        score = max(score, 0.5)
    score = max(0.0, min(1.0, score))
    band = _risk_band(score)
    return {
        "score": round(score, 4),
        "percent": band["percent"],
        "band": band["label"],
        "meaning": "Likelihood of conflict escalation path; different from broad systemic economic criticality.",
    }


def _consistency_warnings(
    top_state: str,
    trend: str,
    overall_criticality: dict[str, Any],
    conflict_escalation: dict[str, Any],
) -> list[str]:
    warnings: list[str] = []
    if top_state in {"Pre-war transition", "Regional war"} and trend == "stable":
        warnings.append("Stable trend here means plateau at high tension, not de-escalation.")
    if _band_rank(conflict_escalation["band"]) >= 3 and _band_rank(overall_criticality["band"]) <= 1:
        warnings.append("Conflict escalation risk can be high while broad economic-system criticality remains guarded.")
    return warnings


def _impact_card(label: str, score: float, summary: str) -> dict[str, Any]:
    return {"label": label, "severity": round(max(0.0, min(1.0, score)), 3), "summary": summary}


def _lens_multiplier(group: str, label: str, *, lens: str, focus: str | None) -> float:
    if lens == "global":
        return 1.0
    label_lower = label.lower()
    focus_lower = (focus or "").strip().lower()

    if lens == "region":
        if group == "regions_world":
            if focus_lower and focus_lower in label_lower:
                return 1.28
            return 0.9
        if group == "countries":
            if focus_lower in {"gulf", "mena", "levant"} and label_lower == "india":
                return 1.1
            return 0.95
        if group in {"sectors", "indicators"}:
            if label in {"Energy", "Shipping & Logistics", "Prices", "Security"}:
                return 1.08
            if focus_lower in {"gulf", "mena", "levant"} and label in {
                "Hospitality",
                "Tourism",
                "F&B, Restaurants, Nightlife",
                "Luxury Shopping",
                "Real Estate",
            }:
                return 1.14
            return 0.96

    if lens == "country":
        if group == "countries":
            if focus_lower and focus_lower == label_lower:
                return 1.35
            return 0.88
        if group in {"sectors", "indicators"}:
            return 1.1 if label in {"Technology", "Economy", "Prices", "Security"} else 0.95
        if group == "regions_world":
            return 0.95
    return 1.0


def _reweight_impact_group(items: list[dict[str, Any]], *, group: str, lens: str, focus: str | None) -> list[dict[str, Any]]:
    weighted: list[dict[str, Any]] = []
    for item in items:
        multiplier = _lens_multiplier(group, item["label"], lens=lens, focus=focus)
        severity = min(item["severity"] * multiplier, 1.0)
        band = _risk_band(severity)
        weighted.append({**item, "severity": round(severity, 3), "band": band["label"], "percent": band["percent"]})
    return sorted(weighted, key=lambda row: row["severity"], reverse=True)


def _build_three_sector_model(
    force_scores: dict[str, float],
    scenario_lookup: dict[str, float],
) -> list[dict[str, Any]]:
    primary_score = (
        (force_scores.get("economic", 0.0) * 0.45)
        + (scenario_lookup.get("Maritime or infrastructure shock", 0.0) * 0.35)
        + 0.1
    )
    secondary_score = (
        (force_scores.get("economic", 0.0) * 0.3)
        + (force_scores.get("cyber", 0.0) * 0.25)
        + (scenario_lookup.get("Regional war escalation", 0.0) * 0.2)
        + 0.1
    )
    tertiary_score = (
        (force_scores.get("narrative", 0.0) * 0.25)
        + (force_scores.get("diplomatic", 0.0) * 0.2)
        + (force_scores.get("economic", 0.0) * 0.2)
        + 0.12
    )
    rows = [
        _impact_card(
            label="Primary Sector",
            score=primary_score,
            summary="Raw materials, food, energy extraction and transport corridors.",
        ),
        _impact_card(
            label="Secondary Sector",
            score=secondary_score,
            summary="Manufacturing, industrial output, and infrastructure production continuity.",
        ),
        _impact_card(
            label="Tertiary Sector",
            score=tertiary_score,
            summary="Services, finance, insurance, logistics services, and policy-sensitive demand.",
        ),
    ]
    enriched: list[dict[str, Any]] = []
    for row in rows:
        band = _risk_band(row["severity"])
        enriched.append({**row, "band": band["label"], "percent": band["percent"]})
    return sorted(enriched, key=lambda row: row["severity"], reverse=True)


def _build_maslow_risk_hierarchy(force_scores: dict[str, float], scenario_lookup: dict[str, float]) -> dict[str, Any]:
    physiological = min(
        (force_scores.get("economic", 0.0) * 0.35)
        + (scenario_lookup.get("Maritime or infrastructure shock", 0.0) * 0.35)
        + 0.12,
        1.0,
    )
    safety = min(
        (force_scores.get("military", 0.0) * 0.45)
        + (force_scores.get("cyber", 0.0) * 0.25)
        + (scenario_lookup.get("Regional war escalation", 0.0) * 0.25)
        + 0.08,
        1.0,
    )
    social = min((force_scores.get("narrative", 0.0) * 0.4) + (force_scores.get("ideological", 0.0) * 0.35) + 0.08, 1.0)
    legitimacy = min((force_scores.get("diplomatic", 0.0) * 0.35) + (force_scores.get("narrative", 0.0) * 0.25) + 0.09, 1.0)
    future = min((force_scores.get("economic", 0.0) * 0.3) + (force_scores.get("cyber", 0.0) * 0.25) + 0.08, 1.0)

    levels = [
        {"name": "Physiological (Food/Energy Access)", "score": round(physiological, 3), "weight": 0.20},
        {"name": "Safety (Conflict/Security)", "score": round(safety, 3), "weight": 0.40},
        {"name": "Social Cohesion (Narrative/Identity)", "score": round(social, 3), "weight": 0.15},
        {"name": "Legitimacy (Political Confidence)", "score": round(legitimacy, 3), "weight": 0.15},
        {"name": "Future Capacity (Growth/Innovation)", "score": round(future, 3), "weight": 0.10},
    ]

    weighted_sum = sum(item["score"] * item["weight"] for item in levels)
    # Max-biased aggregation prevents severe safety risk from being averaged away.
    dominant = max(item["score"] for item in levels)
    hierarchy_score = min((weighted_sum * 0.6) + (dominant * 0.4), 1.0)
    hierarchy_band = _risk_band(hierarchy_score)

    enriched_levels: list[dict[str, Any]] = []
    for item in levels:
        band = _risk_band(item["score"])
        enriched_levels.append(
            {
                **item,
                "percent": band["percent"],
                "band": band["label"],
            }
        )

    return {
        "levels": enriched_levels,
        "weighted_score": round(weighted_sum, 4),
        "dominant_score": round(dominant, 4),
        "hierarchy_score": round(hierarchy_score, 4),
        "percent": hierarchy_band["percent"],
        "band": hierarchy_band["label"],
        "explanation": "Maslow-style risk hierarchy where Safety is heavily weighted and dominant-risk adjusted.",
    }


def _build_expert_review(
    *,
    top_state: str,
    trend: str,
    conflict_escalation: dict[str, Any],
    overall_criticality: dict[str, Any],
    impacts: dict[str, Any],
) -> dict[str, Any]:
    top_sector = impacts["sectors"][0]["label"] if impacts.get("sectors") else "Energy"
    top_indicator = impacts["indicators"][0]["label"] if impacts.get("indicators") else "Security"
    panel = [
        {
            "role": "Political Analyst",
            "region": "Middle East",
            "view": f"State is {top_state.lower()} with signaling competition still active; diplomatic channels are fragile.",
        },
        {
            "role": "Economist",
            "region": "Europe",
            "view": f"System-wide risk is {overall_criticality['band'].lower()}, but transmission to {top_sector.lower()} is likely persistent.",
        },
        {
            "role": "Military Planner",
            "region": "US",
            "view": f"Conflict escalation sits at {conflict_escalation['band'].lower()} with force-posture uncertainty still unresolved.",
        },
        {
            "role": "Academic Researcher",
            "region": "South Asia",
            "view": "Trend labels should be read as velocity, not peace/war state. A stable high-tension plateau can still be dangerous.",
        },
        {
            "role": "Ideology Analyst",
            "region": "Levant",
            "view": f"Identity and narrative competition continue to amplify {top_indicator.lower()} risk even without immediate battlefield expansion.",
        },
    ]
    consensus = "Panel consensus: interpret systemic criticality and escalation likelihood separately; prioritize leading indicators over single composite score."
    consensus_brief = (
        f"Consensus: escalation risk is {conflict_escalation['band'].lower()} while systemic stress is {overall_criticality['band'].lower()}; "
        f"most exposed channels are {top_sector.lower()} and {top_indicator.lower()}."
    )
    return {"panel": panel, "consensus": consensus, "consensus_brief": consensus_brief}


def _build_impacts(
    selected_issues: list[str],
    force_scores: dict[str, float],
    scenarios: list[dict[str, Any]],
    *,
    lens: str,
    focus: str | None,
) -> dict[str, Any]:
    scenario_lookup = {item["name"]: item["probability"] for item in scenarios}
    top_scenario = scenarios[0]["name"] if scenarios else "Unknown"
    top_prob = scenarios[0]["probability"] if scenarios else 0.0
    selected = selected_issues or list(ISSUE_CATALOG.keys())[:3]
    regions = sorted({name for slug in selected for name in ISSUE_REGION_MAPPING.get(slug, ())})
    country_focus_catalog: set[str] = set()
    for region in regions:
        for country, _directness, _base in REGION_COUNTRY_EXPOSURE.get(region, ()):
            country_focus_catalog.add(country)
    if lens == "region":
        # Region lens should prioritize regional geography over global aggregate buckets.
        regions = [name for name in regions if not name.lower().startswith("global ")]
    region_issue_count: dict[str, int] = {}
    for slug in selected:
        for region in ISSUE_REGION_MAPPING.get(slug, ()):
            region_issue_count[region] = region_issue_count.get(region, 0) + 1

    conflict_proxy = (
        scenario_lookup.get("Regional war escalation", 0.0) * 0.5
        + scenario_lookup.get("Maritime or infrastructure shock", 0.0) * 0.2
        + force_scores.get("military", 0.0) * 0.2
        + force_scores.get("economic", 0.0) * 0.1
    )
    anchor = max(0.2, min(0.9, conflict_proxy))
    countries_by_region: list[dict[str, Any]] = []
    for region in regions:
        country_rows = []
        for country, directness, _base in REGION_COUNTRY_EXPOSURE.get(region, ()):
            country_rows.append({"name": country, "directness": directness})
        if country_rows:
            countries_by_region.append({"region": region, "countries": country_rows})
    region_bases = [
        _impact_card(
            label=region,
            score=min(
                (
                    (
                        (force_scores.get("military", 0.0) * 0.45)
                        + (force_scores.get("economic", 0.0) * 0.35)
                        + 0.18
                    )
                    * REGION_BASE_MULTIPLIER.get(region, 1.0)
                )
                + (region_issue_count.get(region, 0) * 0.03)
                + (anchor * 0.08),
                1.0,
            ),
            summary=f"Spillover exposure elevated under {top_scenario.lower()} path.",
        )
        for region in regions[:5]
    ]
    country_seed: dict[str, dict[str, Any]] = {}
    for region in regions:
        for country, directness, base in REGION_COUNTRY_EXPOSURE.get(region, ()):
            score = (
                (force_scores.get("military", 0.0) * 0.28)
                + (force_scores.get("economic", 0.0) * 0.24)
                + (scenario_lookup.get("Regional war escalation", 0.0) * 0.22)
                + (scenario_lookup.get("Maritime or infrastructure shock", 0.0) * 0.16)
                + 0.08
                + (anchor * 0.06)
            ) * base
            summary = (
                "Directly impacted by operational and security spillover channels."
                if directness == "direct"
                else "Indirectly impacted via markets, supply chains, and alliance signaling."
            )
            candidate = _impact_card(label=country, score=score, summary=summary)
            candidate["directness"] = directness
            existing = country_seed.get(country)
            if existing is None or candidate["severity"] > existing["severity"]:
                country_seed[country] = candidate
    if not country_seed:
        for country, directness, base in (
            ("United States", "indirect", 0.76),
            ("China", "indirect", 0.8),
            ("India", "indirect", 0.78),
        ):
            score = ((force_scores.get("economic", 0.0) * 0.3) + (force_scores.get("military", 0.0) * 0.2) + 0.1) * base
            row = _impact_card(label=country, score=score, summary="Broad macro-security transmission exposure.")
            row["directness"] = directness
            country_seed[country] = row
    if lens == "country" and focus:
        focus_name = focus.strip()
        if focus_name and focus_name not in country_seed:
            boost_score = (
                (force_scores.get("military", 0.0) * 0.22)
                + (force_scores.get("economic", 0.0) * 0.28)
                + (scenario_lookup.get("Regional war escalation", 0.0) * 0.18)
                + 0.14
            )
            focus_row = _impact_card(
                label=focus_name,
                score=boost_score,
                summary="Lens-focused country injected to keep focal exposure visible in this view.",
            )
            focus_row["directness"] = "indirect"
            country_seed[focus_name] = focus_row
    country_cards = sorted(country_seed.values(), key=lambda row: row["severity"], reverse=True)[:18]
    sector_cards = [
        _impact_card(
            label="Energy",
            score=(scenario_lookup.get("Maritime or infrastructure shock", 0.0) * 0.55) + (force_scores.get("economic", 0.0) * 0.25),
            summary="Oil and LNG volatility likely to remain bid while transport risk premium stays elevated.",
        ),
        _impact_card(
            label="Shipping & Logistics",
            score=(scenario_lookup.get("Maritime or infrastructure shock", 0.0) * 0.6) + (force_scores.get("military", 0.0) * 0.2),
            summary="Routing, insurance, and port delays are primary pressure channels.",
        ),
        _impact_card(
            label="Technology",
            score=(force_scores.get("cyber", 0.0) * 0.35) + (force_scores.get("economic", 0.0) * 0.25),
            summary="Export controls and cyber frictions affect valuation and hardware lead times.",
        ),
        _impact_card(
            label="Food & Agriculture",
            score=(scenario_lookup.get("Regional war escalation", 0.0) * 0.3) + (force_scores.get("economic", 0.0) * 0.25),
            summary="Freight and commodity disruption risk can transmit into retail food inflation.",
        ),
        _impact_card(
            label="Hospitality",
            score=(force_scores.get("economic", 0.0) * 0.28) + (force_scores.get("narrative", 0.0) * 0.22) + (scenario_lookup.get("Regional war escalation", 0.0) * 0.2),
            summary="Hotel occupancy and business-travel confidence are sensitive to regional security signaling.",
        ),
        _impact_card(
            label="Tourism",
            score=(force_scores.get("narrative", 0.0) * 0.3) + (force_scores.get("military", 0.0) * 0.2) + (scenario_lookup.get("Regional war escalation", 0.0) * 0.24),
            summary="Inbound tourism can reprice quickly when risk perception shifts, even without direct local incidents.",
        ),
        _impact_card(
            label="F&B, Restaurants, Nightlife",
            score=(force_scores.get("economic", 0.0) * 0.24) + (force_scores.get("narrative", 0.0) * 0.2) + (scenario_lookup.get("Maritime or infrastructure shock", 0.0) * 0.16),
            summary="Consumer sentiment, visitor mix, and logistics costs influence discretionary spending velocity.",
        ),
        _impact_card(
            label="Luxury Shopping",
            score=(force_scores.get("economic", 0.0) * 0.3) + (force_scores.get("narrative", 0.0) * 0.18) + (scenario_lookup.get("Managed confrontation", 0.0) * 0.12),
            summary="Cross-border high-net-worth traffic and confidence flows drive volatility in premium retail demand.",
        ),
        _impact_card(
            label="Real Estate",
            score=(force_scores.get("economic", 0.0) * 0.34) + (force_scores.get("diplomatic", 0.0) * 0.12) + (scenario_lookup.get("Regional war escalation", 0.0) * 0.14),
            summary="Capital inflows, residency demand, and financing costs can shift sharply under prolonged geopolitical stress.",
        ),
    ]
    indicators = [
        _impact_card(
            label="Economy",
            score=(force_scores.get("economic", 0.0) * 0.5) + (scenario_lookup.get("Maritime or infrastructure shock", 0.0) * 0.2),
            summary="Growth risk skewed down; inflation and transport costs remain key watch items.",
        ),
        _impact_card(
            label="Safety",
            score=(force_scores.get("military", 0.0) * 0.5) + (scenario_lookup.get("Regional war escalation", 0.0) * 0.25),
            summary="Civilian and infrastructure safety risk rises where conflict spillover channels are active.",
        ),
        _impact_card(
            label="Security",
            score=(force_scores.get("military", 0.0) * 0.45) + (force_scores.get("cyber", 0.0) * 0.3),
            summary="Hybrid threats and force-posture adjustments increase operational uncertainty.",
        ),
        _impact_card(
            label="Prices",
            score=(force_scores.get("economic", 0.0) * 0.55) + (scenario_lookup.get("Maritime or infrastructure shock", 0.0) * 0.2),
            summary="Energy, freight, and insurance pass-through likely to keep headline prices sticky.",
        ),
    ]
    prediction = {
        "most_likely_scenario": top_scenario,
        "probability": round(top_prob, 4),
        "brief": f"Most likely near-term path is {top_scenario.lower()} with layered economic and security spillovers.",
    }
    three_sector = _build_three_sector_model(force_scores, scenario_lookup)
    maslow = _build_maslow_risk_hierarchy(force_scores, scenario_lookup)
    regions_weighted = _reweight_impact_group(region_bases, group="regions_world", lens=lens, focus=focus)
    countries_weighted = _reweight_impact_group(country_cards, group="countries", lens=lens, focus=focus)
    if lens == "country" and focus:
        focus_country = focus.strip().lower()
        countries_weighted = [row for row in countries_weighted if row["label"].lower() == focus_country]
        if not countries_weighted:
            fallback = _impact_card(
                label=focus.strip(),
                score=0.35,
                summary="Focused country details are being estimated from available issue and force signals.",
            )
            fallback["directness"] = "indirect"
            band = _risk_band(fallback["severity"])
            fallback["percent"] = band["percent"]
            fallback["band"] = band["label"]
            countries_weighted = [fallback]

    countries_by_region_weighted = countries_by_region
    if lens == "country" and focus:
        focus_country = focus.strip().lower()
        countries_by_region_weighted = []
        for group in countries_by_region:
            rows = [row for row in group["countries"] if row["name"].lower() == focus_country]
            if rows:
                countries_by_region_weighted.append({"region": group["region"], "countries": rows})

    return {
        "prediction": prediction,
        "regions_world": regions_weighted,
        "countries": countries_weighted,
        "countries_by_region": countries_by_region_weighted,
        "country_focus_options": sorted(country_focus_catalog),
        "sectors": _reweight_impact_group(sector_cards, group="sectors", lens=lens, focus=focus),
        "indicators": _reweight_impact_group(indicators, group="indicators", lens=lens, focus=focus),
        "three_sector_model": three_sector,
        "maslow_hierarchy": maslow,
    }


def _trend_label(items: list[SignalItem]) -> str:
    if not items:
        return "stable"
    now = datetime.now(UTC)
    recent = 0
    older = 0
    for item in items:
        if item.published_utc is None:
            continue
        delta_hours = (now - item.published_utc).total_seconds() / 3600
        if delta_hours <= 24:
            recent += 1
        elif delta_hours <= 72:
            older += 1
    if recent > older:
        return "rising"
    if recent < older:
        return "cooling"
    return "stable"


def _normalize_items(raw_items: list[SignalItem], limit: int) -> list[dict[str, Any]]:
    sorted_items = sorted(
        raw_items,
        key=lambda item: item.published_utc or datetime(1970, 1, 1, tzinfo=UTC),
        reverse=True,
    )
    rows: list[dict[str, Any]] = []
    for item in sorted_items[:limit]:
        rows.append(
            {
                "title": item.title,
                "source": item.source,
                "link": item.link,
                "issue": item.issue,
                "published_utc": None if item.published_utc is None else item.published_utc.isoformat(),
            }
        )
    return rows


def _fallback_demo_signals(selected_issues: list[str]) -> list[SignalItem]:
    issue_list = selected_issues or list(ISSUE_CATALOG.keys())[:3]
    now = datetime.now(UTC)
    demo: list[SignalItem] = []
    for idx, issue in enumerate(issue_list):
        issue_label = ISSUE_CATALOG.get(issue, issue)
        demo.append(
            SignalItem(
                title=f"{issue_label}: diplomatic channel reopened amid continued force posture",
                link="https://example.com/demo/diplomatic",
                source="demo-source",
                published_utc=now,
                issue=issue,
                summary="Negotiation and coercive pressure are both active.",
            )
        )
        demo.append(
            SignalItem(
                title=f"{issue_label}: market and logistics volatility signals elevated risk",
                link="https://example.com/demo/market",
                source="demo-source",
                published_utc=now,
                issue=issue,
                summary="Shipping routes and energy benchmarks moved on new reports.",
            )
        )
        if idx % 2 == 0:
            demo.append(
                SignalItem(
                    title=f"{issue_label}: religious and narrative framing intensifies online",
                    link="https://example.com/demo/narrative",
                    source="demo-source",
                    published_utc=now,
                    issue=issue,
                    summary="Polarized framing may influence escalation tolerance.",
                )
            )
    return demo


async def _fetch_issue_signals(client: httpx.AsyncClient, issue_slug: str, limit: int) -> list[SignalItem]:
    query = ISSUE_QUERIES.get(issue_slug)
    if not query:
        return []

    response = await client.get(_to_google_news_rss_url(query), timeout=20)
    response.raise_for_status()
    root = ElementTree.fromstring(response.text)
    channel = root.find("./channel")
    if channel is None:
        return []

    items: list[SignalItem] = []
    for entry in channel.findall("item")[:limit]:
        title = _extract_text(entry.find("title"))
        link = _extract_text(entry.find("link"))
        source = _extract_text(entry.find("source")) or "google-news"
        pub_date = _safe_parse_datetime(_extract_text(entry.find("pubDate")))
        description = _extract_text(entry.find("description"))
        if not title or not link:
            continue
        items.append(
            SignalItem(
                title=title,
                link=link,
                source=source,
                published_utc=pub_date,
                issue=issue_slug,
                summary=description,
            )
        )
    return items


async def fetch_signals(selected_issues: list[str], *, use_live: bool, per_issue_limit: int = 20) -> list[SignalItem]:
    issue_slugs = [slug for slug in selected_issues if slug in ISSUE_CATALOG]
    if not issue_slugs:
        issue_slugs = list(ISSUE_CATALOG.keys())[:3]

    if not use_live:
        return _fallback_demo_signals(issue_slugs)

    try:
        async with httpx.AsyncClient(headers={"User-Agent": "geostate-engine/0.1"}) as client:
            tasks = [_fetch_issue_signals(client, slug, per_issue_limit) for slug in issue_slugs]
            batches = await asyncio.gather(*tasks)
            merged = [row for batch in batches for row in batch]
            return merged or _fallback_demo_signals(issue_slugs)
    except (httpx.HTTPError, ElementTree.ParseError):
        return _fallback_demo_signals(issue_slugs)


async def build_dashboard_snapshot(
    selected_issues: list[str],
    *,
    use_live: bool,
    lens: str = "global",
    focus: str | None = None,
) -> dict[str, Any]:
    if lens not in LENS_TYPES:
        lens = "global"
    signals = await fetch_signals(selected_issues, use_live=use_live)
    force_scores = _aggregate_forces(signals)
    issue_pressure = _issue_pressure(selected_issues)
    driving_rows = _driving_forces_method(force_scores)
    game_rows = _game_theory_method(force_scores, issue_pressure)
    chess_rows, actor_moves = _chessboard_method(force_scores, issue_pressure, iterations=4)
    trend = _trend_label(signals)
    scenarios, scenario_meta = _consensus_scenarios(
        driving_rows,
        game_rows,
        chess_rows,
        force_totals=force_scores,
        issue_pressure=issue_pressure,
        trend=trend,
    )
    top_state = "Controlled instability"
    if scenarios and scenarios[0]["name"] in {"Negotiated stabilization", "Managed confrontation"}:
        top_state = "Managed tension"
    if scenarios and scenarios[0]["name"] == "Regional war escalation":
        top_state = "Pre-war transition"

    sorted_forces = sorted(force_scores.items(), key=lambda row: row[1], reverse=True)
    top_forces = [{"name": name, "score": score} for name, score in sorted_forces]
    conflict_escalation = _calculate_conflict_escalation(scenarios, force_scores, issue_pressure)
    criticality = _calculate_overall_criticality(
        scenarios,
        force_scores,
        lens,
        issue_pressure,
        conflict_score=conflict_escalation["score"],
    )
    impacts = _build_impacts(selected_issues, force_scores, scenarios, lens=lens, focus=focus)
    consistency_notes = _consistency_warnings(top_state, trend, criticality, conflict_escalation)
    expert_review = _build_expert_review(
        top_state=top_state,
        trend=trend,
        conflict_escalation=conflict_escalation,
        overall_criticality=criticality,
        impacts=impacts,
    )

    explanation = (
        "Scenario movement is derived from weighted signal density across military, economic, "
        "diplomatic, narrative, ideological/perception, and cyber forces. Scores are heuristic in this v1 slice."
    )
    prediction = (
        "Short-horizon expectation: volatility remains elevated while diplomatic channels and coercive "
        "signals coexist. Monitor maritime disruption frequency and sanction posture."
    )
    next_forecast = {
        "scenario": scenarios[0]["name"] if scenarios else "Unknown",
        "probability": scenarios[0]["probability"] if scenarios else 0.0,
        "horizon_steps": 4,
        "actor_moves": actor_moves,
        "rationale": "Consensus from driving-forces, game-theory utility, and finite chessboard best-response simulation.",
    }

    return {
        "generated_utc": datetime.now(UTC).isoformat(),
        "mode": "live" if use_live else "demo",
        "selected_issues": selected_issues,
        "lens": {"type": lens, "focus": focus},
        "current_state": {"label": top_state, "confidence": round(scenarios[0]["probability"], 3) if scenarios else 0.0},
        "trend": trend,
        "forces": top_forces,
        "scenarios": scenarios,
        "scenario_methods": {
            "driving_forces": driving_rows,
            "game_theory": game_rows,
            "chessboard": chess_rows,
            "consensus": {"rows": scenarios, **scenario_meta},
        },
        "next_scenario_forecast": next_forecast,
        "overall_criticality": criticality,
        "conflict_escalation": conflict_escalation,
        "consistency_notes": consistency_notes,
        "expert_review": expert_review,
        "impacts": impacts,
        "signals": _normalize_items(signals, limit=20),
        "explanation": explanation,
        "prediction": prediction,
    }
