"""
TCO Comparison Model — Scenario Engine
Multi-scenario decision engine for comparing equipment sourcing
under different macro and operational conditions.

Supports 6+ predefined scenarios plus custom user-defined scenarios.
"""
from __future__ import annotations

from dataclasses import replace
from typing import Any

import numpy as np
import pandas as pd

import config
from analytics.tco_engine import TCOEngine, EquipmentSpec, TCOResult
from utils.logging_config import get_logger, AuditLogger
from utils.run_metadata import RunMetadata

log = get_logger("scenario_engine")
audit = AuditLogger()


class ScenarioEngine:
    """
    Applies macro-economic and operational scenario shocks to equipment specs,
    then computes TCO under each scenario for comparison.
    """

    def __init__(self, scenarios: dict[str, dict] | None = None):
        self.scenarios = scenarios or config.PREDEFINED_SCENARIOS

    def _apply_scenario(self, spec: EquipmentSpec, scenario: dict) -> EquipmentSpec:
        """Apply scenario adjustments to an equipment specification.

        Shocks applied:
        - **fx_shock_pct** → scales ``base_price_local`` and ``spare_unit_price_local``
        - **tariff_delta_pct** → further scales ``base_price_local`` and
          ``spare_unit_price_local`` (import-duty proxy)
        - **energy_escalation_pct** → scales ``energy_kwh_per_year``
        - **labor_escalation_pct** → scales ``operator_hours_per_year`` and
          ``maintenance_labor_hours_per_event`` (wage-inflation proxy)
        - **disruption_probability** → overrides if provided
        """
        fx_shock = scenario.get("fx_shock_pct", 0)
        tariff_delta = scenario.get("tariff_delta_pct", 0)
        energy_esc = scenario.get("energy_escalation_pct", 0)
        labor_esc = scenario.get("labor_escalation_pct", 0)
        disruption_prob = scenario.get("disruption_probability", None)

        # Adjust base price for FX shock + tariff delta (compounded)
        adjusted_price = spec.base_price_local * (1 + fx_shock) * (1 + tariff_delta)

        # Adjust energy consumption cost proxy (via kwh assumption)
        adjusted_energy = spec.energy_kwh_per_year * (1 + energy_esc)

        # Adjust spare prices (tariffs apply to imported spares too)
        adjusted_spare = spec.spare_unit_price_local * (1 + fx_shock) * (1 + tariff_delta)

        # Adjust labor-driven cost proxies for wage inflation
        adjusted_operator_hours = spec.operator_hours_per_year * (1 + labor_esc)
        adjusted_maint_hours = spec.maintenance_labor_hours_per_event * (1 + labor_esc)

        # Adjust disruption probability
        adj_disruption = disruption_prob if disruption_prob is not None else spec.disruption_probability

        perturbed = replace(
            spec,
            base_price_local=adjusted_price,
            energy_kwh_per_year=adjusted_energy,
            spare_unit_price_local=adjusted_spare,
            operator_hours_per_year=adjusted_operator_hours,
            maintenance_labor_hours_per_event=adjusted_maint_hours,
            disruption_probability=adj_disruption,
        )
        return perturbed

    def run_single_scenario(
        self,
        spec: EquipmentSpec,
        scenario_name: str,
        run_meta: RunMetadata | None = None,
    ) -> dict[str, Any]:
        """Run TCO computation under a single named scenario."""
        meta = run_meta or RunMetadata(scenario=scenario_name)
        scenario = self.scenarios.get(scenario_name)
        if scenario is None:
            raise ValueError(f"Unknown scenario: {scenario_name}. Available: {list(self.scenarios.keys())}")

        adjusted_spec = self._apply_scenario(spec, scenario)
        engine = TCOEngine()
        result = engine.compute(adjusted_spec, meta)

        return {
            "scenario": scenario_name,
            "scenario_label": scenario.get("label", scenario_name),
            "equipment_id": spec.equipment_id,
            "region": spec.region,
            "total_tco": result.total_tco,
            "annualized_tco": result.annualized_tco,
            "acquisition_cost": result.acquisition_cost,
            "operating_cost": result.operating_cost,
            "maintenance_cost": result.maintenance_cost,
            "risk_resilience_cost": result.risk_resilience_cost,
            "scenario_params": scenario,
            "run_metadata": result.run_metadata,
            "evidence_class": "simulated_estimate",
        }

    def run_all_scenarios(
        self,
        spec: EquipmentSpec,
        run_meta: RunMetadata | None = None,
    ) -> pd.DataFrame:
        """Run TCO under all predefined scenarios for one equipment spec."""
        meta = run_meta or RunMetadata(scenario="all_scenarios")
        results = []
        for name in self.scenarios:
            r = self.run_single_scenario(spec, name, meta)
            results.append(r)

        df = pd.DataFrame(results)
        df["tco_delta_vs_base"] = df["total_tco"] - df.loc[df["scenario"] == "base", "total_tco"].values[0]
        df["tco_delta_pct"] = (df["tco_delta_vs_base"] / df.loc[df["scenario"] == "base", "total_tco"].values[0]) * 100

        audit.record("scenario_analysis_complete", {
            "equipment_id": spec.equipment_id,
            "scenarios_run": len(results),
            "base_tco": round(df.loc[df["scenario"] == "base", "total_tco"].values[0], 2),
            "worst_case_tco": round(df["total_tco"].max(), 2),
        }, run_id=meta.run_id)

        log.info("Scenario analysis complete: %s — %d scenarios", spec.name, len(results))
        return df

    def run_comparative_scenarios(
        self,
        specs: list[EquipmentSpec],
        scenario_names: list[str] | None = None,
        run_meta: RunMetadata | None = None,
    ) -> pd.DataFrame:
        """Run selected scenarios across multiple equipment specs for cross-comparison."""
        meta = run_meta or RunMetadata(scenario="comparative")
        scenario_names = scenario_names or list(self.scenarios.keys())

        all_results = []
        for spec in specs:
            for name in scenario_names:
                if name in self.scenarios:
                    r = self.run_single_scenario(spec, name, meta)
                    all_results.append(r)

        df = pd.DataFrame(all_results)
        return df.sort_values(["scenario", "total_tco"])

    def sensitivity_analysis(
        self,
        spec: EquipmentSpec,
        parameter: str,
        values: list[float],
        run_meta: RunMetadata | None = None,
    ) -> pd.DataFrame:
        """One-at-a-time sensitivity analysis on a single parameter."""
        meta = run_meta or RunMetadata(scenario=f"sensitivity_{parameter}")
        engine = TCOEngine()
        results = []

        for val in values:
            adjusted = replace(spec, **{parameter: val})
            result = engine.compute(adjusted, meta)
            results.append({
                "parameter": parameter,
                "value": val,
                "total_tco": result.total_tco,
                "annualized_tco": result.annualized_tco,
            })

        df = pd.DataFrame(results)
        base_tco = df.iloc[len(df) // 2]["total_tco"]
        df["tco_delta"] = df["total_tco"] - base_tco
        df["tco_delta_pct"] = (df["tco_delta"] / base_tco) * 100

        log.info("Sensitivity analysis: %s on %s — %d points", spec.name, parameter, len(values))
        return df
