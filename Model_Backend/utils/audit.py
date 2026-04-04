"""
audit.py — Generic, pipeline-agnostic audit trail logger.

This module has ZERO dependencies on any project-specific code.
It can be used with any pipeline, any framework, any project.

Usage:
    audit = AuditTrail()
    audit.log_step(service="my_step", status="success", output_data={"key": "val"})
    audit.finalize("success")   # saves JSON to audit_logs/
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


# Default directory for saving audit JSON files.
# Can be overridden via AUDIT_LOG_DIR environment variable.
AUDIT_LOG_DIR = Path(
    os.environ.get("AUDIT_LOG_DIR", Path(__file__).resolve().parent.parent / "audit_logs")
)


class AuditTrail:
    """
    A generic, pipeline-agnostic audit trail collector.

    Create one per request. Call log_step() after each processing step.
    Call finalize() at the end to save the audit JSON.

    This class knows NOTHING about your project. It accepts any
    service name, any input/output data. If your pipeline changes,
    this class stays the same.
    """

    def __init__(self, request_id: Optional[str] = None):
        """
        Initialize a new audit trail.

        Args:
            request_id: Optional custom request ID. If not provided,
                        a new UUID is generated.
        """
        self.request_id: str = request_id or str(uuid.uuid4())
        self.timestamp: str = datetime.now(timezone.utc).isoformat()
        self.steps: list[dict[str, Any]] = []
        self.final_status: str = "pending"

    def log_step(
        self,
        service: str,
        status: str,
        input_data: Any = None,
        output_data: Any = None,
        error: Optional[str] = None,
        latency: Optional[float] = None,
        model_version: Optional[str] = None,
    ) -> None:
        """
        Log a single processing step into the audit trail.

        The function that performed the work should call this AFTER
        it finishes, passing in whatever data it wants to record.

        Args:
            service:        Name of the function/model/step (any string).
            status:         "success" or "failed".
            input_data:     Summary of input (keep small — no raw images).
            output_data:    Summary of output (keep small).
            error:          Error message string, if the step failed.
            latency:        Execution time in seconds, if measured.
            model_version:  Version identifier for the model used, if any.
        """
        step = {
            "service": service,
            "status": status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Only include optional fields if they have values.
        # This keeps the JSON clean — no null spam.
        if input_data is not None:
            step["input"] = input_data
        if output_data is not None:
            step["output"] = output_data
        if error is not None:
            step["error"] = error
        if latency is not None:
            step["latency"] = round(latency, 4)
        if model_version is not None:
            step["model_version"] = model_version

        self.steps.append(step)

    def finalize(self, status: str = "success", save: bool = True) -> dict[str, Any]:
        """
        Mark the audit as complete and optionally save to disk.

        Args:
            status: Final status — "success" or "failed".
            save:   Whether to save the JSON file to audit_logs/.

        Returns:
            The complete audit trail as a dictionary.
        """
        self.final_status = status

        audit_dict = self.to_dict()

        if save:
            self._save_to_file(audit_dict)

        return audit_dict

    def to_dict(self) -> dict[str, Any]:
        """Return the full audit trail as a plain Python dictionary."""
        return {
            "request_id": self.request_id,
            "timestamp": self.timestamp,
            "steps": self.steps,
            "final_status": self.final_status,
        }

    def _save_to_file(self, audit_dict: dict[str, Any]) -> Path:
        """
        Save the audit JSON to the audit_logs/ directory.

        Creates the directory if it doesn't exist.
        Filename: {request_id}.json

        Returns:
            Path to the saved file.
        """
        AUDIT_LOG_DIR.mkdir(parents=True, exist_ok=True)

        filepath = AUDIT_LOG_DIR / f"{self.request_id}.json"
        filepath.write_text(
            json.dumps(audit_dict, indent=2, default=str, ensure_ascii=False),
            encoding="utf-8",
        )

        return filepath
