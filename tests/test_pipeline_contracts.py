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
    "Unit_Total_Count",
    "House_Total_Count",
    "Sample_Quality",
    "Median_Weekly_Household_Income_2021",
    "Rent_to_Income_Proxy",
    "Rent_to_Income_Proxy_Pct",
    "Unit_Rent_to_Income_Proxy",
    "Unit_Rent_to_Income_Proxy_Pct",
    "House_Rent_to_Income_Proxy",
    "House_Rent_to_Income_Proxy_Pct",
    "House_Unit_Rent_Gap",
    "House_Unit_Rent_Premium_Pct",
    "Population_2024",
    "Population_2025",
    "Population_Change",
    "Population_Growth_Pct",
    "Natural_Increase_2024_25",
    "Net_Internal_Migration_2024_25",
    "Net_Overseas_Migration_2024_25",
    "Net_Migration_2024_25",
    "Area_km2",
    "Population_Density_2025",
    "House_Approvals_2024_25",
    "Other_Residential_Approvals_2024_25",
    "Residual_Approval_Units_2024_25",
    "Approvals_2024_25",
    "Approvals_2025_26_FYTD",
    "House_Approvals_per_1000",
    "Other_Residential_Approvals_per_1000",
    "Approvals_per_1000",
    "Other_Residential_Approval_Share_Pct",
    "Approvals_per_100_New_Residents",
    "Affordability_Pressure_Score",
    "Demand_Pressure_Score",
    "Supply_Gap_Score",
    "Weighted_Component_Score",
    "Housing_Pressure_Index",
    "Housing_Pressure_Category",
    "Eligible_for_Score",
    "Complete_Score",
]

MONTHLY_OUTPUT_COLUMNS = [
    "Month",
    "House_Approvals",
    "Non_House_Approvals",
    "Dwelling_Approvals",
    "Year",
    "Month_Number",
    "Month_Name",
    "Rolling_3_Month_Avg",
    "Non_House_Approval_Share_Pct",
    "Rolling_12_Month_Total",
    "Monthly_YoY_Change_Pct",
    "Rolling_12_Month_YoY_Change_Pct",
    "Series_Type",
]

ANNUAL_OUTPUT_COLUMNS = [
    "Year",
    "Dwelling_Approvals",
    "Months_Covered",
    "Period_Status",
    "Year_Label",
]

YTD_OUTPUT_COLUMNS = [
    "Year",
    "YTD_Dwelling_Approvals",
    "Months_Compared",
    "Prior_Year_YTD_Dwelling_Approvals",
    "Prior_Year_Months_Compared",
    "YTD_YoY_Change_Pct",
    "Comparison_Label",
]


def _state_source(dates: pd.DatetimeIndex, totals: list[int]) -> pd.DataFrame:
    houses = [round(total * 0.6) for total in totals]
    non_houses = [total - house for total, house in zip(totals, houses)]
    return pd.DataFrame(
        {
            "Series ID": dates,
            "A418757A": houses,
            "A421628R": non_houses,
            "A422466C": totals,
        }
    )


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
    population_components = (
        first["Natural_Increase_2024_25"]
        + first["Net_Internal_Migration_2024_25"]
        + first["Net_Overseas_Migration_2024_25"]
    )
    assert first["Population_Change"].equals(population_components)
    approval_components = (
        first["House_Approvals_2024_25"]
        + first["Other_Residential_Approvals_2024_25"]
        + first["Residual_Approval_Units_2024_25"]
    )
    assert first["Approvals_2024_25"].equals(approval_components)
    assert (
        first["Other_Residential_Approval_Share_Pct"]
        .dropna()
        .between(0, 100, inclusive="both")
        .all()
    )
    assert first.loc[
        first["Population_Change"].le(0),
        "Approvals_per_100_New_Residents",
    ].isna().all()
    assert first.loc[
        first["Unit_Total_Count"].lt(10),
        "Unit_Rent_to_Income_Proxy",
    ].isna().all()
    assert first.loc[
        first["House_Total_Count"].lt(10),
        "House_Rent_to_Income_Proxy",
    ].isna().all()
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
    source = _state_source(dates, list(range(100, 112)))
    monkeypatch.setattr(
        pipeline.pd,
        "read_excel",
        lambda *args, **kwargs: source.copy(),
    )

    monthly, annual, ytd = pipeline.build_state_approvals()

    assert monthly.columns.tolist() == MONTHLY_OUTPUT_COLUMNS
    assert annual.columns.tolist() == ANNUAL_OUTPUT_COLUMNS
    assert ytd.columns.tolist() == YTD_OUTPUT_COLUMNS
    assert monthly["Month"].max() == pd.Timestamp("2025-06-01")
    assert annual["Months_Covered"].eq(6).all()
    assert annual["Year_Label"].str.contains("YTD \\(6 months\\)", regex=True).all()
    assert ytd["Months_Compared"].eq(6).all()
    assert ytd["Comparison_Label"].eq("January–June").all()


