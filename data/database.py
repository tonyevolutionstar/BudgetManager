import streamlit as st
from sqlalchemy import text
import pandas as pd
from streamlit.connections import SQLConnection

@st.cache_resource
def get_db_connection():
    """Create and cache a Neon PostgreSQL connection via Streamlit"""
    return st.connection("neon", type='sql')

def execute_query(query: str) -> pd.DataFrame:
    """Execute a SELECT query and return results as DataFrame"""
    queryData: pd.DataFrame = pd.DataFrame()
    try:
        conn: SQLConnection = get_db_connection()
        queryData = conn.query(query)
    except Exception as e:
        st.error(f"❌ Connection failed: {str(e)}")
        st.info("Make sure your `.streamlit/secrets.toml` is configured correctly.")
    
    return queryData

def execute_update(query: str) -> None:
    """Execute an INSERT, UPDATE, or DELETE query""" 
    try:
    # Fetch categories
        conn = get_db_connection()
        conn.session.execute(text(query))
        conn.session.commit()  
    except Exception as e:
        st.error(f"❌ Connection failed: {str(e)}")
        st.info("Make sure your `.streamlit/secrets.toml` is configured correctly.")
    

def insert_transaction(date, description, amount, category, transaction_type):
    """Insert a new transaction into the database"""
    query = f"""
    INSERT INTO Transactions (date, description, amount, category, type) 
    VALUES ('{date}', '{description}', {amount}, '{category}', '{transaction_type}')
    """
    execute_update(query)

