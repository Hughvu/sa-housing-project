import math

import pandas as pd
import pytest

from src.scoring_model import (
    ScoreWeights,
    calculate_pressure_index,
    percentile_score,
    pressure_category,
    sample_quality,
)


def test_percentile_score_preserves_nulls_and_averages_ties() -> None:
    values = pd.Series([10.0, 10.0, None, 30.0])

    result = percentile_score(values)

    assert result.iloc[0] == result.iloc[1] == 50.0
    assert pd.isna(result.iloc[2])
    assert result.iloc[3] == 100.0


def test_inverse_percentile_reverses_pressure_direction() -> None:
    values = pd.Series([1.0, 2.0, 3.0])

    result = percentile_score(values, higher_is_pressure=False)

    assert result.tolist() == [66.7, 33.3, 0.0]


def test_all_null_percentile_input_remains_null() -> None:
    result = percentile_score(pd.Series([None, pd.NA], dtype="object"))

    assert result.isna().all()


def test_percentile_score_ignores_non_finite_values() -> None:
    values = pd.Series([10.0, 20.0, float("inf"), float("-inf"), float("nan")])

    result = percentile_score(values)

    assert result.iloc[:2].tolist() == [50.0, 100.0]
    assert result.iloc[2:].isna().all()


@pytest.mark.parametrize(
    "weights",
    [
        ScoreWeights(-0.1, 0.6, 0.5),
        ScoreWeights(0.5, -0.1, 0.6),
        ScoreWeights(0.5, 0.6, -0.1),
        ScoreWeights(0.2, 0.2, 0.2),
        ScoreWeights(float("nan"), 0.5, 0.5),
        ScoreWeights(float("inf"), 0.0, 0.0),
        ScoreWeights(float("-inf"), 1.0, 0.0),
    ],
)
def test_invalid_weights_are_rejected(weights: ScoreWeights) -> None:
    with pytest.raises(ValueError):
        weights.validate()


def test_weight_sum_uses_documented_floating_point_tolerance() -> None:
    ScoreWeights(0.1, 0.2, 0.7000000001).validate()


def test_missing_scoring_column_is_reported() -> None:
    frame = pd.DataFrame(
        {
            "Rent_to_Income_Proxy": [0.3],
            "Population_Growth_Pct": [1.0],
        }
    )

    with pytest.raises(ValueError, match="Approvals_per_1000"):
        calculate_pressure_index(frame)


def test_missing_component_prevents_complete_score() -> None:
    frame = pd.DataFrame(
        {
            "Rent_to_Income_Proxy": [0.3, 0.4],
            "Population_Growth_Pct": [1.0, None],
            "Approvals_per_1000": [10.0, 5.0],
            "Eligible_for_Score": [True, True],
        }
    )

    result = calculate_pressure_index(frame)

    assert math.isfinite(result.loc[0, "Housing_Pressure_Index"])
    assert pd.isna(result.loc[1, "Housing_Pressure_Index"])
    assert result.loc[1, "Housing_Pressure_Category"] == "Not scored"


@pytest.mark.parametrize(
    ("count", "expected"),
    [
        (None, "Suppressed / low sample"),
        (5, "Caution (<10 bonds)"),
        (9, "Caution (<10 bonds)"),
        (10, "Moderate (10–19 bonds)"),
        (19, "Moderate (10–19 bonds)"),
        (20, "Stronger (20+ bonds)"),
    ],
)
def test_sample_quality_boundaries(count: float | None, expected: str) -> None:
    assert sample_quality(count) == expected


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (79.9, "High"),
        (80.0, "Very High"),
        (59.9, "Moderate"),
        (60.0, "High"),
        (39.9, "Low"),
        (40.0, "Moderate"),
        (19.9, "Very Low"),
        (20.0, "Low"),
        (None, "Not scored"),
    ],
)
def test_pressure_category_boundaries(
    score: float | None, expected: str
) -> None:
    assert pressure_category(score) == expected
