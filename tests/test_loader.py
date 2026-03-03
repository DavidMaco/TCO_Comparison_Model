"""Tests for Data Ingestion / Loader."""
import pytest
import os
import tempfile
import json
import pandas as pd
from data_ingestion.loader import (
    load_equipment_csv, load_supplier_csv, load_assumptions_json,
    DataValidationError,
)


class TestLoader:

    def test_load_equipment_csv(self, tmp_path):
        csv_path = tmp_path / "equipment.csv"
        df = pd.DataFrame([{
            "equipment_id": "E1", "name": "Test", "category": "CNC Machine",
            "region": "China", "supplier_id": "S1", "supplier_name": "Test Co",
            "base_price_local": 100000, "currency": "CNY",
        }])
        df.to_csv(csv_path, index=False)
        result = load_equipment_csv(str(csv_path))
        assert len(result) == 1
        assert result[0].equipment_id == "E1"

    def test_load_supplier_csv(self, tmp_path):
        csv_path = tmp_path / "suppliers.csv"
        df = pd.DataFrame([{
            "supplier_id": "S1", "supplier_name": "Test",
            "region": "China", "quality_index": 80,
            "delivery_reliability": 85, "service_responsiveness": 7,
            "warranty_performance": 70, "price_competitiveness": 0.8,
            "local_support": 6,
        }])
        df.to_csv(csv_path, index=False)
        result = load_supplier_csv(str(csv_path))
        assert len(result) == 1

    def test_load_assumptions_json(self, tmp_path):
        json_path = tmp_path / "assumptions.json"
        data = {"discount_rate": 0.10, "asset_life_years": 10, "regions": ["China", "India"]}
        with open(json_path, "w") as f:
            json.dump(data, f)
        result = load_assumptions_json(str(json_path))
        assert result["discount_rate"] == 0.10

    def test_missing_file_raises(self):
        with pytest.raises(DataValidationError):
            load_equipment_csv("/nonexistent/path.csv")

    def test_invalid_region_in_csv(self, tmp_path):
        csv_path = tmp_path / "bad_equipment.csv"
        df = pd.DataFrame([{
            "equipment_id": "E1", "name": "Test", "category": "CNC Machine",
            "region": "Mars", "supplier_id": "S1", "supplier_name": "Test Co",
            "base_price_local": 100000, "currency": "CNY",
        }])
        df.to_csv(csv_path, index=False)
        with pytest.raises(DataValidationError):
            load_equipment_csv(str(csv_path))
