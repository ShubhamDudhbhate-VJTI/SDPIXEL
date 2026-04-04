"""
textual_risk_analyzer.py — Stage 1: Textual Risk Analyzer (Data Risk Engine)

Consumes the structured JSON output from vlm_extractor.py and runs it
through the 13-stage deterministic risk pipeline.

DESIGN CONTRACT:
  - Category classification is delegated entirely to the LLM (via vlm_extractor).
  - This module only VALIDATES the LLM-provided category against CATEGORY_TABLE.
  - No local keyword inference. If the LLM gives a bad/missing category → UNKNOWN.
  - CATEGORY_TABLE, HS_RISK_TABLE, COUNTRY_REGION_TABLE are the single source
    of truth. They are never modified at runtime.

Usage:
    from textual_risk_analyzer import TextualRiskAnalyzer

    analyzer = TextualRiskAnalyzer()
    result   = analyzer.analyze(vlm_json_output)
    print(result.to_dict())
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# ═════════════════════════════════════════════════════════════════════════════
# SYSTEM TABLE 1 — CATEGORY TABLE
# Each entry: min/max unit price (₹) and the expected HS chapter (2 digits).
# ═════════════════════════════════════════════════════════════════════════════

CATEGORY_TABLE: Dict[str, Dict[str, Any]] = {
    "Laptop":               {"min": 40_000,  "max": 100_000,   "hs_group": "84"},
    "Mobile Phone":         {"min": 10_000,  "max": 80_000,    "hs_group": "85"},
    "Electronics":          {"min": 5_000,   "max": 50_000,    "hs_group": "85"},
    "Clothing":             {"min": 200,     "max": 5_000,     "hs_group": "61"},
    "Machinery":            {"min": 50_000,  "max": 1_000_000, "hs_group": "84"},
    "Industrial Equipment": {"min": 10_000,  "max": 500_000,   "hs_group": "84"},
    "Food Products":        {"min": 100,     "max": 2_000,     "hs_group": "20"},
    "Furniture":            {"min": 2_000,   "max": 50_000,    "hs_group": "94"},
    "Pharmaceuticals":      {"min": 500,     "max": 20_000,    "hs_group": "30"},
    "Automobile Parts":     {"min": 1_000,   "max": 100_000,   "hs_group": "87"},
    "Cosmetics":            {"min": 200,     "max": 10_000,    "hs_group": "33"},
    "Textiles":             {"min": 500,     "max": 20_000,    "hs_group": "52"},
    "Plastic Goods":        {"min": 300,     "max": 15_000,    "hs_group": "39"},
    "Metal Products":       {"min": 1_000,   "max": 50_000,    "hs_group": "73"},
    "Toys":                 {"min": 100,     "max": 5_000,     "hs_group": "95"},
    "UNKNOWN":              {"min": 1_000,   "max": 1_000_000, "hs_group": "00"},
}

_VALID_CATEGORIES: frozenset = frozenset(CATEGORY_TABLE.keys())


# ═════════════════════════════════════════════════════════════════════════════
# SYSTEM TABLE 2 — HS RISK TABLE  (all chapters 01–97, plus 00 for unknown)
# Risk score ∈ [0, 1] representing regulatory/security risk of each HS chapter.
# ═════════════════════════════════════════════════════════════════════════════

# fmt: off
HS_RISK_TABLE: Dict[str, float] = {
    "01": 0.3,  # Live animals
    "02": 0.3,  # Meat & edible offal
    "03": 0.4,  # Fish & seafood
    "04": 0.3,  # Dairy, eggs, honey
    "05": 0.4,  # Other animal products
    "06": 0.2,  # Live trees & plants
    "07": 0.2,  # Edible vegetables
    "08": 0.2,  # Edible fruits & nuts
    "09": 0.3,  # Coffee, tea, spices
    "10": 0.3,  # Cereals
    "11": 0.3,  # Milling products
    "12": 0.4,  # Oil seeds
    "13": 0.4,  # Lac, gums, resins
    "14": 0.4,  # Vegetable plaiting materials
    "15": 0.4,  # Animal/vegetable fats & oils
    "16": 0.5,  # Preparations of meat/fish
    "17": 0.4,  # Sugars & confectionery
    "18": 0.4,  # Cocoa & preparations
    "19": 0.3,  # Preparations of cereals
    "20": 0.3,  # Preparations of vegetables/fruit
    "21": 0.4,  # Miscellaneous edible preparations
    "22": 0.4,  # Beverages, spirits, vinegar
    "23": 0.3,  # Residues from food industry
    "24": 0.6,  # Tobacco ← elevated risk
    "25": 0.3,  # Salt, sulphur, earths, stone
    "26": 0.4,  # Ores, slag, ash
    "27": 0.6,  # Mineral fuels & oils ← elevated risk
    "28": 0.5,  # Inorganic chemicals
    "29": 0.5,  # Organic chemicals
    "30": 0.6,  # Pharmaceutical products ← elevated risk
    "31": 0.5,  # Fertilisers
    "32": 0.5,  # Tanning/dyeing extracts, paints
    "33": 0.5,  # Essential oils, cosmetics, toiletries
    "34": 0.5,  # Soap, waxes, polishes
    "35": 0.5,  # Albuminoidal substances, glues
    "36": 0.6,  # Explosives, pyrotechnics ← elevated risk
    "37": 0.5,  # Photographic/cinematographic goods
    "38": 0.5,  # Miscellaneous chemical products
    "39": 0.4,  # Plastics & articles thereof
    "40": 0.4,  # Rubber & articles thereof
    "41": 0.3,  # Raw hides & skins
    "42": 0.3,  # Articles of leather, travel goods
    "43": 0.3,  # Furskins & artificial fur
    "44": 0.3,  # Wood & articles of wood
    "45": 0.3,  # Cork & articles thereof
    "46": 0.3,  # Manufactures of straw/esparto
    "47": 0.3,  # Pulp of wood
    "48": 0.3,  # Paper & paperboard
    "49": 0.3,  # Printed books, newspapers, manuscripts
    "50": 0.3,  # Silk
    "51": 0.3,  # Wool, fine/coarse animal hair
    "52": 0.3,  # Cotton
    "53": 0.3,  # Other vegetable textile fibres
    "54": 0.3,  # Man-made filaments
    "55": 0.3,  # Man-made staple fibres
    "56": 0.3,  # Wadding, felt, nonwovens
    "57": 0.3,  # Carpets & floor coverings
    "58": 0.3,  # Special woven fabrics
    "59": 0.3,  # Impregnated/coated textile fabrics
    "60": 0.3,  # Knitted or crocheted fabrics
    "61": 0.2,  # Knitted/crocheted clothing & accessories
    "62": 0.2,  # Non-knitted clothing & accessories
    "63": 0.2,  # Other made-up textile articles
    "64": 0.3,  # Footwear
    "65": 0.3,  # Headgear
    "66": 0.3,  # Umbrellas, walking-sticks, whips
    "67": 0.3,  # Prepared feathers, artificial flowers
    "68": 0.3,  # Articles of stone/plaster/cement
    "69": 0.3,  # Ceramic products
    "70": 0.3,  # Glass & glassware
    "71": 0.6,  # Precious stones/metals, jewellery ← elevated risk
    "72": 0.4,  # Iron & steel
    "73": 0.4,  # Articles of iron or steel
    "74": 0.4,  # Copper & articles thereof
    "75": 0.4,  # Nickel & articles thereof
    "76": 0.4,  # Aluminium & articles thereof
    "78": 0.4,  # Lead & articles thereof
    "79": 0.4,  # Zinc & articles thereof
    "80": 0.4,  # Tin & articles thereof
    "81": 0.4,  # Other base metals, cermets
    "82": 0.4,  # Tools, implements, cutlery of base metal
    "83": 0.4,  # Miscellaneous articles of base metal
    "84": 0.5,  # Machinery & mechanical appliances
    "85": 0.6,  # Electrical machinery & equipment ← elevated risk
    "86": 0.5,  # Railway locomotives & rolling stock
    "87": 0.5,  # Vehicles (not railway/tramway)
    "88": 0.6,  # Aircraft, spacecraft ← elevated risk
    "89": 0.5,  # Ships, boats & floating structures
    "90": 0.5,  # Optical, photographic, medical instruments
    "91": 0.4,  # Clocks & watches
    "92": 0.4,  # Musical instruments
    "93": 0.7,  # Arms & ammunition ← CRITICAL risk
    "94": 0.3,  # Furniture, bedding, lamps
    "95": 0.3,  # Toys, games & sports equipment
    "96": 0.3,  # Miscellaneous manufactured articles
    "97": 0.3,  # Works of art, collectors' pieces
    "00": 0.6,  # Unknown/unclassified ← elevated risk (no chapter identified)
}
# fmt: on


# ═════════════════════════════════════════════════════════════════════════════
# SYSTEM TABLE 3 — COUNTRY → REGION → RISK
# Title-case keys match the spec exactly. Lookup is case-insensitive at runtime.
# ═════════════════════════════════════════════════════════════════════════════

COUNTRY_REGION_TABLE: Dict[str, str] = {
    # ── LOW RISK ──────────────────────────────────────────────────────────────
    "USA":              "LOW",
    "Germany":          "LOW",
    "Japan":            "LOW",
    "UK":               "LOW",
    "United Kingdom":   "LOW",
    "Canada":           "LOW",
    "France":           "LOW",
    "Australia":        "LOW",
    "South Korea":      "LOW",
    "Netherlands":      "LOW",
    "Sweden":           "LOW",

    # ── MEDIUM RISK ───────────────────────────────────────────────────────────
    "UAE":              "MEDIUM",
    "United Arab Emirates": "MEDIUM",
    "India":            "MEDIUM",
    "Singapore":        "MEDIUM",
    "China":            "MEDIUM",
    "Brazil":           "MEDIUM",
    "Mexico":           "MEDIUM",
    "Turkey":           "MEDIUM",
    "Malaysia":         "MEDIUM",
    "Thailand":         "MEDIUM",

    # ── HIGH RISK ─────────────────────────────────────────────────────────────
    "Unknown":          "HIGH",
    "Mixed":            "HIGH",
    "North Korea":      "HIGH",
    "Iran":             "HIGH",
    "Afghanistan":      "HIGH",
    "Syria":            "HIGH",
}

# Pre-built lowercase mirror for O(1) case-insensitive lookup
_COUNTRY_LOOKUP: Dict[str, str] = {k.lower(): v for k, v in COUNTRY_REGION_TABLE.items()}

REGION_RISK_TABLE: Dict[str, float] = {
    "LOW":    0.2,
    "MEDIUM": 0.5,
    "HIGH":   0.7,
}

IMPORTER_RISK_DEFAULT: float = 0.5   # neutral — no historical data available


# ═════════════════════════════════════════════════════════════════════════════
# STAGE 3 HELPER — CATEGORY VALIDATION
# The LLM provides the category. We only validate it here — no local inference.
# ═════════════════════════════════════════════════════════════════════════════

def validate_category(llm_category: Any) -> str:
    """
    Accept the LLM-provided category string if it is a known CATEGORY_TABLE key.
    Returns 'UNKNOWN' for any invalid, missing, or garbage value.

    The LLM was given the exact category list in its prompt, so a valid
    response means exact-string match (case-insensitive fallback accepted).
    A bad response is itself a data quality signal — do not silently fix it.
    """
    if not isinstance(llm_category, str) or not llm_category.strip():
        return "UNKNOWN"
    stripped = llm_category.strip()
    if stripped in _VALID_CATEGORIES:
        return stripped
    # Case-insensitive fallback (handles 'laptop' → 'Laptop')
    lower = stripped.lower()
    for valid in _VALID_CATEGORIES:
        if valid.lower() == lower:
            return valid
    logger.warning("LLM returned unrecognized category %r → UNKNOWN", stripped)
    return "UNKNOWN"


# ═════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═════════════════════════════════════════════════════════════════════════════

@dataclass
class CleanItem:
    item_name:   str
    quantity:    float
    hs_code:     str            # raw HS string from LLM (may be empty/invalid)
    origin:      str            # per-item origin country string from LLM
    unit_value:  Optional[float]
    total_value: Optional[float]
    category:    str = "UNKNOWN"  # set during Stage 3 validation


@dataclass
class RiskBreakdown:
    value_anomaly:  float       # 0–1, financial consistency
    hs_code_risk:   float       # 0–1, regulatory alignment
    importer_risk:  float       # 0–1, importer trust baseline
    country_risk:   float       # 0–1, origin geopolitical risk


@dataclass
class RiskContext:
    origin:            str
    region:            str
    declared_status:   str      # "VALID" | "MISSING" | "INVALID"
    declared_value:    Optional[float]
    total_min:         Optional[float]
    total_max:         Optional[float]
    hs_codes_used:     List[str]
    items:             List[Dict[str, Any]]
    consistency_flags: List[Dict[str, Any]]


@dataclass
class RiskResult:
    Data_Risk:  float
    risk_level: str             # "LOW" | "MEDIUM" | "HIGH"
    breakdown:  RiskBreakdown
    context:    RiskContext
    trace:      List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "Data_Risk":  round(self.Data_Risk, 4),
            "risk_level": self.risk_level,
            "breakdown": {
                "value_anomaly":  round(self.breakdown.value_anomaly, 4),
                "hs_code_risk":   round(self.breakdown.hs_code_risk, 4),
                "importer_risk":  round(self.breakdown.importer_risk, 4),
                "country_risk":   round(self.breakdown.country_risk, 4),
            },
            "context": {
                "origin":            self.context.origin,
                "region":            self.context.region,
                "declared_status":   self.context.declared_status,
                "declared_value":    self.context.declared_value,
                "total_min":         self.context.total_min,
                "total_max":         self.context.total_max,
                "hs_codes_used":     self.context.hs_codes_used,
                "items":             self.context.items,
                "consistency_flags": self.context.consistency_flags,
            },
        }


# ═════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═════════════════════════════════════════════════════════════════════════════

def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def _safe_float(val: Any) -> Optional[float]:
    """
    Convert any LLM output value to float. Returns None on failure.
    Handles: int, float, numeric string, None, 'N/A', '---', '₹1,200', etc.
    """
    if val is None:
        return None
    if isinstance(val, (int, float)):
        f = float(val)
        return None if f != f else f        # guard NaN
    if isinstance(val, str):
        cleaned = re.sub(r"[₹$,\s]", "", val.strip())
        if cleaned.lower() in {"", "n/a", "na", "null", "none", "---", "-", "nil"}:
            return None
        try:
            return float(cleaned)
        except ValueError:
            m = re.search(r"\d+\.?\d*", cleaned)
            if m:
                try:
                    return float(m.group())
                except ValueError:
                    pass
    return None


def _normalize_hs(hs_raw: Any) -> str:
    """
    Extract first 2 digits from a raw HS code string.
    '8471.30' → '84', '61.09' → '61', '' → '00'
    Returns '00' for anything unparseable.
    """
    if not hs_raw or not isinstance(hs_raw, str):
        return "00"
    digits = re.sub(r"[^0-9]", "", hs_raw.strip())
    return digits[:2] if len(digits) >= 2 else "00"


def _get_country_risk(origin: str) -> Tuple[str, float]:
    """
    Resolve origin string → region → risk score using COUNTRY_REGION_TABLE.
    Case-insensitive lookup. Defaults to HIGH for unrecognized countries.
    """
    region = _COUNTRY_LOOKUP.get(origin.lower(), "HIGH")
    return region, REGION_RISK_TABLE[region]


# ═════════════════════════════════════════════════════════════════════════════
# MAIN ANALYZER CLASS
# ═════════════════════════════════════════════════════════════════════════════

class TextualRiskAnalyzer:
    """
    13-stage deterministic Data Risk Engine.

    Input:   Parsed dict from vlm_extractor.extract_invoice_data()
    Output:  RiskResult dataclass — call .to_dict() for plain JSON

    Responsibility split:
      LLM (vlm_extractor)  → item names, categories, HS codes, countries, values
      This module           → validation, normalization, math, risk fusion
    """

    def analyze(self, vlm_output: Dict[str, Any]) -> RiskResult:
        trace: List[Dict[str, Any]] = []

        # ── STAGE 1: RAW FIELD EXTRACTION ────────────────────────────────────
        parties          = vlm_output.get("parties") or {}
        shipment_details = vlm_output.get("shipment_details") or {}
        extracted_items  = vlm_output.get("extracted_items") or []

        consignee     = parties.get("consignee") or {}
        importer_name = str(consignee.get("name") or "").strip()
        raw_subtotal  = _safe_float(shipment_details.get("subtotal"))

        trace.append({
            "stage":        "S1_EXTRACT",
            "importer":     importer_name or "UNKNOWN",
            "raw_subtotal": raw_subtotal,
            "item_count":   len(extracted_items),
        })

        # ── STAGE 2: DATA CLEANING ────────────────────────────────────────────
        # • Normalize item names to lowercase
        # • Drop items with quantity ≤ 0
        # • Prefer 'units' (individual items) over 'packages' (boxes)
        clean_items: List[CleanItem] = []
        for raw in extracted_items:
            name = str(raw.get("item_name") or "").strip()
            if not name:
                continue
            qty = _safe_float(raw.get("units")) or _safe_float(raw.get("packages"))
            if qty is None or qty <= 0:
                logger.debug("Dropping item '%s': quantity invalid or ≤ 0.", name)
                continue
            clean_items.append(CleanItem(
                item_name   = name.lower(),
                quantity    = qty,
                hs_code     = str(raw.get("hs_code") or "").strip(),
                origin      = str(raw.get("origin_country") or "").strip(),
                unit_value  = _safe_float(raw.get("unit_value")),
                total_value = _safe_float(raw.get("total_value")),
                category    = str(raw.get("category") or ""),   # raw LLM label
            ))

        # If subtotal missing from shipment_details, derive from line items
        if raw_subtotal is None:
            derived = sum(
                i.total_value for i in clean_items if i.total_value is not None
            )
            raw_subtotal = derived if derived > 0 else None
            trace.append({"stage": "S2_VALUE_FALLBACK", "derived_subtotal": raw_subtotal})

        trace.append({"stage": "S2_CLEAN", "items_retained": len(clean_items)})

        # ── STAGE 3: CATEGORY VALIDATION ─────────────────────────────────────
        # The LLM classified each item using the full category taxonomy (see prompt).
        # We only validate — no local keyword inference.
        # Bad/missing LLM label → UNKNOWN (wide price range, elevated uncertainty).
        for item in clean_items:
            item.category = validate_category(item.category)

        trace.append({
            "stage":   "S3_CATEGORY",
            "mapping": [(i.item_name, i.category) for i in clean_items],
        })

        # ── STAGE 4 + 5: HS CODE EXTRACTION + NORMALIZATION ──────────────────
        # Each item carries its own HS code from the VLM.
        # Normalize to 2-digit chapter. If VLM gave no usable code, fall back
        # to the category's expected HS chapter (from CATEGORY_TABLE).
        normalized_hs_list: List[str] = []
        for item in clean_items:
            hs = _normalize_hs(item.hs_code)
            if hs == "00":
                hs = CATEGORY_TABLE[item.category]["hs_group"]
            normalized_hs_list.append(hs)

        if not normalized_hs_list:
            normalized_hs_list = ["00"]

        trace.append({"stage": "S4_S5_HS", "normalized": normalized_hs_list})

        # ── STAGE 6: HS RISK CALCULATION ──────────────────────────────────────
        # Look up each 2-digit chapter in HS_RISK_TABLE.
        # Default: 0.6 (elevated) for any chapter absent from the table.
        hs_risks     = [HS_RISK_TABLE.get(hs, 0.6) for hs in normalized_hs_list]
        hs_code_risk = sum(hs_risks) / len(hs_risks)

        trace.append({
            "stage":    "S6_HS_RISK",
            "per_code": list(zip(normalized_hs_list, hs_risks)),
            "average":  hs_code_risk,
        })

        # ── STAGE 7: HS ↔ CATEGORY CONSISTENCY ───────────────────────────────
        # For each item, check if the declared HS chapter matches the chapter
        # expected for its category (from CATEGORY_TABLE).
        # Each mismatch → +0.2 penalty (clamped to 1.0).
        consistency_flags: List[Dict[str, Any]] = []
        for item, actual_hs in zip(clean_items, normalized_hs_list):
            expected_hs = CATEGORY_TABLE[item.category]["hs_group"]
            if expected_hs != actual_hs:
                hs_code_risk += 0.2
                consistency_flags.append({
                    "item":        item.item_name,
                    "category":    item.category,
                    "expected_hs": expected_hs,
                    "declared_hs": actual_hs,
                })

        hs_code_risk = _clamp(hs_code_risk)
        trace.append({
            "stage":              "S7_CONSISTENCY",
            "flags":              consistency_flags,
            "hs_code_risk_final": hs_code_risk,
        })

        # ── STAGE 8: DECLARED VALUE STATUS ───────────────────────────────────
        declared_value: Optional[float] = raw_subtotal
        value_anomaly:  Optional[float] = None

        if declared_value is None:
            declared_status = "MISSING"
        elif declared_value <= 0:
            declared_status = "INVALID"
            value_anomaly   = 1.0
        else:
            declared_status = "VALID"

        trace.append({
            "stage":  "S8_DECLARED_VALUE",
            "status": declared_status,
            "value":  declared_value,
        })

        # ── STAGE 9: IMPORTER RISK ────────────────────────────────────────────
        # Fixed default of 0.5 — neutral baseline, no historical data.
        importer      = importer_name or "UNKNOWN"
        importer_risk = IMPORTER_RISK_DEFAULT

        trace.append({
            "stage":         "S9_IMPORTER",
            "importer":      importer,
            "importer_risk": importer_risk,
        })

        # ── STAGE 10: ORIGIN COUNTRY → REGION → RISK ─────────────────────────
        # Collect distinct origin countries from:
        #   (a) per-item origin_country fields
        #   (b) exporter party block
        # Multiple distinct non-empty origins → "Mixed" → HIGH risk.
        all_origins: Set[str] = {i.origin for i in clean_items if i.origin}
        exporter_country = str(
            (parties.get("exporter") or {}).get("country") or ""
        ).strip()
        if exporter_country:
            all_origins.add(exporter_country)

        if len(all_origins) > 1:
            origin = "Mixed"
        elif len(all_origins) == 1:
            origin = next(iter(all_origins))
        else:
            origin = "Unknown"

        region, country_risk = _get_country_risk(origin)

        trace.append({
            "stage":            "S10_COUNTRY",
            "detected_origins": list(all_origins),
            "resolved_origin":  origin,
            "region":           region,
            "country_risk":     country_risk,
        })

        # ── STAGE 11: VALUE ANOMALY (CATEGORY DEPENDENT) ─────────────────────
        # Build expected price window from CATEGORY_TABLE × quantities.
        # Compare declared total against [total_min, total_max].
        # Dampen score by ×0.7 when any item is UNKNOWN (uncertain bounds).
        total_min: Optional[float] = None
        total_max: Optional[float] = None

        if declared_status == "VALID" and clean_items:
            total_min    = 0.0
            total_max    = 0.0
            unknown_flag = False

            for item in clean_items:
                cat_range = CATEGORY_TABLE[item.category]
                if item.category == "UNKNOWN":
                    unknown_flag = True
                total_min += item.quantity * cat_range["min"]
                total_max += item.quantity * cat_range["max"]

            assert declared_value is not None   # already checked above
            if declared_value < total_min:
                # Undervaluation → likely tax evasion
                value_anomaly = _clamp((total_min - declared_value) / total_min)
            elif declared_value > total_max:
                # Overvaluation → possible money laundering
                value_anomaly = _clamp((declared_value - total_max) / total_max)
            else:
                value_anomaly = 0.0

            if unknown_flag:
                value_anomaly *= 0.7    # widen confidence interval on unknown items

            trace.append({
                "stage":          "S11_VALUE_ANOMALY",
                "total_min":      total_min,
                "total_max":      total_max,
                "declared_value": declared_value,
                "unknown_flag":   unknown_flag,
                "value_anomaly":  value_anomaly,
            })
        else:
            trace.append({
                "stage":   "S11_VALUE_ANOMALY",
                "skipped": True,
                "reason":  declared_status,
            })

        # ── STAGE 12: DATA RISK FUSION ────────────────────────────────────────
        # Weighted sum of four independent components.
        # Missing value anomaly → neutral fallback 0.3 (avoids division by zero).
        value_component = value_anomaly if value_anomaly is not None else 0.3

        Data_Risk = _clamp(
            0.3 * value_component   # financial consistency   (30%)
            + 0.3 * hs_code_risk    # regulatory alignment    (30%)
            + 0.2 * importer_risk   # importer trust baseline (20%)
            + 0.2 * country_risk    # geopolitical risk       (20%)
        )

        trace.append({
            "stage":           "S12_FUSION",
            "value_component": value_component,
            "hs_code_risk":    hs_code_risk,
            "importer_risk":   importer_risk,
            "country_risk":    country_risk,
            "Data_Risk":       Data_Risk,
        })

        # ── STAGE 13: FINAL CLASSIFICATION ───────────────────────────────────
        if Data_Risk >= 0.7:
            risk_level = "HIGH"
        elif Data_Risk >= 0.4:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        trace.append({"stage": "S13_CLASSIFY", "risk_level": risk_level})

        # ── BUILD RESULT ──────────────────────────────────────────────────────
        return RiskResult(
            Data_Risk  = Data_Risk,
            risk_level = risk_level,
            breakdown  = RiskBreakdown(
                value_anomaly = value_component,
                hs_code_risk  = hs_code_risk,
                importer_risk = importer_risk,
                country_risk  = country_risk,
            ),
            context = RiskContext(
                origin            = origin,
                region            = region,
                declared_status   = declared_status,
                declared_value    = declared_value,
                total_min         = total_min,
                total_max         = total_max,
                hs_codes_used     = normalized_hs_list,
                consistency_flags = consistency_flags,
                items = [
                    {
                        "item_name":   i.item_name,
                        "quantity":    i.quantity,
                        "category":    i.category,
                        "hs_code_raw": i.hs_code,
                    }
                    for i in clean_items
                ],
            ),
            trace = trace,
        )
