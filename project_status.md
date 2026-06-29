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

- Final pipeline rebuild: passed.
- Final automated test suite: 57 passed in 6.85 seconds.
- Browser verification covered all six tabs at the default desktop viewport
  and a 390 × 844 narrow viewport.
- Empty-filter recovery displayed correctly across the filtered LGA analysis
  tabs.
- Narrow-layout width was 390 pixels with no horizontal page overflow, and the
  browser console reported no errors.
- Current output: 71 local areas, 53 eligible and completely scored.
- Latest state approvals period: April 2026.
- The BA foundation DOCX passed heading, section and accessibility structure
  audits with zero accessibility findings. Page-image visual QA could not be
  completed because LibreOffice is not installed in this environment.

### 2026-06-28 — Finalisation complete

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

## 2026-06-29 — Expanded evidence documentation

### Documented implementation

- Documented the implemented type-specific rent measures, population-change
  components, migration, density, dwelling-type approval composition,
  population-normalised rates and state approval trend calculations.
- Defined a three-layer evidence model: scored LGA index, non-scored LGA
  context, and state/regional context.
- Classified fields and proposed sources as observed, derived, proxy or
  scenario.
- Added a geography-and-period compatibility matrix, analytical interpretation
  workflow and mandatory source-admission criteria.
- Added an authoritative research roadmap covering delivery, land supply,
  planning performance, population scenarios, social housing, homelessness and
  infrastructure evidence.

### Model status

The Housing Pressure Index remains unchanged at 50% affordability pressure, 25%
population-demand pressure and 25% supply gap. None of the expanded contextual
metrics changes ranking.

### Implementation and verification

- Expanded the production pipeline and regenerated the LGA, monthly and YTD
  dashboard datasets without changing any Housing Pressure Index value,
  category or eligibility result.
- Added strict reconciliation and boundary tests for population components,
  approval composition, rental sample thresholds, rolling windows and
  like-for-like YTD comparisons.
- Added richer analyst views for index drivers, dwelling-type rents, population
  change, approval composition and state pipeline momentum.
- Raised the minimum Streamlit version to 1.51 for the supported chart-width
  API and added a CI drift check for regenerated datasets.
- Removed tracked operating-system metadata, a redundant notebook checkpoint,
  a zero-byte notebook placeholder and stale local pytest cache directories as
  release-hygiene cleanup.
- Final pipeline rebuild: passed.
- Final automated test suite: 70 passed in 5.97 seconds.
- Streamlit runtime harness: six tabs, 12 Plotly charts, eight data tables and
  no application exceptions.
- Browser verification: all six tabs passed at 1280 × 720 and 390 × 844; the
  narrow viewport had no horizontal page overflow and the browser console
  reported no warnings or errors.
- Empty-filter recovery was confirmed with the Streamlit runtime harness across
  all three filtered LGA analysis tabs.

### Production deployment

- Public dashboard:
  https://sa-housing-project-9u83nxa3hjxyuwcjgpwwh2.streamlit.app/
- GitHub `main` was fast-forwarded to verified release commit `42d98ad8`, and
  the resulting remote CI run passed.
- Production verification confirmed all six expanded dashboard tabs at desktop
  and 390 × 844 mobile width.
- The production mobile viewport had no horizontal page overflow, and the
  browser console reported no warnings or errors.
