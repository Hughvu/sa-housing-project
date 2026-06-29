# Decision Explorer rule contract

## Status and purpose

| Property | Value |
|---|---|
| Ruleset ID | `sa-housing-screening-v1` |
| Ruleset version | `1.0` |
| Reference cohort | Full set of 53 complete scored local areas |
| Decision role | Transparent, non-advisory evidence screening |
| Ranking | Existing Housing Pressure Index only |

The Decision Explorer applies fixed rules to the existing analytical dataset.
It identifies areas whose evidence matches a stated question. It does not
calculate another score, alter the Housing Pressure Index, forecast outcomes or
recommend policy, development, investment or resource allocation.

Rule matches are **non-exclusive**. A local area may match more than one positive
screen. The Evidence gaps screen is separate because an incomplete area is
never pressure-ranked.

## Common evaluation contract

- Rules are evaluated once against the full, unfiltered statewide frame.
- Positive rules require `Complete_Score == True`.
- The growth and approval benchmarks use all 53 complete scored local areas.
  Sidebar filters, search, shortlist length and comparison selections do not
  change these medians or any rule membership.
- Positive matches are displayed in descending existing
  `Housing_Pressure_Index`, then alphabetically by `LGA_Name` for equal HPI.
  This is display ordering, not a new priority score.
- Evidence gaps are displayed alphabetically and never pressure-ranked.
- A missing or ineligible score is not interpreted as low pressure.
- A rule uses `AND` between conditions unless its expression explicitly
  contains `OR`.

## Version 1.0 rules

### `broad_relative_pressure`

**Name:** Broad relative pressure

```text
Complete_Score
AND Affordability_Pressure_Score >= 60
AND Demand_Pressure_Score >= 60
AND Supply_Gap_Score >= 60
```

Permitted interpretation: all three existing index components are at or above
the 60th percentile among eligible South Australian local areas.

This is a relative multi-signal pattern. It is not a finding of severe need,
shortage or inadequate infrastructure.

### `affordability_led`

**Name:** Affordability-led pressure

```text
Complete_Score
AND Affordability_Pressure_Score >= 80
AND (Demand_Pressure_Score >= 40 OR Supply_Gap_Score >= 40)
```

Permitted interpretation: the affordability component is at or above the 80th
percentile and at least one other component is at or above the 40th percentile.

The parenthesised `OR` is material: the rule does not require both supporting
components to reach 40.

### `growth_lower_approvals`

**Name:** Higher growth with lower approvals

```text
Complete_Score
AND Population_Growth_Pct > full-reference population-growth median
AND Approvals_per_1000 < full-reference approvals-per-1,000 median
```

The two medians are calculated from the full 53-area complete scored cohort and
are disclosed in the interface and export. Strict `>` and `<` comparisons mean
an area equal to a median does not match.

Permitted interpretation: population growth is above, and the approved-dwelling
rate is below, the complete-cohort medians. This is descriptive mismatch
screening, not proof of housing shortage or insufficient delivery.

### `higher_pressure_stronger_sample`

**Name:** Higher pressure with stronger rental sample

```text
Complete_Score
AND Housing_Pressure_Index >= 60
AND Total_Count >= 20
```

Permitted interpretation: the existing relative HPI is at least 60 and the
quarterly rental evidence is in the project's `20+` published-bond band.

“Stronger rental sample” is a descriptive sample-size category. It is not a
confidence interval, accuracy guarantee or statement that the observations
represent all tenancies.

### `evidence_gaps`

**Name:** Evidence gaps

```text
NOT Complete_Score
```

Permitted interpretation: the area requires evidence review because it is not
eligible for a complete pressure score.

Evidence-gap areas are always separated from positive screens, shown
alphabetically and never assigned a pressure order. “Not scored” does not mean
low pressure.

## Comparison workflow

The explorer permits comparison of **two to five unique local areas**. Selected
order is preserved in the comparison table and downloadable brief.

1. Select the decision question and read its exact expression.
2. Review the statewide match count, full-reference benchmarks and current
   sidebar context.
3. Inspect match reasons, raw values and rental sample quality.
4. Select two to five matched areas or contextual comparators.
5. Compare the existing index components before reviewing non-scored context.
6. Read each evidence panel and any evidence-gap reason.
7. Export the versioned shortlist or comparison brief.
8. Seek current local delivery, vacancy, household-stress and infrastructure
   evidence before making a real-world decision.

