from pathlib import Path

import pandas as pd
import pandas.testing as pdt

from src.decision_rules import (
    REQUIRED_COLUMNS,
    RULES,
    RULESET_ID,
    RULESET_VERSION,
    build_auditable_export,
    evaluate_rules,
)


ROOT = Path(__file__).resolve().parents[1]
LGA_CSV = ROOT / "data" / "processed" / "dashboard_lga_pressure.csv"
APP = ROOT / "app.py"


def _load_lga() -> pd.DataFrame:
    frame = pd.read_csv(LGA_CSV)
    frame["Complete_Score"] = (
        frame["Complete_Score"].astype(str).str.lower().eq("true")
    )
    return frame


def test_committed_dataset_full_reference_contract() -> None:
    frame = _load_lga()
    screening = evaluate_rules(frame)
    complete = frame["Complete_Score"]

    assert frame.shape[0] == 71
    assert REQUIRED_COLUMNS.issubset(frame.columns)
    assert complete.sum() == 53
    assert screening.benchmarks.complete_lga_count == 53
    assert screening.benchmarks.population_growth_median_pct == float(
        frame.loc[complete, "Population_Growth_Pct"].median()
    )
    assert screening.benchmarks.approvals_per_1000_median == float(
        frame.loc[complete, "Approvals_per_1000"].median()
    )


def test_full_reference_benchmarks_survive_subsetting() -> None:
    screening = evaluate_rules(_load_lga())
    subset = screening.frame.head(5)

    assert screening.benchmarks.complete_lga_count == 53
    assert len(subset) == 5
    assert screening.benchmarks.population_growth_median_pct != float(
        subset.loc[
            subset["Complete_Score"], "Population_Growth_Pct"
        ].median()
    )


def test_current_rule_outputs_are_complete_deterministic_and_non_mutating() -> None:
    frame = _load_lga()
    hpi_before = frame[
        ["LGA_Name", "Housing_Pressure_Index", "Housing_Pressure_Category"]
    ].copy()

    first = evaluate_rules(frame)
    second = evaluate_rules(frame)

    assert first.frame.shape[0] == 71
    assert first.frame["LGA_Name"].is_unique
    pdt.assert_frame_equal(first.frame, second.frame)
    pdt.assert_frame_equal(
        hpi_before,
        first.frame[
            ["LGA_Name", "Housing_Pressure_Index", "Housing_Pressure_Category"]
        ],
    )
    for rule in RULES:
        assert first.frame[f"Rule_{rule.rule_id}_Matched"].dtype == bool
        assert first.frame[f"Rule_{rule.rule_id}_Reason"].str.strip().ne("").all()


def test_current_audit_export_is_exactly_71_by_5_rules() -> None:
    export = build_auditable_export(evaluate_rules(_load_lga()))

    assert len(export) == 71 * 5
    assert export[["LGA_Name", "Rule_ID"]].duplicated().sum() == 0
    assert export["LGA_Name"].nunique() == 71
    assert export["Rule_ID"].nunique() == 5
    assert export["Ruleset_ID"].eq(RULESET_ID).all()
    assert export["Ruleset_Version"].eq(RULESET_VERSION).all()


def test_app_wires_decision_module_before_sidebar_filtering() -> None:
    source = APP.read_text(encoding="utf-8")

    assert "from src.decision_rules import (" in source
    assert source.count("screening = evaluate_rules(lga)") == 1
    assert source.index("screening = evaluate_rules(lga)") < source.index(
        "selected_categories = st.sidebar.multiselect("
    )
    assert source.index("screening = evaluate_rules(lga)") < source.index(
        "filtered = lga["
    )


def test_app_has_seventh_tab_without_duplicating_rule_conditions() -> None:
    source = APP.read_text(encoding="utf-8")

    assert '"Decision Explorer",' in source
    assert "with tabs[6]:" in source
    assert '["Affordability_Pressure_Score"].ge(' not in source
    assert '["Demand_Pressure_Score"].ge(' not in source
    assert '["Supply_Gap_Score"].ge(' not in source
    assert ".ge(60)" not in source
    assert ".ge(80)" not in source
    assert "growth_lower_approvals" not in source


def test_app_downloads_are_versioned_and_language_is_non_advisory() -> None:
    source = APP.read_text(encoding="utf-8")
    explorer = source[source.index("with tabs[6]:"):]

    assert "version_slug = RULESET_VERSION.replace" in explorer
    assert "sa_decision_shortlist_" in explorer
    assert "sa_decision_brief_v" in explorer
    assert "does not recommend policy, development, investment" in explorer
    assert "not a forecast or a housing-shortage model" in explorer
    assert "not a new priority score" in explorer
