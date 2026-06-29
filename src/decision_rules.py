"""Transparent, non-advisory screening rules for the Decision Explorer.

The rules classify existing analytical evidence. They do not create a new
score, alter the Housing Pressure Index, forecast outcomes or recommend policy,
development or investment decisions.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Sequence

import pandas as pd
from pandas.api.types import is_bool_dtype


RULESET_ID = "sa-housing-screening-v1"
RULESET_VERSION = "1.0"

SOURCE_PERIODS = (
    "Rental bonds: December quarter 2025; household income: 2021 Census; "
    "population: 2024–25; LGA dwelling approvals: 2024–25."
)

FIXED_LIMITATIONS = (
    "Results are relative screening signals, not forecasts, causal findings, "
    "housing-shortage estimates or recommendations.",
    "Rental data cover bonds lodged in one quarter, not all tenancies, asking "
    "rents or vacancy; small counts are suppressed and published totals rounded.",
    "The rent-to-income measure combines current rent with 2021 Census household "
    "income and is an area-level proxy, not household rental stress.",
    "Building approvals are permits and may not become commenced, completed or "
    "occupied dwellings.",
    "Reference medians and percentile scores depend on the complete statewide "
    "eligible cohort and can change when source data or eligibility change.",
    "Infrastructure capacity is not measured.",
)

COMPONENTS = (
    ("Affordability", "Affordability_Pressure_Score"),
    ("Population growth", "Demand_Pressure_Score"),
    ("Lower approval rate", "Supply_Gap_Score"),
)

REQUIRED_COLUMNS = {
    "LGA_Name",
    "Complete_Score",
    "Affordability_Pressure_Score",
    "Demand_Pressure_Score",
    "Supply_Gap_Score",
    "Population_Growth_Pct",
    "Population_Change",
    "Approvals_per_1000",
    "Approvals_2024_25",
    "Other_Residential_Approval_Share_Pct",
    "Housing_Pressure_Index",
    "Housing_Pressure_Category",
    "Rent_to_Income_Proxy_Pct",
    "Total_Count",
    "Sample_Quality",
}

NUMERIC_SCREEN_COLUMNS = [
    "Affordability_Pressure_Score",
    "Demand_Pressure_Score",
    "Supply_Gap_Score",
    "Population_Growth_Pct",
    "Approvals_per_1000",
    "Housing_Pressure_Index",
    "Total_Count",
]


@dataclass(frozen=True)
class RuleMetadata:
    """Stable metadata for one screening rule."""

    rule_id: str
    name: str
    question: str
    expression: str
    permitted_interpretation: str


@dataclass(frozen=True)
class ReferenceBenchmarks:
    """Full-reference medians used by the comparison rule."""

    population_growth_median_pct: float
    approvals_per_1000_median: float
    complete_lga_count: int


@dataclass(frozen=True)
class ScreeningResult:
    """Evaluated screening frame and the full-reference benchmarks it used."""

    frame: pd.DataFrame
    benchmarks: ReferenceBenchmarks


RULES = (
    RuleMetadata(
        rule_id="broad_relative_pressure",
        name="Broad relative pressure",
        question="Are all three relative pressure components elevated?",
        expression=(
            "Complete_Score AND affordability >= 60 AND demand >= 60 "
            "AND supply_gap >= 60"
        ),
        permitted_interpretation=(
            "All three index components are at or above the 60th percentile "
            "among eligible South Australian LGAs."
        ),
    ),
    RuleMetadata(
        rule_id="affordability_led",
        name="Affordability-led pressure",
        question="Is affordability pressure very high with another elevated signal?",
        expression=(
            "Complete_Score AND affordability >= 80 AND "
            "(demand >= 40 OR supply_gap >= 40)"
        ),
        permitted_interpretation=(
            "The affordability component is at or above the 80th percentile and "
            "at least one other component is at or above the 40th percentile."
        ),
    ),
    RuleMetadata(
        rule_id="growth_lower_approvals",
        name="Higher growth with lower approvals",
        question=(
            "Is population growth above, and the approval rate below, the "
            "full-reference medians?"
        ),
        expression=(
            "Complete_Score AND population_growth > full-reference median "
            "AND approvals_per_1000 < full-reference median"
        ),
        permitted_interpretation=(
            "Population growth is above and approvals per 1,000 residents are "
            "below the medians of all complete scored LGAs; this is not proof of "
            "a shortage or inadequate delivery."
        ),
    ),
    RuleMetadata(
        rule_id="higher_pressure_stronger_sample",
        name="Higher pressure with stronger rental sample",
        question="Is relative pressure elevated with at least 20 published bonds?",
        expression=(
            "Complete_Score AND Housing_Pressure_Index >= 60 "
            "AND Total_Count >= 20"
        ),
        permitted_interpretation=(
            "The relative HPI is at least 60 and the quarterly rental evidence "
            "has the project's stronger sample classification."
        ),
    ),
    RuleMetadata(
        rule_id="evidence_gaps",
        name="Evidence gaps",
        question="Is the area ineligible for a complete pressure score?",
        expression="NOT Complete_Score",
        permitted_interpretation=(
            "The area requires evidence review and must not be presented or "
            "ranked as a low-pressure area."
        ),
    ),
)

RULE_BY_ID = {rule.rule_id: rule for rule in RULES}
POSITIVE_RULE_IDS = tuple(
    rule.rule_id for rule in RULES if rule.rule_id != "evidence_gaps"
)


def validate_screening_frame(frame: pd.DataFrame) -> None:
    """Validate the full statewide reference frame used by the rules."""

    if not isinstance(frame, pd.DataFrame):
        raise TypeError("Screening input must be a pandas DataFrame.")
    if frame.empty:
        raise ValueError("Screening input is empty.")

    missing = REQUIRED_COLUMNS.difference(frame.columns)
    if missing:
        raise ValueError(f"Screening input is missing columns: {sorted(missing)}")

    names = frame["LGA_Name"].astype("string").str.strip()
    if names.isna().any() or names.eq("").any():
        raise ValueError("LGA names must be present and non-blank.")
    duplicate_names = names[names.duplicated(keep=False)].drop_duplicates()
    if not duplicate_names.empty:
        raise ValueError(
            "Duplicate LGA names are not allowed: "
            f"{duplicate_names.head(5).tolist()}"
        )

    complete = frame["Complete_Score"]
    if (
        complete.isna().any()
        or not is_bool_dtype(complete.dtype)
        or not complete.isin([True, False]).all()
    ):
        raise ValueError("Complete_Score must contain only boolean values.")
    complete = complete.astype(bool)
    if not complete.any():
        raise ValueError("At least one complete scored LGA is required.")

    numeric = frame[NUMERIC_SCREEN_COLUMNS].apply(
        pd.to_numeric,
        errors="coerce",
    )
    for column in NUMERIC_SCREEN_COLUMNS:
        invalid = numeric.loc[complete, column].map(
            lambda value: not isfinite(value)
        )
        if invalid.any():
            affected = names.loc[complete].loc[invalid].head(5).tolist()
            raise ValueError(
                f"Complete scored LGAs have non-finite {column}: {affected}"
            )

    score_columns = [
        "Affordability_Pressure_Score",
        "Demand_Pressure_Score",
        "Supply_Gap_Score",
        "Housing_Pressure_Index",
    ]
    outside_score_range = ~numeric.loc[complete, score_columns].apply(
        lambda series: series.between(0, 100, inclusive="both")
    )
    if outside_score_range.any().any():
        raise ValueError("Complete scored LGAs have a score outside 0–100.")
    if numeric.loc[complete, "Approvals_per_1000"].lt(0).any():
        raise ValueError("Approvals_per_1000 cannot be negative.")
    if numeric.loc[complete, "Total_Count"].lt(10).any():
        raise ValueError(
            "Complete scored LGAs must have at least 10 published rental bonds."
        )


def calculate_reference_benchmarks(
    full_reference: pd.DataFrame,
) -> ReferenceBenchmarks:
    """Calculate medians from every complete row in the full reference frame."""

    validate_screening_frame(full_reference)
    complete = full_reference["Complete_Score"].astype(bool)
    growth = pd.to_numeric(
        full_reference.loc[complete, "Population_Growth_Pct"],
        errors="raise",
    )
    approvals = pd.to_numeric(
        full_reference.loc[complete, "Approvals_per_1000"],
        errors="raise",
    )
    return ReferenceBenchmarks(
        population_growth_median_pct=float(growth.median()),
        approvals_per_1000_median=float(approvals.median()),
        complete_lga_count=int(complete.sum()),
    )


def _highest_component(
    row: pd.Series,
    *,
    complete: bool,
) -> tuple[str, float | None, bool]:
    """Return the highest component label, score and exact-tie flag."""

    if not complete:
        return "Not assessed", None, False
    values = {
        label: float(row[column])
        for label, column in COMPONENTS
    }
    maximum = max(values.values())
    leaders = [
        label for label, value in values.items() if value == maximum
    ]
    if len(leaders) == 1:
        return leaders[0], maximum, False
    return f"Joint: {' + '.join(leaders)}", maximum, True


def _evidence_gap_reason(row: pd.Series) -> str:
    """Explain why an unscored row requires evidence review."""

    if bool(row["Complete_Score"]):
        return ""
    count = pd.to_numeric(pd.Series([row["Total_Count"]]), errors="coerce").iloc[0]
    if pd.isna(count):
        return "Published total rental-bond count is unavailable or suppressed."
    if count < 10:
        return (
            f"Published total rental-bond count is {count:.0f}, below the "
            "minimum score sample of 10."
        )
    return "One or more inputs required for the pressure index are unavailable."


def _rule_reason(
    rule_id: str,
    row: pd.Series,
    benchmarks: ReferenceBenchmarks,
    matched: bool,
) -> str:
    """Build a deterministic, auditable reason for a rule result."""

    complete = bool(row["Complete_Score"])
    if rule_id == "evidence_gaps":
        return (
            _evidence_gap_reason(row)
            if matched
            else "Complete_Score is true; the area has a complete pressure score."
        )
    if not complete:
        return "Not matched because Complete_Score is false."

    affordability = float(row["Affordability_Pressure_Score"])
    demand = float(row["Demand_Pressure_Score"])
    supply_gap = float(row["Supply_Gap_Score"])
    growth = float(row["Population_Growth_Pct"])
    approvals = float(row["Approvals_per_1000"])
    hpi = float(row["Housing_Pressure_Index"])
    count = float(row["Total_Count"])

    if rule_id == "broad_relative_pressure":
        return (
            f"Component scores: affordability {affordability:.1f}, demand "
            f"{demand:.1f}, supply gap {supply_gap:.1f}; all must be at least 60."
        )
    if rule_id == "affordability_led":
        return (
            f"Affordability is {affordability:.1f} (required >=80); demand is "
            f"{demand:.1f} and supply gap is {supply_gap:.1f} "
            "(at least one required >=40)."
        )
    if rule_id == "growth_lower_approvals":
        return (
            f"Population growth is {growth:.1f}% versus the full-reference "
            f"median {benchmarks.population_growth_median_pct:.1f}%; approvals "
            f"are {approvals:.2f} per 1,000 versus the full-reference median "
            f"{benchmarks.approvals_per_1000_median:.2f}. Strict > and < tests apply."
        )
    if rule_id == "higher_pressure_stronger_sample":
        return (
            f"HPI is {hpi:.1f} (required >=60) and the published quarterly "
            f"rental-bond count is {count:.0f} (required >=20)."
        )
    raise KeyError(f"Unknown rule ID: {rule_id}")


def evaluate_rules(full_reference: pd.DataFrame) -> ScreeningResult:
    """Evaluate all fixed rules against a full, unfiltered reference frame."""

    validate_screening_frame(full_reference)
    benchmarks = calculate_reference_benchmarks(full_reference)
    result = full_reference.copy(deep=True)
    complete = result["Complete_Score"].astype(bool)
    numeric = result[NUMERIC_SCREEN_COLUMNS].apply(
        pd.to_numeric,
        errors="coerce",
    )

    matches = {
        "broad_relative_pressure": (
            complete
            & numeric["Affordability_Pressure_Score"].ge(60)
            & numeric["Demand_Pressure_Score"].ge(60)
            & numeric["Supply_Gap_Score"].ge(60)
        ),
        "affordability_led": (
            complete
            & numeric["Affordability_Pressure_Score"].ge(80)
            & (
                numeric["Demand_Pressure_Score"].ge(40)
                | numeric["Supply_Gap_Score"].ge(40)
            )
        ),
        "growth_lower_approvals": (
            complete
            & numeric["Population_Growth_Pct"].gt(
                benchmarks.population_growth_median_pct
            )
            & numeric["Approvals_per_1000"].lt(
                benchmarks.approvals_per_1000_median
            )
        ),
        "higher_pressure_stronger_sample": (
            complete
            & numeric["Housing_Pressure_Index"].ge(60)
            & numeric["Total_Count"].ge(20)
        ),
        "evidence_gaps": ~complete,
    }

    for rule in RULES:
        match_column = f"Rule_{rule.rule_id}_Matched"
        reason_column = f"Rule_{rule.rule_id}_Reason"
        result[match_column] = matches[rule.rule_id].astype(bool)
        result[reason_column] = [
            _rule_reason(
                rule.rule_id,
                row,
                benchmarks,
                bool(is_match),
            )
            for (_, row), is_match in zip(
                result.iterrows(),
                matches[rule.rule_id],
            )
        ]

    component_results = [
        _highest_component(row, complete=bool(is_complete))
        for (_, row), is_complete in zip(result.iterrows(), complete)
    ]
    result["Highest_Index_Component"] = [
        item[0] for item in component_results
    ]
    result["Highest_Component_Score"] = [
        item[1] for item in component_results
    ]
    result["Highest_Component_Is_Tied"] = [
        item[2] for item in component_results
    ]
    result["Evidence_Gap_Reason"] = [
        _evidence_gap_reason(row) for _, row in result.iterrows()
    ]
    result["Matched_Rule_IDs"] = [
        ";".join(
            rule.rule_id
            for rule in RULES
            if bool(result.at[index, f"Rule_{rule.rule_id}_Matched"])
        )
        for index in result.index
    ]
    result["Pressure_Ranking_Status"] = complete.map(
        {
            True: "Scored — may be ordered by the existing HPI",
            False: "Evidence gap — not pressure-ranked",
        }
    )
    result["Ruleset_ID"] = RULESET_ID
    result["Ruleset_Version"] = RULESET_VERSION
    return ScreeningResult(frame=result, benchmarks=benchmarks)


def deterministic_matched_shortlist(
    screening: ScreeningResult,
    rule_ids: Sequence[str] | None = None,
) -> pd.DataFrame:
    """Return matches with evidence gaps separated from pressure-ranked rows."""

    selected_rules = tuple(rule_ids) if rule_ids is not None else tuple(
        rule.rule_id for rule in RULES
    )
    if not selected_rules:
        raise ValueError("At least one rule ID must be selected.")
    unknown = [rule_id for rule_id in selected_rules if rule_id not in RULE_BY_ID]
    if unknown:
        raise ValueError(f"Unknown rule IDs: {unknown}")
    if len(set(selected_rules)) != len(selected_rules):
        raise ValueError("Rule IDs must be unique.")

    frame = screening.frame.copy(deep=True)
    selected_match_columns = [
        f"Rule_{rule_id}_Matched" for rule_id in selected_rules
    ]
    shortlist = frame.loc[frame[selected_match_columns].any(axis=1)].copy()
    shortlist["Matched_Selected_Rule_IDs"] = [
        ";".join(
            rule_id
            for rule_id in selected_rules
            if bool(shortlist.at[index, f"Rule_{rule_id}_Matched"])
        )
        for index in shortlist.index
    ]

    evidence = shortlist["Rule_evidence_gaps_Matched"]
    positive = shortlist.loc[~evidence].sort_values(
        ["Housing_Pressure_Index", "LGA_Name"],
        ascending=[False, True],
        kind="stable",
    )
    positive["Shortlist_Section"] = "Pressure-screen matches"
    evidence_rows = shortlist.loc[evidence].sort_values(
        "LGA_Name",
        kind="stable",
    )
    evidence_rows["Shortlist_Section"] = (
        "Evidence review — not pressure-ranked"
    )
    return pd.concat([positive, evidence_rows], ignore_index=True)


def select_comparison_lgas(
    screening: ScreeningResult,
    lga_names: Sequence[str],
) -> pd.DataFrame:
    """Select two to five unique LGAs while preserving requested order."""

    selected = [str(name).strip() for name in lga_names]
    if not 2 <= len(selected) <= 5:
        raise ValueError("Select between 2 and 5 LGAs for comparison.")
    if any(not name for name in selected):
        raise ValueError("Comparison LGA names must be non-blank.")
    if len(set(selected)) != len(selected):
        raise ValueError("Comparison LGA names must be unique.")

    available = screening.frame.set_index("LGA_Name", drop=False)
    missing = [name for name in selected if name not in available.index]
    if missing:
        raise ValueError(f"Unknown comparison LGAs: {missing}")
    return available.loc[selected].reset_index(drop=True).copy(deep=True)


def build_auditable_export(screening: ScreeningResult) -> pd.DataFrame:
    """Return one auditable row per LGA and rule."""

    records: list[dict[str, object]] = []
    for _, row in screening.frame.iterrows():
        for rule in RULES:
            records.append(
                {
                    "Ruleset_ID": RULESET_ID,
                    "Ruleset_Version": RULESET_VERSION,
                    "LGA_Name": row["LGA_Name"],
                    "Rule_ID": rule.rule_id,
                    "Rule_Name": rule.name,
                    "Question": rule.question,
                    "Expression": rule.expression,
                    "Matched": bool(
                        row[f"Rule_{rule.rule_id}_Matched"]
                    ),
                    "Evaluation_Reason": row[
                        f"Rule_{rule.rule_id}_Reason"
                    ],
                    "Permitted_Interpretation": (
                        rule.permitted_interpretation
                    ),
                    "Housing_Pressure_Index": row[
                        "Housing_Pressure_Index"
                    ],
                    "Housing_Pressure_Category": row[
                        "Housing_Pressure_Category"
                    ],
                    "Affordability_Pressure_Score": row[
                        "Affordability_Pressure_Score"
                    ],
                    "Demand_Pressure_Score": row[
                        "Demand_Pressure_Score"
                    ],
                    "Supply_Gap_Score": row[
                        "Supply_Gap_Score"
                    ],
                    "Rent_to_Income_Proxy_Pct": row[
                        "Rent_to_Income_Proxy_Pct"
                    ],
                    "Population_Growth_Pct": row[
                        "Population_Growth_Pct"
                    ],
                    "Population_Change": row["Population_Change"],
                    "Approvals_per_1000": row["Approvals_per_1000"],
                    "Approvals_2024_25": row["Approvals_2024_25"],
                    "Other_Residential_Approval_Share_Pct": row[
                        "Other_Residential_Approval_Share_Pct"
                    ],
                    "Total_Count": row["Total_Count"],
                    "Sample_Quality": row["Sample_Quality"],
                    "Highest_Index_Component": row[
                        "Highest_Index_Component"
                    ],
                    "Highest_Component_Score": row[
                        "Highest_Component_Score"
                    ],
                    "Highest_Component_Is_Tied": row[
                        "Highest_Component_Is_Tied"
                    ],
                    "Evidence_Gap_Reason": row["Evidence_Gap_Reason"],
                    "Pressure_Ranking_Status": row[
                        "Pressure_Ranking_Status"
                    ],
                    "Reference_Population_Growth_Median_Pct": (
                        screening.benchmarks.population_growth_median_pct
                    ),
                    "Reference_Approvals_per_1000_Median": (
                        screening.benchmarks.approvals_per_1000_median
                    ),
                    "Reference_Complete_LGA_Count": (
                        screening.benchmarks.complete_lga_count
                    ),
                    "Source_Periods": SOURCE_PERIODS,
                    "Fixed_Limitations": " | ".join(FIXED_LIMITATIONS),
                }
            )
    return pd.DataFrame.from_records(records)


def build_markdown_decision_brief(
    screening: ScreeningResult,
    lga_names: Sequence[str],
) -> str:
    """Build a deterministic, non-advisory Markdown comparison brief."""

    selected = select_comparison_lgas(screening, lga_names)
    lines = [
        "# SA Housing Decision Explorer brief",
        "",
        f"Ruleset: `{RULESET_ID}` version `{RULESET_VERSION}`.",
        "",
        "This brief reports fixed screening-rule results. It does not recommend "
        "policy, development, investment or resource allocation.",
        "",
        "## Full-reference benchmarks",
        "",
        (
            "- Population growth median: "
            f"{screening.benchmarks.population_growth_median_pct:.1f}%."
        ),
        (
            "- Approvals per 1,000 median: "
            f"{screening.benchmarks.approvals_per_1000_median:.2f}."
        ),
        (
            "- Complete scored LGAs in reference: "
            f"{screening.benchmarks.complete_lga_count}."
        ),
        "",
        "## Selected LGAs",
        "",
    ]

    for _, row in selected.iterrows():
        matched = [
            rule
            for rule in RULES
            if bool(row[f"Rule_{rule.rule_id}_Matched"])
        ]
        lines.extend(
            [
                f"### {row['LGA_Name']}",
                "",
                f"- Ranking status: {row['Pressure_Ranking_Status']}.",
                (
                    "- Highest index component: "
                    f"{row['Highest_Index_Component']}"
                    + (
                        f" ({float(row['Highest_Component_Score']):.1f})."
                        if pd.notna(row["Highest_Component_Score"])
                        else "."
                    )
                ),
                (
                    "- Matched rules: "
                    + (
                        ", ".join(rule.name for rule in matched)
                        if matched
                        else "None"
                    )
                    + "."
                ),
            ]
        )
        if row["Evidence_Gap_Reason"]:
            lines.append(
                f"- Evidence gap: {row['Evidence_Gap_Reason']}"
            )
        for rule in matched:
            lines.append(
                f"- **{rule.name}:** "
                f"{row[f'Rule_{rule.rule_id}_Reason']} "
                f"Permitted interpretation: {rule.permitted_interpretation}"
            )
        lines.append("")

    lines.extend(
        [
            "## Source periods",
            "",
            SOURCE_PERIODS,
            "",
            "## Fixed limitations",
            "",
        ]
    )
    lines.extend(f"- {limitation}" for limitation in FIXED_LIMITATIONS)
    return "\n".join(lines).rstrip() + "\n"
