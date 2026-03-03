-- ============================================================
-- TCO Comparison Model — Database Schema
-- Normalized star-schema for equipment, suppliers, TCO results,
-- scenarios, and audit trail.
-- ============================================================

CREATE DATABASE IF NOT EXISTS tco_comparison
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE tco_comparison;

-- ─── Dimension: Regions ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS dim_region (
    region_id       INT AUTO_INCREMENT PRIMARY KEY,
    region_name     VARCHAR(50) NOT NULL UNIQUE,
    currency_code   VARCHAR(3) NOT NULL,
    labor_rate_usd  DECIMAL(10,2),
    energy_cost_kwh DECIMAL(10,4),
    risk_index      DECIMAL(5,3) DEFAULT 0.0,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT IGNORE INTO dim_region (region_name, currency_code, labor_rate_usd, energy_cost_kwh, risk_index)
VALUES
    ('China',  'CNY', 8.50, 0.0800, 0.40),
    ('India',  'INR', 4.20, 0.0900, 0.42),
    ('Europe', 'EUR', 38.00, 0.2200, 0.15);

-- ─── Dimension: Suppliers ───────────────────────────────────────
CREATE TABLE IF NOT EXISTS dim_supplier (
    supplier_id         VARCHAR(50) PRIMARY KEY,
    supplier_name       VARCHAR(200) NOT NULL,
    region_id           INT,
    quality_index       DECIMAL(5,2),
    delivery_reliability DECIMAL(5,2),
    service_responsiveness DECIMAL(5,2),
    warranty_performance DECIMAL(5,2),
    price_competitiveness DECIMAL(5,3),
    local_support       DECIMAL(5,2),
    composite_score     DECIMAL(5,4),
    financial_risk      DECIMAL(5,3) DEFAULT 0.3,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (region_id) REFERENCES dim_region(region_id)
);

-- ─── Dimension: Equipment ───────────────────────────────────────
CREATE TABLE IF NOT EXISTS dim_equipment (
    equipment_id        VARCHAR(50) PRIMARY KEY,
    name                VARCHAR(200) NOT NULL,
    category            VARCHAR(100),
    region_id           INT,
    supplier_id         VARCHAR(50),
    base_price_local    DECIMAL(15,2),
    currency            VARCHAR(3),
    asset_life_years    INT DEFAULT 10,
    mtbf_hours          DECIMAL(10,1),
    mttr_hours          DECIMAL(10,1),
    rated_throughput    DECIMAL(10,2),
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (region_id) REFERENCES dim_region(region_id),
    FOREIGN KEY (supplier_id) REFERENCES dim_supplier(supplier_id)
);

-- ─── Fact: TCO Results ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS fact_tco_result (
    result_id           INT AUTO_INCREMENT PRIMARY KEY,
    run_id              VARCHAR(100) NOT NULL,
    equipment_id        VARCHAR(50) NOT NULL,
    scenario            VARCHAR(50) DEFAULT 'base',
    acquisition_cost    DECIMAL(15,2),
    installation_cost   DECIMAL(15,2),
    operating_cost      DECIMAL(15,2),
    maintenance_cost    DECIMAL(15,2),
    spares_logistics_cost DECIMAL(15,2),
    risk_resilience_cost DECIMAL(15,2),
    utilization_cost    DECIMAL(15,2),
    residual_value      DECIMAL(15,2),
    total_tco           DECIMAL(15,2),
    annualized_tco      DECIMAL(15,2),
    tco_rank            INT,
    evidence_class      VARCHAR(50) DEFAULT 'simulated_estimate',
    input_fingerprint   VARCHAR(32),
    computed_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (equipment_id) REFERENCES dim_equipment(equipment_id)
);

CREATE INDEX idx_tco_run ON fact_tco_result(run_id);
CREATE INDEX idx_tco_equipment ON fact_tco_result(equipment_id);
CREATE INDEX idx_tco_scenario ON fact_tco_result(scenario);

-- ─── Fact: Monte Carlo Results ──────────────────────────────────
CREATE TABLE IF NOT EXISTS fact_monte_carlo (
    mc_id               INT AUTO_INCREMENT PRIMARY KEY,
    run_id              VARCHAR(100) NOT NULL,
    equipment_id        VARCHAR(50) NOT NULL,
    n_simulations       INT,
    seed                INT,
    tco_mean            DECIMAL(15,2),
    tco_median          DECIMAL(15,2),
    tco_std             DECIMAL(15,2),
    tco_p05             DECIMAL(15,2),
    tco_p25             DECIMAL(15,2),
    tco_p50             DECIMAL(15,2),
    tco_p75             DECIMAL(15,2),
    tco_p95             DECIMAL(15,2),
    tco_cv              DECIMAL(8,4),
    evidence_class      VARCHAR(50) DEFAULT 'simulated_estimate',
    computed_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (equipment_id) REFERENCES dim_equipment(equipment_id)
);

-- ─── Fact: Scenario Comparisons ─────────────────────────────────
CREATE TABLE IF NOT EXISTS fact_scenario (
    scenario_id         INT AUTO_INCREMENT PRIMARY KEY,
    run_id              VARCHAR(100) NOT NULL,
    equipment_id        VARCHAR(50) NOT NULL,
    scenario_name       VARCHAR(50) NOT NULL,
    scenario_label      VARCHAR(100),
    total_tco           DECIMAL(15,2),
    tco_delta_vs_base   DECIMAL(15,2),
    tco_delta_pct       DECIMAL(8,2),
    evidence_class      VARCHAR(50) DEFAULT 'simulated_estimate',
    computed_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (equipment_id) REFERENCES dim_equipment(equipment_id)
);

-- ─── Fact: Financial Analysis ───────────────────────────────────
CREATE TABLE IF NOT EXISTS fact_financial (
    financial_id        INT AUTO_INCREMENT PRIMARY KEY,
    run_id              VARCHAR(100) NOT NULL,
    equipment_id        VARCHAR(50) NOT NULL,
    npv_usd             DECIMAL(15,2),
    irr                 DECIMAL(8,4),
    payback_years       DECIMAL(5,1),
    annual_opex_usd     DECIMAL(15,2),
    working_capital_usd DECIMAL(15,2),
    discount_rate       DECIMAL(5,4),
    evidence_class      VARCHAR(50) DEFAULT 'simulated_estimate',
    computed_at         TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (equipment_id) REFERENCES dim_equipment(equipment_id)
);

-- ─── Fact: Optimization Recommendations ─────────────────────────
CREATE TABLE IF NOT EXISTS fact_recommendation (
    rec_id              INT AUTO_INCREMENT PRIMARY KEY,
    run_id              VARCHAR(100) NOT NULL,
    recommendation_type VARCHAR(50) NOT NULL,
    equipment_id        VARCHAR(50),
    region              VARCHAR(50),
    recommendation      TEXT,
    annual_savings_usd  DECIMAL(15,2),
    confidence          VARCHAR(50),
    evidence_class      VARCHAR(50) DEFAULT 'simulated_estimate',
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (equipment_id) REFERENCES dim_equipment(equipment_id)
);

-- ─── Audit Trail ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS audit_trail (
    audit_id            INT AUTO_INCREMENT PRIMARY KEY,
    run_id              VARCHAR(100),
    event_type          VARCHAR(100) NOT NULL,
    evidence_class      VARCHAR(50),
    details             JSON,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_run ON audit_trail(run_id);
CREATE INDEX idx_audit_event ON audit_trail(event_type);

-- ─── Assumption Registry ────────────────────────────────────────
CREATE TABLE IF NOT EXISTS assumption_registry (
    assumption_id       INT AUTO_INCREMENT PRIMARY KEY,
    run_id              VARCHAR(100) NOT NULL,
    assumption_key      VARCHAR(200) NOT NULL,
    assumption_value    TEXT,
    source              VARCHAR(200),
    version             VARCHAR(50),
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_assumption_run ON assumption_registry(run_id);
