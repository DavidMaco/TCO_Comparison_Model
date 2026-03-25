"""Tests for Supplier Scorecard."""
import pandas as pd
import pytest

from analytics.supplier_scorecard import SupplierScorecard


class TestSupplierScorecard:

    def test_score_single(self, demo_suppliers):
        sc = SupplierScorecard()
        result = sc.score_supplier(demo_suppliers[0])
        assert isinstance(result, dict)
        assert "composite_score" in result
        assert 0 <= result["composite_score"] <= 1

    def test_score_multiple(self, demo_suppliers):
        sc = SupplierScorecard()
        df = sc.score_multiple(demo_suppliers)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 3
        # All composite scores between 0 and 1
        for _, r in df.iterrows():
            assert 0 <= r["composite_score"] <= 1

    def test_ranking_order(self, demo_suppliers):
        sc = SupplierScorecard()
        df = sc.score_multiple(demo_suppliers)
        eu_rows = df[df["region"] == "Europe"]
        assert not eu_rows.empty
        eu_score = eu_rows.iloc[0]["composite_score"]
        assert eu_score > 0.5

    def test_generate_report(self, demo_suppliers):
        sc = SupplierScorecard()
        report = sc.generate_report(demo_suppliers)
        assert isinstance(report, dict)
        assert "individual_scores" in report
        assert "regional_summary" in report

    def test_regional_comparison(self, demo_suppliers):
        sc = SupplierScorecard()
        regional = sc.regional_comparison(demo_suppliers)
        assert isinstance(regional, pd.DataFrame)
        assert len(regional) == 3  # 3 regions

    def test_normalized_dimensions(self, demo_suppliers):
        sc = SupplierScorecard()
        df = sc.score_multiple(demo_suppliers)
        for _, r in df.iterrows():
            for key in ["quality_index_normalized", "delivery_reliability_normalized"]:
                if key in r.index:
                    assert 0 <= r[key] <= 1
