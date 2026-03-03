-- ============================================================
-- TCO Comparison Model — Semantic Views for BI / Power BI
-- ============================================================

USE tco_comparison;

-- ─── Executive TCO Comparison View ──────────────────────────────
CREATE OR REPLACE VIEW v_tco_comparison AS
SELECT
    t.run_id,
    t.equipment_id,
    e.name AS equipment_name,
    e.category,
    r.region_name,
    s.supplier_name,
    t.scenario,
    t.acquisition_cost,
    t.installation_cost,
    t.operating_cost,
    t.maintenance_cost,
    t.spares_logistics_cost,
    t.risk_resilience_cost,
    t.utilization_cost,
    t.residual_value,
    t.total_tco,
    t.annualized_tco,
    t.tco_rank,
    t.evidence_class,
    t.computed_at
FROM fact_tco_result t
JOIN dim_equipment e ON t.equipment_id = e.equipment_id
JOIN dim_region r ON e.region_id = r.region_id
LEFT JOIN dim_supplier s ON e.supplier_id = s.supplier_id;

-- ─── Monte Carlo Summary View ───────────────────────────────────
CREATE OR REPLACE VIEW v_monte_carlo_summary AS
SELECT
    mc.run_id,
    mc.equipment_id,
    e.name AS equipment_name,
    r.region_name,
    mc.n_simulations,
    mc.tco_mean,
    mc.tco_median,
    mc.tco_std,
    mc.tco_p05,
    mc.tco_p50,
    mc.tco_p95,
    mc.tco_cv,
    (mc.tco_p95 - mc.tco_p05) AS confidence_range_90,
    mc.evidence_class,
    mc.computed_at
FROM fact_monte_carlo mc
JOIN dim_equipment e ON mc.equipment_id = e.equipment_id
JOIN dim_region r ON e.region_id = r.region_id;

-- ─── Scenario Comparison View ───────────────────────────────────
CREATE OR REPLACE VIEW v_scenario_comparison AS
SELECT
    sc.run_id,
    sc.equipment_id,
    e.name AS equipment_name,
    r.region_name,
    sc.scenario_name,
    sc.scenario_label,
    sc.total_tco,
    sc.tco_delta_vs_base,
    sc.tco_delta_pct,
    sc.evidence_class,
    sc.computed_at
FROM fact_scenario sc
JOIN dim_equipment e ON sc.equipment_id = e.equipment_id
JOIN dim_region r ON e.region_id = r.region_id;

-- ─── Supplier Scorecard View ────────────────────────────────────
CREATE OR REPLACE VIEW v_supplier_scorecard AS
SELECT
    s.supplier_id,
    s.supplier_name,
    r.region_name,
    s.quality_index,
    s.delivery_reliability,
    s.service_responsiveness,
    s.warranty_performance,
    s.price_competitiveness,
    s.local_support,
    s.composite_score,
    s.financial_risk,
    s.updated_at
FROM dim_supplier s
JOIN dim_region r ON s.region_id = r.region_id;

-- ─── Financial Summary View ─────────────────────────────────────
CREATE OR REPLACE VIEW v_financial_summary AS
SELECT
    f.run_id,
    f.equipment_id,
    e.name AS equipment_name,
    r.region_name,
    s.supplier_name,
    f.npv_usd,
    f.irr,
    f.payback_years,
    f.annual_opex_usd,
    f.working_capital_usd,
    f.discount_rate,
    f.evidence_class,
    f.computed_at
FROM fact_financial f
JOIN dim_equipment e ON f.equipment_id = e.equipment_id
JOIN dim_region r ON e.region_id = r.region_id
LEFT JOIN dim_supplier s ON e.supplier_id = s.supplier_id;
