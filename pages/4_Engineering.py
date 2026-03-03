"""
TCO Comparison Model — Engineering View
Reliability curves, maintenance planning, performance benchmarks.
"""
import os
os.environ.setdefault("TCO_DEV_MODE", "true")

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

from analytics.tco_engine import TCOEngine, EquipmentSpec
from analytics.optimization import TCOptimizer
from analytics.benchmarking import BenchmarkEngine, INDUSTRY_FAILURE_RATES
from utils.run_metadata import RunMetadata
from utils.demo_data import get_demo_specs

st.set_page_config(page_title="TCO · Engineering View", page_icon="🔩", layout="wide")
st.title("🔩 Engineering View")

# ─── Demo specs ──────────────────────────────────────────────────────
specs = get_demo_specs()

# ─── Reliability Curves ─────────────────────────────────────────────
st.markdown("### 📉 Reliability Curves (Weibull)")
selected_region = st.selectbox("Region", ["China", "India", "Europe"])
idx = {"China": 0, "India": 1, "Europe": 2}[selected_region]
spec = specs[idx]

# Weibull reliability R(t) = exp(-(t/η)^β)
beta = 1.5  # shape
eta = spec.mtbf_hours  # scale ≈ MTBF
t = np.linspace(0, eta * 3, 500)
reliability = np.exp(-((t / eta) ** beta))

fig = go.Figure()
fig.add_trace(go.Scatter(x=t, y=reliability * 100, name="Reliability R(t)", line=dict(width=3)))
fig.add_hline(y=50, line_dash="dash", annotation_text="50% Reliability")
fig.add_vline(x=spec.mtbf_hours, line_dash="dash", annotation_text=f"MTBF={spec.mtbf_hours:,.0f}h")
fig.update_layout(title=f"Reliability Curve — {selected_region} ({spec.name})",
                  xaxis_title="Operating Hours", yaxis_title="Reliability (%)")
st.plotly_chart(fig, use_container_width=True)

# ─── Maintenance Optimization ───────────────────────────────────────
st.markdown("### 🔧 Maintenance Interval Optimization")
optimizer = TCOptimizer()
meta = RunMetadata(scenario="engineering_dashboard")

@st.cache_data(ttl=600)
def _run_maintenance_optimization(_specs):
    _optimizer = TCOptimizer()
    _meta = RunMetadata(scenario="engineering_dashboard")
    return [_optimizer.optimize_maintenance_interval(s, _meta) for s in _specs]

maint_results = _run_maintenance_optimization(specs)

maint_df = pd.DataFrame(maint_results)
st.dataframe(maint_df[["region", "current_pm_interval_hours", "optimal_pm_interval_hours",
                        "current_annual_maintenance_cost", "optimal_annual_maintenance_cost",
                        "annual_savings", "savings_pct"]].round(1), use_container_width=True)

# ─── Spare Inventory Optimization ───────────────────────────────────
st.markdown("### 📦 Spare Parts Inventory")

@st.cache_data(ttl=600)
def _run_spare_optimization(_specs):
    _optimizer = TCOptimizer()
    _meta = RunMetadata(scenario="engineering_dashboard")
    return [_optimizer.optimize_spare_inventory(s, run_meta=_meta) for s in _specs]

spare_results = _run_spare_optimization(specs)
spare_df = pd.DataFrame(spare_results)
st.dataframe(spare_df[["region", "eoq_units", "safety_stock_units", "reorder_point_units",
                        "optimal_annual_inventory_cost", "annual_savings"]].round(1), use_container_width=True)

# ─── Industry Benchmarks ────────────────────────────────────────────
st.markdown("### 📏 Industry Benchmarks")
bench = BenchmarkEngine()
bench_data = [{"equipment_id": s.equipment_id, "category": s.category, "region": s.region,
               "mtbf_hours": s.mtbf_hours, "mttr_hours": s.mttr_hours} for s in specs]
report = bench.full_benchmark_report(bench_data, meta)

bench_ref = pd.DataFrame([
    {"Category": k, "Benchmark MTBF (hrs)": v["mtbf_hours"], "Benchmark MTTR (hrs)": v["mttr_hours"], "Source": v["source"]}
    for k, v in INDUSTRY_FAILURE_RATES.items() if v["mtbf_hours"]
])
st.dataframe(bench_ref, use_container_width=True)

# ─── Make vs Buy ─────────────────────────────────────────────────────
st.markdown("### ⚖️ Make vs Buy — Maintenance Service")

@st.cache_data(ttl=600)
def _run_make_vs_buy(_specs):
    _optimizer = TCOptimizer()
    _meta = RunMetadata(scenario="engineering_dashboard")
    return [_optimizer.make_vs_buy_analysis(s, run_meta=_meta) for s in _specs]

mb_results = _run_make_vs_buy(specs)
mb_df = pd.DataFrame(mb_results)
st.dataframe(mb_df[["region", "in_house_annual_cost", "outsource_annual_cost",
                     "recommendation", "savings_with_recommendation"]].round(2), use_container_width=True)

st.caption("⚠️ Evidence class: **simulated_estimate** — reliability models use assumed Weibull parameters.")
