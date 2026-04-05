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
    date_filter: Optional[str] = None,
    limit: Optional[int] = None,
) -> list[dict[str, Any]]:
    """
    Query audit records from Supabase.

    Args:
        status:     Filter by status ("success" or "failed").
        user_id:    Filter by user.
        request_id: Filter by specific request ID.
        date_filter: Filter by exact date (YYYY-MM-DD).
        limit:      Max records to return.

    Returns:
        List of audit metadata records.
    """
    base_url = _get_base_url()
    headers = _get_headers()

    url = f"{base_url}/rest/v1/{TABLE_NAME}?order=created_at.desc"
    
    if limit is not None:
        url += f"&limit={limit}"

    if status:
        url += f"&status=eq.{status}"
    if user_id:
        url += f"&user_id=eq.{user_id}"
    if request_id:
        url += f"&request_id=eq.{request_id}"
    if date_filter:
        url += f"&created_at=gte.{date_filter}T00:00:00Z&created_at=lte.{date_filter}T23:59:59Z"

    response = requests.get(url, headers=headers, timeout=15)
    response.raise_for_status()

    return response.json()


# ── Transaction Functions ────────────────────────────────────────────────

TRANSACTIONS_TABLE = "transactions"


def store_transaction(
    transaction_id: str,
    request_id: Optional[str] = None,
    container_id: Optional[str] = None,
    risk_score: Optional[int] = None,
    risk_level: Optional[str] = None,
    metadata: Optional[dict] = None,
    status: str = "completed",
) -> dict[str, Any]:
    """
    Store a transaction in Supabase.

    Args:
        transaction_id: Unique transaction ID (e.g., TXN-XXX-XXX)
        request_id: Audit request ID for linking to audit logs
        container_id: Optional container identifier
        risk_score: Risk score (0-100)
        risk_level: Risk level (CLEAR, SUSPICIOUS, PROHIBITED)
        metadata: Additional JSON metadata
        status: Transaction status

    Returns:
        The inserted row as a dictionary.
    """
    base_url = _get_base_url()
    headers = _get_headers()

    # Build payload with only non-null values for required fields
    payload = {
        "transaction_id": transaction_id,
        "status": status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    
    # Only add optional fields if they have values
    if request_id:
        payload["request_id"] = request_id
    if container_id:
        payload["container_id"] = container_id
    if risk_score is not None:
        payload["risk_score"] = risk_score
    if risk_level:
        payload["risk_level"] = risk_level
    if metadata:
        payload["metadata"] = metadata

    url = f"{base_url}/rest/v1/{TRANSACTIONS_TABLE}"

    logger.info("Storing transaction in Supabase (transaction_id=%s)...", transaction_id)
    logger.debug("Payload: %s", payload)

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        response.raise_for_status()
        
        result = response.json()
        logger.info("✓ Transaction stored in Supabase: transaction_id=%s", transaction_id)
        return result[0] if isinstance(result, list) and result else result
    except requests.exceptions.HTTPError as e:
        error_detail = ""
        try:
            error_detail = response.text
        except:
            pass
        logger.error("Supabase HTTP error: %s - %s", e, error_detail)
        raise


def get_transaction(transaction_id: str) -> Optional[dict[str, Any]]:
    """
    Get a single transaction by ID.

    Args:
        transaction_id: The transaction ID to look up

    Returns:
        Transaction data or None if not found
    """
    base_url = _get_base_url()
    headers = _get_headers()

    url = f"{base_url}/rest/v1/{TRANSACTIONS_TABLE}?transaction_id=eq.{transaction_id}&limit=1"

    logger.info("Fetching transaction from Supabase (transaction_id=%s)...", transaction_id)

    response = requests.get(url, headers=headers, timeout=15)
    response.raise_for_status()

    result = response.json()
    if result and len(result) > 0:
        logger.info("✓ Transaction found in Supabase: transaction_id=%s", transaction_id)
        return result[0]
    
    logger.warning("Transaction not found in Supabase: transaction_id=%s", transaction_id)
    return None


def query_transactions(
    request_id: Optional[str] = None,
    container_id: Optional[str] = None,
    risk_level: Optional[str] = None,
    status: Optional[str] = None,
    date_filter: Optional[str] = None,
    limit: Optional[int] = None,
) -> list[dict[str, Any]]:
    """
    Query transactions from Supabase.

    Args:
        request_id: Filter by audit request ID
        container_id: Filter by container ID
        risk_level: Filter by risk level
        status: Filter by status
        date_filter: Filter by date (YYYY-MM-DD)
        limit: Max records to return

    Returns:
        List of transaction records
    """
    base_url = _get_base_url()
    headers = _get_headers()

    url = f"{base_url}/rest/v1/{TRANSACTIONS_TABLE}?order=created_at.desc"

    if limit is not None:
        url += f"&limit={limit}"

    if request_id:
        url += f"&request_id=eq.{request_id}"
    if container_id:
        url += f"&container_id=eq.{container_id}"
    if risk_level:
        url += f"&risk_level=eq.{risk_level}"
    if status:
        url += f"&status=eq.{status}"
    if date_filter:
        url += f"&created_at=gte.{date_filter}T00:00:00Z&created_at=lte.{date_filter}T23:59:59Z"

    logger.info("Querying transactions from Supabase...")

    response = requests.get(url, headers=headers, timeout=15)
    response.raise_for_status()

    result = response.json()
    logger.info("✓ Found %d transactions in Supabase", len(result))
    return result
