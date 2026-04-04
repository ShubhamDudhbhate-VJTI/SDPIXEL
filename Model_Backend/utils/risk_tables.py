"""
Risk lookup tables for the composite scoring system.

All tables are plain Python dicts — no external dependencies.

Tables:
    CATEGORY_TABLE          : category → (min_unit_price_usd, max_unit_price_usd)
    HS_RISK_TABLE           : hs_2digit_prefix (str) → risk_score (0–1)
    COUNTRY_RISK_TABLE      : country_name_lower → risk_score (0–1)
    CATEGORY_HS_GROUP       : category → set of valid 2-digit HS prefixes
"""

# ---------------------------------------------------------------------------
# CATEGORY_TABLE
# (min_price_usd, max_price_usd) per single unit
# ---------------------------------------------------------------------------
CATEGORY_TABLE: dict[str, tuple[float, float]] = {
    "electronics":          (50.0,   2500.0),
    "laptops":              (300.0,  3500.0),
    "mobile_phones":        (100.0,  1500.0),
    "tablets":              (150.0,  1200.0),
    "cameras":              (80.0,   3000.0),
    "audio_equipment":      (20.0,   800.0),
    "clothing":             (5.0,    300.0),
    "footwear":             (10.0,   500.0),
    "textiles":             (2.0,    50.0),     # per metre / per kg
    "furniture":            (50.0,   5000.0),
    "toys":                 (5.0,    200.0),
    "sporting_goods":       (10.0,   1000.0),
    "cosmetics":            (5.0,    300.0),
    "pharmaceuticals":      (10.0,   2000.0),
    "food":                 (1.0,    50.0),
    "beverages":            (2.0,    100.0),
    "chemicals":            (5.0,    500.0),
    "machinery":            (200.0,  50000.0),
    "automotive_parts":     (20.0,   5000.0),
    "tools":                (10.0,   1000.0),
    "jewelry":              (50.0,   50000.0),
    "watches":              (30.0,   20000.0),
    "books":                (5.0,    100.0),
    "medical_devices":      (50.0,   10000.0),
    "batteries":            (5.0,    200.0),
    "cables":               (2.0,    100.0),
    "plastics":             (1.0,    50.0),
    "paper":                (1.0,    30.0),
    "weapons":              (100.0,  5000.0),
    "other":                (1.0,    1000.0),
}

