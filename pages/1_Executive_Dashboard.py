"""
TCO Comparison Model — Executive Dashboard
Summary TCO comparison, risk heatmaps, financial impact overview.
"""
import os

os.environ.setdefault("TCO_DEV_MODE", "true")

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import config
from analytics.financial_translator import FinancialTranslator
from analytics.monte_carlo import MonteCarloSimulator
from analytics.scenario_engine import ScenarioEngine
from analytics.tco_engine import EquipmentSpec, TCOEngine
from utils.demo_data import get_demo_specs
from utils.run_metadata import RunMetadata

st.set_page_config(page_title="TCO · Executive Dashboard", page_icon="📊", layout="wide")
st.title("📊 Executive Dashboard")
st.markdown("**TCO comparison across China, India, and Europe with risk-adjusted financial metrics.**")


# ─── Demo Equipment Specs ────────────────────────────────────────────
@st.cache_data(ttl=600)
def _get_demo_specs():
    """Generate demo equipment specs for the three regions."""
    return get_demo_specs()


specs = _get_demo_specs()

# ─── TCO Comparison ─────────────────────────────────────────────────
st.markdown("### 💰 TCO Comparison")

engine = TCOEngine()
meta = RunMetadata(scenario="executive_dashboard")
comparison_df = engine.compare(specs, meta)

col1, col2, col3 = st.columns(3)
for i, (_, row) in enumerate(comparison_df.iterrows()):
    with [col1, col2, col3][i]:
        rank_emoji = ["🥇", "🥈", "🥉"][i] if i < 3 else ""
        st.metric(
            f"{rank_emoji} {row['region']}",
            f"${row['total_tco']:,.0f}",
            f"Rank #{row['tco_rank']}",
        )

# Stacked bar chart
layer_cols = ["acquisition_cost", "installation_cost", "operating_cost", "maintenance_cost",
              "spares_logistics_cost", "risk_resilience_cost", "utilization_impact_cost"]
chart_data = comparison_df[["region"] + layer_cols].set_index("region")
fig = px.bar(
    chart_data.reset_index().melt(id_vars="region", var_name="Cost Layer", value_name="USD"),
    x="region", y="USD", color="Cost Layer", barmode="stack",
    title="TCO Breakdown by Region",
    color_discrete_sequence=px.colors.qualitative.Set2,
)
fig.update_layout(xaxis_title="Region", yaxis_title="Cost (USD)", yaxis_tickformat="$,.0f")
st.plotly_chart(fig, use_container_width=True)

# ─── Risk Heatmap ───────────────────────────────────────────────────
st.markdown("### 🔥 Risk Heatmap")
risk_data = []
for region, indices in config.REGIONAL_RISK_INDICES.items():
    for risk_type, value in indices.items():
        risk_data.append({"Region": region, "Risk Type": risk_type.replace("_", " ").title(), "Risk Level": value})
risk_df = pd.DataFrame(risk_data)
pivot = risk_df.pivot(index="Risk Type", columns="Region", values="Risk Level")
fig_heat = px.imshow(
    pivot, text_auto=".2f", color_continuous_scale="RdYlGn_r",
    title="Regional Risk Index Heatmap",
)
st.plotly_chart(fig_heat, use_container_width=True)

# ─── Monte Carlo Summary ────────────────────────────────────────────
st.markdown("### 📈 Monte Carlo Uncertainty")

@st.cache_data(ttl=600)
def _run_mc_comparison(_specs):
    mc = MonteCarloSimulator(n_simulations=2000, seed=42)
    return mc.simulate_comparison(_specs, RunMetadata(scenario="executive_dashboard_mc"))

mc_df = _run_mc_comparison(specs)

fig_mc = go.Figure()
for _, row in mc_df.iterrows():
    fig_mc.add_trace(go.Box(
        name=row["region"],
        q1=[row["tco_p25"]], median=[row["tco_p50"]], q3=[row["tco_p75"]],
        lowerfence=[row["tco_p05"]], upperfence=[row["tco_p95"]],
        mean=[row["tco_mean"]],
    ))
fig_mc.update_layout(title="TCO Distribution by Region (90% CI)", yaxis_title="Total TCO (USD)", yaxis_tickformat="$,.0f")
st.plotly_chart(fig_mc, use_container_width=True)

st.caption("⚠️ Evidence class: **simulated_estimate** — based on synthetic data and modeled assumptions.")
