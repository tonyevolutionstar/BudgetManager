import logging

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

logger = logging.getLogger(__name__)

st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")
st.title("📊 Financial Dashboard")

df: pd.DataFrame = st.session_state.get("df", pd.DataFrame())

if df.empty:
    st.info("No transactions available. Import a bank statement to see your charts.")
    st.stop()

# ── Common preparation ────────────────────────────────────────────────────────
df = df.copy()
df["Date"]  = pd.to_datetime(df["Date"], errors="coerce", dayfirst=True)
df["Month"] = df["Date"].dt.to_period("M").astype(str)

# ── Row 1: KPIs ───────────────────────────────────────────────────────────────
total_in    = df["Income"].sum()
total_out   = df["Expense"].sum()
net         = total_in - total_out
avg_expense = df[df["Expense"] > 0]["Expense"].mean()

k1, k2, k3, k4 = st.columns(4)
k1.metric("💰 Total Income",       f"€ {total_in:,.2f}")
k2.metric("💸 Total Expenses",     f"€ {total_out:,.2f}")
k3.metric("📈 Net Balance",        f"€ {net:,.2f}",
          delta="positive" if net >= 0 else "negative")
k4.metric("🧾 Average Expense",    f"€ {avg_expense:,.2f}")

st.divider()

# ── Row 2: Monthly bar + Running balance area ─────────────────────────────────
col1, col2 = st.columns(2)

with col1:
    st.subheader("Income vs Expenses by Month")
    monthly = (
        df.groupby("Month")
        .agg(Income=("Income", "sum"), Expense=("Expense", "sum"))
        .reset_index()
    )
    fig = go.Figure()
    fig.add_bar(x=monthly["Month"], y=monthly["Income"],
                name="Income",   marker_color="#2ecc71")
    fig.add_bar(x=monthly["Month"], y=monthly["Expense"],
                name="Expenses", marker_color="#e74c3c")
    fig.update_layout(barmode="group",
                      xaxis_title="Month", yaxis_title="€",
                      legend_title="Type")
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("Cumulative Balance Over Time")
    df_sorted = df.sort_values("Date")
    df_sorted["RunningBalance"] = (df_sorted["Income"] - df_sorted["Expense"]).cumsum()
    fig2 = px.area(
        df_sorted, x="Date", y="RunningBalance",
        labels={"RunningBalance": "Balance (€)", "Date": "Date"},
        color_discrete_sequence=["#3498db"],
    )
    fig2.add_hline(y=0, line_dash="dash", line_color="red", opacity=0.5)
    st.plotly_chart(fig2, use_container_width=True)

# ── Row 3: Category breakdown ─────────────────────────────────────────────────
col3, col4 = st.columns(2)

by_cat = (
    df[df["Expense"] > 0]
    .groupby("Category")["Expense"]
    .sum()
    .reset_index()
    .sort_values("Expense", ascending=False)
)

with col3:
    st.subheader("Expenses by Category (Donut)")
    fig3 = px.pie(
        by_cat, names="Category", values="Expense",
        hole=0.45,
        color_discrete_sequence=px.colors.qualitative.Set3,
    )
    fig3.update_traces(textposition="inside", textinfo="percent+label")
    st.plotly_chart(fig3, use_container_width=True)

with col4:
    st.subheader("Top 10 Expense Categories")
    top10 = by_cat.head(10)
    fig4 = px.bar(
        top10, x="Expense", y="Category", orientation="h",
        labels={"Expense": "€", "Category": ""},
        color="Expense",
        color_continuous_scale="Reds",
    )
    fig4.update_layout(yaxis={"categoryorder": "total ascending"},
                       coloraxis_showscale=False)
    st.plotly_chart(fig4, use_container_width=True)

# ── Row 4: Budget vs Actual ───────────────────────────────────────────────────
st.subheader("Budget vs Actual Spending (current month)")

