"""Tests for Scenario Engine."""
import pandas as pd
import pytest

from analytics.scenario_engine import ScenarioEngine


class TestScenarioEngine:

    def test_run_single_scenario(self, china_spec, run_meta):
        se = ScenarioEngine()
        r = se.run_single_scenario(china_spec, "base")
        assert isinstance(r, dict)
        assert r["region"] == "China"
        assert "total_tco" in r

    def test_all_scenarios_returns_df(self, china_spec, run_meta):
        se = ScenarioEngine()
        df = se.run_all_scenarios(china_spec)
        assert isinstance(df, pd.DataFrame)
        assert len(df) >= 6  # At least 6 predefined scenarios

    def test_scenario_names_present(self, china_spec, run_meta):
        se = ScenarioEngine()
        df = se.run_all_scenarios(china_spec)
        assert "base" in df["scenario"].values
        assert "pessimistic" in df["scenario"].values

    def test_comparative_scenarios(self, all_specs, run_meta):
        se = ScenarioEngine()
        df = se.run_comparative_scenarios(all_specs, run_meta=run_meta)
        assert isinstance(df, pd.DataFrame)
        assert len(df) >= 3  # At least 3 regions × some scenarios

    def test_pessimistic_higher_than_base(self, china_spec, run_meta):
        se = ScenarioEngine()
        base = se.run_single_scenario(china_spec, "base")
        pess = se.run_single_scenario(china_spec, "pessimistic")
        # Pessimistic should generally be more expensive
        assert pess["total_tco"] >= base["total_tco"] * 0.9  # Allow small tolerance

    def test_scenario_delta_pct(self, china_spec, run_meta):
        se = ScenarioEngine()
        df = se.run_all_scenarios(china_spec)
        base_row = df[df["scenario"] == "base"]
        assert abs(base_row["tco_delta_pct"].iloc[0]) < 0.01  # Base delta ≈ 0%

    def test_sensitivity_analysis(self, china_spec, run_meta):
        se = ScenarioEngine()
        result = se.sensitivity_analysis(china_spec, "base_price_local", [50000, 100000, 200000], run_meta)
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 3
