# app.py
import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

st.set_page_config(page_title="Executive Dashboard", layout="wide")

# ---------- Load & prepare data ----------
df = pd.read_csv("ba_orders_2024.csv")

required_cols = {"product", "channel", "region", "unit_price", "discount_pct", "revenue", "cost"}
missing = required_cols - set(df.columns)
if missing:
    st.error(f"Missing columns in CSV: {', '.join(sorted(missing))}")
    st.stop()

df["net_price"] = df["unit_price"] * (1 - df["discount_pct"])
df["profit"] = df["revenue"] - df["cost"]

summary = df.groupby(["channel", "region"], as_index=False).agg(
    orders=("product", "count"),
    revenue=("revenue", "sum"),
    profit=("profit", "sum"),
)
summary["AOV"] = np.where(summary["orders"] > 0, summary["revenue"] / summary["orders"], 0.0)

# ---------- Sidebar filters ----------
st.sidebar.header("Filters")
channels = sorted(summary["channel"].unique())
regions = sorted(summary["region"].unique())
selected_channel = st.sidebar.multiselect("Select Channels", channels, default=channels)
selected_region = st.sidebar.multiselect("Select Regions", regions, default=regions)

filtered = summary[
    (summary["channel"].isin(selected_channel)) &
    (summary["region"].isin(selected_region))
].copy()

# ---------- Helpers ----------
def simulate_price_change(base_units: float, avg_price: float, elasticity: float, delta_p: float):
    # demand_factor = (1 + Δp)^(-e)
    demand_factor = (1 + delta_p) ** (-elasticity)
    proj_units = base_units * demand_factor
    proj_revenue = proj_units * avg_price * (1 + delta_p)
    return proj_units, proj_revenue

def kpi_row(df_like: pd.DataFrame, title_prefix: str = ""):
    total_rev = df_like["revenue"].sum()
    total_orders = df_like["orders"].sum()
    avg_aov = df_like["AOV"].replace([np.inf, -np.inf], 0).mean() if len(df_like) else 0
    total_profit = df_like["profit"].sum()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric(f"{title_prefix}Total Revenue", f"${total_rev:,.0f}")
    c2.metric(f"{title_prefix}Total Orders", f"{int(total_orders):,}")
    c3.metric(f"{title_prefix}AOV", f"${avg_aov:,.2f}")
    c4.metric(f"{title_prefix}Total Profit", f"${total_profit:,.0f}")

def elasticity_block(base_units: float, avg_price: float, baseline_revenue: float, key_prefix: str):
    st.subheader("Elasticity Simulator")
    col_a, col_b = st.columns(2)
    with col_a:
        delta_p = st.slider("Price Change (%)", -0.20, 0.20, 0.05, step=0.01, key=f"dp_{key_prefix}")
    with col_b:
        elasticity = st.slider("Elasticity (e)", 0.5, 2.0, 1.2, step=0.1, key=f"e_{key_prefix}")

    if base_units <= 0 or avg_price <= 0:
        st.info("Not enough data for simulation in this segment.")
        return

    proj_units, proj_revenue = simulate_price_change(
        base_units=base_units,
        avg_price=avg_price,
        elasticity=elasticity,
        delta_p=delta_p,
    )

    st.write(f"Projected Units: **{proj_units:,.0f}**")
    st.write(f"Projected Revenue: **${proj_revenue:,.0f}**")
    rev_change = proj_revenue - baseline_revenue
    st.metric("Revenue Δ", f"${rev_change:,.0f}")

# ---------- Tabs ----------
tab_overview, tab_channel, tab_region = st.tabs(["Overview", "By Channel", "By Region"])

