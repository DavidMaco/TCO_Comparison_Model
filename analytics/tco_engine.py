"""
TCO Comparison Model — Core TCO Engine
Computes deterministic Total Cost of Ownership across all lifecycle layers
for Chinese, Indian, and European equipment and spares.

Every output includes assumption provenance and evidence class tags.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

import numpy as np
import pandas as pd

import config
from utils.logging_config import AuditLogger, get_logger
from utils.run_metadata import RunMetadata

log = get_logger("tco_engine")
audit = AuditLogger()


# ─── Data Structures ─────────────────────────────────────────────────

@dataclass
class EquipmentSpec:
    """Input specification for a single equipment/spare item."""
    equipment_id: str
    name: str
    category: str  # e.g., "CNC Machine", "Compressor", "Spare Part"
    region: str     # "China", "India", "Europe"
    supplier_id: str
    supplier_name: str

    # 2.1 Purchase cost
    base_price_local: float = 0.0
    currency: str = "USD"
    volume_discount_pct: float = 0.0
    trade_finance_cost_pct: float = 0.0

    # 2.2 Installation
    site_prep_cost: float = 0.0
    utilities_infra_cost: float = 0.0
    installation_labor_hours: float = 0.0
    certification_cost: float = 0.0
    testing_validation_cost: float = 0.0
    startup_consumables_cost: float = 0.0

    # 2.3 Operating
    energy_kwh_per_year: float = 0.0
    operator_hours_per_year: float = 0.0
    consumables_per_year: float = 0.0
    monitoring_cost_per_year: float = 0.0

    # 2.4 Maintenance
    preventive_maintenance_events_per_year: float = 2.0
    corrective_maintenance_events_per_year: float = 1.0
    maintenance_labor_hours_per_event: float = 8.0
    spares_cost_per_event: float = 0.0
    mtbf_hours: float = 5000.0
    mttr_hours: float = 24.0
    warranty_years: float = 1.0
    warranty_coverage_pct: float = 0.80

    # 2.5 Spares & logistics
    spare_unit_price_local: float = 0.0
    spares_per_year: float = 2.0
    logistics_mode: str = "Sea"  # Sea, Air, Rail, Road
    logistics_distance_km: float = 5000.0
    spare_weight_kg: float = 50.0
    customs_clearance_cost: float = 500.0
    inventory_carrying_pct: float = 0.20
    lead_time_days: float = 30.0
    lead_time_std_days: float = 10.0
    obsolescence_risk_pct: float = 0.05

    # 2.6 Risk & resilience (overrides, or region defaults used)
    disruption_probability: float | None = None
    supplier_financial_risk: float = 0.3

    # 2.7 Utilization
    rated_throughput_per_hour: float = 100.0
    actual_throughput_per_hour: float = 90.0
    yield_rate: float = 0.95
    scrap_cost_per_unit: float = 0.50

    # 2.8 Residual value
    salvage_value_pct: float = 0.10
    disposal_cost: float = 0.0
    environmental_compliance_cost: float = 0.0

    # Metadata
    asset_life_years: int = 10
    depreciation_method: str = "straight_line"


@dataclass
class TCOResult:
    """Complete TCO breakdown for one equipment specification."""
    equipment_id: str
    region: str
    supplier_id: str

    # Layer totals (lifetime, USD)
    acquisition_cost: float = 0.0
    installation_cost: float = 0.0
    operating_cost: float = 0.0
    maintenance_cost: float = 0.0
    spares_logistics_cost: float = 0.0
    risk_resilience_cost: float = 0.0
    utilization_impact_cost: float = 0.0
    residual_value: float = 0.0  # negative = recovery
    externalities_cost: float = 0.0

    total_tco: float = 0.0
    annualized_tco: float = 0.0

    # Breakdown details
    layer_details: dict = field(default_factory=dict)
    assumptions: dict = field(default_factory=dict)
    run_metadata: dict = field(default_factory=dict)
    evidence_class: str = "simulated_estimate"

    def to_dict(self) -> dict:
        return asdict(self)


# ─── Engine ──────────────────────────────────────────────────────────

class TCOEngine:
    """
    Deterministic Total Cost of Ownership calculator.
    Computes each layer independently, then aggregates.
    All costs normalized to USD using config FX rates.
    """

    def __init__(self, discount_rate: float = config.DEFAULT_DISCOUNT_RATE):
        self.discount_rate = discount_rate
        self.fx_rates = config.FX_ANCHOR_RATES
        self.labor_rates = config.REGIONAL_LABOR_RATES
        self.energy_costs = config.REGIONAL_ENERGY_COSTS
        self.tariffs = config.TARIFF_DEFAULTS
        self.logistics = config.LOGISTICS_MODES
        self.risk_indices = config.REGIONAL_RISK_INDICES

    def to_usd(self, amount: float, currency: str) -> float:
        """Convert local currency to USD."""
        if currency == "USD":
            return amount
        rate = self.fx_rates.get(currency, 1.0)
        return amount / rate if rate else amount

    # ── Layer Calculators ────────────────────────────────────────────

    def _calc_acquisition(self, spec: EquipmentSpec) -> dict:
        """2.1 Purchase cost layer."""
        base_usd = self.to_usd(spec.base_price_local, spec.currency)
        discount = base_usd * (spec.volume_discount_pct / 100)
        net_price = base_usd - discount
        trade_finance = net_price * (spec.trade_finance_cost_pct / 100)

        tariff_info = self.tariffs.get(spec.region, {})
        import_duty = net_price * tariff_info.get("import_duty_pct", 0) / 100
        anti_dumping = net_price * tariff_info.get("anti_dumping_pct", 0) / 100

        total = net_price + trade_finance + import_duty + anti_dumping
        return {
            "base_price_usd": base_usd,
            "volume_discount_usd": discount,
            "net_price_usd": net_price,
            "trade_finance_usd": trade_finance,
            "import_duty_usd": import_duty,
            "anti_dumping_usd": anti_dumping,
            "total_acquisition_usd": total,
        }

    def _calc_installation(self, spec: EquipmentSpec) -> dict:
        """2.2 Installation & commissioning layer."""
        labor_rate = self.labor_rates.get(spec.region, 20.0)
        labor = spec.installation_labor_hours * labor_rate
        total = (
            spec.site_prep_cost
            + spec.utilities_infra_cost
            + labor
            + spec.certification_cost
            + spec.testing_validation_cost
            + spec.startup_consumables_cost
        )
        return {
            "site_prep_usd": spec.site_prep_cost,
            "utilities_infra_usd": spec.utilities_infra_cost,
            "installation_labor_usd": labor,
            "certification_usd": spec.certification_cost,
            "testing_validation_usd": spec.testing_validation_cost,
            "startup_consumables_usd": spec.startup_consumables_cost,
            "total_installation_usd": total,
        }

    def _calc_operating(self, spec: EquipmentSpec, years: int) -> dict:
        """2.3 Operating cost layer (lifetime)."""
        energy_rate = self.energy_costs.get(spec.region, 0.15)
        labor_rate = self.labor_rates.get(spec.region, 20.0)
        annual_energy = spec.energy_kwh_per_year * energy_rate
        annual_labor = spec.operator_hours_per_year * labor_rate
        annual_total = annual_energy + annual_labor + spec.consumables_per_year + spec.monitoring_cost_per_year
        lifetime_total = sum(
            annual_total / ((1 + self.discount_rate) ** y) for y in range(1, years + 1)
        )
        return {
            "annual_energy_usd": annual_energy,
            "annual_labor_usd": annual_labor,
            "annual_consumables_usd": spec.consumables_per_year,
            "annual_monitoring_usd": spec.monitoring_cost_per_year,
            "annual_operating_usd": annual_total,
            "lifetime_operating_pv_usd": lifetime_total,
        }

    def _calc_maintenance(self, spec: EquipmentSpec, years: int) -> dict:
        """2.4 Maintenance, Repair & Overhaul layer (lifetime, PV)."""
        labor_rate = self.labor_rates.get(spec.region, 20.0)
        events_per_year = spec.preventive_maintenance_events_per_year + spec.corrective_maintenance_events_per_year
        labor_per_event = spec.maintenance_labor_hours_per_event * labor_rate
        cost_per_event = labor_per_event + spec.spares_cost_per_event
        annual_maintenance = events_per_year * cost_per_event

        # Warranty offset: first N years covered at X%
        warranty_yrs = int(min(spec.warranty_years, years))
        lifetime = 0.0
        for y in range(1, years + 1):
            annual = annual_maintenance
            if y <= warranty_yrs:
                annual *= (1 - spec.warranty_coverage_pct)
            lifetime += annual / ((1 + self.discount_rate) ** y)

        # Unplanned downtime cost estimate
        operating_hours_per_year = 8760 * 0.85  # 85% utilization
        expected_failures_per_year = operating_hours_per_year / spec.mtbf_hours if spec.mtbf_hours else 0
        downtime_cost_per_event = spec.mttr_hours * labor_rate * 1.5  # 1.5x for urgency premium
        annual_downtime_cost = expected_failures_per_year * downtime_cost_per_event
        lifetime_downtime = sum(
            annual_downtime_cost / ((1 + self.discount_rate) ** y) for y in range(1, years + 1)
        )

        return {
            "events_per_year": events_per_year,
            "cost_per_event_usd": cost_per_event,
            "annual_planned_maintenance_usd": annual_maintenance,
            "warranty_years": warranty_yrs,
            "expected_failures_per_year": expected_failures_per_year,
            "annual_downtime_cost_usd": annual_downtime_cost,
            "lifetime_planned_pv_usd": lifetime,
            "lifetime_downtime_pv_usd": lifetime_downtime,
            "total_maintenance_pv_usd": lifetime + lifetime_downtime,
        }

    def _calc_spares_logistics(self, spec: EquipmentSpec, years: int) -> dict:
        """2.5 Spare parts & supply chain layer (lifetime, PV)."""
        spare_usd = self.to_usd(spec.spare_unit_price_local, spec.currency)
        mode_info = self.logistics.get(spec.logistics_mode, self.logistics["Sea"])
        freight_per_shipment = spec.spare_weight_kg * spec.logistics_distance_km * mode_info["cost_per_kg_km"]

        annual_spares_cost = spec.spares_per_year * spare_usd
        annual_freight = spec.spares_per_year * (freight_per_shipment + spec.customs_clearance_cost)
        annual_inventory_carrying = annual_spares_cost * spec.inventory_carrying_pct
        annual_obsolescence = annual_spares_cost * spec.obsolescence_risk_pct

        annual_total = annual_spares_cost + annual_freight + annual_inventory_carrying + annual_obsolescence
        lifetime_total = sum(
            annual_total / ((1 + self.discount_rate) ** y) for y in range(1, years + 1)
        )
        return {
            "spare_unit_price_usd": spare_usd,
            "freight_per_shipment_usd": freight_per_shipment,
            "annual_spares_cost_usd": annual_spares_cost,
            "annual_freight_usd": annual_freight,
            "annual_inventory_carrying_usd": annual_inventory_carrying,
            "annual_obsolescence_usd": annual_obsolescence,
            "annual_total_usd": annual_total,
            "lifetime_spares_logistics_pv_usd": lifetime_total,
        }

    def _calc_risk_resilience(self, spec: EquipmentSpec, acquisition_cost: float, years: int) -> dict:
        """2.6 Risk & resilience cost layer."""
        region_risks = self.risk_indices.get(spec.region, {})
        disruption_prob = spec.disruption_probability if spec.disruption_probability is not None else region_risks.get("supply_disruption", 0.1)

        # Expected annual loss from disruption
        disruption_impact = acquisition_cost * 0.15  # 15% of asset cost per disruption event
        annual_disruption_eal = disruption_prob * disruption_impact

        # FX risk (annual expected loss from currency moves)
        currency = config.REGION_CURRENCIES.get(spec.region, "USD")
        fx_vol = config.FX_VOLATILITIES.get(currency, 0.10)
        annual_fx_risk_cost = acquisition_cost * fx_vol * 0.5  # half-vol as expected cost

        # Political / regulatory risk premium
        political_risk = region_risks.get("political_regulatory", 0.1)
        annual_political_cost = acquisition_cost * political_risk * 0.02

        # Supplier financial health risk
        annual_supplier_risk = acquisition_cost * spec.supplier_financial_risk * 0.03

        annual_total = annual_disruption_eal + annual_fx_risk_cost + annual_political_cost + annual_supplier_risk
        lifetime_total = sum(
            annual_total / ((1 + self.discount_rate) ** y) for y in range(1, years + 1)
        )
        return {
            "disruption_probability": disruption_prob,
            "annual_disruption_eal_usd": annual_disruption_eal,
            "annual_fx_risk_usd": annual_fx_risk_cost,
            "annual_political_risk_usd": annual_political_cost,
            "annual_supplier_risk_usd": annual_supplier_risk,
            "annual_total_risk_usd": annual_total,
            "lifetime_risk_pv_usd": lifetime_total,
        }

    def _calc_utilization(self, spec: EquipmentSpec, years: int) -> dict:
        """2.7 Asset utilization & productivity impact."""
        throughput_gap = spec.rated_throughput_per_hour - spec.actual_throughput_per_hour
        annual_hours = 8760 * 0.85
        annual_lost_units = throughput_gap * annual_hours
        yield_loss = (1 - spec.yield_rate) * spec.actual_throughput_per_hour * annual_hours
        annual_scrap_cost = yield_loss * spec.scrap_cost_per_unit
        annual_productivity_loss = annual_lost_units * spec.scrap_cost_per_unit * 0.5  # proxy

        annual_total = annual_scrap_cost + annual_productivity_loss
        lifetime_total = sum(
            annual_total / ((1 + self.discount_rate) ** y) for y in range(1, years + 1)
        )
        return {
            "throughput_gap_per_hour": throughput_gap,
            "annual_lost_units": annual_lost_units,
            "annual_scrap_cost_usd": annual_scrap_cost,
            "annual_productivity_loss_usd": annual_productivity_loss,
            "lifetime_utilization_pv_usd": lifetime_total,
        }

    def _calc_residual(self, spec: EquipmentSpec, acquisition_cost: float) -> dict:
        """2.8 Residual value & disposal."""
        salvage_value = acquisition_cost * spec.salvage_value_pct
        # Discount to present value
        pv_salvage = salvage_value / ((1 + self.discount_rate) ** spec.asset_life_years)
        pv_disposal = (spec.disposal_cost + spec.environmental_compliance_cost) / (
            (1 + self.discount_rate) ** spec.asset_life_years
        )
        net_residual = pv_salvage - pv_disposal
        return {
            "salvage_value_usd": salvage_value,
            "pv_salvage_usd": pv_salvage,
            "disposal_cost_usd": spec.disposal_cost,
            "environmental_cost_usd": spec.environmental_compliance_cost,
            "pv_disposal_usd": pv_disposal,
            "net_residual_pv_usd": net_residual,
        }

    # ── Main Compute ─────────────────────────────────────────────────

    def compute(self, spec: EquipmentSpec, run_meta: RunMetadata | None = None) -> TCOResult:
        """Compute full lifecycle TCO for a single equipment spec."""
        meta = run_meta or RunMetadata()
        years = spec.asset_life_years

        # Compute each layer
        acq = self._calc_acquisition(spec)
        inst = self._calc_installation(spec)
        ops = self._calc_operating(spec, years)
        maint = self._calc_maintenance(spec, years)
        spares = self._calc_spares_logistics(spec, years)
        risk = self._calc_risk_resilience(spec, acq["total_acquisition_usd"], years)
        util = self._calc_utilization(spec, years)
        resid = self._calc_residual(spec, acq["total_acquisition_usd"])

        total_tco = (
            acq["total_acquisition_usd"]
            + inst["total_installation_usd"]
            + ops["lifetime_operating_pv_usd"]
            + maint["total_maintenance_pv_usd"]
            + spares["lifetime_spares_logistics_pv_usd"]
            + risk["lifetime_risk_pv_usd"]
            + util["lifetime_utilization_pv_usd"]
            - resid["net_residual_pv_usd"]
        )

        result = TCOResult(
            equipment_id=spec.equipment_id,
            region=spec.region,
            supplier_id=spec.supplier_id,
            acquisition_cost=acq["total_acquisition_usd"],
            installation_cost=inst["total_installation_usd"],
            operating_cost=ops["lifetime_operating_pv_usd"],
            maintenance_cost=maint["total_maintenance_pv_usd"],
            spares_logistics_cost=spares["lifetime_spares_logistics_pv_usd"],
            risk_resilience_cost=risk["lifetime_risk_pv_usd"],
            utilization_impact_cost=util["lifetime_utilization_pv_usd"],
            residual_value=resid["net_residual_pv_usd"],
            total_tco=total_tco,
            annualized_tco=total_tco / years if years else 0,
            layer_details={
                "acquisition": acq,
                "installation": inst,
                "operating": ops,
                "maintenance": maint,
                "spares_logistics": spares,
                "risk_resilience": risk,
                "utilization": util,
                "residual": resid,
            },
            assumptions={
                "discount_rate": self.discount_rate,
                "asset_life_years": years,
                "region": spec.region,
                "currency": spec.currency,
                "fx_rate_used": self.fx_rates.get(spec.currency, 1.0),
                "labor_rate_usd_hr": self.labor_rates.get(spec.region, 20.0),
                "energy_rate_usd_kwh": self.energy_costs.get(spec.region, 0.15),
                "logistics_mode": spec.logistics_mode,
            },
            run_metadata=meta.seal({"equipment_id": spec.equipment_id, "region": spec.region}),
            evidence_class="simulated_estimate",
        )

        audit.record("tco_computed", {
            "equipment_id": spec.equipment_id,
            "region": spec.region,
            "total_tco": round(total_tco, 2),
        }, run_id=meta.run_id)

        log.info(
            "TCO computed: %s (%s) = $%.0f over %d years",
            spec.name, spec.region, total_tco, years,
        )
        return result

    def compare(self, specs: list[EquipmentSpec], run_meta: RunMetadata | None = None) -> pd.DataFrame:
        """Compute and compare TCO across multiple equipment specs / regions."""
        meta = run_meta or RunMetadata()
        results = [self.compute(spec, meta) for spec in specs]
        df = pd.DataFrame([r.to_dict() for r in results])

        # Rank
        df["tco_rank"] = df["total_tco"].rank(method="min").astype(int)
        df = df.sort_values("total_tco")

        audit.record("tco_comparison", {
            "items_compared": len(specs),
            "regions": list(df["region"].unique()),
            "best_tco_equipment": df.iloc[0]["equipment_id"] if len(df) else None,
        }, run_id=meta.run_id)

        return df
