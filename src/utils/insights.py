import streamlit as st
import pandas as pd
import plotly.express as px

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

    repo = st.session_state.get("categoryRepository")
    if repo is None:
        return alerts_count

    categories = repo.get_all_categories()
    for category in categories:
        limit = category.get("threshold")
        if limit is None:
            continue

        spent = df[df["Category"] == category.get("name")]["Expense"].sum()
        if spent > limit:
            icon = category.get("icon", "💳")
            st.warning(
                f"{icon} **{category.get('name')}** spending (€{spent:.2f}) exceeds your threshold (€{limit:.2f})"
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

@st.cache_data
def account_balance(df: pd.DataFrame):
    df["Accounting Balance"] = df["Income"].sub(df["Expense"])
    df["Balance"] = df["Accounting Balance"].cumsum()

    # Metrics row
    col1, col2 = st.columns(2)
    col1.metric(label="Total Income", 
                value=f"€{df['Income'].sum():.2f}",
                delta="Gains")
    col2.metric(label="Total Expense",
                value=f"€{df['Expense'].sum():.2f}",
                delta="Losses",
                delta_color="inverse")
    st.header("📊 Spending Analysis")
    col_ch1, col_ch2 = st.columns(2)

    with col_ch1:
        st.subheader("Spending by Category")
        spending = get_spending_by_category(df)
        if not spending.empty:
            fig = px.bar(spending, x="Category", y="Expense", 
                            title="Total Expenses per Category",
                            labels={"Expense": "Amount (€)"},
                            color="Category" 
                        )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No expense data to display.")

    with col_ch2:
        st.subheader("Expense Distribution")
        expenses_df = df[df["Expense"] > 0]
        if not expenses_df.empty:
            fig_pie = px.pie(expenses_df, names="Category", values="Expense", 
                            title="Expenses by Category", hole=0.4,
                            color="Category")
            st.plotly_chart(fig_pie, use_container_width=True)
        else:
            st.info("No expenses to show in pie chart.")

@st.cache_data
def spending_by_category(df, name):
    pass