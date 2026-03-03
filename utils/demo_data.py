"""
TCO Comparison Model — Shared Demo Data
Centralized demo equipment specs and supplier data used across dashboard pages.
"""
from __future__ import annotations

from analytics.tco_engine import EquipmentSpec


# ─── Common Parameters ───────────────────────────────────────────────
COMMON_SPEC_PARAMS = dict(
    category="CNC Machine",
    energy_kwh_per_year=50000,
    operator_hours_per_year=2000,
    consumables_per_year=5000,
    monitoring_cost_per_year=2000,
    preventive_maintenance_events_per_year=4,
    corrective_maintenance_events_per_year=2,
    maintenance_labor_hours_per_event=12,
    spares_cost_per_event=800,
    mtbf_hours=6000,
    mttr_hours=18,
    warranty_years=2,
    warranty_coverage_pct=0.80,
    spares_per_year=6,
    spare_weight_kg=30,
    customs_clearance_cost=400,
    rated_throughput_per_hour=100,
    actual_throughput_per_hour=92,
    yield_rate=0.96,
    scrap_cost_per_unit=0.45,
    asset_life_years=10,
    site_prep_cost=3000,
    installation_labor_hours=60,
    certification_cost=2500,
    spare_unit_price_local=500,
    logistics_distance_km=5000,
    logistics_mode="Sea",
)


def get_demo_specs(
    *,
    asset_life: int = 10,
    base_price_cn: float = 580000,
    base_price_in: float = 6500000,
    base_price_eu: float = 92000,
) -> list[EquipmentSpec]:
    """Return three demo EquipmentSpec instances (China, India, Europe).

    Parameters allow dashboard sliders to override defaults.
    """
    common = {**COMMON_SPEC_PARAMS, "asset_life_years": asset_life}
    return [
        EquipmentSpec(
            equipment_id="CNC-CN-01",
            name="CNC Machine (China)",
            region="China",
            supplier_id="SUP-CN-01",
            supplier_name="Shenyang Machine Tool",
            base_price_local=base_price_cn,
            currency="CNY",
            **common,
        ),
        EquipmentSpec(
            equipment_id="CNC-IN-01",
            name="CNC Machine (India)",
            region="India",
            supplier_id="SUP-IN-01",
            supplier_name="HMT Machine Tools",
            base_price_local=base_price_in,
            currency="INR",
            **common,
        ),
        EquipmentSpec(
            equipment_id="CNC-EU-01",
            name="CNC Machine (Europe)",
            region="Europe",
            supplier_id="SUP-EU-01",
            supplier_name="DMG Mori",
            base_price_local=base_price_eu,
            currency="EUR",
            **common,
        ),
    ]


DEMO_SUPPLIERS = [
    {
        "supplier_id": "SUP-CN-01", "supplier_name": "Shenyang Machine Tool",
        "region": "China", "quality_index": 72, "delivery_reliability": 78,
        "service_responsiveness": 6, "warranty_performance": 65,
        "price_competitiveness": 0.7, "local_support": 5,
    },
    {
        "supplier_id": "SUP-CN-02", "supplier_name": "Dalian Machine Tool",
        "region": "China", "quality_index": 75, "delivery_reliability": 80,
        "service_responsiveness": 6.5, "warranty_performance": 68,
        "price_competitiveness": 0.75, "local_support": 5.5,
    },
    {
        "supplier_id": "SUP-IN-01", "supplier_name": "HMT Machine Tools",
        "region": "India", "quality_index": 70, "delivery_reliability": 72,
        "service_responsiveness": 5.5, "warranty_performance": 60,
        "price_competitiveness": 0.65, "local_support": 6,
    },
    {
        "supplier_id": "SUP-IN-02", "supplier_name": "BFW",
        "region": "India", "quality_index": 74, "delivery_reliability": 76,
        "service_responsiveness": 6, "warranty_performance": 64,
        "price_competitiveness": 0.68, "local_support": 6.5,
    },
    {
        "supplier_id": "SUP-EU-01", "supplier_name": "DMG Mori",
        "region": "Europe", "quality_index": 95, "delivery_reliability": 96,
        "service_responsiveness": 9, "warranty_performance": 92,
        "price_competitiveness": 1.5, "local_support": 9,
    },
    {
        "supplier_id": "SUP-EU-02", "supplier_name": "Trumpf",
        "region": "Europe", "quality_index": 93, "delivery_reliability": 94,
        "service_responsiveness": 8.5, "warranty_performance": 90,
        "price_competitiveness": 1.45, "local_support": 8.5,
    },
]
