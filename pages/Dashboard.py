import logging

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from data.database import DatabaseError
from service import CategorizationService as categorizer
from src.repository import CategoryRepository
from src.utils import date as dt

logger = logging.getLogger(__name__)

st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")

REQUIRED_COLUMNS = {"Date", "Description", "Expense", "Income", "Category"}
DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

@st.cache_data(ttl=60)
def load_budgets() -> dict[str, float]:
    """Monthly budget per category name (only categories with a budget > 0)."""
    return {
        c["name"]: c["monthlybudget"]
        for c in CategoryRepository().get_all_categories()
        if c["monthlybudget"] and c["monthlybudget"] > 0
    }

df: pd.DataFrame = st.session_state.get("df", pd.DataFrame())

if df is None or df.empty or not REQUIRED_COLUMNS <= set(df.columns):
    st.info("No transactions available. Import a bank statement to see your charts.")
    st.stop()

df = df.copy()
df["Date"] = dt.parse_dates(df["Date"])                    # never swaps day and month
df = df.dropna(subset=["Date"])
for col in ("Expense", "Income"):
    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
df["Category"] = df["Category"].fillna("Others").astype(str)

if df.empty:
    st.info("No transactions with a valid date.")
    st.stop()

def apply_auto_categories() -> None:
    changed = categorizer.auto_categorise_session()
    st.session_state.cat_flash = (
        f"Automatic categories applied to {changed} transactions." if changed else "Nothing to change."
    )

# ---------------------------------------------------------------------------
# Categories that are not the app
# ---------------------------------------------------------------------------
flash = st.session_state.pop("cat_flash", None)
if flash:
    st.success(flash)
 
known_lower = {c.lower() for c in categorizer.get_known_categories()}
foreign = df.loc[~df["Category"].str.lower().isin(known_lower), "Category"].value_counts()
if not foreign.empty:
    shown = ", ".join(foreign.index[:5]) + ("…" if len(foreign) > 5 else "")
    st.warning(
        f"{int(foreign.sum())} transactions use categories that are not your categories ({shown}), "
        "so the category charts do not reflect your own categorisation."
    )
    st.button("🏷️ Apply automatic categories", on_click=apply_auto_categories, type="primary", key="dash_auto_cat")

#region Sidebar: Period filter
min_date, max_date = df["Date"].min().date(), df["Date"].max().date()
st.sidebar.header("📅 Period")
period = st.sidebar.date_input(
    "Date range", value=(min_date, max_date),
    min_value=min_date, max_value=max_date, format=dt.DATE_FORMAT_DISPLAY,
)
if not (isinstance(period, tuple) and len(period) == 2):
    st.sidebar.info("Select an end date.")
    st.stop()
 
start, end = period
df = df[(df["Date"].dt.date >= start) & (df["Date"].dt.date <= end)]
if df.empty:
    st.info("No transactions in this period.")
    st.stop()
 
df["Month"] = df["Date"].dt.to_period("M").astype(str)

#endregion

#region Row 1: KPIs
total_in  = df["Income"].sum()
total_out = df["Expense"].sum()
net = total_in - total_out
expenses_only = df.loc[df["Expense"] > 0, "Expense"]
avg_expense = expenses_only.mean() if not expenses_only.empty else 0.0

k1, k2, k3, k4 = st.columns(4)
k1.metric("💰 Total Income",       f"€ {total_in:,.2f}")
k2.metric("💸 Total Expenses",     f"€ {total_out:,.2f}")
k3.metric("📈 Net Balance",        f"€ {net:,.2f}",
          delta="positive" if net >= 0 else "negative", delta_color="inverse" if net < 0 else "normal", delta_arrow = "down" if net < 0 else "up")
k4.metric("🧾 Average Expense",    f"€ {avg_expense:,.2f}")

st.divider()
#endregion

#region Row 2: Monthly bar + Running balance area 
col1, col2 = st.columns(2)

with col1:
    st.subheader("Income vs Expenses by Month")
    monthly = (
        df.groupby("Month")
        .agg(Income=("Income", "sum"), Expense=("Expense", "sum"))
        .reset_index()
    )
    fig = go.Figure()
    fig.add_bar(x=monthly["Month"], y=monthly["Income"], name="Income", marker_color="#2ecc71")
    fig.add_bar(x=monthly["Month"], y=monthly["Expense"], name="Expenses", marker_color="#e74c3c")
    fig.update_layout(barmode="group", xaxis_title="Month", yaxis_title="€", legend_title="Type")
    st.plotly_chart(fig, width="stretch")

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
    st.plotly_chart(fig2, width="stretch")
