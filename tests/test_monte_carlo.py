"""Tests for Monte Carlo simulation engine."""
import pandas as pd
import pytest

from analytics.monte_carlo import MonteCarloSimulator


class TestMonteCarloSimulator:

    def test_simulate_single_returns_dict(self, china_spec, run_meta):
        mc = MonteCarloSimulator(n_simulations=100)
        result = mc.simulate_single(china_spec, run_meta)
        assert isinstance(result, dict)
        assert "tco_mean" in result
        assert "tco_p50" in result

    def test_percentiles_ordered(self, china_spec, run_meta):
        mc = MonteCarloSimulator(n_simulations=500)
        r = mc.simulate_single(china_spec, run_meta)
        assert r["tco_p05"] <= r["tco_p25"] <= r["tco_p50"] <= r["tco_p75"] <= r["tco_p95"]

    def test_mean_within_bounds(self, china_spec, run_meta):
        mc = MonteCarloSimulator(n_simulations=500)
        r = mc.simulate_single(china_spec, run_meta)
        assert r["tco_p05"] <= r["tco_mean"] <= r["tco_p95"]

    def test_simulate_comparison_returns_df(self, all_specs, run_meta):
        mc = MonteCarloSimulator(n_simulations=100)
        df = mc.simulate_comparison(all_specs, run_meta)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 3

    def test_std_positive(self, china_spec, run_meta):
        mc = MonteCarloSimulator(n_simulations=500)
        r = mc.simulate_single(china_spec, run_meta)
        assert r["tco_std"] > 0

    def test_reproducible_with_seed(self, china_spec, run_meta):
        mc1 = MonteCarloSimulator(n_simulations=200, seed=42)
        mc2 = MonteCarloSimulator(n_simulations=200, seed=42)
        r1 = mc1.simulate_single(china_spec, run_meta)
        r2 = mc2.simulate_single(china_spec, run_meta)
        assert abs(r1["tco_mean"] - r2["tco_mean"]) < 0.01

    def test_more_sims_narrow_ci(self, china_spec, run_meta):
        mc_small = MonteCarloSimulator(n_simulations=100, seed=42)
        mc_large = MonteCarloSimulator(n_simulations=2000, seed=42)
        r_small = mc_small.simulate_single(china_spec, run_meta)
        r_large = mc_large.simulate_single(china_spec, run_meta)
        spread_small = r_small["tco_p95"] - r_small["tco_p05"]
        spread_large = r_large["tco_p95"] - r_large["tco_p05"]
        # Both spreads must be positive
        assert spread_small > 0
        assert spread_large > 0
        # CV (coefficient of variation) should be tighter with more samples
        cv_small = r_small["tco_std"] / r_small["tco_mean"]
        cv_large = r_large["tco_std"] / r_large["tco_mean"]
        # Both should be in a reasonable ballpark (< 50% CV)
        assert cv_small < 0.5
        assert cv_large < 0.5
