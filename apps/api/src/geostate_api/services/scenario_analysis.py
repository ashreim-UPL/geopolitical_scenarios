from __future__ import annotations

import asyncio
import os
import sys
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any
from xml.etree import ElementTree
from urllib.parse import quote

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

BASE_GLOBAL_RSS_SOURCES: tuple[dict[str, str], ...] = (
    {"name": "BBC World", "url": "https://feeds.bbci.co.uk/news/world/rss.xml"},
    {"name": "Guardian World", "url": "https://www.theguardian.com/world/rss"},
    {"name": "Al Jazeera", "url": "https://www.aljazeera.com/xml/rss/all.xml"},
)

ISSUE_FILTER_HINTS: dict[str, tuple[str, ...]] = {
    "red-sea-shipping": ("red sea", "bab el-mandeb", "suez", "hormuz", "shipping", "container"),
    "gulf-energy-security": ("gulf", "hormuz", "oil", "lng", "refinery", "energy"),
    "us-china-technology": ("us", "china", "semiconductor", "chip", "export control", "technology"),
    "taiwan-strait": ("taiwan", "strait", "pla", "incursion", "drill", "east china sea"),
    "russia-ukraine-war": ("russia", "ukraine", "missile", "frontline", "black sea"),
    "iran-israel-dynamics": ("iran", "israel", "proxy", "tehran", "hezbollah", "levan"),
}

MAJOR_CONFLICT_CATALOG: dict[str, dict[str, Any]] = {
    "red-sea-shipping": {
        "name": "Red Sea Maritime Security Crisis",
        "primary_regions": ["Red Sea", "Bab el-Mandeb", "Suez corridor"],
        "principal_actors": ["Yemen Houthis", "US-led naval forces", "Regional shipping insurers"],
    },
    "gulf-energy-security": {
        "name": "Gulf Energy Security Tension",
        "primary_regions": ["Gulf", "Hormuz", "Global LNG routes"],
        "principal_actors": ["Iran", "GCC states", "Global importers"],
    },
    "us-china-technology": {
        "name": "US-China Strategic Technology Contest",
        "primary_regions": ["US", "China", "Global semiconductor chain"],
        "principal_actors": ["United States", "China", "Allied export-control states"],
    },
    "taiwan-strait": {
        "name": "Taiwan Strait Military-Strategic Pressure",
        "primary_regions": ["Taiwan Strait", "East Asia"],
        "principal_actors": ["China", "Taiwan", "US and allies"],
    },
    "russia-ukraine-war": {
        "name": "Russia-Ukraine High-Intensity Conflict",
        "primary_regions": ["Eastern Europe", "Black Sea"],
        "principal_actors": ["Russia", "Ukraine", "NATO states"],
    },
    "iran-israel-dynamics": {
        "name": "Iran-Israel Escalation Track",
        "primary_regions": ["Levant", "Gulf", "Regional proxy theaters"],
        "principal_actors": ["Iran", "Israel", "Regional proxies", "US"],
    },
}

ALTERNATIVE_SOURCE_FEEDS: list[dict[str, str]] = [
    {
        "name": "Substack Geopolitical Longform",
        "type": "esoteric",
        "description": "Narrative-heavy independent geopolitics commentary; high hypothesis density.",
    },
    {
        "name": "Telegram Open-Source Rumor Channels",
        "type": "conspiracy-adjacent",
        "description": "Fast rumor propagation; low verification quality, useful for early signal watch only.",
    },
    {
        "name": "YouTube Strategic Speculation Streams",
        "type": "conspiracy-adjacent",
        "description": "Speculative claims and scenario storytelling; requires strict evidence separation.",
    },
    {
        "name": "Fringe Forums / Imageboards",
        "type": "conspiracy",
        "description": "High noise and disinformation risk; only for alternate narrative monitoring.",
    },
]

ALTERNATIVE_RSS_SOURCES: tuple[dict[str, str], ...] = (
    {"name": "EUvsDisinfo", "url": "https://euvsdisinfo.eu/feed/"},
    {"name": "HKS Misinformation Review", "url": "https://misinforeview.hks.harvard.edu/feed/"},
    {"name": "Sky News Strange", "url": "https://feeds.skynews.com/feeds/rss/strange.xml"},
)

ALTERNATIVE_THEME_CATALOG: list[dict[str, Any]] = [
    {
        "name": "Prophetic-cycle narratives (Nostradamus-style)",
        "type": "esoteric",
        "description": "Apocalyptic pattern-reading narratives projecting civilizational collision windows.",
        "force_bias": {"narrative": 0.08, "ideological": 0.08},
    },
    {
        "name": "Religious end-times war framing",
        "type": "ideological",
        "description": "Eschatological interpretations of conflict used in mobilization and perception warfare.",
        "force_bias": {"ideological": 0.12, "military": 0.03},
    },
    {
        "name": "Hidden-hand / covert-orchestrator theories",
        "type": "conspiracy",
        "description": "Claims of unseen elite coordination shaping escalation and market shock events.",
        "force_bias": {"narrative": 0.1, "economic": 0.04},
    },
]

_SCENARIO_IMAGE_CACHE: dict[str, tuple[datetime, dict[str, Any]]] = {}
_SCENARIO_IMAGE_CACHE_TTL = timedelta(minutes=max(15, int(os.getenv("SCENARIO_IMAGE_CACHE_TTL_MINUTES", "120"))))
_SNAPSHOT_CACHE: dict[str, dict[str, Any]] = {}
_SNAPSHOT_HISTORY: dict[str, list[dict[str, Any]]] = {}
_SNAPSHOT_REFRESH_TASKS: dict[str, asyncio.Task[Any]] = {}
_SIGNAL_CACHE: dict[str, tuple[datetime, list[SignalItem]]] = {}
_SIGNAL_REFRESH_TASKS: dict[str, asyncio.Task[Any]] = {}
_SEMANTIC_PARSE_CACHE: dict[str, tuple[datetime, dict[str, Any]]] = {}
_SEMANTIC_PARSE_CACHE_TTL = timedelta(minutes=max(5, int(os.getenv("SEMANTIC_PARSE_CACHE_TTL_MINUTES", "30"))))
_SOURCE_HEALTH: dict[str, dict[str, str | None]] = {}


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
    "Gulf region": (("Iran", "direct", 1.0), ("Saudi Arabia", "direct", 0.9), ("UAE", "direct", 0.86), ("Qatar", "indirect", 0.76), ("Bahrain", "indirect", 0.72), ("Kuwait", "indirect", 0.74), ("Oman", "indirect", 0.7), ("Yemen", "direct", 0.92)),
    "MENA": (("Turkey", "indirect", 0.73), ("Iraq", "direct", 0.88), ("Syria", "direct", 0.9), ("Yemen", "direct", 0.9)),
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
    ai_summary: str = ""
    ai_keywords: tuple[str, ...] = ()
    ai_force_scores: dict[str, float] | None = None
    ai_relevance_score: float | None = None
    ai_assigned_issue: str | None = None
    ai_include_in_scope: bool = True


def _to_google_news_rss_url(query: str) -> str:
    encoded = query.replace(" ", "+")
    return f"https://news.google.com/rss/search?q={encoded}&hl=en-US&gl=US&ceid=US:en"


def _global_rss_sources() -> list[dict[str, str]]:
    rows = list(BASE_GLOBAL_RSS_SOURCES)
    raw = os.getenv("ADDITIONAL_RSS_FEEDS", "").strip()
    if not raw:
        return rows
    for chunk in raw.split(";"):
        item = chunk.strip()
        if not item:
            continue
        if "|" not in item:
            continue
        name, url = item.split("|", 1)
        name = name.strip()
        url = url.strip()
        if not name or not url:
            continue
        rows.append({"name": name, "url": url})
    return rows


def _alternative_rss_sources() -> list[dict[str, str]]:
    rows = list(ALTERNATIVE_RSS_SOURCES)
    raw = os.getenv("ALTERNATIVE_RSS_FEEDS", "").strip()
    if not raw:
        return rows
    for chunk in raw.split(";"):
        item = chunk.strip()
        if not item or "|" not in item:
            continue
        name, url = item.split("|", 1)
        name = name.strip()
        url = url.strip()
        if not name or not url:
            continue
        rows.append({"name": name, "url": url})
    return rows


def _default_selected_issues() -> list[str]:
    configured = os.getenv("DEFAULT_ISSUE_BUCKET", "").strip()
    if configured in ISSUE_CATALOG:
        return [configured]
    top_issue = max(ISSUE_ESCALATION_PRESSURE.items(), key=lambda row: row[1])[0]
    return [top_issue]


def _mark_source_success(source_name: str) -> None:
    row = _SOURCE_HEALTH.setdefault(
        source_name,
        {"last_success_utc": None, "last_error_utc": None, "last_error": None},
    )
    row["last_success_utc"] = datetime.now(UTC).isoformat()
    row["last_error"] = None


