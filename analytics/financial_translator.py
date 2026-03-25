"""
TCO Comparison Model — Financial Translator
Converts TCO engineering outputs into finance-grade metrics:
NPV, IRR, EBITDA impact, working capital, and lifecycle cashflow profiles.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

import config
from analytics.tco_engine import EquipmentSpec, TCOResult
from utils.logging_config import AuditLogger, get_logger
from utils.run_metadata import RunMetadata

log = get_logger("financial_translator")
audit = AuditLogger()


class FinancialTranslator:
    """
    Translates TCO results into financial decision metrics.
    Bridges engineering cost analysis with CFO / finance accountability.
    """

    def __init__(self, discount_rate: float = config.DEFAULT_DISCOUNT_RATE):
        self.discount_rate = discount_rate

    def lifecycle_cashflow(self, spec: EquipmentSpec, tco_result: TCOResult) -> pd.DataFrame:
        """Generate year-by-year cashflow schedule for the asset."""
        years = spec.asset_life_years
        details = tco_result.layer_details

        rows = []
        for y in range(0, years + 1):
            if y == 0:
                # Year 0: acquisition + installation
                row = {
                    "year": 0,
                    "acquisition": -tco_result.acquisition_cost,
                    "installation": -tco_result.installation_cost,
                    "operating": 0,
                    "maintenance": 0,
                    "spares_logistics": 0,
                    "risk_cost": 0,
                    "utilization_loss": 0,
                    "residual": 0,
                    "net_cashflow": -(tco_result.acquisition_cost + tco_result.installation_cost),
                }
            elif y == years:
                # Final year: normal ops + residual recovery
                ops = details["operating"].get("annual_operating_usd", 0)
                maint = details["maintenance"].get("annual_planned_maintenance_usd", 0) + details["maintenance"].get("annual_downtime_cost_usd", 0)
                spares = details["spares_logistics"].get("annual_total_usd", 0)
                risk_annual = details["risk_resilience"].get("annual_total_risk_usd", 0)
                util_annual = details["utilization"].get("annual_scrap_cost_usd", 0) + details["utilization"].get("annual_productivity_loss_usd", 0)
                residual = details["residual"].get("salvage_value_usd", 0) - details["residual"].get("disposal_cost_usd", 0) - details["residual"].get("environmental_cost_usd", 0)

                row = {
                    "year": y,
                    "acquisition": 0,
                    "installation": 0,
                    "operating": -ops,
                    "maintenance": -maint,
                    "spares_logistics": -spares,
                    "risk_cost": -risk_annual,
                    "utilization_loss": -util_annual,
                    "residual": residual,
                    "net_cashflow": -(ops + maint + spares + risk_annual + util_annual) + residual,
                }
            else:
                # Operating years
                ops = details["operating"].get("annual_operating_usd", 0)
                maint_base = details["maintenance"].get("annual_planned_maintenance_usd", 0) + details["maintenance"].get("annual_downtime_cost_usd", 0)
                # Warranty offset
                warranty_yrs = int(details["maintenance"].get("warranty_years", 0))
                if y <= warranty_yrs:
                    maint = maint_base * (1 - spec.warranty_coverage_pct)
                else:
                    maint = maint_base
                spares = details["spares_logistics"].get("annual_total_usd", 0)
                risk_annual = details["risk_resilience"].get("annual_total_risk_usd", 0)
                util_annual = details["utilization"].get("annual_scrap_cost_usd", 0) + details["utilization"].get("annual_productivity_loss_usd", 0)

                row = {
                    "year": y,
                    "acquisition": 0,
                    "installation": 0,
                    "operating": -ops,
                    "maintenance": -maint,
                    "spares_logistics": -spares,
                    "risk_cost": -risk_annual,
                    "utilization_loss": -util_annual,
                    "residual": 0,
                    "net_cashflow": -(ops + maint + spares + risk_annual + util_annual),
                }
            rows.append(row)

        df = pd.DataFrame(rows)
        df["cumulative_cashflow"] = df["net_cashflow"].cumsum()
        df["discount_factor"] = [(1 / (1 + self.discount_rate) ** y) for y in df["year"]]
        df["pv_cashflow"] = df["net_cashflow"] * df["discount_factor"]
        return df

    def compute_npv(self, cashflows: pd.DataFrame) -> float:
        """Net Present Value of the lifecycle cashflows."""
        return float(cashflows["pv_cashflow"].sum())

    def compute_irr(self, cashflows: pd.DataFrame) -> float | None:
        """Internal Rate of Return — numerical solver."""
        cf = cashflows["net_cashflow"].values
        try:
            return float(np.irr(cf)) if hasattr(np, "irr") else self._irr_bisection(cf)
        except Exception:
            return self._irr_bisection(cf)

    @staticmethod
    def _irr_bisection(cashflows: np.ndarray, tol: float = 1e-6, max_iter: int = 1000) -> float | None:
        """Bisection method for IRR computation."""
        lo, hi = -0.5, 5.0
        for _ in range(max_iter):
            mid = (lo + hi) / 2
            npv = sum(cf / (1 + mid) ** t for t, cf in enumerate(cashflows))
            if abs(npv) < tol:
                return mid
            if npv > 0:
                lo = mid
            else:
                hi = mid
        return (lo + hi) / 2

    def compute_ebitda_impact(self, spec: EquipmentSpec, tco_result: TCOResult) -> dict:
        """Estimate annual EBITDA impact from equipment ownership."""
        details = tco_result.layer_details
        annual_ops = details["operating"].get("annual_operating_usd", 0)
        annual_maint = details["maintenance"].get("annual_planned_maintenance_usd", 0) + details["maintenance"].get("annual_downtime_cost_usd", 0)
        annual_spares = details["spares_logistics"].get("annual_total_usd", 0)

        annual_opex = annual_ops + annual_maint + annual_spares
        # Straight-line depreciation over asset life
        asset_life = max(spec.asset_life_years, 1)
        annual_depreciation = tco_result.acquisition_cost / asset_life

        return {
            "annual_opex_usd": annual_opex,
            "annual_ebitda_drag_usd": annual_opex,
            "acquisition_capex_usd": tco_result.acquisition_cost + tco_result.installation_cost,
            "annual_depreciation_usd": annual_depreciation,
        }

    def compute_working_capital_impact(self, spec: EquipmentSpec, tco_result: TCOResult) -> dict:
        """Estimate working capital requirements."""
        details = tco_result.layer_details
        annual_spares = details["spares_logistics"].get("annual_total_usd", 0)
        inventory_value = annual_spares * spec.inventory_carrying_pct

        return {
            "spare_inventory_value_usd": inventory_value,
            "lead_time_days": spec.lead_time_days,
            "safety_stock_days": spec.lead_time_std_days * 1.65,  # 95% service level
            "working_capital_tied_usd": inventory_value * (spec.lead_time_days / 365),
        }

    def full_financial_analysis(
        self,
        spec: EquipmentSpec,
        tco_result: TCOResult,
        run_meta: RunMetadata | None = None,
    ) -> dict[str, Any]:
        """Complete financial analysis package for one equipment/region."""
        meta = run_meta or RunMetadata(scenario="financial_analysis")
        cashflows = self.lifecycle_cashflow(spec, tco_result)
        npv = self.compute_npv(cashflows)
        irr = self.compute_irr(cashflows)
        ebitda = self.compute_ebitda_impact(spec, tco_result)
        working_cap = self.compute_working_capital_impact(spec, tco_result)

        result = {
            "equipment_id": spec.equipment_id,
            "region": spec.region,
            "npv_usd": npv,
            "irr": irr,
            "total_tco_usd": tco_result.total_tco,
            "annualized_tco_usd": tco_result.annualized_tco,
            "ebitda_impact": ebitda,
            "working_capital_impact": working_cap,
            "cashflow_schedule": cashflows.to_dict("records"),
            "payback_period_years": self._payback_period(cashflows),
            "discount_rate": self.discount_rate,
            "evidence_class": "simulated_estimate",
            "run_metadata": meta.seal({"equipment_id": spec.equipment_id}),
        }

        audit.record("financial_analysis_complete", {
            "equipment_id": spec.equipment_id,
            "npv": round(npv, 2),
            "irr": round(irr, 4) if irr is not None else None,
        }, run_id=meta.run_id)

        log.info("Financial analysis: %s (%s) — NPV=$%.0f, IRR=%s", spec.name, spec.region, npv, f"{irr:.2%}" if irr else "N/A")
        return result

    @staticmethod
    def _payback_period(cashflows: pd.DataFrame) -> float | None:
        """Estimate payback period from cumulative cashflows."""
        cum = cashflows["cumulative_cashflow"]
        positive = cum[cum >= 0]
        if positive.empty:
            return None
        return float(positive.index[0])

    def compare_financial(
        self,
        specs: list[EquipmentSpec],
        tco_results: list[TCOResult],
        run_meta: RunMetadata | None = None,
    ) -> pd.DataFrame:
        """Compare financial metrics across multiple equipment options."""
        meta = run_meta or RunMetadata(scenario="financial_comparison")
        rows = []
        for spec, tco in zip(specs, tco_results):
            analysis = self.full_financial_analysis(spec, tco, meta)
            rows.append({
                "equipment_id": spec.equipment_id,
                "region": spec.region,
                "supplier": spec.supplier_name,
                "total_tco": analysis["total_tco_usd"],
                "npv": analysis["npv_usd"],
                "irr": analysis["irr"],
                "annualized_tco": analysis["annualized_tco_usd"],
                "payback_years": analysis["payback_period_years"],
                "working_capital_tied": analysis["working_capital_impact"]["working_capital_tied_usd"],
            })
        df = pd.DataFrame(rows)
        df["npv_rank"] = df["npv"].rank(ascending=False, method="min").astype(int)
        return df.sort_values("npv", ascending=False)
