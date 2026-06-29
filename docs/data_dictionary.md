# Data dictionary

## Evidence labels

- **Observed** — published source value, including an official estimate.
- **Derived** — transparent calculation from source fields.
- **Proxy** — calculation approximating a concept it does not directly measure.
- **Scenario** — conditional future value based on assumptions.

## `dashboard_lga_pressure.csv`

| Field | Type | Evidence | Definition |
|---|---|---|---|
| `LGA_Code` | integer | Observed | ABS Local Government Area code |
| `LGA_Name` | text | Observed | ABS LGA name |
| `Total_Median` | currency/week | Observed | Median weekly rent for all reported dwelling types, October–December 2025 |
| `Unit_Total_Median` | currency/week | Observed | Median weekly unit rent |
| `House_Total_Median` | currency/week | Observed | Median weekly house rent |
| `Total_Count` | number | Observed | Quarterly total bonds lodged; 1–5 is suppressed and totals are rounded |
| `Unit_Total_Count` | number | Observed | Quarterly published unit bond count |
| `House_Total_Count` | number | Observed | Quarterly published house bond count |
| `Sample_Quality` | category | Derived | Total published-bond-count quality band |
| `Median_Weekly_Household_Income_2021` | currency/week | Observed | ABS 2021 Census median total household income |
| `Rent_to_Income_Proxy` | ratio | Proxy | `Total_Median / Median_Weekly_Household_Income_2021` |
| `Rent_to_Income_Proxy_Pct` | percent | Proxy | Total screening proxy displayed as a percentage |
| `Unit_Rent_to_Income_Proxy` | ratio | Proxy | Unit median / 2021 income when at least 10 unit bonds are published |
| `Unit_Rent_to_Income_Proxy_Pct` | percent | Proxy | Unit screening proxy displayed as a percentage |
| `House_Rent_to_Income_Proxy` | ratio | Proxy | House median / 2021 income when at least 10 house bonds are published |
| `House_Rent_to_Income_Proxy_Pct` | percent | Proxy | House screening proxy displayed as a percentage |
| `House_Unit_Rent_Gap` | currency/week | Derived | House median minus unit median when both type samples meet the threshold |
| `House_Unit_Rent_Premium_Pct` | percent | Derived | House–unit gap divided by unit median × 100 |
| `Population_2024` | persons | Observed | ABS ERP estimate at 30 June 2024 |
| `Population_2025` | persons | Observed | ABS ERP estimate at 30 June 2025 |
| `Population_Change` | persons | Observed | ABS estimated 2024–25 ERP change |
| `Population_Growth_Pct` | percent | Observed | ABS estimated 2024–25 ERP percentage change |
| `Natural_Increase_2024_25` | persons | Observed | Estimated births minus deaths contribution |
| `Net_Internal_Migration_2024_25` | persons | Observed | Estimated net movement within Australia |
| `Net_Overseas_Migration_2024_25` | persons | Observed | Estimated net overseas migration contribution |
| `Net_Migration_2024_25` | persons | Derived | Internal plus overseas net migration |
| `Area_km2` | square kilometres | Observed | ABS LGA area |
| `Population_Density_2025` | persons/km² | Observed | Published estimated June 2025 population density |
| `House_Approvals_2024_25` | dwellings | Observed | Complete-year new-house approvals |
| `Other_Residential_Approvals_2024_25` | dwellings | Observed | Complete-year other-residential approvals |
| `Residual_Approval_Units_2024_25` | dwellings | Derived | Total less house and other-residential components; reconciliation field, not a dwelling type |
| `Approvals_2024_25` | dwellings | Observed | Total approvals in complete 2024–25 financial year |
| `Approvals_2025_26_FYTD` | dwellings | Observed | FYTD approvals through April 2026 |
| `House_Approvals_per_1000` | rate | Derived | House approvals / population × 1,000 |
| `Other_Residential_Approvals_per_1000` | rate | Derived | Other-residential approvals / population × 1,000 |
| `Approvals_per_1000` | rate | Derived | Total approvals / population × 1,000 |
| `Other_Residential_Approval_Share_Pct` | percent | Derived | Other-residential / total approvals × 100 |
| `Approvals_per_100_New_Residents` | rate | Derived | Total approvals / positive population change × 100; contextual, not a sufficiency benchmark |
| `Affordability_Pressure_Score` | 0–100 | Derived | Eligible-area percentile of total rent-to-income proxy |
| `Demand_Pressure_Score` | 0–100 | Derived | Eligible-area percentile of population growth |
| `Supply_Gap_Score` | 0–100 | Derived | Inverse eligible-area percentile of approvals per 1,000 |
| `Weighted_Component_Score` | 0–100 | Derived | Unchanged 50/25/25 weighted component result |
| `Housing_Pressure_Index` | 0–100 | Derived | Percentile rank of weighted component score |
| `Housing_Pressure_Category` | category | Derived | Relative five-band index category |
| `Eligible_for_Score` | boolean | Derived | `True` when at least 10 total quarterly bonds are published |
| `Complete_Score` | boolean | Derived | `True` when eligible and all three score inputs exist |

