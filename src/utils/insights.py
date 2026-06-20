import streamlit as st
import pandas as pd
from data import categories as ctg

def check_alerts(df: pd.DataFrame) -> int:
    """Display financial alerts based on spending data and category thresholds."""
    st.header("⚠️ Financial Health Alerts")
    alerts_count = 0
 
    # Overall expense vs income alert
    total_expense = df["Expense"].sum()
    total_income = df["Income"].sum()
    if total_expense > total_income:
        st.error("⚠️ Your total expenses exceed your total income. Consider reviewing your spending.")
        alerts_count += 1
 
    # Per-category threshold alerts
    for category, limit in ctg.get_all_thresholds().items():
        if limit is None:
            continue
        spent = df[df["Category"] == category]["Expense"].sum()
        if spent > limit:
            icon = ctg.get_category_icon(category)
            st.warning(
                f"{icon} **{category}** spending (€{spent:.2f}) exceeds your threshold (€{limit:.2f})"
            )
            alerts_count += 1
 
    if alerts_count == 0:
        st.success("✅ No alerts! Your spending looks healthy.")
 
    return alerts_count

@st.cache_data
def get_spending_by_category(df: pd.DataFrame) -> pd.DataFrame:
    """Return a DataFrame with total expenses grouped by category."""
    return df.groupby("Category")["Expense"].sum().reset_index()
 
@st.cache_data
def get_daily_income_expenses(df: pd.DataFrame) -> pd.DataFrame:
    """Return a DataFrame with daily sums of Expense and Income."""
    return df.groupby("Date").agg({"Expense": "sum", "Income": "sum"}).reset_index()

@st.cache_data
def get_monthly_trends(df: pd.DataFrame) -> pd.DataFrame:
    """Get monthly spending trends."""
    df["Month"] = df["Date"].dt.to_period("M")
    return df.groupby("Month").agg({
        "Expense": "sum",
        "Income": "sum"
    }).reset_index()

@st.cache_data
def get_anomalies(df: pd.DataFrame) -> pd.DataFrame:
    """Detect unusual transactions using IQR."""
    Q1 = df["Expense"].quantile(0.25)
    Q3 = df["Expense"].quantile(0.75)
    IQR = Q3 - Q1
    return df[(df["Expense"] > Q3 + 1.5 * IQR) | (df["Expense"] < Q1 - 1.5 * IQR)]