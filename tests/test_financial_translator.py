"""Tests for Financial Translator."""
import pytest
import pandas as pd
from analytics.tco_engine import TCOEngine
from analytics.financial_translator import FinancialTranslator


class TestFinancialTranslator:

    def _get_tco(self, spec, meta):
        return TCOEngine().compute(spec, meta)

    def test_npv_returns_float(self, china_spec, run_meta):
        fin = FinancialTranslator()
        tco = self._get_tco(china_spec, run_meta)
        cashflows = fin.lifecycle_cashflow(china_spec, tco)
        npv = fin.compute_npv(cashflows)
        assert isinstance(npv, float)

    def test_npv_negative_for_cost(self, china_spec, run_meta):
        fin = FinancialTranslator()
        tco = self._get_tco(china_spec, run_meta)
        cashflows = fin.lifecycle_cashflow(china_spec, tco)
        npv = fin.compute_npv(cashflows)
        assert npv < 0  # Pure cost asset should have negative NPV

    def test_lifecycle_cashflow_df(self, china_spec, run_meta):
        fin = FinancialTranslator()
        tco = self._get_tco(china_spec, run_meta)
        cf = fin.lifecycle_cashflow(china_spec, tco)
        assert isinstance(cf, pd.DataFrame)
        assert len(cf) == china_spec.asset_life_years + 1  # Year 0 through N

    def test_irr_returns_value(self, china_spec, run_meta):
        fin = FinancialTranslator()
        tco = self._get_tco(china_spec, run_meta)
        cashflows = fin.lifecycle_cashflow(china_spec, tco)
        irr = fin.compute_irr(cashflows)
        # IRR may be None if no positive cashflow — acceptable for pure cost
        assert irr is None or isinstance(irr, float)

    def test_ebitda_impact(self, china_spec, run_meta):
        fin = FinancialTranslator()
        tco = self._get_tco(china_spec, run_meta)
        ebitda = fin.compute_ebitda_impact(china_spec, tco)
        assert isinstance(ebitda, dict)
        assert "annual_depreciation_usd" in ebitda
        # Depreciation should equal acquisition / asset_life
        expected_dep = tco.acquisition_cost / china_spec.asset_life_years
        assert abs(ebitda["annual_depreciation_usd"] - expected_dep) < 1.0

    def test_working_capital(self, china_spec, run_meta):
        fin = FinancialTranslator()
        tco = self._get_tco(china_spec, run_meta)
        wc = fin.compute_working_capital_impact(china_spec, tco)
        assert isinstance(wc, dict)

    def test_full_financial_analysis(self, china_spec, run_meta):
        fin = FinancialTranslator()
        tco = self._get_tco(china_spec, run_meta)
        analysis = fin.full_financial_analysis(china_spec, tco, run_meta)
        assert isinstance(analysis, dict)
        assert "npv_usd" in analysis
        assert "total_tco_usd" in analysis

    def test_compare_financial(self, all_specs, run_meta):
        engine = TCOEngine()
        fin = FinancialTranslator()
        tco_results = [engine.compute(s, run_meta) for s in all_specs]
        df = fin.compare_financial(all_specs, tco_results, run_meta)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 3
