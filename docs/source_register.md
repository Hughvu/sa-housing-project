# Source register

## Implemented production sources

| Dataset | Authority | Reference period | Local file | Use | Key caveat |
|---|---|---|---|---|---|
| Private Rent Report | SA Housing Trust / Consumer and Business Services | 1 Oct–31 Dec 2025 | `data/raw/rent/private-rental-report-2025-12.xlsx` | LGA median rents and bond counts | Quarterly bond lodgements; counts 1–5 suppressed; totals rounded |
| Building Approvals, Table 04 | Australian Bureau of Statistics | Jan 2021–Apr 2026 | `data/raw/approvals/8731004.xlsx` | State original monthly approval series | Permit, not commencement or completion; revisions occur |
| LGA Building Approvals | Australian Bureau of Statistics | 2024–25 | `data/raw/approvals/87310do016_202604.xlsx` | Complete-year local supply pipeline | Small-area volatility |
| LGA Building Approvals | Australian Bureau of Statistics | 2025–26 through Apr 2026 | `data/raw/approvals/87310do017_202604.xlsx` | FYTD context only | Partial year; not directly comparable with a full year |
| Regional Population | Australian Bureau of Statistics | 2024–25 | `data/raw/population/32180DS0002_2024-25.xlsx` | Population growth and rate denominator | Estimated resident population; revisions possible |
| General Community Profile, LGA | Australian Bureau of Statistics | 2021 Census | `data/raw/income/2021_GCP_LGA_for_SA_short-header.zip` | Median weekly household income | Older than rent period; proxy must be labelled |

## Source URLs

- Private rent: https://data.sa.gov.au/data/dataset/private-rent-report
- Building approvals: https://www.abs.gov.au/statistics/industry/building-and-construction/building-approvals-australia/latest-release
- Regional population: https://www.abs.gov.au/statistics/people/population/regional-population/latest-release
- Census DataPacks: https://www.abs.gov.au/census/find-census-data/datapacks

The production index uses only these implemented local sources. The expanded
population and approval context fields come from the same Regional Population
and Building Approvals files; they are not additional score inputs.

## Candidate and contextual sources

These authoritative sources have been researched but are not production inputs.

| Dataset | Authority | Latest verified period | Geography | Proposed layer | Key caveat |
|---|---|---|---|---|---|
| Building Activity | ABS | Dec quarter 2025, released 8 Apr 2026 | State/territory | State delivery context | Survey estimates of commencements, completions and work; subject to revision and generally not reliable at LGA level |
| Census Rent Affordability Indicator and tenure | ABS | 2021 Census | LGA and other Census geographies | Historical local context | Historical baseline; undetermined income/cost cases and changed comparability rules must remain visible |
| Population Projections for SA and Regions | PlanSA | 2021–2051 state; local horizon 2021–2041 | State, region, LGA and SA2 products | Scenario context | Conditional migration and natural-change assumptions; not an observed forecast outcome |
| Land Supply Dashboard | PlanSA | Live dashboard; Greater Adelaide focus | Greater Adelaide | Regional land context | Unequal statewide coverage prevents a 71-area score |
| Planning Performance Indicators | State Planning Commission / PlanSA | 2024–25 annual report | South Australia planning system | State planning context | Applications and assessment performance are not dwelling completions |
| Report on Government Services — Housing | Productivity Commission | 2026 report; primarily 30 Jun 2025/2024–25 data | State/territory | State social-housing context | Eligibility, allocation and service models differ across jurisdictions |
| Specialist Homelessness Services | AIHW | 2024–25 | State/territory and selected cohorts | State service-demand context | Measures service clients and responses, not prevalence; SA collection changes affect trend interpretation |
| 20-Year State Infrastructure Strategy | Infrastructure SA | 2025 strategy | State and strategic regions | Strategic context | Planning evidence, not quantitative LGA service-capacity data |

### Candidate source URLs

- Building Activity:
  https://www.abs.gov.au/statistics/industry/building-and-construction/building-activity-australia/latest-release
- ABS 2021 Census:
  https://www.abs.gov.au/census/find-census-data
- AIHW housing-affordability concepts:
  https://www.aihw.gov.au/reports/australias-welfare/housing-affordability
- PlanSA population projections:
  https://plan.sa.gov.au/__data/assets/pdf_file/0005/1236767/Population-Projections-for-South-Australia-and-Regions-2021-to-2051-Summary.pdf
- PlanSA Land Supply Dashboard:
  https://plan.sa.gov.au/state_snapshot/land_supply/land-supply-dashboard
- PlanSA performance indicators:
  https://plan.sa.gov.au/our_planning_system/schemes/performance_indicators
- Productivity Commission housing data:
  https://www.pc.gov.au/ongoing/report-on-government-services/housing-homelessness/housing/
- AIHW Specialist Homelessness Services:
  https://www.aihw.gov.au/reports/homelessness-services/specialist-homelessness-services-annual-report/contents/summary
- Infrastructure SA strategy:
  https://www.infrastructure.sa.gov.au/20-year-strategy/2025-Strategy

Candidate sources must pass the admission criteria in
`docs/analytical_framework.md` before implementation.

## Refresh protocol

1. Save new raw files without overwriting prior releases.
2. Update the source-path constants, period labels and output field names in
   `src/pipeline.py` only where the new release requires them.
3. Check workbook sheet names, header rows, required columns, positional
   layouts and ZIP-member names against the new source before accepting it.
4. Rebuild with `python -m src.pipeline`; the pipeline will reject duplicate
   join keys, missing required LGA coverage and invalid output contracts.
5. Run `pytest -q`.
6. Reconcile state and local-area totals, inspect name aliases and investigate
   every unmatched or newly added area.
7. Confirm partial periods remain visibly labelled and that the common YTD
   comparison window updates correctly.
8. Update this register and `project_status.md` with source filenames, release
   dates, schema changes, validation results and any model implications.

Generated CSVs under `data/processed/` are rebuildable artifacts and must not be
hand-edited.
