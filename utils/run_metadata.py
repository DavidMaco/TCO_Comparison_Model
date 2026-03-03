"""
TCO Comparison Model — Run Metadata & Fingerprinting
Every analytics run is assigned a unique fingerprint for full traceability.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any


def generate_run_id() -> str:
    """Create a unique run identifier."""
    return f"tco-run-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}"


def fingerprint_inputs(inputs: dict[str, Any]) -> str:
    """SHA-256 fingerprint of the input assumptions for reproducibility."""
    canonical = json.dumps(inputs, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]


class RunMetadata:
    """Captures full metadata for an analytics run."""

    def __init__(self, run_id: str | None = None, scenario: str = "base"):
        self.run_id = run_id or generate_run_id()
        self.scenario = scenario
        self.started_at = datetime.now(timezone.utc)
        self.finished_at: datetime | None = None
        self.input_fingerprint: str = ""
        self.evidence_class: str = "simulated_estimate"
        self.model_version: str = "0.1.0"
        self.assumptions_version: str = ""
        self.warnings: list[str] = []

    def seal(self, inputs: dict) -> dict:
        """Finalize the run and produce metadata summary."""
        self.finished_at = datetime.now(timezone.utc)
        self.input_fingerprint = fingerprint_inputs(inputs)
        return {
            "run_id": self.run_id,
            "scenario": self.scenario,
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat(),
            "duration_seconds": (self.finished_at - self.started_at).total_seconds(),
            "input_fingerprint": self.input_fingerprint,
            "evidence_class": self.evidence_class,
            "model_version": self.model_version,
            "assumptions_version": self.assumptions_version,
            "warnings": self.warnings,
        }
