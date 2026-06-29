"""Streamlit application for the SA Housing Pressure & Supply Dashboard."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.decision_rules import (
    POSITIVE_RULE_IDS,
    RULE_BY_ID,
    RULES,
    RULESET_ID,
    RULESET_VERSION,
    build_auditable_export,
    build_markdown_decision_brief,
    deterministic_matched_shortlist,
    evaluate_rules,
    select_comparison_lgas,
)


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data" / "processed"

CATEGORY_ORDER = ["Very High", "High", "Moderate", "Low", "Very Low", "Not scored"]
CATEGORY_COLOURS = {
    "Very High": "#991B1B",
    "High": "#DC2626",
    "Moderate": "#F59E0B",
    "Low": "#2563EB",
    "Very Low": "#0F766E",
    "Not scored": "#64748B",
}

CHART_CONFIG = {
    "displaylogo": False,
    "responsive": True,
    "scrollZoom": False,
}

REQUIRED_LGA_COLUMNS = {
    "LGA_Name",
    "Total_Median",
    "Unit_Total_Median",
    "House_Total_Median",
    "Total_Count",
    "Unit_Total_Count",
    "House_Total_Count",
    "Sample_Quality",
    "Median_Weekly_Household_Income_2021",
    "Rent_to_Income_Proxy_Pct",
    "Unit_Rent_to_Income_Proxy_Pct",
    "House_Rent_to_Income_Proxy_Pct",
    "House_Unit_Rent_Gap",
    "House_Unit_Rent_Premium_Pct",
    "Population_Change",
    "Population_2025",
    "Population_Growth_Pct",
    "Natural_Increase_2024_25",
    "Net_Internal_Migration_2024_25",
    "Net_Overseas_Migration_2024_25",
    "Population_Density_2025",
    "House_Approvals_2024_25",
    "Other_Residential_Approvals_2024_25",
    "Residual_Approval_Units_2024_25",
    "Approvals_2024_25",
    "Approvals_2025_26_FYTD",
    "Other_Residential_Approval_Share_Pct",
    "Approvals_per_100_New_Residents",
    "Approvals_per_1000",
    "Affordability_Pressure_Score",
    "Demand_Pressure_Score",
    "Supply_Gap_Score",
    "Housing_Pressure_Index",
    "Housing_Pressure_Category",
    "Eligible_for_Score",
    "Complete_Score",
}
REQUIRED_MONTHLY_COLUMNS = {
    "Month",
    "House_Approvals",
    "Non_House_Approvals",
    "Dwelling_Approvals",
    "Rolling_3_Month_Avg",
    "Non_House_Approval_Share_Pct",
    "Rolling_12_Month_Total",
    "Rolling_12_Month_YoY_Change_Pct",
    "Series_Type",
}
REQUIRED_ANNUAL_COLUMNS = {
    "Year",
    "Dwelling_Approvals",
    "Months_Covered",
    "Period_Status",
    "Year_Label",
}
REQUIRED_YTD_COLUMNS = {
    "Year",
    "YTD_Dwelling_Approvals",
    "Months_Compared",
    "Prior_Year_YTD_Dwelling_Approvals",
    "YTD_YoY_Change_Pct",
    "Comparison_Label",
}


st.set_page_config(
    page_title="SA Housing Pressure & Supply",
    page_icon="🏘️",
    layout="wide",
)

st.markdown(
    """
    <style>
      .block-container {
        padding-top: 1.75rem;
        padding-bottom: 3rem;
        max-width: 1400px;
      }
      [data-testid="stMetric"] {
        border: 1px solid rgba(100, 116, 139, 0.35);
        border-radius: 0.65rem;
        padding: 0.8rem 1rem;
        background: var(--secondary-background-color);
      }
      [data-testid="stMetricLabel"] {font-weight: 600;}
      [data-testid="stCaptionContainer"] {max-width: 78rem;}
      .stDownloadButton button {min-height: 2.75rem;}
      :focus-visible {
        outline: 3px solid #2563eb !important;
        outline-offset: 2px !important;
      }
      @media (max-width: 700px) {
        .block-container {padding-top: 1rem; padding-left: 1rem; padding-right: 1rem;}
        h1 {font-size: 1.85rem !important;}
        h2 {font-size: 1.45rem !important;}
      }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner=False)
