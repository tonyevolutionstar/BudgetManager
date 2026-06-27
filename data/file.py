import pandas as pd
import tempfile, os
import streamlit as st
from data.bankStatementExtractor import BankStatementExtractor

CSV_COLUMNS = ["Date", "Date_Value", "Description", "Expense", "Income", "Accounting Balance", "Balance", "Category"]
SUPPORTED_TYPES = ["csv", "pdf"]

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
            
            df = pd.DataFrame()
            
            # Skip rows before header
            if skip_rows > 0:
                df = pd.read_csv(
                    file, 
                    sep=";", 
                    skiprows=range(skip_rows),
                    header=0,  # First row after skip becomes header
                    parse_dates=[0, 1],
                    date_format="%d/%m/%Y",
                    na_values="null"
                )
            else:
                # Use specified header row
                df = pd.read_csv(
                    file, 
                    sep=";", 
                    header=header_row,
                    parse_dates=[0, 1],
                    date_format="%d/%m/%Y",
                    na_values="null"
                )
        else:
            # Streamlit UploadedFile object
            df = pd.read_csv(
                file, 
                sep=";", 
                skiprows=range(skip_rows) if skip_rows > 0 else None,
                header=0 if skip_rows > 0 else header_row,
                parse_dates=[0, 1],
                date_format="%d/%m/%Y",
                na_values="null"
            )
        
        return normalize_dataframe(df)
    except Exception as e:
        st.error(f"Error loading CSV: {e}")
        return pd.DataFrame(columns=CSV_COLUMNS)


def normalize_dataframe(df: pd.DataFrame):
    """Normalize DataFrame with better error handling."""
    df = df.copy()
    
    # Use more robust date parsing
    for col in ["Date", "Date_Value"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce", dayfirst=True)
    
    # Use nullable types for numeric columns
    for col in ["Expense", "Income", "Accounting Balance", "Balance"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Float64")
    
    return df

def save_dataframe(df: pd.DataFrame, path: str = "data/csv/transactions.csv"):
    df.to_csv(path, sep=";", index=False, encoding="utf-8-sig")