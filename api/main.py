"""
TCO Comparison Model — FastAPI Application
REST API for TCO computation, scenario analysis, optimization, and reporting.
"""
from __future__ import annotations

import logging
import os
import time
from collections import defaultdict
from typing import Any

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import config
from analytics.benchmarking import BenchmarkEngine
from analytics.financial_translator import FinancialTranslator
from analytics.monte_carlo import MonteCarloSimulator
from analytics.optimization import TCOptimizer
from analytics.scenario_engine import ScenarioEngine
from analytics.supplier_scorecard import SupplierScorecard
from analytics.tco_engine import EquipmentSpec, TCOEngine
from utils.run_metadata import RunMetadata

log = logging.getLogger("tco.api")

_allowed_origins = os.environ.get("TCO_CORS_ORIGINS", "http://localhost:8501").split(",")

# ─── Optional API-key authentication ─────────────────────────────────
_API_KEY: str | None = os.environ.get("TCO_API_KEY") or None

# ─── Simple in-memory rate limiter ───────────────────────────────────
_RATE_LIMIT: int = int(os.environ.get("TCO_RATE_LIMIT", "60"))   # requests per window
_RATE_WINDOW: int = int(os.environ.get("TCO_RATE_WINDOW", "60"))  # seconds
_hits: dict[str, list[float]] = defaultdict(list)