def load_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load and validate every processed dataset used by the dashboard."""
    lga = pd.read_csv(DATA / "dashboard_lga_pressure.csv")
    monthly = pd.read_csv(DATA / "dashboard_monthly_approvals.csv")
    annual = pd.read_csv(DATA / "dashboard_annual_approvals.csv")
    ytd = pd.read_csv(DATA / "dashboard_ytd_approvals.csv")

    datasets = {
        "LGA": (lga, REQUIRED_LGA_COLUMNS),
        "monthly approvals": (monthly, REQUIRED_MONTHLY_COLUMNS),
        "annual approvals": (annual, REQUIRED_ANNUAL_COLUMNS),
        "YTD approvals": (ytd, REQUIRED_YTD_COLUMNS),
    }
    for label, (frame, required_columns) in datasets.items():
        if frame.empty:
            raise ValueError(f"{label} dataset is empty.")
        missing = required_columns.difference(frame.columns)
        if missing:
            raise ValueError(
                f"{label} dataset is missing columns: {sorted(missing)}"
            )

    monthly["Month"] = pd.to_datetime(monthly["Month"], errors="raise")
    for column in ["Eligible_for_Score", "Complete_Score"]:
        values = lga[column].astype(str).str.strip().str.lower()
        if not values.isin({"true", "false"}).all():
            raise ValueError(f"LGA dataset has invalid boolean values in {column}.")
        lga[column] = values.eq("true")
    return lga, monthly.sort_values("Month"), annual, ytd


def show_plotly_chart(figure: go.Figure) -> None:
    """Render a responsive chart with consistent accessible presentation."""
    figure.update_layout(
        font={"size": 14},
        margin={"l": 20, "r": 20, "t": 70, "b": 45},
        legend_title_text="",
        hoverlabel={"font_size": 14},
    )
    st.plotly_chart(
        figure,
        width="stretch",
        config=CHART_CONFIG,
    )


def show_no_results(context: str) -> None:
    """Explain an empty filtered view and give a clear recovery action."""
    st.warning(
        f"No scored LGAs are available for {context} with the current filters. "
        "Broaden the pressure categories, rental sample qualities, or LGA search "
        "in the sidebar."
    )


try:
    lga, monthly, annual, ytd = load_data()
    screening = evaluate_rules(lga)
except (OSError, TypeError, ValueError, pd.errors.ParserError) as error:
    st.error(f"Dashboard data could not be loaded: {error}")
    st.code("python -m src.pipeline")
    st.stop()


st.title("South Australian Housing Pressure & Supply Dashboard")
st.caption(
    "A relative LGA decision-support view combining rental affordability proxy, "
    "population growth and dwelling approvals. Data current to April 2026."
)

st.sidebar.header("Filters")
st.sidebar.caption("Filters apply to the three LGA analysis tabs.")
selected_categories = st.sidebar.multiselect(
    "Relative pressure category",
    options=CATEGORY_ORDER[:-1],
    default=CATEGORY_ORDER[:-1],
)
selected_quality = st.sidebar.multiselect(
    "Rental sample quality",
    options=sorted(lga["Sample_Quality"].dropna().unique()),
    default=sorted(lga["Sample_Quality"].dropna().unique()),
)
search_text = st.sidebar.text_input("Find an LGA", placeholder="e.g. Playford")
include_unscored = st.sidebar.checkbox("Include areas not eligible for scoring", value=False)

quality_match = (
    lga["Sample_Quality"].isin(selected_quality) | lga["Sample_Quality"].isna()
)
filtered = lga[
    lga["Complete_Score"]
    & lga["Housing_Pressure_Category"].isin(selected_categories)
    & quality_match
].copy()
if include_unscored:
    filtered = pd.concat(
        [filtered, lga[~lga["Complete_Score"] & quality_match]],
        ignore_index=True,
    ).drop_duplicates(subset="LGA_Name")
if search_text:
    filtered = filtered[
        filtered["LGA_Name"].str.contains(search_text, case=False, na=False)
    ]

st.sidebar.divider()
st.sidebar.metric("Areas shown", f"{len(filtered)} of {len(lga)}")
st.sidebar.caption(
    "Only LGAs with at least 10 published quarterly rental bonds and complete "
    "inputs receive a pressure score."
)

tabs = st.tabs(
    [
        "Executive summary",
        "LGA pressure",
        "Rental affordability",
        "Supply & demand",
        "State pipeline",
        "Methodology & quality",
        "Decision Explorer",
    ]
)


with tabs[0]:
    scored = lga[lga["Complete_Score"]]
    latest = monthly.iloc[-1]
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("LGAs scored", f"{len(scored)} of {len(lga)}")
    col2.metric(
        "Median rent-to-income proxy",
        f"{scored['Rent_to_Income_Proxy_Pct'].median():.1f}%",
        help="Quarterly median weekly rent divided by 2021 Census median weekly household income.",
    )
    col3.metric(
        "Median approvals per 1,000",
        f"{scored['Approvals_per_1000'].median():.1f}",
        help="2024–25 dwelling approvals divided by June 2025 population.",
    )
    col4.metric(
        f"State approvals — {latest['Month'].strftime('%b %Y')}",
        f"{latest['Dwelling_Approvals']:,.0f}",
        help="ABS original series; approvals are permits, not completed homes.",
    )

    st.info(
        "This version compares demand and supply at one geography: Local Government "
        "Area. The index is a relative prioritisation tool, not a forecast and not "
        "a direct measure of household financial stress."
    )

    chart_data = scored.nlargest(15, "Housing_Pressure_Index").sort_values(
        "Housing_Pressure_Index"
    )
    fig = px.bar(
        chart_data,
        x="Housing_Pressure_Index",
        y="LGA_Name",
        color="Housing_Pressure_Category",
        color_discrete_map=CATEGORY_COLOURS,
        category_orders={"Housing_Pressure_Category": CATEGORY_ORDER},
        orientation="h",
        title="Highest relative housing pressure index",
        labels={
            "Housing_Pressure_Index": "Relative pressure index (0–100)",
            "LGA_Name": "LGA",
        },
        hover_data={
            "Rent_to_Income_Proxy_Pct": ":.1f",
            "Population_Growth_Pct": ":.1f",
            "Approvals_per_1000": ":.2f",
            "Sample_Quality": True,
        },
    )
    fig.update_layout(showlegend=False, height=530)
    fig.update_xaxes(range=[0, 100], ticksuffix="")
    show_plotly_chart(fig)
    with st.expander("View the ranked values behind this chart"):
        st.dataframe(
            chart_data[
                [
                    "LGA_Name",
                    "Housing_Pressure_Index",
                    "Housing_Pressure_Category",
                    "Rent_to_Income_Proxy_Pct",
                    "Population_Growth_Pct",
                    "Approvals_per_1000",
                ]
            ].sort_values("Housing_Pressure_Index", ascending=False),
            width="stretch",
            hide_index=True,
            column_config={
                "LGA_Name": "LGA",
                "Housing_Pressure_Index": st.column_config.NumberColumn(
                    "Pressure index", format="%.1f"
                ),
                "Housing_Pressure_Category": "Category",
                "Rent_to_Income_Proxy_Pct": st.column_config.NumberColumn(
                    "Rent/income proxy", format="%.1f%%"
                ),
                "Population_Growth_Pct": st.column_config.NumberColumn(
                    "Population growth", format="%.1f%%"
                ),
                "Approvals_per_1000": st.column_config.NumberColumn(
                    "Approvals/1,000", format="%.2f"
                ),
            },
        )

    st.subheader("How to read the result")
    c1, c2, c3 = st.columns(3)
    c1.markdown(
        "**Affordability pressure — 50%**  \nHigher current rent relative to the "
        "LGA's 2021 Census household income increases pressure."
    )
    c2.markdown(
        "**Demand pressure — 25%**  \nHigher 2024–25 population growth increases pressure."
    )
    c3.markdown(
        "**Supply gap — 25%**  \nFewer 2024–25 approvals per 1,000 residents increases pressure."
    )


with tabs[1]:
    st.header("LGA pressure comparison")
    if filtered.empty:
        show_no_results("the pressure comparison")
    else:
        plot_data = filtered[filtered["Complete_Score"]].copy()
        if plot_data.empty:
            show_no_results("the pressure comparison")
        else:
            fig = px.scatter(
                plot_data,
                x="Approvals_per_1000",
                y="Rent_to_Income_Proxy_Pct",
                size="Population_2025",
                color="Housing_Pressure_Category",
                color_discrete_map=CATEGORY_COLOURS,
                category_orders={"Housing_Pressure_Category": CATEGORY_ORDER},
                hover_name="LGA_Name",
                hover_data={
                    "Housing_Pressure_Index": ":.1f",
                    "Population_Growth_Pct": ":.1f",
                    "Total_Median": ":$,.0f",
                    "Total_Count": ":,.0f",
                    "Sample_Quality": True,
                    "Population_2025": ":,.0f",
                },
                title="Rental-cost proxy versus dwelling approvals",
                labels={
                    "Approvals_per_1000": "2024–25 approvals per 1,000 residents",
                    "Rent_to_Income_Proxy_Pct": "Rent-to-income proxy (%)",
                    "Housing_Pressure_Category": "Pressure category",
                    "Housing_Pressure_Index": "Pressure index",
                    "Population_Growth_Pct": "Population growth (%)",
                    "Total_Median": "Median weekly rent",
                    "Total_Count": "Published rental bonds",
                    "Sample_Quality": "Sample quality",
                    "Population_2025": "June 2025 population",
                },
            )
            fig.add_hline(
                y=30,
                line_dash="dot",
                line_color="#475569",
                annotation_text="30% reference only",
            )
            fig.update_layout(height=600)
            fig.update_xaxes(rangemode="tozero")
            fig.update_yaxes(rangemode="tozero", ticksuffix="%")
            show_plotly_chart(fig)
            st.caption(
                "Bubble size represents June 2025 population. The 30% line is "
                "contextual: the income denominator is the 2021 Census median and "
                "is not a current household-level rental-stress measure."
            )

    if not filtered.empty:
        display_columns = [
            "LGA_Name",
            "Housing_Pressure_Index",
            "Housing_Pressure_Category",
            "Rent_to_Income_Proxy_Pct",
            "Population_Growth_Pct",
            "Approvals_per_1000",
            "Total_Count",
            "Sample_Quality",
        ]
        st.dataframe(
            filtered[display_columns].sort_values(
                "Housing_Pressure_Index", ascending=False
            ),
            width="stretch",
            hide_index=True,
            column_config={
                "LGA_Name": "LGA",
                "Housing_Pressure_Index": st.column_config.NumberColumn(
                    "Pressure index", format="%.1f"
                ),
                "Rent_to_Income_Proxy_Pct": st.column_config.NumberColumn(
                    "Rent/income proxy", format="%.1f%%"
                ),
                "Population_Growth_Pct": st.column_config.NumberColumn(
                    "Population growth", format="%.1f%%"
                ),
                "Approvals_per_1000": st.column_config.NumberColumn(
                    "Approvals/1,000", format="%.2f"
                ),
                "Total_Count": st.column_config.NumberColumn(
                    "Published bonds", format="%d"
                ),
                "Sample_Quality": "Sample quality",
            },
        )

    profile_options = sorted(
        filtered.loc[filtered["Complete_Score"], "LGA_Name"].tolist()
    )
    if profile_options:
        st.subheader("LGA profile and index drivers")
        profile_name = st.selectbox(
            "Choose a scored LGA",
            profile_options,
            key="pressure_profile_lga",
        )
        profile = lga.loc[lga["LGA_Name"].eq(profile_name)].iloc[0]
        p1, p2, p3, p4 = st.columns(4)
        p1.metric(
            f"Pressure index — {profile['Housing_Pressure_Category']}",
            f"{profile['Housing_Pressure_Index']:.1f}",
        )
        p2.metric(
            "Rent/income proxy",
            f"{profile['Rent_to_Income_Proxy_Pct']:.1f}%",
            help="December-quarter 2025 median rent divided by 2021 "
            "Census median household income.",
        )
        p3.metric(
            "Population growth",
            f"{profile['Population_Growth_Pct']:.1f}%",
            help="ABS estimated resident population growth during 2024–25.",
        )
        p4.metric(
            "Approvals per 1,000",
            f"{profile['Approvals_per_1000']:.2f}",
            help="2024–25 dwelling approvals per 1,000 June 2025 residents.",
        )

        component_data = pd.DataFrame(
            {
                "Component": [
                    "Affordability pressure (50%)",
                    "Demand pressure (25%)",
                    "Supply gap (25%)",
                ],
                "Percentile score": [
                    profile["Affordability_Pressure_Score"],
                    profile["Demand_Pressure_Score"],
                    profile["Supply_Gap_Score"],
                ],
            }
        )
        component_fig = px.bar(
            component_data,
            x="Percentile score",
            y="Component",
            orientation="h",
            text_auto=".1f",
            title=f"What drives {profile_name}'s relative index?",
            labels={"Percentile score": "Relative percentile score (0–100)"},
        )
        component_fig.update_traces(marker_color="#2563EB", textposition="outside")
        component_fig.update_xaxes(range=[0, 105])
        component_fig.update_layout(height=330, showlegend=False)
        show_plotly_chart(component_fig)
        st.caption(
            f"Rental sample: {profile['Sample_Quality']} "
            f"({profile['Total_Count']:,.0f} published bonds). Component scores "
            "are relative percentiles among eligible areas, not independent "
            "measures of need or infrastructure sufficiency."
        )


with tabs[2]:
    st.header("Rental affordability proxy")
    st.warning(
        "This is a screening proxy, not a current affordability rate. It combines "
        "December-quarter 2025 rents with 2021 Census median household income."
    )
    eligible = filtered[filtered["Complete_Score"]].nlargest(
        20, "Rent_to_Income_Proxy_Pct"
    )
    if eligible.empty:
        show_no_results("the rental affordability comparison")
    else:
        fig = px.bar(
            eligible.sort_values("Rent_to_Income_Proxy_Pct"),
            x="Rent_to_Income_Proxy_Pct",
            y="LGA_Name",
            color="Sample_Quality",
            orientation="h",
            title="Highest median-rent-to-household-income proxies",
            labels={
                "Rent_to_Income_Proxy_Pct": "Rent-to-income proxy (%)",
                "LGA_Name": "LGA",
                "Sample_Quality": "Rental sample quality",
                "Total_Median": "Median weekly rent",
                "Median_Weekly_Household_Income_2021": (
                    "2021 median weekly household income"
                ),
                "Total_Count": "Published rental bonds",
            },
            hover_data={
                "Total_Median": ":$,.0f",
                "Median_Weekly_Household_Income_2021": ":$,.0f",
                "Total_Count": ":,.0f",
            },
        )
        fig.add_vline(
            x=30,
            line_dash="dot",
            line_color="#475569",
            annotation_text="30% reference only",
        )
        fig.update_layout(height=650)
        fig.update_xaxes(rangemode="tozero", ticksuffix="%")
        show_plotly_chart(fig)

    st.subheader("House and unit rental context")
    st.caption(
        "Type-specific proxies are shown only where both house and unit samples "
        "have at least 10 published bonds. They reuse the same 2021 household-income "
        "denominator and are contextual; they do not change the pressure index."
    )
    type_context = filtered[
        filtered["Complete_Score"]
        & filtered["House_Total_Count"].ge(10)
        & filtered["Unit_Total_Count"].ge(10)
        & filtered["House_Rent_to_Income_Proxy_Pct"].notna()
        & filtered["Unit_Rent_to_Income_Proxy_Pct"].notna()
    ].nlargest(15, "House_Unit_Rent_Gap")
    if type_context.empty:
        st.info(
            "No filtered LGAs have publishable house and unit samples for this "
            "comparison."
        )
    else:
        type_long = type_context[
            [
                "LGA_Name",
                "House_Rent_to_Income_Proxy_Pct",
                "Unit_Rent_to_Income_Proxy_Pct",
            ]
        ].melt(
            id_vars="LGA_Name",
            var_name="Dwelling type",
            value_name="Rent-to-income proxy (%)",
        )
        type_long["Dwelling type"] = type_long["Dwelling type"].map(
            {
                "House_Rent_to_Income_Proxy_Pct": "House",
                "Unit_Rent_to_Income_Proxy_Pct": "Unit",
            }
        )
        type_fig = px.bar(
            type_long,
            x="Rent-to-income proxy (%)",
            y="LGA_Name",
            color="Dwelling type",
            barmode="group",
            orientation="h",
            title="Type-specific rent-to-income screening proxies",
            labels={"LGA_Name": "LGA"},
            color_discrete_map={"House": "#2563EB", "Unit": "#0F766E"},
        )
        type_fig.update_xaxes(rangemode="tozero", ticksuffix="%")
        type_fig.update_layout(
            height=max(430, 30 * len(type_context) + 170),
            yaxis={"categoryorder": "total ascending"},
        )
        show_plotly_chart(type_fig)
        with st.expander("View type-specific rent values and sample counts"):
            st.dataframe(
                type_context[
                    [
                        "LGA_Name",
                        "House_Total_Median",
                        "House_Total_Count",
                        "Unit_Total_Median",
                        "Unit_Total_Count",
                        "House_Unit_Rent_Gap",
                        "House_Unit_Rent_Premium_Pct",
                    ]
                ].sort_values("House_Unit_Rent_Gap", ascending=False),
                width="stretch",
                hide_index=True,
                column_config={
                    "LGA_Name": "LGA",
                    "House_Total_Median": st.column_config.NumberColumn(
                        "House median", format="$%d"
                    ),
                    "House_Total_Count": st.column_config.NumberColumn(
                        "House bonds", format="%d"
                    ),
                    "Unit_Total_Median": st.column_config.NumberColumn(
                        "Unit median", format="$%d"
                    ),
                    "Unit_Total_Count": st.column_config.NumberColumn(
                        "Unit bonds", format="%d"
                    ),
                    "House_Unit_Rent_Gap": st.column_config.NumberColumn(
                        "House–unit gap", format="$%d"
                    ),
                    "House_Unit_Rent_Premium_Pct": st.column_config.NumberColumn(
                        "House premium", format="%.1f%%"
                    ),
                },
            )

    excluded = lga[~lga["Eligible_for_Score"]][
        ["LGA_Name", "Total_Median", "Total_Count", "Sample_Quality"]
    ]
    with st.expander(f"Areas excluded by the sample rule ({len(excluded)})"):
        st.caption(
            "These areas have fewer than 10 published quarterly rental bonds. "
            "They are shown for transparency and are not included in the index."
        )
        st.dataframe(
            excluded,
            width="stretch",
            hide_index=True,
            column_config={
                "LGA_Name": "LGA",
                "Total_Median": st.column_config.NumberColumn(
                    "Median weekly rent", format="$%d"
                ),
                "Total_Count": st.column_config.NumberColumn(
                    "Published bonds", format="%d"
                ),
                "Sample_Quality": "Sample quality",
            },
        )


with tabs[3]:
    st.header("Local supply and demand")
    supply_data = filtered[filtered["Complete_Score"]].copy()
    if supply_data.empty:
        show_no_results("the local supply and demand comparison")
    else:
        scored_reference = lga[lga["Complete_Score"]]
        growth_reference = scored_reference["Population_Growth_Pct"].median()
        approval_reference = scored_reference["Approvals_per_1000"].median()
        fig = px.scatter(
            supply_data,
            x="Population_Growth_Pct",
            y="Approvals_per_1000",
            color="Housing_Pressure_Category",
            color_discrete_map=CATEGORY_COLOURS,
            category_orders={"Housing_Pressure_Category": CATEGORY_ORDER},
            size="Population_2025",
            hover_name="LGA_Name",
            hover_data={
                "Approvals_2024_25": ":,.0f",
                "Approvals_2025_26_FYTD": ":,.0f",
                "Population_2025": ":,.0f",
            },
            title="Population growth versus approved supply",
            labels={
                "Population_Growth_Pct": "Population growth, 2024–25 (%)",
                "Approvals_per_1000": "2024–25 approvals per 1,000 residents",
                "Housing_Pressure_Category": "Pressure category",
                "Approvals_2024_25": "2024–25 approvals",
                "Approvals_2025_26_FYTD": "2025–26 approvals (FYTD)",
                "Population_2025": "June 2025 population",
            },
        )
        fig.add_vline(
            x=growth_reference,
            line_dash="dot",
            line_color="#475569",
            annotation_text="Eligible-area median growth",
        )
        fig.add_hline(
            y=approval_reference,
            line_dash="dot",
            line_color="#475569",
            annotation_text="Eligible-area median approvals",
        )
        fig.update_layout(height=600)
        fig.update_xaxes(ticksuffix="%")
        fig.update_yaxes(rangemode="tozero")
        show_plotly_chart(fig)
        st.caption(
            "Bubble size represents June 2025 population. Small-area approvals "
            "are volatile and subject to revision. Dotted lines divide the chart "
            "at medians for all eligible areas: the lower-right quadrant identifies "
            "higher growth alongside a lower approval rate, not a proven shortage. "
            "The index uses a completed financial year rather than comparing a "
            "partial year with a full year."
        )

        st.subheader("Population and approval composition")
        context_name = st.selectbox(
            "Choose an LGA for contextual flows",
            sorted(supply_data["LGA_Name"].tolist()),
            key="supply_context_lga",
        )
        context = lga.loc[lga["LGA_Name"].eq(context_name)].iloc[0]
        s1, s2, s3, s4 = st.columns(4)
        s1.metric(
            "Population change",
            f"{context['Population_Change']:+,.0f}",
            help="Change in estimated resident population during 2024–25.",
        )
        s2.metric(
            "Population density",
            f"{context['Population_Density_2025']:,.1f}/km²",
            help="June 2025 estimated resident population per square kilometre.",
        )
        s3.metric(
            "Other-residential share",
            f"{context['Other_Residential_Approval_Share_Pct']:.1f}%",
            help="Share of 2024–25 dwelling approvals classified as other "
            "residential rather than houses.",
        )
        approvals_per_new_resident = context["Approvals_per_100_New_Residents"]
        s4.metric(
            "Approvals per 100 new residents",
            (
                f"{approvals_per_new_resident:.1f}"
                if pd.notna(approvals_per_new_resident)
                else "Not applicable"
            ),
            help="A descriptive flow ratio shown only for positive population "
            "change. It is not a dwelling-sufficiency benchmark.",
        )

        population_components = pd.DataFrame(
            {
                "Component": [
                    "Natural increase",
                    "Net internal migration",
                    "Net overseas migration",
                ],
                "People": [
                    context["Natural_Increase_2024_25"],
                    context["Net_Internal_Migration_2024_25"],
                    context["Net_Overseas_Migration_2024_25"],
                ],
            }
        )
        approval_components = pd.DataFrame(
            {
                "Component": [
                    "Houses",
                    "Other residential",
                    "Residual source units",
                ],
                "Approved dwellings": [
                    context["House_Approvals_2024_25"],
                    context["Other_Residential_Approvals_2024_25"],
                    context["Residual_Approval_Units_2024_25"],
                ],
            }
        )
        pc1, pc2 = st.columns(2)
        with pc1:
            population_fig = px.bar(
                population_components,
                x="Component",
                y="People",
                title=f"{context_name}: population-change components",
                text_auto=",.0f",
                color="People",
                color_continuous_scale=["#991B1B", "#CBD5E1", "#0F766E"],
                color_continuous_midpoint=0,
            )
            population_fig.update_layout(
                height=430,
                coloraxis_showscale=False,
                showlegend=False,
            )
            population_fig.update_xaxes(tickangle=-20)
            show_plotly_chart(population_fig)
        with pc2:
            approval_fig = px.bar(
                approval_components,
                x="Component",
                y="Approved dwellings",
                title=f"{context_name}: 2024–25 approval composition",
                text_auto=",.0f",
                color="Component",
                color_discrete_map={
                    "Houses": "#2563EB",
                    "Other residential": "#0F766E",
                    "Residual source units": "#64748B",
                },
            )
            approval_fig.update_layout(height=430, showlegend=False)
            approval_fig.update_xaxes(tickangle=-20)
            approval_fig.update_yaxes(rangemode="tozero")
            show_plotly_chart(approval_fig)
        st.caption(
            "Population components are ABS estimates. Approval composition is a "
            "flow of permits, not construction, completions, occupied supply or "
            "evidence that infrastructure can support growth. Residual source "
            "units reconcile the published total where source components differ."
        )
        with st.expander("View the selected LGA context as a table"):
            st.dataframe(
                pd.DataFrame(
                    {
                        "Measure": [
                            "Natural increase",
                            "Net internal migration",
                            "Net overseas migration",
                            "House approvals",
                            "Other-residential approvals",
                            "Residual source units",
                            "Total dwelling approvals",
                        ],
                        "Value": [
                            context["Natural_Increase_2024_25"],
                            context["Net_Internal_Migration_2024_25"],
                            context["Net_Overseas_Migration_2024_25"],
                            context["House_Approvals_2024_25"],
                            context["Other_Residential_Approvals_2024_25"],
                            context["Residual_Approval_Units_2024_25"],
                            context["Approvals_2024_25"],
                        ],
                    }
                ),
                width="stretch",
                hide_index=True,
                column_config={
                    "Measure": "Context measure",
                    "Value": st.column_config.NumberColumn(
                        "People or approved dwellings", format="%d"
                    ),
                },
            )


with tabs[4]:
    st.header("State dwelling approval pipeline")
    st.caption(
        "ABS original series. Building approval is a supply-pipeline indicator, "
        "not evidence that construction started or a dwelling was completed."
    )
    latest = monthly.iloc[-1]
    latest_ytd = ytd.iloc[-1]
    k1, k2, k3, k4 = st.columns(4)
    k1.metric(
        f"{latest_ytd['Comparison_Label']} approvals",
        f"{latest_ytd['YTD_Dwelling_Approvals']:,.0f}",
        (
            f"{latest_ytd['YTD_YoY_Change_Pct']:+.1f}% vs prior year"
            if pd.notna(latest_ytd["YTD_YoY_Change_Pct"])
            else None
        ),
    )
    k2.metric(
        "Rolling 12-month approvals",
        f"{latest['Rolling_12_Month_Total']:,.0f}",
        (
            f"{latest['Rolling_12_Month_YoY_Change_Pct']:+.1f}% year on year"
            if pd.notna(latest["Rolling_12_Month_YoY_Change_Pct"])
            else None
        ),
    )
    k3.metric(
        f"House approvals — {latest['Month'].strftime('%b %Y')}",
        f"{latest['House_Approvals']:,.0f}",
    )
    k4.metric(
        "Non-house share",
        f"{latest['Non_House_Approval_Share_Pct']:.1f}%",
        help="Non-house dwelling approvals as a share of all original-series "
        "approvals in the latest month.",
    )
    st.caption(
        "Changes describe approval flows in the ABS original series. Monthly "
        "values are volatile and revised; they do not measure whether approved "
        "dwellings commence or complete."
    )

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=monthly["Month"],
            y=monthly["Dwelling_Approvals"],
            name="Monthly approvals",
            mode="lines",
            line={"color": "#94A3B8", "width": 1.5},
        )
    )
    fig.add_trace(
        go.Scatter(
            x=monthly["Month"],
            y=monthly["Rolling_3_Month_Avg"],
            name="3-month rolling average",
            mode="lines",
            line={"color": "#0F766E", "width": 3},
        )
    )
    fig.update_layout(
        title="South Australian monthly dwelling approvals",
        xaxis_title="Month",
        yaxis_title="Dwelling approvals",
        height=500,
        hovermode="x unified",
    )
    fig.update_yaxes(rangemode="tozero", tickformat=",")
    show_plotly_chart(fig)

    recent_mix = monthly.tail(12)
    mix_fig = go.Figure()
    mix_fig.add_trace(
        go.Bar(
            x=recent_mix["Month"],
            y=recent_mix["House_Approvals"],
            name="Houses",
            marker_color="#2563EB",
        )
    )
    mix_fig.add_trace(
        go.Bar(
            x=recent_mix["Month"],
            y=recent_mix["Non_House_Approvals"],
            name="Non-house dwellings",
            marker_color="#0F766E",
        )
    )
    mix_fig.update_layout(
        barmode="stack",
        title="Latest 12 months: house and non-house approval mix",
        xaxis_title="Month",
        yaxis_title="Dwelling approvals",
        height=430,
        hovermode="x unified",
    )
    mix_fig.update_yaxes(rangemode="tozero", tickformat=",")
    show_plotly_chart(mix_fig)

    c1, c2 = st.columns(2)
    with c1:
        annual_fig = px.bar(
            annual,
            x="Year_Label",
            y="Dwelling_Approvals",
            color="Period_Status",
            color_discrete_map={
                "Full calendar year": "#2563EB",
                "Year to date": "#F59E0B",
            },
            title="Annual totals with partial period identified",
            labels={"Year_Label": "Period", "Dwelling_Approvals": "Approvals"},
            text_auto=",.0f",
        )
        annual_fig.update_yaxes(rangemode="tozero", tickformat=",")
        annual_fig.update_traces(textposition="outside", cliponaxis=False)
        show_plotly_chart(annual_fig)
    with c2:
        ytd_fig = px.bar(
            ytd,
            x="Year",
            y="YTD_Dwelling_Approvals",
            title=f"Like-for-like {ytd.iloc[-1]['Comparison_Label']} comparison",
            labels={"YTD_Dwelling_Approvals": "Approvals"},
            text_auto=",.0f",
        )
        ytd_fig.update_traces(marker_color="#0F766E")
        ytd_fig.update_yaxes(rangemode="tozero", tickformat=",")
        ytd_fig.update_traces(textposition="outside", cliponaxis=False)
        show_plotly_chart(ytd_fig)
    with st.expander("View recent state pipeline values"):
        st.dataframe(
            recent_mix[
                [
                    "Month",
                    "House_Approvals",
                    "Non_House_Approvals",
                    "Dwelling_Approvals",
                    "Rolling_12_Month_Total",
                    "Rolling_12_Month_YoY_Change_Pct",
                ]
            ].sort_values("Month", ascending=False),
            width="stretch",
            hide_index=True,
            column_config={
                "Month": st.column_config.DateColumn("Month", format="MMM YYYY"),
                "House_Approvals": st.column_config.NumberColumn(
                    "Houses", format="%d"
                ),
                "Non_House_Approvals": st.column_config.NumberColumn(
                    "Non-house", format="%d"
                ),
                "Dwelling_Approvals": st.column_config.NumberColumn(
                    "Total approvals", format="%d"
                ),
                "Rolling_12_Month_Total": st.column_config.NumberColumn(
                    "Rolling 12 months", format="%d"
                ),
                "Rolling_12_Month_YoY_Change_Pct": (
                    st.column_config.NumberColumn(
                        "Rolling-12 change", format="%.1f%%"
                    )
                ),
            },
        )


with tabs[5]:
    st.header("Methodology, limitations and data quality")
    scored_count = int(lga["Complete_Score"].sum())
    low_sample_count = int(
        lga["Sample_Quality"].fillna("").str.contains(
            "suppressed|low", case=False, regex=True
        ).sum()
    )
    q1, q2, q3 = st.columns(3)
    q1.metric(
        "Scored coverage",
        f"{scored_count} of {len(lga)} "
        f"({scored_count / len(lga) * 100:.1f}%)",
    )
    q2.metric(
        "Not scored",
        f"{len(lga) - scored_count}",
        help="Areas without a complete eligible score, primarily because the "
        "published quarterly rental sample is below 10.",
    )
    q3.metric(
        "Suppressed or low rental sample",
        f"{low_sample_count}",
        help="Areas whose sample-quality label identifies suppressed or low "
        "rental evidence.",
    )
    quality_summary = (
        lga["Sample_Quality"]
        .fillna("Not available")
        .value_counts()
        .rename_axis("Rental sample quality")
        .reset_index(name="Local areas")
    )
    with st.expander("View rental sample-quality coverage"):
        st.dataframe(quality_summary, width="stretch", hide_index=True)

    st.subheader("Index calculation")
    st.markdown(
        """
        Each eligible LGA receives percentile scores from 0 to 100:

        1. **Affordability pressure (50%)** — higher rent-to-income proxy.
        2. **Demand pressure (25%)** — higher annual population growth.
        3. **Supply gap (25%)** — lower full-year approvals per 1,000 residents.

        The weighted result is ranked again to create a relative 0–100 index.
        Categories are relative bands: Very High ≥80, High ≥60, Moderate ≥40,
        Low ≥20 and Very Low <20. Areas with fewer than 10 published quarterly
        rental bonds are not scored.
        """
    )

    st.subheader("Known limitations")
    st.markdown(
        """
        - The rental source covers bonds lodged during one quarter, not all existing
          tenancies, asking rents or vacancy rates.
        - Counts of 1–5 are suppressed; published totals are rounded to the nearest five.
        - The income denominator is from the 2021 Census and has not been income-indexed.
        - Approvals are permits and may not become commenced or completed dwellings.
        - Approval and population-flow ratios are context, not evidence that supply
          is sufficient for growth. Small-area approval data are volatile and revised.
        - Infrastructure capacity is not scored. Water, wastewater, schools, transport
          and health require capacity data, not merely distance to facilities.
        """
    )

    st.subheader("Infrastructure readiness status")
    st.info(
        "The title no longer claims infrastructure readiness. A future readiness "
        "module should remain separate until auditable service-capacity and land-release "
        "data are available."
    )

    st.subheader("Authoritative sources")
    st.markdown(
        """
        - [SA Housing Trust Private Rent Report](https://data.sa.gov.au/data/dataset/private-rent-report)
        - [ABS Building Approvals](https://www.abs.gov.au/statistics/industry/building-and-construction/building-approvals-australia/latest-release)
        - [ABS Regional Population 2024–25](https://www.abs.gov.au/statistics/people/population/regional-population/latest-release)
        - [ABS 2021 Census DataPacks](https://www.abs.gov.au/census/find-census-data/datapacks)
        - [AIHW Housing Affordability](https://www.aihw.gov.au/reports/australias-welfare/housing-affordability)
        - [PlanSA Land Supply](https://plan.sa.gov.au/state_snapshot/land_supply)
        """
    )

    st.subheader("Download auditable data")
    d1, d2, d3 = st.columns(3)
    d1.download_button(
        "Download LGA analytical dataset",
        lga.to_csv(index=False).encode("utf-8"),
        file_name="sa_lga_housing_pressure.csv",
        mime="text/csv",
        help="Includes scored and unscored areas plus source-quality fields.",
    )
    d2.download_button(
        "Download state monthly approvals",
        monthly.to_csv(index=False).encode("utf-8"),
        file_name="sa_monthly_dwelling_approvals.csv",
        mime="text/csv",
        help="Includes monthly approvals and the three-month rolling average.",
    )
    d3.download_button(
        "Download comparable state YTD approvals",
        ytd.to_csv(index=False).encode("utf-8"),
        file_name="sa_ytd_dwelling_approvals.csv",
        mime="text/csv",
        help="Includes like-for-like months, prior-year values and YTD change.",
    )
    with st.expander("Preview the full LGA analytical dataset"):
        st.dataframe(lga, width="stretch", hide_index=True)


with tabs[6]:
    st.header("Decision Explorer")
    st.warning(
        "This explorer produces transparent investigation shortlists from fixed "
        "screening rules. It does not recommend policy, development, investment "
        "or resource allocation; it is not a forecast or a housing-shortage model."
    )

    rule_label_to_id = {
        f"{rule.name} — {rule.question}": rule.rule_id for rule in RULES
    }
    selected_rule_label = st.selectbox(
        "Decision question",
        options=list(rule_label_to_id),
        help="Each question uses a versioned fixed rule evaluated against the "
        "full, unfiltered statewide dataset.",
    )
    selected_rule_id = rule_label_to_id[selected_rule_label]
    selected_rule = RULE_BY_ID[selected_rule_id]
    shortlist_size = st.slider(
        "Maximum positive-rule shortlist size",
        min_value=5,
        max_value=15,
        value=10,
        help="Evidence-gap results are always shown in full and alphabetically; "
        "they are never pressure-ranked.",
    )

    st.caption(
        f"Ruleset `{RULESET_ID}` version `{RULESET_VERSION}`. Rule membership "
        "and reference benchmarks were evaluated once from the full statewide "
        "frame and do not change with sidebar filters."
    )
    st.markdown(f"**Exact expression:** `{selected_rule.expression}`")
    st.markdown(
        f"**Permitted interpretation:** {selected_rule.permitted_interpretation}"
    )
    st.markdown(
        "**Full-reference benchmarks:** "
        f"{screening.benchmarks.complete_lga_count} complete scored LGAs; "
        f"population growth median "
        f"{screening.benchmarks.population_growth_median_pct:.1f}%; "
        f"approvals median "
        f"{screening.benchmarks.approvals_per_1000_median:.2f} per 1,000."
    )

    full_rule_matches = deterministic_matched_shortlist(
        screening,
        [selected_rule_id],
    )
    statewide_match_count = len(full_rule_matches)
    sidebar_match_count = int(
        full_rule_matches["LGA_Name"].isin(filtered["LGA_Name"]).sum()
    )
    is_positive_rule = selected_rule_id in POSITIVE_RULE_IDS
    if is_positive_rule:
        visible_matches = full_rule_matches[
            full_rule_matches["LGA_Name"].isin(filtered["LGA_Name"])
        ].copy()
        displayed_matches = visible_matches.head(shortlist_size).copy()
        ordering_note = (
            "Positive matches use the module's deterministic existing-HPI "
            "descending order, with LGA name alphabetical for equal HPI values. "
            "This is display ordering, not a new priority score."
        )
    else:
        visible_matches = full_rule_matches.copy()
        displayed_matches = visible_matches.copy()
        ordering_note = (
            "Evidence gaps are shown alphabetically and are not pressure-ranked. "
            "Sidebar filters and the unscored checkbox do not remove this view."
        )

    category_filter_text = (
        ", ".join(selected_categories) if selected_categories else "none selected"
    )
    quality_filter_text = (
        ", ".join(selected_quality) if selected_quality else "none selected"
    )
    search_filter_text = search_text.strip() if search_text.strip() else "none"
    st.markdown(
        f"- **Statewide rule matches:** {statewide_match_count}\n"
        f"- **Matches after current sidebar filters:** {sidebar_match_count}\n"
        f"- **Sidebar context:** categories: {category_filter_text}; rental "
        f"quality: {quality_filter_text}; search: {search_filter_text}; "
        f"include-unscored toggle: {'on' if include_unscored else 'off'}.\n"
        f"- **Ordering:** {ordering_note}"
    )
    st.caption(
        "Positive screens require a complete score. Unscored areas are excluded "
        "from positive shortlists, not classified as low pressure, and remain "
        "available through the unranked Evidence gaps question."
    )
    if not is_positive_rule:
        st.info(
            "The post-filter count is disclosed for auditability only. All "
            "evidence-gap matches remain visible because an evidence gap must "
            "not be interpreted as low pressure."
        )
    elif statewide_match_count > sidebar_match_count:
        st.info(
            "Some statewide matches are outside the current sidebar filters. "
            "Broaden the sidebar categories, sample qualities or search to see "
            "them; their rule membership and statewide benchmarks do not change."
        )

    st.subheader("Transparent match table")
    if displayed_matches.empty:
        st.warning(
            "The fixed rule has no matches within the current sidebar filters. "
            "The statewide match count above remains unchanged. Broaden the "
            "sidebar filters or choose another question."
        )
    else:
        match_reason_column = f"Rule_{selected_rule_id}_Reason"
        match_table = displayed_matches[
            [
                "LGA_Name",
                "Housing_Pressure_Index",
                "Housing_Pressure_Category",
                "Highest_Index_Component",
                "Rent_to_Income_Proxy_Pct",
                "Population_Growth_Pct",
                "Population_Change",
                "Approvals_per_1000",
                "Approvals_2024_25",
                "Other_Residential_Approval_Share_Pct",
                "Total_Count",
                "Sample_Quality",
                "Matched_Rule_IDs",
                match_reason_column,
                "Pressure_Ranking_Status",
            ]
        ].copy()
        match_table["Matched_Rule_IDs"] = match_table[
            "Matched_Rule_IDs"
        ].map(
            lambda value: ", ".join(
                RULE_BY_ID[rule_id].name
                for rule_id in str(value).split(";")
                if rule_id
            )
        )
        if is_positive_rule:
            match_table.insert(
                0,
                "Display_Order",
                range(1, len(match_table) + 1),
            )
        st.dataframe(
            match_table,
            width="stretch",
            hide_index=True,
            column_config={
                "Display_Order": "Display order",
                "LGA_Name": "LGA",
                "Housing_Pressure_Index": st.column_config.NumberColumn(
                    "Existing HPI", format="%.1f"
                ),
                "Housing_Pressure_Category": "HPI category",
                "Highest_Index_Component": "Largest index component",
                "Rent_to_Income_Proxy_Pct": st.column_config.NumberColumn(
                    "Rent/income proxy", format="%.1f%%"
                ),
                "Population_Growth_Pct": st.column_config.NumberColumn(
                    "Population growth", format="%.1f%%"
                ),
                "Population_Change": st.column_config.NumberColumn(
                    "Population change", format="%d"
                ),
                "Approvals_per_1000": st.column_config.NumberColumn(
                    "Approvals/1,000", format="%.2f"
                ),
                "Approvals_2024_25": st.column_config.NumberColumn(
                    "2024–25 approvals", format="%d"
                ),
                "Other_Residential_Approval_Share_Pct": (
                    st.column_config.NumberColumn(
                        "Other-residential share", format="%.1f%%"
                    )
                ),
                "Total_Count": st.column_config.NumberColumn(
                    "Published bonds", format="%d"
                ),
                "Sample_Quality": "Rental sample quality",
                "Matched_Rule_IDs": "All matched screens",
                match_reason_column: "Why this rule matched",
                "Pressure_Ranking_Status": "Ranking status",
            },
        )
        st.caption(
            "Rows can match more than one fixed screen. Raw values are shown as "
            "evidence; they are not combined into another score."
        )

    st.subheader("Compare matched areas and contextual comparators")
    matched_names = displayed_matches["LGA_Name"].tolist()
    all_comparison_names = matched_names + [
        name
        for name in sorted(screening.frame["LGA_Name"].tolist())
        if name not in matched_names
    ]
    default_comparison = matched_names[:2]
    if len(default_comparison) < 2:
        default_comparison.extend(
            name
            for name in all_comparison_names
            if name not in default_comparison
        )
        default_comparison = default_comparison[:2]
    comparison_names = st.multiselect(
        "Select 2–5 LGAs in the order they should appear",
        options=all_comparison_names,
        default=default_comparison,
        max_selections=5,
        help="The first options are currently displayed matches; all other "
        "areas remain available as contextual comparators.",
    )

    if len(comparison_names) < 2:
        st.info(
            "Select at least two LGAs to show the comparison, evidence panels "
            "and Markdown brief."
        )
    else:
        comparison = select_comparison_lgas(screening, comparison_names)
        scored_comparison = comparison[comparison["Complete_Score"]].copy()
        if scored_comparison.empty:
            st.info(
                "None of the selected areas has a complete pressure score, so "
                "no component chart is shown. Their raw evidence remains below."
            )
        else:
            component_long = scored_comparison[
                [
                    "LGA_Name",
                    "Affordability_Pressure_Score",
                    "Demand_Pressure_Score",
                    "Supply_Gap_Score",
                ]
            ].melt(
                id_vars="LGA_Name",
                var_name="Index component",
                value_name="Percentile score",
            )
            component_long["Index component"] = component_long[
                "Index component"
            ].map(
                {
                    "Affordability_Pressure_Score": "Affordability",
                    "Demand_Pressure_Score": "Population growth",
                    "Supply_Gap_Score": "Lower approval rate",
                }
            )
            component_fig = px.bar(
                component_long,
                x="Percentile score",
                y="LGA_Name",
                color="Index component",
                barmode="group",
                orientation="h",
                text_auto=".1f",
                title="Existing index components for scored selections",
                labels={"LGA_Name": "LGA"},
                color_discrete_map={
                    "Affordability": "#991B1B",
                    "Population growth": "#2563EB",
                    "Lower approval rate": "#0F766E",
                },
            )
            component_fig.update_xaxes(range=[0, 105])
            component_fig.update_layout(
                height=max(360, 85 * len(scored_comparison) + 170)
            )
            show_plotly_chart(component_fig)
            st.caption(
                "Direct labels and the raw-evidence table provide non-colour "
                "equivalents. Components are existing eligible-area percentiles."
            )

        comparison_table = comparison[
            [
                "LGA_Name",
                "Pressure_Ranking_Status",
                "Housing_Pressure_Index",
                "Housing_Pressure_Category",
                "Affordability_Pressure_Score",
                "Demand_Pressure_Score",
                "Supply_Gap_Score",
                "Total_Median",
                "Median_Weekly_Household_Income_2021",
                "Rent_to_Income_Proxy_Pct",
                "Population_2025",
                "Population_Growth_Pct",
                "Population_Change",
                "Approvals_per_1000",
                "Approvals_2024_25",
                "Other_Residential_Approval_Share_Pct",
                "Total_Count",
                "Sample_Quality",
            ]
        ].copy()
        comparison_table.insert(
            0,
            "Selection_Order",
            range(1, len(comparison_table) + 1),
        )
        st.dataframe(
            comparison_table,
            width="stretch",
            hide_index=True,
            column_config={
                "Selection_Order": "Selection order",
                "LGA_Name": "LGA",
                "Pressure_Ranking_Status": "Ranking status",
                "Housing_Pressure_Index": st.column_config.NumberColumn(
                    "Existing HPI", format="%.1f"
                ),
                "Housing_Pressure_Category": "HPI category",
                "Affordability_Pressure_Score": st.column_config.NumberColumn(
                    "Affordability component", format="%.1f"
                ),
                "Demand_Pressure_Score": st.column_config.NumberColumn(
                    "Growth component", format="%.1f"
                ),
                "Supply_Gap_Score": st.column_config.NumberColumn(
                    "Approval-rate component", format="%.1f"
                ),
                "Total_Median": st.column_config.NumberColumn(
                    "Median weekly rent", format="$%d"
                ),
                "Median_Weekly_Household_Income_2021": (
                    st.column_config.NumberColumn(
                        "2021 weekly household income", format="$%d"
                    )
                ),
                "Rent_to_Income_Proxy_Pct": st.column_config.NumberColumn(
                    "Rent/income proxy", format="%.1f%%"
                ),
                "Population_2025": st.column_config.NumberColumn(
                    "June 2025 population", format="%d"
                ),
                "Population_Growth_Pct": st.column_config.NumberColumn(
                    "Population growth", format="%.1f%%"
                ),
                "Population_Change": st.column_config.NumberColumn(
                    "Population change", format="%d"
                ),
                "Approvals_per_1000": st.column_config.NumberColumn(
                    "Approvals/1,000", format="%.2f"
                ),
                "Approvals_2024_25": st.column_config.NumberColumn(
                    "2024–25 approvals", format="%d"
                ),
                "Other_Residential_Approval_Share_Pct": (
                    st.column_config.NumberColumn(
                        "Other-residential share", format="%.1f%%"
                    )
                ),
                "Total_Count": st.column_config.NumberColumn(
                    "Published bonds", format="%d"
                ),
                "Sample_Quality": "Rental sample quality",
            },
        )

        st.markdown("#### Evidence panels")
        for _, area in comparison.iterrows():
            with st.expander(str(area["LGA_Name"])):
                st.markdown(
                    f"- **Ranking status:** {area['Pressure_Ranking_Status']}.\n"
                    f"- **Selected screen:** "
                    f"{area[f'Rule_{selected_rule_id}_Reason']}\n"
                    f"- **Largest existing index component:** "
                    f"{area['Highest_Index_Component']}"
                    + (
                        f" ({area['Highest_Component_Score']:.1f}).\n"
                        if pd.notna(area["Highest_Component_Score"])
                        else ".\n"
                    )
                    + f"- **Rental evidence:** {area['Sample_Quality']}; "
                    f"{area['Total_Count']:,.0f} published bonds where available.\n"
                    f"- **Observed context:** population growth "
                    f"{area['Population_Growth_Pct']:.1f}%; "
                    f"{area['Approvals_per_1000']:.2f} approvals per 1,000 "
                    "residents. Approvals are permits, not completed supply."
                )
                if area["Evidence_Gap_Reason"]:
                    st.warning(f"Evidence gap: {area['Evidence_Gap_Reason']}")

    st.subheader("Auditable downloads")
    auditable_export = build_auditable_export(screening)
    export_names = displayed_matches["LGA_Name"].tolist()
    shortlist_export = auditable_export[
        auditable_export["Rule_ID"].eq(selected_rule_id)
        & auditable_export["Matched"]
        & auditable_export["LGA_Name"].isin(export_names)
    ].copy()
    version_slug = RULESET_VERSION.replace(".", "-")
    st.download_button(
        "Download versioned shortlist CSV",
        shortlist_export.to_csv(index=False).encode("utf-8"),
        file_name=(
            f"sa_decision_shortlist_{selected_rule_id}_v{version_slug}.csv"
        ),
        mime="text/csv",
        disabled=shortlist_export.empty,
        help="Exports the displayed matches from the module's full auditable "
        "one-row-per-LGA-and-rule dataset.",
    )
    if len(comparison_names) >= 2:
        markdown_brief = build_markdown_decision_brief(
            screening,
            comparison_names,
        )
        st.download_button(
            "Download versioned Markdown comparison brief",
            markdown_brief.encode("utf-8"),
            file_name=f"sa_decision_brief_v{version_slug}.md",
            mime="text/markdown",
            help="Generated by the decision-rules module with fixed source "
            "periods, rule results and limitations.",
        )
    st.caption(
        "The rent-to-income evidence combines December-quarter 2025 rents with "
        "2021 Census household income. Approvals are original-series permits, "
        "are volatile and revised, and do not demonstrate commencement, "
        "completion, housing sufficiency or infrastructure capacity."
    )
