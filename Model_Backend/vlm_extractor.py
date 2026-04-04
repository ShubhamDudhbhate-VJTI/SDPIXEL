"""
vlm_extractor.py — Stage 2: Vision-Language Model invoice extraction.

UPDATED PROMPT: The LLM is now given the complete CATEGORY_TABLE taxonomy
with descriptions and HS chapter hints so it can classify each item
confidently. The textual_risk_analyzer.py trusts this output and only
validates — it does not re-infer locally.

Usage:
    from vlm_extractor import extract_invoice_data

    result = extract_invoice_data(base64_image_string)
    # result is a parsed dict — guaranteed, never raw text.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, Optional

import requests

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────
DEFAULT_OLLAMA_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL      = "ministral-3:14b-cloud"
DEFAULT_TIMEOUT    = 300  # seconds


# ─────────────────────────────────────────────────────────────────────────────
# CATEGORY TAXONOMY
# This is injected verbatim into the prompt so the LLM knows exactly what
# labels to use and what each label means. Must stay in sync with
# CATEGORY_TABLE in textual_risk_analyzer.py.
# ─────────────────────────────────────────────────────────────────────────────

CATEGORY_TAXONOMY = """
CATEGORY TAXONOMY (use the exact string shown — case-sensitive):

  "Laptop"               — portable personal computers, notebooks, MacBooks,
                           Chromebooks, ultrabooks. Expected HS chapter: 84.

  "Mobile Phone"         — smartphones, iPhones, Android handsets, feature
                           phones, cellular devices. Expected HS chapter: 85.

  "Electronics"          — consumer electronics that are NOT laptops or phones:
                           tablets, headphones, earbuds, cameras, speakers, TVs,
                           monitors, keyboards, mice, routers, USB hubs, SSDs,
                           hard drives, smartwatches, drones, power banks.
                           Expected HS chapter: 85.

  "Clothing"             — finished garments worn on the body: shirts, t-shirts,
                           jeans, trousers, jackets, dresses, coats, uniforms,
                           socks, underwear, shoes, boots, sandals, sneakers.
                           Expected HS chapter: 61.

  "Machinery"            — heavy industrial machines: CNC machines, lathes,
                           pumps, compressors, turbines, motors, boilers,
                           generators (industrial scale). Expected HS chapter: 84.

  "Industrial Equipment" — equipment used in factories/warehouses: cranes,
                           forklifts, conveyors, welding sets, hydraulic
                           equipment, pneumatic tools. Expected HS chapter: 84.

  "Food Products"        — edible goods: rice, wheat, flour, spices, sauces,
                           biscuits, snacks, chocolate, coffee, tea, sugar, oils,
                           grains, cereals, pasta, noodles, juices, canned food.
                           Expected HS chapter: 20.

  "Furniture"            — chairs, tables, desks, sofas, cabinets, shelves,
                           wardrobes, mattresses, bed frames, bookcases.
                           Expected HS chapter: 94.

  "Pharmaceuticals"      — medicines, drugs, vaccines, antibiotics, capsules,
                           syrups, injections, supplements, vitamins.
                           Expected HS chapter: 30.

  "Automobile Parts"     — parts for cars/vehicles: tyres, brakes, engine
                           components, gears, axles, bumpers, headlights,
                           exhaust systems, catalytic converters.
                           Expected HS chapter: 87.

  "Cosmetics"            — personal care & beauty products: perfumes, creams,
                           lotions, shampoos, lipstick, mascara, foundation,
                           serums, deodorants, sunscreens. Expected HS chapter: 33.

  "Textiles"             — raw/semi-processed fabric material (NOT finished
                           garments): fabric rolls, yarn, cotton bales, wool,
                           silk, linen, polyester, nylon, thread.
                           Expected HS chapter: 52.

  "Plastic Goods"        — manufactured plastic articles: containers, PVC
                           products, polypropylene goods, plastic bottles/bags,
                           casings. Expected HS chapter: 39.

  "Metal Products"       — articles of base metal: steel/iron/aluminium parts,
                           bolts, nuts, screws, wires, pipes, tubes, sheet metal,
                           castings, forgings. Expected HS chapter: 73.

  "Toys"                 — children's toys & games: dolls, action figures,
                           puzzles, LEGO, board games, stuffed animals, RC cars.
                           Expected HS chapter: 95.

  "UNKNOWN"              — use ONLY if the item cannot be confidently classified
                           into any of the above 15 categories.
