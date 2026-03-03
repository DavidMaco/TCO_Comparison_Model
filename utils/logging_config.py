"""
TCO Comparison Model — Logging Configuration
"""
import logging
import os
import json
from datetime import datetime, timezone


LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
os.makedirs(LOG_DIR, exist_ok=True)


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Return a configured logger with console + file output."""
    logger = logging.getLogger(f"tco.{name}")
    if logger.handlers:
        return logger
    logger.setLevel(level)
    fmt = logging.Formatter("[%(asctime)s] %(levelname)-8s %(name)s — %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    fh = logging.FileHandler(os.path.join(LOG_DIR, "tco_pipeline.log"), encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    return logger


class AuditLogger:
    """Immutable audit trail logger — every decision/output is traceable."""

    def __init__(self):
        self.log_path = os.path.join(LOG_DIR, "audit_trail.jsonl")
        self._logger = get_logger("audit")

    def record(self, event_type: str, details: dict, run_id: str = "", evidence_class: str = "simulated_estimate"):
        """Append an immutable audit record."""
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "run_id": run_id,
            "event_type": event_type,
            "evidence_class": evidence_class,
            "details": details,
        }
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\n")
        self._logger.info("[AUDIT] %s: %s (evidence=%s)", event_type, event_type, evidence_class)
        return record


class DataQualityLogger:
    """Track data quality metrics during pipeline execution."""

    def __init__(self):
        self._logger = get_logger("data_quality")
        self.checks: list[dict] = []

    def check(self, name: str, passed: bool, details: str = ""):
        entry = {"check": name, "passed": passed, "details": details, "ts": datetime.now(timezone.utc).isoformat()}
        self.checks.append(entry)
        level = "INFO" if passed else "WARNING"
        self._logger.log(getattr(logging, level), "[DQ] %s: %s %s", name, "PASS" if passed else "FAIL", details)

    def summary(self) -> dict:
        total = len(self.checks)
        passed = sum(1 for c in self.checks if c["passed"])
        return {"total": total, "passed": passed, "failed": total - passed, "pass_rate": passed / total if total else 0}
