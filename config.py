"""
TCO Comparison Model — Configuration Module

Total Cost of Ownership analysis for Chinese, Indian, and European
equipment and spares sourcing decisions.

Reads settings from (highest priority first):
  1. Streamlit Cloud secrets  (st.secrets["database"]["DB_HOST"], etc.)
  2. Environment variables     (DB_HOST, DB_PASSWORD, ...)
  3. Built-in defaults
"""
import os
import sys


def _secret(section: str, key: str, fallback: str = "") -> str:
    """Read a value from Streamlit secrets, env var, or fallback.

    Env-var lookup order: ``TCO_<key>`` → ``<key>`` → *fallback*.
    This ensures Docker Compose variables like ``TCO_DB_HOST`` are picked up
    while bare names still work for local development.
    """
    try:
        import streamlit as st
    except ImportError:
        return os.getenv(f"TCO_{key}", os.getenv(key, fallback))
    try:
        return str(st.secrets[section][key])
    except Exception:
        return os.getenv(f"TCO_{key}", os.getenv(key, fallback))


# ─── Database ────────────────────────────────────────────────────────
DB_HOST = _secret("database", "DB_HOST", "localhost")
DB_PORT = int(_secret("database", "DB_PORT", "3306"))
DB_USER = _secret("database", "DB_USER", "root")
DB_PASSWORD = _secret("database", "DB_PASSWORD", "")
DB_NAME = _secret("database", "DB_NAME", "tco_comparison")
DB_SSL = _secret("database", "DB_SSL", "false").lower() in ("true", "1", "yes")

# ── Strict-mode guard ─────────────────────────────────────────────
_DEV_MODE = os.getenv("TCO_DEV_MODE", "").lower() in ("1", "true", "yes")
_TEST_MODE = (
    os.getenv("TCO_TEST_MODE", "").lower() in ("1", "true", "yes")
    or "PYTEST_CURRENT_TEST" in os.environ
    or any("pytest" in arg for arg in sys.argv)
)
if not (_DEV_MODE or _TEST_MODE) and not DB_PASSWORD:
    raise RuntimeError(
        "DB_PASSWORD is required when TCO_DEV_MODE is not enabled. "
        "Set DB_PASSWORD for production/staging, or set TCO_DEV_MODE=true for local development."
    )

_base_url = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
if DB_SSL:
    _base_url += "?ssl_verify_cert=true&ssl_verify_identity=true"
DATABASE_URL = os.getenv("DATABASE_URL", _base_url)


def pymysql_ssl_context():
    """Return an ssl.SSLContext for raw pymysql connections, or None."""
    if not DB_SSL:
        return None
    import ssl
    return ssl.create_default_context()


# ─── Regions ─────────────────────────────────────────────────────────
REGIONS = ["China", "India", "Europe"]
REGION_CURRENCIES = {
    "China": "CNY",
    "India": "INR",
    "Europe": "EUR",
}
BASE_CURRENCY = "USD"

# ─── FX API (3-tier failover) ───────────────────────────────────────
FX_API_PRIMARY = "https://open.er-api.com/v6/latest/USD"
FX_API_SECONDARY = "https://api.exchangerate-api.com/v4/latest/USD"
FX_API_TERTIARY = "https://api.frankfurter.dev/latest?base=USD"

# ─── FX Anchor Rates (live feed with static fallback) ───────────────
_FX_STATIC_RATES = {
    "EUR": 0.92, "GBP": 0.79, "CNY": 7.24, "INR": 83.50,
    "JPY": 151.0, "KRW": 1330.0, "BRL": 4.97, "ZAR": 18.60, "TRY": 32.50,
}

# ─── FX Volatilities (annual σ) ─────────────────────────────────────
FX_VOLATILITIES = {
    "EUR": 0.08,
    "GBP": 0.10,
    "CNY": 0.06,
    "INR": 0.09,
    "JPY": 0.12,
    "KRW": 0.10,
    "BRL": 0.18,
    "ZAR": 0.15,
    "TRY": 0.35,
}


