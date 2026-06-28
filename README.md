# South Australian Housing Pressure & Supply Dashboard

A reproducible Business Analyst portfolio project that compares rental-cost
pressure, population growth and approved housing supply across South Australian
Local Government Areas (LGAs).

The application is intentionally described as a **relative decision-support
tool**. It is not a forecast, a measure of individual household rental stress,
or an infrastructure-capacity model.

## What changed from the original prototype

- Replaced suburb rent thresholds with a transparent LGA-level relative index.
- Joined SA Housing Trust LGA rent data to ABS LGA approvals.
- Added ABS 2024–25 population growth and population-normalised approvals.
- Added a rent-to-income screening proxy using ABS 2021 Census household income.
- Excluded rental observations with fewer than 10 published quarterly bonds
  from scoring.
- Correctly labels 2026 state approvals as year-to-date.
- Added like-for-like January–April comparisons.
- Added reproducible processing modules, automated tests, source documentation
  and data downloads.
- Removed the unsupported “infrastructure readiness” claim from the product name.

## Quick start

Use Python 3.10 or newer.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python -m src.pipeline
pytest -q
streamlit run app.py
```

The dashboard expects the raw source files described in
[`docs/source_register.md`](docs/source_register.md). Processed CSV files are
generated under `data/processed/`.

## Index methodology

Only areas with complete inputs and at least 10 published rental bonds receive
a score.

| Component | Weight | Higher pressure means |
|---|---:|---|
| Affordability pressure | 50% | Higher December-quarter 2025 median rent relative to 2021 median weekly household income |
| Demand pressure | 25% | Higher 2024–25 population growth |
| Supply gap | 25% | Fewer 2024–25 dwelling approvals per 1,000 June 2025 residents |

Each component is converted to a percentile rank. The weighted result is ranked
again to produce the 0–100 **Housing Pressure Index**:

- Very High: 80–100
- High: 60–79.9
- Moderate: 40–59.9
- Low: 20–39.9
- Very Low: below 20

See [`docs/data_dictionary.md`](docs/data_dictionary.md) for field definitions.

## Important limitations

- The rent report covers bonds lodged during one quarter, not every tenancy,
  vacancy rates or asking rents.
- Counts of 1–5 are suppressed and published totals are rounded.
- The income denominator is from the 2021 Census. The resulting ratio is a
  screening proxy, not a current rental-stress rate.
- Building approvals are permits. They do not prove construction commenced or
  that a dwelling was completed.
- ABS small-area approvals are volatile and subject to revision.
- Infrastructure capacity is deliberately not scored. A credible module needs
  capacity data for water, wastewater, schools, health and transport, as well
  as land-release sequencing.

## Project structure

```text
app.py                         Streamlit presentation layer
src/pipeline.py                Raw-to-processed data pipeline
src/scoring_model.py           Tested scoring functions
tests/                         Automated integrity and model tests
data/raw/                      Immutable source files
data/processed/                Rebuildable dashboard datasets
docs/data_dictionary.md        Output field definitions
docs/source_register.md        Sources, periods and caveats
project_status.md              Chronological implementation log
```

## Quality checks

The pipeline validates source contracts before transforming data. It fails
clearly when:

- an expected raw file, workbook sheet, ZIP member or required column is
  missing;
- a positional workbook extract is narrower than the documented source layout;
- LGA join keys are duplicated or a required approvals, population or income
  record is absent;
- a state aggregate enters the local-area output;
- fewer than 50 areas have eligible, complete scores;
- an output is empty, monthly approvals are not chronological, or negative
  approval values appear.

Rates are calculated only when denominators are positive and finite. Generated
CSVs are written atomically so an interrupted rebuild does not leave a partial
output.

Run all checks with:

```powershell
python -m src.pipeline
pytest -q
```

GitHub Actions repeats the rebuild and tests on Linux with Python 3.10 and
Python 3.12. A local Streamlit/browser review is still required for material
interface changes.

## Geography note

The current processed file contains 71 ABS-coded South Australian local areas:
68 incorporated LGAs plus three Unincorporated SA statistical areas. The
dashboard uses “LGA” as a compact interface label, but the 71-area count should
not be interpreted as 71 councils. Of these areas, 53 currently meet the
published-rental-sample rule and have all model inputs required for a score.

## Authoritative sources

- [SA Housing Trust Private Rent Report](https://data.sa.gov.au/data/dataset/private-rent-report)
- [ABS Building Approvals](https://www.abs.gov.au/statistics/industry/building-and-construction/building-approvals-australia/latest-release)
- [ABS Regional Population](https://www.abs.gov.au/statistics/people/population/regional-population/latest-release)
- [ABS Census DataPacks](https://www.abs.gov.au/census/find-census-data/datapacks)
- [AIHW Housing Affordability](https://www.aihw.gov.au/reports/australias-welfare/housing-affordability)
- [PlanSA Land Supply](https://plan.sa.gov.au/state_snapshot/land_supply)

## Change log

See [`project_status.md`](project_status.md) for completed work, verification
results and remaining evidence gaps.
