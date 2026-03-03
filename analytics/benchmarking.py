"""
TCO Comparison Model — Benchmarking Engine
Embeds global benchmarks for failure rates, regional costs,
energy curves, and logistics costs to ground assumptions.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

import config
from utils.logging_config import get_logger
from utils.run_metadata import RunMetadata

log = get_logger("benchmarking")


# ─── Embedded Benchmark Data ─────────────────────────────────────────

INDUSTRY_FAILURE_RATES = {
    "CNC Machine": {"mtbf_hours": 6000, "mttr_hours": 18, "source": "ISO 12100 / Industry surveys"},
    "Compressor": {"mtbf_hours": 8000, "mttr_hours": 12, "source": "API 618 / OEM data"},
    "Pump": {"mtbf_hours": 10000, "mttr_hours": 8, "source": "API 610 / Reliability databases"},
    "Conveyor System": {"mtbf_hours": 12000, "mttr_hours": 6, "source": "CEMA standards"},
    "Packaging Machine": {"mtbf_hours": 5000, "mttr_hours": 16, "source": "PMMI surveys"},
    "Injection Molder": {"mtbf_hours": 7000, "mttr_hours": 20, "source": "SPI data"},
    "Heat Exchanger": {"mtbf_hours": 15000, "mttr_hours": 24, "source": "TEMA standards"},
    "Electrical Panel": {"mtbf_hours": 20000, "mttr_hours": 4, "source": "IEEE reliability data"},
    "Spare Part (Generic)": {"mtbf_hours": None, "mttr_hours": 2, "source": "General estimate"},
}

REGIONAL_COST_BENCHMARKS = {
    "China": {
        "labor_rate_usd_hr": {"p25": 5.0, "p50": 8.5, "p75": 14.0},
        "energy_usd_kwh": {"p25": 0.06, "p50": 0.08, "p75": 0.11},
        "logistics_premium_pct": 1.15,  # 15% premium for cross-border logistics
    },
    "India": {
        "labor_rate_usd_hr": {"p25": 2.5, "p50": 4.2, "p75": 8.0},
        "energy_usd_kwh": {"p25": 0.07, "p50": 0.09, "p75": 0.12},
        "logistics_premium_pct": 1.20,
    },
    "Europe": {
        "labor_rate_usd_hr": {"p25": 25.0, "p50": 38.0, "p75": 55.0},
        "energy_usd_kwh": {"p25": 0.16, "p50": 0.22, "p75": 0.32},
        "logistics_premium_pct": 1.05,
    },
}

ENERGY_ESCALATION_CURVES = {
    "low": 0.02,
    "base": 0.04,
    "high": 0.08,
    "extreme": 0.12,
}


class BenchmarkEngine:
    """
    Compare equipment/supplier parameters against industry benchmarks.
    Flags outliers and provides credibility assessment.
    """

    def benchmark_equipment(self, category: str, params: dict) -> dict[str, Any]:
        """Compare equipment parameters against industry standards."""
        benchmark = INDUSTRY_FAILURE_RATES.get(category, INDUSTRY_FAILURE_RATES.get("Spare Part (Generic)", {}))

        findings = []
        if benchmark.get("mtbf_hours") and params.get("mtbf_hours"):
            ratio = params["mtbf_hours"] / benchmark["mtbf_hours"]
            if ratio < 0.7:
                findings.append({"param": "mtbf_hours", "status": "below_benchmark", "ratio": round(ratio, 2), "severity": "high"})
            elif ratio > 1.5:
                findings.append({"param": "mtbf_hours", "status": "above_benchmark", "ratio": round(ratio, 2), "severity": "info"})
            else:
                findings.append({"param": "mtbf_hours", "status": "within_benchmark", "ratio": round(ratio, 2), "severity": "ok"})

        if benchmark.get("mttr_hours") and params.get("mttr_hours"):
            ratio = params["mttr_hours"] / benchmark["mttr_hours"]
            if ratio > 1.5:
                findings.append({"param": "mttr_hours", "status": "above_benchmark", "ratio": round(ratio, 2), "severity": "warning"})
            else:
                findings.append({"param": "mttr_hours", "status": "within_benchmark", "ratio": round(ratio, 2), "severity": "ok"})

        return {
            "category": category,
            "benchmark_source": benchmark.get("source", "N/A"),
            "benchmark_values": benchmark,
            "input_values": params,
            "findings": findings,
        }

    def benchmark_regional_costs(self, region: str, labor_rate: float, energy_rate: float) -> dict[str, Any]:
        """Compare regional costs against benchmarks."""
        bench = REGIONAL_COST_BENCHMARKS.get(region, {})
        findings = []

        if bench.get("labor_rate_usd_hr"):
            lb = bench["labor_rate_usd_hr"]
            if labor_rate < lb["p25"]:
                findings.append({"param": "labor_rate", "status": "below_p25", "value": labor_rate, "benchmark_p50": lb["p50"]})
            elif labor_rate > lb["p75"]:
                findings.append({"param": "labor_rate", "status": "above_p75", "value": labor_rate, "benchmark_p50": lb["p50"]})

        if bench.get("energy_usd_kwh"):
            eb = bench["energy_usd_kwh"]
            if energy_rate < eb["p25"]:
                findings.append({"param": "energy_rate", "status": "below_p25", "value": energy_rate, "benchmark_p50": eb["p50"]})
            elif energy_rate > eb["p75"]:
                findings.append({"param": "energy_rate", "status": "above_p75", "value": energy_rate, "benchmark_p50": eb["p50"]})

        return {
            "region": region,
            "benchmarks": bench,
            "input_values": {"labor_rate": labor_rate, "energy_rate": energy_rate},
            "findings": findings,
        }

    def full_benchmark_report(
        self,
        equipment_data: list[dict],
        run_meta: RunMetadata | None = None,
    ) -> dict[str, Any]:
        """Generate complete benchmark report for all equipment."""
        meta = run_meta or RunMetadata(scenario="benchmarking")

        equipment_benchmarks = []
        for eq in equipment_data:
            eb = self.benchmark_equipment(
                eq.get("category", "Spare Part (Generic)"),
                {"mtbf_hours": eq.get("mtbf_hours"), "mttr_hours": eq.get("mttr_hours")},
            )
            eb["equipment_id"] = eq.get("equipment_id")
            eb["region"] = eq.get("region")
            equipment_benchmarks.append(eb)

        regional_benchmarks = []
        for region in config.REGIONS:
            rb = self.benchmark_regional_costs(
                region,
                config.REGIONAL_LABOR_RATES.get(region, 20),
                config.REGIONAL_ENERGY_COSTS.get(region, 0.15),
            )
            regional_benchmarks.append(rb)

        total_findings = sum(len(eb["findings"]) for eb in equipment_benchmarks)
        high_severity = sum(
            1 for eb in equipment_benchmarks
            for f in eb["findings"] if f.get("severity") == "high"
        )

        report = {
            "equipment_benchmarks": equipment_benchmarks,
            "regional_benchmarks": regional_benchmarks,
            "summary": {
                "total_checks": total_findings,
                "high_severity_flags": high_severity,
                "benchmark_sources": list(set(
                    eb["benchmark_source"] for eb in equipment_benchmarks if eb.get("benchmark_source")
                )),
            },
            "evidence_class": "reference_benchmark",
            "run_metadata": meta.seal({"n_equipment": len(equipment_data)}),
        }

        log.info("Benchmark report: %d equipment items, %d findings (%d high severity)",
                 len(equipment_data), total_findings, high_severity)
        return report
