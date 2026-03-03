"""
TCO Comparison Model — Monte Carlo Simulation Engine
Stochastic uncertainty quantification for TCO estimates.
Propagates distributions through all cost layers to produce
confidence intervals for total lifecycle cost.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

import config
from analytics.tco_engine import TCOEngine, EquipmentSpec, TCOResult
from utils.logging_config import get_logger, AuditLogger
from utils.run_metadata import RunMetadata

log = get_logger("monte_carlo")
audit = AuditLogger()


# ─── Default Uncertainty Parameters ─────────────────────────────────

DEFAULT_UNCERTAINTY = {
    "base_price_sigma_pct": 0.08,       # 8% price volatility
    "energy_cost_sigma_pct": 0.15,      # 15% energy price volatility
    "fx_rate_sigma_pct": None,           # None = use config.FX_VOLATILITIES
    "mtbf_sigma_pct": 0.20,             # 20% MTBF uncertainty
    "mttr_sigma_pct": 0.25,             # 25% MTTR uncertainty
    "lead_time_sigma_pct": 0.30,        # 30% lead time variability
    "disruption_prob_sigma_pct": 0.40,  # 40% disruption probability uncertainty
    "throughput_sigma_pct": 0.10,       # 10% throughput variability
    "spare_price_sigma_pct": 0.12,      # 12% spare part price volatility
}


def _perturb(base: float, sigma_pct: float, rng: np.random.Generator, floor: float = 0.0) -> float:
    """Apply lognormal perturbation to a base value."""
    if base <= 0 or sigma_pct <= 0:
        return base
    sigma = abs(base * sigma_pct)
    # Use lognormal to avoid negative values
    log_mean = np.log(base) - 0.5 * (sigma_pct ** 2)
    log_sigma = sigma_pct
    val = rng.lognormal(log_mean, log_sigma)
    return max(val, floor)


class MonteCarloSimulator:
    """
    Monte Carlo simulation over TCO inputs.
    Perturbs key input parameters stochastically, computes TCO for each trial,
    and aggregates into distributional outputs with confidence intervals.
    """

    def __init__(
        self,
        n_simulations: int = config.MC_DEFAULT_PATHS,
        seed: int = config.RANDOM_SEED,
        uncertainty_params: dict[str, float] | None = None,
    ):
        self.n_simulations = min(n_simulations, config.MC_MAX_PATHS)
        self.seed = seed
        self.uncertainty = {**DEFAULT_UNCERTAINTY, **(uncertainty_params or {})}

    def _perturb_spec(self, spec: EquipmentSpec, rng: np.random.Generator) -> EquipmentSpec:
        """Create a perturbed copy of the equipment specification."""
        from dataclasses import replace

        currency = config.REGION_CURRENCIES.get(spec.region, spec.currency)
        fx_sigma = self.uncertainty.get("fx_rate_sigma_pct") or config.FX_VOLATILITIES.get(currency, 0.10)

        perturbed = replace(
            spec,
            base_price_local=_perturb(spec.base_price_local, self.uncertainty["base_price_sigma_pct"], rng),
            energy_kwh_per_year=_perturb(spec.energy_kwh_per_year, self.uncertainty["energy_cost_sigma_pct"], rng),
            mtbf_hours=_perturb(spec.mtbf_hours, self.uncertainty["mtbf_sigma_pct"], rng, floor=100),
            mttr_hours=_perturb(spec.mttr_hours, self.uncertainty["mttr_sigma_pct"], rng, floor=1),
            lead_time_days=_perturb(spec.lead_time_days, self.uncertainty["lead_time_sigma_pct"], rng, floor=1),
            actual_throughput_per_hour=min(
                spec.rated_throughput_per_hour,
                _perturb(spec.actual_throughput_per_hour, self.uncertainty["throughput_sigma_pct"], rng),
            ),
            spare_unit_price_local=_perturb(
                spec.spare_unit_price_local, self.uncertainty["spare_price_sigma_pct"], rng
            ),
        )

        # Perturb disruption probability separately (bounded 0-1)
        if spec.disruption_probability is not None:
            dp = _perturb(max(spec.disruption_probability, 0.01), self.uncertainty["disruption_prob_sigma_pct"], rng)
            perturbed = replace(perturbed, disruption_probability=min(dp, 1.0))

        return perturbed

    def simulate_single(
        self,
        spec: EquipmentSpec,
        run_meta: RunMetadata | None = None,
        *,
        include_raw_draws: bool = False,
    ) -> dict[str, Any]:
        """
        Run Monte Carlo simulation for a single equipment spec.
        Returns distributional statistics of the TCO.

        Parameters
        ----------
        include_raw_draws : bool
            When *True*, the returned dict includes a ``raw_draws`` key with
            the full list of TCO draws.  Defaults to *False* to conserve memory.
        """
        meta = run_meta or RunMetadata(scenario="monte_carlo")
        rng = np.random.default_rng(self.seed)
        engine = TCOEngine()

        tco_draws = np.zeros(self.n_simulations)
        layer_draws = {
            "acquisition": np.zeros(self.n_simulations),
            "installation": np.zeros(self.n_simulations),
            "operating": np.zeros(self.n_simulations),
            "maintenance": np.zeros(self.n_simulations),
            "spares_logistics": np.zeros(self.n_simulations),
            "risk_resilience": np.zeros(self.n_simulations),
            "utilization": np.zeros(self.n_simulations),
            "residual": np.zeros(self.n_simulations),
        }

        for i in range(self.n_simulations):
            perturbed = self._perturb_spec(spec, rng)
            result = engine.compute(perturbed)
            tco_draws[i] = result.total_tco
            layer_draws["acquisition"][i] = result.acquisition_cost
            layer_draws["installation"][i] = result.installation_cost
            layer_draws["operating"][i] = result.operating_cost
            layer_draws["maintenance"][i] = result.maintenance_cost
            layer_draws["spares_logistics"][i] = result.spares_logistics_cost
            layer_draws["risk_resilience"][i] = result.risk_resilience_cost
            layer_draws["utilization"][i] = result.utilization_impact_cost
            layer_draws["residual"][i] = result.residual_value

        # Compute statistics
        percentiles = [5, 10, 25, 50, 75, 90, 95]
        stats = {
            "equipment_id": spec.equipment_id,
            "region": spec.region,
            "n_simulations": self.n_simulations,
            "seed": self.seed,
            "tco_mean": float(np.mean(tco_draws)),
            "tco_median": float(np.median(tco_draws)),
            "tco_std": float(np.std(tco_draws)),
            "tco_cv": float(np.std(tco_draws) / np.mean(tco_draws)) if np.mean(tco_draws) > 0 else 0,
            "tco_min": float(np.min(tco_draws)),
            "tco_max": float(np.max(tco_draws)),
        }
        for p in percentiles:
            stats[f"tco_p{p:02d}"] = float(np.percentile(tco_draws, p))

        # Layer-level statistics
        for layer, draws in layer_draws.items():
            stats[f"{layer}_mean"] = float(np.mean(draws))
            stats[f"{layer}_std"] = float(np.std(draws))
            stats[f"{layer}_p05"] = float(np.percentile(draws, 5))
            stats[f"{layer}_p95"] = float(np.percentile(draws, 95))

        # Sensitivity: rank layers by coefficient of variation
        layer_cv = {}
        for layer, draws in layer_draws.items():
            mean = np.mean(draws)
            layer_cv[layer] = float(np.std(draws) / mean) if mean > 0 else 0
        stats["layer_sensitivity_ranking"] = sorted(layer_cv.items(), key=lambda x: -x[1])

        stats["run_metadata"] = meta.seal({"equipment_id": spec.equipment_id, "n_simulations": self.n_simulations})
        stats["evidence_class"] = "simulated_estimate"
        if include_raw_draws:
            stats["raw_draws"] = tco_draws.tolist()

        audit.record("monte_carlo_completed", {
            "equipment_id": spec.equipment_id,
            "region": spec.region,
            "n_simulations": self.n_simulations,
            "tco_mean": round(stats["tco_mean"], 2),
            "tco_p05": round(stats["tco_p05"], 2),
            "tco_p95": round(stats["tco_p95"], 2),
        }, run_id=meta.run_id, evidence_class="simulated_estimate")

        log.info(
            "Monte Carlo complete: %s (%s) — mean=$%.0f [P5=$%.0f, P95=$%.0f] (%d sims)",
            spec.name, spec.region, stats["tco_mean"], stats["tco_p05"], stats["tco_p95"], self.n_simulations,
        )
        return stats

    def simulate_comparison(
        self, specs: list[EquipmentSpec], run_meta: RunMetadata | None = None
    ) -> pd.DataFrame:
        """Run Monte Carlo for multiple specs and return comparison DataFrame."""
        meta = run_meta or RunMetadata(scenario="monte_carlo_comparison")
        results = [self.simulate_single(spec, meta) for spec in specs]

        # Build comparison table (exclude raw draws)
        rows = [{k: v for k, v in r.items() if k != "raw_draws"} for r in results]
        df = pd.DataFrame(rows)
        df["tco_mean_rank"] = df["tco_mean"].rank(method="min").astype(int)
        df["risk_adjusted_rank"] = df["tco_p95"].rank(method="min").astype(int)
        return df.sort_values("tco_mean")
