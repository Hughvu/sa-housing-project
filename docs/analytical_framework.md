# Analytical framework

## Purpose and model boundary

This dashboard is a screening and decision-support tool for comparing South
Australian housing signals. It separates three evidence layers so descriptive
context cannot silently change the ranked result.

The implemented Housing Pressure Index is unchanged:

| Scored component | Weight | Direction of pressure |
|---|---:|---|
| Rent-to-income screening proxy | 50% | Higher is greater pressure |
| Annual population growth | 25% | Higher is greater pressure |
| Dwelling approvals per 1,000 residents | 25% | Lower is greater pressure |

Only these three inputs affect the score. Approval composition, migration
components, population density, rent by dwelling type and state approval trends
are contextual measures. They do not alter the 50/25/25 model.

## Evidence labels

- **Observed** — a published source value, including an official estimate.
- **Derived** — a transparent calculation from observed fields.
- **Proxy** — a derived measure that approximates a concept it does not measure
  directly.
- **Scenario** — a conditional view based on stated future assumptions, not an
  observed outcome or forecast certainty.

The ABS estimated resident population fields are labelled observed for this
framework because they are official published estimates; they are not a census
count. Percentile scores, rates, ratios and residuals are derived. Every
rent-to-income field is a proxy because it combines 2025 rent medians with 2021
household-income medians.

## Three-layer evidence model

### Layer 1 — scored LGA index

The scored layer contains:

1. December-quarter 2025 total median rent divided by 2021 Census median weekly
   household income.
2. ABS estimated resident population growth from 2024 to 2025.
3. ABS 2024–25 dwelling approvals per 1,000 June 2025 residents.

An area must have at least 10 published total rental bonds and complete values
for all three inputs. Eligible inputs are percentile-ranked using average ranks
for ties. The weighted component score is:

```text
0.50 × affordability percentile
+ 0.25 × population-growth percentile
+ 0.25 × inverse approvals-per-1,000 percentile
```

The weighted result is percentile-ranked again to create the 0–100 Housing
Pressure Index. It is relative to the eligible South Australian comparison set,
not an absolute shortage, need or household-stress measure.

### Layer 2 — non-scored LGA context

Implemented local context explains what may sit behind the index:

- unit and house rent medians, published bond counts and type-specific
  rent-to-income proxies;
- house–unit weekly rent gap and unit-to-house comparison;
- population change split into natural increase, net internal migration and net
  overseas migration;
- land area and population density;
- house, other-residential and residual approval units;
- type-specific approval rates, other-residential share and approvals per 100
  new residents.

These fields are descriptive. In particular, approvals per 100 new residents is
only calculated for positive population change and is not a dwelling-sufficiency
benchmark. Residual approval units reconcile the ABS published total where the
displayed source components do not sum exactly to it; they are not a dwelling
type.

### Layer 3 — state and regional context

The implemented state layer contains the ABS original monthly approvals series,
house/non-house composition, rolling totals, year-on-year changes, calendar-year
totals and like-for-like year-to-date comparisons.

Candidate state or regional evidence includes dwelling commencements and
completions, land supply, planning-system performance, social-housing demand,
homelessness-service demand and population projections. These remain outside
the score unless they later meet the source-admission and geography rules below.

## Implemented formulas

| Measure | Formula | Label |
|---|---|---|
| Total rent-to-income proxy | `Total_Median / Median_Weekly_Household_Income_2021` | Proxy |
| Unit or house rent-to-income proxy | Type median / 2021 household income, only when that type has at least 10 published bonds | Proxy |
| House–unit rent gap | `House_Total_Median - Unit_Total_Median` | Derived |
| House premium over unit rent | `House_Unit_Rent_Gap / Unit_Total_Median × 100` | Derived |
| Population change | `Population_2025 - Population_2024`; source components must reconcile | Observed estimate |
| Net migration | Net internal migration + net overseas migration | Derived |
| Population density | June 2025 population per square kilometre, as published by ABS | Observed estimate |
| Approvals per 1,000 | `Approvals_2024_25 / Population_2025 × 1,000` | Derived |
| Type approvals per 1,000 | House or other-residential approvals / population × 1,000 | Derived |
| Other-residential share | Other-residential approvals / total approvals × 100 | Derived |
| Approvals per 100 new residents | Total approvals / positive population change × 100 | Derived context |
| Three-month approval average | Mean of current and preceding two monthly totals | Derived |
| Rolling 12-month approvals | Sum of current and preceding 11 monthly totals | Derived |
| Monthly year-on-year change | Current month / same month one year earlier × 100 − 100 | Derived |
| Rolling-12-month year-on-year change | Current rolling annual total / prior-year rolling annual total × 100 − 100 | Derived |
| YTD year-on-year change | Current YTD / prior-year YTD × 100 − 100, only for matching month counts | Derived |

All ratios require a positive, finite denominator. Missing or ineligible values
remain missing rather than being imputed.

## Geography and period compatibility

