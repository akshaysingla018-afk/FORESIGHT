import streamlit as st
import pandas as pd
from pathlib import Path
import plotly.express as px

BASE = Path(__file__).resolve().parent
DATA = BASE / "data"

st.set_page_config(
    page_title="FORESIGHT Planning Dashboard",
    layout="wide"
)

@st.cache_data
def load():
    sku = pd.read_csv(DATA / "sku_master.csv")
    risk = pd.read_csv(DATA / "sku_risk_scoring.csv")
    fc = pd.read_csv(
        DATA / "forecast_next_8_weeks.csv",
        parse_dates=["week_start"]
    )
    actual = pd.read_csv(
        DATA / "weekly_demand_recent.csv",
        parse_dates=["week_start"]
    )
    return sku, risk, fc, actual


sku, risk, fc, actual = load()

st.title("FORESIGHT - Demand Forecast & Inventory Risk")
st.caption(
    "8-week SKU-level planning view | "
    "Forecast model: LightGBM | "
    "Risk logic: transparent stockout/overstock guardrails"
)

cat = st.selectbox(
    "Category",
    ["All"] + sorted(sku.category.dropna().unique().tolist())
)

filtered_risk = risk.copy()

if cat != "All":
    filtered_risk = filtered_risk.merge(
        sku[["sku_id", "category"]],
        on="sku_id",
        how="left"
    )
    filtered_risk = filtered_risk[
        filtered_risk.category.eq(cat)
    ]

sel = st.selectbox(
    "SKU",
    ["All"] + sorted(filtered_risk.sku_id.unique().tolist())
)

if sel != "All":
    filtered_risk = filtered_risk[
        filtered_risk.sku_id.eq(sel)
    ]

col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "SKUs in view",
    f"{len(filtered_risk):,}"
)

col2.metric(
    "Sales at risk",
    f"INR {filtered_risk.sales_at_risk.sum()/1e6:.1f}M"
)

col3.metric(
    "Capital locked",
    f"INR {filtered_risk.capital_locked.sum()/1e6:.1f}M"
)

col4.metric(
    "Reorder now",
    f"{(filtered_risk.action == 'Reorder now').sum():,}"
)

left, right = st.columns(2)

with left:
    st.subheader("Forecast vs Actual")

    if sel != "All":
        a = actual[
            actual.sku_id.eq(sel)
        ].sort_values("week_start")

        f = fc[
            fc.sku_id.eq(sel)
        ].sort_values("week_start")

        fig = px.line(
            a,
            x="week_start",
            y="units_sold",
            title="Historical Weekly Demand"
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

        if not f.empty:
            forecast_fig = px.line(
                f,
                x="week_start",
                y="prediction",
                title="8-Week Demand Forecast"
            )

            st.plotly_chart(
                forecast_fig,
                use_container_width=True
            )
    else:
        st.info(
            "Select an SKU to view its forecast history."
        )

with right:
    st.subheader("Risk Actions")

    action_counts = (
        filtered_risk.action
        .value_counts()
        .rename_axis("action")
        .reset_index(name="count")
    )

    fig = px.bar(
        action_counts,
        x="action",
        y="count",
        title="SKUs by Recommended Action"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

st.subheader("Prioritised Decision List")

cols = [
    "sku_id",
    "sku_name",
    "category",
    "forecast_8w_units",
    "stock_on_hand",
    "sales_at_risk",
    "capital_locked",
    "action"
]

st.dataframe(
    filtered_risk[cols].head(50),
    use_container_width=True
)