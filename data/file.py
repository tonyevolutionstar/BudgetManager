import pandas as pd
import tempfile, os
import streamlit as st
from bankStatementExtractor import BankStatementExtractor

CSV_COLUMNS = ["Date", "Date_Value", "Description", "Expense", "Income", "Accounting Balance", "Balance", "Category"]
SUPPORTED_TYPES = ["csv", "pdf"]

def handle_upload_file(uploaded_file) -> pd.DataFrame:
    mime = uploaded_file.type
    if mime.endswith(SUPPORTED_TYPES[0]):
        st.session_state.df = load_csv_file(uploaded_file)
        st.session_state.model = None
        st.write(st.session_state.df.columns)
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
            for col in file.CSV_COLUMNS:
                if col not in pdf_df.columns:
                    pdf_df[col] = 0.0
            st.session_state.df = file.normalize_dataframe(pdf_df[file.CSV_COLUMNS])
            st.session_state.model = None
            st.success(f"PDF imported: {result['total_transactions']} transactions found.")
        else:
            st.error(result.get("error", "Could not extract transactions from PDF."))
    finally:
        os.unlink(tmp_path)
    return pdf_df

def load_csv_file(file): 
    """
    Load transactions from a CSV source.
    Accepts either a file path string (disk) or a Streamlit UploadedFile object.
    Returns a normalized DataFrame or an empty one if the source is missing/empty.
    """
    try:
        # File path string: check existence before reading
        if isinstance(file, (str, os.PathLike)):
            if not os.path.exists(file):
                return pd.DataFrame(columns=CSV_COLUMNS)
            df = pd.read_csv(file, sep=";", header=0, parse_dates=[0, 1],
                             date_format="%d/%m/%Y", na_values="null")
        else:
            # Streamlit UploadedFile object: read directly
            df = pd.read_csv(file, sep=";", header=0, parse_dates=[0, 1],
                             date_format="%d/%m/%Y", na_values="null")
        return normalize_dataframe(df)
    except Exception:
        return pd.DataFrame(columns=CSV_COLUMNS)

def normalize_dataframe(df: pd.DataFrame):
    """Ensure correct dtypes and fill missing values."""
    # Ensure all required columns exist
    for col in CSV_COLUMNS:
        if col not in df.columns:
            df[col] = 0.0 if col != "Description" else ""
    
    # Date columns
    for col in ["Date", "Date_Value"]:
        df[col] = pd.to_datetime(df[col], errors="coerce", dayfirst=True)
    
    # Numeric columns
    for col in ["Expense", "Income", "Accounting Balance", "Balance"]:
        df[col] = pd.to_numeric(df[col], errors="coerce", downcast=float).fillna(0.0)
    
    # Fill missing descriptions
    df["Description"] = df["Description"].fillna("")
 
    # Fill missing category
    df["Category"] = df["Category"].fillna("Others")
    
    return df