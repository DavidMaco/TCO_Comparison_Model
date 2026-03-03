"""
TCO Comparison Model — Supplier Scorecard Engine
Statistically normalized, weighted supplier evaluation across
quality, delivery, service, warranty, price, and local support dimensions.

Supports Chinese, Indian, and European OEM comparison with
validated normalization and transparent weighting.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

import config
from utils.logging_config import get_logger, AuditLogger
from utils.run_metadata import RunMetadata

log = get_logger("supplier_scorecard")
audit = AuditLogger()


# ─── Scorecard Dimension Definitions ─────────────────────────────────

DIMENSIONS = {
    "quality_index": {
        "description": "Product quality & defect rate",
        "higher_is_better": True,
        "min_val": 0.0,
        "max_val": 100.0,
    },
    "delivery_reliability": {
        "description": "On-time delivery percentage",
        "higher_is_better": True,
        "min_val": 0.0,
        "max_val": 100.0,
    },
    "service_responsiveness": {
        "description": "Service response time score (1-10)",
        "higher_is_better": True,
        "min_val": 1.0,
        "max_val": 10.0,
    },
    "warranty_performance": {
        "description": "Warranty claim acceptance & resolution rate",
        "higher_is_better": True,
        "min_val": 0.0,
        "max_val": 100.0,
    },
    "price_competitiveness": {
        "description": "Price vs market benchmark (lower is better)",
        "higher_is_better": False,
        "min_val": 0.5,
        "max_val": 2.0,
    },
    "local_support": {
        "description": "Local service infrastructure availability (1-10)",
        "higher_is_better": True,
        "min_val": 1.0,
        "max_val": 10.0,
    },
}


def _minmax_normalize(value: float, dim_config: dict) -> float:
    """Min-max normalize a value to 0-1 scale."""
    min_v = dim_config["min_val"]
    max_v = dim_config["max_val"]
    if max_v == min_v:
        return 0.5
    normalized = (value - min_v) / (max_v - min_v)
    if not dim_config["higher_is_better"]:
        normalized = 1.0 - normalized
    return max(0.0, min(1.0, normalized))


def _percentile_rank(values: pd.Series) -> pd.Series:
    """Compute percentile rank (0–100) within a group."""
    return values.rank(pct=True) * 100


class SupplierScorecard:
    """
    Evaluates and ranks suppliers using weighted multi-criteria scoring.
    All scores are normalized (0–1) and weighted per config.
    """

    def __init__(self, weights: dict[str, float] | None = None):
        self.weights = weights or config.SUPPLIER_SCORECARD_WEIGHTS
        # Validate weights sum
        w_sum = sum(self.weights.values())
        if abs(w_sum - 1.0) > 0.01:
            log.warning("Scorecard weights sum to %.3f (expected 1.00) — normalizing", w_sum)
            self.weights = {k: v / w_sum for k, v in self.weights.items()}

    def score_supplier(self, supplier_data: dict[str, Any]) -> dict[str, Any]:
        """Score a single supplier across all dimensions."""
        scores = {}
        for dim, dim_cfg in DIMENSIONS.items():
            raw = supplier_data.get(dim, dim_cfg["min_val"])
            scores[f"{dim}_raw"] = raw
            scores[f"{dim}_normalized"] = _minmax_normalize(raw, dim_cfg)

        # Weighted composite
        composite = sum(
            scores[f"{dim}_normalized"] * self.weights.get(dim, 0)
            for dim in DIMENSIONS
        )
        scores["composite_score"] = composite

        return {
            "supplier_id": supplier_data.get("supplier_id", ""),
            "supplier_name": supplier_data.get("supplier_name", ""),
            "region": supplier_data.get("region", ""),
            **scores,
            "weights_used": dict(self.weights),
        }

    def score_multiple(self, suppliers: list[dict[str, Any]]) -> pd.DataFrame:
        """Score and rank multiple suppliers."""
        results = [self.score_supplier(s) for s in suppliers]
        df = pd.DataFrame(results)

        if not df.empty:
            df["composite_rank"] = df["composite_score"].rank(ascending=False, method="min").astype(int)
            df["percentile"] = _percentile_rank(df["composite_score"])
            df = df.sort_values("composite_score", ascending=False)

        return df

    def regional_comparison(self, suppliers: list[dict[str, Any]]) -> pd.DataFrame:
        """Aggregate scorecard by region for China vs India vs Europe comparison."""
        scored = self.score_multiple(suppliers)
        if scored.empty:
            return pd.DataFrame()

        agg = scored.groupby("region").agg(
            avg_composite=("composite_score", "mean"),
            min_composite=("composite_score", "min"),
            max_composite=("composite_score", "max"),
            supplier_count=("supplier_id", "count"),
            **{
                f"avg_{dim}_norm": (f"{dim}_normalized", "mean")
                for dim in DIMENSIONS
            },
        ).reset_index()
        agg["region_rank"] = agg["avg_composite"].rank(ascending=False, method="min").astype(int)
        return agg.sort_values("avg_composite", ascending=False)

    def generate_report(
        self,
        suppliers: list[dict[str, Any]],
        run_meta: RunMetadata | None = None,
    ) -> dict[str, Any]:
        """Full scorecard report with individual + regional summaries."""
        meta = run_meta or RunMetadata(scenario="supplier_scorecard")
        individual = self.score_multiple(suppliers)
        regional = self.regional_comparison(suppliers)

        report = {
            "individual_scores": individual.to_dict("records"),
            "regional_summary": regional.to_dict("records"),
            "dimensions": {k: v["description"] for k, v in DIMENSIONS.items()},
            "weights": self.weights,
            "total_suppliers_evaluated": len(suppliers),
            "evidence_class": "simulated_estimate",
            "run_metadata": meta.seal({"n_suppliers": len(suppliers)}),
        }

        audit.record("supplier_scorecard_generated", {
            "n_suppliers": len(suppliers),
            "regions": list(individual["region"].unique()) if not individual.empty else [],
            "top_supplier": individual.iloc[0]["supplier_name"] if not individual.empty else None,
        }, run_id=meta.run_id)

        log.info("Supplier scorecard: %d suppliers evaluated across %d regions",
                 len(suppliers), individual["region"].nunique() if not individual.empty else 0)
        return report
