"""Shared test fixtures for TCO Comparison Model."""
import os

os.environ.setdefault("TCO_DEV_MODE", "true")

import pytest

from analytics.tco_engine import EquipmentSpec
from utils.run_metadata import RunMetadata


@pytest.fixture
def run_meta():
    """Standard run metadata for tests."""
    return RunMetadata(scenario="unit_test")


@pytest.fixture
def china_spec():
    return EquipmentSpec(
        equipment_id="TEST-CN-01", name="Test China CNC", category="CNC Machine",
        region="China", supplier_id="SUP-CN-01", supplier_name="Test Shenyang",
        base_price_local=580000, currency="CNY",
        site_prep_cost=3000, installation_labor_hours=80, certification_cost=2000,
        energy_kwh_per_year=50000, operator_hours_per_year=2000,
        consumables_per_year=5000, monitoring_cost_per_year=2000,
        preventive_maintenance_events_per_year=4, corrective_maintenance_events_per_year=2,
        maintenance_labor_hours_per_event=12, spares_cost_per_event=800,
        mtbf_hours=6000, mttr_hours=18, warranty_years=2, warranty_coverage_pct=0.80,
        spare_unit_price_local=4500, spares_per_year=6, logistics_mode="Sea",
        logistics_distance_km=8000, spare_weight_kg=30, customs_clearance_cost=400,
        rated_throughput_per_hour=100, actual_throughput_per_hour=92, yield_rate=0.96,
        scrap_cost_per_unit=0.45, asset_life_years=10,
    )


@pytest.fixture
def india_spec():
    return EquipmentSpec(
        equipment_id="TEST-IN-01", name="Test India CNC", category="CNC Machine",
        region="India", supplier_id="SUP-IN-01", supplier_name="Test HMT",
        base_price_local=6500000, currency="INR",
        site_prep_cost=2500, installation_labor_hours=90, certification_cost=1800,
        energy_kwh_per_year=50000, operator_hours_per_year=2000,
        consumables_per_year=5000, monitoring_cost_per_year=2000,
        preventive_maintenance_events_per_year=4, corrective_maintenance_events_per_year=2,
        maintenance_labor_hours_per_event=12, spares_cost_per_event=800,
        mtbf_hours=6000, mttr_hours=18, warranty_years=2, warranty_coverage_pct=0.80,
        spare_unit_price_local=45000, spares_per_year=6, logistics_mode="Sea",
        logistics_distance_km=6000, spare_weight_kg=30, customs_clearance_cost=400,
        rated_throughput_per_hour=100, actual_throughput_per_hour=92, yield_rate=0.96,
        scrap_cost_per_unit=0.45, asset_life_years=10,
    )


@pytest.fixture
def europe_spec():
    return EquipmentSpec(
        equipment_id="TEST-EU-01", name="Test Europe CNC", category="CNC Machine",
        region="Europe", supplier_id="SUP-EU-01", supplier_name="Test DMG Mori",
        base_price_local=92000, currency="EUR",
        site_prep_cost=5000, installation_labor_hours=40, certification_cost=3500,
        energy_kwh_per_year=50000, operator_hours_per_year=2000,
        consumables_per_year=5000, monitoring_cost_per_year=2000,
        preventive_maintenance_events_per_year=4, corrective_maintenance_events_per_year=2,
        maintenance_labor_hours_per_event=12, spares_cost_per_event=800,
        mtbf_hours=6000, mttr_hours=18, warranty_years=2, warranty_coverage_pct=0.80,
        spare_unit_price_local=1200, spares_per_year=6, logistics_mode="Road",
        logistics_distance_km=2000, spare_weight_kg=30, customs_clearance_cost=400,
        rated_throughput_per_hour=100, actual_throughput_per_hour=92, yield_rate=0.96,
        scrap_cost_per_unit=0.45, asset_life_years=10,
    )


@pytest.fixture
def all_specs(china_spec, india_spec, europe_spec):
    return [china_spec, india_spec, europe_spec]


@pytest.fixture
def demo_suppliers():
    return [
        {"supplier_id": "SUP-CN-01", "supplier_name": "Shenyang", "region": "China",
         "quality_index": 72, "delivery_reliability": 78, "service_responsiveness": 6,
         "warranty_performance": 65, "price_competitiveness": 0.7, "local_support": 5},
        {"supplier_id": "SUP-IN-01", "supplier_name": "HMT", "region": "India",
         "quality_index": 70, "delivery_reliability": 72, "service_responsiveness": 5.5,
         "warranty_performance": 60, "price_competitiveness": 0.65, "local_support": 6},
        {"supplier_id": "SUP-EU-01", "supplier_name": "DMG Mori", "region": "Europe",
         "quality_index": 95, "delivery_reliability": 96, "service_responsiveness": 9,
         "warranty_performance": 92, "price_competitiveness": 1.5, "local_support": 9},
    ]
