"""Tests for the core TCO Engine."""
import pytest

from analytics.tco_engine import EquipmentSpec, TCOEngine, TCOResult


class TestTCOEngine:

    def test_compute_returns_result(self, china_spec, run_meta):
        engine = TCOEngine()
        result = engine.compute(china_spec, run_meta)
        assert isinstance(result, TCOResult)
        assert result.equipment_id == "TEST-CN-01"
        assert result.region == "China"

    def test_total_tco_positive(self, china_spec, run_meta):
        engine = TCOEngine()
        result = engine.compute(china_spec, run_meta)
        assert result.total_tco > 0

    def test_all_layers_non_negative(self, china_spec, run_meta):
        engine = TCOEngine()
        result = engine.compute(china_spec, run_meta)
        assert result.acquisition_cost >= 0
        assert result.installation_cost >= 0
        assert result.operating_cost >= 0
        assert result.maintenance_cost >= 0
        assert result.spares_logistics_cost >= 0
        assert result.risk_resilience_cost >= 0
        assert result.utilization_impact_cost >= 0

    def test_total_equals_sum_of_parts(self, china_spec, run_meta):
        engine = TCOEngine()
        r = engine.compute(china_spec, run_meta)
        expected = (r.acquisition_cost + r.installation_cost + r.operating_cost
                    + r.maintenance_cost + r.spares_logistics_cost + r.risk_resilience_cost
                    + r.utilization_impact_cost - r.residual_value + r.externalities_cost)
        assert abs(r.total_tco - expected) < 1.0  # within $1 rounding

    def test_annualized_tco(self, china_spec, run_meta):
        engine = TCOEngine()
        r = engine.compute(china_spec, run_meta)
        expected_annual = r.total_tco / china_spec.asset_life_years
        assert abs(r.annualized_tco - expected_annual) < 1.0

    def test_compare_returns_df(self, all_specs, run_meta):
        engine = TCOEngine()
        df = engine.compare(all_specs, run_meta)
        assert len(df) == 3
        assert "tco_rank" in df.columns
        assert df["tco_rank"].tolist() == [1, 2, 3]

    def test_evidence_class_set(self, china_spec, run_meta):
        engine = TCOEngine()
        r = engine.compute(china_spec, run_meta)
        assert r.evidence_class == "simulated_estimate"

    def test_different_regions_produce_different_tco(self, china_spec, india_spec, europe_spec, run_meta):
        engine = TCOEngine()
        r_cn = engine.compute(china_spec, run_meta)
        r_in = engine.compute(india_spec, run_meta)
        r_eu = engine.compute(europe_spec, run_meta)
        tcos = [r_cn.total_tco, r_in.total_tco, r_eu.total_tco]
        assert len(set(tcos)) == 3  # All distinct

    def test_zero_price_spec(self, run_meta):
        """Zero base price should still compute (edge case)."""
        spec = EquipmentSpec(
            equipment_id="ZERO-01", name="Zero", category="Test",
            region="China", supplier_id="S0", supplier_name="Zero Co",
            base_price_local=0.0, currency="CNY", asset_life_years=5,
        )
        engine = TCOEngine()
        r = engine.compute(spec, run_meta)
        assert r.total_tco >= 0

    def test_to_dict(self, china_spec, run_meta):
        engine = TCOEngine()
        r = engine.compute(china_spec, run_meta)
        d = r.to_dict()
        assert isinstance(d, dict)
        assert "total_tco" in d
