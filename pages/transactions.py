import logging

import streamlit as st
import pandas as pd

from data.database import DatabaseError
from service import CategorizationService as categorizer
from service import ClassifierService as classifier
from service import FileImporterService
from src.repository import CategoryRepository
from src.utils import date as dt

logger = logging.getLogger(__name__)

st.title("📊 Transactions")

CSV_COLUMNS = FileImporterService.CSV_COLUMNS
MAX_AMOUNT = 1_000_000_000.0


# ==================== DATA HELPERS ====================
@st.cache_data(ttl=60)
def _load_category_names() -> list[str]:
    """Category names from the DB, cached for a minute so typing doesn't query on every rerun.
    Exceptions are not cached, so a failed lookup is retried on the next rerun."""
    categories = CategoryRepository().get_all_categories()
    return [c["name"] for c in categories if c.get("name")]

def get_categories() -> list[str]:
    try:
        names = _load_category_names()
        if names:
            return names
    except DatabaseError as e:
        st.error(str(e))
    return ["Others"]


def ensure_frame(df: pd.DataFrame | None) -> pd.DataFrame:
    """Return the transactions with the app's columns and a real datetime Date column."""
    if df is None or df.empty:
        return pd.DataFrame(columns=CSV_COLUMNS)
    df = df.copy()
    df["Date"] = dt.parse_dates(df["Date"])
    return df


def balance_at(df: pd.DataFrame, when: pd.Timestamp) -> float:
    """Balance after the latest transaction on or before `when` (0.0 if there is none).

    Files may list the newest transaction first (bank exports) or last (appended
    rows). The order is inferred from the first and last dates, and only decides
    which of several same-day rows is the latest.
    """
    eligible = df[df["Date"] <= when]
    if eligible.empty:
        return 0.0
    last_day = eligible[eligible["Date"] == eligible["Date"].max()]
    newest_first = df["Date"].iloc[0] > df["Date"].iloc[-1]
    row = last_day.iloc[0] if newest_first else last_day.iloc[-1]
    return float(row["Balance"])


def flash(kind: str, message: str) -> None:
    st.session_state.tx_flash = (kind, message)


def get_classifier(df: pd.DataFrame, categories: list[str]) -> classifier.TransactionClassifier:
    """Build the classifier once per data change (session 'model' is reset to None when data changes)."""
    if st.session_state.get("model") is None:
        valid = set(categories)
        from_data = [] if df.empty else [
            (str(desc), cat) for desc, cat in zip(df["Description"], df["Category"]) if cat in valid
        ]
        # your stored corrections (MLTrainingSample) first, then the categories already in the data
        samples = categorizer.get_training_samples() + from_data
        st.session_state.model = classifier.TransactionClassifier(training_samples=samples)
    return st.session_state.model


def record_feedback(description: str, chosen: str, suggestion) -> None:
    """Save the category chosen for a manual entry as a training sample (MLTrainingSample)."""
    if suggestion.source == "unclassified" and chosen == categorizer.DEFAULT_CATEGORY:
        return   # nothing was suggested and nothing meaningful was chosen
    if chosen != suggestion.category:
        source = "manual"
    elif suggestion.source == "ml":
        source = "confirmed_ml"
    else:
        source = "confirmed_rule"
    try:
        categorizer.save_feedback([(description, chosen, source)])
    except DatabaseError:
        logger.warning("Could not save the category choice for learning.")