app = FastAPI(
    title="TCO Comparison Model API",
    description="Total Cost of Ownership analysis for Chinese, Indian, and European equipment & spares",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.middleware("http")
async def auth_and_rate_limit(request: Request, call_next) -> Response:
    """Enforce optional API-key auth and per-IP rate limiting.

    - If ``TCO_API_KEY`` is set, every request (except ``/health`` and ``/docs``)
      must include ``X-API-Key`` header or ``api_key`` query param.
    - Rate limiting uses a sliding-window counter keyed by client IP.
    """
    path = request.url.path

    # --- API-key gate (skip health/docs/openapi) ---
    if _API_KEY and path not in ("/health", "/docs", "/openapi.json", "/redoc"):
        provided = request.headers.get("X-API-Key") or request.query_params.get("api_key")
        if provided != _API_KEY:
            return Response(content='{"detail":"Invalid or missing API key"}',
                            status_code=401, media_type="application/json")

    # --- Rate limiting ---
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    window_start = now - _RATE_WINDOW
    # Prune old hits
    _hits[client_ip] = [t for t in _hits[client_ip] if t > window_start]
    if len(_hits[client_ip]) >= _RATE_LIMIT:
        return Response(
            content='{"detail":"Rate limit exceeded. Try again later."}',
            status_code=429,
            media_type="application/json",
        )
    _hits[client_ip].append(now)

    return await call_next(request)


# ─── Pydantic Models ────────────────────────────────────────────────

class EquipmentInput(BaseModel):
    equipment_id: str
    name: str
    category: str = "CNC Machine"
    region: str = Field(..., pattern="^(China|India|Europe)$")
    supplier_id: str
    supplier_name: str
    base_price_local: float = 0.0
    currency: str = "USD"
    volume_discount_pct: float = 0.0
    trade_finance_cost_pct: float = 0.0
    site_prep_cost: float = 0.0
    utilities_infra_cost: float = 0.0
    installation_labor_hours: float = 0.0
    certification_cost: float = 0.0
    testing_validation_cost: float = 0.0
    startup_consumables_cost: float = 0.0
    energy_kwh_per_year: float = 0.0
    operator_hours_per_year: float = 0.0
    consumables_per_year: float = 0.0
    monitoring_cost_per_year: float = 0.0
    preventive_maintenance_events_per_year: float = 2.0
    corrective_maintenance_events_per_year: float = 1.0
    maintenance_labor_hours_per_event: float = 8.0
    spares_cost_per_event: float = 0.0
    mtbf_hours: float = 5000.0
    mttr_hours: float = 24.0
    warranty_years: float = 1.0
    warranty_coverage_pct: float = 0.80
    spare_unit_price_local: float = 0.0
    spares_per_year: float = 2.0
    logistics_mode: str = "Sea"
    logistics_distance_km: float = 5000.0
    spare_weight_kg: float = 50.0
    customs_clearance_cost: float = 500.0
    inventory_carrying_pct: float = 0.20
    lead_time_days: float = 30.0
    lead_time_std_days: float = 10.0
    obsolescence_risk_pct: float = 0.05
    disruption_probability: float | None = None
    supplier_financial_risk: float = 0.3
    rated_throughput_per_hour: float = 100.0
    actual_throughput_per_hour: float = 90.0
    yield_rate: float = 0.95
    scrap_cost_per_unit: float = 0.50
    salvage_value_pct: float = 0.10
    disposal_cost: float = 0.0
    environmental_compliance_cost: float = 0.0
    asset_life_years: int = 10
    depreciation_method: str = "straight_line"

    def to_spec(self) -> EquipmentSpec:
        return EquipmentSpec(**self.model_dump())


class ComparisonInput(BaseModel):
    equipment: list[EquipmentInput]
    discount_rate: float = 0.10


class ScenarioInput(BaseModel):
    equipment: EquipmentInput
    scenarios: list[str] | None = None


class MonteCarloInput(BaseModel):
    equipment: list[EquipmentInput]
    n_simulations: int = Field(default=10000, ge=100, le=100000)
    seed: int = 42


class SupplierInput(BaseModel):
    supplier_id: str
    supplier_name: str
    region: str
    quality_index: float = 80.0
    delivery_reliability: float = 85.0
    service_responsiveness: float = 7.0
    warranty_performance: float = 75.0
    price_competitiveness: float = 1.0
    local_support: float = 6.0


class ScorecardInput(BaseModel):
    suppliers: list[SupplierInput]


class OptimizationInput(BaseModel):
    equipment: list[EquipmentInput]
    supplier_data: list[SupplierInput] | None = None
    risk_tolerance: str = "moderate"


# ─── Endpoints ───────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "healthy", "version": "0.1.0"}


@app.get("/config/regions")
def get_regions():
    return {
        "regions": config.REGIONS,
        "currencies": config.REGION_CURRENCIES,
        "labor_rates": config.REGIONAL_LABOR_RATES,
        "energy_costs": config.REGIONAL_ENERGY_COSTS,
        "tariffs": config.TARIFF_DEFAULTS,
        "risk_indices": config.REGIONAL_RISK_INDICES,
    }


@app.get("/config/scenarios")
def get_scenarios():
    return config.PREDEFINED_SCENARIOS


@app.post("/tco/compute")
def compute_tco(input_data: EquipmentInput):
    """Compute TCO for a single equipment specification."""
    try:
        engine = TCOEngine()
        meta = RunMetadata(scenario="api_single")
        result = engine.compute(input_data.to_spec(), meta)
        return result.to_dict()
    except Exception as e:
        log.exception("compute_tco error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/tco/compare")
def compare_tco(input_data: ComparisonInput):
    """Compare TCO across multiple equipment/region options."""
    try:
        engine = TCOEngine(discount_rate=input_data.discount_rate)
        meta = RunMetadata(scenario="api_comparison")
        specs = [eq.to_spec() for eq in input_data.equipment]
        df = engine.compare(specs, meta)
        return {"comparison": df.drop(columns=["layer_details", "assumptions", "run_metadata"], errors="ignore").to_dict("records")}
    except Exception as e:
        log.exception("compare_tco error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/monte-carlo/simulate")
def monte_carlo_simulate(input_data: MonteCarloInput):
    """Run Monte Carlo simulation for uncertainty quantification."""
    try:
        mc = MonteCarloSimulator(n_simulations=input_data.n_simulations, seed=input_data.seed)
        meta = RunMetadata(scenario="api_monte_carlo")
        specs = [eq.to_spec() for eq in input_data.equipment]
        df = mc.simulate_comparison(specs, meta)
        return {"simulation_results": df.to_dict("records")}
    except Exception as e:
        log.exception("monte_carlo error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/scenarios/analyze")
def scenario_analysis(input_data: ScenarioInput):
    """Run multi-scenario TCO analysis."""
    try:
        engine = ScenarioEngine()
        meta = RunMetadata(scenario="api_scenario")
        spec = input_data.equipment.to_spec()

        if input_data.scenarios:
            results = []
            for name in input_data.scenarios:
                r = engine.run_single_scenario(spec, name, meta)
                results.append(r)
            return {"scenario_results": results}
        else:
            df = engine.run_all_scenarios(spec, meta)
            return {"scenario_results": df.to_dict("records")}
    except Exception as e:
        log.exception("scenario_analysis error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/financial/analyze")
def financial_analysis(input_data: EquipmentInput):
    """Full financial analysis (NPV, IRR, cashflow, EBITDA impact)."""
    try:
        tco_engine = TCOEngine()
        fin = FinancialTranslator()
        meta = RunMetadata(scenario="api_financial")
        spec = input_data.to_spec()
        tco_result = tco_engine.compute(spec, meta)
        analysis = fin.full_financial_analysis(spec, tco_result, meta)
        return analysis
    except Exception as e:
        log.exception("financial_analysis error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/suppliers/scorecard")
def supplier_scorecard(input_data: ScorecardInput):
    """Generate supplier scorecards with regional comparison."""
    try:
        sc = SupplierScorecard()
        meta = RunMetadata(scenario="api_scorecard")
        data = [s.model_dump() for s in input_data.suppliers]
        report = sc.generate_report(data, meta)
        return report
    except Exception as e:
        log.exception("supplier_scorecard error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/optimize")
def optimize(input_data: OptimizationInput):
    """Full prescriptive optimization report."""
    try:
        optimizer = TCOptimizer()
        meta = RunMetadata(scenario="api_optimization")
        specs = [eq.to_spec() for eq in input_data.equipment]
        supplier_data = [s.model_dump() for s in input_data.supplier_data] if input_data.supplier_data else None
        report = optimizer.full_optimization(specs, supplier_data, meta)
        return report
    except Exception as e:
        log.exception("optimize error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/benchmark")
def benchmark(input_data: ComparisonInput):
    """Benchmark equipment against industry standards."""
    try:
        bench = BenchmarkEngine()
        meta = RunMetadata(scenario="api_benchmark")
        equipment_data = [eq.model_dump() for eq in input_data.equipment]
        report = bench.full_benchmark_report(equipment_data, meta)
        return report
    except Exception as e:
        log.exception("benchmark error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