| Evidence | Geography | Period | Permitted use | Compatibility rule |
|---|---|---|---|---|
| Private Rent Report | ABS-coded local-area names joined to LGA | Oct–Dec 2025 | Scored and local context | Flow of new bonds; sample thresholds apply |
| Census household income | 2021 LGA | 2021 Census | Proxy denominator | Must retain 2021 label beside 2025 rent |
| Regional Population | 2025 LGA classification | 2024–25 | Scored and local context | Official estimate; components must reconcile |
| LGA Building Approvals | 2024/2025 LGA releases | 2024–25 and 2025–26 FYTD | Scored full year and contextual FYTD | FYTD never compared with a full year |
| State Building Approvals | South Australia | Jan 2021–Apr 2026 | State context | Original series; monthly revisions expected |
| Building Activity candidate | South Australia | Latest available quarter | State context only | Survey estimates are not allocated to LGAs |
| PlanSA land supply candidate | Greater Adelaide | Dashboard/report release | Separate regional context | Cannot rank statewide local areas |
| PlanSA population projections candidate | Region, LGA or SA2 | 2021–2051/2041 scenarios | Scenario context | Never presented as observed demand |
| Social housing and homelessness candidates | Primarily South Australia | Annual reporting periods | State context only | Service demand is not local prevalence |

The processed output contains 71 ABS-coded local areas: 68 incorporated LGAs
and three Unincorporated SA statistical areas. The interface shorthand “LGA”
does not turn those three statistical areas into councils.

## Interpretation workflow

1. **Check eligibility and quality.** Confirm the area is scored, inspect the
   total and type-specific bond counts, and note any suppressed data.
2. **Read the components before the composite.** Identify whether affordability,
   growth or the inverse approval rate drives the relative position.
3. **Use local context to form questions.** Review migration, natural increase,
   density, dwelling-type rent and approval composition without treating them
   as additional score evidence.
4. **Check period and geography.** Do not compare a partial year with a full
   year or apply Greater Adelaide/state evidence to an LGA without qualification.
5. **Distinguish pipeline stages.** A planning application, building approval,
   commencement, completion and occupied dwelling are different events.
6. **Conclude proportionately.** A high score supports deeper investigation; it
   does not establish causation, unmet need, infrastructure capacity or a policy
   prescription.

## Source-admission criteria

A new source must satisfy all mandatory criteria before production use:

- authoritative government publisher and stable official URL;
- reproducible, lawful download in a documented machine-readable format;
- defined geography, reference period, concepts and revision policy;
- coverage sufficient for its intended layer, with missingness and suppression
  understood;
- join keys or a documented concordance that can be validated;
- update cadence and immutable local filename recorded;
- formulas, direction, units and denominator rules documented;
- tests for schema drift, key coverage, impossible values and reconciliation;
- no material duplication of an existing scored concept;
- explicit decision on whether the measure is observed, derived, proxy or
  scenario.

Any proposal to change score inputs, weights, thresholds, eligibility, ranking
direction or tie handling is a model change. It requires sensitivity analysis,
tests, documentation and release approval.

## Authoritative evidence roadmap

### Near term

1. Maintain current quarterly rent, annual population and monthly approval
   releases.
2. Preserve the newly implemented dwelling-type, migration, density and trend
   measures as non-scored context.
3. Add a 2021 Census Rent Affordability Indicator baseline only as historical
   context; it is closer to a household stress concept than the current
   median-to-median proxy but is not current.

### Separate contextual modules

- **Delivery:** ABS Building Activity provides commencements, completions, work
  under construction and pipeline estimates, generally at state/territory level.
- **Land and planning:** PlanSA land supply can support a Greater Adelaide
  module; planning performance can describe applications and assessment times.
- **Forward scenarios:** PlanSA population projections can support scenario
  analysis when assumptions and 2021 baselines remain visible.
- **Social need:** Productivity Commission social-housing data and AIHW
  specialist-homelessness data can support state context, not an LGA shortage
  score.

### Blocked pending better evidence

Infrastructure readiness remains unscored. The Infrastructure SA strategy
identifies planning needs but is not a quantitative LGA capacity dataset.
Scoring would require compatible measures of water, wastewater, transport,
schools, health and land-release sequencing.

## Official references

- [SA Housing Trust Private Rent Report](https://data.sa.gov.au/data/dataset/private-rent-report)
- [ABS Building Approvals](https://www.abs.gov.au/statistics/industry/building-and-construction/building-approvals-australia/latest-release)
- [ABS Building Approvals methodology](https://www.abs.gov.au/methodologies/building-approvals-australia-methodology)
- [ABS Regional Population](https://www.abs.gov.au/statistics/people/population/regional-population/latest-release)
- [ABS 2021 Census DataPacks](https://www.abs.gov.au/census/find-census-data/datapacks)
- [ABS Building Activity](https://www.abs.gov.au/statistics/industry/building-and-construction/building-activity-australia/latest-release)
- [AIHW housing affordability](https://www.aihw.gov.au/reports/australias-welfare/housing-affordability)
- [PlanSA Land Supply Dashboard](https://plan.sa.gov.au/state_snapshot/land_supply/land-supply-dashboard)
- [PlanSA planning-system performance indicators](https://plan.sa.gov.au/our_planning_system/schemes/performance_indicators)
- [PlanSA population projections summary](https://plan.sa.gov.au/__data/assets/pdf_file/0005/1236767/Population-Projections-for-South-Australia-and-Regions-2021-to-2051-Summary.pdf)
- [Productivity Commission Report on Government Services 2026 — Housing](https://www.pc.gov.au/ongoing/report-on-government-services/housing-homelessness/housing/)
- [AIHW Specialist Homelessness Services 2024–25](https://www.aihw.gov.au/reports/homelessness-services/specialist-homelessness-services-annual-report/contents/summary)
- [Infrastructure SA 20-Year State Infrastructure Strategy 2025](https://www.infrastructure.sa.gov.au/20-year-strategy/2025-Strategy)
