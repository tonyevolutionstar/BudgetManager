import streamlit as st
import pandas as pd
from datetime import date

from service import FileImporterService
from src.utils import date as dt
from data.database import DatabaseError
from service import CategorizationService as categorizer

st.set_page_config(
    page_title="Budget Manager", 
    page_icon=":material/money_bag:",
    layout="wide",
    initial_sidebar_state="auto"
)

# ---------------------------------------------------------------------------
# Session state initialisation
# ---------------------------------------------------------------------------
def init_session_state():
    defaults = {
        "df": pd.DataFrame(columns=FileImporterService.CSV_COLUMNS),
        "model": None,
        "cat_version": 0
    }
    for key, default in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default

init_session_state()

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
st.title(":green[:material/money_bag:] Budget Manager")
st.markdown("Manage your budget effectively by categorizing transactions and visualizing spending patterns.")

flash = st.session_state.pop("cat_flash", None)
if flash:
    st.success(flash)

# ---------------------------------------------------------------------------
# File import
# ---------------------------------------------------------------------------
with st.expander(":material/settings: Import transactions", expanded=True):
    col1, col2 = st.columns(2)
    with col1:
        skip_rows = st.number_input(
            "Rows to skip", min_value=0, value=6, 
            help="CSV only. Lines to discard at the top; the next line is the header."
        )
    with col2:
        header_row = st.number_input(
            "Header row (0-indexed)", min_value=0, value=6, 
            help="CSV only. Used only when 'Rows to skip' is 0. The row number (0-indexed) that contains the column names."
        )
    
    uploaded_file = st.file_uploader(
        label="Upload a bank statement (CSV or PDF)",
        type=FileImporterService.SUPPORTED_TYPES,
        accept_multiple_files=False
    )
    
    auto_categorise_on_import = st.checkbox(
        "Categorise automatically after import", value=True, key="auto_cat_on_import",
        help="Replaces the bank's own labels (e.g. 'Diversos') with your categories, using keywords in the description.",
    )
    
    if st.button(":material/done_outline: Confirm"):
        if uploaded_file is None:
            st.warning("Choose a file to upload before confirming.", icon="⚠️")
        else:
            before = st.session_state.df
            after = FileImporterService.handle_upload_file(uploaded_file, skip_rows=skip_rows, header_row=header_row)
            st.session_state.df = after
            if auto_categorise_on_import and after is not before: 
                changed = categorizer.auto_categorise_session()
                st.session_state.cat_version += 1
                st.info(f"Automatic categories applied to {changed} of {len(after)} transactions.")

# ---------------------------------------------------------------------------
# Automatic categories: preview, edit, apply
# ---------------------------------------------------------------------------
with st.expander(":material/label: Automatic categories"):
    all_df = st.session_state.df
    if all_df.empty:
        st.caption("Import transactions first.")
    else:
        mode_label = st.radio(
            "Apply to",
            ["Uncategorised only", "All transactions"],
            horizontal=True,
            key="cat_mode",
            help="'Uncategorised only' keeps categories you already chose. 'All' re-evaluates every row and "
                 "overwrites your choices when a keyword matches.",
        )
        mode = "uncategorised" if mode_label == "Uncategorised only" else "all"
 
        extractor = categorizer.get_extractor()
        known = categorizer.get_known_categories(extractor)
        memory, ml = categorizer.get_learned()
        changes = categorizer.suggest_categories(all_df, known, mode, extractor, memory, ml)
 
        if changes.empty:
            st.success("Nothing to change: every transaction already has one of your categories.")
        else:
            st.caption(
                f"{len(changes)} of {len(all_df)} transactions would change. "
                "Edit the **Suggested** column to correct a suggestion before applying. "
                "Your corrections, and the keyword/ML suggestions you accept, are saved so the next suggestions learn from them."
            )
            editor_key = f"cat_editor_{mode}_{len(all_df)}_{st.session_state.cat_version}"
            edited = st.data_editor(
                changes,
                key=editor_key,
                hide_index=True,
                width="stretch",
                disabled=["Row", "Date", "Description", "Current", "Confidence", "Matched"],
                column_config={
                    "Row": None,   # internal: position in the transaction table
                    "Date": st.column_config.DateColumn("Date", format="DD/MM/YYYY"),
                    "Suggested": st.column_config.SelectboxColumn(
                        "Suggested", options=categorizer.category_options(known, extractor), required=True,
                    ),
                    "Confidence": st.column_config.NumberColumn("Confidence", format="%.2f"),
                },
            )
 
            if st.button("Apply categories", type="primary", key="apply_auto_cat"):
                items = categorizer.feedback_items(changes, edited)

                st.session_state.df = categorizer.apply_categories(all_df, edited)
                st.session_state.model = None
                st.session_state.cat_version += 1
                message = f"Categories applied to {len(edited)} transactions."
                try:
                    saved, skipped = categorizer.save_feedback(items)
                    if saved:
                        message += f" {saved} saved for learning."
                    if skipped:
                        message += f" {skipped} not saved (category not in your database)."
                except DatabaseError:
                    message += " The learning could not be saved (database unavailable)."
                st.session_state.cat_flash = message
                st.rerun()
                
    # -- what has been learned: review and forget
    st.divider()
    st.markdown("**Learned corrections**")
    try:
        learned_df = categorizer.list_samples()
    except DatabaseError as e:
        learned_df = None
        st.warning(str(e))
    if learned_df is not None:
        if learned_df.empty:
            st.caption("Nothing learned yet. Corrections and accepted suggestions you apply above are saved here.")
        else:
            st.caption(f"{len(learned_df)} most recent. Tick a row and press **Delete selected** to forget it.")
            view = learned_df.copy()
            view.insert(0, "Delete", False)
            ticked = st.data_editor(
                view,
                key=f"samples_editor_{len(learned_df)}_{st.session_state.cat_version}",
                hide_index=True,
                width="stretch",
                disabled=["description", "category", "source", "created_at"],
                column_config={
                    "id": None,
                    "created_at": st.column_config.DatetimeColumn("Learned at", format="DD/MM/YYYY HH:mm"),
                },
            )
            if st.button("Delete selected", key="delete_samples"):
                ids = ticked.loc[ticked["Delete"], "id"].tolist()
                if not ids:
                    st.warning("Tick the rows to forget first.")
                else:
                    removed = categorizer.delete_samples(ids)
                    st.session_state.cat_version += 1
                    st.session_state.cat_flash = f"Forgot {removed} learned corrections."
                    st.rerun()

# ---------------------------------------------------------------------------
# Transaction history (respects the sidebar date filter)
# ---------------------------------------------------------------------------
df, filter_type, start_date, end_date = dt.date_filter(st.session_state.df)
st.header("📜 Transaction History")
st.dataframe(st.session_state.df, width="stretch", hide_index=True)