import streamlit as st
import data.database as database

st.set_page_config(
    page_title="Database Info",
    page_icon="🗄️",
    layout="wide"
)

st.header("🗄️ Database Connection Info")

try:
    # Fetch categories
    categories = database.get_categories()
    st.success("✅ Connection successful!")
    
    st.subheader("Categories in Database")
    if not categories.empty:
        st.dataframe(categories, use_container_width=True)
    else:
        st.warning("No categories found in database.")
    
    # Connection details
    st.subheader("Connection Details")
    
except Exception as e:
    st.error(f"❌ Connection failed: {str(e)}")
    st.info("Make sure your `.streamlit/secrets.toml` is configured correctly.")