def _mark_source_error(source_name: str, error: Exception | str) -> None:
    row = _SOURCE_HEALTH.setdefault(
        source_name,
        {"last_success_utc": None, "last_error_utc": None, "last_error": None},
    )
    row["last_error_utc"] = datetime.now(UTC).isoformat()
    row["last_error"] = str(error)[:240]


def source_health_rows() -> list[dict[str, str | None]]:
    rows = []
    for source_name, row in _SOURCE_HEALTH.items():
        rows.append(
            {
                "source": source_name,
                "last_success_utc": row.get("last_success_utc"),
                "last_error_utc": row.get("last_error_utc"),
                "last_error": row.get("last_error"),
                "status": "degraded" if row.get("last_error") else "ok",
            }
        )
    rows.sort(key=lambda item: item["source"] or "")
    return rows


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


def _sanitize_force_scores(raw: dict[str, Any] | None) -> dict[str, float]:
    clean: dict[str, float] = {}
    if raw:
        for force in FORCE_KEYWORDS:
            value = raw.get(force, 0.0)
            try:
                clean[force] = round(max(0.0, min(1.0, float(value))), 3)
            except (TypeError, ValueError):
                clean[force] = 0.0
    else:
        clean = {force: 0.0 for force in FORCE_KEYWORDS}

    mass = sum(clean.values())
    if mass <= 0:
        return FORCE_PRIORS.copy()
    normalized = {force: round(value / mass, 4) for force, value in clean.items()}
    drift = round(1.0 - sum(normalized.values()), 4)
    if drift != 0:
        top_force = max(normalized, key=normalized.get)
        normalized[top_force] = round(normalized[top_force] + drift, 4)
    return normalized


def _extract_json_snippet(raw: str) -> str:
    text = raw.strip()
    if text.startswith("{") and text.endswith("}"):
        return text
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        return text[start : end + 1]
    return text


async def _semantic_enrich_signals(
    items: list[SignalItem],
    *,
    provider_info: dict[str, Any],
    selected_issues: list[str],
) -> tuple[list[SignalItem], dict[str, Any]]:
    if not items:
        return items, {"summary": "No signals available.", "keywords": []}
    if not provider_info.get("llm_enabled"):
        return items, {"summary": "LLM disabled; deterministic parsing active.", "keywords": []}

    compact_rows = []
    for idx, item in enumerate(items[:40]):
        compact_rows.append(
            {
                "idx": idx,
                "title": item.title[:280],
                "source": item.source[:120],
                "issue": item.issue,
                "summary": item.summary[:400],
            }
        )
    cache_basis = "|".join(
        [str(provider_info.get("provider", "deterministic"))]
        + [f"{row['issue']}::{row['title']}" for row in compact_rows]
    )
    cache_key = str(hash(cache_basis))
    now = datetime.now(UTC)
    cached_parse = _SEMANTIC_PARSE_CACHE.get(cache_key)
    if cached_parse and (now - cached_parse[0]) <= _SEMANTIC_PARSE_CACHE_TTL:
        parsed = cached_parse[1]
    else:
        parsed = None

    schema_hint = {
        "signal_parsing": [
            {
                "idx": 0,
                "brief": "One-sentence factual synthesis",
                "keywords": ["shipping", "hormuz"],
                "assigned_issue": "red-sea-shipping",
                "relevance_score": 0.82,
                "include_in_scope": True,
                "forces": {force: 0.0 for force in FORCE_KEYWORDS},
            }
        ],
        "compiled_summary": "120-180 words factual synthesis of key developments.",
        "compiled_keywords": ["keyword1", "keyword2", "keyword3"],
    }
    base_prompt = (
        "Parse geopolitical signals semantically. Return ONLY strict JSON.\n"
        "Requirements:\n"
        "1) For each signal idx, produce brief, keywords(3-6), and force scores across military/economic/diplomatic/narrative/ideological/cyber.\n"
        "2) Force scores must be floats in [0,1] and reflect causal relevance, not keyword counts.\n"
        "3) Assign each signal to one issue slug from selected_issue_slugs, add relevance_score [0,1], and include_in_scope boolean.\n"
        "4) Produce compiled_summary (120-180 words, factual, no hallucinations) and compiled_keywords(6-12).\n"
        "5) If evidence is ambiguous, lower force intensity and note uncertainty in brief."
    )

    issue_scope = selected_issues or _default_selected_issues()
    payload_hint = f"selected_issue_slugs: {issue_scope}\nSchema: {schema_hint}\nSignals: {compact_rows}"
    provider = str(provider_info.get("provider", "deterministic"))
    openai_key = os.getenv("OPENAI_API_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY")

    parsed_result: dict[str, Any] | None = parsed

    if parsed_result is None and provider in {"openai", "deterministic", "nano"} and openai_key:
        model = os.getenv("OPENAI_TEXT_MODEL", "gpt-4o-mini")
        try:
            async with httpx.AsyncClient(timeout=80) as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {openai_key}", "Content-Type": "application/json"},
                    json={
                        "model": model,
                        "temperature": 0.2,
                        "response_format": {"type": "json_object"},
                        "messages": [
                            {"role": "system", "content": "You are a geopolitical intelligence parser. Output strict JSON only."},
                            {"role": "user", "content": f"{base_prompt}\n\n{payload_hint}"},
                        ],
                    },
                )
                response.raise_for_status()
                content = (((response.json().get("choices") or [{}])[0]).get("message") or {}).get("content", "{}")
                parsed_result = _safe_json_load(_extract_json_snippet(content))
        except Exception:
            parsed_result = None
    elif parsed_result is None and provider == "gemini-cloud" and gemini_key:
        model = os.getenv("GEMINI_TEXT_MODEL", "gemini-1.5-pro")
        try:
            async with httpx.AsyncClient(timeout=80) as client:
                response = await client.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={gemini_key}",
                    headers={"Content-Type": "application/json"},
                    json={
                        "contents": [{"parts": [{"text": f"{base_prompt}\n\n{payload_hint}"}]}],
                        "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"},
                    },
                )
                response.raise_for_status()
                candidates = response.json().get("candidates") or []
                text = ""
                if candidates:
                    parts = (((candidates[0] or {}).get("content") or {}).get("parts") or [])
                    if parts:
                        text = str((parts[0] or {}).get("text", "{}"))
                parsed_result = _safe_json_load(_extract_json_snippet(text))
        except Exception:
            parsed_result = None

    if not isinstance(parsed_result, dict):
        return items, {"summary": "Semantic parser unavailable; deterministic parsing active.", "keywords": []}
    _SEMANTIC_PARSE_CACHE[cache_key] = (now, parsed_result)

    by_idx: dict[int, dict[str, Any]] = {}
    for row in parsed_result.get("signal_parsing", []) if isinstance(parsed_result.get("signal_parsing"), list) else []:
        try:
            idx = int(row.get("idx"))
        except (TypeError, ValueError):
            continue
        by_idx[idx] = row

    for idx, item in enumerate(items[:40]):
        ai_row = by_idx.get(idx)
        if not ai_row:
            continue
        item.ai_summary = str(ai_row.get("brief", "")).strip()[:400]
        keywords = ai_row.get("keywords")
        if isinstance(keywords, list):
            item.ai_keywords = tuple(str(token).strip() for token in keywords if str(token).strip())[:12]
        assigned_issue = str(ai_row.get("assigned_issue", item.issue)).strip()
        if assigned_issue in ISSUE_CATALOG:
            item.ai_assigned_issue = assigned_issue
            item.issue = assigned_issue
        try:
            item.ai_relevance_score = max(0.0, min(1.0, float(ai_row.get("relevance_score", 0.0))))
        except (TypeError, ValueError):
            item.ai_relevance_score = 0.0
        include_in_scope = bool(ai_row.get("include_in_scope", True))
        if item.ai_relevance_score is not None and item.ai_relevance_score < 0.45:
            include_in_scope = False
        if issue_scope and item.issue not in issue_scope:
            include_in_scope = False
        item.ai_include_in_scope = include_in_scope
        forces = ai_row.get("forces")
        if isinstance(forces, dict):
            item.ai_force_scores = _sanitize_force_scores(forces)

    compiled_keywords = parsed_result.get("compiled_keywords")
    if not isinstance(compiled_keywords, list):
        compiled_keywords = []
    return items, {
        "summary": str(parsed_result.get("compiled_summary", "")).strip(),
        "keywords": [str(token).strip() for token in compiled_keywords if str(token).strip()][:12],
    }


def _aggregate_forces(items: list[SignalItem]) -> dict[str, float]:
    totals = {force: 0.0 for force in FORCE_KEYWORDS}
    if not items:
        return FORCE_PRIORS.copy()
    for item in items:
        if item.ai_force_scores:
            scores = item.ai_force_scores
        else:
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