def _fetch_live_fx() -> dict:
    """3-tier failover: open.er-api → exchangerate-api → frankfurter."""
    if os.getenv("TCO_FX_OFFLINE"):
        return dict(_FX_STATIC_RATES)
    import urllib.request, json as _json, logging as _log
    _apis = [FX_API_PRIMARY, FX_API_SECONDARY, FX_API_TERTIARY]
    for url in _apis:
        try:
            with urllib.request.urlopen(url, timeout=8) as resp:
                data = _json.loads(resp.read().decode())
            rates = data.get("rates", {})
            if rates:
                live = {c: float(rates[c]) for c in _FX_STATIC_RATES if c in rates}
                for c, r in _FX_STATIC_RATES.items():
                    live.setdefault(c, r)
                _log.getLogger(__name__).info("Live FX rates loaded from %s", url)
                return live
        except Exception as exc:
            _log.getLogger(__name__).debug("FX fetch failed (%s): %s", url, exc)
    _log.getLogger(__name__).warning("All FX APIs failed — using static fallback rates")
    return dict(_FX_STATIC_RATES)


FX_ANCHOR_RATES = _fetch_live_fx()

# ─── Monte Carlo Defaults ───────────────────────────────────────────
MC_DEFAULT_PATHS = 10_000
MC_DEFAULT_HORIZON_DAYS = 365
MC_MAX_PATHS = 100_000
MC_MAX_HORIZON_DAYS = 3650  # 10 years

# ─── TCO Cost Layer Weights (for composite scoring, sum = 1.00) ─────
TCO_LAYER_WEIGHTS = {
    "acquisition": 0.15,
    "installation": 0.05,
    "operating": 0.20,
    "maintenance": 0.20,
    "spares_logistics": 0.10,
    "risk_resilience": 0.10,
    "utilization_productivity": 0.10,
    "residual_disposal": 0.05,
    "externalities": 0.05,
}

# ─── Risk Scoring Weights (sum = 1.00) ──────────────────────────────
RISK_WEIGHTS = {
    "supply_disruption": 0.20,
    "fx_exposure": 0.15,
    "quality_failure": 0.15,
    "political_regulatory": 0.10,
    "logistics_bottleneck": 0.10,
    "supplier_financial_health": 0.10,
    "lead_time_volatility": 0.10,
    "obsolescence": 0.10,
}

# ─── Regional Risk Indices (0-1, higher = riskier) ──────────────────
REGIONAL_RISK_INDICES = {
    "China": {
        "political_regulatory": 0.45,
        "supply_disruption": 0.35,
        "logistics_bottleneck": 0.40,
        "ip_risk": 0.55,
        "quality_consistency": 0.40,
    },
    "India": {
        "political_regulatory": 0.35,
        "supply_disruption": 0.40,
        "logistics_bottleneck": 0.50,
        "ip_risk": 0.30,
        "quality_consistency": 0.45,
    },
    "Europe": {
        "political_regulatory": 0.15,
        "supply_disruption": 0.15,
        "logistics_bottleneck": 0.15,
        "ip_risk": 0.10,
        "quality_consistency": 0.15,
    },
}

# ─── Regional Labor Rates (USD/hour, manufacturing technician) ──────
REGIONAL_LABOR_RATES = {
    "China": 8.50,
    "India": 4.20,
    "Europe": 38.00,
}

# ─── Regional Energy Costs (USD/kWh) ────────────────────────────────
REGIONAL_ENERGY_COSTS = {
    "China": 0.08,
    "India": 0.09,
    "Europe": 0.22,
}

# ─── Logistics Cost Defaults ────────────────────────────────────────
LOGISTICS_MODES = {
    "Sea": {"cost_per_kg_km": 0.0003, "transit_days_range": (25, 50), "co2_per_tonne_km": 0.016},
    "Air": {"cost_per_kg_km": 0.005, "transit_days_range": (2, 7), "co2_per_tonne_km": 0.602},
    "Rail": {"cost_per_kg_km": 0.001, "transit_days_range": (14, 28), "co2_per_tonne_km": 0.028},
    "Road": {"cost_per_kg_km": 0.002, "transit_days_range": (3, 14), "co2_per_tonne_km": 0.062},
}

