"""Reproducible data pipeline for the SA housing dashboard."""

from __future__ import annotations

import os
import re
import tempfile
import zipfile
from pathlib import Path
from typing import Iterable

import pandas as pd

from src.scoring_model import calculate_pressure_index, sample_quality


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"

RENT_FILE = RAW / "rent" / "private-rental-report-2025-12.xlsx"
APPROVALS_STATE_FILE = RAW / "approvals" / "8731004.xlsx"
APPROVALS_LGA_FULL_FILE = RAW / "approvals" / "87310do016_202604.xlsx"
APPROVALS_LGA_YTD_FILE = RAW / "approvals" / "87310do017_202604.xlsx"
POPULATION_FILE = RAW / "population" / "32180DS0002_2024-25.xlsx"
INCOME_ARCHIVE = RAW / "income" / "2021_GCP_LGA_for_SA_short-header.zip"

RENT_COLUMNS = {
    0: "Rental_LGA_Label",
    9: "Unit_Total_Count",
    10: "Unit_Total_Median",
    19: "House_Total_Count",
    20: "House_Total_Median",
    25: "Total_Count",
    26: "Total_Median",
}

NAME_ALIASES = {
    "berriandbarmera": "berribarmera",
    "lowereyrepeninsula": "lowereyrepeninsula",
    "naracoorteandlucindale": "naracoortelucindale",
    "norwoodpaynehamstpeters": "norwoodpaynehamandstpeters",
    "portpiriecityanddists": "portpirie",
}


def _require_file(path: Path) -> None:
    """Raise a source-specific error when an expected input is unavailable."""

    if not path.is_file():
        raise FileNotFoundError(f"Required source file not found: {path}")


def _read_excel(
    path: Path,
    *,
    sheet_name: str,
    header: int | None,
) -> pd.DataFrame:
    """Read an expected worksheet and translate common source errors."""

    _require_file(path)
    try:
        return pd.read_excel(path, sheet_name=sheet_name, header=header)
    except ValueError as exc:
        raise ValueError(
            f"Could not read worksheet {sheet_name!r} from {path.name}: {exc}"
        ) from exc


def _require_columns(
    frame: pd.DataFrame,
    columns: Iterable[object],
    *,
    source: str,
) -> None:
    """Fail with a concise schema error before selecting named columns."""

    required = list(columns)
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"{source} is missing required columns: {missing}")


def _require_column_positions(
    frame: pd.DataFrame,
    positions: Iterable[int],
    *,
    source: str,
) -> None:
    """Validate positional source extraction against the workbook width."""

    required = list(positions)
    if not required:
        return
    highest = max(required)
    if frame.shape[1] <= highest:
        raise ValueError(
            f"{source} has {frame.shape[1]} columns; expected at least {highest + 1}."
        )


def _require_unique(
    frame: pd.DataFrame,
    columns: str | list[str],
    *,
    source: str,
) -> None:
    """Reject duplicate join keys before they can obscure source problems."""

    key_columns = [columns] if isinstance(columns, str) else columns
    duplicated = frame.duplicated(subset=key_columns, keep=False)
    if duplicated.any():
        keys = frame.loc[duplicated, key_columns]
        examples = keys.drop_duplicates().head(5).to_dict(orient="records")
        raise ValueError(f"{source} contains duplicate keys: {examples}")


def _require_key_coverage(
    reference: pd.DataFrame,
    candidate: pd.DataFrame,
    key: str,
    *,
    source: str,
) -> None:
    """Ensure every reference key exists in a required join source."""

    missing = reference.loc[~reference[key].isin(candidate[key]), key].drop_duplicates()
    if not missing.empty:
        raise ValueError(
            f"{source} is missing {len(missing)} required {key} values; "
            f"examples: {missing.head(5).tolist()}"
        )


def _safe_ratio(
    numerator: pd.Series,
    denominator: pd.Series,
    *,
    scale: float = 1.0,
) -> pd.Series:
    """Divide only by finite positive denominators, preserving missing values."""

    numeric_numerator = pd.to_numeric(numerator, errors="coerce")
    numeric_denominator = pd.to_numeric(denominator, errors="coerce")
    valid = (
        numeric_numerator.abs().ne(float("inf"))
        & numeric_denominator.gt(0)
        & numeric_denominator.abs().ne(float("inf"))
    )
    result = pd.Series(float("nan"), index=numerator.index, dtype="float64")
    result.loc[valid] = (
        numeric_numerator.loc[valid] / numeric_denominator.loc[valid] * scale
    )
    return result