def resolve_intelligence_provider(*, prefer_local_ai: bool = False) -> dict[str, Any]:
    if prefer_local_ai and os.getenv("WINDOW_AI_AVAILABLE", "").lower() in {"1", "true", "yes"}:
        return {
            "tier": "tier1-edge",
            "provider": "nano",
            "model_version": "gemini-nano",
            "llm_enabled": True,
        }
    if os.getenv("GEMINI_API_KEY"):
        return {
            "tier": "tier2-deep",
            "provider": "gemini-cloud",
            "model_version": "gemini-1.5-pro",
            "llm_enabled": True,
        }
    if os.getenv("OPENAI_API_KEY"):
        return {
            "tier": "tier2-deep",
            "provider": "openai",
            "model_version": "gpt-family",
            "llm_enabled": True,
        }
    return {
        "tier": "tier3-deterministic",
        "provider": "deterministic",
        "model_version": "heuristic-v1",
        "llm_enabled": False,
    }


def _build_intelligence_metadata(
    provider_info: dict[str, Any],
    *,
    confidence_score: float,
    reasoning_tokens: str,
) -> dict[str, Any]:
    return {
        "provider": provider_info["provider"],
        "reasoning_tokens": reasoning_tokens,
        "confidence_score": round(max(0.0, min(1.0, confidence_score)), 3),
        "model_version": provider_info["model_version"],
    }


def _identify_major_conflicts(
    selected_issues: list[str],
    scenarios: list[dict[str, Any]],
    force_scores: dict[str, float],
) -> list[dict[str, Any]]:
    selected = selected_issues or _default_selected_issues()
    scenario_lookup = {row["name"]: row["probability"] for row in scenarios}
    base_pressure = (
        (scenario_lookup.get("Regional war escalation", 0.0) * 0.42)
        + (scenario_lookup.get("Maritime or infrastructure shock", 0.0) * 0.22)
        + (force_scores.get("military", 0.0) * 0.2)
        + (force_scores.get("economic", 0.0) * 0.16)
    )

    rows: list[dict[str, Any]] = []
    for slug in selected:
        catalog = MAJOR_CONFLICT_CATALOG.get(slug)
        if not catalog:
            continue
        issue_pressure = ISSUE_ESCALATION_PRESSURE.get(slug, 0.55)
        score = min((base_pressure * 0.62) + (issue_pressure * 0.38), 1.0)
        band = _risk_band(score)
        rows.append(
            {
                "issue_slug": slug,
                "issue_label": ISSUE_CATALOG.get(slug, slug),
                "conflict_name": catalog["name"],
                "primary_regions": catalog["primary_regions"],
                "principal_actors": catalog["principal_actors"],
                "severity": round(score, 3),
                "band": band["label"],
                "percent": band["percent"],
                "rationale": "Ranked by selected issue pressure + scenario escalation contribution + force posture.",
            }
        )
    return sorted(rows, key=lambda row: row["severity"], reverse=True)


def _build_pestel_framework(force_scores: dict[str, float], lens: str, focus: str | None) -> list[dict[str, Any]]:
    military = force_scores.get("military", 0.0)
    cyber = force_scores.get("cyber", 0.0)
    economic = force_scores.get("economic", 0.0)
    diplomatic = force_scores.get("diplomatic", 0.0)
    narrative = force_scores.get("narrative", 0.0)
    ideological = force_scores.get("ideological", 0.0)

    pestel_raw = {
        "Political": (diplomatic * 0.5) + (military * 0.2) + 0.12,
        "Economic": (economic * 0.72) + 0.1,
        "Social": (narrative * 0.5) + (ideological * 0.35) + 0.1,
        "Technological": (cyber * 0.62) + 0.08,
        "Environmental": (economic * 0.2) + (military * 0.2) + 0.06,
        "Legal": (diplomatic * 0.35) + (economic * 0.25) + 0.07,
    }

    focus_lower = (focus or "").strip().lower()
    if lens == "country":
        if focus_lower in {"uae", "saudi arabia", "qatar", "oman", "kuwait", "bahrain"}:
            pestel_raw["Economic"] *= 1.16
            pestel_raw["Social"] *= 1.1
        if focus_lower in {"ukraine", "russia", "iran", "israel", "syria", "iraq", "taiwan"}:
            pestel_raw["Political"] *= 1.18
            pestel_raw["Technological"] *= 1.12
    elif lens == "region" and focus_lower in {"gulf", "mena", "levant"}:
        pestel_raw["Political"] *= 1.12
        pestel_raw["Economic"] *= 1.1

    rows: list[dict[str, Any]] = []
    for label, score in pestel_raw.items():
        bounded = min(max(score, 0.0), 1.0)
        band = _risk_band(bounded)
        rows.append(
            {
                "dimension": label,
                "severity": round(bounded, 3),
                "band": band["label"],
                "percent": band["percent"],
            }
        )
    return sorted(rows, key=lambda row: row["severity"], reverse=True)


def _build_lens_alignment(lens: str, focus: str | None) -> dict[str, Any]:
    active = f"{lens} ({focus})" if focus else lens
    is_scoped = lens in {"region", "country"}
    return {
        "active_lens": active,
        "sections": {
            "three_sector_model": is_scoped or lens == "global",
            "maslow_hierarchy": is_scoped or lens == "global",
            "sector_impact": is_scoped or lens == "global",
            "indicator_impact": is_scoped or lens == "global",
        },
        "notes": "All impact sections are lens-aware; country/region selections apply explicit reweight multipliers.",
    }


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
        if group == "three_sector_model":
            if focus_lower in {"gulf", "mena", "levant"} and label == "Tertiary Sector":
                return 1.16
            if focus_lower in {"gulf", "mena", "levant"} and label == "Primary Sector":
                return 1.08
            return 0.97
        if group == "maslow_levels":
            if label.startswith("Safety"):
                return 1.12
            if focus_lower in {"gulf", "mena", "levant"} and label.startswith("Physiological"):
                return 1.08
            return 0.98

    if lens == "country":
        conflict_core = {"ukraine", "russia", "iran", "israel", "syria", "iraq", "taiwan"}
        gulf_services = {"uae", "saudi arabia", "qatar", "bahrain", "oman", "kuwait"}
        food_energy_importers = {"india", "bangladesh", "pakistan", "egypt"}
        if group == "countries":
            if focus_lower and focus_lower == label_lower:
                return 1.35
            return 0.88
        if group == "sectors":
            if focus_lower in gulf_services and label in {
                "Hospitality",
                "Tourism",
                "F&B, Restaurants, Nightlife",
                "Luxury Shopping",
                "Real Estate",
            }:
                return 1.24
            if focus_lower in food_energy_importers and label in {
                "Energy",
                "Shipping & Logistics",
                "Food & Agriculture",
            }:
                return 1.22
            if focus_lower in conflict_core and label in {
                "Energy",
                "Shipping & Logistics",
                "Technology",
            }:
                return 1.32
            if focus_lower in conflict_core and label in {
                "Food & Agriculture",
                "Tourism",
                "Hospitality",
                "F&B, Restaurants, Nightlife",
                "Real Estate",
                "Luxury Shopping",
            }:
                return 1.16
            if focus_lower in conflict_core:
                return 1.1
            return 0.98
        if group == "indicators":
            if focus_lower in conflict_core and label in {"Safety", "Security"}:
                return 1.45
            if focus_lower in conflict_core and label in {"Prices", "Economy"}:
                return 1.2
            if focus_lower in gulf_services and label in {"Economy", "Prices"}:
                return 1.18
            if focus_lower in food_energy_importers and label in {"Prices", "Economy"}:
                return 1.16
            if focus_lower in conflict_core:
                return 1.08
            return 0.98
        if group == "three_sector_model":
            if focus_lower in gulf_services:
                if label == "Tertiary Sector":
                    return 1.26
                if label == "Primary Sector":
                    return 1.08
                return 1.02
            if focus_lower in conflict_core:
                if label in {"Primary Sector", "Secondary Sector"}:
                    return 1.28
                return 1.06
            return 1.0
        if group == "maslow_levels":
            if focus_lower in conflict_core:
                if label.startswith("Safety"):
                    return 1.42
                if label.startswith("Physiological"):
                    return 1.2
                return 1.08
            if focus_lower in gulf_services:
                if label.startswith("Future Capacity"):
                    return 1.14
                if label.startswith("Safety"):
                    return 1.1
            return 0.96
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


def _apply_min_floor(items: list[dict[str, Any]], floors: dict[str, float]) -> list[dict[str, Any]]:
    adjusted: list[dict[str, Any]] = []
    for row in items:
        target = floors.get(row["label"])
        if target is None:
            adjusted.append(row)
            continue
        severity = max(row["severity"], target)
        band = _risk_band(severity)
        adjusted.append({**row, "severity": round(severity, 3), "band": band["label"], "percent": band["percent"]})
    return sorted(adjusted, key=lambda entry: entry["severity"], reverse=True)


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


