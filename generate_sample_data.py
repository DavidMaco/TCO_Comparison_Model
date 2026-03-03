"""
TCO Comparison Model — Sample Data Generator
Generates realistic synthetic equipment, supplier, and cost data
for all 3 regions (China, India, Europe) across multiple categories.
"""
import os
os.environ.setdefault("TCO_DEV_MODE", "true")

import csv
import json
import random
from pathlib import Path

import config

OUTPUT_DIR = Path(__file__).parent / "sample_data"

CATEGORIES = [
    ("CNC Machine", 6000, 18),
    ("Compressor", 8000, 12),
    ("Pump", 10000, 8),
    ("Conveyor System", 12000, 6),
    ("Packaging Machine", 5000, 16),
    ("Injection Molder", 7000, 20),
]

SUPPLIERS = {
    "China": [
        ("SUP-CN-01", "Shenyang Machine Tool"),
        ("SUP-CN-02", "Dalian Machine Tool"),
        ("SUP-CN-03", "Jinan Foundry Group"),
    ],
    "India": [
        ("SUP-IN-01", "HMT Machine Tools"),
        ("SUP-IN-02", "BFW"),
        ("SUP-IN-03", "Ace Micromatic"),
    ],
    "Europe": [
        ("SUP-EU-01", "DMG Mori"),
        ("SUP-EU-02", "Trumpf"),
        ("SUP-EU-03", "Siemens AG"),
    ],
}

# Base price ranges by category (in USD equivalent)
BASE_PRICES_USD = {
    "CNC Machine": (60000, 120000),
    "Compressor": (25000, 80000),
    "Pump": (8000, 45000),
    "Conveyor System": (30000, 100000),
    "Packaging Machine": (50000, 150000),
    "Injection Molder": (80000, 200000),
}

REGION_CURRENCY = {"China": "CNY", "India": "INR", "Europe": "EUR"}
REGION_FX = {"China": config.FX_ANCHOR_RATES["CNY"],
             "India": config.FX_ANCHOR_RATES["INR"],
             "Europe": config.FX_ANCHOR_RATES["EUR"]}

random.seed(42)


def _rand_between(lo, hi):
    return round(random.uniform(lo, hi), 2)


def generate_equipment_data() -> list[dict]:
    """Generate equipment specs for all regions × categories × suppliers."""
    rows = []
    eq_id = 0
    for region, suppliers in SUPPLIERS.items():
        for cat, ref_mtbf, ref_mttr in CATEGORIES:
            for sup_id, sup_name in suppliers:
                eq_id += 1
                lo, hi = BASE_PRICES_USD[cat]
                price_usd = _rand_between(lo, hi)

                # Apply regional price multiplier
                if region == "China":
                    price_usd *= _rand_between(0.60, 0.80)
                elif region == "India":
                    price_usd *= _rand_between(0.55, 0.75)
                # Europe stays at 1.0–1.2 of base

                local_price = round(price_usd * REGION_FX[region], 2)
                currency = REGION_CURRENCY[region]

                # Vary MTBF/MTTR by region
                mtbf_mult = {"China": 0.85, "India": 0.80, "Europe": 1.10}[region]
                mttr_mult = {"China": 1.15, "India": 1.25, "Europe": 0.85}[region]

                row = {
                    "equipment_id": f"EQ-{eq_id:04d}",
                    "name": f"{cat} ({region} — {sup_name})",
                    "category": cat,
                    "region": region,
                    "supplier_id": sup_id,
                    "supplier_name": sup_name,
                    "base_price_local": local_price,
                    "currency": currency,
                    "site_prep_cost": _rand_between(1500, 8000),
                    "installation_labor_hours": _rand_between(30, 120),
                    "certification_cost": _rand_between(1000, 5000),
                    "energy_kwh_per_year": _rand_between(20000, 80000),
                    "operator_hours_per_year": _rand_between(1000, 3000),
                    "consumables_per_year": _rand_between(2000, 10000),
                    "monitoring_cost_per_year": _rand_between(1000, 4000),
                    "preventive_maintenance_events_per_year": random.choice([2, 3, 4, 6]),
                    "corrective_maintenance_events_per_year": random.choice([1, 2, 3]),
                    "maintenance_labor_hours_per_event": _rand_between(4, 24),
                    "spares_cost_per_event": _rand_between(300, 2000),
                    "mtbf_hours": round(ref_mtbf * mtbf_mult * _rand_between(0.85, 1.15)),
                    "mttr_hours": round(ref_mttr * mttr_mult * _rand_between(0.85, 1.15)),
                    "warranty_years": random.choice([1, 2, 3]),
                    "warranty_coverage_pct": _rand_between(0.60, 0.95),
                    "spare_unit_price_local": round(local_price * _rand_between(0.005, 0.02), 2),
                    "spares_per_year": random.choice([3, 4, 6, 8, 12]),
                    "logistics_mode": random.choice(["Sea", "Air", "Rail", "Road"]) if region != "Europe" else random.choice(["Road", "Rail"]),
                    "logistics_distance_km": {"China": _rand_between(6000, 12000), "India": _rand_between(4000, 8000), "Europe": _rand_between(500, 3000)}[region],
                    "spare_weight_kg": _rand_between(5, 100),
                    "customs_clearance_cost": _rand_between(200, 800),
                    "rated_throughput_per_hour": _rand_between(50, 200),
                    "actual_throughput_per_hour": _rand_between(40, 190),
                    "yield_rate": _rand_between(0.88, 0.99),
                    "scrap_cost_per_unit": _rand_between(0.20, 1.50),
                    "asset_life_years": random.choice([8, 10, 12, 15]),
                }
                rows.append(row)
    return rows


