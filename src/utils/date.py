import logging
from datetime import date, datetime

import pandas as pd
import streamlit as st
import data.constants as const

logger = logging.getLogger(__name__)

def get_today() -> date:
    """Return today's date (date, not datetime)."""
    return date.today()

def get_now() -> datetime:
    """Return the current datetime."""
    return datetime.now()

def format_date(d: datetime) -> str:
    """Format a date or datetime as DD/MM/YYYY string."""
    return d.strftime(const.DATE_FORMAT_FILE)

def parse_dates(series: pd.Series) -> pd.Series:
    """Parse a Date column to datetime64 without swapping day and month."""
    if pd.api.types.is_datetime64_any_dtype(series):
        return series
    s = series.astype("string").str.strip()
    parsed = pd.to_datetime(s, format=const.DATE_FORMAT_FILE, errors="coerce")
    missing = parsed.isna() & s.notna()
    if missing.any():
        parsed.loc[missing] = pd.to_datetime(s[missing], dayfirst=True, errors="coerce", format="mixed")
    return parsed

def apply_date_filter(df: pd.DataFrame, filter_type: str, start_date: date | datetime | None,
    end_date: date | datetime | None) -> pd.DataFrame:
    """Return a filtered copy of *df* based on the selected filter type.

    Does nothing (returns a copy) when df is empty or has no 'Date' column.
    """
    if df.empty or "Date" not in df.columns:
        return df.copy()

    today   = get_today()
    df_copy = df.copy()
    df_copy["Date"] = parse_dates(df_copy["Date"])

    if filter_type == "Today":
        return df_copy[df_copy["Date"].dt.date == today]

    if filter_type == "This Month":
        return df_copy[
            (df_copy["Date"].dt.year  == today.year) &
            (df_copy["Date"].dt.month == today.month)
        ]

    # Custom Range
    if start_date and end_date:
        # Normalise to date objects for comparison
        s = start_date.date() if isinstance(start_date, datetime) else start_date
        e = end_date.date()   if isinstance(end_date,   datetime) else end_date
        return df_copy[
            (df_copy["Date"].dt.date >= s) &
            (df_copy["Date"].dt.date <= e)
        ]

    return df_copy


def date_filter(df: pd.DataFrame) -> tuple[pd.DataFrame, str, date, date]:
    """Render the sidebar date filter and return (filtered_df, filter_type, start, end)."""
    st.sidebar.header("📅 Date Filter")

    filter_type: str = st.sidebar.radio(
        "Select period",
        ["Today", "This Month", "Custom Range"],
        index=1,
    )

    today      = get_today()
    start_date = today
    end_date   = today

    if filter_type == "Custom Range":
        col1, col2 = st.sidebar.columns(2)
        with col1:
            start_date = st.date_input(
                "From", value=today, max_value=today, format=const.DATE_FORMAT_DISPLAY
            )
        with col2:
            end_date = st.date_input(
                "To", value=today, max_value=today, format=const.DATE_FORMAT_DISPLAY
            )
        if start_date > end_date:
            st.sidebar.error("'From' must be on or before 'To'.")
            return df.iloc[0:0].copy(), filter_type, start_date, end_date

    filtered_df = apply_date_filter(df, filter_type, start_date, end_date)

    if filter_type == "Today":
        st.sidebar.info(f"Showing data for **{today.strftime('%d of %B')}**")
    elif filter_type == "This Month":
        st.sidebar.info(f"Showing data for **{today.strftime('%B %Y')}**")
    else:
        st.sidebar.info(
            f"From **{start_date.strftime(const.DATE_FORMAT_FILE)}** "
            f"to **{end_date.strftime(const.DATE_FORMAT_FILE)}**"
        )

    return filtered_df, filter_type, start_date, end_date