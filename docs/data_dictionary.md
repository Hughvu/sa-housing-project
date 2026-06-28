# Data dictionary

## `dashboard_lga_pressure.csv`

| Field | Type | Definition |
|---|---|---|
| `LGA_Code` | integer | ABS Local Government Area code |
| `LGA_Name` | text | ABS LGA name |
| `Total_Median` | currency/week | Median weekly rent for all reported dwelling types, October–December 2025 |
| `Unit_Total_Median` | currency/week | Median weekly unit rent |
| `House_Total_Median` | currency/week | Median weekly house rent |
| `Total_Count` | number | Quarterly bonds lodged; 1–5 is suppressed and totals are rounded |
| `Sample_Quality` | category | Published-bond-count quality band |
| `Median_Weekly_Household_Income_2021` | currency/week | ABS 2021 Census median total household income |
| `Rent_to_Income_Proxy` | ratio | `Total_Median / Median_Weekly_Household_Income_2021` |
| `Rent_to_Income_Proxy_Pct` | percent | Screening proxy displayed as a percentage |
| `Population_2024` | persons | ABS estimated resident population at 30 June 2024 |
| `Population_2025` | persons | ABS estimated resident population at 30 June 2025 |
| `Population_Change` | persons | Annual ERP change |
| `Population_Growth_Pct` | percent | 2024–25 ERP percentage change |
| `Approvals_2024_25` | dwellings | ABS dwelling approvals in the complete 2024–25 financial year |
| `Approvals_2025_26_FYTD` | dwellings | ABS 2025–26 approvals through April 2026; never compared as a full year |
| `Approvals_per_1000` | rate | `Approvals_2024_25 / Population_2025 × 1,000` |
| `Affordability_Pressure_Score` | 0–100 | Eligible-LGA percentile of rent-to-income proxy |
| `Demand_Pressure_Score` | 0–100 | Eligible-LGA percentile of annual population growth |
| `Supply_Gap_Score` | 0–100 | Inverse eligible-LGA percentile of approvals per 1,000 |
| `Weighted_Component_Score` | 0–100 | 50/25/25 weighted component result before final ranking |
| `Housing_Pressure_Index` | 0–100 | Percentile rank of the weighted component score |
| `Housing_Pressure_Category` | category | Relative five-band index category |
| `Eligible_for_Score` | boolean | `True` when at least 10 quarterly bonds are published |
| `Complete_Score` | boolean | `True` when eligible and all three component inputs exist |

## State approval outputs

`dashboard_monthly_approvals.csv` contains the ABS original monthly series and a
three-month rolling average. `dashboard_annual_approvals.csv` includes
`Months_Covered`, `Period_Status` and `Year_Label` so partial years cannot appear
as complete years. `dashboard_ytd_approvals.csv` provides comparable
January-to-latest-month totals for each year.

## Interpretation rule

The Housing Pressure Index ranks LGAs against one another for the input periods.
It does not measure the probability of shortage, identify causality, estimate
unmet dwelling need, or determine whether an individual household is in stress.
