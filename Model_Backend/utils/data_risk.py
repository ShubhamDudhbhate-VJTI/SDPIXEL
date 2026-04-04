"""
Data risk scoring — Stage 5 of the composite risk pipeline.

Computes risk derived from the commercial invoice / packing list:
    - Value anomaly    (declared value vs expected price range)
    - HS code risk     (inherent HS risk + category mismatch penalty)
    - Country risk     (origin country)
    - Importer risk    (fixed at 0.5 per spec)

Public API:
    compute_data_risk(items, declared_value, origin_country) → dict
"""

from __future__ import annotations

from .risk_tables import (
    CATEGORY_HS_GROUP,
    CATEGORY_TABLE,
    COUNTRY_RISK_TABLE,
    HS_RISK_TABLE,
)

# Importer risk is fixed at 0.5 per specification (no importer history yet).
IMPORTER_RISK: float = 0.5

# Penalty added when HS code prefix doesn't match the declared category.
HS_MISMATCH_PENALTY: float = 0.2


# ---------------------------------------------------------------------------
# Sub-scorers
# ---------------------------------------------------------------------------


def compute_value_anomaly(
    items: list[dict],
    declared_value: float | None,
) -> float:
    """
    Compare declared_value against the expected price range for the item list.

    Each item dict must contain:
        name       (str)   — used for logging only
        quantity   (int | float)
        category   (str)   — must match a key in CATEGORY_TABLE

    Returns:
        Anomaly score in [0, 1].
        0.0 if declared_value is None or items is empty.
    """
    if declared_value is None or not items:
        return 0.0

    total_min = 0.0
    total_max = 0.0

    for item in items:
        category = (item.get("category") or "other").lower().strip()
        quantity = float(item.get("quantity") or 1)

        min_price, max_price = CATEGORY_TABLE.get(
            category, CATEGORY_TABLE["other"]
        )
        total_min += quantity * min_price
        total_max += quantity * max_price

    if total_min == 0 and total_max == 0:
        return 0.0

    if declared_value < total_min:
        anomaly = (total_min - declared_value) / total_min
    elif declared_value > total_max:
        anomaly = (declared_value - total_max) / total_max
    else:
        anomaly = 0.0

    return min(anomaly, 1.0)


def compute_hs_risk(items: list[dict]) -> float:
    """
    Compute average HS code risk across all items.

    Each item dict should contain:
        hs_code   (str | None)  — raw HS code (any format)
        category  (str | None)

    Logic per item:
        1. Normalize HS → first 2 digits (zero-padded).
        2. Look up base risk from HS_RISK_TABLE (default 0.4 if unknown).
        3. If hs_code prefix is NOT in the valid set for the declared category,
           add HS_MISMATCH_PENALTY (0.2), clamped to 1.0.
        4. Items with no hs_code contribute 0.4 (neutral default).

    Returns:
        Average risk across all items, clamped to [0, 1].
        0.0 if items is empty.
    """
    if not items:
        return 0.0

    risks: list[float] = []

    for item in items:
        raw_hs = item.get("hs_code")
        category = (item.get("category") or "other").lower().strip()

        if not raw_hs:
            risks.append(0.4)
            continue

        # Normalise: strip spaces / dots / dashes, keep only digits, take first 2
        digits = "".join(filter(str.isdigit, str(raw_hs)))
        prefix = digits[:2].zfill(2) if digits else ""

        base_risk = HS_RISK_TABLE.get(prefix, 0.4)

        # Mismatch penalty: skip for "other" category (CATEGORY_HS_GROUP["other"] is empty)
        valid_prefixes = CATEGORY_HS_GROUP.get(category, set())
        if valid_prefixes and prefix not in valid_prefixes:
            base_risk = min(base_risk + HS_MISMATCH_PENALTY, 1.0)

        risks.append(base_risk)

    return min(sum(risks) / len(risks), 1.0)


def compute_country_risk(origin_country: str | None) -> float:
    """
    Look up country risk from COUNTRY_RISK_TABLE.

    Matching is case-insensitive. Falls back to the "_default" entry (0.4)
    for unknown countries.

    Returns:
        Risk score in [0, 1].
    """
    if not origin_country:
        return COUNTRY_RISK_TABLE["_default"]

    key = origin_country.lower().strip()
    return COUNTRY_RISK_TABLE.get(key, COUNTRY_RISK_TABLE["_default"])


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def compute_data_risk(
    items: list[dict],
    declared_value: float | None,
    origin_country: str | None,
) -> dict:
    """
    Compute the overall data risk from invoice / manifest data.

    Formula (Stage 5.6):
        Data_Risk = (0.3 × value_anomaly)
                  + (0.3 × hs_code_risk)
                  + (0.2 × importer_risk)   [fixed at 0.5]
                  + (0.2 × country_risk)

    Args:
        items          : List of item dicts from LLM extraction.
                         Each must have: name, quantity, category, hs_code.
        declared_value : Total declared customs value in USD, or None.
        origin_country : Country of origin string, or None.

    Returns:
        Dict with keys:
            data_risk       (float [0, 1])
            value_anomaly   (float [0, 1])
            hs_code_risk    (float [0, 1])
            country_risk    (float [0, 1])
            importer_risk   (float — always 0.5)
    """
    value_anomaly = compute_value_anomaly(items, declared_value)
    hs_code_risk = compute_hs_risk(items)
    country_risk = compute_country_risk(origin_country)
    importer_risk = IMPORTER_RISK

    data_risk = (
        0.3 * value_anomaly
        + 0.3 * hs_code_risk
        + 0.2 * importer_risk
        + 0.2 * country_risk
    )
    data_risk = min(max(data_risk, 0.0), 1.0)

    return {
        "data_risk": round(data_risk, 4),
        "value_anomaly": round(value_anomaly, 4),
        "hs_code_risk": round(hs_code_risk, 4),
        "country_risk": round(country_risk, 4),
        "importer_risk": round(importer_risk, 4),
    }
