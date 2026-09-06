import logging

import streamlit as st
import pandas as pd

from service import FileImporterService
from service import ClassifierService as classifier
from src.repository import CategoryRepository
from src.utils import date as dt

logger = logging.getLogger(__name__)

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

if st.session_state.model is not None:
    # We read description from session_state if it was stored previously;
    # otherwise default to empty so the first render is safe.
    _preview_desc = st.session_state.get("_preview_desc", "")
    suggested = st.session_state.model.classify(_preview_desc).category \
                if _preview_desc else "Others"
else:
    suggested = "Others"
 
categories  = get_categories()
default_idx = categories.index(suggested) if suggested in categories else 0

with st.form("transaction_form", clear_on_submit=True, enter_to_submit=False):
    transaction_date = st.date_input("Date", value=dt.get_today(), format=dt.DATE_FORMAT_DISPLAY)
    description = st.text_input("Description")

    is_expense = st.checkbox(label="Is Expense?", value=True)

    amount = st.number_input(
        label="Expense Amount" if is_expense else "Income Amount",
        min_value=0.0,
        step=0.5,
        format="%.2f",
        key="_amount"
    )
    
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
            new_balance = current_balance + delta

            new_row = pd.DataFrame([{
                "Date":                transaction_date.strftime(dt.DATE_FORMAT_FILE),
                "Date_Value":          transaction_date.strftime(dt.DATE_FORMAT_DISPLAY ),
                "Description":         description.strip(),
                "Expense":             amount if is_expense else 0.0,
                "Income":              amount if not is_expense else 0.0,
                "Accounting Balance":  delta,
                "Balance":             new_balance,
                "Category":            category,
            }])

            st.session_state.df = pd.concat([st.session_state.df, new_row], ignore_index=True)
            FileImporterService.save_dataframe(st.session_state.df)

            # Invalidate model so it retrains with the new transaction
            st.session_state["_preview_desc"] = description.strip()
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