# Project status

This file is the chronological audit trail for material project changes,
validation results, source updates and known limitations.

## 2026-06-28 — Analytical rebuild

### Completed

- Audited the original app, notebook, raw workbooks and processed outputs.
- Replaced the rent-only suburb threshold score with an LGA-level relative index.
- Integrated the existing SA Housing Trust LGA rental worksheet with both ABS
  LGA building-approval cubes.
- Added official ABS 2024–25 LGA population estimates.
- Added official ABS 2021 Census LGA median weekly household income.
- Added population growth and approvals-per-1,000 measures.
- Added a minimum published rental sample of 10 bonds for scoring.
- Added sample-quality labels and visible methodology warnings.
- Removed Metro, Country, Grand Total and state aggregates from local ranking.
- Corrected 2026 approvals labelling to “YTD (4 months).”
- Added comparable January–April approval totals for 2021–2026.
- Renamed the dashboard to avoid claiming infrastructure readiness without
  capacity evidence.
- Rebuilt the Streamlit interface with LGA filters, transparent component
  explanations, source links, downloadable datasets and data-quality content.
- Replaced the 129-package environment freeze with minimal runtime and
  development dependency files.
- Added a reproducible Python pipeline and separate scoring module.
- Added automated tests, CI configuration, a data dictionary and source register.

### Model specification

- Affordability pressure: 50%.
- Population-demand pressure: 25%.
- Supply gap: 25%.
- Component and final scores use eligible-LGA percentile ranks.
- Categories: Very High ≥80, High ≥60, Moderate ≥40, Low ≥20, Very Low <20.
- An LGA is eligible only when at least 10 quarterly rental bonds are published.

### Verification

- Baseline pipeline rebuild and Streamlit automated smoke test passed before
  the current testing, cleanup and dashboard-polish phase.
- Current output: 71 local areas, 53 eligible and completely scored.
- Latest state approvals period: April 2026.
- Current integration verification is pending. Before release, rerun
  `python -m src.pipeline`, `pytest -q` and browser checks at desktop and narrow
  widths, then record the exact results here.

### 2026-06-28 — Finalisation work in progress

- Expanded source-contract validation for missing files, worksheets, ZIP
  members, columns, duplicate join keys and incomplete key coverage.
- Added safe denominator handling and atomic processed-CSV writes.
- Expanded automated edge-case and pipeline-contract coverage.
- Configured CI to rebuild and test on Python 3.10 and Python 3.12.
- Polished dashboard responsiveness, empty-result guidance, chart labels,
  tooltips, focus visibility and download context without changing the model.
- Clarified that the 71 output records are ABS-coded local areas: 68
  incorporated LGAs plus three Unincorporated SA areas.
- Created the Business Analysis foundation document under `docs/`.

Final integrated pipeline, test and browser results are intentionally pending
until the implementation review is complete.

### Known evidence gaps

- The rent-to-income measure uses 2021 Census income and is a proxy, not a
  current rental-stress rate.
- Vacancy rates and advertised-rent availability are not in the government
  rental-bond source.
- Approvals do not measure dwelling commencement or completion.
- Infrastructure readiness remains deliberately unscored. It requires service
  capacity and land-release data covering water, wastewater, transport,
  schools and health.

### Next evidence release actions

- Refresh the private-rent workbook when the next official quarter is published.
- Refresh ABS approvals monthly and LGA cubes after revisions.
- Replace or index the 2021 income denominator when an authoritative,
  methodologically compatible update is available.
- Add a separate infrastructure-readiness module only after capacity measures,
  geographic coverage and scoring assumptions are documented and tested.