def test_state_rolling_windows_and_twelve_month_changes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dates = pd.date_range("2023-01-01", periods=24, freq="MS")
    source = _state_source(dates, [100] * 12 + [200] * 12)
    monkeypatch.setattr(
        pipeline,
        "_read_excel",
        lambda *args, **kwargs: source.copy(),
    )

    monthly, _, _ = pipeline.build_state_approvals()

    assert monthly["Rolling_12_Month_Total"].iloc[:11].isna().all()
    assert monthly.loc[11, "Rolling_12_Month_Total"] == 1200
    assert monthly["Monthly_YoY_Change_Pct"].iloc[:12].isna().all()
    assert monthly.loc[12, "Monthly_YoY_Change_Pct"] == 100.0
    assert monthly["Rolling_12_Month_YoY_Change_Pct"].iloc[:23].isna().all()
    assert monthly.loc[23, "Rolling_12_Month_YoY_Change_Pct"] == 100.0


def test_ytd_yoy_requires_matched_month_counts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dates = pd.to_datetime(
        [
            *(f"2023-{month:02d}-01" for month in range(1, 7)),
            *(f"2024-{month:02d}-01" for month in range(1, 6)),
            *(f"2025-{month:02d}-01" for month in range(1, 7)),
        ]
    )
    source = _state_source(dates, [100] * 6 + [110] * 5 + [120] * 6)
    monkeypatch.setattr(
        pipeline,
        "_read_excel",
        lambda *args, **kwargs: source.copy(),
    )

    _, _, ytd = pipeline.build_state_approvals()

    assert ytd["Months_Compared"].tolist() == [6, 5, 6]
    assert ytd["YTD_YoY_Change_Pct"].isna().all()


def test_ytd_yoy_calculates_for_matched_month_counts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dates = pd.to_datetime(
        [
            *(f"2024-{month:02d}-01" for month in range(1, 7)),
            *(f"2025-{month:02d}-01" for month in range(1, 7)),
        ]
    )
    source = _state_source(dates, [100] * 6 + [120] * 6)
    monkeypatch.setattr(
        pipeline,
        "_read_excel",
        lambda *args, **kwargs: source.copy(),
    )

    _, _, ytd = pipeline.build_state_approvals()

    current = ytd.loc[ytd["Year"].eq(2025)].iloc[0]
    assert current["Prior_Year_YTD_Dwelling_Approvals"] == 600
    assert current["Prior_Year_Months_Compared"] == 6
    assert current["YTD_YoY_Change_Pct"] == 20.0


def test_state_approvals_reports_missing_required_columns(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        pipeline,
        "_read_excel",
        lambda *args, **kwargs: pd.DataFrame({"Series ID": ["2025-01-01"]}),
    )

    with pytest.raises(
        ValueError,
        match=r"missing required columns.*A418757A.*A421628R.*A422466C",
    ):
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


