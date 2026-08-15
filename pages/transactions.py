import streamlit as st
import pandas as pd

from service import FileImporterService
from service import ClassifierService as classifier
from src.repository import CategoryRepository
from src.utils import date as dt

st.title("📊 Transactions")

# Guard: ensure shared state exists before anything else
if "df" not in st.session_state:
    st.session_state.df = pd.DataFrame(columns=FileImporterService.CSV_COLUMNS)

if "model" not in st.session_state:
    st.session_state.model = None

df: pd.DataFrame = st.session_state.df
model = st.session_state.model

def get_categories():
    """Return category names from the DB, falling back to ['Others']."""
    if "categoryRepository" not in st.session_state or st.session_state.categoryRepository is None:
        st.session_state.categoryRepository = CategoryRepository()

    try:
        categories = st.session_state.categoryRepository.get_all_categories()
        if categories:
            names = [c.get('name') for c in categories if c.get('name')]
            if names:
                return names
    except Exception as e:
        st.error(f"Error fetching categories: {e}")

    return ['Others']

if model is None and not df.empty:
    model = classifier.TransactionClassifier()
    st.session_state.model = model

st.sidebar.header("New Transaction")

def _reset_amount():
    """Clear the amount input when toggling expense / income."""
    st.session_state["_amount"] = 0.0

with st.sidebar.form("transaction_form", clear_on_submit=True, enter_to_submit=False):
    transaction_date = st.date_input("Date", value=dt.get_today(), format=dt.DATE_FORMAT_DISPLAY)
    description = st.text_input("Description")

    # NOTE: on_change must be a callable reference, not a call expression
    is_expense = st.checkbox(label="Is Expense?", value=True, on_change=_reset_amount)

    amount = st.number_input(
        label="Expense Amount" if is_expense else "Income Amount",
        min_value=0.0,
        step=0.5,
        format="%.2f",
        key="_amount"
    )
    
    st.session_state.model = model
    assert st.session_state.model is not None
    suggested = st.session_state.model.classify(description).category if description else "Others"
    categories = get_categories()
    default_idx = categories.index(suggested) if suggested in categories else 0
    category = st.selectbox("Category", categories, index=default_idx)

    submitted = st.form_submit_button("Add Transaction")

    if submitted:
        if not description.strip():
            st.error("Please enter a description.")
        elif amount <= 0:
            st.error("Please enter a positive amount.")
        else:
            # Compute the new running balance
            current_balance = (df["Income"] - df["Expense"]).sum() if not df.empty else 0.0
            delta = amount if not is_expense else -amount
            new_accounting = delta
            new_balance = current_balance + delta

            new_row = pd.DataFrame([{
                "Date":                transaction_date.strftime("%d/%m/%Y"),
                "Date_Value":          transaction_date.strftime("%d/%m/%Y"),
                "Description":         description.strip(),
                "Expense":             amount if is_expense else 0.0,
                "Income":              amount if not is_expense else 0.0,
                "Accounting Balance":  new_accounting,
                "Balance":             new_balance,
                "Category":            category,
            }])

            st.session_state.df = pd.concat(
                [st.session_state.df, new_row], ignore_index=True
            )
            FileImporterService.save_dataframe(st.session_state.df)

            # Invalidate model so it retrains with the new transaction
            st.session_state.model = None
            st.success("Transaction added successfully!")
            st.rerun()

# -------------------------------
# Main: Transaction table
# -------------------------------
st.subheader("All Transactions")

current_df = st.session_state.df
if current_df.empty:
    st.info("No transactions yet. Use the sidebar to add one.")
else:
    st.dataframe(current_df, use_container_width=True)