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

- Pipeline rebuild: passed.
- Streamlit automated smoke test: passed with zero application exceptions.
- Dashboard tabs detected: 6.
- Current output: 71 local areas, 53 eligible and completely scored.
- Latest state approvals period: April 2026.

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
