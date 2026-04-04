"""
pdf_extractor.py — PDF-to-image conversion utility.

Converts the first page of a PDF into a high-resolution JPEG image,
returning both raw bytes and a base64-encoded string for API transport.

This module has ZERO dependencies on Streamlit or any UI framework.

Usage:
    from utils.pdf_extractor import pdf_to_base64, pdf_to_jpeg_bytes

    # From raw bytes
    b64, jpeg = pdf_to_base64(pdf_bytes)

    # From file path
    b64, jpeg = pdf_to_base64_from_path("invoice.pdf")
"""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Optional, Union

import fitz  # PyMuPDF


def pdf_to_jpeg_bytes(
    pdf_source: Union[bytes, str, Path],
    page_number: int = 0,
    zoom: float = 2.0,
    jpeg_quality: int = 90,
) -> bytes:
    """
    Render a single page of a PDF as JPEG bytes.

    Args:
        pdf_source:    Raw PDF bytes, or a file path (str / Path).
        page_number:   Zero-indexed page to render. Defaults to 0 (first page).
        zoom:          Rendering zoom factor. 2.0 = 2× resolution.
        jpeg_quality:  JPEG compression quality (1–100).

    Returns:
        Raw JPEG bytes of the rendered page.

    Raises:
        ValueError:  If the PDF has no pages or page_number is out of range.
        FileNotFoundError: If pdf_source is a path that doesn't exist.
    """
    doc = _open_document(pdf_source)

    try:
        if doc.page_count == 0:
            raise ValueError("PDF has no pages.")

        if page_number < 0 or page_number >= doc.page_count:
            raise ValueError(
                f"page_number {page_number} out of range "
                f"(document has {doc.page_count} page(s))."
            )

        page = doc.load_page(page_number)
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        jpeg_bytes: bytes = pix.tobytes(output="jpeg", jpg_quality=jpeg_quality)
    finally:
        doc.close()

    return jpeg_bytes


def pdf_to_base64(
    pdf_source: Union[bytes, str, Path],
    page_number: int = 0,
    zoom: float = 2.0,
    jpeg_quality: int = 90,
) -> tuple[str, bytes]:
    """
    Render a PDF page as JPEG and return (base64_string, raw_jpeg_bytes).

    This is the primary convenience function for downstream VLM APIs
    that expect base64-encoded images.

    Args:
        pdf_source:    Raw PDF bytes, or a file path (str / Path).
        page_number:   Zero-indexed page to render.
        zoom:          Rendering zoom factor.
        jpeg_quality:  JPEG compression quality (1–100).

    Returns:
        Tuple of (base64_encoded_string, raw_jpeg_bytes).
    """
    jpeg_bytes = pdf_to_jpeg_bytes(
        pdf_source,
        page_number=page_number,
        zoom=zoom,
        jpeg_quality=jpeg_quality,
    )
    b64_string = base64.b64encode(jpeg_bytes).decode("utf-8")
    return b64_string, jpeg_bytes


def pdf_to_base64_from_path(
    file_path: Union[str, Path],
    page_number: int = 0,
    zoom: float = 2.0,
    jpeg_quality: int = 90,
) -> tuple[str, bytes]:
    """
    Convenience wrapper — reads a PDF file from disk and returns
    (base64_string, raw_jpeg_bytes).
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF file not found: {path}")
    return pdf_to_base64(path, page_number=page_number, zoom=zoom, jpeg_quality=jpeg_quality)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _open_document(pdf_source: Union[bytes, str, Path]) -> fitz.Document:
    """Open a PyMuPDF Document from bytes or a file path."""
    if isinstance(pdf_source, bytes):
        return fitz.open(stream=pdf_source, filetype="pdf")
    path = Path(pdf_source)
    if not path.exists():
        raise FileNotFoundError(f"PDF file not found: {path}")
    return fitz.open(str(path))
