import streamlit as st
import pandas as pd
import plotly.express as px

from data import categories as ctg
from data import file
from data import model as ctgAI
from utils import insights
from utils import date
from pypdf import PdfReader

# Page config must be first Streamlit command
st.set_page_config(page_title="Budget Manager", page_icon=":material/finance:", layout="wide", initial_sidebar_state="auto")

fileTypes = ["csv", "pdf"]

uploaded_file = st.file_uploader(label="Choose File", type=fileTypes, accept_multiple_files=False)
if uploaded_file is not None:
    attribute = uploaded_file.__getattribute__("type")
    if attribute.endswith(fileTypes[0]):
        if "df" not in st.session_state:
            st.session_state.df = file.load_csv_file(uploaded_file)
            st.write(st.session_state.df.columns)
    elif attribute.endswith(fileTypes[1]):
        reader = PdfReader(uploaded_file)
        st.write(reader.read(uploaded_file.getbuffer()))

df = st.session_state.df

# Train/load model
model, _ = ctgAI.get_trained_model(df)
today = date.get_actual_date()

# -------------------------------
# Helper: apply date filter
# -------------------------------
def apply_date_filter(df, filter_type, start_date=None, end_date=None):
    """Return filtered DataFrame based on selected filter type."""
    if df.empty or "Date" not in df.columns:
        return df.copy()
    
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

# -------------------------------
# Sidebar: Date Filter
# -------------------------------
st.sidebar.header("📅 Date Filter")
filter_type = st.sidebar.radio(
    "Select period",
    ["Today", "This Month", "Custom Range"],
    index=1  # default to "This Month"
)

start_date = None
end_date = None
if filter_type == "Custom Range":
    col1, col2 = st.sidebar.columns(2)
    with col1:
        start_date = st.date_input("From", max_value=today, format="DD/MM/YYYY")
    with col2:
        end_date = st.date_input("To", max_value=today, format="DD/MM/YYYY")

# Apply filter to main DataFrame
filtered_df = apply_date_filter(df, filter_type, start_date, end_date)

# Display current filter info in sidebar
if filter_type == "Today":
    st.sidebar.info(f"Showing data for **{today.strftime("%d of %B")}**")
elif filter_type == "This Month":
    st.sidebar.info(f"Showing data for **{today.strftime("%B")}**")


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

# Alerts
st.header("⚠️ Financial Health Alerts")
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

# Clear data button (with confirmation)
if st.button("🗑️ Clear All Transactions", type="primary"):
    # Optional: add confirmation dialog
    empty_df = pd.DataFrame(columns=file.CSV_COLUMNS)
    st.session_state.df = empty_df
    file.save_dataframe(empty_df)
    st.cache_resource.clear()
    st.success("All transactions cleared. Reloading...")
    st.rerun()