def _reweight_maslow_hierarchy(hierarchy: dict[str, Any], *, lens: str, focus: str | None) -> dict[str, Any]:
    adjusted_levels: list[dict[str, Any]] = []
    for level in hierarchy.get("levels", []):
        multiplier = _lens_multiplier("maslow_levels", level["name"], lens=lens, focus=focus)
        adjusted_score = min(level["score"] * multiplier, 1.0)
        band = _risk_band(adjusted_score)
        adjusted_levels.append(
            {
                **level,
                "score": round(adjusted_score, 3),
                "percent": band["percent"],
                "band": band["label"],
            }
        )

    weighted_sum = sum(item["score"] * item["weight"] for item in adjusted_levels)
    dominant = max((item["score"] for item in adjusted_levels), default=0.0)
    hierarchy_score = min((weighted_sum * 0.6) + (dominant * 0.4), 1.0)
    hierarchy_band = _risk_band(hierarchy_score)
    return {
        **hierarchy,
        "levels": adjusted_levels,
        "weighted_score": round(weighted_sum, 4),
        "dominant_score": round(dominant, 4),
        "hierarchy_score": round(hierarchy_score, 4),
        "percent": hierarchy_band["percent"],
        "band": hierarchy_band["label"],
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
    selected = selected_issues or _default_selected_issues()
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
    country_cards = sorted(country_seed.values(), key=lambda row: row["severity"], reverse=True)
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
    three_sector = _reweight_impact_group(
        _build_three_sector_model(force_scores, scenario_lookup),
        group="three_sector_model",
        lens=lens,
        focus=focus,
    )
    maslow = _reweight_maslow_hierarchy(_build_maslow_risk_hierarchy(force_scores, scenario_lookup), lens=lens, focus=focus)
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

    sectors_weighted = _reweight_impact_group(sector_cards, group="sectors", lens=lens, focus=focus)
    indicators_weighted = _reweight_impact_group(indicators, group="indicators", lens=lens, focus=focus)

    if lens == "country" and focus:
        focus_name = focus.strip().lower()
        focus_row = next((row for row in countries_weighted if row["label"].strip().lower() == focus_name), None)
        if focus_row and focus_row.get("directness") == "direct" and float(focus_row.get("severity", 0.0)) >= 0.34:
            sectors_weighted = _apply_min_floor(
                sectors_weighted,
                {
                    "Energy": 0.42,
                    "Shipping & Logistics": 0.39,
                    "Technology": 0.34,
                    "Food & Agriculture": 0.31,
                    "Hospitality": 0.33,
                    "Tourism": 0.3,
                    "F&B, Restaurants, Nightlife": 0.31,
                    "Luxury Shopping": 0.29,
                    "Real Estate": 0.32,
                },
            )
            indicators_weighted = _apply_min_floor(
                indicators_weighted,
                {
                    "Safety": 0.52,
                    "Security": 0.48,
                    "Economy": 0.41,
                    "Prices": 0.43,
                },
            )

    return {
        "prediction": prediction,
        "regions_world": regions_weighted,
        "countries": countries_weighted,
        "countries_by_region": countries_by_region_weighted,
        "country_focus_options": sorted(country_focus_catalog),
        "sectors": sectors_weighted,
        "indicators": indicators_weighted,
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


def _normalize_items(raw_items: list[SignalItem], limit: int, *, provider_info: dict[str, Any], use_live: bool) -> list[dict[str, Any]]:
    sorted_items = sorted(
        raw_items,
        key=lambda item: item.published_utc or datetime(1970, 1, 1, tzinfo=UTC),
        reverse=True,
    )
    now = datetime.now(UTC)
    dedupe: set[str] = set()
    rows: list[dict[str, Any]] = []
    for item in sorted_items[:limit]:
        if item.ai_include_in_scope is False:
            continue
        title_key = "".join(ch for ch in item.title.lower() if ch.isalnum() or ch.isspace()).strip()
        if not title_key or title_key in dedupe:
            continue
        if use_live and item.published_utc is not None:
            age_hours = (now - item.published_utc).total_seconds() / 3600
            if age_hours > 72:
                continue
        dedupe.add(title_key)
        rows.append(
            {
                "title": item.title,
                "source": item.source,
                "link": item.link,
                "issue": item.issue,
                "published_utc": None if item.published_utc is None else item.published_utc.isoformat(),
                "summary": item.ai_summary or item.summary,
                "keywords": list(item.ai_keywords),
                "intelligence_metadata": _build_intelligence_metadata(
                    provider_info,
                    confidence_score=0.62,
                    reasoning_tokens=(
                        "Signal semantically parsed by LLM for causal force mapping."
                        if item.ai_force_scores
                        else "Signal classified through deterministic keyword/force fallback."
                    ),
                ),
            }
        )
        if len(rows) >= limit:
            break
    return rows


def _fallback_demo_signals(selected_issues: list[str]) -> list[SignalItem]:
    issue_list = selected_issues or _default_selected_issues()
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


def _build_alternative_signals(
    selected_issues: list[str],
    *,
    provider_info: dict[str, Any],
    generated_at: datetime,
) -> list[dict[str, Any]]:
    issue_list = selected_issues or _default_selected_issues()
    rows: list[dict[str, Any]] = []
    templates = (
        "{issue}: unverified claim of covert signaling pressure in active corridor.",
        "{issue}: rumor chain suggests informal de-escalation backchannel activity.",
        "{issue}: speculative chatter indicates infrastructure pressure escalation.",
        "{issue}: gossip network points to alliance posture recalibration.",
    )
    for idx, issue in enumerate(issue_list):
        label = ISSUE_CATALOG.get(issue, issue)
        for source_idx, source in enumerate(ALTERNATIVE_SOURCE_FEEDS[:3]):
            title = templates[(idx + source_idx) % len(templates)].format(issue=label)
            published = generated_at - timedelta(minutes=(idx * 11) + (source_idx * 4))
            rows.append(
                {
                    "title": title,
                    "source": source["name"],
                    "link": f"https://example.com/alternative/{issue}/{source_idx}",
                    "issue": issue,
                    "published_utc": published.isoformat(),
                    "intelligence_metadata": _build_intelligence_metadata(
                        provider_info,
                        confidence_score=0.41,
                        reasoning_tokens="Alternative narrative clustering from low-verification sources.",
                    ),
                }
            )
    return rows[:20]


async def fetch_alternative_signals(
    selected_issues: list[str],
    *,
    use_live: bool,
    provider_info: dict[str, Any],
    generated_at: datetime,
) -> list[dict[str, Any]]:
    issue_list = selected_issues or _default_selected_issues()
    if not use_live:
        return _build_alternative_signals(issue_list, provider_info=provider_info, generated_at=generated_at)

    rows: list[dict[str, Any]] = []
    try:
        async with httpx.AsyncClient(headers={"User-Agent": "geostate-engine/0.1"}) as client:
            collected: list[SignalItem] = []
            for issue in issue_list:
                rss_rows = await _fetch_alternative_feed_signals(client, issue, limit=10)
                feedly_rows = await _fetch_feedly_alt_signals(client, issue, limit=10)
                collected.extend(rss_rows)
                collected.extend(feedly_rows)
            if collected:
                collected, digest = await _semantic_enrich_signals(
                    collected,
                    provider_info=provider_info,
                    selected_issues=issue_list,
                )
                for item in collected:
                    if item.ai_include_in_scope is False:
                        continue
                    rows.append(
                        {
                            "title": item.title,
                            "source": item.source,
                            "link": item.link,
                            "issue": item.issue,
                            "published_utc": None if item.published_utc is None else item.published_utc.isoformat(),
                            "summary": item.ai_summary or item.summary,
                            "keywords": list(item.ai_keywords),
                            "intelligence_metadata": _build_intelligence_metadata(
                                provider_info,
                                confidence_score=0.45,
                                reasoning_tokens="Alternative-source semantic parser with low-confidence narrative scope.",
                            ),
                        }
                    )
                    if len(rows) >= 20:
                        break
                if rows:
                    return rows
                if digest.get("summary"):
                    # keep digest effect through fallback path metadata
                    pass
    except Exception:
        pass
    return _build_alternative_signals(issue_list, provider_info=provider_info, generated_at=generated_at)


def _normalize_force_distribution(force_scores: dict[str, float]) -> dict[str, float]:
    total = sum(max(0.0, value) for value in force_scores.values()) or 1.0
    normalized = {key: round(max(0.0, value) / total, 4) for key, value in force_scores.items()}
    drift = round(1.0 - sum(normalized.values()), 4)
    if drift != 0:
        top_force = max(normalized, key=normalized.get)
        normalized[top_force] = round(normalized[top_force] + drift, 4)
    return normalized


def _alternative_rows_to_signal_items(rows: list[dict[str, Any]]) -> list[SignalItem]:
    items: list[SignalItem] = []
    for row in rows:
        items.append(
            SignalItem(
                title=row.get("title", ""),
                link=row.get("link", ""),
                source=row.get("source", "alternative-source"),
                published_utc=_safe_parse_datetime(row.get("published_utc", "")),
                issue=row.get("issue", "alternative"),
                summary="Alternative narrative channel signal.",
            )
        )
    return items


def _build_alternative_theme_matrix(
    selected_issues: list[str],
    issue_pressure: float,
) -> list[dict[str, Any]]:
    issue_count = max(1, len(selected_issues))
    rows: list[dict[str, Any]] = []
    for idx, theme in enumerate(ALTERNATIVE_THEME_CATALOG):
        base = 0.24 + (issue_pressure * 0.28) + (issue_count * 0.018) + (idx * 0.035)
        score = min(base, 0.86)
        band = _risk_band(score)
        rows.append(
            {
                "name": theme["name"],
                "type": theme["type"],
                "description": theme["description"],
                "score": round(score, 3),
                "percent": band["percent"],
                "band": band["label"],
                "force_bias": theme["force_bias"],
            }
        )
    return sorted(rows, key=lambda row: row["score"], reverse=True)


def _recommended_refresh_policy(*, use_live: bool, signals: list[SignalItem]) -> dict[str, Any]:
    now = datetime.now(UTC)
    if not use_live:
        interval = 10800  # 3h
        rationale = "Demo/static mode: lower update cadence is sufficient."
    else:
        published = [item.published_utc for item in signals if item.published_utc is not None]
        if not published:
            interval = 7200  # 2h
            rationale = "No recent live timestamps; fallback to slower refresh."
        else:
            newest = max(published)
            age_minutes = max(0.0, (now - newest).total_seconds() / 60.0)
            if age_minutes <= 90:
                interval = 900  # 15m
                rationale = "High-churn live feed detected; using 10-15 minute cadence."
            elif age_minutes <= 360:
                interval = 1800  # 30m
                rationale = "Moderate live update rate; using 30 minute cadence."
            else:
                interval = 7200  # 2h
                rationale = "Lower live churn; using 2-3 hour cadence."
    return {
        "recommended_interval_seconds": interval,
        "rationale": rationale,
        "next_refresh_utc": (now + timedelta(seconds=interval)).isoformat(),
    }


def _snapshot_cache_key(
    *,
    selected_issues: list[str],
    use_live: bool,
    lens: str,
    focus: str | None,
    local_ai_enabled: bool,
    alternative_mode: bool,
) -> str:
    issues = ",".join(sorted(selected_issues))
    return f"{'alt' if alternative_mode else 'main'}|{issues}|{use_live}|{lens}|{focus or ''}|{local_ai_enabled}"


def _snapshot_cache_ttl_seconds(*, use_live: bool) -> int:
    return 900 if use_live else 7200


def _push_snapshot_history(cache_key: str, snapshot: dict[str, Any]) -> None:
    history = _SNAPSHOT_HISTORY.setdefault(cache_key, [])
    row = {
        "generated_utc": snapshot.get("generated_utc"),
        "mode": snapshot.get("mode"),
        "overall_criticality": (snapshot.get("overall_criticality") or {}).get("percent"),
        "conflict_escalation": (snapshot.get("conflict_escalation") or {}).get("percent"),
        "top_scenario": ((snapshot.get("scenarios") or [{}])[0]).get("name"),
    }
    history.insert(0, row)
    del history[2:]


def _safe_json_load(raw: str) -> dict[str, Any] | None:
    try:
        import json

        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        return None


async def _generate_creative_prediction_payload(
    *,
    selected_issues: list[str],
    scenario: str,
    probability: float,
    prediction_text: str,
    alternative_mode: bool,
) -> dict[str, Any]:
    openai_key = os.getenv("OPENAI_API_KEY")
    context = (
        f"Selected issues: {', '.join(selected_issues) if selected_issues else 'default issue basket'}. "
        f"Lead scenario: {scenario}. Probability: {int(round(probability * 100))}%. "
        f"Context: {prediction_text[:800]}"
    )
    if not openai_key:
        fallback_story = (
            f"{scenario} remains the leading near-term path across the selected issues, with signals pointing to a tense but adaptive operating environment where security signaling, market risk premiums, and diplomatic maneuvering coexist. In practical terms, the next 24-72 hours are likely to be driven by visible posturing and narrative escalation, while the 3-14 day window will determine whether disruptions harden into sustained spillovers across transport, prices, and investor confidence; the most reliable posture is to track measurable signposts and treat high-noise claims as provisional until corroborated."
        )
        fallback_visual = (
            "Wide cinematic 16:9 geopolitical command-center and port-corridor scene at dusk, realistic documentary style, neutral palette, clean lighting, visible infrastructure and shipping lanes, no text overlays, no logos, no faces, no gore."
        )
        return {
            "story_text": fallback_story,
            "visual_prompt": fallback_visual,
            "scenarios_payload": {
                "scenarios": [
                    {
                        "name": scenario,
                        "narrative": fallback_story,
                        "signposts": [
                            "Shipping insurance premiums increase >10%",
                            "Daily hostile incident count rises for 3 consecutive days",
                            "Emergency diplomatic hotline traffic spikes >20%",
                        ],
                        "implications": [
                            "Risk transfer costs rise across energy and logistics sectors",
                            "Higher policy uncertainty discounts regional assets",
                            "Supply chain rerouting extends lead times",
                        ],
                        "no_regret_moves": [
                            "Maintain diversified logistics routing",
                            "Hedge fuel and shipping cost exposure",
                            "Pre-position continuity protocols for critical operations",
                        ],
                        "contingent_moves": [
                            "Escalate contingency staffing when incident frequency breaches threshold",
                            "Trigger alternative payment channels if sanctions intensify",
                            "Switch to protected freight corridors if maritime risk index spikes",
                        ],
                    }
                ]
            },
            "provider": "deterministic",
            "model": "fallback-template-v1",
            "generated": False,
        }

    mode_hint = (
        "Mode: Alternative narrative track (blend verified signals with rumor/esoteric overlays)."
        if alternative_mode
        else "Mode: Main intelligence track (prioritize verified and high-reliability signals)."
    )
    scenarios_prompt = (
        "Generate a vivid, and highly differentiated scenarios based on the selected issue and the colelcted data and analysis "
        "These scenarios should be creative, employing elements of storytelling to bring the future to life.\n\n"
        "Return ONLY a JSON object that strictly matches the Scenarios Payload schema.\n\n"
        "Creative Requirements:\n"
        "- **Names**: Use descreptive names that attracts audience.\n"
        "- **Narrative**: Write 2–4 vivid paragraphs (120–220 words) for each scenario. Describe the \"feel\" of the world, not just the economics. No placeholders.\n"
        "- **Logic**: Ensure logical consistency with the data\n\n"
        "Structural Rules:\n"
        "- `signposts` must be concrete, measurable indicators (minimum 3 per scenario).\n"
        "- Include actionable `implications`, `no_regret_moves`, and `contingent_moves` (minimum 3 each per scenario)."
        "\n\nUse only the provided scenario context. Do not invent factual events that are not supported by the context.\n"
        f"{mode_hint}"
    )
    story_prompt = (
        "You are a master storyteller and futurist. Craft an immersive, \"Show, Don't Tell\" narrative that brings this scenario to life.\n\n"
        "Return ONLY a JSON object that matches the Scenario Story schema.\n\n"
        "Guidance:\n"
        "- **story_text**: Write exactly one captivating paragraph (90-150 words), easy to read, grounded strictly in provided context.\n"
        "- **visual_prompt**: A highly detailed cinematic description suitable for image generation, 16:9 wide composition, consulting-photography realism, clean lighting, neutral palette, no text overlays, no logos, no faces, no gore.\n"
        "- **Consistency**: Ensure narrative is strictly grounded in the provided economic/political logic and include uncertainty cues where evidence is limited.\n"
        f"{mode_hint}"
    )

    model = os.getenv("OPENAI_TEXT_MODEL", "gpt-4o-mini")
    try:
        async with httpx.AsyncClient(timeout=80) as client:
            scenarios_resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {openai_key}", "Content-Type": "application/json"},
                json={
                    "model": model,
                    "temperature": 0.8,
                    "response_format": {"type": "json_object"},
                    "messages": [
                        {"role": "system", "content": "You are a geopolitical scenario architect. Output strict JSON only."},
                        {"role": "user", "content": f"{scenarios_prompt}\n\nScenario context:\n{context}"},
                    ],
                },
            )
            scenarios_resp.raise_for_status()
            scenarios_content = (((scenarios_resp.json().get("choices") or [{}])[0]).get("message") or {}).get("content", "{}")
            scenarios_payload = _safe_json_load(scenarios_content) or {"scenarios": []}

            story_resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {openai_key}", "Content-Type": "application/json"},
                json={
                    "model": model,
                    "temperature": 0.9,
                    "response_format": {"type": "json_object"},
                    "messages": [
                        {"role": "system", "content": "You are a master storyteller and futurist. Output strict JSON only."},
                        {"role": "user", "content": f"{story_prompt}\n\nScenario context:\n{context}\nAlternative mode: {alternative_mode}"},
                    ],
                },
            )
            story_resp.raise_for_status()
            story_content = (((story_resp.json().get("choices") or [{}])[0]).get("message") or {}).get("content", "{}")
            story_payload = _safe_json_load(story_content) or {}
            return {
                "story_text": str(story_payload.get("story_text", "")),
                "visual_prompt": str(story_payload.get("visual_prompt", "")),
                "scenarios_payload": scenarios_payload,
                "provider": "openai",
                "model": model,
                "generated": True,
            }
    except httpx.HTTPError:
        return {
            "story_text": "",
            "visual_prompt": "",
            "scenarios_payload": {"scenarios": []},
            "provider": "openai",
            "model": model,
            "generated": False,
        }


