"""
Final risk scoring — Stages 7 & 8 of the composite risk pipeline.

Combines data_risk and visual_risk into a single final score and maps it
to a RED / YELLOW / GREEN customs decision.

Public API:
    compute_final_risk(data_risk, visual_risk) → (final_risk: float, decision: str)
"""

from __future__ import annotations

# Decision thresholds (Stage 8)
THRESHOLD_RED: float = 0.7
THRESHOLD_YELLOW: float = 0.4

# Weights when both data_risk and visual_risk are available (Stage 7)
WEIGHT_DATA: float = 0.4
WEIGHT_VISUAL: float = 0.6


def _decide(final_risk: float) -> str:
    """Map a final_risk score to a RED / YELLOW / GREEN decision string."""
    if final_risk >= THRESHOLD_RED:
        return "RED"
    if final_risk >= THRESHOLD_YELLOW:
        return "YELLOW"
    return "GREEN"


def compute_final_risk(
    data_risk: float | None,
    visual_risk: float,
) -> tuple[float, str]:
    """
    Compute the composite final risk and the customs decision.

    When data_risk is available (manifest was uploaded and LLM extracted it):
        final_risk = (0.4 × data_risk) + (0.6 × visual_risk)

    When data_risk is None (no manifest / extraction failed):
        final_risk = visual_risk
        (The data weight is not redistributed — visual_risk already
        captures all available signal.)

    Args:
        data_risk    : Output of compute_data_risk()["data_risk"], or None.
        visual_risk  : Output of compute_visual_risk() in [0, 1].

    Returns:
        (final_risk, decision) where:
            final_risk : float clamped to [0, 1]
            decision   : "RED" | "YELLOW" | "GREEN"
    """
    if data_risk is None:
        final_risk = visual_risk
    else:
        final_risk = WEIGHT_DATA * data_risk + WEIGHT_VISUAL * visual_risk

    final_risk = min(max(final_risk, 0.0), 1.0)
    decision = _decide(final_risk)
    return round(final_risk, 4), decision
