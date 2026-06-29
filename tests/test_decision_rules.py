from copy import deepcopy

import pandas as pd
import pandas.testing as pdt
import pytest

from src.decision_rules import (
    FIXED_LIMITATIONS,
    POSITIVE_RULE_IDS,
    REQUIRED_COLUMNS,
    RULES,
    RULESET_ID,
    RULESET_VERSION,
    SOURCE_PERIODS,
    build_auditable_export,
    build_markdown_decision_brief,
    calculate_reference_benchmarks,
    deterministic_matched_shortlist,
    evaluate_rules,
    select_comparison_lgas,
    validate_screening_frame,
)


EXPORT_COLUMNS = [
    "Ruleset_ID",
    "Ruleset_Version",
    "LGA_Name",
    "Rule_ID",
    "Rule_Name",
    "Question",
    "Expression",
    "Matched",
    "Evaluation_Reason",
    "Permitted_Interpretation",
    "Housing_Pressure_Index",
    "Housing_Pressure_Category",
    "Affordability_Pressure_Score",
    "Demand_Pressure_Score",
    "Supply_Gap_Score",
    "Rent_to_Income_Proxy_Pct",
    "Population_Growth_Pct",
    "Population_Change",
    "Approvals_per_1000",
    "Approvals_2024_25",
    "Other_Residential_Approval_Share_Pct",
    "Total_Count",
    "Sample_Quality",
    "Highest_Index_Component",
    "Highest_Component_Score",
    "Highest_Component_Is_Tied",
    "Evidence_Gap_Reason",
    "Pressure_Ranking_Status",
    "Reference_Population_Growth_Median_Pct",
    "Reference_Approvals_per_1000_Median",
    "Reference_Complete_LGA_Count",
    "Source_Periods",
    "Fixed_Limitations",
]


def _row(
    name: str,
    *,
    complete: bool = True,
    affordability: float = 50,
    demand: float = 50,
    supply_gap: float = 50,
    growth: float = 2,
    approvals_rate: float = 10,
    hpi: float = 50,
    count: float | None = 20,
    category: str = "Moderate",
) -> dict[str, object]:
    return {
        "LGA_Name": name,
        "Complete_Score": complete,
        "Affordability_Pressure_Score": affordability,
        "Demand_Pressure_Score": demand,
        "Supply_Gap_Score": supply_gap,
        "Population_Growth_Pct": growth,
        "Population_Change": 100,
        "Approvals_per_1000": approvals_rate,
        "Approvals_2024_25": 200,
        "Other_Residential_Approval_Share_Pct": 25,
        "Housing_Pressure_Index": hpi,
        "Housing_Pressure_Category": category,
        "Rent_to_Income_Proxy_Pct": 35,
        "Total_Count": count,
        "Sample_Quality": (
            "Stronger (20+ bonds)"
            if count is not None and count >= 20
            else "Caution (<10 bonds)"
        ),
    }


def _truth_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            _row(
                "Overlap",
                affordability=80,
                demand=60,
                supply_gap=60,
                growth=3,
                approvals_rate=5,
                hpi=80,
                category="Very High",
            ),
            _row("Median", growth=2, approvals_rate=10),
            _row("Lower pressure", growth=1, approvals_rate=15, count=19),
            _row(
                "Evidence B",
                complete=False,
                affordability=float("nan"),
                demand=float("inf"),
                supply_gap=float("-inf"),
                growth=float("nan"),
                approvals_rate=float("nan"),
                hpi=float("nan"),
                count=None,
                category="Not scored",
            ),
            _row(
                "Evidence A",
                complete=False,
                affordability=float("nan"),
                demand=float("nan"),
                supply_gap=float("nan"),
                growth=float("nan"),
                approvals_rate=float("nan"),
                hpi=float("nan"),
                count=5,
                category="Not scored",
            ),
        ]
    )


def test_fixed_ruleset_identity_and_metadata() -> None:
    assert RULESET_ID == "sa-housing-screening-v1"
    assert RULESET_VERSION == "1.0"
    assert [(rule.rule_id, rule.expression) for rule in RULES] == [
        (
            "broad_relative_pressure",
            "Complete_Score AND affordability >= 60 AND demand >= 60 "
            "AND supply_gap >= 60",
        ),
        (
            "affordability_led",
            "Complete_Score AND affordability >= 80 AND "
            "(demand >= 40 OR supply_gap >= 40)",
        ),
        (
            "growth_lower_approvals",
            "Complete_Score AND population_growth > full-reference median "
            "AND approvals_per_1000 < full-reference median",
        ),
        (
            "higher_pressure_stronger_sample",
            "Complete_Score AND Housing_Pressure_Index >= 60 "
            "AND Total_Count >= 20",
        ),
        ("evidence_gaps", "NOT Complete_Score"),
    ]
    assert POSITIVE_RULE_IDS == tuple(
        rule.rule_id for rule in RULES if rule.rule_id != "evidence_gaps"
    )
    for rule in RULES:
        assert all(
            value.strip()
            for value in (
                rule.rule_id,
                rule.name,
                rule.question,
                rule.expression,
                rule.permitted_interpretation,
            )
        )
    assert "2025" in SOURCE_PERIODS
    assert "2021 Census" in SOURCE_PERIODS
    assert len(FIXED_LIMITATIONS) >= 5