def test_safe_ratio_distinguishes_zero_from_missing_numerators() -> None:
    result = pipeline._safe_ratio(
        pd.Series([0, None]),
        pd.Series([1000, 1000]),
    )

    assert result.iloc[0] == 0
    assert pd.isna(result.iloc[1])


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
            "Population_Change": [3] * size,
            "Natural_Increase_2024_25": [1] * size,
            "Net_Internal_Migration_2024_25": [1] * size,
            "Net_Overseas_Migration_2024_25": [1] * size,
            "House_Approvals_2024_25": [60] * size,
            "Other_Residential_Approvals_2024_25": [30] * size,
            "Residual_Approval_Units_2024_25": [10] * size,
            "Approvals_2024_25": [100] * size,
            "Other_Residential_Approval_Share_Pct": [30.0] * size,
            "Unit_Total_Count": [20] * size,
            "House_Total_Count": [20] * size,
            "Unit_Rent_to_Income_Proxy": [0.3] * size,
            "House_Rent_to_Income_Proxy": [0.4] * size,
            "House_Unit_Rent_Gap": [100.0] * size,
        }
    )


def _valid_monthly_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Month": pd.to_datetime(["2025-01-01", "2025-02-01"]),
            "Dwelling_Approvals": [100, 110],
            "House_Approvals": [60, 66],
            "Non_House_Approvals": [40, 44],
            "Non_House_Approval_Share_Pct": [40.0, 40.0],
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


def test_validation_rejects_population_component_mismatch() -> None:
    lga = _valid_lga_frame()
    lga.loc[0, "Natural_Increase_2024_25"] = 2

    with pytest.raises(ValueError, match="Population change does not reconcile"):
        pipeline.validate_outputs(lga, _valid_monthly_frame())


def test_validation_rejects_lga_approval_component_mismatch() -> None:
    lga = _valid_lga_frame()
    lga.loc[0, "Residual_Approval_Units_2024_25"] = 9

    with pytest.raises(ValueError, match="approvals do not reconcile"):
        pipeline.validate_outputs(lga, _valid_monthly_frame())


@pytest.mark.parametrize("share", [-0.1, 100.1])
def test_validation_rejects_unbounded_lga_approval_share(share: float) -> None:
    lga = _valid_lga_frame()
    lga.loc[0, "Other_Residential_Approval_Share_Pct"] = share

    with pytest.raises(ValueError, match="share is outside 0–100%"):
        pipeline.validate_outputs(lga, _valid_monthly_frame())


@pytest.mark.parametrize("share", [-0.1, 100.1])
def test_validation_rejects_unbounded_monthly_approval_share(share: float) -> None:
    monthly = _valid_monthly_frame()
    monthly.loc[0, "Non_House_Approval_Share_Pct"] = share

    with pytest.raises(ValueError, match="share is outside 0–100%"):
        pipeline.validate_outputs(_valid_lga_frame(), monthly)


def test_validation_rejects_monthly_component_mismatch_over_tolerance() -> None:
    monthly = _valid_monthly_frame()
    monthly.loc[0, "Non_House_Approvals"] = 38

    with pytest.raises(ValueError, match="components differ from total"):
        pipeline.validate_outputs(_valid_lga_frame(), monthly)


def test_validation_allows_one_unit_monthly_component_rounding_gap() -> None:
    monthly = _valid_monthly_frame()
    monthly.loc[0, "Non_House_Approvals"] = 39

    pipeline.validate_outputs(_valid_lga_frame(), monthly)


def test_validation_enforces_type_specific_sample_thresholds() -> None:
    lga = _valid_lga_frame()
    lga.loc[0, "Unit_Total_Count"] = 9

    with pytest.raises(ValueError, match="bypassed its sample threshold"):
        pipeline.validate_outputs(lga, _valid_monthly_frame())
