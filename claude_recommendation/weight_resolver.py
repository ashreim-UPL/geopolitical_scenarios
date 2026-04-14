"""
weight_resolver.py
Location: /packages/scenarios/weight_resolver.py

Derives method weights (driving_forces / game_theory / chessboard)
from system state, phase velocity, and dominant force type.

This is the canonical weight logic. The frontend mirrors this in
resolveWeights() inside page.tsx. Both must stay in sync.

Rules:
- Weights must sum to 1.0 after normalization.
- Weights are re-derived on every state update cycle.
- Analyst overrides are versioned and stored separately.
- Never hardcode METHOD_WEIGHTS as a constant — always call resolve().
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum


# ── Enumerations ──────────────────────────────────────────────────────────────

class SystemState(str, Enum):
    STABLE                      = "stable"
    MANAGED_TENSION             = "managed_tension"
    CONTROLLED_INSTABILITY      = "controlled_instability"
    DISTRIBUTED_COERCION        = "distributed_coercion"
    MARITIME_PRESSURE           = "maritime_pressure"
    HYBRID_ESCALATION           = "hybrid_escalation"
    PRE_WAR_TRANSITION          = "pre_war_transition"
    REGIONAL_WAR                = "regional_war"
    NEGOTIATED_STABILIZATION    = "negotiated_stabilization"
    POST_SHOCK_RECOVERY         = "post_shock_recovery"


class PhaseVelocity(str, Enum):
    ACCELERATING  = "accelerating"
    STABLE        = "stable"
    DECELERATING  = "decelerating"


class ForceType(str, Enum):
    MILITARY   = "military"
    ECONOMIC   = "economic"
    NARRATIVE  = "narrative"
    BALANCED   = "balanced"


# ── Data contracts ─────────────────────────────────────────────────────────────

@dataclass
class MethodWeights:
    driving_forces: float          # normalized, sums to 1.0 with others
    game_theory:    float
    chessboard:     float
    derived_from:   str            # human-readable justification
    analyst_override: bool = False # True if analyst manually adjusted
    raw_df: float = 0.0            # pre-normalization values, for audit
    raw_gt: float = 0.0
    raw_cb: float = 0.0

    def __post_init__(self) -> None:
        total = self.driving_forces + self.game_theory + self.chessboard
        assert abs(total - 1.0) < 0.001, f"Weights must sum to 1.0, got {total:.4f}"

    @property
    def disagreement_index(self) -> float:
        """
        Low values mean methods are aligned (< 0.1 = aligned).
        High values mean methods diverge significantly (> 0.2 = flag for review).
        """
        df = self.driving_forces
        gt = self.game_theory
        cb = self.chessboard
        return round(abs(df - gt) * 0.15 + abs(gt - cb) * 0.10, 3)

    def as_percentages(self) -> dict[str, int]:
        return {
            "driving_forces": round(self.driving_forces * 100),
            "game_theory":    round(self.game_theory * 100),
            "chessboard":     round(self.chessboard * 100),
        }


# ── State-based default table ──────────────────────────────────────────────────
#
# Rationale:
# - In STABLE / STABILIZATION states, structural forces explain most variance
#   → driving_forces dominant.
# - In active crisis (HYBRID_ESCALATION, PRE_WAR), actor choice is the marginal
#   variable → game_theory rises toward 0.40.
# - In MARITIME_PRESSURE, geographic chokepoint positioning is decisive
#   → chessboard dominant.
# - In REGIONAL_WAR, game theory fully dominant (rational actor decisions at the margin).
#
_STATE_DEFAULTS: dict[SystemState, tuple[float, float, float]] = {
    # state                              df     gt     cb
    SystemState.STABLE:                 (0.50, 0.25, 0.25),
    SystemState.MANAGED_TENSION:        (0.40, 0.30, 0.30),
    SystemState.CONTROLLED_INSTABILITY: (0.35, 0.35, 0.30),
    SystemState.DISTRIBUTED_COERCION:   (0.35, 0.35, 0.30),
    SystemState.MARITIME_PRESSURE:      (0.30, 0.30, 0.40),
    SystemState.HYBRID_ESCALATION:      (0.30, 0.40, 0.30),
    SystemState.PRE_WAR_TRANSITION:     (0.25, 0.40, 0.35),
    SystemState.REGIONAL_WAR:           (0.20, 0.45, 0.35),
    SystemState.NEGOTIATED_STABILIZATION: (0.45, 0.25, 0.30),
    SystemState.POST_SHOCK_RECOVERY:    (0.45, 0.25, 0.30),
}


def _apply_modifiers(
    df: float,
    gt: float,
    cb: float,
    phase_velocity: PhaseVelocity,
    dominant_force_type: ForceType,
) -> tuple[float, float, float]:
    """
    Apply force-type and velocity modifiers on top of state defaults.
    All values are in percentage points (e.g. 5 = 5pp), applied before normalization.
    """
    # Convert to percentages for modifier arithmetic
    df_pp = df * 100
    gt_pp = gt * 100
    cb_pp = cb * 100

    # Force-type modifiers
    if dominant_force_type == ForceType.MILITARY:
        # Military-dominant: chessboard explains positioning better
        cb_pp += 5
        df_pp -= 5
    elif dominant_force_type == ForceType.ECONOMIC:
        # Economic-dominant: structural/market forces drive outcomes
        df_pp += 5
        cb_pp -= 5
    elif dominant_force_type == ForceType.NARRATIVE:
        # Narrative-dominant: structural framing matters most
        df_pp += 10
        gt_pp -= 5
        cb_pp -= 5

    # Phase velocity modifiers
    if phase_velocity == PhaseVelocity.ACCELERATING:
        # Accelerating crisis → actor choice becoming more decisive
        gt_pp += 5
        df_pp -= 5
    elif phase_velocity == PhaseVelocity.DECELERATING:
        # De-escalating → structural forces re-emerge
        df_pp += 5
        gt_pp -= 5

    # Clamp to [10, 70] to avoid degenerate distributions
    df_pp = max(10.0, min(70.0, df_pp))
    gt_pp = max(10.0, min(60.0, gt_pp))
    cb_pp = max(10.0, min(60.0, cb_pp))

    return df_pp / 100, gt_pp / 100, cb_pp / 100


def _normalize(df: float, gt: float, cb: float) -> tuple[float, float, float]:
    total = df + gt + cb
    if total == 0:
        return 1/3, 1/3, 1/3
    return df / total, gt / total, cb / total


# ── Public API ────────────────────────────────────────────────────────────────

def resolve_method_weights(
    system_state: SystemState,
    phase_velocity: PhaseVelocity = PhaseVelocity.STABLE,
    dominant_force_type: ForceType = ForceType.BALANCED,
) -> MethodWeights:
    """
    Derive method weights from current system state, phase velocity,
    and dominant force type.

    This is the ONLY function that should produce MethodWeights.
    Never instantiate MethodWeights directly with hardcoded values.

    Example:
        weights = resolve_method_weights(
            system_state=SystemState.MANAGED_TENSION,
            phase_velocity=PhaseVelocity.ACCELERATING,
            dominant_force_type=ForceType.MILITARY,
        )
        # Returns: driving_forces≈0.33, game_theory≈0.35, chessboard≈0.32
    """
    base_df, base_gt, base_cb = _STATE_DEFAULTS[system_state]
    raw_df, raw_gt, raw_cb = _apply_modifiers(
        base_df, base_gt, base_cb, phase_velocity, dominant_force_type
    )
    df, gt, cb = _normalize(raw_df, raw_gt, raw_cb)

    justification = (
        f"State={system_state.value} "
        f"velocity={phase_velocity.value} "
        f"force_type={dominant_force_type.value} "
        f"→ base={int(base_df*100)}/{int(base_gt*100)}/{int(base_cb*100)} "
        f"normalized={round(df*100)}/{round(gt*100)}/{round(cb*100)}"
    )

    return MethodWeights(
        driving_forces=round(df, 4),
        game_theory=round(gt, 4),
        chessboard=round(cb, 4),
        derived_from=justification,
        analyst_override=False,
        raw_df=round(raw_df, 4),
        raw_gt=round(raw_gt, 4),
        raw_cb=round(raw_cb, 4),
    )


def apply_analyst_override(
    weights: MethodWeights,
    driving_forces_pct: int,
    game_theory_pct: int,
    chessboard_pct: int,
    reason: str = "",
) -> MethodWeights:
    """
    Apply an analyst manual override to the derived weights.
    Normalizes inputs and marks override=True for audit trail.

    Args:
        weights: the model-derived weights (used to preserve derived_from)
        driving_forces_pct: analyst-specified driving forces percentage (0-100)
        game_theory_pct: analyst-specified game theory percentage (0-100)
        chessboard_pct: analyst-specified chessboard percentage (0-100)
        reason: analyst annotation for the audit log
    """
    df, gt, cb = _normalize(
        driving_forces_pct / 100,
        game_theory_pct / 100,
        chessboard_pct / 100,
    )
    override_note = (
        f"ANALYST OVERRIDE: {driving_forces_pct}/{game_theory_pct}/{chessboard_pct} "
        f"reason='{reason}' | original={weights.derived_from}"
    )
    return MethodWeights(
        driving_forces=round(df, 4),
        game_theory=round(gt, 4),
        chessboard=round(cb, 4),
        derived_from=override_note,
        analyst_override=True,
    )


# ── Convenience: all state defaults as a reference table ─────────────────────

def get_all_state_presets() -> list[dict]:
    """Returns all state presets as a JSON-serializable list. Useful for UI."""
    result = []
    for state, (df, gt, cb) in _STATE_DEFAULTS.items():
        result.append({
            "state": state.value,
            "driving_forces": int(df * 100),
            "game_theory": int(gt * 100),
            "chessboard": int(cb * 100),
        })
    return result


# ── Tests (run with: python -m pytest weight_resolver.py -v) ─────────────────

if __name__ == "__main__":
    import json

    print("=== Weight Resolver Smoke Test ===\n")

    cases = [
        (SystemState.MANAGED_TENSION,     PhaseVelocity.STABLE,        ForceType.MILITARY),
        (SystemState.MARITIME_PRESSURE,   PhaseVelocity.ACCELERATING,  ForceType.MILITARY),
        (SystemState.PRE_WAR_TRANSITION,  PhaseVelocity.ACCELERATING,  ForceType.BALANCED),
        (SystemState.REGIONAL_WAR,        PhaseVelocity.STABLE,        ForceType.MILITARY),
        (SystemState.NEGOTIATED_STABILIZATION, PhaseVelocity.DECELERATING, ForceType.ECONOMIC),
    ]

    for state, vel, force in cases:
        w = resolve_method_weights(state, vel, force)
        pct = w.as_percentages()
        assert abs(w.driving_forces + w.game_theory + w.chessboard - 1.0) < 0.001, "Weights don't sum to 1!"
        print(f"{state.value:<35} | DF={pct['driving_forces']}% GT={pct['game_theory']}% CB={pct['chessboard']}% | di={w.disagreement_index}")

    print("\nAll presets:")
    print(json.dumps(get_all_state_presets(), indent=2))
    print("\n✓ All checks passed")
