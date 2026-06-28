"""Transparent scoring functions for the SA housing pressure dashboard.

The index is relative, not a forecast or a declaration that a household is in
financial stress. Inputs are converted to percentile ranks so unlike measures
can be combined without arbitrary dollar thresholds.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

import pandas as pd


@dataclass(frozen=True)
class ScoreWeights:
    """Weights for the three pressure dimensions."""

    affordability: float = 0.50
    demand: float = 0.25
    supply_gap: float = 0.25

    def validate(self) -> None:
        values = (self.affordability, self.demand, self.supply_gap)
        if any(not isfinite(value) or value < 0 for value in values):
            raise ValueError("Score weights must be finite and non-negative.")
        if abs(sum(values) - 1.0) > 1e-9:
            raise ValueError("Score weights must sum to 1.0.")


def percentile_score(series: pd.Series, *, higher_is_pressure: bool = True) -> pd.Series:
    """Return a 0–100 percentile score while preserving missing values."""

    numeric = pd.to_numeric(series, errors="coerce")
    numeric = numeric.where(numeric.abs().ne(float("inf")))
    score = numeric.rank(method="average", pct=True) * 100
    if not higher_is_pressure:
        score = 100 - score
    return score.round(1)


def pressure_category(score: float | None) -> str:
    """Convert a 0–100 relative score to a five-band category."""

    if pd.isna(score):
        return "Not scored"
    if score >= 80:
        return "Very High"
    if score >= 60:
        return "High"
    if score >= 40:
        return "Moderate"
    if score >= 20:
        return "Low"
    return "Very Low"


def sample_quality(count: float | None) -> str:
    """Classify rental observations using the source's suppression convention."""

    if pd.isna(count):
        return "Suppressed / low sample"
    if count < 10:
        return "Caution (<10 bonds)"
    if count < 20:
        return "Moderate (10–19 bonds)"
    return "Stronger (20+ bonds)"


def calculate_pressure_index(
    frame: pd.DataFrame,
    weights: ScoreWeights = ScoreWeights(),
) -> pd.DataFrame:
    """Calculate the relative LGA housing pressure index.

    Required columns:
      - Rent_to_Income_Proxy: current quarterly median rent divided by 2021
        Census median weekly household income.
      - Population_Growth_Pct: latest annual ERP growth.
      - Approvals_per_1000: full-year dwelling approvals per 1,000 residents.
    """

    weights.validate()
    required = {
        "Rent_to_Income_Proxy",
        "Population_Growth_Pct",
        "Approvals_per_1000",
    }
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Missing scoring columns: {sorted(missing)}")

    result = frame.copy()
    scoring_inputs = result[
        ["Rent_to_Income_Proxy", "Population_Growth_Pct", "Approvals_per_1000"]
    ].copy()
    if "Eligible_for_Score" in result.columns:
        scoring_inputs = scoring_inputs.where(result["Eligible_for_Score"].fillna(False))
    result["Affordability_Pressure_Score"] = percentile_score(
        scoring_inputs["Rent_to_Income_Proxy"]
    )
    result["Demand_Pressure_Score"] = percentile_score(
        scoring_inputs["Population_Growth_Pct"]
    )
    result["Supply_Gap_Score"] = percentile_score(
        scoring_inputs["Approvals_per_1000"], higher_is_pressure=False
    )

    component_columns = [
        "Affordability_Pressure_Score",
        "Demand_Pressure_Score",
        "Supply_Gap_Score",
    ]
    complete = result[component_columns].notna().all(axis=1)
    result["Weighted_Component_Score"] = pd.NA
    result.loc[complete, "Weighted_Component_Score"] = (
        result.loc[complete, "Affordability_Pressure_Score"]
        * weights.affordability
        + result.loc[complete, "Demand_Pressure_Score"] * weights.demand
        + result.loc[complete, "Supply_Gap_Score"] * weights.supply_gap
    ).round(1)
    result["Weighted_Component_Score"] = pd.to_numeric(
        result["Weighted_Component_Score"], errors="coerce"
    )
    result["Housing_Pressure_Index"] = percentile_score(
        result["Weighted_Component_Score"]
    )
    result["Housing_Pressure_Category"] = result[
        "Housing_Pressure_Index"
    ].apply(pressure_category)
    return result
