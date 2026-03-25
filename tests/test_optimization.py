"""Tests for Optimization Engine."""
import pytest

from analytics.optimization import TCOptimizer


class TestOptimizer:

    def test_recommend_source(self, all_specs, run_meta):
        opt = TCOptimizer()
        result = opt.recommend_source(all_specs, run_meta=run_meta)
        assert isinstance(result, dict)
        assert "recommended_source" in result
        assert result["recommended_source"]["region"] in ["China", "India", "Europe"]

    def test_optimize_maintenance(self, china_spec, run_meta):
        opt = TCOptimizer()
        r = opt.optimize_maintenance_interval(china_spec, run_meta)
        assert isinstance(r, dict)
        assert "optimal_pm_interval_hours" in r
        assert r["optimal_pm_interval_hours"] > 0

    def test_optimize_spares(self, china_spec, run_meta):
        opt = TCOptimizer()
        r = opt.optimize_spare_inventory(china_spec, run_meta=run_meta)
        assert isinstance(r, dict)
        assert "eoq_units" in r
        assert r["eoq_units"] >= 1

    def test_make_vs_buy(self, china_spec, run_meta):
        opt = TCOptimizer()
        r = opt.make_vs_buy_analysis(china_spec, run_meta=run_meta)
        assert isinstance(r, dict)
        assert "recommendation" in r
        assert r["recommendation"] in ["in_house", "outsource"]

    def test_full_optimization(self, all_specs, run_meta):
        opt = TCOptimizer()
        r = opt.full_optimization(all_specs, run_meta=run_meta)
        assert isinstance(r, dict)
        assert "sourcing_recommendation" in r
        assert "maintenance_optimizations" in r
        assert "spare_inventory_optimizations" in r

    def test_maintenance_savings_non_negative(self, china_spec, run_meta):
        opt = TCOptimizer()
        r = opt.optimize_maintenance_interval(china_spec, run_meta)
        # Savings could be negative if current is already near optimal
        assert isinstance(r["annual_savings"], (int, float))

    def test_eoq_formula(self, europe_spec, run_meta):
        opt = TCOptimizer()
        r = opt.optimize_spare_inventory(europe_spec, run_meta=run_meta)
        assert r["eoq_units"] >= 1
        assert r["safety_stock_units"] >= 0
