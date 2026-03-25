"""
TCO Comparison Model — Run Pipeline
Master orchestrator: generates data → runs analytics → persists results.
"""
import os

os.environ.setdefault("TCO_DEV_MODE", "true")

import json
import time
from datetime import datetime
from pathlib import Path

import pandas as pd

import config
from analytics.benchmarking import BenchmarkEngine
from analytics.financial_translator import FinancialTranslator
from analytics.monte_carlo import MonteCarloSimulator
from analytics.optimization import TCOptimizer
from analytics.scenario_engine import ScenarioEngine
from analytics.supplier_scorecard import SupplierScorecard
from analytics.tco_engine import EquipmentSpec, TCOEngine
from data_ingestion.loader import load_assumptions_json, load_equipment_csv, load_supplier_csv
from utils.logging_config import AuditLogger, get_logger
from utils.run_metadata import RunMetadata, generate_run_id

log = get_logger("pipeline")
audit = AuditLogger()

REPORTS_DIR = Path(__file__).parent / "reports"
SAMPLE_DATA_DIR = Path(__file__).parent / "sample_data"


def ensure_sample_data():
    """Generate sample data if not present."""
    if not SAMPLE_DATA_DIR.exists() or not (SAMPLE_DATA_DIR / "equipment.csv").exists():
        log.info("Sample data not found — generating...")
        from generate_sample_data import main as gen_main
        gen_main()


def load_data():
    """Load equipment and supplier data from CSV."""
    eq_data = load_equipment_csv(str(SAMPLE_DATA_DIR / "equipment.csv"))
    sup_data = load_supplier_csv(str(SAMPLE_DATA_DIR / "suppliers.csv"))
    return eq_data, sup_data


# Note: load_equipment_csv() already returns list[EquipmentSpec] — no conversion needed.


def run_pipeline():
    """Execute the full analytics pipeline."""
    start = time.time()
    run_id = generate_run_id()
    meta = RunMetadata(scenario="full_pipeline", run_id=run_id)

    log.info(f"{'='*60}")
    log.info(f"TCO Comparison Model Pipeline — Run {run_id}")
    log.info(f"{'='*60}")

    # ─── Step 1: Data ────────────────────────────────────────────────
    log.info("[1/7] Loading data...")
    ensure_sample_data()
    specs, sup_data = load_data()
    log.info(f"  Loaded {len(specs)} equipment specs, {len(sup_data)} suppliers")

    # ─── Step 2: TCO Engine ──────────────────────────────────────────
    log.info("[2/7] Computing deterministic TCO...")
    engine = TCOEngine()
    tco_results = [engine.compute(s, meta) for s in specs]
    comparison_df = engine.compare(specs, meta)

    # ─── Step 3: Monte Carlo ─────────────────────────────────────────
    log.info("[3/7] Running Monte Carlo simulations (may take a moment)...")
    mc = MonteCarloSimulator(n_simulations=config.MC_DEFAULT_PATHS, seed=42)
    # Run MC for a representative subset (one per region × category)
    mc_specs = []
    seen = set()
    for s in specs:
        key = (s.region, s.category)
        if key not in seen:
            mc_specs.append(s)
            seen.add(key)
    mc_df = mc.simulate_comparison(mc_specs, meta)

    # ─── Step 4: Scenario Engine ─────────────────────────────────────
    log.info("[4/7] Running scenario analysis...")
    scenario_engine = ScenarioEngine()
    scenario_results = []
    for s in mc_specs:
        row = scenario_engine.run_all_scenarios(s)
        scenario_results.append(row)
    scenario_df = pd.concat(scenario_results, ignore_index=True) if scenario_results else pd.DataFrame()

    # ─── Step 5: Financial Translation ───────────────────────────────
    log.info("[5/7] Translating to financial metrics...")
    fin = FinancialTranslator()
    fin_analyses = []
    for s, r in zip(specs, tco_results):
        fa = fin.full_financial_analysis(s, r, meta)
        fin_analyses.append(fa)
    fin_df = pd.DataFrame(fin_analyses)

    # ─── Step 6: Supplier Scorecard ──────────────────────────────────
    log.info("[6/7] Scoring suppliers...")
    scorecard = SupplierScorecard()
    report = scorecard.generate_report(sup_data)
    scored_suppliers = pd.DataFrame(report["individual_scores"])

    # ─── Step 7: Optimization ────────────────────────────────────────
    log.info("[7/7] Running optimization engine...")
    optimizer = TCOptimizer()
    # Source recommendation for every unique (region, category) group
    opt_results = []
    for key, group_specs in _group_specs(specs).items():
        if len(group_specs) >= 2:
            r = optimizer.recommend_source(group_specs, run_meta=meta)
            opt_results.append(r)

    # ─── Persist Results ─────────────────────────────────────────────
    REPORTS_DIR.mkdir(exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

    comparison_df.to_csv(REPORTS_DIR / f"tco_comparison_{ts}.csv", index=False)
    mc_df.to_csv(REPORTS_DIR / f"monte_carlo_summary_{ts}.csv", index=False)
    scenario_df.to_csv(REPORTS_DIR / f"scenario_analysis_{ts}.csv", index=False)
    fin_df.to_csv(REPORTS_DIR / f"financial_analysis_{ts}.csv", index=False)
    scored_suppliers.to_csv(REPORTS_DIR / f"supplier_scorecard_{ts}.csv", index=False)

    if opt_results:
        with open(REPORTS_DIR / f"optimization_{ts}.json", "w") as f:
            json.dump(opt_results, f, indent=2, default=str)

    elapsed = time.time() - start
    log.info(f"{'='*60}")
    log.info(f"Pipeline complete in {elapsed:.1f}s")
    log.info(f"Reports saved to: {REPORTS_DIR}")
    log.info(f"{'='*60}")

    audit.record("pipeline_complete", {
        "run_id": run_id,
        "equipment_count": len(specs),
        "supplier_count": len(sup_data),
        "elapsed_seconds": round(elapsed, 2),
        "reports_dir": str(REPORTS_DIR),
    })


def _group_specs(specs: list[EquipmentSpec]) -> dict:
    """Group specs by category for optimization."""
    groups = {}
    for s in specs:
        key = s.category
        groups.setdefault(key, []).append(s)
    return groups


if __name__ == "__main__":
    run_pipeline()