## State approval outputs

### `dashboard_monthly_approvals.csv`

| Field | Type | Evidence | Definition |
|---|---|---|---|
| `Month` | date | Observed | Calendar month in ISO date form |
| `House_Approvals` | dwellings | Observed | Original-series house approvals |
| `Non_House_Approvals` | dwellings | Observed | Original-series non-house dwelling approvals |
| `Dwelling_Approvals` | dwellings | Observed | Total original-series South Australian dwelling approvals |
| `Year` | integer | Derived | Calendar year |
| `Month_Number` | integer | Derived | Month number, 1–12 |
| `Month_Name` | text | Derived | Display label such as `Apr 2026` |
| `Rolling_3_Month_Avg` | dwellings | Derived | Three-month rolling mean |
| `Non_House_Approval_Share_Pct` | percent | Derived | Non-house approvals / total approvals × 100 |
| `Rolling_12_Month_Total` | dwellings | Derived | Sum of current and preceding 11 months |
| `Monthly_YoY_Change_Pct` | percent | Derived | Change from same month one year earlier |
| `Rolling_12_Month_YoY_Change_Pct` | percent | Derived | Change from rolling total one year earlier |
| `Series_Type` | text | Observed | Source-series label `Original`; not seasonally adjusted |

### `dashboard_annual_approvals.csv`

| Field | Type | Evidence | Definition |
|---|---|---|---|
| `Year` | integer | Derived | Calendar year |
| `Dwelling_Approvals` | dwellings | Derived | Sum of available monthly approvals |
| `Months_Covered` | integer | Derived | Number of months included |
| `Period_Status` | text | Derived | `Full calendar year` or `Year to date` |
| `Year_Label` | text | Derived | Display label that makes a partial year explicit |

### `dashboard_ytd_approvals.csv`

| Field | Type | Evidence | Definition |
|---|---|---|---|
| `Year` | integer | Derived | Calendar year |
| `YTD_Dwelling_Approvals` | dwellings | Derived | January-to-comparison-month approval total |
| `Months_Compared` | integer | Derived | Common number of months included in every year |
| `Prior_Year_YTD_Dwelling_Approvals` | dwellings | Derived | Previous calendar year’s matching YTD total |
| `Prior_Year_Months_Compared` | integer | Derived | Previous year’s included month count |
| `YTD_YoY_Change_Pct` | percent | Derived | YTD change when current and prior month counts match |
| `Comparison_Label` | text | Derived | Human-readable comparison window, currently January–April |

### `data_quality_summary.csv`

| Field | Type | Definition |
|---|---|---|
| `Check` | text | Validation or coverage measure name |
| `Value` | mixed | Recorded count or latest source date |

The current quality summary records the number of local areas in the output,
the number with complete scores, the number with suppressed/low rental samples,
and the latest state approval month.

## Geography coverage

The 71 records in `dashboard_lga_pressure.csv` are ABS-coded local areas: 68
incorporated LGAs and three Unincorporated SA statistical areas. `LGA_Code` and
`LGA_Name` follow the ABS source nomenclature. “71 local areas” therefore does
not mean 71 councils.

## Interpretation rule

The Housing Pressure Index ranks LGAs against one another for the input periods.
It does not measure the probability of shortage, identify causality, estimate
unmet dwelling need, or determine whether an individual household is in stress.
