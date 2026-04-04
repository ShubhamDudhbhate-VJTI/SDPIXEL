"""
test_pipeline.py — Verify the full document risk pipeline without Ollama.

Three test cases covering: valid normal, undervaluation, missing value + unknown origin.
"""

import json
from textual_risk_analyzer import TextualRiskAnalyzer

analyzer = TextualRiskAnalyzer()

# ─────────────────────────────────────────────────────────────────────────────
# CASE 1: Normal shipment — China, electronics + clothing, value in range
# Expect: MEDIUM (China = MEDIUM, everything else clean)
# ─────────────────────────────────────────────────────────────────────────────
CASE_1 = {
    "parties": {
        "exporter":  {"name": "ShenZhen TechExports Ltd", "country": "China"},
        "consignee": {"name": "GlobalTrade Pvt Ltd",       "country": "India"},
    },
    "shipment_details": {
        "ship_date": "2024-03-15", "invoice_no": "INV-2024-0831",
        "subtotal": 320_000, "insurance": 500, "freight": 2_000,
        "packing": 300, "handling": 200, "other": 0,
    },
    "extracted_items": [
        {
            "packages": 5, "units": 5, "net_weight": "12.5 kg", "uom": "PCS",
            "item_name": "MacBook Pro 16-inch",
            "category":  "Laptop",             # LLM gave this
            "hs_code":   "8471.30",
            "origin_country": "China",
            "unit_value": 55_000, "total_value": 275_000,
            "vision_label": "xray image of flat rectangular slab with dense layered internal circuitry",
        },
        {
            "packages": 2, "units": 10, "net_weight": "3.2 kg", "uom": "PCS",
            "item_name": "Cotton T-shirts (assorted)",
            "category":  "Clothing",           # LLM gave this
            "hs_code":   "6109.10",
            "origin_country": "China",
            "unit_value": 450, "total_value": 4_500,
            "vision_label": "xray image of stacked folded flat fabric silhouettes of uniform density",
        },
    ],
}

# ─────────────────────────────────────────────────────────────────────────────
# CASE 2: Undervaluation — 10 laptops declared at ₹50k total (min = ₹400k)
# Expect: HIGH (massive undervaluation + China)
# ─────────────────────────────────────────────────────────────────────────────
CASE_2 = {
    "parties": {
        "exporter":  {"name": "FastShip Ltd",     "country": "China"},
        "consignee": {"name": "BudgetImports Inc", "country": "India"},
    },
    "shipment_details": {
        "ship_date": "2024-04-01", "invoice_no": "INV-2024-9999",
        "subtotal": 50_000,         # declared, but 10 laptops min = ₹400k
        "insurance": None, "freight": None, "packing": None, "handling": None, "other": None,
    },
    "extracted_items": [
        {
            "packages": 10, "units": 10, "net_weight": "25 kg", "uom": "PCS",
            "item_name": "Dell XPS 15 Laptop",
            "category":  "Laptop",
            "hs_code":   "8471.30",
            "origin_country": "China",
            "unit_value": 5_000, "total_value": 50_000,   # suspiciously low
            "vision_label": "xray image of stacked rectangular flat slabs with internal circuit boards",
        },
    ],
}

# ─────────────────────────────────────────────────────────────────────────────
# CASE 3: Missing value + unknown origin + bad LLM category
# Expect: MEDIUM-HIGH (unknown origin = HIGH country risk, value fallback = 0.3,
#         bad category → UNKNOWN)
# ─────────────────────────────────────────────────────────────────────────────
CASE_3 = {
    "parties": {
        "exporter":  {"name": "Unknown Seller", "country": ""},     # missing country
        "consignee": {"name": "Mystery Corp",   "country": "India"},
    },
    "shipment_details": {
        "ship_date": "N/A", "invoice_no": "---",
        "subtotal": None,   # no declared value
        "insurance": None, "freight": None, "packing": None, "handling": None, "other": None,
    },
    "extracted_items": [
        {
            "packages": 3, "units": 3, "net_weight": "5 kg", "uom": "PCS",
            "item_name": "Assorted Electronic Components",
            "category":  "Electronic Stuff",   # invalid — LLM hallucinated a bad label
            "hs_code":   "",                   # no HS code
            "origin_country": "",              # unknown origin
            "unit_value": None, "total_value": None,
            "vision_label": "xray image of loose small rectangular and cylindrical components",
        },
    ],
}


def run(label: str, case: dict) -> None:
    print(f"\n{'═'*60}")
    print(f"  {label}")
    print(f"{'═'*60}")
    r = analyzer.analyze(case)
    d = r.to_dict()
    print(f"  DATA_RISK  : {d['Data_Risk']:.4f}")
    print(f"  RISK LEVEL : {d['risk_level']}")
    print(f"  Breakdown:")
    for k, v in d["breakdown"].items():
        print(f"    {k:<18}: {v:.4f}")
    print(f"  Origin: {d['context']['origin']} ({d['context']['region']})")
    print(f"  Value : {d['context']['declared_status']}  "
          f"declared={d['context']['declared_value']}  "
          f"window=[{d['context']['total_min']}, {d['context']['total_max']}]")
    if d["context"]["consistency_flags"]:
        print(f"  ⚠ HS Flags:")
        for f in d["context"]["consistency_flags"]:
            print(f"    {f['item']} → expected HS {f['expected_hs']}, got {f['declared_hs']}")
    cats = [(i["item_name"], i["category"]) for i in d["context"]["items"]]
    print(f"  Categories: {cats}")


if __name__ == "__main__":
    run("CASE 1 — Normal (China, Laptop + Clothing, value in range)", CASE_1)
    run("CASE 2 — Undervaluation (10 Laptops, declared ₹50k vs min ₹400k)", CASE_2)
    run("CASE 3 — Missing value + Unknown origin + bad LLM category", CASE_3)
