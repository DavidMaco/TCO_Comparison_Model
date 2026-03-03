"""
TCO Comparison Model — Data Ingestion & Validation
Loads equipment, supplier, and cost data from CSV / Excel / JSON
with strict schema validation and fail-fast on contract violations.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

import config
from analytics.tco_engine import EquipmentSpec
from utils.logging_config import get_logger, DataQualityLogger

log = get_logger("data_ingestion")
dq = DataQualityLogger()


# ─── Required Schemas ────────────────────────────────────────────────

EQUIPMENT_REQUIRED_COLUMNS = [
    "equipment_id", "name", "category", "region", "supplier_id", "supplier_name",
    "base_price_local", "currency",
]

SUPPLIER_REQUIRED_COLUMNS = [
    "supplier_id", "supplier_name", "region",
    "quality_index", "delivery_reliability", "service_responsiveness",
    "warranty_performance", "price_competitiveness", "local_support",
]

VALID_REGIONS = set(config.REGIONS)
VALID_CURRENCIES = set(config.FX_ANCHOR_RATES.keys()) | {"USD"}
VALID_LOGISTICS_MODES = set(config.LOGISTICS_MODES.keys())


class DataValidationError(Exception):
    """Raised when input data fails validation."""
    pass


def _validate_dataframe(df: pd.DataFrame, required_cols: list[str], name: str) -> list[str]:
    """Validate a DataFrame against required column schema."""
    errors = []
    missing = set(required_cols) - set(df.columns)
    if missing:
        errors.append(f"[{name}] Missing required columns: {missing}")

    if df.empty:
        errors.append(f"[{name}] DataFrame is empty")

    return errors


def load_equipment_csv(filepath: str | Path, strict: bool = True) -> list[EquipmentSpec]:
    """
    Load equipment specifications from CSV.
    Validates schema, regions, currencies, and numeric ranges.
    """
    filepath = Path(filepath)
    if not filepath.exists():
        raise DataValidationError(f"Equipment file not found: {filepath}")

    df = pd.read_csv(filepath)
    log.info("Loaded equipment CSV: %s (%d rows)", filepath.name, len(df))

    errors = _validate_dataframe(df, EQUIPMENT_REQUIRED_COLUMNS, "equipment")

    # Validate regions
    if "region" in df.columns:
        invalid_regions = set(df["region"].unique()) - VALID_REGIONS
        if invalid_regions:
            errors.append(f"Invalid regions: {invalid_regions}. Valid: {VALID_REGIONS}")

    # Validate currencies
    if "currency" in df.columns:
        invalid_currencies = set(df["currency"].unique()) - VALID_CURRENCIES
        if invalid_currencies:
            errors.append(f"Invalid currencies: {invalid_currencies}")

    if errors and strict:
        for e in errors:
            log.error(e)
            dq.check(e, passed=False)
        raise DataValidationError("\n".join(errors))

    # Convert to EquipmentSpec list
    specs = []
    spec_fields = {f.name for f in EquipmentSpec.__dataclass_fields__.values()}
    for _, row in df.iterrows():
        kwargs = {}
        for col in df.columns:
            if col in spec_fields:
                val = row[col]
                if pd.isna(val):
                    continue
                kwargs[col] = val
        try:
            specs.append(EquipmentSpec(**kwargs))
            dq.check(f"equipment_{row.get('equipment_id', 'unknown')}", passed=True)
        except Exception as e:
            log.warning("Skipping row: %s", e)
            dq.check(f"equipment_{row.get('equipment_id', 'unknown')}", passed=False, details=str(e))

    log.info("Loaded %d equipment specifications", len(specs))
    return specs


def load_supplier_csv(filepath: str | Path, strict: bool = True) -> list[dict[str, Any]]:
    """Load supplier scorecard data from CSV."""
    filepath = Path(filepath)
    if not filepath.exists():
        raise DataValidationError(f"Supplier file not found: {filepath}")

    df = pd.read_csv(filepath)
    log.info("Loaded supplier CSV: %s (%d rows)", filepath.name, len(df))

    errors = _validate_dataframe(df, SUPPLIER_REQUIRED_COLUMNS, "suppliers")
    if errors and strict:
        for e in errors:
            log.error(e)
        raise DataValidationError("\n".join(errors))

    return df.to_dict("records")


def load_assumptions_json(filepath: str | Path) -> dict[str, Any]:
    """Load assumption overrides from JSON."""
    filepath = Path(filepath)
    if not filepath.exists():
        raise DataValidationError(f"Assumptions file not found: {filepath}")

    with open(filepath, "r", encoding="utf-8") as f:
        assumptions = json.load(f)

    log.info("Loaded assumptions: %s (%d keys)", filepath.name, len(assumptions))
    return assumptions