@pytest.mark.parametrize("missing", sorted(REQUIRED_COLUMNS))
def test_every_required_column_is_enforced(missing: str) -> None:
    frame = _truth_frame().drop(columns=missing)

    with pytest.raises(ValueError, match="missing columns"):
        validate_screening_frame(frame)


@pytest.mark.parametrize(
    ("affordability", "demand", "supply_gap", "matched"),
    [
        (60, 60, 60, True),
        (59.9, 60, 60, False),
        (60, 59.9, 60, False),
        (60, 60, 59.9, False),
    ],
)
def test_broad_pressure_threshold_boundaries(
    affordability: float,
    demand: float,
    supply_gap: float,
    matched: bool,
) -> None:
    frame = _truth_frame()
    frame.loc[0, [
        "Affordability_Pressure_Score",
        "Demand_Pressure_Score",
        "Supply_Gap_Score",
    ]] = [affordability, demand, supply_gap]

    result = evaluate_rules(frame).frame

    assert bool(result.loc[0, "Rule_broad_relative_pressure_Matched"]) is matched


@pytest.mark.parametrize(
    ("affordability", "demand", "supply_gap", "matched"),
    [
        (80, 40, 39.9, True),
        (80, 39.9, 40, True),
        (79.9, 80, 80, False),
        (80, 39.9, 39.9, False),
    ],
)
def test_affordability_led_threshold_boundaries(
    affordability: float,
    demand: float,
    supply_gap: float,
    matched: bool,
) -> None:
    frame = _truth_frame()
    frame.loc[0, [
        "Affordability_Pressure_Score",
        "Demand_Pressure_Score",
        "Supply_Gap_Score",
    ]] = [affordability, demand, supply_gap]

    result = evaluate_rules(frame).frame

    assert bool(result.loc[0, "Rule_affordability_led_Matched"]) is matched


@pytest.mark.parametrize(
    ("hpi", "count", "matched"),
    [(60, 20, True), (59.9, 20, False), (60, 19.9, False), (79.9, 20, True), (80, 20, True)],
)
def test_stronger_sample_threshold_boundaries(
    hpi: float, count: float, matched: bool
) -> None:
    frame = _truth_frame()
    frame.loc[0, ["Housing_Pressure_Index", "Total_Count"]] = [hpi, count]

    result = evaluate_rules(frame).frame

    assert (
        bool(result.loc[0, "Rule_higher_pressure_stronger_sample_Matched"])
        is matched
    )


def test_growth_and_approvals_use_strict_full_reference_medians() -> None:
    frame = _truth_frame()
    result = evaluate_rules(frame)

    assert result.benchmarks.population_growth_median_pct == 2
    assert result.benchmarks.approvals_per_1000_median == 10
    assert result.benchmarks.complete_lga_count == 3
    assert result.frame.loc[
        result.frame["LGA_Name"].eq("Overlap"),
        "Rule_growth_lower_approvals_Matched",
    ].item()
    assert not result.frame.loc[
        result.frame["LGA_Name"].eq("Median"),
        "Rule_growth_lower_approvals_Matched",
    ].item()


def test_all_five_rules_and_non_exclusive_overlap() -> None:
    result = evaluate_rules(_truth_frame()).frame.set_index("LGA_Name")

    assert result.at["Overlap", "Rule_broad_relative_pressure_Matched"]
    assert result.at["Overlap", "Rule_affordability_led_Matched"]
    assert result.at["Overlap", "Rule_growth_lower_approvals_Matched"]
    assert result.at["Overlap", "Rule_higher_pressure_stronger_sample_Matched"]
    assert not result.at["Overlap", "Rule_evidence_gaps_Matched"]
    assert result.at["Evidence A", "Rule_evidence_gaps_Matched"]
    assert result.at["Evidence A", "Matched_Rule_IDs"] == "evidence_gaps"


def test_evidence_gap_reasons_cover_suppressed_low_and_missing_inputs() -> None:
    result = evaluate_rules(_truth_frame()).frame.set_index("LGA_Name")

    assert "unavailable or suppressed" in result.at[
        "Evidence B", "Evidence_Gap_Reason"
    ]
    assert "below the minimum" in result.at[
        "Evidence A", "Evidence_Gap_Reason"
    ]
    assert not result.loc[
        ["Evidence A", "Evidence B"],
        [f"Rule_{rule_id}_Matched" for rule_id in POSITIVE_RULE_IDS],
    ].to_numpy().any()


