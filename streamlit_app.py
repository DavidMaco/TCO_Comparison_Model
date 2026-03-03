"""
TCO Comparison Model — Main Streamlit Application
Multi-persona dashboard: Executive, Category Manager, Finance/CFO, Engineering.
"""
import os
os.environ.setdefault("TCO_DEV_MODE", "true")

import streamlit as st

st.set_page_config(
    page_title="TCO Comparison Model",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ──────────────────────────────────────────────────────
st.markdown("""
<style>
    .main .block-container { padding-top: 1rem; max-width: 1400px; }
    .stMetric { background: #f8f9fa; border-radius: 8px; padding: 12px; }
    .stMetric label { font-size: 0.85rem; color: #6c757d; }
    .stMetric [data-testid="stMetricValue"] { font-size: 1.8rem; font-weight: 700; }
    div[data-testid="stSidebar"] { background: linear-gradient(180deg, #0d1b2a, #1b263b); }
    div[data-testid="stSidebar"] .stMarkdown { color: #e0e0e0; }
    h1, h2, h3 { color: #0d1b2a; }
</style>
""", unsafe_allow_html=True)


# ─── Sidebar ─────────────────────────────────────────────────────────
st.sidebar.markdown("## ⚙️ TCO Comparison Model")
st.sidebar.markdown("**Total Cost of Ownership**")
st.sidebar.markdown("China · India · Europe")
st.sidebar.markdown("---")
st.sidebar.caption("v0.1.0 · © 2026")


# ─── Landing Page ────────────────────────────────────────────────────
st.title("⚙️ TCO Comparison Model")
st.markdown("""
**Investment-grade Total Cost of Ownership analysis** for equipment and spares
sourced from **China, India, and Europe**.

> Combines deterministic lifecycle costing, Monte Carlo uncertainty quantification,
> multi-scenario analysis, financial translation (NPV/IRR), supplier scorecards,
> and prescriptive optimization — with full assumption traceability and auditability.
""")

st.markdown("---")

# Key capabilities
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Cost Layers", "8", help="Full lifecycle: acquisition through disposal")
with col2:
    st.metric("Scenarios", "6+", help="Base, optimistic, pessimistic, regulatory, supply shock, market volatility")
with col3:
    st.metric("Regions", "3", help="China, India, Europe")
with col4:
    st.metric("Simulations", "10,000", help="Monte Carlo paths per analysis")

st.markdown("---")

st.markdown("### 📊 Dashboard Views")
st.markdown("""
Navigate to specialized views using the sidebar:

| View | Audience | Key Features |
|------|----------|-------------|
| **Executive Dashboard** | C-Suite / Board | TCO comparison heatmaps, risk overview, financial summary |
| **Category Manager** | Procurement | What-if scenario builder, supplier scorecards, assumption sliders |
| **Finance / CFO** | Finance Team | NPV, IRR, cashflow modeling, working capital impact |
| **Engineering** | Technical Team | Reliability curves, maintenance planning, performance benchmarks |
""")

st.markdown("---")
st.markdown("### 🏗️ Architecture")
st.markdown("""
- **TCO Engine** — Deterministic lifecycle cost across 8 layers
- **Monte Carlo** — Stochastic simulation with confidence intervals
- **Scenario Engine** — 6+ predefined macro/operational scenarios
- **Financial Translator** — NPV, IRR, EBITDA, working capital
- **Supplier Scorecard** — Weighted multi-criteria evaluation
- **Optimization** — Sourcing, maintenance, inventory recommendations
- **Benchmarking** — Industry standard comparisons
- **API Layer** — RESTful endpoints for ERP/EAM integration
""")

st.info("ℹ️ All outputs are labeled with evidence class (simulated_estimate, pilot_observed, production_realized) for transparency.")