async def _generate_ai_scenario_image(
    *,
    scenario: str,
    probability: float,
    prediction_text: str,
    alternative_mode: bool,
    visual_prompt_override: str | None = None,
) -> dict[str, Any]:
    cache_key = f"{alternative_mode}:{scenario}:{round(probability, 3)}"
    now = datetime.now(UTC)
    cached = _SCENARIO_IMAGE_CACHE.get(cache_key)
    if cached and (now - cached[0]) <= _SCENARIO_IMAGE_CACHE_TTL:
        return cached[1]

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return {"image_data_url": None, "provider": "none", "model": "none", "generated": False}

    safe_prompt_prefix = (
        "Wide 16:9 cinematic alternative-risk depiction blending rumor, ideological narratives, and geopolitical stress markers; realistic consulting-photography style, neutral palette. "
        if alternative_mode
        else "Wide 16:9 cinematic geopolitical intelligence depiction based on verified signals and scenario dynamics; realistic consulting-photography style, neutral palette. "
    )
    safe_prompt = (
        f"{safe_prompt_prefix}"
        f"Scenario: {scenario}. Probability: {int(round(probability * 100))} percent. "
        f"Context: {prediction_text[:220]}. "
        "No text overlays, no logos, no faces, no gore."
    )
    primary_prompt = (visual_prompt_override or "").strip() or safe_prompt

    async def _request_image(prompt_text: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.post(
                "https://api.openai.com/v1/images/generations",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "model": "gpt-image-1",
                    "size": "1024x1024",
                    "prompt": prompt_text,
                },
            )
            response.raise_for_status()
            payload = response.json()
            image_row = (payload.get("data") or [{}])[0]
            b64_image = image_row.get("b64_json")
            image_url = image_row.get("url")
            if not b64_image and not image_url:
                raise ValueError("No image payload returned")
            return {
                "image_data_url": f"data:image/png;base64,{b64_image}" if b64_image else image_url,
                "provider": "openai",
                "model": "gpt-image-1",
                "generated": True,
                "prompt_used": prompt_text[:240],
            }

    try:
        result = await _request_image(primary_prompt)
        _SCENARIO_IMAGE_CACHE[cache_key] = (now, result)
        return result
    except Exception as primary_error:
        if primary_prompt != safe_prompt:
            try:
                fallback_result = await _request_image(safe_prompt)
                _SCENARIO_IMAGE_CACHE[cache_key] = (now, fallback_result)
                return fallback_result
            except Exception as fallback_error:
                return {
                    "image_data_url": None,
                    "provider": "openai",
                    "model": "gpt-image-1",
                    "generated": False,
                    "error": f"primary={type(primary_error).__name__}; fallback={type(fallback_error).__name__}",
                }
        return {
            "image_data_url": None,
            "provider": "openai",
            "model": "gpt-image-1",
            "generated": False,
            "error": type(primary_error).__name__,
        }


