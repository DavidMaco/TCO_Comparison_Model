"""Tests for Benchmarking Engine."""
import pytest

from analytics.benchmarking import INDUSTRY_FAILURE_RATES, BenchmarkEngine


class TestBenchmarkEngine:

    def test_benchmark_equipment(self, run_meta):
        bench = BenchmarkEngine()
        data = [{"equipment_id": "E1", "category": "CNC Machine", "region": "China",
                 "mtbf_hours": 6000, "mttr_hours": 18}]
        report = bench.full_benchmark_report(data, run_meta)
        assert isinstance(report, dict)

    def test_failure_rates_data(self):
        assert "CNC Machine" in INDUSTRY_FAILURE_RATES
        assert INDUSTRY_FAILURE_RATES["CNC Machine"]["mtbf_hours"] == 6000

    def test_multiple_categories(self, run_meta):
        bench = BenchmarkEngine()
        data = [
            {"equipment_id": "E1", "category": "CNC Machine", "region": "China", "mtbf_hours": 6000, "mttr_hours": 18},
            {"equipment_id": "E2", "category": "Compressor", "region": "India", "mtbf_hours": 8000, "mttr_hours": 12},
        ]
        report = bench.full_benchmark_report(data, run_meta)
        assert isinstance(report, dict)

    def test_unknown_category_handled(self, run_meta):
        bench = BenchmarkEngine()
        data = [{"equipment_id": "E1", "category": "Unknown Widget", "region": "Europe",
                 "mtbf_hours": 5000, "mttr_hours": 10}]
        # Should not raise
        report = bench.full_benchmark_report(data, run_meta)
        assert isinstance(report, dict)
