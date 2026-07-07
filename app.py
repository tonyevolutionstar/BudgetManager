from sqlalchemy import true
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date

from data import file
from data import model as ctgAI
from src.utils import insights
from src.utils import date as dt

# Page config must be the very first Streamlit call
st.set_page_config(
    page_title="Budget Manager", 
    page_icon=":material/money_bag:",
    layout="wide",
    initial_sidebar_state="auto"
)

# Current: Unclear state initialization
# Better: Use proper state initialization
def init_session_state():
    defaults = {
        "df": pd.DataFrame(),
        "model": None,
        "page": "dashboard"
    }
    for key, default in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default

# Call at app start
init_session_state()

# -------------------------------
# Main Dashboard
# -------------------------------
st.title(":green[:material/money_bag:] Budget Manager")
st.markdown("Manage your budget effectively by categorizing transactions and visualizing spending patterns.")

model = st.session_state.model
today: date = dt.get_today()

df, filter_type, start_date, end_date = dt.date_filter(st.session_state.df)
if df.empty:
    st.info("No transactions yet. Use the sidebar to add your first transaction.")
    st.stop()

with st.expander("⚙️ CSV Import Settings", True):
    col1, col2 = st.columns(2)
    with col1:
        skip_rows = st.number_input("Rows to skip", min_value=0, max_value=20, value=6)
    with col2:
        header_row = st.number_input("Header row (0-indexed)", min_value=0, max_value=20, value=6)
    
    uploaded_file = st.file_uploader(
        label="Upload a bank statement (CSV or PDF)",
        type=file.SUPPORTED_TYPES,
        accept_multiple_files=False
    )
    
    if st.button("Apply settings") and uploaded_file:
        st.session_state.df = file.handle_upload_file(uploaded_file, skip_rows=skip_rows, header_row=header_row)
        st.dataframe(st.session_state.df)

# Train model lazily (only when needed and not yet trained)
if st.session_state.model is None and not st.session_state.df.empty:
    model, _ = ctgAI.get_trained_model(df=st.session_state.df)
    st.session_state.model = model


insights.account_balance(df)
insights.check_alerts(df)

# Time series
st.subheader("Daily Income vs Expenses")
daily = insights.get_daily_income_expenses(df)
if not daily.empty:
    fig_line = px.line(daily, x="Date", y=["Expense", "Income"], 
                       title="Daily Trends",
                       labels={"value": "Amount (€)", "variable": "Type"},
                       color_discrete_map={"Expense": "red", "Income": "green"})
    st.plotly_chart(fig_line, use_container_width=True)
else:
    st.info("Not enough data for time series.")

# Transaction History
st.header("📜 Transaction History")
st.dataframe(df, use_container_width=True)