#endregion

#region Row 3: Category breakdown
by_cat = (
    df[df["Expense"] > 0]
    .groupby("Category")["Expense"]
    .sum()
    .reset_index()
    .sort_values("Expense", ascending=False)
)

col3, col4 = st.columns(2)

with col3:
    st.subheader("Expenses by Category")
    fig3 = px.pie(
        by_cat, names="Category", values="Expense",
        hole=0.45,
        color_discrete_sequence=px.colors.qualitative.Set3,
    )
    fig3.update_traces(textposition="inside", textinfo="percent+label")
    st.plotly_chart(fig3, width="stretch")

with col4:
    st.subheader("Top 10 Expense Categories")
    top10 = by_cat.head(10)
    fig4 = px.bar(
        top10, x="Expense", y="Category", orientation="h",
        labels={"Expense": "€", "Category": ""},
        color="Expense",
        color_continuous_scale="Reds",
    )
    fig4.update_layout(yaxis={"categoryorder": "total ascending"}, coloraxis_showscale=False)
    st.plotly_chart(fig4, width="stretch")
#endregion

#region Row 4: Budget vs Actual
st.subheader("Budget vs Actual Spending")

months = sorted(df["Month"].unique())
month = st.selectbox("Month", months, index=len(months) - 1)

try:
    budgets = load_budgets()
except DatabaseError as e:
    budgets = {}
    st.warning(str(e))

try:
    spent = df[df["Month"] == month].groupby("Category")["Expense"].sum()
    spent_by_name = spent.groupby(spent.index.str.lower()).sum() 
    budget_rows = [
        {
            "Category": name,
            "Budget": budget,
            "Spent": float(spent_by_name.get(name.lower(), 0.0)),
            "Pct": float(spent_by_name.get(name.lower(), 0.0)) / budget * 100,
        }
        for name, budget in budgets.items()
    ]
    bdf = pd.DataFrame(budget_rows).sort_values("Pct", ascending=True)

    fig5 = go.Figure()
    fig5.add_bar(y=bdf["Category"], x=bdf["Budget"], name="Budget", orientation="h",
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
    fig5.update_layout(barmode="overlay", xaxis_title="€", legend_title="Legend")
    st.plotly_chart(fig5, width="stretch")
    unbudgeted = sorted(c for c in spent.index if c.lower() not in {n.lower() for n in budgets} and spent[c] > 0)
    if unbudgeted:
        st.caption("Spent in categories without a budget (or not in the database): " + ", ".join(unbudgeted))
except Exception as e:
    logger.warning("Budget chart error: %s", e)
#endregion

#region Row 5: Day-of-week pattern + Anomaly scatter
col5, col6 = st.columns(2)

with col5:
    st.subheader("Average Spending by Day of Week")
    dow = (
        df[df["Expense"] > 0]
        .assign(Day=lambda d: d["Date"].dt.dayofweek)
        .groupby("Day")["Expense"].mean()
        .reindex(range(7), fill_value=0.0)
        .reset_index()
    )
    dow["DayName"] = dow["Day"].map(dict(enumerate(DAY_NAMES)))
    
    fig6 = px.bar(
        dow, x="DayName", y="Expense",
        labels={"Expense": "Average Expense (€)", "DayName": "Day"},
        color="Expense", color_continuous_scale="Blues"
    )
    fig6.update_layout(coloraxis_showscale=False)
    st.plotly_chart(fig6, width="stretch")

with col6:
    st.subheader("Anomalous Transactions (IQR Method)")
    expenses  = df[df["Expense"] > 0]["Expense"]
    if len(expenses) < 4:
        st.error("Not enough expenses to detect anomalies (at least 4 needed).")
    else:
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
            st.plotly_chart(fig7, width="stretch")
#endregion

#region Row 6: Monthly heatmap
st.subheader("Expense Heatmap — Day × Month")
heat = (
    df[df["Expense"] > 0]
    .assign(Day=lambda d: d["Date"].dt.day)
    .groupby(["Month", "Day"])["Expense"].sum()    
    .reset_index()
    .pivot(index="Month", columns="Day", values="Expense")
    .fillna(0)
)
if heat.empty:
    st.info("No expenses in this period.")
else:
    fig8 = px.imshow(
        heat,
        labels={"x": "Day", "y": "Month", "color": "€"},
        color_continuous_scale="YlOrRd",
        aspect="auto",
    )
    st.plotly_chart(fig8, width="stretch")
#endregion