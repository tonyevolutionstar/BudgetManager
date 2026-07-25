import pandas as pd
import streamlit as st
from datetime import date, datetime

DATE_FORMAT_FILE = '%d/%m/%Y'
DATE_FORMAT_DISPLAY = 'DD/MM/YYYY'

def get_today() -> date:
    """Return today's date (date, not datetime)."""
    return date.today()

def get_now() -> datetime:
    """Return the current datetime."""
    return datetime.now()

def format_date(d: datetime) -> str:
    """Format a date or datetime as DD/MM/YYYY string."""
    return d.strftime(DATE_FORMAT_FILE)

def apply_date_filter(df: pd.DataFrame, filter_type, start_date, end_date) -> pd.DataFrame:
    """Return filtered DataFrame based on selected filter type."""
    if df.empty or "Date" not in df.columns:
        return df.copy()
    
    today = get_today()
    df_copy = df.copy()
    # Ensure Date is datetime
    df_copy["Date"] = pd.to_datetime(df_copy["Date"])
    
    if filter_type == "Today":
        filtered = df_copy[df_copy["Date"].dt.date == today]
    elif filter_type == "This Month":
        filtered = df_copy[(df_copy["Date"].dt.year == today.year) & 
                           (df_copy["Date"].dt.month == today.month)]
    else:  # Custom
        if start_date and end_date:
            filtered = df_copy[(df_copy["Date"].dt.date >= start_date) & 
                               (df_copy["Date"].dt.date <= end_date)]
        else:
            filtered = df_copy
    return filtered

def date_filter(df: pd.DataFrame) -> tuple[pd.DataFrame, str, date | datetime, date | datetime]:
    """Select a filter Date"""
    st.sidebar.header("📅 Date Filter")
    filter_type = st.sidebar.radio(
        "Select period",
        ["Today", "This Month", "Custom Range"],
        index=1  # default to "This Month"
    )

    start_date = get_today()
    end_date = get_today()
    today = get_today()
    if filter_type == "Custom Range":
        col1, col2 = st.sidebar.columns(2)
        with col1:
            start_date = st.date_input("From", max_value=today, format=DATE_FORMAT_DISPLAY)
        with col2:
            end_date = st.date_input("To", max_value=today, format=DATE_FORMAT_DISPLAY)

    # Apply filter to main DataFrame
    filtered_df = apply_date_filter(df, filter_type, start_date, end_date)

    # Display current filter info in sidebar
    if filter_type == "Today":
        st.sidebar.info(f"Showing data for **{today.strftime('%d of %B')}**")
    elif filter_type == "This Month":
        st.sidebar.info(f"Showing data for **{today.strftime('%B')}**")
    return filtered_df, filter_type, start_date, end_date