def _write_csv_atomic(frame: pd.DataFrame, path: Path) -> None:
    """Write a CSV atomically so an interrupted run cannot leave a partial file."""

    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    os.close(descriptor)
    temporary_path = Path(temporary_name)
    try:
        frame.to_csv(temporary_path, index=False)
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def normalise_lga_name(value: str) -> str:
    """Normalise known formatting differences between government sources."""

    text = re.sub(r"\s+Total$", "", str(value).strip())
    text = re.sub(r"\s*\([^)]*\)", "", text)
    text = text.replace("Municipal Council of ", "").replace("The ", "")
    key = re.sub(r"[^a-z0-9]", "", text.lower())
    return NAME_ALIASES.get(key, key)


def _numeric(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    for column in columns:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame


def load_lga_rent() -> pd.DataFrame:
    """Extract published LGA totals from the SA Housing Trust workbook."""

    raw = _read_excel(RENT_FILE, sheet_name="SLA", header=None)
    _require_column_positions(
        raw,
        RENT_COLUMNS,
        source=f"{RENT_FILE.name} worksheet 'SLA'",
    )
    if len(raw) <= 15:
        raise ValueError(
            f"{RENT_FILE.name} worksheet 'SLA' has no rows below the expected header."
        )
    rent = raw.iloc[15:, list(RENT_COLUMNS)].rename(columns=RENT_COLUMNS).copy()
    rent = rent[rent["Rental_LGA_Label"].notna()]
    rent["Rental_LGA_Label"] = rent["Rental_LGA_Label"].astype(str).str.strip()
    rent = rent[rent["Rental_LGA_Label"].str.endswith(" Total")]
    rent = rent[rent["Rental_LGA_Label"] != "Grand Total"]
    for column in RENT_COLUMNS.values():
        rent[column] = rent[column].where(rent[column].ne("*"), pd.NA)
    rent = _numeric(rent, list(RENT_COLUMNS.values())[1:])
    rent["LGA_Key"] = rent["Rental_LGA_Label"].map(normalise_lga_name)
    rent["Sample_Quality"] = rent["Total_Count"].apply(sample_quality)
    _require_unique(rent, "LGA_Key", source="Rental LGA data")
    return rent.reset_index(drop=True)


def load_lga_approvals(path: Path, period_label: str) -> pd.DataFrame:
    """Extract LGA dwelling approvals from an ABS small-area cube."""

    raw = _read_excel(path, sheet_name="Table_1", header=4)
    _require_column_positions(
        raw,
        [0, 1, 4],
        source=f"{path.name} worksheet 'Table_1'",
    )
    approvals = raw.iloc[:, [0, 1, 4]].copy()
    approvals.columns = ["LGA_Code", "LGA_Name", "Dwelling_Approvals"]
    approvals["LGA_Code"] = pd.to_numeric(approvals["LGA_Code"], errors="coerce")
    approvals["Dwelling_Approvals"] = pd.to_numeric(
        approvals["Dwelling_Approvals"], errors="coerce"
    )
    approvals = approvals[
        approvals["LGA_Code"].between(40000, 49999, inclusive="both")
        & approvals["LGA_Name"].notna()
        & approvals["LGA_Name"].ne("Migratory - Offshore - Shipping (SA)")
    ].copy()
    approvals["LGA_Code"] = approvals["LGA_Code"].astype(int)
    approvals["LGA_Key"] = approvals["LGA_Name"].map(normalise_lga_name)
    approvals["Approval_Period"] = period_label
    _require_unique(approvals, "LGA_Code", source=f"Approvals data ({period_label})")
    return approvals.reset_index(drop=True)


def load_population() -> pd.DataFrame:
    """Load 2024 and 2025 LGA estimated resident population for SA."""

    raw = _read_excel(POPULATION_FILE, sheet_name="Table 4", header=5)
    _require_column_positions(
        raw,
        range(6),
        source=f"{POPULATION_FILE.name} worksheet 'Table 4'",
    )
    population = raw.iloc[:, :6].copy()
    population.columns = [
        "LGA_Code",
        "Population_LGA_Name",
        "Population_2024",
        "Population_2025",
        "Population_Change",
        "Population_Growth_Pct",
    ]
    population["LGA_Code"] = pd.to_numeric(population["LGA_Code"], errors="coerce")
    population = population[
        population["LGA_Code"].between(40000, 49999, inclusive="both")
    ].copy()
    population["LGA_Code"] = population["LGA_Code"].astype(int)
    population = _numeric(
        population,
        [
            "Population_2024",
            "Population_2025",
            "Population_Change",
            "Population_Growth_Pct",
        ],
    )
    _require_unique(population, "LGA_Code", source="Population data")
    return population.reset_index(drop=True)


def load_income() -> pd.DataFrame:
    """Load 2021 Census median weekly household income by LGA."""

    _require_file(INCOME_ARCHIVE)
    try:
        with zipfile.ZipFile(INCOME_ARCHIVE) as archive:
            matches = [
                name
                for name in archive.namelist()
                if name.endswith("2021Census_G02_SA_LGA.csv")
            ]
            if len(matches) != 1:
                raise ValueError(
                    "Expected exactly one ABS Census G02 SA LGA CSV in "
                    f"{INCOME_ARCHIVE.name}; found {len(matches)}."
                )
            with archive.open(matches[0]) as source:
                income_header = pd.read_csv(source, nrows=0)
            income_columns = ["LGA_CODE_2021", "Median_tot_hhd_inc_weekly"]
            _require_columns(
                income_header,
                income_columns,
                source=INCOME_ARCHIVE.name,
            )
            with archive.open(matches[0]) as source:
                income = pd.read_csv(source, usecols=income_columns)
    except zipfile.BadZipFile as exc:
        raise ValueError(
            f"Income source is not a valid ZIP archive: {INCOME_ARCHIVE}"
        ) from exc
    income["LGA_Code"] = pd.to_numeric(
        income["LGA_CODE_2021"].astype("string").str.replace("LGA", "", regex=False),
        errors="coerce",
    )
    income = income[income["LGA_Code"].notna()].copy()
    income["LGA_Code"] = income["LGA_Code"].astype(int)
    income = income.rename(
        columns={"Median_tot_hhd_inc_weekly": "Median_Weekly_Household_Income_2021"}
    )
    income["Median_Weekly_Household_Income_2021"] = pd.to_numeric(
        income["Median_Weekly_Household_Income_2021"], errors="coerce"
    )
    _require_unique(income, "LGA_Code", source="Census household income data")
    return income[["LGA_Code", "Median_Weekly_Household_Income_2021"]]


def build_lga_dashboard() -> pd.DataFrame:
    """Join rent, approvals, population and income at consistent LGA geography."""

    rent = load_lga_rent()
    full = load_lga_approvals(APPROVALS_LGA_FULL_FILE, "2024-25")
    ytd = load_lga_approvals(APPROVALS_LGA_YTD_FILE, "2025-26 FYTD")
    population = load_population()
    income = load_income()

    _require_key_coverage(
        full,
        ytd,
        "LGA_Code",
        source="2025-26 FYTD approvals data",
    )
    _require_key_coverage(full, population, "LGA_Code", source="Population data")
    _require_key_coverage(full, income, "LGA_Code", source="Census income data")

    full = full.rename(columns={"Dwelling_Approvals": "Approvals_2024_25"})
    ytd = ytd[["LGA_Code", "Dwelling_Approvals"]].rename(
        columns={"Dwelling_Approvals": "Approvals_2025_26_FYTD"}
    )
    joined = full.merge(ytd, on="LGA_Code", how="left", validate="one_to_one")
    joined = joined.merge(population, on="LGA_Code", how="left", validate="one_to_one")
    joined = joined.merge(income, on="LGA_Code", how="left", validate="one_to_one")
    joined = joined.merge(
        rent.drop(columns=["Rental_LGA_Label"]),
        on="LGA_Key",
        how="left",
        validate="one_to_one",
    )

    joined["Approvals_per_1000"] = _safe_ratio(
        joined["Approvals_2024_25"],
        joined["Population_2025"],
        scale=1000,
    ).round(2)
    joined["Rent_to_Income_Proxy"] = _safe_ratio(
        joined["Total_Median"],
        joined["Median_Weekly_Household_Income_2021"],
    ).round(4)
    joined["Rent_to_Income_Proxy_Pct"] = (
        joined["Rent_to_Income_Proxy"] * 100
    ).round(1)
    joined["Eligible_for_Score"] = joined["Total_Count"].ge(10)
    joined = calculate_pressure_index(joined)
    joined["Complete_Score"] = joined["Housing_Pressure_Index"].notna()

    columns = [
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
    return joined[columns].sort_values(
        "Housing_Pressure_Index", ascending=False, na_position="last"
    )


def build_state_approvals() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Create monthly, annual-labelled and comparable YTD state series."""

    raw = _read_excel(APPROVALS_STATE_FILE, sheet_name="Data1", header=9)
    _require_columns(
        raw,
        ["Series ID", "A422466C"],
        source=f"{APPROVALS_STATE_FILE.name} worksheet 'Data1'",
    )
    monthly = raw[["Series ID", "A422466C"]].copy()
    monthly.columns = ["Month", "Dwelling_Approvals"]
    monthly["Month"] = pd.to_datetime(monthly["Month"], errors="coerce")
    monthly["Dwelling_Approvals"] = pd.to_numeric(
        monthly["Dwelling_Approvals"], errors="coerce"
    )
    monthly = monthly[
        (monthly["Month"] >= "2021-01-01")
        & monthly["Month"].notna()
        & monthly["Dwelling_Approvals"].notna()
    ].sort_values("Month")
    if monthly.empty:
        raise ValueError("State approvals source contains no usable data from 2021.")
    monthly["Year"] = monthly["Month"].dt.year
    monthly["Month_Number"] = monthly["Month"].dt.month
    monthly["Month_Name"] = monthly["Month"].dt.strftime("%b %Y")
    monthly["Rolling_3_Month_Avg"] = (
        monthly["Dwelling_Approvals"].rolling(3, min_periods=3).mean().round(1)
    )
    monthly["Series_Type"] = "Original"

    annual = (
        monthly.groupby("Year", as_index=False)
        .agg(
            Dwelling_Approvals=("Dwelling_Approvals", "sum"),
            Months_Covered=("Month", "count"),
        )
        .sort_values("Year")
    )
    annual["Period_Status"] = annual["Months_Covered"].map(
        lambda months: "Full calendar year" if months == 12 else "Year to date"
    )
    annual["Year_Label"] = annual.apply(
        lambda row: str(row["Year"])
        if row["Months_Covered"] == 12
        else f"{row['Year']} YTD ({int(row['Months_Covered'])} months)",
        axis=1,
    )

    latest_month = int(monthly.iloc[-1]["Month_Number"])
    ytd = monthly[monthly["Month_Number"] <= latest_month].copy()
    ytd = (
        ytd.groupby("Year", as_index=False)
        .agg(
            YTD_Dwelling_Approvals=("Dwelling_Approvals", "sum"),
            Months_Compared=("Month", "count"),
        )
        .sort_values("Year")
    )
    ytd["Comparison_Label"] = f"January–{monthly.iloc[-1]['Month'].strftime('%B')}"
    return monthly, annual, ytd


def validate_outputs(lga: pd.DataFrame, monthly: pd.DataFrame) -> None:
    """Fail the pipeline when important integrity conditions are not met."""

    _require_columns(
        lga,
        ["LGA_Code", "LGA_Name", "Complete_Score"],
        source="LGA dashboard output",
    )
    _require_columns(
        monthly,
        ["Month", "Dwelling_Approvals"],
        source="Monthly approvals output",
    )
    if lga.empty:
        raise ValueError("LGA dashboard output is empty.")
    if monthly.empty:
        raise ValueError("Monthly approvals output is empty.")
    if lga["LGA_Code"].duplicated().any():
        raise ValueError("Duplicate LGA codes in dashboard output.")
    if lga["LGA_Name"].str.contains("South Australia", case=False).any():
        raise ValueError("State aggregate leaked into LGA output.")
    if lga["Complete_Score"].sum() < 50:
        raise ValueError("Fewer than 50 LGAs have complete, eligible scoring inputs.")
    if not monthly["Month"].is_monotonic_increasing:
        raise ValueError("Monthly approvals are not chronological.")
    if (monthly["Dwelling_Approvals"] < 0).any():
        raise ValueError("Negative dwelling approvals detected.")


def run_pipeline() -> None:
    """Build all processed files consumed by the dashboard."""

    PROCESSED.mkdir(parents=True, exist_ok=True)
    lga = build_lga_dashboard()
    monthly, annual, ytd = build_state_approvals()
    validate_outputs(lga, monthly)

    _write_csv_atomic(lga, PROCESSED / "dashboard_lga_pressure.csv")
    _write_csv_atomic(monthly, PROCESSED / "dashboard_monthly_approvals.csv")
    _write_csv_atomic(annual, PROCESSED / "dashboard_annual_approvals.csv")
    _write_csv_atomic(ytd, PROCESSED / "dashboard_ytd_approvals.csv")

    quality = pd.DataFrame(
        [
            {"Check": "LGAs in output", "Value": len(lga)},
            {"Check": "LGAs with complete score", "Value": int(lga["Complete_Score"].sum())},
            {
                "Check": "LGAs with suppressed / low rental sample",
                "Value": int(lga["Sample_Quality"].eq("Suppressed / low sample").sum()),
            },
            {"Check": "Latest state approval month", "Value": monthly["Month"].max().date()},
        ]
    )
    _write_csv_atomic(quality, PROCESSED / "data_quality_summary.csv")


if __name__ == "__main__":
    run_pipeline()