# ---------------------------------------------------------------------------
# HS_RISK_TABLE
# Keyed by the first 2 digits of the HS code (as a zero-padded string).
# Risk reflects likelihood of fraud, smuggling, or mis-classification
# based on WTO/WCO enforcement data.
# ---------------------------------------------------------------------------
HS_RISK_TABLE: dict[str, float] = {
    # Live animals / animal products
    "01": 0.4,   # Live animals
    "02": 0.5,   # Meat
    "03": 0.5,   # Fish / seafood
    "04": 0.3,   # Dairy
    "05": 0.5,   # Other animal products

    # Vegetable products
    "06": 0.3,   # Live plants
    "07": 0.3,   # Vegetables
    "08": 0.3,   # Fruits / nuts
    "09": 0.35,  # Coffee / spices
    "10": 0.2,   # Cereals
    "11": 0.2,   # Milling products
    "12": 0.4,   # Oil seeds
    "13": 0.4,   # Lac / gums / resins
    "14": 0.3,   # Vegetable plaiting materials

    # Fats and oils
    "15": 0.35,  # Animal/vegetable fats

    # Food preparations
    "16": 0.3,   # Prepared meat/fish
    "17": 0.3,   # Sugar
    "18": 0.25,  # Cocoa
    "19": 0.2,   # Cereals / pastry
    "20": 0.2,   # Prepared vegetables
    "21": 0.25,  # Miscellaneous food
    "22": 0.45,  # Beverages / spirits / vinegar
    "23": 0.2,   # Residues / animal feed
    "24": 0.7,   # Tobacco — high duty evasion risk

    # Mineral products
    "25": 0.3,   # Salt / sulphur / stone
    "26": 0.35,  # Ores / slag
    "27": 0.55,  # Mineral fuels / oils

    # Chemicals
    "28": 0.55,  # Inorganic chemicals
    "29": 0.6,   # Organic chemicals
    "30": 0.65,  # Pharmaceutical products
    "31": 0.3,   # Fertilizers
    "32": 0.4,   # Tanning / dyeing extracts
    "33": 0.4,   # Essential oils / cosmetics
    "34": 0.3,   # Soap / cleaning agents
    "35": 0.3,   # Albuminoidal substances
    "36": 0.75,  # Explosives / fireworks
    "37": 0.35,  # Photographic goods
    "38": 0.5,   # Miscellaneous chemicals

    # Plastics / rubber
    "39": 0.35,  # Plastics
    "40": 0.35,  # Rubber

    # Raw hides / leather / furskins
    "41": 0.45,  # Raw hides
    "42": 0.5,   # Leather articles
    "43": 0.55,  # Furskins

    # Wood / paper
    "44": 0.3,   # Wood / articles of wood
    "45": 0.25,  # Cork
    "46": 0.2,   # Manufactures of straw
    "47": 0.2,   # Pulp of wood
    "48": 0.2,   # Paper / paperboard
    "49": 0.2,   # Printed books / newspapers

    # Textiles
    "50": 0.4,   # Silk
    "51": 0.4,   # Wool
    "52": 0.4,   # Cotton
    "53": 0.35,  # Other vegetable fibres
    "54": 0.45,  # Man-made filaments
    "55": 0.45,  # Man-made staple fibres
    "56": 0.35,  # Wadding / felt / nonwovens
    "57": 0.35,  # Carpets
    "58": 0.35,  # Special woven fabrics
    "59": 0.35,  # Impregnated textiles
    "60": 0.35,  # Knitted / crocheted fabrics
    "61": 0.5,   # Knitted clothing — high counterfeit risk
    "62": 0.5,   # Woven clothing — high counterfeit risk
    "63": 0.4,   # Other made-up textile articles

    # Footwear / headgear
    "64": 0.55,  # Footwear — high counterfeit risk
    "65": 0.35,  # Headgear
    "66": 0.3,   # Umbrellas / walking sticks
    "67": 0.35,  # Prepared feathers

    # Articles of stone / ceramic / glass
    "68": 0.25,  # Stone articles
    "69": 0.25,  # Ceramic products
    "70": 0.3,   # Glass

    # Precious metals / jewelry
    "71": 0.75,  # Natural pearls / precious stones / jewelry

    # Base metals
    "72": 0.35,  # Iron / steel
    "73": 0.35,  # Iron / steel articles
    "74": 0.4,   # Copper
    "75": 0.35,  # Nickel
    "76": 0.35,  # Aluminium
    "78": 0.3,   # Lead
    "79": 0.3,   # Zinc
    "80": 0.3,   # Tin
    "81": 0.35,  # Other base metals
    "82": 0.4,   # Tools / knives
    "83": 0.3,   # Miscellaneous metal articles

    # Machinery / electronics
    "84": 0.45,  # Nuclear reactors / machinery
    "85": 0.5,   # Electrical machinery / electronics

    # Transport
    "86": 0.3,   # Railway
    "87": 0.45,  # Motor vehicles
    "88": 0.5,   # Aircraft
    "89": 0.4,   # Ships

    # Precision instruments
    "90": 0.5,   # Optical / photographic / medical instruments
    "91": 0.55,  # Clocks / watches

    # Miscellaneous manufactured articles
    "92": 0.3,   # Musical instruments
    "93": 0.85,  # Arms / ammunition — highest risk
    "94": 0.3,   # Furniture
    "95": 0.4,   # Toys / games / sports equipment
    "96": 0.35,  # Miscellaneous manufactured articles
    "97": 0.6,   # Works of art / antiques
    "99": 0.7,   # Special classification provisions
}

