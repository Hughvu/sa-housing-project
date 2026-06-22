import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(
    page_title="SA Housing Dashboard",
    page_icon="🏘️",
    layout="wide"
)

st.title("SA Housing Supply & Infrastructure Readiness Dashboard")

st.markdown("""
This dashboard is a Business Analyst portfolio project that explores housing pressure
and housing supply indicators in South Australia using public datasets.
""")

# Load data
rent = pd.read_csv("data/processed/dashboard_housing_pressure_score.csv")
monthly_approvals = pd.read_csv("data/processed/dashboard_monthly_approvals.csv")
annual_approvals = pd.read_csv("data/processed/dashboard_annual_approvals.csv")

monthly_approvals["Month"] = pd.to_datetime(monthly_approvals["Month"])

# Sidebar filters
st.sidebar.header("Filters")

selected_category = st.sidebar.multiselect(
    "Housing pressure category",
    options=sorted(rent["Housing_Pressure_Category"].unique()),
    default=sorted(rent["Housing_Pressure_Category"].unique())
)

filtered_rent = rent[rent["Housing_Pressure_Category"].isin(selected_category)]

tabs = st.tabs([
    "Executive Summary",
    "Rental Pressure",
    "Housing Pressure Score",
    "Housing Supply",
    "BA Interpretation",
    "Data Tables"
])

# -----------------------------
# Executive Summary
# -----------------------------
with tabs[0]:
    st.header("Executive Summary")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Suburbs analysed", len(filtered_rent))
    col2.metric("Highest median rent", f"${filtered_rent['Total_Median'].max():,.0f}")
    col3.metric("Average median rent", f"${filtered_rent['Total_Median'].mean():,.0f}")
    col4.metric("Latest monthly approvals", f"{monthly_approvals['Dwelling_Approvals'].iloc[-1]:,.0f}")

    st.subheader("Project purpose")

    st.info("""
    This dashboard supports early identification of housing pressure by combining
    rental market indicators and dwelling approval trends. The current version uses
    suburb-level rental data and state-level building approval data.
    """)

    st.subheader("Top 10 suburbs by median rent")

    top_rent = filtered_rent.sort_values("Total_Median", ascending=False).head(10)

    fig = px.bar(
        top_rent,
        x="Total_Median",
        y="Suburb",
        orientation="h",
        title="Top 10 suburbs by total median rent",
        labels={
            "Total_Median": "Median rent ($)",
            "Suburb": "Suburb"
        },
        hover_data=["Housing_Pressure_Score", "Housing_Pressure_Category"]
    )

    fig.update_layout(yaxis={"categoryorder": "total ascending"})

    st.plotly_chart(fig, use_container_width=True)


# -----------------------------
# Rental Pressure
# -----------------------------
with tabs[1]:
    st.header("Rental Pressure")

    st.markdown("""
    Rental pressure is measured using total median rent from the December 2025
    Private Rent Report.
    """)

    top_20_rent = filtered_rent.sort_values("Total_Median", ascending=False).head(20)

    fig = px.bar(
        top_20_rent,
        x="Total_Median",
        y="Suburb",
        color="Housing_Pressure_Category",
        orientation="h",
        title="Top 20 suburbs by total median rent",
        labels={
            "Total_Median": "Median rent ($)",
            "Suburb": "Suburb",
            "Housing_Pressure_Category": "Housing pressure"
        },
        hover_data=["Housing_Pressure_Score"]
    )

    fig.update_layout(yaxis={"categoryorder": "total ascending"})

    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Housing pressure category count")

    category_count = (
        filtered_rent
        .groupby("Housing_Pressure_Category", as_index=False)
        .size()
        .rename(columns={"size": "Suburb_Count"})
    )

    fig2 = px.bar(
        category_count,
        x="Housing_Pressure_Category",
        y="Suburb_Count",
        title="Number of suburbs by housing pressure category",
        labels={
            "Housing_Pressure_Category": "Housing pressure category",
            "Suburb_Count": "Number of suburbs"
        }
    )

    st.plotly_chart(fig2, use_container_width=True)