repo = st.session_state.get("categoryRepository")
if repo:
    try:
        cats = repo.get_all_categories()
        budgets = {
            c["name"]: c.get("monthly_budget") or c.get("threshold") or 0
            for c in cats
            if c.get("monthly_budget") or c.get("threshold")
        }
        today      = pd.Timestamp.today()
        this_month = df[
            (df["Date"].dt.year  == today.year) &
            (df["Date"].dt.month == today.month)
        ]
        actual = this_month.groupby("Category")["Expense"].sum()

        budget_rows = [
            {
                "Category": cat,
                "Budget":   budget,
                "Spent":    actual.get(cat, 0),
                "Pct":      min(actual.get(cat, 0) / budget * 100, 100)
                            if budget > 0 else 0,
            }
            for cat, budget in budgets.items()
        ]

        if budget_rows:
            bdf = pd.DataFrame(budget_rows).sort_values("Pct", ascending=True)
            fig5 = go.Figure()
            fig5.add_bar(
                y=bdf["Category"], x=bdf["Budget"],
                name="Budget", orientation="h",
                marker_color="rgba(52,152,219,0.3)",
            )
            fig5.add_bar(
                y=bdf["Category"], x=bdf["Spent"],
                name="Spent", orientation="h",
                marker_color=[
                    "#e74c3c" if r["Pct"] >= 100 else
                    "#f39c12" if r["Pct"] >= 80  else
                    "#2ecc71"
                    for _, r in bdf.iterrows()
                ],
            )
            fig5.update_layout(
                barmode="overlay",
                xaxis_title="€",
                legend_title="Legend",
            )
            st.plotly_chart(fig5, use_container_width=True)
        else:
            st.info("Set monthly budgets on your categories to see this chart.")
    except Exception as e:
        logger.warning("Budget chart error: %s", e)
else:
    st.info("Category repository not loaded.")

# ── Row 5: Day-of-week pattern + Anomaly scatter ──────────────────────────────
col5, col6 = st.columns(2)

with col5:
    st.subheader("Average Spending by Day of Week")
    df["DayOfWeek"] = df["Date"].dt.day_name()
    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday",
                 "Friday", "Saturday", "Sunday"]
    dow = (
        df[df["Expense"] > 0]
        .groupby("DayOfWeek")["Expense"]
        .mean()
        .reindex(day_order)
        .reset_index()
    )
    fig6 = px.bar(
        dow, x="DayOfWeek", y="Expense",
        labels={"Expense": "Average Expense (€)", "DayOfWeek": "Day"},
        color="Expense",
        color_continuous_scale="Blues",
    )
    fig6.update_layout(coloraxis_showscale=False)
    st.plotly_chart(fig6, use_container_width=True)

with col6:
    st.subheader("Anomalous Transactions (IQR Method)")
    expenses  = df[df["Expense"] > 0]["Expense"]
    q1, q3    = expenses.quantile(0.25), expenses.quantile(0.75)
    iqr       = q3 - q1
    threshold = q3 + 1.5 * iqr
    anomalies = df[df["Expense"] > threshold]

    if anomalies.empty:
        st.success("✅ No anomalous transactions detected.")
    else:
        st.warning(f"⚠️ {len(anomalies)} transactions above the normal range.")
        plot_df = df[df["Expense"] > 0].sort_values("Date").copy()
        plot_df["Status"] = plot_df["Expense"].apply(
            lambda v: "Anomalous" if v > threshold else "Normal"
        )
        fig7 = px.scatter(
            plot_df, x="Date", y="Expense",
            color="Status",
            color_discrete_map={"Anomalous": "#e74c3c", "Normal": "#95a5a6"},
            hover_data=["Description", "Category"],
            labels={"Expense": "€"},
        )
        st.plotly_chart(fig7, use_container_width=True)

# ── Row 6: Monthly heatmap ────────────────────────────────────────────────────
st.subheader("Expense Heatmap — Day × Month")
df["Day"]       = df["Date"].dt.day
df["MonthName"] = df["Date"].dt.strftime("%Y-%m")
heat = (
    df[df["Expense"] > 0]
    .groupby(["MonthName", "Day"])["Expense"]
    .sum()
    .reset_index()
    .pivot(index="MonthName", columns="Day", values="Expense")
    .fillna(0)
)
fig8 = px.imshow(
    heat,
    labels={"x": "Day", "y": "Month", "color": "€"},
    color_continuous_scale="YlOrRd",
    aspect="auto",
)
st.plotly_chart(fig8, use_container_width=True)