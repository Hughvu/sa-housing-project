"""Reproducible data pipeline for the SA housing dashboard."""

from __future__ import annotations

import re
import zipfile
from pathlib import Path

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

    raw = pd.read_excel(RENT_FILE, sheet_name="SLA", header=None)
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
    return rent.reset_index(drop=True)


def load_lga_approvals(path: Path, period_label: str) -> pd.DataFrame:
    """Extract LGA dwelling approvals from an ABS small-area cube."""

    raw = pd.read_excel(path, sheet_name="Table_1", header=4)
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
    return approvals.reset_index(drop=True)


def load_population() -> pd.DataFrame:
    """Load 2024 and 2025 LGA estimated resident population for SA."""

    raw = pd.read_excel(POPULATION_FILE, sheet_name="Table 4", header=5)
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
    return population.reset_index(drop=True)


def load_income() -> pd.DataFrame:
    """Load 2021 Census median weekly household income by LGA."""

    with zipfile.ZipFile(INCOME_ARCHIVE) as archive:
        matches = [
            name for name in archive.namelist() if name.endswith("2021Census_G02_SA_LGA.csv")
        ]
        if len(matches) != 1:
            raise FileNotFoundError("Expected one ABS Census G02 LGA file in archive.")
        with archive.open(matches[0]) as source:
            income = pd.read_csv(
                source,
                usecols=["LGA_CODE_2021", "Median_tot_hhd_inc_weekly"],
            )
    income["LGA_Code"] = pd.to_numeric(
        income["LGA_CODE_2021"].str.replace("LGA", "", regex=False),
        errors="coerce",
    )
    income = income[income["LGA_Code"].notna()].copy()
    income["LGA_Code"] = income["LGA_Code"].astype(int)
    income = income.rename(
        columns={"Median_tot_hhd_inc_weekly": "Median_Weekly_Household_Income_2021"}
    )
    return income[["LGA_Code", "Median_Weekly_Household_Income_2021"]]


def build_lga_dashboard() -> pd.DataFrame:
    """Join rent, approvals, population and income at consistent LGA geography."""

    rent = load_lga_rent()
    full = load_lga_approvals(APPROVALS_LGA_FULL_FILE, "2024-25")
    ytd = load_lga_approvals(APPROVALS_LGA_YTD_FILE, "2025-26 FYTD")
    population = load_population()
    income = load_income()

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

    joined["Approvals_per_1000"] = (
        joined["Approvals_2024_25"] / joined["Population_2025"] * 1000
    ).round(2)
    joined["Rent_to_Income_Proxy"] = (
        joined["Total_Median"] / joined["Median_Weekly_Household_Income_2021"]
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

    raw = pd.read_excel(APPROVALS_STATE_FILE, sheet_name="Data1", header=9)
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

    lga.to_csv(PROCESSED / "dashboard_lga_pressure.csv", index=False)
    monthly.to_csv(PROCESSED / "dashboard_monthly_approvals.csv", index=False)
    annual.to_csv(PROCESSED / "dashboard_annual_approvals.csv", index=False)
    ytd.to_csv(PROCESSED / "dashboard_ytd_approvals.csv", index=False)

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
    quality.to_csv(PROCESSED / "data_quality_summary.csv", index=False)


if __name__ == "__main__":
    run_pipeline()