"""


# ─────────────────────────────────────────────────────────────────────────────
# EXTRACTION PROMPT
# ─────────────────────────────────────────────────────────────────────────────

EXTRACTION_PROMPT = f"""You are an expert X-ray cargo security translation engine. \
Carefully analyze the provided invoice image and extract ALL specified fields \
into a single valid JSON object. Return ONLY the JSON — no text before or after it, \
no markdown fences, no explanation.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK A — ITEM EXTRACTION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
For EACH line item in the invoice table produce:

  1. "item_name"      Copy exactly as it appears on the invoice.

  2. "category"       Classify the item into EXACTLY ONE category from the
                      taxonomy below. Use the exact string shown (case-sensitive).
                      If genuinely uncertain, use "UNKNOWN".

  3. "vision_label"   Translate the item into a physical/structural description
                      for a downstream open-vocabulary X-ray vision model.

{CATEGORY_TAXONOMY}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK B — VISION LABEL RULES (CRITICAL)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ✓ MANDATORY PREFIX: every vision_label MUST begin with "xray image of "
  ✓ FOCUS ON STRUCTURE: describe geometry, silhouettes, structural density
  ✓ NO COLORS: images are grayscale — never use color words (blue, red, dark, light)
  ✗ NO SINGLE WORDS: never use bare nouns alone
  Good example:  "xray image of flat rectangular slab with dense layered internal circuitry"
  Bad example:   "xray image of laptop"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK C — CATEGORY DECISION RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  • Use the HS code on the invoice as a hint, but classify by the ITEM NAME.
  • Finished garments → "Clothing". Raw fabric rolls → "Textiles".
  • Industrial generators → "Machinery". Consumer power banks → "Electronics".
  • If you are less than 80% confident → use "UNKNOWN".

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT SCHEMA (strict — all fields required)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{{
  "parties": {{
    "exporter":  {{ "name": "string", "country": "string" }},
    "consignee": {{ "name": "string", "country": "string" }}
  }},
  "shipment_details": {{
    "ship_date":  "string",
    "invoice_no": "string",
    "subtotal":   <number or null>,
    "insurance":  <number or null>,
    "freight":    <number or null>,
    "packing":    <number or null>,
    "handling":   <number or null>,
    "other":      <number or null>
  }},
  "extracted_items": [
    {{
      "packages":       <number>,
      "units":          <number>,
      "net_weight":     "string",
      "uom":            "string",
      "item_name":      "string",
      "category":       "string",
      "hs_code":        "string",
      "origin_country": "string",
      "unit_value":     <number or null>,
      "total_value":    <number or null>,
      "vision_label":   "string"
    }}
  ]
}}

Return ONLY the JSON object. No preamble. No explanation. No markdown."""


# ─────────────────────────────────────────────────────────────────────────────
# Core extraction function
# ─────────────────────────────────────────────────────────────────────────────

def extract_invoice_data(
    base64_image: str,
    *,
    ollama_url: str = DEFAULT_OLLAMA_URL,
    model:      str = DEFAULT_MODEL,
    timeout:    int = DEFAULT_TIMEOUT,
    prompt: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Send a base64-encoded invoice image to the Ollama VLM and return
    the extracted data as a parsed Python dict.

    Args:
        base64_image:  Base64-encoded JPEG/PNG (no data-URI prefix).
        ollama_url:    Ollama API endpoint.
        model:         Model tag (e.g. 'qwen3-vl:235b-cloud').
        timeout:       Request timeout in seconds.
        prompt:        Override prompt. Uses EXTRACTION_PROMPT if None.

    Returns:
        Parsed dict matching the invoice schema.
        On parse failure: dict with '_raw_response' and '_error' keys.

    Raises:
        requests.exceptions.ConnectionError  — Ollama unreachable
        requests.exceptions.Timeout          — request exceeded timeout
        requests.exceptions.HTTPError        — non-2xx response
    """
    payload = {
        "model":  model,
        "prompt": prompt or EXTRACTION_PROMPT,
        "images": [base64_image],
        "stream": False,
        "format": "json",
    }

    logger.info("Sending extraction request → %s  model=%s", ollama_url, model)

    response = requests.post(ollama_url, json=payload, timeout=timeout)
    response.raise_for_status()

    raw_text = response.json().get("response", "{}")
    return _sanitize_and_parse(raw_text)


# ─────────────────────────────────────────────────────────────────────────────
# JSON sanitization
# ─────────────────────────────────────────────────────────────────────────────

def _sanitize_and_parse(raw_text: str) -> Dict[str, Any]:
    """
    Parse JSON from VLM output. Strips markdown code fences if present.
    Returns error dict on failure — never raises.
    """
    cleaned = raw_text.strip()
    cleaned = re.sub(r"^```(?:json|JSON)?\s*\n?", "", cleaned)
    cleaned = re.sub(r"\n?\s*```\s*$", "", cleaned)
    cleaned = cleaned.strip()

    try:
        result = json.loads(cleaned)
        return result if isinstance(result, dict) else {"data": result}
    except (json.JSONDecodeError, TypeError):
        logger.warning("Failed to parse VLM output as JSON. Raw: %s", raw_text[:200])
        return {
            "_raw_response": raw_text,
            "_error":        "Model output was not valid JSON.",
        }