def test_non_finite_complete_values_rejected_but_incomplete_values_safe() -> None:
    evaluate_rules(_truth_frame())
    for value in (float("nan"), float("inf"), float("-inf")):
        frame = _truth_frame()
        frame.loc[0, "Demand_Pressure_Score"] = value
        with pytest.raises(ValueError, match="non-finite"):
            evaluate_rules(frame)


@pytest.mark.parametrize("name", ["", "   ", None])
def test_blank_lga_names_rejected(name: str | None) -> None:
    frame = _truth_frame()
    frame.loc[0, "LGA_Name"] = name
    with pytest.raises(ValueError, match="non-blank"):
        validate_screening_frame(frame)


def test_duplicate_lga_names_rejected_after_trimming() -> None:
    frame = _truth_frame()
    frame.loc[1, "LGA_Name"] = " Overlap "
    with pytest.raises(ValueError, match="Duplicate LGA names"):
        validate_screening_frame(frame)


def test_no_complete_reference_cohort_rejected() -> None:
    frame = _truth_frame()
    frame["Complete_Score"] = False
    with pytest.raises(ValueError, match="At least one complete"):
        calculate_reference_benchmarks(frame)


def test_evaluation_is_deterministic_and_does_not_mutate_inputs() -> None:
    frame = _truth_frame()
    original = deepcopy(frame)

    first = evaluate_rules(frame)
    second = evaluate_rules(frame)

    pdt.assert_frame_equal(frame, original)
    pdt.assert_frame_equal(first.frame, second.frame)
    assert first.benchmarks == second.benchmarks


def test_shortlist_orders_pressure_by_hpi_and_evidence_alphabetically() -> None:
    screening = evaluate_rules(_truth_frame())

    shortlist = deterministic_matched_shortlist(screening)

    evidence_start = shortlist["Shortlist_Section"].eq(
        "Evidence review — not pressure-ranked"
    ).idxmax()
    pressure = shortlist.iloc[:evidence_start]
    evidence = shortlist.iloc[evidence_start:]
    assert pressure["Housing_Pressure_Index"].is_monotonic_decreasing
    assert evidence["LGA_Name"].tolist() == ["Evidence A", "Evidence B"]


@pytest.mark.parametrize("names", [[], ["Overlap"], ["Overlap"] * 6])
def test_comparison_requires_two_to_five_lgas(names: list[str]) -> None:
    screening = evaluate_rules(_truth_frame())
    with pytest.raises(ValueError, match="between 2 and 5"):
        select_comparison_lgas(screening, names)


def test_comparison_preserves_order_and_rejects_duplicates_or_unknowns() -> None:
    screening = evaluate_rules(_truth_frame())
    selected = select_comparison_lgas(screening, ["Median", "Overlap"])
    assert selected["LGA_Name"].tolist() == ["Median", "Overlap"]
    five = ["Evidence B", "Overlap", "Median", "Evidence A", "Lower pressure"]
    assert select_comparison_lgas(screening, five)["LGA_Name"].tolist() == five
    with pytest.raises(ValueError, match="unique"):
        select_comparison_lgas(screening, ["Overlap", "Overlap"])
    with pytest.raises(ValueError, match="Unknown"):
        select_comparison_lgas(screening, ["Overlap", "Unknown"])


def test_auditable_export_has_exact_raw_and_metadata_contract() -> None:
    screening = evaluate_rules(_truth_frame())

    export = build_auditable_export(screening)

    assert export.columns.tolist() == EXPORT_COLUMNS
    assert export.shape == (len(_truth_frame()) * len(RULES), len(EXPORT_COLUMNS))
    assert export["Ruleset_ID"].eq(RULESET_ID).all()
    assert export["Ruleset_Version"].eq(RULESET_VERSION).all()
    assert export["Source_Periods"].eq(SOURCE_PERIODS).all()
    assert export.groupby("LGA_Name")["Rule_ID"].nunique().eq(5).all()


def test_markdown_brief_is_deterministic_and_contains_safety_limitations() -> None:
    screening = evaluate_rules(_truth_frame())

    first = build_markdown_decision_brief(screening, ["Overlap", "Evidence A"])
    second = build_markdown_decision_brief(screening, ["Overlap", "Evidence A"])

    assert first == second
    assert "does not recommend" in first
    assert SOURCE_PERIODS in first
    assert all(limitation in first for limitation in FIXED_LIMITATIONS)
    assert first.endswith("\n")


def test_evaluation_does_not_change_existing_hpi_or_category() -> None:
    frame = _truth_frame()
    before = frame[["Housing_Pressure_Index", "Housing_Pressure_Category"]].copy()

    after = evaluate_rules(frame).frame

    pdt.assert_frame_equal(
        before,
        after[["Housing_Pressure_Index", "Housing_Pressure_Category"]],
    )
