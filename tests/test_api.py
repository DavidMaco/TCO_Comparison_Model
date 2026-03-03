"""
Integration tests for the TCO Comparison Model REST API.
Uses FastAPI TestClient (backed by httpx) — no live server required.
"""
import os

os.environ.setdefault("TCO_DEV_MODE", "true")
# Ensure API key is unset so the middleware does not block test requests
os.environ.pop("TCO_API_KEY", None)

import pytest
from fastapi.testclient import TestClient

from api.main import app, _hits

# ─── Helpers ─────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def _clear_rate_limiter():
    """Reset the in-memory rate-limit hits between tests."""
    _hits.clear()
    yield
    _hits.clear()


@pytest.fixture
def client():
    return TestClient(app)


# Minimal valid equipment payload (reusable)
_EQUIPMENT = {
    "equipment_id": "CNC-CN-01",
    "name": "China CNC",
    "region": "China",
    "supplier_id": "SUP-CN-01",
    "supplier_name": "Shenyang",
    "base_price_local": 580000,
    "currency": "CNY",
    "energy_kwh_per_year": 50000,
    "operator_hours_per_year": 2000,
    "consumables_per_year": 5000,
    "monitoring_cost_per_year": 2000,
    "preventive_maintenance_events_per_year": 4,
    "corrective_maintenance_events_per_year": 2,
    "maintenance_labor_hours_per_event": 12,
    "spares_cost_per_event": 800,
    "mtbf_hours": 6000,
    "mttr_hours": 18,
    "warranty_years": 2,
    "warranty_coverage_pct": 0.80,
    "spares_per_year": 6,
    "spare_weight_kg": 30,
    "customs_clearance_cost": 400,
    "rated_throughput_per_hour": 100,
    "actual_throughput_per_hour": 92,
    "yield_rate": 0.96,
    "scrap_cost_per_unit": 0.45,
    "asset_life_years": 10,
    "site_prep_cost": 3000,
    "installation_labor_hours": 60,
    "certification_cost": 2500,
    "spare_unit_price_local": 500,
    "logistics_distance_km": 5000,
    "logistics_mode": "Sea",
}


# ─── Tests ───────────────────────────────────────────────────────────


class TestHealth:
    def test_health_ok(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "healthy"

    def test_health_has_version(self, client):
        body = client.get("/health").json()
        assert "version" in body


class TestConfigEndpoints:
    def test_regions(self, client):
        r = client.get("/config/regions")
        assert r.status_code == 200
        data = r.json()
        assert "regions" in data
        assert "China" in data["regions"]

    def test_scenarios(self, client):
        r = client.get("/config/scenarios")
        assert r.status_code == 200
        data = r.json()
        assert "base" in data


class TestTCOCompute:
    def test_compute_single(self, client):
        r = client.post("/tco/compute", json=_EQUIPMENT)
        assert r.status_code == 200
        body = r.json()
        assert "total_tco" in body
        assert body["total_tco"] > 0

    def test_compute_invalid_region(self, client):
        payload = {**_EQUIPMENT, "region": "Mars"}
        r = client.post("/tco/compute", json=payload)
        assert r.status_code == 422  # Pydantic validation

    def test_compare(self, client):
        eu = {**_EQUIPMENT,
              "equipment_id": "CNC-EU-01", "name": "Europe CNC",
              "region": "Europe", "base_price_local": 92000, "currency": "EUR"}
        r = client.post("/tco/compare", json={"equipment": [_EQUIPMENT, eu]})
        assert r.status_code == 200
        assert len(r.json()["comparison"]) == 2


class TestMonteCarlo:
    def test_simulate(self, client):
        r = client.post("/monte-carlo/simulate", json={
            "equipment": [_EQUIPMENT],
            "n_simulations": 200,
            "seed": 42,
        })
        assert r.status_code == 200
        results = r.json()["simulation_results"]
        assert len(results) == 1
        assert results[0]["tco_mean"] > 0


class TestScenario:
    def test_single_scenario(self, client):
        r = client.post("/scenarios/analyze", json={
            "equipment": _EQUIPMENT,
            "scenarios": ["base"],
        })
        assert r.status_code == 200
        body = r.json()
        assert len(body["scenario_results"]) == 1

    def test_all_scenarios(self, client):
        r = client.post("/scenarios/analyze", json={"equipment": _EQUIPMENT})
        assert r.status_code == 200
        assert len(r.json()["scenario_results"]) >= 6


class TestFinancial:
    def test_financial_analyze(self, client):
        r = client.post("/financial/analyze", json=_EQUIPMENT)
        assert r.status_code == 200
        body = r.json()
        assert "npv_usd" in body
        assert "irr" in body


class TestSupplierScorecard:
    def test_scorecard(self, client):
        suppliers = [{
            "supplier_id": "SUP-CN-01", "supplier_name": "Shenyang", "region": "China",
            "quality_index": 72, "delivery_reliability": 78,
            "service_responsiveness": 6, "warranty_performance": 65,
            "price_competitiveness": 0.7, "local_support": 5,
        }]
        r = client.post("/suppliers/scorecard", json={"suppliers": suppliers})
        assert r.status_code == 200


class TestOptimize:
    def test_optimize(self, client):
        r = client.post("/optimize", json={
            "equipment": [_EQUIPMENT],
            "risk_tolerance": "moderate",
        })
        assert r.status_code == 200


class TestBenchmark:
    def test_benchmark(self, client):
        r = client.post("/benchmark", json={"equipment": [_EQUIPMENT]})
        assert r.status_code == 200


class TestAPIKeyAuth:
    """Test that API-key middleware works when TCO_API_KEY is set."""

    def test_rejects_without_key(self, monkeypatch):
        """When API key is required, requests without it get 401."""
        import api.main as api_mod
        monkeypatch.setattr(api_mod, "_API_KEY", "test-secret-key")
        with TestClient(app) as c:
            r = c.get("/config/regions")
        assert r.status_code == 401

    def test_accepts_with_header(self, monkeypatch):
        import api.main as api_mod
        monkeypatch.setattr(api_mod, "_API_KEY", "test-secret-key")
        with TestClient(app) as c:
            r = c.get("/config/regions", headers={"X-API-Key": "test-secret-key"})
        assert r.status_code == 200

    def test_health_bypasses_key(self, monkeypatch):
        """Health endpoint should always work regardless of API key."""
        import api.main as api_mod
        monkeypatch.setattr(api_mod, "_API_KEY", "test-secret-key")
        with TestClient(app) as c:
            r = c.get("/health")
        assert r.status_code == 200


class TestRateLimiting:
    def test_rate_limit_exceeded(self, monkeypatch):
        import api.main as api_mod
        monkeypatch.setattr(api_mod, "_RATE_LIMIT", 3)
        monkeypatch.setattr(api_mod, "_RATE_WINDOW", 60)
        _hits.clear()
        with TestClient(app) as c:
            for _ in range(3):
                c.get("/health")
            r = c.get("/health")
        assert r.status_code == 429
