"""
Visual risk scoring — Stage 6 of the composite risk pipeline.

Functions:
    ssim_score_to_risk   : maps SSIM similarity score → risk bucket
    compute_visual_risk  : weighted sum of visual risk signals → [0, 1]
"""


def ssim_score_to_risk(ssim_score: float | None) -> float:
    """
    Map an SSIM similarity score to a risk value.

    Args:
        ssim_score: Structural similarity index in [0, 1], or None if no
                    reference scan was provided.

    Returns:
        Risk value in [0, 1]:
            ssim_score is None  → 0.3  (no reference; mild default)
            ssim_score < 0.5    → 0.9  (very different from reference)
            ssim_score < 0.8    → 0.5  (moderately different)
            ssim_score >= 0.8   → 0.2  (similar to reference; low risk)
    """
    if ssim_score is None:
        return 0.3
    if ssim_score < 0.5:
        return 0.9
    if ssim_score < 0.8:
        return 0.5
    return 0.2


def compute_visual_risk(
    suspicious_score: float,
    uncertain_ratio: float,
    ssim_risk: float,
    shap_intensity_score: float | None,
) -> float:
    """
    Compute the visual risk score from four signals.

    Formula (Stage 6):
        Visual_Risk = (0.5 × suspicious_score)
                    + (0.2 × uncertain_ratio)
                    + (0.2 × ssim_risk)
                    + (0.1 × shap_intensity_score)

    When shap_intensity_score is None (Colab call failed / not configured),
    its weight (0.1) is redistributed to suspicious_score so the total
    weight remains 1.0:
        Visual_Risk = (0.6 × suspicious_score)
                    + (0.2 × uncertain_ratio)
                    + (0.2 × ssim_risk)

    Args:
        suspicious_score     : 1.0 if YOLO detected suspicious/prohibited item,
                               0.0 otherwise.
        uncertain_ratio      : undeclared_count / total_detected from zero-shot
                               (0.0 if zero-shot didn't run).
        ssim_risk            : output of ssim_score_to_risk().
        shap_intensity_score : SHAP intensity in [0, 1] from Colab, or None.

    Returns:
        Visual risk score clamped to [0, 1].
    """
    if shap_intensity_score is None:
        score = (
            0.6 * suspicious_score
            + 0.2 * uncertain_ratio
            + 0.2 * ssim_risk
        )
    else:
        score = (
            0.5 * suspicious_score
            + 0.2 * uncertain_ratio
            + 0.2 * ssim_risk
            + 0.1 * shap_intensity_score
        )

    return min(max(score, 0.0), 1.0)
