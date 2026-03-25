"""Tests for config module."""
import os

os.environ.setdefault("TCO_DEV_MODE", "true")

import config


class TestConfig:

    def test_regions_defined(self):
        assert "China" in config.REGIONS
        assert "India" in config.REGIONS
        assert "Europe" in config.REGIONS

    def test_scenarios_defined(self):
        assert "base" in config.PREDEFINED_SCENARIOS
        assert "pessimistic" in config.PREDEFINED_SCENARIOS
        assert len(config.PREDEFINED_SCENARIOS) >= 6

    def test_fx_anchor_rates(self):
        assert config.FX_ANCHOR_RATES["CNY"] > 0
        assert config.FX_ANCHOR_RATES["INR"] > 0
        assert config.FX_ANCHOR_RATES["EUR"] > 0

    def test_discount_rate_reasonable(self):
        assert 0.01 <= config.DEFAULT_DISCOUNT_RATE <= 0.30

    def test_logistics_modes(self):
        assert "Sea" in config.LOGISTICS_MODES
        assert "Air" in config.LOGISTICS_MODES

    def test_risk_weights_sum_to_one(self):
        total = sum(config.RISK_WEIGHTS.values())
        assert abs(total - 1.0) < 0.01

    def test_supplier_scorecard_weights(self):
        total = sum(config.SUPPLIER_SCORECARD_WEIGHTS.values())
        assert abs(total - 1.0) < 0.01

    def test_tco_layer_weights(self):
        total = sum(config.TCO_LAYER_WEIGHTS.values())
        assert abs(total - 1.0) < 0.01
