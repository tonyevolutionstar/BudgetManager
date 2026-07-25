import streamlit as st
from sqlalchemy import text
import pandas as pd

def get_db_connection():
    """Get database connection using Streamlit's native connection."""
    try:
        return st.connection("neon", type="sql")
    except Exception as e:
        st.error(f"Database connection error: {str(e)}")
        raise

def fetch_query_results(query, params=None):
    """Execute a query and return results as DataFrame."""
    conn = get_db_connection()
    try:
        return conn.query(query, params=params)
    except Exception as e:
        st.error(f"Query execution error: {str(e)}")
        raise

def perform_database_operation(query, params=None):
    """Execute an insert/update/delete query."""
    conn = get_db_connection()
    try:
        with conn.session as session:
            result = session.execute(text(query), params or {})
            session.commit()
            return result
    except Exception as e:
        st.error(f"Query execution error: {str(e)}")
        conn.session.rollback()
        raise