async def _fetch_issue_signals(client: httpx.AsyncClient, issue_slug: str, limit: int) -> list[SignalItem]:
    query = ISSUE_QUERIES.get(issue_slug)
    if not query:
        return []

    source_name = "Google News"
    try:
        response = await client.get(_to_google_news_rss_url(query), timeout=20)
        response.raise_for_status()
        root = ElementTree.fromstring(response.text)
        _mark_source_success(source_name)
    except Exception as exc:
        _mark_source_error(source_name, exc)
        raise
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


def _pick_link_from_entry(entry: ElementTree.Element) -> str:
    link_node = entry.find("link")
    if link_node is None:
        return ""
    href = link_node.attrib.get("href", "").strip()
    if href:
        return href
    return (link_node.text or "").strip()


def _is_relevant_to_issue(issue_slug: str, title: str, summary: str) -> bool:
    text = f"{title} {summary}".lower()
    hints = ISSUE_FILTER_HINTS.get(issue_slug, ())
    if not hints:
        return True
    return any(token in text for token in hints)


async def _fetch_global_feed_signals(client: httpx.AsyncClient, issue_slug: str, limit: int) -> list[SignalItem]:
    return await _fetch_rss_sources_signals(client, issue_slug, _global_rss_sources(), limit)


async def _fetch_rss_sources_signals(
    client: httpx.AsyncClient,
    issue_slug: str,
    sources: list[dict[str, str]],
    limit: int,
) -> list[SignalItem]:
    rows: list[SignalItem] = []
    for source in sources:
        try:
            response = await client.get(source["url"], timeout=20)
            response.raise_for_status()
            root = ElementTree.fromstring(response.text)
            _mark_source_success(source["name"])
        except Exception:
            _mark_source_error(source["name"], "rss_fetch_failed")
            continue

        channel = root.find("./channel")
        if channel is not None:
            candidates = channel.findall("item")
            for entry in candidates:
                title = _extract_text(entry.find("title"))
                link = _extract_text(entry.find("link"))
                published = _safe_parse_datetime(_extract_text(entry.find("pubDate")))
                summary = _extract_text(entry.find("description"))
                if not title or not link:
                    continue
                if not _is_relevant_to_issue(issue_slug, title, summary):
                    continue
                rows.append(
                    SignalItem(
                        title=title,
                        link=link,
                        source=source["name"],
                        published_utc=published,
                        issue=issue_slug,
                        summary=summary,
                    )
                )
                if len(rows) >= limit:
                    return rows
            continue

        entries = root.findall(".//{http://www.w3.org/2005/Atom}entry")
        for entry in entries:
            title = _extract_text(entry.find("{http://www.w3.org/2005/Atom}title"))
            summary = _extract_text(entry.find("{http://www.w3.org/2005/Atom}summary"))
            if not summary:
                summary = _extract_text(entry.find("{http://www.w3.org/2005/Atom}content"))
            link = _pick_link_from_entry(entry.find("{http://www.w3.org/2005/Atom}link") or entry)
            published = _safe_parse_datetime(
                _extract_text(entry.find("{http://www.w3.org/2005/Atom}updated"))
                or _extract_text(entry.find("{http://www.w3.org/2005/Atom}published"))
            )
            if not title or not link:
                continue
            if not _is_relevant_to_issue(issue_slug, title, summary):
                continue
            rows.append(
                SignalItem(
                    title=title,
                    link=link,
                    source=source["name"],
                    published_utc=published,
                    issue=issue_slug,
                    summary=summary,
                )
            )
            if len(rows) >= limit:
                return rows
    return rows


async def _fetch_alternative_feed_signals(client: httpx.AsyncClient, issue_slug: str, limit: int) -> list[SignalItem]:
    return await _fetch_rss_sources_signals(client, issue_slug, _alternative_rss_sources(), limit)


def _feedly_streams() -> list[str]:
    raw = os.getenv("FEEDLY_STREAM_IDS", "").strip()
    if not raw:
        default = os.getenv("FEEDLY_STREAM_ID", "").strip()
        return [default] if default else []
    return [item.strip() for item in raw.split(",") if item.strip()]


def _feedly_alt_streams() -> list[str]:
    raw = os.getenv("FEEDLY_ALT_STREAM_IDS", "").strip()
    if not raw:
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


