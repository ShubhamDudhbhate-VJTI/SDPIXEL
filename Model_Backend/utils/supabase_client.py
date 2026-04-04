"""
supabase_client.py — Store and query audit metadata in Supabase.

This module has ZERO dependencies on any project-specific code.
It only knows how to store CID + metadata and query audit records.

Requires table 'audit_logs' in Supabase with columns:
  id (uuid PK), cid (text), request_id (text), user_id (text),
  status (text), description (text), created_at (timestamptz)

Usage:
    from utils.supabase_client import store_audit_metadata, query_audits

    store_audit_metadata(cid="QmXyz...", request_id="abc", status="success")
    results = query_audits(status="failed")
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Optional

import requests

logger = logging.getLogger(__name__)

# ── Configuration ────────────────────────────────────────────────────────

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
TABLE_NAME = "audit_logs"


def _get_headers() -> dict[str, str]:
    """Build Supabase REST API headers."""
    key = SUPABASE_KEY or os.environ.get("SUPABASE_KEY", "")
    if not key or key.startswith("paste_"):
        raise ValueError(
            "SUPABASE_KEY is not configured. "
            "Set it in your .env file or environment variables."
        )
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


def _get_base_url() -> str:
    """Get the Supabase REST API base URL."""
    url = SUPABASE_URL or os.environ.get("SUPABASE_URL", "")
    if not url or url.startswith("paste_"):
        raise ValueError(
            "SUPABASE_URL is not configured. "
            "Set it in your .env file or environment variables."
        )
    return url.rstrip("/")


def store_audit_metadata(
    cid: str,
    request_id: str,
    status: str = "success",
    user_id: str = "default_user",
    description: str = "",
) -> dict[str, Any]:
    """
    Store audit metadata (CID + context) in Supabase.

    Args:
        cid:         IPFS CID of the full audit JSON.
        request_id:  Audit request ID.
        status:      "success" or "failed".
        user_id:     User identifier.
        description: Flexible field for context (model used, notes, etc.)

    Returns:
        The inserted row as a dictionary.
    """
    base_url = _get_base_url()
    headers = _get_headers()

    payload = {
        "cid": cid,
        "request_id": request_id,
        "user_id": user_id,
        "status": status,
        "description": description,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    url = f"{base_url}/rest/v1/{TABLE_NAME}"

    logger.info("Storing audit metadata in Supabase (request_id=%s)...", request_id)

    response = requests.post(url, json=payload, headers=headers, timeout=15)
    response.raise_for_status()

    result = response.json()
    logger.info("✓ Audit metadata stored in Supabase: request_id=%s, cid=%s", request_id, cid)
    return result[0] if isinstance(result, list) and result else result


def query_audits(
    status: Optional[str] = None,
    user_id: Optional[str] = None,
    request_id: Optional[str] = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """
    Query audit records from Supabase.

    Args:
        status:     Filter by status ("success" or "failed").
        user_id:    Filter by user.
        request_id: Filter by specific request ID.
        limit:      Max records to return.

    Returns:
        List of audit metadata records.
    """
    base_url = _get_base_url()
    headers = _get_headers()

    url = f"{base_url}/rest/v1/{TABLE_NAME}?order=created_at.desc&limit={limit}"

    if status:
        url += f"&status=eq.{status}"
    if user_id:
        url += f"&user_id=eq.{user_id}"
    if request_id:
        url += f"&request_id=eq.{request_id}"

    response = requests.get(url, headers=headers, timeout=15)
    response.raise_for_status()

    return response.json()
