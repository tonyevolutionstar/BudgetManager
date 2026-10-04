from __future__ import annotations

import io
import logging
import os
from pathlib import Path

import pandas as pd
import pdfplumber
import streamlit as st

from data.bankStatementExtractor import BankStatementExtractor
import src.utils.date as dateUtils

logger = logging.getLogger(__name__)

CSV_COLUMNS = ["Date", "BalanceDate", "Description", "Expense", "Income",
               "Accounting Balance", "Balance", "Category"]
SUPPORTED_TYPES = ["csv", "pdf"]
NUMERIC_COLUMNS = ["Expense", "Income", "Accounting Balance", "Balance"]
DEFAULT_CATEGORY = "Others"
DEFAULT_CSV_PATH = Path("data/csv/transactions.csv")

MAX_UPLOAD_BYTES = 10 * 1024 * 1024   # also set server.maxUploadSize in .streamlit/config.toml
MAX_PDF_PAGES = 50

class StatementImportError(Exception):
    """A problem with the uploaded file that is safe to show to the user."""
    
# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------

def _file_extension(name: str) -> str:
    return Path(name).suffix.lower().lstrip(".")


def _read_bytes(file) -> bytes:
    """Read an uploaded file (or a path) into bytes, enforcing the size limit."""
    if isinstance(file, (str, os.PathLike)):
        path = Path(file)
        if not path.exists():
            raise StatementImportError("File not found.")
        if path.stat().st_size > MAX_UPLOAD_BYTES:
            raise StatementImportError(f"File is too large (max {MAX_UPLOAD_BYTES // (1024 * 1024)} MB).")
        raw = path.read_bytes()
    else:
        raw = file.getvalue() if hasattr(file, "getvalue") else file.read()
    if not raw:
        raise StatementImportError("The file is empty.")
    if len(raw) > MAX_UPLOAD_BYTES:
        raise StatementImportError(f"File is too large (max {MAX_UPLOAD_BYTES // (1024 * 1024)} MB).")
    return raw


def _decode(raw: bytes) -> str:
    """UTF-8 (with or without BOM) first, then latin-1 (typical for Portuguese bank exports)."""
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return raw.decode("latin-1")


def _parse_numbers(series: pd.Series) -> pd.Series:
    """Parse '1.234,56' (PT) and '1234.56' alike; blanks and junk become 0.0."""
    if pd.api.types.is_numeric_dtype(series):
        return series.fillna(0.0).astype(float)
    s = series.astype("string").str.replace("[\\s\u00a0]", "", regex=True)
    portuguese = s.str.contains(",", na=False)  # a comma means PT format: '.' is the thousands separator
    s = s.where(~portuguese, s.str.replace(".", "", regex=False).str.replace(",", ".", regex=False))
    return pd.to_numeric(s, errors="coerce").fillna(0.0).astype(float)


def _parse_dates(series: pd.Series) -> pd.Series:
    """Parse dd/mm/yyyy first, then fall back to other day-first formats. Unparseable -> NaT."""
    if pd.api.types.is_datetime64_any_dtype(series):
        return series
    s = series.astype("string").str.strip()
    parsed = pd.to_datetime(s, format=dateUtils.DATE_FORMAT_FILE, errors="coerce")
    missing = parsed.isna() & s.notna()
    if missing.any():
        parsed.loc[missing] = pd.to_datetime(s[missing], dayfirst=True, errors="coerce", format="mixed")
    return parsed


def _finalise(df: pd.DataFrame) -> pd.DataFrame:
    """Coerce a DataFrame with CSV_COLUMNS to the app's types and drop non-transaction rows."""
    out = df[CSV_COLUMNS].copy()
    out["Date"] = _parse_dates(out["Date"])
    out["BalanceDate"] = _parse_dates(out["BalanceDate"])
    out = out[out["Date"].notna()]  # footers, totals and blank lines have no valid date

    for col in NUMERIC_COLUMNS:
        out[col] = _parse_numbers(out[col])

    out["Description"] = out["Description"].fillna("").astype(str).str.strip()
    category = out["Category"].fillna("").astype(str).str.strip().str.capitalize()
    out["Category"] = category.where(category != "", DEFAULT_CATEGORY)
    return out.reset_index(drop=True)

# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def load_csv_file(file, skip_rows: int = 0, header_row: int = 0) -> pd.DataFrame:
    """Load a semicolon-separated bank export.

    If skip_rows > 0 the first skip_rows lines are discarded and the next line
    is the header (header_row is ignored); otherwise header_row picks the header
    line. This is the behaviour the old loader had, written down.
    """
    text = _decode(_read_bytes(file))
    try:
        raw = pd.read_csv(
            io.StringIO(text),
            sep=";",
            skiprows=range(skip_rows) if skip_rows > 0 else None,
            header=0 if skip_rows > 0 else header_row,
            dtype=str,
        )
    except (pd.errors.ParserError, pd.errors.EmptyDataError) as exc:
        logger.warning("CSV parse error: %s", exc)
        raise StatementImportError("Could not parse the CSV. Check 'rows to skip' / 'header row'.") from exc

    # A trailing ';' on every line produces an empty "Unnamed: n" column: drop trailing ones only.
    while raw.shape[1] and str(raw.columns[-1]).startswith("Unnamed") and raw.iloc[:, -1].isna().all():
        raw = raw.iloc[:, :-1]

    raw = raw.iloc[:, :len(CSV_COLUMNS)]
    raw.columns = CSV_COLUMNS[:raw.shape[1]]
    if "Category" not in raw.columns:
        raw["Category"] = ""

    df = _finalise(raw)
    if df.empty:
        raise StatementImportError("No valid transactions found. Check 'rows to skip' / 'header row'.")
    return df


def load_pdf_file(file) -> pd.DataFrame:
    """Load transactions from a PDF statement using BankStatementExtractor."""
    stream = io.BytesIO(_read_bytes(file))

    try:
        with pdfplumber.open(stream) as pdf:
            if len(pdf.pages) > MAX_PDF_PAGES:
                raise StatementImportError(f"PDF has too many pages (max {MAX_PDF_PAGES}).")
    except StatementImportError:
        raise
    except Exception as exc:
        logger.exception("Could not open PDF")
        raise StatementImportError("Could not read this PDF.") from exc
    stream.seek(0)

    result = BankStatementExtractor().process_statement(stream.name)
    if "error" in result or not result.get("transactions"):
        raise StatementImportError(result.get("error", "Could not extract transactions from the PDF."))

    t = pd.DataFrame(result["transactions"])
    df = pd.DataFrame({
        "Date": t["date"],
        "BalanceDate": t["date"],
        "Description": t["description"],
        "Expense": t["debit"],
        "Income": t["credit"],
        "Accounting Balance": t["credit"] - t["debit"],
        "Balance": t["balance"],
        "Category": t["category"],
    })
    df = _finalise(df)
    if df.empty:
        raise StatementImportError("No valid transactions found in the PDF.")
    return df

def handle_upload_file(uploaded_file, skip_rows: int, header_row: int) -> pd.DataFrame:
    """Route the uploaded file to the right loader and update session state.

    On failure the transactions already loaded are kept and returned unchanged.
    """
    current = st.session_state.get("df", pd.DataFrame(columns=CSV_COLUMNS))
    extension = _file_extension(uploaded_file.name)

    try:
        if extension == "csv":
            df = load_csv_file(uploaded_file, skip_rows=skip_rows, header_row=header_row)
        elif extension == "pdf":
            df = load_pdf_file(uploaded_file)
        else:
            st.error(f"Unsupported file type '.{extension}'. Upload a CSV or PDF.")
            return current
    except StatementImportError as exc:
        st.error(str(exc))
        return current
    except Exception:
        logger.exception("Unexpected error importing %s file", extension)
        st.error("Something went wrong reading this file. Check that it is a valid bank statement.")
        return current

    st.session_state.df = df
    st.session_state.model = None  # force the classifier to retrain
    st.success(f"Imported {len(df)} transactions.")
    if extension == "pdf":
        st.warning(
            "PDF parsing is heuristic: review the amounts, and note that Balance is a running "
            "total of the imported rows, not the bank's balance."
        )
    return df


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def search_last_column_fast(df: pd.DataFrame, search_text: str) -> pd.DataFrame:
    """Rows whose last column contains search_text (plain text match, not a regex)."""
    mask = df.iloc[:, -1].astype(str).str.contains(search_text, case=False, na=False, regex=False)
    return df.loc[mask]


def save_dataframe(df: pd.DataFrame, path: str | os.PathLike = DEFAULT_CSV_PATH) -> None:
    """Write the transactions to CSV (creates the folder, replaces the file atomically).

    NOTE: this file contains your financial data. Keep data/csv/ out of git.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    df.to_csv(tmp, sep=";", index=False, encoding="utf-8-sig", date_format=dateUtils.DATE_FORMAT_FILE)
    os.replace(tmp, path)