import streamlit as st
from sqlalchemy import create_engine, engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Create base first
Base = declarative_base()
conn = st.connection("neon", type='sql')
st.write(f"Connection URL: {conn.engine.url}")  # Debugging line to check the connection URL
# Create engine using the connection URL
engine = create_engine(conn.engine.url, echo=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db_connection():
    """Get database connection."""
    class DBConnection:
        def __init__(self):
            self.session = SessionLocal()
        
        def close(self):
            if self.session:
                self.session.close()
    
    return DBConnection()

def init_db():
    """Create all tables."""
    Base.metadata.create_all(bind=engine)
    print("✅ Database initialized successfully")