Comparators do not need to match the selected rule. Their presence supports
transparent contrast and does not change rule membership.

## Interpretation boundaries

### Permitted

- “These areas match the fixed `broad_relative_pressure` rule.”
- “This area has population growth above and approvals per 1,000 below the full
  scored-cohort medians.”
- “The area matches more than one version 1.0 screen.”
- “The result supports further investigation.”
- “Rows are ordered by the existing HPI for display.”

### Prohibited

- “These are the best, optimal, recommended or priority LGAs.”
- “Build, invest, fund or intervene here first.”
- “This area is undersupplied” or “infrastructure ready.”
- “Low approvals caused high rent.”
- “A non-match means there is no pressure or need.”
- “Not scored means low pressure.”
- “The rule threshold is a South Australian Government policy threshold.”
- “A match predicts affordability improvement or housing delivery.”

The module must not use population density, migration components, dwelling mix,
approvals per 100 new residents or other contextual fields as hidden ranking
inputs.

## Source periods

- Rental bonds: December quarter 2025.
- Household income: 2021 Census.
- Population and growth: 2024–25.
- LGA dwelling approvals used by the screens: complete 2024–25 financial year.

The income/rent ratio remains an area-level screening proxy across different
periods. Building approvals are permits, not commencements, completions or
occupied dwellings.

## Auditable shortlist export

The CSV export is one row per local area and rule. All export fields are
derived metadata or copies of existing observed/derived evidence; no new score
is present.

### Rule and evaluation metadata

- `Ruleset_ID`
- `Ruleset_Version`
- `LGA_Name`
- `Rule_ID`
- `Rule_Name`
- `Question`
- `Expression`
- `Matched`
- `Evaluation_Reason`
- `Permitted_Interpretation`

### Existing score and raw evidence

- `Housing_Pressure_Index`
- `Housing_Pressure_Category`
- `Affordability_Pressure_Score`
- `Demand_Pressure_Score`
- `Supply_Gap_Score`
- `Rent_to_Income_Proxy_Pct`
- `Population_Growth_Pct`
- `Population_Change`
- `Approvals_per_1000`
- `Approvals_2024_25`
- `Other_Residential_Approval_Share_Pct`
- `Total_Count`
- `Sample_Quality`

### Explanation, reference and limitation metadata

- `Highest_Index_Component`
- `Highest_Component_Score`
- `Highest_Component_Is_Tied`
- `Evidence_Gap_Reason`
- `Pressure_Ranking_Status`
- `Reference_Population_Growth_Median_Pct`
- `Reference_Approvals_per_1000_Median`
- `Reference_Complete_LGA_Count`
- `Source_Periods`
- `Fixed_Limitations`

The shortlist download contains displayed matches for the selected rule. The
filename includes the rule ID and ruleset version. The Markdown comparison brief
records the ruleset, full-reference benchmarks, selected areas in user order,
matching rules, source periods and fixed limitations.

## Fixed limitations

- Results are relative screening signals, not forecasts, causal findings,
  housing-shortage estimates or recommendations.
- Rental data covers bonds lodged in one quarter, not all tenancies, asking
  rents or vacancy; small counts are suppressed and published totals rounded.
- The rent-to-income measure combines December-quarter 2025 rent with 2021
  Census household income and is not household rental stress.
- Building approvals may not become commenced, completed or occupied dwellings.
- Reference medians and percentile scores can change when source data,
  geography or eligibility changes.
- Infrastructure capacity is not measured.
- Sidebar filters alter what is displayed, not the statewide rules or
  benchmarks.
- Shortlist length truncates display and export; it does not change statewide
  match counts.

## Version governance

`sa-housing-screening-v1` version `1.0` is a published analytical contract.
Changing a threshold, operator, input field, complete-score gate, benchmark
cohort, ordering rule or evidence-gap treatment requires:

1. a new ruleset version;
2. updated tests at every boundary and for null/tie behaviour;
3. comparison of old and new matches;
4. updated documentation, export metadata and change log;
5. integration and browser verification before release.

Display-copy corrections that do not alter evaluation semantics may retain the
version, but must still be recorded. Arbitrary user weights are outside version
1.0 because they would create an undocumented alternative model.
