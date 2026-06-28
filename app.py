"""Streamlit application for the SA Housing Pressure & Supply Dashboard."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


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
    "Total_Count",
    "Sample_Quality",
    "Rent_to_Income_Proxy_Pct",
    "Population_2025",
    "Population_Growth_Pct",
    "Approvals_2024_25",
    "Approvals_per_1000",
    "Housing_Pressure_Index",
    "Housing_Pressure_Category",
    "Eligible_for_Score",
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
    lga = pd.read_csv(DATA / "dashboard_lga_pressure.csv")
    monthly = pd.read_csv(DATA / "dashboard_monthly_approvals.csv")
    annual = pd.read_csv(DATA / "dashboard_annual_approvals.csv")
    ytd = pd.read_csv(DATA / "dashboard_ytd_approvals.csv")
    missing = REQUIRED_LGA_COLUMNS.difference(lga.columns)
    if missing:
        raise ValueError(f"LGA dataset is missing columns: {sorted(missing)}")
    monthly["Month"] = pd.to_datetime(monthly["Month"])
    for column in ["Eligible_for_Score", "Complete_Score"]:
        if column in lga:
            lga[column] = lga[column].astype(str).str.lower().eq("true")
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
except (FileNotFoundError, ValueError) as error:
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
    options=CATEGORY_ORDER,
    default=CATEGORY_ORDER[:-1],
)
selected_quality = st.sidebar.multiselect(
    "Rental sample quality",
    options=sorted(lga["Sample_Quality"].dropna().unique()),
    default=sorted(lga["Sample_Quality"].dropna().unique()),
)
search_text = st.sidebar.text_input("Find an LGA", placeholder="e.g. Playford")
include_unscored = st.sidebar.checkbox("Include areas not eligible for scoring", value=False)

filtered = lga[
    lga["Housing_Pressure_Category"].isin(selected_categories)
    & lga["Sample_Quality"].isin(selected_quality)
].copy()
if include_unscored:
    quality_match = lga["Sample_Quality"].isin(selected_quality) | lga["Sample_Quality"].isna()
    filtered = lga[
        (lga["Housing_Pressure_Category"].isin(selected_categories) | ~lga["Complete_Score"])
        & quality_match
    ].copy()
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
        fig.update_layout(height=600)
        fig.update_xaxes(ticksuffix="%")
        fig.update_yaxes(rangemode="tozero")
        show_plotly_chart(fig)
        st.caption(
            "Bubble size represents June 2025 population. Small-area approvals "
            "are volatile and subject to revision. The index uses a completed "
            "financial year rather than comparing a partial year with a full year."
        )


with tabs[4]:
    st.header("State dwelling approval pipeline")
    st.caption(
        "ABS original series. Building approval is a supply-pipeline indicator, "
        "not evidence that construction started or a dwelling was completed."
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


with tabs[5]:
    st.header("Methodology, limitations and data quality")
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
        - Small-area approval data are volatile and revised by the ABS.
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
    d1, d2 = st.columns(2)
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
    with st.expander("Preview the full LGA analytical dataset"):
        st.dataframe(lga, width="stretch", hide_index=True)
