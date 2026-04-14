from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class SystemState(str, Enum):
    STABLE = "stable"
    MANAGED_TENSION = "managed_tension"
    CONTROLLED_INSTABILITY = "controlled_instability"
    MARITIME_PRESSURE = "maritime_pressure"
    HYBRID_ESCALATION = "hybrid_escalation"
    PRE_WAR_TRANSITION = "pre_war_transition"
    REGIONAL_WAR = "regional_war"
    NEGOTIATED_STABILIZATION = "negotiated_stabilization"


class PhaseVelocity(str, Enum):
    ACCELERATING = "accelerating"
    STABLE = "stable"
    DECELERATING = "decelerating"


class ForceType(str, Enum):
    MILITARY = "military"
    ECONOMIC = "economic"
    NARRATIVE = "narrative"
    BALANCED = "balanced"


@dataclass
class MethodWeights:
    driving_forces: float
    game_theory: float
    chessboard: float
    derived_from: str
    analyst_override: bool = False

    @property
    def disagreement_index(self) -> float:
        df = self.driving_forces
        gt = self.game_theory
        cb = self.chessboard
        return round(abs(df - gt) * 0.15 + abs(gt - cb) * 0.1, 3)


_STATE_DEFAULTS: dict[SystemState, tuple[float, float, float]] = {
    SystemState.STABLE: (0.50, 0.25, 0.25),
    SystemState.MANAGED_TENSION: (0.40, 0.30, 0.30),
    SystemState.CONTROLLED_INSTABILITY: (0.35, 0.35, 0.30),
    SystemState.MARITIME_PRESSURE: (0.30, 0.30, 0.40),
    SystemState.HYBRID_ESCALATION: (0.30, 0.40, 0.30),
    SystemState.PRE_WAR_TRANSITION: (0.25, 0.40, 0.35),
    SystemState.REGIONAL_WAR: (0.20, 0.45, 0.35),
    SystemState.NEGOTIATED_STABILIZATION: (0.45, 0.25, 0.30),
}


def _normalize(df: float, gt: float, cb: float) -> tuple[float, float, float]:
    total = df + gt + cb
    if total <= 0:
        return (1 / 3, 1 / 3, 1 / 3)
    return (df / total, gt / total, cb / total)


def resolve_method_weights(
    *,
    system_state: SystemState,
    phase_velocity: PhaseVelocity,
    dominant_force_type: ForceType,
) -> MethodWeights:
    df, gt, cb = _STATE_DEFAULTS[system_state]

    if dominant_force_type == ForceType.MILITARY:
        cb += 0.05
        df -= 0.05
    elif dominant_force_type == ForceType.ECONOMIC:
        df += 0.05
        cb -= 0.05
    elif dominant_force_type == ForceType.NARRATIVE:
        df += 0.10
        gt -= 0.05
        cb -= 0.05

    if phase_velocity == PhaseVelocity.ACCELERATING:
        gt += 0.05
        df -= 0.05
    elif phase_velocity == PhaseVelocity.DECELERATING:
        df += 0.05
        gt -= 0.05

    df, gt, cb = _normalize(max(0.1, df), max(0.1, gt), max(0.1, cb))
    return MethodWeights(
        driving_forces=round(df, 4),
        game_theory=round(gt, 4),
        chessboard=round(cb, 4),
        derived_from=(
            f"State={system_state.value}, velocity={phase_velocity.value}, "
            f"dominant_force={dominant_force_type.value}"
        ),
        analyst_override=False,
    )