# ---------------------------------------------------------------------------
# COUNTRY_RISK_TABLE
# Lower = lower risk, Higher = higher risk (0–1).
# Based on WCO compliance data, FATF assessments, and customs enforcement stats.
# Keys are lowercase country names.
# ---------------------------------------------------------------------------
COUNTRY_RISK_TABLE: dict[str, float] = {
    # Very Low Risk (0.1–0.2)
    "united states":        0.15,
    "usa":                  0.15,
    "canada":               0.1,
    "australia":            0.1,
    "new zealand":          0.1,
    "norway":               0.1,
    "sweden":               0.1,
    "denmark":              0.1,
    "finland":              0.1,
    "switzerland":          0.15,
    "netherlands":          0.15,
    "germany":              0.15,
    "austria":              0.15,
    "japan":                0.15,
    "south korea":          0.2,
    "singapore":            0.15,

    # Low Risk (0.2–0.35)
    "united kingdom":       0.2,
    "france":               0.2,
    "italy":                0.2,
    "spain":                0.2,
    "portugal":             0.25,
    "belgium":              0.2,
    "ireland":              0.2,
    "czech republic":       0.25,
    "poland":               0.25,
    "hungary":              0.25,
    "taiwan":               0.2,
    "hong kong":            0.25,
    "israel":               0.25,
    "united arab emirates": 0.3,
    "uae":                  0.3,
    "brazil":               0.35,
    "mexico":               0.35,
    "chile":                0.3,
    "argentina":            0.35,
    "malaysia":             0.3,
    "thailand":             0.3,
    "indonesia":            0.35,
    "india":                0.35,
    "south africa":         0.35,

    # Medium Risk (0.4–0.6)
    "china":                0.5,
    "russia":               0.6,
    "turkey":               0.45,
    "vietnam":              0.45,
    "bangladesh":           0.5,
    "pakistan":             0.55,
    "sri lanka":            0.45,
    "egypt":                0.5,
    "morocco":              0.45,
    "nigeria":              0.6,
    "ghana":                0.5,
    "kenya":                0.5,
    "ethiopia":             0.5,
    "ukraine":              0.55,
    "kazakhstan":           0.5,
    "philippines":          0.45,
    "cambodia":             0.55,
    "peru":                 0.45,
    "colombia":             0.55,
    "ecuador":              0.5,
    "jordan":               0.45,
    "lebanon":              0.6,
    "algeria":              0.5,
    "tunisia":              0.45,

    # High Risk (0.65–0.85)
    "iran":                 0.85,
    "north korea":          0.95,
    "venezuela":            0.75,
    "cuba":                 0.7,
    "myanmar":              0.75,
    "syria":                0.85,
    "libya":                0.8,
    "sudan":                0.75,
    "somalia":              0.85,
    "afghanistan":          0.85,
    "iraq":                 0.75,
    "yemen":                0.8,
    "mali":                 0.7,
    "central african republic": 0.75,
    "democratic republic of congo": 0.75,
    "drc":                  0.75,
    "zimbabwe":             0.7,
    "haiti":                0.7,
    "belarus":              0.65,

    # Default for unknown
    "_default":             0.4,
}

# ---------------------------------------------------------------------------
# CATEGORY_HS_GROUP
# Maps each category to a set of valid 2-digit HS code prefixes.
# Used to detect HS code / category mismatches (+0.2 penalty).
# ---------------------------------------------------------------------------
CATEGORY_HS_GROUP: dict[str, set[str]] = {
    "electronics":          {"84", "85"},
    "laptops":              {"84", "85"},
    "mobile_phones":        {"85"},
    "tablets":              {"84", "85"},
    "cameras":              {"90"},
    "audio_equipment":      {"85"},
    "clothing":             {"61", "62"},
    "footwear":             {"64"},
    "textiles":             {"50", "51", "52", "53", "54", "55", "56", "57", "58", "59", "60", "63"},
    "furniture":            {"94"},
    "toys":                 {"95"},
    "sporting_goods":       {"95"},
    "cosmetics":            {"33"},
    "pharmaceuticals":      {"30"},
    "food":                 {"02", "03", "04", "07", "08", "16", "17", "18", "19", "20", "21"},
    "beverages":            {"22"},
    "chemicals":            {"28", "29", "38"},
    "machinery":            {"84"},
    "automotive_parts":     {"87"},
    "tools":                {"82", "84"},
    "jewelry":              {"71"},
    "watches":              {"91"},
    "books":                {"49"},
    "medical_devices":      {"90"},
    "batteries":            {"85"},
    "cables":               {"85"},
    "plastics":             {"39"},
    "paper":                {"48", "49"},
    "weapons":              {"93"},
    "other":                set(),   # no mismatch penalty for "other"
}
