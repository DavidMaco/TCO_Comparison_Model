"""
TCO Comparison Model — Finance / CFO View
NPV, IRR, lifecycle cashflow, working capital, EBITDA impact.
"""
import os

os.environ.setdefault("TCO_DEV_MODE", "true")

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import config
from analytics.financial_translator import FinancialTranslator
from analytics.tco_engine import EquipmentSpec, TCOEngine
from utils.demo_data import get_demo_specs
from utils.run_metadata import RunMetadata

st.set_page_config(page_title="TCO · Finance View", page_icon="💵", layout="wide")
st.title("💵 Finance / CFO View")

specs = get_demo_specs()

engine = TCOEngine()
fin = FinancialTranslator()
meta = RunMetadata(scenario="finance_dashboard")

# ─── Financial Comparison ────────────────────────────────────────────
st.markdown("### 📊 Financial Comparison")

tco_results = [engine.compute(s, meta) for s in specs]
fin_df = fin.compare_financial(specs, tco_results, meta)

col1, col2, col3 = st.columns(3)
for i, (_, row) in enumerate(fin_df.iterrows()):
    with [col1, col2, col3][i]:
        st.metric(f"{row['region']} NPV", f"${row['npv']:,.0f}")
        irr_str = f"{row['irr']:.2%}" if row['irr'] else "N/A"
        st.metric("IRR", irr_str)

st.dataframe(fin_df[["region", "supplier", "total_tco", "npv", "irr", "annualized_tco",
                      "payback_years", "working_capital_tied"]].round(2), use_container_width=True)

# ─── Lifecycle Cashflow ──────────────────────────────────────────────
st.markdown("### 💸 Lifecycle Cashflow")
selected_region = st.selectbox("Select Region", ["China", "India", "Europe"])
idx = {"China": 0, "India": 1, "Europe": 2}[selected_region]

cashflows = fin.lifecycle_cashflow(specs[idx], tco_results[idx])

fig = go.Figure()
fig.add_trace(go.Bar(x=cashflows["year"], y=cashflows["net_cashflow"], name="Annual Cashflow",
                     marker_color=["#e74c3c" if v < 0 else "#2ecc71" for v in cashflows["net_cashflow"]]))
fig.add_trace(go.Scatter(x=cashflows["year"], y=cashflows["cumulative_cashflow"], name="Cumulative",
                         line=dict(color="#3498db", width=3)))
fig.update_layout(title=f"Lifecycle Cashflow — {selected_region}",
                  xaxis_title="Year", yaxis_title="USD", yaxis_tickformat="$,.0f")
st.plotly_chart(fig, use_container_width=True)

# ─── Working Capital ─────────────────────────────────────────────────
st.markdown("### 🏦 Working Capital Impact")
wc_data = []
for i, spec in enumerate(specs):
    wc = fin.compute_working_capital_impact(spec, tco_results[i])
    wc["region"] = spec.region
    wc_data.append(wc)
wc_df = pd.DataFrame(wc_data)
st.dataframe(wc_df.round(2), use_container_width=True)

st.caption("⚠️ Evidence class: **simulated_estimate** — NPV/IRR based on modeled assumptions, not audited financials.")
