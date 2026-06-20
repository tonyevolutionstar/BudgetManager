from pandas import DataFrame
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import date

from data import categories as ctg
from data import file
from data import model as ctgAI
from src.utils import insights
from src.utils import date as dt

# Current: Unclear state initialization
# Better: Use proper state initialization
def init_session_state():
    defaults = {
        "df": pd.DataFrame(),
        "model": None,
        "categories_initialized": False,
        "page": "dashboard"
    }
    for key, default in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default

# Call at app start
init_session_state()

# Page config must be the very first Streamlit call
st.set_page_config(
    page_title="Budget Manager", 
    page_icon=":material/finance:",
    layout="wide",
    initial_sidebar_state="auto"
)

df = DataFrame()


# Na UI, permite ao utilizador configurar
with st.expander("⚙️ CSV Import Settings"):
    col1, col2 = st.columns(2)
    with col1:
        skip_rows = st.number_input("Rows to skip", min_value=0, max_value=20, value=6)
    with col2:
        header_row = st.number_input("Header row (0-indexed)", min_value=0, max_value=20, value=6)
    
    if st.button("Apply settings"):
        uploaded_file = st.file_uploader(
            label="Upload a bank statement (CSV or PDF)",
            type=file.SUPPORTED_TYPES,
            accept_multiple_files=False
        )

        if uploaded_file is not None:
            df = file.handle_upload_file(uploaded_file, skip_rows=skip_rows, header_row=header_row)
            st.success(f"CSV loaded with skip_rows={skip_rows} and header_row={header_row}")

# Train model lazily (only when needed and not yet trained)
if st.session_state.model is None and not df.empty:
    model, _ = ctgAI.get_trained_model(df)
    st.session_state.model = model

model = st.session_state.model
today: date = dt.get_today()

df, filter_type, start_date, end_date = dt.date_filter(df)
dt.apply_date_filter(df, filter_type, start_date,end_date)

# -------------------------------
# Main Dashboard
# -------------------------------
st.title(":green[:material/money_bag:] Budget Manager")
st.markdown("Manage your budget effectively by categorizing transactions and visualizing spending patterns.")

if df.empty:
    st.info("No transactions yet. Use the sidebar to add your first transaction.")
    st.stop()

# Calculate running balances
df["Accounting Balance"] = df["Income"].sub(df["Expense"])
df["Balance"] = df["Accounting Balance"].cumsum()

# Metrics row
col1, col2 = st.columns(2)
col1.metric(label="Total Income", value=df['Income'].sum(), format="euro", delta="Gains", delta_color="normal")
col2.metric(label="Total Expense", value=df['Expense'].sum(), format="euro", delta="Losses", delta_arrow="down", delta_color="inverse")

insights.check_alerts(df)

# Charts
st.header("📊 Spending Analysis")
col_ch1, col_ch2 = st.columns(2)

with col_ch1:
    st.subheader("Spending by Category")
    spending = insights.get_spending_by_category(df)
    if not spending.empty:
        fig = px.bar(spending, x="Category", y="Expense", 
                     title="Total Expenses per Category",
                     labels={"Expense": "Amount (€)"},
                     color="Category", 
                     color_discrete_map=ctg.get_all_thresholds()  # just for colors? Better use category_colors
                    )
        # Fix colors: use category_colors
        fig.update_traces(marker_color=[ctg.get_category_color(cat) for cat in spending["Category"]])
        st.plotly_chart(fig, width="content")
    else:
        st.info("No expense data to display.")

with col_ch2:
    st.subheader("Expense Distribution")
    expenses_df = df[df["Expense"] > 0]
    if not expenses_df.empty:
        fig_pie = px.pie(expenses_df, names="Category", values="Expense", 
                         title="Expenses by Category", hole=0.4,
                         color="Category",
                         color_discrete_map={cat: ctg.get_category_color(cat) for cat in expenses_df["Category"].unique()})
        st.plotly_chart(fig_pie, width="content")
    else:
        st.info("No expenses to show in pie chart.")

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

