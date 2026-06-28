from pathlib import Path

from src.pipeline import (
    build_lga_dashboard,
    build_state_approvals,
    normalise_lga_name,
    validate_outputs,
)


def test_known_lga_aliases_normalise() -> None:
    assert normalise_lga_name("Berri and Barmera (DC) Total") == "berribarmera"
    assert normalise_lga_name("Norwood Payneham St Peters (C) Total") == (
        "norwoodpaynehamandstpeters"
    )


def test_lga_dashboard_integrity() -> None:
    lga = build_lga_dashboard()
    assert len(lga) >= 70
    assert lga["LGA_Code"].is_unique
    assert lga["Complete_Score"].sum() >= 50
    assert not lga["LGA_Name"].str.contains("South Australia", case=False).any()
    assert not lga["LGA_Name"].str.contains("Migratory", case=False).any()
    assert lga.loc[lga["Complete_Score"], "Total_Count"].ge(10).all()


def test_state_period_labels_and_validation() -> None:
    monthly, annual, ytd = build_state_approvals()
    validate_outputs(build_lga_dashboard(), monthly)
    row_2026 = annual.loc[annual["Year"] == 2026].iloc[0]
    assert row_2026["Months_Covered"] == 4
    assert row_2026["Period_Status"] == "Year to date"
    assert "YTD" in row_2026["Year_Label"]
    assert ytd["Months_Compared"].eq(4).all()


def test_app_uses_current_streamlit_width_api() -> None:
    source = Path("app.py").read_text(encoding="utf-8")
    assert "use_container_width" not in source
