"""
TCO Comparison Model — Prescriptive Optimization Engine
Recommends optimal sourcing decisions under constraints:
- Best equipment source per scenario
- Maintenance scheduling optimization
- Spare parts stocking strategy
- Outsource vs in-house trade-offs
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from scipy import optimize as sp_optimize

import config
from analytics.tco_engine import TCOEngine, EquipmentSpec, TCOResult
from analytics.monte_carlo import MonteCarloSimulator
from analytics.supplier_scorecard import SupplierScorecard
from utils.logging_config import get_logger, AuditLogger
from utils.run_metadata import RunMetadata

log = get_logger("optimization")
audit = AuditLogger()


class TCOptimizer:
    """
    Prescriptive optimization engine that recommends:
    1. Best sourcing region under risk-adjusted TCO
    2. Optimal maintenance intervals
    3. Spare inventory strategy (EOQ-based)
    4. Make vs buy service decisions
    """

    def __init__(self):
        self.engine = TCOEngine()

    # ── 1. Sourcing Recommendation ───────────────────────────────────

    def recommend_source(
        self,
        specs: list[EquipmentSpec],
        supplier_data: list[dict] | None = None,
        risk_tolerance: str = "moderate",  # "low", "moderate", "high"
        run_meta: RunMetadata | None = None,
    ) -> dict[str, Any]:
        """
        Recommend best equipment source considering TCO + risk + supplier quality.
        """
        meta = run_meta or RunMetadata(scenario="sourcing_recommendation")

        # Compute deterministic TCO
        tco_results = [self.engine.compute(s, meta) for s in specs]

        # Monte Carlo for risk bands
        mc = MonteCarloSimulator(n_simulations=2000)
        mc_results = [mc.simulate_single(s, meta) for s in specs]

        # Supplier scores (if data available)
        scorecard = SupplierScorecard()
        supplier_scores = None
        if supplier_data:
            supplier_scores = scorecard.score_multiple(supplier_data)

        # Risk tolerance mapping
        risk_weights = {"low": 0.6, "moderate": 0.3, "high": 0.1}
        risk_w = risk_weights.get(risk_tolerance, 0.3)
        cost_w = 1 - risk_w

        # Composite ranking
        rankings = []
        for i, (spec, tco, mc_r) in enumerate(zip(specs, tco_results, mc_results)):
            # Normalize TCO (lower is better)
            tco_norm = tco.total_tco
            # Risk metric: use P95 - P50 as risk spread
            risk_spread = mc_r["tco_p95"] - mc_r["tco_p50"]

            # Supplier quality bonus (if available)
            supplier_bonus = 0
            if supplier_scores is not None and not supplier_scores.empty:
                match = supplier_scores[supplier_scores["supplier_id"] == spec.supplier_id]
                if not match.empty:
                    supplier_bonus = match.iloc[0]["composite_score"] * 0.1 * tco_norm  # up to 10% TCO reduction

            adjusted_score = (cost_w * tco_norm) + (risk_w * risk_spread) - supplier_bonus

            rankings.append({
                "equipment_id": spec.equipment_id,
                "region": spec.region,
                "supplier": spec.supplier_name,
                "deterministic_tco": tco.total_tco,
                "mc_mean_tco": mc_r["tco_mean"],
                "mc_p05_tco": mc_r["tco_p05"],
                "mc_p95_tco": mc_r["tco_p95"],
                "risk_spread": risk_spread,
                "supplier_quality_bonus": supplier_bonus,
                "risk_adjusted_score": adjusted_score,
            })

        df = pd.DataFrame(rankings).sort_values("risk_adjusted_score")
        df["recommendation_rank"] = range(1, len(df) + 1)

        best = df.iloc[0]
        recommendation = {
            "recommended_source": {
                "equipment_id": best["equipment_id"],
                "region": best["region"],
                "supplier": best["supplier"],
                "risk_adjusted_score": round(best["risk_adjusted_score"], 2),
                "deterministic_tco": round(best["deterministic_tco"], 2),
                "confidence_range": [round(best["mc_p05_tco"], 2), round(best["mc_p95_tco"], 2)],
            },
            "all_options": df.to_dict("records"),
            "risk_tolerance": risk_tolerance,
            "methodology": "Weighted TCO + Monte Carlo risk spread + supplier quality adjustment",
            "evidence_class": "simulated_estimate",
            "run_metadata": meta.seal({"n_options": len(specs), "risk_tolerance": risk_tolerance}),
        }

        audit.record("sourcing_recommendation", {
            "recommended": best["equipment_id"],
            "region": best["region"],
            "score": round(best["risk_adjusted_score"], 2),
        }, run_id=meta.run_id)

        log.info("Sourcing recommendation: %s (%s) — score=$%.0f", best["equipment_id"], best["region"], best["risk_adjusted_score"])
        return recommendation

    # ── 2. Maintenance Scheduling ────────────────────────────────────

    def optimize_maintenance_interval(
        self,
        spec: EquipmentSpec,
        run_meta: RunMetadata | None = None,
    ) -> dict[str, Any]:
        """
        Find the PM interval that minimizes total maintenance + downtime cost.
        Uses simple cost-rate optimization.
        """
        meta = run_meta or RunMetadata(scenario="maintenance_optimization")
        labor_rate = config.REGIONAL_LABOR_RATES.get(spec.region, 20.0)

        # Cost of one PM event
        pm_cost = spec.maintenance_labor_hours_per_event * labor_rate + spec.spares_cost_per_event

        # Cost of one corrective event (unplanned — higher due to urgency)
        cm_cost = pm_cost * 2.5  # 2.5x urgency multiplier
        downtime_cost_per_hour = labor_rate * 3  # opportunity cost multiplier

        def total_cost_rate(pm_interval_hours: float) -> float:
            """Annual cost rate as function of PM interval."""
            if pm_interval_hours <= 0:
                return 1e12
            # PM events per year
            operating_hours = 8760 * 0.85
            n_pm = operating_hours / pm_interval_hours
            pm_annual = n_pm * pm_cost

            # Failure rate increases as PM interval stretches beyond MTBF
            ratio = pm_interval_hours / spec.mtbf_hours if spec.mtbf_hours > 0 else 1
            failure_rate = (operating_hours / spec.mtbf_hours) * (1 + max(0, ratio - 0.8) * 2)
            cm_annual = failure_rate * (cm_cost + spec.mttr_hours * downtime_cost_per_hour)

            return pm_annual + cm_annual

        # Search optimal interval
        result = sp_optimize.minimize_scalar(
            total_cost_rate,
            bounds=(100, spec.mtbf_hours * 2),
            method="bounded",
        )

        optimal_interval = result.x
        optimal_cost = result.fun
        current_interval = 8760 * 0.85 / spec.preventive_maintenance_events_per_year if spec.preventive_maintenance_events_per_year > 0 else spec.mtbf_hours
        current_cost = total_cost_rate(current_interval)

        savings = current_cost - optimal_cost

        recommendation = {
            "equipment_id": spec.equipment_id,
            "region": spec.region,
            "current_pm_interval_hours": round(current_interval, 0),
            "optimal_pm_interval_hours": round(optimal_interval, 0),
            "current_annual_maintenance_cost": round(current_cost, 2),
            "optimal_annual_maintenance_cost": round(optimal_cost, 2),
            "annual_savings": round(savings, 2),
            "savings_pct": round(savings / current_cost * 100, 1) if current_cost > 0 else 0,
            "evidence_class": "simulated_estimate",
            "run_metadata": meta.seal({"equipment_id": spec.equipment_id}),
        }

        log.info("Maintenance optimization: %s — optimal interval=%.0f hrs, savings=$%.0f/yr",
                 spec.name, optimal_interval, savings)
        return recommendation

    # ── 3. Spare Parts Inventory Optimization ────────────────────────

    def optimize_spare_inventory(
        self,
        spec: EquipmentSpec,
        service_level: float = 0.95,
        run_meta: RunMetadata | None = None,
    ) -> dict[str, Any]:
        """
        EOQ-based spare parts inventory optimization with safety stock.
        """
        meta = run_meta or RunMetadata(scenario="spare_inventory_optimization")

        spare_usd = config.FX_ANCHOR_RATES.get(config.REGION_CURRENCIES.get(spec.region, "USD"), 1.0)
        spare_unit_cost = spec.spare_unit_price_local / spare_usd if spare_usd else spec.spare_unit_price_local

        annual_demand = spec.spares_per_year
        ordering_cost = spec.customs_clearance_cost + 200  # admin + customs per order
        holding_cost_per_unit = spare_unit_cost * spec.inventory_carrying_pct

        # EOQ
        if holding_cost_per_unit > 0 and annual_demand > 0:
            eoq = np.sqrt(2 * annual_demand * ordering_cost / holding_cost_per_unit)
        else:
            eoq = annual_demand

        # Safety stock (normal approximation)
        z = {0.90: 1.28, 0.95: 1.65, 0.99: 2.33}.get(service_level, 1.65)
        daily_demand = annual_demand / 365
        safety_stock = z * np.sqrt(spec.lead_time_days) * daily_demand * (spec.lead_time_std_days / spec.lead_time_days if spec.lead_time_days > 0 else 0.3)

        reorder_point = daily_demand * spec.lead_time_days + safety_stock
        total_inventory_cost = (annual_demand / eoq) * ordering_cost + (eoq / 2 + safety_stock) * holding_cost_per_unit

        # Compare to naive strategy (order each time)
        naive_cost = annual_demand * ordering_cost + (annual_demand / 2) * holding_cost_per_unit

        recommendation = {
            "equipment_id": spec.equipment_id,
            "region": spec.region,
            "spare_unit_cost_usd": round(spare_unit_cost, 2),
            "annual_demand_units": round(annual_demand, 1),
            "eoq_units": round(eoq, 1),
            "safety_stock_units": round(safety_stock, 1),
            "reorder_point_units": round(reorder_point, 1),
            "optimal_annual_inventory_cost": round(total_inventory_cost, 2),
            "naive_annual_inventory_cost": round(naive_cost, 2),
            "annual_savings": round(naive_cost - total_inventory_cost, 2),
            "service_level": service_level,
            "evidence_class": "simulated_estimate",
            "run_metadata": meta.seal({"equipment_id": spec.equipment_id}),
        }

        log.info("Spare inventory optimization: %s — EOQ=%.0f, safety=%.0f, saves=$%.0f/yr",
                 spec.name, eoq, safety_stock, naive_cost - total_inventory_cost)
        return recommendation

    # ── 4. Make vs Buy Service Decision ──────────────────────────────

    def make_vs_buy_analysis(
        self,
        spec: EquipmentSpec,
        outsource_cost_per_event: float = 0.0,
        run_meta: RunMetadata | None = None,
    ) -> dict[str, Any]:
        """Compare in-house maintenance vs outsourced service contract."""
        meta = run_meta or RunMetadata(scenario="make_vs_buy")
        labor_rate = config.REGIONAL_LABOR_RATES.get(spec.region, 20.0)

        # In-house cost
        events = spec.preventive_maintenance_events_per_year + spec.corrective_maintenance_events_per_year
        in_house_per_event = spec.maintenance_labor_hours_per_event * labor_rate + spec.spares_cost_per_event
        in_house_annual = events * in_house_per_event

        # Outsourced cost (if not provided, estimate at 1.4x in-house)
        if outsource_cost_per_event <= 0:
            outsource_cost_per_event = in_house_per_event * 1.4
        outsource_annual = events * outsource_cost_per_event

        # Risk adjustment: outsourcing reduces downtime risk (faster response)
        downtime_reduction_pct = 0.30  # 30% less downtime with dedicated service
        in_house_downtime_cost = spec.mttr_hours * labor_rate * 1.5 * (8760 * 0.85 / spec.mtbf_hours if spec.mtbf_hours else 0)
        outsource_downtime_cost = in_house_downtime_cost * (1 - downtime_reduction_pct)

        in_house_total = in_house_annual + in_house_downtime_cost
        outsource_total = outsource_annual + outsource_downtime_cost

        recommendation = {
            "equipment_id": spec.equipment_id,
            "region": spec.region,
            "in_house_annual_cost": round(in_house_total, 2),
            "outsource_annual_cost": round(outsource_total, 2),
            "cost_difference": round(outsource_total - in_house_total, 2),
            "recommendation": "in_house" if in_house_total <= outsource_total else "outsource",
            "savings_with_recommendation": round(abs(outsource_total - in_house_total), 2),
            "downtime_risk_factor": downtime_reduction_pct,
            "evidence_class": "simulated_estimate",
            "run_metadata": meta.seal({"equipment_id": spec.equipment_id}),
        }

        log.info("Make vs Buy: %s — recommend %s, saves $%.0f/yr",
                 spec.name, recommendation["recommendation"], recommendation["savings_with_recommendation"])
        return recommendation

    # ── 5. Full Optimization Report ──────────────────────────────────

    def full_optimization(
        self,
        specs: list[EquipmentSpec],
        supplier_data: list[dict] | None = None,
        run_meta: RunMetadata | None = None,
    ) -> dict[str, Any]:
        """Run all optimization analyses and compile a full report."""
        meta = run_meta or RunMetadata(scenario="full_optimization")

        sourcing = self.recommend_source(specs, supplier_data, run_meta=meta)
        maintenance_recs = [self.optimize_maintenance_interval(s, meta) for s in specs]
        spare_recs = [self.optimize_spare_inventory(s, run_meta=meta) for s in specs]
        make_buy_recs = [self.make_vs_buy_analysis(s, run_meta=meta) for s in specs]

        total_potential_savings = (
            sum(m["annual_savings"] for m in maintenance_recs)
            + sum(s["annual_savings"] for s in spare_recs)
            + sum(mb["savings_with_recommendation"] for mb in make_buy_recs)
        )

        report = {
            "sourcing_recommendation": sourcing,
            "maintenance_optimizations": maintenance_recs,
            "spare_inventory_optimizations": spare_recs,
            "make_vs_buy_analyses": make_buy_recs,
            "total_annual_savings_potential": round(total_potential_savings, 2),
            "evidence_class": "simulated_estimate",
            "run_metadata": meta.seal({"n_specs": len(specs)}),
        }

        audit.record("full_optimization_complete", {
            "n_specs": len(specs),
            "total_savings_potential": round(total_potential_savings, 2),
        }, run_id=meta.run_id)

        log.info("Full optimization: %d equipment items — total savings potential $%.0f/yr",
                 len(specs), total_potential_savings)
        return report
