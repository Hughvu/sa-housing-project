from pathlib import Path

import pandas as pd
import pandas.testing as pdt
import pytest

import src.pipeline as pipeline


LGA_OUTPUT_COLUMNS = [
    "LGA_Code",
    "LGA_Name",
    "Total_Median",
    "Unit_Total_Median",
    "House_Total_Median",
    "Total_Count",
    "Sample_Quality",
    "Median_Weekly_Household_Income_2021",
    "Rent_to_Income_Proxy",
    "Rent_to_Income_Proxy_Pct",
    "Population_2024",
    "Population_2025",
    "Population_Change",
    "Population_Growth_Pct",
    "Approvals_2024_25",
    "Approvals_2025_26_FYTD",
    "Approvals_per_1000",
    "Affordability_Pressure_Score",
    "Demand_Pressure_Score",
    "Supply_Gap_Score",
    "Weighted_Component_Score",
    "Housing_Pressure_Index",
    "Housing_Pressure_Category",
    "Eligible_for_Score",
    "Complete_Score",
]


def test_lga_output_schema_eligibility_and_order_are_deterministic() -> None:
    first = pipeline.build_lga_dashboard().reset_index(drop=True)
    second = pipeline.build_lga_dashboard().reset_index(drop=True)

    assert first.columns.tolist() == LGA_OUTPUT_COLUMNS
    pdt.assert_frame_equal(first, second)
    assert first["LGA_Code"].is_unique
    assert first["Eligible_for_Score"].equals(first["Total_Count"].ge(10))
    assert first.loc[first["Complete_Score"], "Eligible_for_Score"].all()
    assert first["Housing_Pressure_Index"].dropna().is_monotonic_decreasing
    assert first["Population_2025"].dropna().gt(0).all()
    assert first["Approvals_per_1000"].dropna().ge(0).all()
    assert not first["LGA_Name"].str.contains(
        "South Australia|Migratory", case=False, regex=True
    ).any()