def generate_supplier_data() -> list[dict]:
    """Generate supplier performance metrics."""
    rows = []
    for region, suppliers in SUPPLIERS.items():
        for sup_id, sup_name in suppliers:
            quality_base = {"China": 70, "India": 68, "Europe": 90}[region]
            delivery_base = {"China": 75, "India": 70, "Europe": 92}[region]
            service_base = {"China": 5.5, "India": 5.0, "Europe": 8.5}[region]
            warranty_base = {"China": 62, "India": 58, "Europe": 88}[region]
            price_base = {"China": 0.7, "India": 0.65, "Europe": 1.4}[region]
            support_base = {"China": 4.5, "India": 5.0, "Europe": 8.0}[region]

            row = {
                "supplier_id": sup_id,
                "supplier_name": sup_name,
                "region": region,
                "quality_index": round(quality_base + _rand_between(-3, 5)),
                "delivery_reliability": round(delivery_base + _rand_between(-3, 5)),
                "service_responsiveness": round(service_base + _rand_between(-0.5, 1.0), 1),
                "warranty_performance": round(warranty_base + _rand_between(-4, 6)),
                "price_competitiveness": round(price_base + _rand_between(-0.05, 0.15), 2),
                "local_support": round(support_base + _rand_between(-0.5, 1.5), 1),
            }
            rows.append(row)
    return rows


def generate_assumptions() -> dict:
    """Generate assumptions file matching config defaults."""
    return {
        "model_version": "0.1.0",
        "discount_rate": config.DEFAULT_DISCOUNT_RATE,
        "asset_life_years_default": 10,
        "monte_carlo_simulations": config.MC_DEFAULT_PATHS,
        "regions": config.REGIONS,
        "fx_anchor_rates": config.FX_ANCHOR_RATES,
        "fx_volatilities": config.FX_VOLATILITIES,
        "risk_weights": config.RISK_WEIGHTS,
        "tco_layer_weights": config.TCO_LAYER_WEIGHTS,
        "supplier_scorecard_weights": config.SUPPLIER_SCORECARD_WEIGHTS,
        "scenarios": list(config.PREDEFINED_SCENARIOS.keys()),
        "data_source": "synthetic_generator",
        "evidence_class": "simulated_estimate",
        "disclaimer": "All data is synthetically generated for demonstration. Not for production decisions.",
    }


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)

    # Equipment
    equipment = generate_equipment_data()
    eq_path = OUTPUT_DIR / "equipment.csv"
    with open(eq_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=equipment[0].keys())
        writer.writeheader()
        writer.writerows(equipment)
    print(f"✅ Generated {len(equipment)} equipment records → {eq_path}")

    # Suppliers
    suppliers = generate_supplier_data()
    sup_path = OUTPUT_DIR / "suppliers.csv"
    with open(sup_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=suppliers[0].keys())
        writer.writeheader()
        writer.writerows(suppliers)
    print(f"✅ Generated {len(suppliers)} supplier records → {sup_path}")

    # Assumptions
    assumptions = generate_assumptions()
    asm_path = OUTPUT_DIR / "assumptions.json"
    with open(asm_path, "w") as f:
        json.dump(assumptions, f, indent=2)
    print(f"✅ Generated assumptions → {asm_path}")

    print(f"\n📁 All sample data written to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