# -----------------------------
# Housing Pressure Score
# -----------------------------
with tabs[2]:
    st.header("Housing Pressure Score")

    st.markdown("""
    The Housing Pressure Score is a prototype scoring model that ranks suburbs
    based on total median rent. A higher score indicates stronger rental pressure.

    In this version, the score is based on rent only. Future versions should include
    population growth and LGA-level building approvals to create a more complete
    demand-versus-supply score.
    """)

    st.subheader("Top 20 suburbs by median rent and pressure category")

    top_score = filtered_rent.sort_values(
        "Total_Median",
        ascending=False
    ).head(20)

    fig_score = px.bar(
        top_score,
        x="Total_Median",
        y="Suburb",
        color="Housing_Pressure_Category",
        orientation="h",
        title="Top 20 suburbs by median rent and Housing Pressure Category",
        labels={
            "Total_Median": "Median rent ($)",
            "Suburb": "Suburb",
            "Housing_Pressure_Category": "Housing pressure category"
        },
        hover_data=["Housing_Pressure_Score", "House_Total_Median", "Unit_Total_Median", "Total_Count"]
    )

    fig_score.update_layout(yaxis={"categoryorder": "total ascending"})

    st.plotly_chart(fig_score, use_container_width=True)

    st.subheader("Housing pressure score distribution")

    score_count = (
        filtered_rent
        .groupby(["Housing_Pressure_Score", "Housing_Pressure_Category"], as_index=False)
        .size()
        .rename(columns={"size": "Suburb_Count"})
        .sort_values("Housing_Pressure_Score", ascending=False)
    )

    fig_score_count = px.bar(
        score_count,
        x="Housing_Pressure_Category",
        y="Suburb_Count",
        color="Housing_Pressure_Category",
        title="Number of suburbs by Housing Pressure Score",
        labels={
            "Housing_Pressure_Category": "Housing pressure category",
            "Suburb_Count": "Number of suburbs"
        },
        hover_data=["Housing_Pressure_Score"]
    )

    st.plotly_chart(fig_score_count, use_container_width=True)

    st.subheader("Scoring logic")

    scoring_table = pd.DataFrame({
        "Score": [5, 4, 3, 2, 1],
        "Category": ["Very High", "High", "Medium", "Low", "Very Low"],
        "Total median rent range": [
            "$850 and above",
            "$750 to $849",
            "$650 to $749",
            "$550 to $649",
            "Below $550"
        ],
        "Interpretation": [
            "Very high rental pressure",
            "High rental pressure",
            "Moderate rental pressure",
            "Low rental pressure",
            "Very low rental pressure"
        ]
    })

    st.dataframe(scoring_table, use_container_width=True)


# -----------------------------
# Housing Supply
# -----------------------------
with tabs[3]:
    st.header("Housing Supply")

    st.markdown("""
    Housing supply activity is represented by monthly dwelling approvals in South Australia.
    Building approvals are treated as a supply pipeline indicator, not completed dwellings.
    """)

    fig3 = px.line(
        monthly_approvals,
        x="Month",
        y=["Dwelling_Approvals", "Rolling_3_Month_Avg"],
        title="Monthly dwelling approvals and 3-month rolling average",
        labels={
            "Month": "Month",
            "value": "Dwelling approvals",
            "variable": "Measure"
        }
    )

    st.plotly_chart(fig3, use_container_width=True)

    fig4 = px.bar(
        annual_approvals,
        x="Year",
        y="Dwelling_Approvals",
        title="Annual dwelling approvals in South Australia",
        labels={
            "Year": "Year",
            "Dwelling_Approvals": "Total dwelling approvals"
        }
    )

    st.plotly_chart(fig4, use_container_width=True)


# -----------------------------
# BA Interpretation
# -----------------------------
with tabs[4]:
    st.header("BA Interpretation")

    st.subheader("Current findings")

    st.markdown("""
    Based on the current prototype:

    - Rental data can identify suburbs with higher median rent levels.
    - The Housing Pressure Score provides a simple ranking of suburbs based on rental pressure.
    - Building approval data provides a statewide view of housing supply activity.
    - The current version highlights housing pressure but does not yet directly compare
      rent and approvals by the same local geography.
    - A future version should add LGA-level or SA2-level building approval data to allow
      a direct demand-versus-supply comparison by area.
    """)

    st.subheader("Key limitation")

    st.warning("""
    The rent dataset is suburb-level, while the current building approvals dataset is
    state-level. Because the geographic levels are different, this version should not
    claim that a specific suburb has low supply. It should only show rental pressure
    by suburb and supply trends for South Australia overall.
    """)

    st.subheader("Next recommended enhancement")

    st.success("""
    Add LGA-level building approvals and population data. This would allow the dashboard
    to calculate a more meaningful Housing Pressure Score by area.
    """)


# -----------------------------
# Data Tables
# -----------------------------
with tabs[5]:
    st.header("Data Tables")

    st.subheader("Housing pressure dataset")
    st.dataframe(filtered_rent, use_container_width=True)

    st.subheader("Monthly approvals dataset")
    st.dataframe(monthly_approvals, use_container_width=True)

    st.subheader("Annual approvals dataset")
    st.dataframe(annual_approvals, use_container_width=True)
