import pandas as pd
import pytest

from src.scoring_model import (
    ScoreWeights,
    calculate_pressure_index,
    percentile_score,
    pressure_category,
    sample_quality,
)


def test_percentile_score_direction() -> None:
    values = pd.Series([10, 20, 30])
    assert percentile_score(values).is_monotonic_increasing
    assert percentile_score(values, higher_is_pressure=False).is_monotonic_decreasing


def test_weights_must_sum_to_one() -> None:
    with pytest.raises(ValueError):
        ScoreWeights(0.5, 0.5, 0.5).validate()


def test_ineligible_rows_are_not_scored() -> None:
    frame = pd.DataFrame(
        {
            "Rent_to_Income_Proxy": [0.3, 0.4, 0.8],
            "Population_Growth_Pct": [1.0, 2.0, 9.0],
            "Approvals_per_1000": [10.0, 5.0, 0.1],
            "Eligible_for_Score": [True, True, False],
        }
    )
    result = calculate_pressure_index(frame)
    assert result.loc[:1, "Housing_Pressure_Index"].notna().all()
    assert pd.isna(result.loc[2, "Housing_Pressure_Index"])
    assert result.loc[2, "Housing_Pressure_Category"] == "Not scored"


@pytest.mark.parametrize(
    ("score", "expected"),
    [(80, "Very High"), (60, "High"), (40, "Moderate"), (20, "Low"), (19.9, "Very Low")],
)
def test_pressure_categories(score: float, expected: str) -> None:
    assert pressure_category(score) == expected


def test_sample_quality_rules() -> None:
    assert sample_quality(None) == "Suppressed / low sample"
    assert sample_quality(5) == "Caution (<10 bonds)"
    assert sample_quality(15) == "Moderate (10–19 bonds)"
    assert sample_quality(20) == "Stronger (20+ bonds)"
