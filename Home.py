import streamlit as st
import pandas as pd
from datetime import date

from service import FileImporterService
from src.utils import date as dt

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
        "df": pd.DataFrame(),
        "model": None
    }
    for key, default in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default

init_session_state()

# ---------------------------------------------------------------------------
# Main Dashboard
# ---------------------------------------------------------------------------
st.title(":green[:material/money_bag:] Budget Manager")
st.markdown("Manage your budget effectively by categorizing transactions and visualizing spending patterns.")

# ---------------------------------------------------------------------------
# File import
# ---------------------------------------------------------------------------
with st.expander(":material/settings: Import transactions", expanded=True):
    col1, col2 = st.columns(2)
    with col1:
        skip_rows = st.number_input("Rows to skip", min_value=0, max_value=20, value=6, 
        help="CSV only. Lines to discard at the top; the next line is the header.")
    with col2:
        header_row = st.number_input("Header row (0-indexed)", min_value=0, max_value=20, value=6, 
        help="CSV only. Used only when 'Rows to skip' is 0. The row number (0-indexed) that contains the column names.")
    
    uploaded_file = st.file_uploader(
        label="Upload a bank statement (CSV or PDF)",
        type=FileImporterService.SUPPORTED_TYPES,
        accept_multiple_files=False
    )
    
    if st.button(":material/done_outline: Confirm"):
        if uploaded_file is None:
            st.warning("Choose a file to upload before confirming.", icon="⚠️")
        else:
            st.session_state.df = FileImporterService.handle_upload_file(uploaded_file, skip_rows=skip_rows, header_row=header_row)

# ---------------------------------------------------------------------------
# Transaction history (respects the sidebar date filter)
# ---------------------------------------------------------------------------
df, filter_type, start_date, end_date = dt.date_filter(st.session_state.df)
st.header("📜 Transaction History")
st.dataframe(st.session_state.df, width='stretch', hide_index=True)