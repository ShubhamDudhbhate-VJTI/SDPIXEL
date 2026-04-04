"""
ipfs_client.py — Upload and retrieve audit JSON from IPFS via Pinata.

This module has ZERO dependencies on any project-specific code.
It only knows how to upload JSON to IPFS and fetch it back using a CID.

Usage:
    from utils.ipfs_client import upload_to_ipfs, fetch_from_ipfs

    cid = upload_to_ipfs({"request_id": "abc", "steps": [...]})
    data = fetch_from_ipfs(cid)
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Optional

import requests

logger = logging.getLogger(__name__)

# ── Configuration ────────────────────────────────────────────────────────

# Pinata API endpoints
PINATA_PIN_JSON_URL = "https://api.pinata.cloud/pinning/pinJSONToIPFS"
PINATA_GATEWAY_URL = os.environ.get(
    "PINATA_GATEWAY_URL", "https://gateway.pinata.cloud/ipfs"
)

# JWT token from environment
PINATA_JWT = os.environ.get("PINATA_JWT", "")


def _get_jwt() -> str:
    """Get the Pinata JWT, raising an error if not configured."""
    jwt = PINATA_JWT or os.environ.get("PINATA_JWT", "")
    if not jwt or jwt == "your_pinata_jwt_token_here":
        raise ValueError(
            "PINATA_JWT is not configured. "
            "Set it in your .env file or environment variables. "
            "Get your JWT from https://app.pinata.cloud/developers/api-keys"
        )
    return jwt


def upload_to_ipfs(
    audit_dict: dict[str, Any],
    name: Optional[str] = None,
) -> str:
    """
    Upload an audit JSON dictionary to IPFS via Pinata.

    Args:
        audit_dict: The audit trail dictionary to upload.
        name: Optional name for the pin (defaults to request_id).

    Returns:
        The IPFS CID (Content Identifier) string.

    Raises:
        ValueError: If PINATA_JWT is not configured.
        requests.HTTPError: If the Pinata API request fails.
    """
    jwt = _get_jwt()

    # Build the Pinata request payload
    pin_name = name or audit_dict.get("request_id", "audit")
    payload = {
        "pinataContent": audit_dict,
        "pinataMetadata": {
            "name": f"audit_{pin_name}",
        },
    }

    headers = {
        "Authorization": f"Bearer {jwt}",
        "Content-Type": "application/json",
    }

    logger.info("Uploading audit to IPFS via Pinata (request_id=%s)...", pin_name)

    response = requests.post(
        PINATA_PIN_JSON_URL,
        json=payload,
        headers=headers,
        timeout=30,
    )
    response.raise_for_status()

    result = response.json()
    cid = result.get("IpfsHash", "")

    if not cid:
        raise RuntimeError(f"Pinata returned no CID. Response: {result}")

    logger.info("✓ Audit uploaded to IPFS: CID=%s", cid)
    return cid


def fetch_from_ipfs(cid: str) -> dict[str, Any]:
    """
    Fetch an audit JSON from IPFS using its CID.

    Args:
        cid: The IPFS Content Identifier.

    Returns:
        The audit trail dictionary retrieved from IPFS.

    Raises:
        requests.HTTPError: If the fetch request fails.
    """
    url = f"{PINATA_GATEWAY_URL}/{cid}"
    logger.info("Fetching audit from IPFS: CID=%s", cid)

    response = requests.get(url, timeout=30)
    response.raise_for_status()

    data = response.json()
    logger.info("✓ Audit fetched from IPFS: CID=%s", cid)
    return data
