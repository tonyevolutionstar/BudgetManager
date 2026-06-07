import streamlit as st
import pandas as pd
from data import categories as ctg

def check_alerts(df):
    """Display financial alerts based on data and thresholds."""
    alerts_count = 0
    
    # Basic expense vs income alert
    total_expense = df["Expense"].sum()
    total_income = df["Income"].sum()
    if total_expense > total_income:
        st.error("⚠️ Your total expenses exceed your total income. Consider reviewing your spending.")
        alerts_count += 1
    
    # Category threshold alerts
    thresholds = ctg.get_all_thresholds()
    for category, limit in thresholds.items():
        if limit is None:
            continue
        spent = df[df["Category"] == category]["Expense"].sum()
        if spent > limit:
            icon = ctg.get_category_icon(category)
            st.warning(f"{icon} **{category}** spending (€{spent:.2f}) exceeds your threshold (€{limit:.2f})")
            alerts_count += 1
    
    if alerts_count == 0:
        st.success("✅ No alerts! Your spending looks healthy.")
    
    return alerts_count

def get_spending_by_category(df):
    """Return DataFrame of total expense per category."""
    return df.groupby("Category")["Expense"].sum().reset_index()

def get_daily_income_expenses(df):
    """Return DataFrame with daily sums of Expense and Income."""
    daily = df.groupby("Date").agg({"Expense": "sum", "Income": "sum"}).reset_index()
    return daily