async def _fetch_feedly_signals(client: httpx.AsyncClient, issue_slug: str, limit: int) -> list[SignalItem]:
    token = os.getenv("FEEDLY_API_KEY", "").strip()
    streams = _feedly_streams()
    if not token or not streams:
        return []

    rows: list[SignalItem] = []
    headers = {"Authorization": f"Bearer {token}"}
    for stream_id in streams:
        source_name = f"Feedly:{stream_id}"
        try:
            url = (
                "https://api.feedly.com/v3/streams/contents"
                f"?streamId={quote(stream_id, safe='')}&count={max(20, limit * 2)}"
            )
            response = await client.get(url, headers=headers, timeout=25)
            response.raise_for_status()
            payload = response.json()
            _mark_source_success(source_name)
        except Exception as exc:
            _mark_source_error(source_name, exc)
            continue

        for item in payload.get("items", []) if isinstance(payload, dict) else []:
            title = str(item.get("title", "")).strip()
            summary = ""
            summary_obj = item.get("summary")
            if isinstance(summary_obj, dict):
                summary = str(summary_obj.get("content", "")).strip()
            if not summary:
                content_obj = item.get("content")
                if isinstance(content_obj, dict):
                    summary = str(content_obj.get("content", "")).strip()
            alternate = item.get("alternate")
            link = ""
            if isinstance(alternate, list) and alternate:
                first = alternate[0]
                if isinstance(first, dict):
                    link = str(first.get("href", "")).strip()
            source = "Feedly"
            origin = item.get("origin")
            if isinstance(origin, dict):
                source = str(origin.get("title", "Feedly")).strip() or "Feedly"
            published_ms = item.get("published")
            published = None
            if isinstance(published_ms, (int, float)):
                published = datetime.fromtimestamp(float(published_ms) / 1000.0, tz=UTC)
            if not title or not link:
                continue
            if not _is_relevant_to_issue(issue_slug, title, summary):
                continue
            rows.append(
                SignalItem(
                    title=title,
                    link=link,
                    source=source,
                    published_utc=published,
                    issue=issue_slug,
                    summary=summary,
                )
            )
            if len(rows) >= limit:
                return rows
    return rows


async def _fetch_feedly_alt_signals(client: httpx.AsyncClient, issue_slug: str, limit: int) -> list[SignalItem]:
    token = os.getenv("FEEDLY_API_KEY", "").strip()
    streams = _feedly_alt_streams()
    if not token or not streams:
        return []

    rows: list[SignalItem] = []
    headers = {"Authorization": f"Bearer {token}"}
    for stream_id in streams:
        source_name = f"FeedlyAlt:{stream_id}"
        try:
            url = (
                "https://api.feedly.com/v3/streams/contents"
                f"?streamId={quote(stream_id, safe='')}&count={max(20, limit * 2)}"
            )
            response = await client.get(url, headers=headers, timeout=25)
            response.raise_for_status()
            payload = response.json()
            _mark_source_success(source_name)
        except Exception as exc:
            _mark_source_error(source_name, exc)
            continue

        for item in payload.get("items", []) if isinstance(payload, dict) else []:
            title = str(item.get("title", "")).strip()
            summary = ""
            summary_obj = item.get("summary")
            if isinstance(summary_obj, dict):
                summary = str(summary_obj.get("content", "")).strip()
            if not summary:
                content_obj = item.get("content")
                if isinstance(content_obj, dict):
                    summary = str(content_obj.get("content", "")).strip()
            alternate = item.get("alternate")
            link = ""
            if isinstance(alternate, list) and alternate:
                first = alternate[0]
                if isinstance(first, dict):
                    link = str(first.get("href", "")).strip()
            source = "FeedlyAlt"
            origin = item.get("origin")
            if isinstance(origin, dict):
                source = str(origin.get("title", "FeedlyAlt")).strip() or "FeedlyAlt"
            published_ms = item.get("published")
            published = None
            if isinstance(published_ms, (int, float)):
                published = datetime.fromtimestamp(float(published_ms) / 1000.0, tz=UTC)
            if not title or not link:
                continue
            rows.append(
                SignalItem(
                    title=title,
                    link=link,
                    source=source,
                    published_utc=published,
                    issue=issue_slug,
                    summary=summary,
                )
            )
            if len(rows) >= limit:
                return rows
    return rows


def _signal_cache_ttl_seconds() -> int:
    return max(60, int(os.getenv("SIGNAL_INGEST_TTL_SECONDS", "180")))


