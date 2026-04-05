try:
    from .pdf_extractor import pdf_to_base64, pdf_to_jpeg_bytes, pdf_to_base64_from_path
except ImportError as e:
    print(f"Warning: pdf_extractor not available: {e}")
    pdf_to_base64 = pdf_to_jpeg_bytes = pdf_to_base64_from_path = None

try:
    from .vlm_extractor import extract_invoice_data, sanitize_and_parse_json
except ImportError as e:
    print(f"Warning: vlm_extractor not available: {e}")
    extract_invoice_data = sanitize_and_parse_json = None
