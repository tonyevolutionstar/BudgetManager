import logging

import streamlit as st
from sqlalchemy import text
import pandas as pd

logger = logging.getLogger(__name__)
 
def get_db_connection():
    """Return the Streamlit SQL connection (cached by Streamlit internally)."""
    try:
        return st.connection("neon", type="sql")
    except Exception as e:
        logger.error("Database connection error: %s", e)
        st.error(f"Database connection error: {e}")
        raise

def fetch_query_results(query: str, params: dict | None = None) -> pd.DataFrame:
    """Execute a SELECT query and return results as a DataFrame."""
    conn = get_db_connection()
    try:
        return conn.query(query, params=params)
    except Exception as e:
        logger.error("Query execution error: %s", e)
        st.error(f"Query execution error: {e}")
        raise

def perform_database_operation(query: str, params: dict | None = None):
    """Execute an INSERT / UPDATE / DELETE statement.
 
    The session context manager already rolls back on exception — calling
    session.rollback() manually inside an except block can itself raise
    because the session is already in a rolled-back state.
    """
    conn = get_db_connection()
    try:
        with conn.session as session:
            result = session.execute(text(query), params or {})
            session.commit()
            return result
    except Exception as e:
        # Let the context manager handle rollback; just log and re-raise.
        logger.error("Database operation error: %s", e)
        st.error(f"Database operation error: {e}")
        raise
    
def get_table_columns(table_name: str) -> list[str]:
    """Return the column names of a table."""
    query = "SELECT column_name FROM information_schema.columns WHERE table_name = :table_name"
    df = fetch_query_results(query, params={"table_name": table_name})
    return list(df["column_name"]) if not df.empty else []