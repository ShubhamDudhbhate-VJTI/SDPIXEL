"""Quick test for the VLM JSON sanitizer."""
import sys
import json
sys.path.insert(0, ".")
from utils.vlm_extractor import sanitize_and_parse_json

# Test 1: Markdown code fences (the exact bug the user reported)
raw_fenced = """```json
{
  "parties": {
    "exporter": { "name": "FastTrade Ltd", "country": "UAE" },
    "consignee": { "name": "ABC Traders", "country": "India" }
  },
  "shipment_details": {
    "ship_date": "01-04-2026",
    "invoice_no": "INV-002",
    "subtotal": 10000
  },
  "extracted_items": [
    {
      "item_name": "Cotton T-shirts",
      "hs_code": "6109",
      "vision_label": "xray image of a stack of cotton T-shirts"
    }
  ]
}
```"""

result1 = sanitize_and_parse_json(raw_fenced)
assert "_error" not in result1, f"FAIL Test 1: {result1.get('_error')}"
assert result1["parties"]["exporter"]["name"] == "FastTrade Ltd"
print("PASS Test 1: Markdown code fences stripped correctly")

# Test 2: Clean JSON (should still work)
raw_clean = '{"parties": {"exporter": {"name": "Test"}}, "extracted_items": []}'
result2 = sanitize_and_parse_json(raw_clean)
assert "_error" not in result2
print("PASS Test 2: Clean JSON parsed correctly")

# Test 3: JSON with leading prose
raw_prose = 'Here is the extracted data:\n{"parties": {}, "extracted_items": []}\nDone.'
result3 = sanitize_and_parse_json(raw_prose)
assert "_error" not in result3
print("PASS Test 3: Leading prose handled correctly")

# Test 4: Completely invalid text
raw_garbage = "I cannot process this image."
result4 = sanitize_and_parse_json(raw_garbage)
assert "_error" in result4
print("PASS Test 4: Garbage input returns error dict correctly")

print("\nAll tests passed!")
