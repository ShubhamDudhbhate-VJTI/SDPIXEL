"""
vlm_extractor.py — Vision-Language Model invoice extraction utility.

Sends a base64-encoded invoice image to an Ollama-hosted VLM and returns
structured JSON with party info, shipment details, and per-item vision labels
for downstream X-ray inspection.

This module has ZERO dependencies on Streamlit or any UI framework.

Usage:
    from utils.vlm_extractor import extract_invoice_data

    result = extract_invoice_data(base64_image_string)
    # result is a parsed dict, guaranteed — never raw text.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, Optional

import requests

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration defaults (can be overridden per-call)
# ---------------------------------------------------------------------------
DEFAULT_OLLAMA_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "qwen3-vl:235b-cloud"
DEFAULT_TIMEOUT = 300  # seconds

# ---------------------------------------------------------------------------
# The extraction prompt
# ---------------------------------------------------------------------------
EXTRACTION_PROMPT = """You are an expert X-ray security translation engine. Carefully analyze the provided image of the cargo invoice. Extract the specified fields from the visual layout into a valid JSON object. 
For each item found in the table, you must do two things:
1. Keep 'item_name' exactly as it appears on the invoice.
2. Generate ONE 'vision_label'. This label translates the item into a physical, structural description for a downstream open-vocabulary vision model.
3. STRICT RULE ALWAYS CREATE A VALID JSON OBJECT NO STRINGS BEFORE OR AFTER IT

**CRITICAL RULES FOR 'vision_label':**
- **Mandatory Prefix:** Every vision_label MUST begin exactly with the phrase 'xray image of '.
- **No Single Words:** Never use basic nouns.
- **Focus on Structure:** Describe global geometry, silhouettes, and structural density (e.g., 'xray image of "item_name" and description about it').
- **STRICTLY NO COLORS:** The images are grayscale. Never use words like blue, red, dark, or light.
- **JSON ONLY**
**Expected JSON Schema Output:**
{
  "parties": {
    "exporter": { "name": "string", "country": "string" },
    "consignee": { "name": "string", "country": "string" }
  },
  "shipment_details": {
    "ship_date": "string",
    "invoice_no": "string",
    "subtotal": "number",
    "insurance": "number",
    "freight": "number",
    "packing": "number",
    "handling": "number",
    "other": "number"
  },
  "extracted_items": [
    {
      "packages": "number",
      "units": "number",
      "net_weight": "string",
      "uom": "string",
      "item_name": "string", 
      "hs_code": "string",
      "origin_country": "string",
      "unit_value": "number",
      "total_value": "number",
      "vision_label": "string" 
    }
  ]
}"""


# ---------------------------------------------------------------------------
# Core extraction function
# ---------------------------------------------------------------------------

def extract_invoice_data(
    base64_image: str,
    *,
    ollama_url: str = DEFAULT_OLLAMA_URL,
    model: str = DEFAULT_MODEL,
    timeout: int = DEFAULT_TIMEOUT,
    prompt: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Send a base64-encoded invoice image to the Ollama VLM and return
    the extracted data as a parsed Python dict.

    Args:
        base64_image:  Base64-encoded JPEG/PNG string (no data-URI prefix).
        ollama_url:    Ollama API endpoint URL.
        model:         Model name to use (e.g. 'qwen3-vl:235b-cloud').
        timeout:       Request timeout in seconds.
        prompt:        Custom extraction prompt. Uses built-in prompt if None.

    Returns:
        Parsed dict matching the invoice schema. On parse failure, returns
        a dict with '_raw_response' and '_error' keys.

    Raises:
        requests.exceptions.ConnectionError: If Ollama is unreachable.
        requests.exceptions.Timeout:         If the request exceeds timeout.
        requests.exceptions.HTTPError:       If Ollama returns a non-2xx status.
    """
    payload = {
        "model": model,
        "prompt": prompt or EXTRACTION_PROMPT,
        "images": [base64_image],
        "stream": False,
        "format": "json",
    }

    logger.info("Sending extraction request to %s (model=%s)", ollama_url, model)

    response = requests.post(ollama_url, json=payload, timeout=timeout)
    response.raise_for_status()

    result = response.json()
    raw_text = result.get("response", "{}")

    return sanitize_and_parse_json(raw_text)


# ---------------------------------------------------------------------------
# JSON sanitization — strip ```json fences if present, then parse
# ---------------------------------------------------------------------------

def sanitize_and_parse_json(raw_text: str) -> Dict[str, Any]:
    """
    Parse JSON from VLM output. If the output is wrapped in markdown
    code fences (```json ... ```), strip them first via regex.
    If not, do nothing — just parse directly.

    Args:
        raw_text: The raw string returned by the VLM.

    Returns:
        Parsed dict on success, or a dict with '_raw_response' and '_error'
        keys on failure.
    """
    cleaned = raw_text.strip()

    # Strip ```json ... ``` fences if present, otherwise leave as-is
    cleaned = re.sub(r"^```(?:json|JSON)?\s*\n?", "", cleaned)
    cleaned = re.sub(r"\n?\s*```\s*$", "", cleaned)
    cleaned = cleaned.strip()

    try:
        result = json.loads(cleaned)
        if isinstance(result, dict):
            return result
        return {"data": result}
    except (json.JSONDecodeError, TypeError):
        logger.warning("Failed to parse VLM output as JSON.")
        return {
            "_raw_response": raw_text,
            "_error": "Model output was not valid JSON.",
        }