# ========== OVERVIEW ==========
with tab_overview:
    st.title("Executive Dashboard")

    # KPIs
    kpi_row(filtered)

    # Bar chart
    fig = px.bar(
        filtered,
        x="channel",
        y="revenue",
        color="region",
        barmode="stack",
        color_discrete_sequence=px.colors.qualitative.Set2,
        title="Revenue by Channel and Region",
    )
    fig.update_layout(plot_bgcolor="white", paper_bgcolor="white", legend_title_text="Region")
    st.plotly_chart(fig, use_container_width=True)

    # Elasticity simulator (global, based on current filters)
    st.header("Price Change Simulation (Filtered Total)")

    base_units_total = filtered["orders"].sum()
    total_revenue = filtered["revenue"].sum()
    avg_price_total = (total_revenue / base_units_total) if base_units_total > 0 else 0
    elasticity_block(
        base_units=base_units_total,
        avg_price=avg_price_total,
        baseline_revenue=total_revenue,
        key_prefix="overall",
    )

    # Detail table
    st.subheader("Detail (Filtered)")
    st.dataframe(
        filtered.sort_values(["channel", "region"]).assign(
            revenue=lambda d: d["revenue"].round(2),
            profit=lambda d: d["profit"].round(2),
            AOV=lambda d: d["AOV"].round(2),
        ),
        use_container_width=True,
    )

# ========== BY CHANNEL ==========
with tab_channel:
    st.header("Channel Mini Dashboard")
    chan_list = sorted(filtered["channel"].unique())
    if not chan_list:
        st.info("No channels available with current filters.")
    else:
        sel_chan = st.selectbox("Channel", chan_list, index=0, key="chan_sel")
        chan_df = filtered[filtered["channel"] == sel_chan].copy()

        # KPIs for the selected channel (aggregated across its regions)
        kpi_row(chan_df, title_prefix=f"{sel_chan} – ")

        # Chart: revenue by region within the selected channel
        fig_c = px.bar(
            chan_df,
            x="region",
            y="revenue",
            color="region",
            text_auto=".2s",
            color_discrete_sequence=px.colors.qualitative.Set2,
            title=f"Revenue by Region – {sel_chan}",
        )
        fig_c.update_layout(showlegend=False, plot_bgcolor="white", paper_bgcolor="white")
        st.plotly_chart(fig_c, use_container_width=True)

        # Elasticity for the selected channel
        chan_orders = chan_df["orders"].sum()
        chan_revenue = chan_df["revenue"].sum()
        chan_avg_price = (chan_revenue / chan_orders) if chan_orders > 0 else 0
        elasticity_block(
            base_units=chan_orders,
            avg_price=chan_avg_price,
            baseline_revenue=chan_revenue,
            key_prefix=f"channel_{sel_chan}",
        )

        # Table
        st.subheader(f"Detail – {sel_chan}")
        st.dataframe(
            chan_df.sort_values("region").assign(
                revenue=lambda d: d["revenue"].round(2),
                profit=lambda d: d["profit"].round(2),
                AOV=lambda d: d["AOV"].round(2),
            ),
            use_container_width=True,
        )

# ========== BY REGION ==========
with tab_region:
    st.header("Region Mini Dashboard")
    reg_list = sorted(filtered["region"].unique())
    if not reg_list:
        st.info("No regions available with current filters.")
    else:
        sel_reg = st.selectbox("Region", reg_list, index=0, key="reg_sel")
        reg_df = filtered[filtered["region"] == sel_reg].copy()

        # KPIs for the selected region (aggregated across its channels)
        kpi_row(reg_df, title_prefix=f"{sel_reg} – ")

        # Chart: revenue by channel within the selected region
        fig_r = px.bar(
            reg_df,
            x="channel",
            y="revenue",
            color="channel",
            text_auto=".2s",
            color_discrete_sequence=px.colors.qualitative.Set2,
            title=f"Revenue by Channel – {sel_reg}",
        )
        fig_r.update_layout(showlegend=False, plot_bgcolor="white", paper_bgcolor="white")
        st.plotly_chart(fig_r, use_container_width=True)

        # Elasticity for the selected region
        reg_orders = reg_df["orders"].sum()
        reg_revenue = reg_df["revenue"].sum()
        reg_avg_price = (reg_revenue / reg_orders) if reg_orders > 0 else 0
        elasticity_block(
            base_units=reg_orders,
            avg_price=reg_avg_price,
            baseline_revenue=reg_revenue,
            key_prefix=f"region_{sel_reg}",
        )

        # Table
        st.subheader(f"Detail – {sel_reg}")
        st.dataframe(
            reg_df.sort_values("channel").assign(
                revenue=lambda d: d["revenue"].round(2),
                profit=lambda d: d["profit"].round(2),
                AOV=lambda d: d["AOV"].round(2),
            ),
            use_container_width=True,
        )