# ==================== SUBMIT CALLBACK ====================
def add_transaction() -> None:
    """Validate the form state and append the transaction. Runs before the page reruns."""
    ss = st.session_state
    description = (ss.get("tx_desc") or "").strip()
    amount = float(ss.get("tx_amount") or 0.0)

    if not description:
        flash("error", "Please enter a description.")
        return
    if amount <= 0:
        flash("error", "Please enter a positive amount.")
        return
    if amount > MAX_AMOUNT:
        flash("error", "That amount is too large.")
        return

    df = ensure_frame(ss.get("df"))
    suggestion = get_classifier(df, get_categories()).classify(description)   # what the app would have chosen
    when = pd.Timestamp(ss.tx_date)
    delta = -amount if ss.tx_kind == "Expense" else amount
    # A manual entry has no bank balance of its own: both balance columns hold the new balance.
    new_balance = round(balance_at(df, when) + delta, 2) if not df.empty else round(delta, 2)

    new_row = pd.DataFrame([{
        "Date": when,
        "BalanceDate": when,
        "Description": description,
        "Expense": amount if ss.tx_kind == "Expense" else 0.0,
        "Income": amount if ss.tx_kind == "Income" else 0.0,
        "Accounting Balance": new_balance,
        "Balance": new_balance,
        "Category": ss.tx_category,
    }], columns=CSV_COLUMNS)

    backdated = not df.empty and when < df["Date"].max()
    ss.df = new_row if df.empty else pd.concat([df, new_row], ignore_index=True)
    ss.model = None  # retrain the classifier with the new data
    record_feedback(description, ss.tx_category, suggestion)

    try:
        FileImporterService.save_dataframe(ss.df)
    except OSError:
        logger.exception("Could not save transactions to CSV")
        flash("warning", "Transaction added, but it could not be saved to disk.")
        ss.tx_desc, ss.tx_amount, ss._suggested_for = "", 0.0, ""
        return

    if backdated:
        flash("warning", "Transaction added. It is dated before the latest one, so the balances of later rows were not recalculated.")
    else:
        flash("success", "Transaction added successfully!")
    ss.tx_desc, ss.tx_amount, ss._suggested_for = "", 0.0, ""


# ==================== FORM ====================
if "model" not in st.session_state:
    st.session_state.model = None

df = ensure_frame(st.session_state.get("df"))
st.session_state.df = df
categories = get_categories()

pending = st.session_state.pop("tx_flash", None)
if pending:
    getattr(st, pending[0])(pending[1])

col1, col2 = st.columns(2)
with col1:
    st.date_input("Date", value=dt.get_today(), format=dt.DATE_FORMAT_DISPLAY, key="tx_date")
with col2:
    st.radio("Type", ["Expense", "Income"], horizontal=True, key="tx_kind")

st.text_input("Description", key="tx_desc", max_chars=200)

# Suggest a category for the description being typed now (not the previous one),
# but only when the description changed, so a manual choice isn't overwritten.
description = (st.session_state.get("tx_desc") or "").strip()
if description:
    suggestion = get_classifier(df, categories).classify(description)
    if st.session_state.get("_suggested_for") != description:
        st.session_state._suggested_for = description
        if suggestion.category in categories:
            st.session_state.tx_category = suggestion.category
    st.caption(f"💡 Suggested category: **{suggestion.category}** ({suggestion.source})")

if st.session_state.get("tx_category") not in categories:   # e.g. the category was deleted
    st.session_state.tx_category = categories[0]

st.number_input(
    "Amount (€)",
    min_value=0.0,
    max_value=MAX_AMOUNT,
    step=0.5,
    format="%.2f",
    key="tx_amount",
)
st.selectbox("Category", categories, key="tx_category")
st.button("Add Transaction", type="primary", on_click=add_transaction)


# ==================== TRANSACTION TABLE ====================
st.subheader("All Transactions")

if df.empty:
    st.info("No transactions yet. Add one above, or import a statement on the Home page.")
else:
    st.dataframe(
        df.sort_values("Date", ascending=False, kind="stable"),
        width="stretch",
        hide_index=True,
        column_config={
            "Date": st.column_config.DateColumn("Date", format="DD/MM/YYYY"),
            "BalanceDate": st.column_config.DateColumn("Value date", format="DD/MM/YYYY"),
            "Expense": st.column_config.NumberColumn("Expense", format="€ %.2f"),
            "Income": st.column_config.NumberColumn("Income", format="€ %.2f"),
            "Accounting Balance": st.column_config.NumberColumn("Accounting Balance", format="€ %.2f"),
            "Balance": st.column_config.NumberColumn("Balance", format="€ %.2f"),
        },
    )