def test_state_ytd_uses_latest_available_month_not_april(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dates = pd.to_datetime(
        [
            *(f"2024-{month:02d}-01" for month in range(1, 7)),
            *(f"2025-{month:02d}-01" for month in range(1, 7)),
        ]
    )
    source = pd.DataFrame(
        {
            "Series ID": dates,
            "A422466C": range(100, 112),
        }
    )
    monkeypatch.setattr(
        pipeline.pd,
        "read_excel",
        lambda *args, **kwargs: source.copy(),
    )

    monthly, annual, ytd = pipeline.build_state_approvals()

    assert monthly["Month"].max() == pd.Timestamp("2025-06-01")
    assert annual["Months_Covered"].eq(6).all()
    assert annual["Year_Label"].str.contains("YTD \\(6 months\\)", regex=True).all()
    assert ytd["Months_Compared"].eq(6).all()
    assert ytd["Comparison_Label"].eq("January–June").all()


def test_state_approvals_reports_missing_required_columns(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        pipeline,
        "_read_excel",
        lambda *args, **kwargs: pd.DataFrame({"Series ID": ["2025-01-01"]}),
    )

    with pytest.raises(ValueError, match=r"missing required columns.*A422466C"):
        pipeline.build_state_approvals()


def test_lga_approvals_rejects_narrow_worksheet(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        pipeline,
        "_read_excel",
        lambda *args, **kwargs: pd.DataFrame([[1, 2, 3, 4]]),
    )

    with pytest.raises(ValueError, match=r"has 4 columns; expected at least 5"):
        pipeline.load_lga_approvals(Path("approvals.xlsx"), "test period")


def test_duplicate_source_join_keys_are_rejected() -> None:
    source = pd.DataFrame(
        {
            "LGA_Code": [40001, 40001, 40002],
            "Value": [1, 2, 3],
        }
    )

    with pytest.raises(ValueError, match=r"contains duplicate keys.*40001"):
        pipeline._require_unique(source, "LGA_Code", source="Test source")


def test_missing_required_lga_key_coverage_is_rejected() -> None:
    reference = pd.DataFrame({"LGA_Code": [40001, 40002, 40003]})
    candidate = pd.DataFrame({"LGA_Code": [40001]})

    with pytest.raises(
        ValueError,
        match=r"missing 2 required LGA_Code values.*40002.*40003",
    ):
        pipeline._require_key_coverage(
            reference,
            candidate,
            "LGA_Code",
            source="Test source",
        )


def test_safe_ratio_rejects_zero_negative_and_non_finite_denominators() -> None:
    numerator = pd.Series([10, 10, 10, 10, 10, 10])
    denominator = pd.Series([2, 0, -2, float("inf"), float("-inf"), None])

    result = pipeline._safe_ratio(numerator, denominator, scale=100)

    assert result.iloc[0] == 500
    assert result.iloc[1:].isna().all()


def test_safe_ratio_rejects_non_finite_numerators() -> None:
    numerator = pd.Series([10, float("inf"), float("-inf"), None])
    denominator = pd.Series([2, 2, 2, 2])

    result = pipeline._safe_ratio(numerator, denominator)

    assert result.iloc[0] == 5
    assert result.iloc[1:].isna().all()


def test_atomic_writer_removes_temporary_file_when_csv_write_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = Path("tests") / "atomic_writer_failure.csv"
    temporary_pattern = f".{target.name}.*.tmp"

    def fail_to_csv(*args: object, **kwargs: object) -> None:
        raise OSError("simulated write failure")

    monkeypatch.setattr(pd.DataFrame, "to_csv", fail_to_csv)

    with pytest.raises(OSError, match="simulated write failure"):
        pipeline._write_csv_atomic(pd.DataFrame({"value": [1]}), target)

    assert not target.exists()
    assert not list(target.parent.glob(temporary_pattern))


def test_pipeline_regenerates_committed_dashboard_outputs(
) -> None:
    expected_lga = pd.read_csv(
        pipeline.PROCESSED / "dashboard_lga_pressure.csv"
    )
    expected_monthly = pd.read_csv(
        pipeline.PROCESSED / "dashboard_monthly_approvals.csv",
        parse_dates=["Month"],
    )
    expected_annual = pd.read_csv(
        pipeline.PROCESSED / "dashboard_annual_approvals.csv"
    )
    expected_ytd = pd.read_csv(
        pipeline.PROCESSED / "dashboard_ytd_approvals.csv"
    )

    actual_lga = pipeline.build_lga_dashboard().reset_index(drop=True)
    actual_monthly, actual_annual, actual_ytd = pipeline.build_state_approvals()

    pdt.assert_frame_equal(actual_lga, expected_lga, check_dtype=False)
    pdt.assert_frame_equal(
        actual_monthly.reset_index(drop=True),
        expected_monthly,
        check_dtype=False,
    )
    pdt.assert_frame_equal(
        actual_annual.reset_index(drop=True),
        expected_annual,
        check_dtype=False,
    )
    pdt.assert_frame_equal(
        actual_ytd.reset_index(drop=True),
        expected_ytd,
        check_dtype=False,
    )


def _valid_lga_frame(size: int = 50) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "LGA_Code": range(40000, 40000 + size),
            "LGA_Name": [f"Area {index}" for index in range(size)],
            "Complete_Score": [True] * size,
        }
    )


def _valid_monthly_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Month": pd.to_datetime(["2025-01-01", "2025-02-01"]),
            "Dwelling_Approvals": [100, 110],
        }
    )


def test_validation_rejects_duplicate_lga_codes() -> None:
    lga = _valid_lga_frame()
    lga.loc[1, "LGA_Code"] = lga.loc[0, "LGA_Code"]

    with pytest.raises(ValueError, match="Duplicate LGA codes"):
        pipeline.validate_outputs(lga, _valid_monthly_frame())


def test_validation_rejects_state_aggregate() -> None:
    lga = _valid_lga_frame()
    lga.loc[0, "LGA_Name"] = "South Australia"

    with pytest.raises(ValueError, match="State aggregate"):
        pipeline.validate_outputs(lga, _valid_monthly_frame())


def test_validation_rejects_too_few_complete_scores() -> None:
    lga = _valid_lga_frame()
    lga.loc[49, "Complete_Score"] = False

    with pytest.raises(ValueError, match="Fewer than 50"):
        pipeline.validate_outputs(lga, _valid_monthly_frame())


def test_validation_rejects_non_chronological_months() -> None:
    monthly = _valid_monthly_frame().iloc[::-1].reset_index(drop=True)

    with pytest.raises(ValueError, match="not chronological"):
        pipeline.validate_outputs(_valid_lga_frame(), monthly)


def test_validation_rejects_negative_approvals() -> None:
    monthly = _valid_monthly_frame()
    monthly.loc[0, "Dwelling_Approvals"] = -1

    with pytest.raises(ValueError, match="Negative dwelling approvals"):
        pipeline.validate_outputs(_valid_lga_frame(), monthly)