# ─── Tariff / Duty Defaults (% of goods value) ──────────────────────
TARIFF_DEFAULTS = {
    "China": {"import_duty_pct": 7.5, "anti_dumping_pct": 2.0, "vat_pct": 13.0},
    "India": {"import_duty_pct": 10.0, "anti_dumping_pct": 0.0, "vat_pct": 18.0},
    "Europe": {"import_duty_pct": 3.5, "anti_dumping_pct": 0.0, "vat_pct": 20.0},
}

# ─── Discount Rate for NPV (WACC proxy) ─────────────────────────────
DEFAULT_DISCOUNT_RATE = 0.10  # 10%

# ─── Depreciation ───────────────────────────────────────────────────
DEPRECIATION_METHODS = ["straight_line", "declining_balance", "units_of_production"]
DEFAULT_DEPRECIATION = "straight_line"
DEFAULT_ASSET_LIFE_YEARS = 10
DEFAULT_SALVAGE_VALUE_PCT = 0.10  # 10% of purchase price

# ─── Supplier Scorecard Weights (sum = 1.00) ────────────────────────
SUPPLIER_SCORECARD_WEIGHTS = {
    "quality_index": 0.25,
    "delivery_reliability": 0.20,
    "service_responsiveness": 0.15,
    "warranty_performance": 0.15,
    "price_competitiveness": 0.15,
    "local_support": 0.10,
}

# ─── Scenario Definitions ───────────────────────────────────────────
PREDEFINED_SCENARIOS = {
    "base": {
        "label": "Base Case",
        "fx_shock_pct": 0.0,
        "demand_shock_pct": 0.0,
        "tariff_delta_pct": 0.0,
        "disruption_probability": 0.05,
        "energy_escalation_pct": 0.03,
        "labor_escalation_pct": 0.03,
    },
    "optimistic": {
        "label": "Optimistic",
        "fx_shock_pct": -0.05,
        "demand_shock_pct": 0.10,
        "tariff_delta_pct": -0.02,
        "disruption_probability": 0.02,
        "energy_escalation_pct": 0.01,
        "labor_escalation_pct": 0.02,
    },
    "pessimistic": {
        "label": "Pessimistic",
        "fx_shock_pct": 0.10,
        "demand_shock_pct": -0.15,
        "tariff_delta_pct": 0.05,
        "disruption_probability": 0.15,
        "energy_escalation_pct": 0.08,
        "labor_escalation_pct": 0.06,
    },
    "regulatory_shock": {
        "label": "Regulatory Shock",
        "fx_shock_pct": 0.03,
        "demand_shock_pct": -0.05,
        "tariff_delta_pct": 0.15,
        "disruption_probability": 0.10,
        "energy_escalation_pct": 0.05,
        "labor_escalation_pct": 0.04,
    },
    "supply_disruption": {
        "label": "Supply Chain Shock",
        "fx_shock_pct": 0.08,
        "demand_shock_pct": -0.20,
        "tariff_delta_pct": 0.03,
        "disruption_probability": 0.30,
        "energy_escalation_pct": 0.10,
        "labor_escalation_pct": 0.05,
    },
    "market_volatility": {
        "label": "Market Volatility",
        "fx_shock_pct": 0.15,
        "demand_shock_pct": -0.10,
        "tariff_delta_pct": 0.08,
        "disruption_probability": 0.12,
        "energy_escalation_pct": 0.12,
        "labor_escalation_pct": 0.07,
    },
}

# ─── Performance Standards ───────────────────────────────────────────
PERFORMANCE_STANDARDS = {
    "scenario_compute_target_seconds": 10,
    "min_scenario_coverage": 6,
    "min_supplier_coverage_pct": 90,
    "audit_traceability_pct": 100,
}

# ─── Feature Flags ──────────────────────────────────────────────────
ENABLE_LIVE_FX = os.getenv("ENABLE_LIVE_FX", "false").lower() == "true"
DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() == "true"
RANDOM_SEED = 42
