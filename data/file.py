import pandas as pd
import tempfile, os
from pdfplumber.convert import CSV_COLS_TO_PREPEND
import streamlit as st
from data.bankStatementExtractor import BankStatementExtractor
import src.utils.date as dateUtils
from googletrans import Translator

CSV_COLUMNS = ["Date", "BalanceDate", "Description", "Expense", "Income", "Accounting Balance", "Balance", "Category"]
SUPPORTED_TYPES = ["csv", "pdf"]

@st.cache_resource
def handle_upload_file(uploaded_file, skip_rows: int, header_row: int) -> pd.DataFrame:
    mime = uploaded_file.type
    if mime.endswith(SUPPORTED_TYPES[0]):
        st.session_state.df = load_csv_file(uploaded_file, skip_rows=skip_rows, header_row=header_row)
        st.session_state.model = None
    elif mime.endswith(SUPPORTED_TYPES[1]):
        st.session_state.df = load_pdf_file(uploaded_file)
    
    return st.session_state.df

def load_pdf_file(file) -> pd.DataFrame:
    extractor = BankStatementExtractor()
    pdf_df = pd.DataFrame()
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(file.read())
            tmp_path = tmp.name
    try:
        result = extractor.process_statement(tmp_path)
        if "error" not in result and result.get("transactions"):
            pdf_df = pd.DataFrame(result["transactions"])
            # Map extractor column names → app column names
            pdf_df = pdf_df.rename(columns={
                "date": "Date",
                "description": "Description",
                "debit": "Expense",
                "credit": "Income",
                "balance": "Balance",
                "category": "Category",
            })
            pdf_df["Date_Value"] = pdf_df["Date"]
            pdf_df["Accounting Balance"] = pdf_df["Income"] - pdf_df["Expense"]
            for col in CSV_COLUMNS:
                if col not in pdf_df.columns:
                    pdf_df[col] = 0.0
            st.session_state.df = normalize_dataframe(pdf_df[CSV_COLUMNS])
            st.session_state.model = None
            st.success(f"PDF imported: {result['total_transactions']} transactions found.")
        else:
            st.error(result.get("error", "Could not extract transactions from PDF."))
    finally:
        os.unlink(tmp_path)
    return pdf_df

@st.cache_resource
def load_csv_file(file, skip_rows: int, header_row: int) -> pd.DataFrame:
    """
    Load transactions from a CSV source with configurable skip and header rows.
    
    Args:
        file: File path or Streamlit UploadedFile
        skip_rows: Number of rows to skip from the top (default: 6)
        header_row: Row index to use as header (0-indexed, default: 6)
    """
    try:
        # File path string
        if isinstance(file, (str, os.PathLike)):
            if not os.path.exists(file):
                return pd.DataFrame(columns=CSV_COLUMNS)
            
            # Skip rows before header
            if skip_rows > 0:
                st.session_state.df = pd.read_csv(
                    file, 
                    sep=";", 
                    skiprows=range(skip_rows),
                    header=0,  # First row after skip becomes header
                    parse_dates=[0, 1],
                    date_format=dateUtils.DATE_FORMAT_FILE,
                    na_values=['', ' '],
                    encoding='latin1'
                )
            else:
                # Use specified header row
                st.session_state.df = pd.read_csv(
                    file, 
                    sep=";", 
                    header=header_row,
                    parse_dates=[0, 1],
                    date_format=dateUtils.DATE_FORMAT_FILE,
                    na_values=['', ' '],
                    encoding='latin1'
                )
        else:
            # Streamlit UploadedFile object
            st.session_state.df = pd.read_csv(
                file, 
                sep=";", 
                skiprows=range(skip_rows) if skip_rows > 0 else None,
                header=0 if skip_rows > 0 else header_row,
                parse_dates=[0, 1],
                date_format=dateUtils.DATE_FORMAT_FILE,
                na_values=['', ' '],
                encoding='latin1'
            )
        return normalize_dataframe(df=st.session_state.df)
    except Exception as e:
        st.error(f"Error loading CSV: {e}")
        return pd.DataFrame(columns=CSV_COLUMNS)

@st.cache_resource
def normalize_dataframe(df: pd.DataFrame, src_lang="pt", det_lang="en"):
    """Normalize DataFrame with better error handling."""
    # Exclude last column
    df = df.iloc[:, :-1]
    # Exclude last row
    df = df.iloc[:-1, :]

    df = df.rename(columns={
        df.columns[0]: CSV_COLUMNS[0],
        df.columns[1]: CSV_COLUMNS[1],
        df.columns[2]: CSV_COLUMNS[2],
        df.columns[3]: CSV_COLUMNS[3],
        df.columns[4]: CSV_COLUMNS[4],
        df.columns[5]: CSV_COLUMNS[5],
        df.columns[6]: CSV_COLUMNS[6],
        df.columns[7]: CSV_COLUMNS[7]
    })
    
    df.columns = df.columns.str.strip()
    # Use more robust date parsing
    for col in [df.columns[0], df.columns[1]]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce", dayfirst=True)
    
    # Use nullable types for numeric columns
    for col in [df.columns[3], df.columns[4], df.columns[5], df.columns[6]]:
        df[col] = df[col].str.replace(".", "").str.replace(",", ".").astype(float).fillna(0.0)

    df[-1] = df[-1].str.capitalize()
    return df


def search_last_column_fast(df, search_text):
    """
    Optimized search for large DataFrames.
    """
    # Use vectorized string operations
    last_col = df.iloc[:, -1]
    
    # Convert to string only once
    str_col = last_col.astype(str)
    
    # Use .str.contains with vectorized operations
    mask = str_col.str.contains(search_text, case=False, na=False)
    
    # Use .loc for efficient filtering
    return df.loc[mask]

# For very large DataFrames, consider using .query()
def search_last_column_query(df, search_text):
    """Using query for better performance with large datasets."""
    last_col = df.columns[-1]
    query_str = f"`{last_col}`.astype(str).str.contains('{search_text}')"
    return df.query(query_str)

def set_category(df):
    df= search_last_column_query(df, "Diversos")
        
def save_dataframe(df: pd.DataFrame, path: str = "data/csv/transactions.csv"):
    df.to_csv(path, sep=";", index=False, encoding="utf-8-sig")