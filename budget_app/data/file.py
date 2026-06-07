import pandas as pd
import os

#DATA_FILE = "budget_data.csv"

CSV_COLUMNS = ["Date", "Date_Value", "Description", "Expense", "Income", "Accounting Balance", "Balance", "Category"]

def load_csv_file(file):
    """Load transactions from CSV, return DataFrame or None if file missing/empty."""
    if not os.path.exists(file):
        # Return empty DataFrame with correct columns
        return pd.DataFrame(columns=CSV_COLUMNS) 
    try:
        df = pd.read_csv(file, sep=";", header=0, parse_dates=[0, 1], date_format="%d/%m/%Y", na_values="null")
        return normalize_dataframe(df)
    except Exception:
        return pd.DataFrame(columns=CSV_COLUMNS)

def normalize_dataframe(df):
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