async def _refresh_issue_signal_cache(issue_slug: str, *, per_issue_limit: int) -> None:
    try:
        async with httpx.AsyncClient(headers={"User-Agent": "geostate-engine/0.1"}) as client:
            google_rows = await _fetch_issue_signals(client, issue_slug, per_issue_limit)
            global_rows = await _fetch_global_feed_signals(client, issue_slug, max(8, per_issue_limit // 2))
            feedly_rows = await _fetch_feedly_signals(client, issue_slug, max(10, per_issue_limit // 2))
            combined = sorted(
                [*google_rows, *global_rows, *feedly_rows],
                key=lambda row: row.published_utc or datetime(1970, 1, 1, tzinfo=UTC),
                reverse=True,
            )
            dedupe: dict[str, SignalItem] = {}
            for row in combined:
                key = "".join(ch for ch in row.title.lower() if ch.isalnum() or ch.isspace()).strip()
                if not key or key in dedupe:
                    continue
                dedupe[key] = row
                if len(dedupe) >= per_issue_limit:
                    break
            rows = list(dedupe.values())
            if rows:
                _SIGNAL_CACHE[issue_slug] = (datetime.now(UTC), rows)
    except Exception:
        # ingestion refresh failures should not break request path
        pass
    finally:
        _SIGNAL_REFRESH_TASKS.pop(issue_slug, None)


async def ingest_live_signals_background(selected_issues: list[str] | None = None, *, per_issue_limit: int = 20) -> None:
    issue_slugs = [slug for slug in (selected_issues or list(ISSUE_CATALOG.keys())) if slug in ISSUE_CATALOG]
    if not issue_slugs:
        issue_slugs = list(ISSUE_CATALOG.keys())
    tasks = []
    for slug in issue_slugs:
        tasks.append(_refresh_issue_signal_cache(slug, per_issue_limit=per_issue_limit))
    await asyncio.gather(*tasks, return_exceptions=True)


async def fetch_signals(selected_issues: list[str], *, use_live: bool, per_issue_limit: int = 20) -> list[SignalItem]:
    issue_slugs = [slug for slug in selected_issues if slug in ISSUE_CATALOG]
    if not issue_slugs:
        issue_slugs = _default_selected_issues()

    if not use_live:
        return _fallback_demo_signals(issue_slugs)

    ttl = _signal_cache_ttl_seconds()
    now = datetime.now(UTC)
    merged: list[SignalItem] = []
    missing: list[str] = []
    stale: list[str] = []
    for slug in issue_slugs:
        cached = _SIGNAL_CACHE.get(slug)
        if not cached:
            missing.append(slug)
            continue
        cached_at, rows = cached
        age = (now - cached_at).total_seconds()
        if age > ttl:
            stale.append(slug)
        merged.extend(rows)

    if missing:
        try:
            await asyncio.gather(*[_refresh_issue_signal_cache(slug, per_issue_limit=per_issue_limit) for slug in missing])
            for slug in missing:
                cached_now = _SIGNAL_CACHE.get(slug)
                if cached_now:
                    merged.extend(cached_now[1])
        except Exception:
            pass

    for slug in stale:
        if slug not in _SIGNAL_REFRESH_TASKS:
            _SIGNAL_REFRESH_TASKS[slug] = asyncio.create_task(_refresh_issue_signal_cache(slug, per_issue_limit=per_issue_limit))

    return merged or _fallback_demo_signals(issue_slugs)


async def build_dashboard_snapshot(
    selected_issues: list[str],
    *,
    use_live: bool,
    lens: str = "global",
    focus: str | None = None,
    local_ai_enabled: bool = True,
) -> dict[str, Any]:
    if lens not in LENS_TYPES:
        lens = "global"
    provider_info = resolve_intelligence_provider(prefer_local_ai=local_ai_enabled)
    signals = await fetch_signals(selected_issues, use_live=use_live)
    signals, signal_digest = await _semantic_enrich_signals(
        signals,
        provider_info=provider_info,
        selected_issues=selected_issues,
    )
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
    major_conflicts = _identify_major_conflicts(selected_issues, scenarios, force_scores)
    pestel_framework = _build_pestel_framework(force_scores, lens=lens, focus=focus)
    lens_alignment = _build_lens_alignment(lens, focus)
    consistency_notes = _consistency_warnings(top_state, trend, criticality, conflict_escalation)
    expert_review = _build_expert_review(
        top_state=top_state,
        trend=trend,
        conflict_escalation=conflict_escalation,
        overall_criticality=criticality,
        impacts=impacts,
    )

    explanation = (
        "Scenario movement is derived from semantically parsed source signals across military, economic, "
        "diplomatic, narrative, ideological/perception, and cyber forces, with deterministic fallback when AI parsing is unavailable."
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

    analysis_provenance = {
        "tier_resolution_order": ["tier1-edge", "tier2-deep", "tier3-deterministic"],
        "active_provider": provider_info["provider"],
        "active_tier": provider_info["tier"],
        "llm_enabled": provider_info["llm_enabled"],
        "model_version": provider_info["model_version"],
        "areas": [
            {"area": "signal scoring", "engine": provider_info["provider"] if provider_info["llm_enabled"] else "deterministic"},
            {"area": "signal summarization", "engine": provider_info["provider"] if provider_info["llm_enabled"] else "deterministic"},
            {"area": "force split", "engine": "deterministic"},
            {"area": "scenario fusion", "engine": "deterministic"},
            {"area": "consensus brief", "engine": provider_info["provider"] if provider_info["llm_enabled"] else "deterministic"},
            {"area": "impact reweighting", "engine": "deterministic"},
        ],
        "notes": "Current deployment defaults to deterministic anchor; LLM tiers activate only when provider credentials/runtime are available.",
    }

    intelligence_metadata = _build_intelligence_metadata(
        provider_info,
        confidence_score=0.68 if provider_info["llm_enabled"] else 0.58,
        reasoning_tokens="Composite outcome derived from force scoring, three-method scenario fusion, and lens-aware impact reweighting.",
    )
    creative_prediction = await _generate_creative_prediction_payload(
        selected_issues=selected_issues,
        scenario=next_forecast["scenario"],
        probability=float(next_forecast["probability"]),
        prediction_text=prediction,
        alternative_mode=False,
    )
    scenario_visual = await _generate_ai_scenario_image(
        scenario=next_forecast["scenario"],
        probability=float(next_forecast["probability"]),
        prediction_text=prediction,
        alternative_mode=False,
        visual_prompt_override=creative_prediction.get("visual_prompt") or None,
    )
    refresh_policy = _recommended_refresh_policy(use_live=use_live, signals=signals)

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
        "major_conflicts": major_conflicts,
        "pestel_framework": pestel_framework,
        "lens_alignment": lens_alignment,
        "analysis_provenance": analysis_provenance,
        "intelligence_metadata": intelligence_metadata,
        "creative_prediction": creative_prediction,
        "scenario_visual": scenario_visual,
        "update_policy": refresh_policy,
        "signal_digest": signal_digest,
        "source_health": source_health_rows(),
        "alternative_intelligence": {
            "disclaimer": "Alternative/esoteric sources are not validated truth. Use for narrative-monitoring only.",
            "sources": ALTERNATIVE_SOURCE_FEEDS,
        },
        "expert_review": expert_review,
        "impacts": impacts,
        "signals": _normalize_items(signals, limit=20, provider_info=provider_info, use_live=use_live),
        "explanation": explanation,
        "prediction": prediction,
    }


async def build_alternative_snapshot(
    selected_issues: list[str],
    *,
    use_live: bool,
    lens: str = "global",
    focus: str | None = None,
    local_ai_enabled: bool = True,
) -> dict[str, Any]:
    base = await build_dashboard_snapshot(
        selected_issues,
        use_live=use_live,
        lens=lens,
        focus=focus,
        local_ai_enabled=local_ai_enabled,
    )
    provider_info = {
        "provider": base.get("intelligence_metadata", {}).get("provider", "deterministic"),
        "model_version": base.get("intelligence_metadata", {}).get("model_version", "heuristic-v1"),
    }
    generated_at = datetime.now(UTC)
    alternative_signals = await fetch_alternative_signals(
        selected_issues,
        use_live=use_live,
        provider_info=provider_info,
        generated_at=generated_at,
    )
    alt_signal_items = _alternative_rows_to_signal_items(alternative_signals)
    issue_pressure = _issue_pressure(selected_issues)
    theme_rows = _build_alternative_theme_matrix(selected_issues, issue_pressure)

    base_force_scores = {row["name"]: float(row["score"]) for row in base.get("forces", [])}
    for force in FORCE_KEYWORDS:
        base_force_scores.setdefault(force, FORCE_PRIORS.get(force, 0.1))
    alt_force_scores = base_force_scores.copy()
    for theme in theme_rows:
        theme_weight = float(theme["score"])
        for force_name, bump in (theme.get("force_bias") or {}).items():
            alt_force_scores[force_name] = alt_force_scores.get(force_name, 0.0) + (float(bump) * theme_weight)
    alt_force_scores = _normalize_force_distribution(alt_force_scores)

    alt_driving = _driving_forces_method(alt_force_scores)
    alt_game = _game_theory_method(alt_force_scores, min(1.0, issue_pressure + 0.06))
    alt_chess, alt_actor_moves = _chessboard_method(alt_force_scores, min(1.0, issue_pressure + 0.08), iterations=4)
    alt_scenarios, alt_meta = _consensus_scenarios(
        alt_driving,
        alt_game,
        alt_chess,
        force_totals=alt_force_scores,
        issue_pressure=min(1.0, issue_pressure + 0.08),
        trend=base.get("trend", "stable"),
    )
    alt_conflict = _calculate_conflict_escalation(alt_scenarios, alt_force_scores, min(1.0, issue_pressure + 0.08))
    alt_criticality = _calculate_overall_criticality(
        alt_scenarios,
        alt_force_scores,
        lens,
        min(1.0, issue_pressure + 0.08),
        conflict_score=alt_conflict["score"],
    )
    alt_impacts = _build_impacts(selected_issues, alt_force_scores, alt_scenarios, lens=lens, focus=focus)
    alt_expert = _build_expert_review(
        top_state=base.get("current_state", {}).get("label", "Managed tension"),
        trend=base.get("trend", "stable"),
        conflict_escalation=alt_conflict,
        overall_criticality=alt_criticality,
        impacts=alt_impacts,
    )
    alt_prediction = (
        "Alternative blended outlook: verified channels plus rumor/esoteric pressure suggest "
        f"{alt_scenarios[0]['name'].lower()} remains the strongest narrative path."
    ) if alt_scenarios else "Alternative blended outlook pending."
    alt_creative_prediction = await _generate_creative_prediction_payload(
        selected_issues=selected_issues,
        scenario=alt_scenarios[0]["name"] if alt_scenarios else "Alternative scenario pending",
        probability=float(alt_scenarios[0]["probability"]) if alt_scenarios else 0.0,
        prediction_text=alt_prediction,
        alternative_mode=True,
    )
    alt_visual = await _generate_ai_scenario_image(
        scenario=alt_scenarios[0]["name"] if alt_scenarios else "Alternative scenario pending",
        probability=float(alt_scenarios[0]["probability"]) if alt_scenarios else 0.0,
        prediction_text=alt_prediction,
        alternative_mode=True,
        visual_prompt_override=alt_creative_prediction.get("visual_prompt") or None,
    )
    merged_signals = alternative_signals[:20]
    refresh_policy = _recommended_refresh_policy(use_live=use_live, signals=alt_signal_items)

    return {
        **base,
        "mode": "alternative",
        "forces": [{"name": name, "score": score} for name, score in sorted(alt_force_scores.items(), key=lambda item: item[1], reverse=True)],
        "scenarios": alt_scenarios,
        "scenario_methods": {
            "driving_forces": alt_driving,
            "game_theory": alt_game,
            "chessboard": alt_chess,
            "consensus": {"rows": alt_scenarios, **alt_meta},
        },
        "next_scenario_forecast": {
            "scenario": alt_scenarios[0]["name"] if alt_scenarios else "Unknown",
            "probability": alt_scenarios[0]["probability"] if alt_scenarios else 0.0,
            "horizon_steps": 4,
            "actor_moves": alt_actor_moves,
            "rationale": "Alternative blend from verified signals + rumor streams + esoteric/ideological narrative overlays.",
        },
        "overall_criticality": alt_criticality,
        "conflict_escalation": alt_conflict,
        "impacts": alt_impacts,
        "expert_review": alt_expert,
        "signals": merged_signals,
        "prediction": alt_prediction,
        "creative_prediction": alt_creative_prediction,
        "explanation": (
            "This page blends verified feeds with rumors, speculative/esoteric framing, and conspiracy-adjacent narratives. "
            "Use as alternative narrative pressure index, not validated truth."
        ),
        "scenario_visual": alt_visual,
        "update_policy": refresh_policy,
        "analysis_provenance": {
            **base.get("analysis_provenance", {}),
            "areas": [
                {"area": "verified signal ingestion", "engine": "live-rss"},
                {"area": "rumor/gossip ingestion", "engine": "alternative-source-cluster"},
                {"area": "esoteric theme overlay", "engine": "deterministic-theme-matrix"},
                {"area": "scenario fusion", "engine": provider_info["provider"] if base.get("analysis_provenance", {}).get("llm_enabled") else "deterministic"},
            ],
            "notes": "Alternative page uses mixed verified and non-verified channels with explicit theme overlays.",
        },
        "alternative_intelligence": {
            "disclaimer": (
                "Alternative/esoteric/conspiracy-adjacent sources are for narrative contrast only. "
                "Treat as low-confidence until verified."
            ),
            "sources": ALTERNATIVE_SOURCE_FEEDS,
            "themes": theme_rows,
        },
    }
