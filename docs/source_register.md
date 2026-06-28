# Source register

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

## Refresh protocol

1. Save new raw files without overwriting prior releases.
2. Update source constants and period labels in `src/pipeline.py`.
3. Rebuild with `python -m src.pipeline`.
4. Run `pytest -q`.
5. Reconcile state totals and inspect unmatched LGAs.
6. Update `project_status.md` with source dates, validation results and model changes.
