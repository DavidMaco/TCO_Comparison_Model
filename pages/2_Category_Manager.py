"""
TCO Comparison Model — Category Manager Workbench
What-if scenario builder, assumption sliders, supplier scorecards.
"""
import os
os.environ.setdefault("TCO_DEV_MODE", "true")

import streamlit as st
import pandas as pd
import plotly.express as px

from analytics.tco_engine import TCOEngine, EquipmentSpec
from analytics.scenario_engine import ScenarioEngine
from analytics.supplier_scorecard import SupplierScorecard
from utils.run_metadata import RunMetadata
from utils.demo_data import get_demo_specs, DEMO_SUPPLIERS
import config

st.set_page_config(page_title="TCO · Category Manager", page_icon="🔧", layout="wide")
st.title("🔧 Category Manager Workbench")

# ─── Assumption Sliders ─────────────────────────────────────────────
st.sidebar.markdown("### ⚙️ Assumptions")
discount_rate = st.sidebar.slider("Discount Rate (%)", 5, 20, 10) / 100
asset_life = st.sidebar.slider("Asset Life (years)", 5, 20, 10)
base_price_cn = st.sidebar.number_input("China Base Price (CNY)", value=580000, step=10000)
base_price_in = st.sidebar.number_input("India Base Price (INR)", value=6500000, step=100000)
base_price_eu = st.sidebar.number_input("Europe Base Price (EUR)", value=92000, step=5000)
selected_scenario = st.sidebar.selectbox("Scenario", list(config.PREDEFINED_SCENARIOS.keys()))

# Build specs from sliders using shared demo data
specs = get_demo_specs(
    asset_life=asset_life,
    base_price_cn=base_price_cn,
    base_price_in=base_price_in,
    base_price_eu=base_price_eu,
)

# ─── Scenario Analysis ──────────────────────────────────────────────
st.markdown("### 📐 Scenario Analysis")
scenario_engine = ScenarioEngine()

results = []
for spec in specs:
    r = scenario_engine.run_single_scenario(spec, selected_scenario)
    results.append(r)

scenario_df = pd.DataFrame(results)
fig = px.bar(scenario_df, x="region", y="total_tco", color="region",
             title=f"TCO Under '{selected_scenario}' Scenario",
             color_discrete_sequence=px.colors.qualitative.Set1)
fig.update_layout(yaxis_tickformat="$,.0f", yaxis_title="Total TCO (USD)")
st.plotly_chart(fig, use_container_width=True)

# All scenarios comparison for one region
st.markdown("### 🔄 All Scenarios — China")
all_sc = scenario_engine.run_all_scenarios(specs[0])
fig2 = px.bar(all_sc, x="scenario", y="total_tco", color="tco_delta_pct",
              title="TCO Across All Scenarios (China CNC)",
              color_continuous_scale="RdYlGn_r")
fig2.update_layout(yaxis_tickformat="$,.0f")
st.plotly_chart(fig2, use_container_width=True)

# ─── Supplier Scorecard ─────────────────────────────────────────────
st.markdown("### 🏆 Supplier Scorecard")

sc = SupplierScorecard()
report = sc.generate_report(DEMO_SUPPLIERS)
scored_df = pd.DataFrame(report["individual_scores"])
st.dataframe(scored_df[["supplier_name", "region", "composite_score", "composite_rank",
                         "quality_index_normalized", "delivery_reliability_normalized",
                         "service_responsiveness_normalized", "warranty_performance_normalized"]].round(3),
             use_container_width=True)

fig3 = px.bar(scored_df, x="supplier_name", y="composite_score", color="region",
              title="Supplier Composite Scores")
st.plotly_chart(fig3, use_container_width=True)

st.caption("⚠️ Evidence class: **simulated_estimate** — based on demo data.")
