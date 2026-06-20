# src/data/category_loader.py
import pandas as pd
import streamlit as st
from pathlib import Path
from .csv_handler import get_csv_handler

class CategoryDataLoader:
    """Load category data from CSV files into session state using ; separator"""
    
    def __init__(self):
        self.handler = get_csv_handler()
        self.categories_file = "categories.csv"
        self.subcategories_file = "subcategories.csv"
        
    def load_into_session_state(self):
        """Load all category data from CSV into st.session_state"""
        
        # Load categories
        categories_df = self.handler.read_csv(self.categories_file)
        
        if not categories_df.empty:
            # Convert to lists and dictionaries
            st.session_state.categories = categories_df['name'].tolist()
            
            # Create thresholds dictionary (convert NaN to 0)
            st.session_state.thresholds = {}
            for _, row in categories_df.iterrows():
                threshold = row['threshold']
                if pd.isna(threshold) or threshold == "":
                    st.session_state.thresholds[row['name']] = 0.0
                else:
                    st.session_state.thresholds[row['name']] = float(threshold)
            
            # Create colors dictionary
            st.session_state.category_colors = dict(zip(
                categories_df['name'], 
                categories_df['color'].tolist()
            ))
            
            # Create icons dictionary
            st.session_state.category_icons = dict(zip(
                categories_df['name'], 
                categories_df['icon'].tolist()
            ))
        else:
            # Initialize with defaults if file doesn't exist
            self._initialize_default_categories()
        
        # Load subcategories
        subcategories_df = self.handler.read_csv(self.subcategories_file)
        
        if not subcategories_df.empty:
            # Group subcategories by category
            st.session_state.sub_categories = {}
            for category in st.session_state.categories:
                subs = subcategories_df[
                    subcategories_df['category_name'] == category
                ]['subcategory_name'].tolist()
                if subs:
                    st.session_state.sub_categories[category] = subs
        else:
            self._initialize_default_subcategories()
    
    def _initialize_default_categories(self):
        """Initialize default categories from hardcoded data"""
        
        categories_data = {
            "id": list(range(1, 16)),
            "name": ["Housing", "Transportation", "Food", "Utilities", "Entertainment",
                    "Healthcare", "Insurance", "Personal", "Debt", "Savings", "Gifts",
                    "Education", "Income", "Subscriptions", "Others"],
            "type": ["expense", "expense", "expense", "expense", "expense",
                    "expense", "expense", "expense", "expense", "expense", "expense",
                    "expense", "income", "expense", "expense"],
            "parent_category": [""] * 15,
            "color": ["blue", "green", "orange", "purple", "red",
                     "pink", "cyan", "magenta", "brown", "teal", "yellow",
                     "gray", "black", "indigo", "lightgray"],
            "icon": ["🏠", "🚗", "🍔", "💡", "🎉",
                    "💊", "🛡️", "👤", "💳", "💰", "🎁",
                    "📚", "💼", "📱", "❓"],
            "threshold": [1000.0, 500.0, 300.0, 200.0, 150.0,
                         200.0, 300.0, 100.0, 400.0, 500.0, 100.0,
                         400.0, None, 50.0, None],
            "is_active": [1] * 15,
            "created_at": ["2024-01-01 00:00:00"] * 15
        }
        
        df = pd.DataFrame(categories_data)
        self.handler.write_csv(self.categories_file, df)
        
        # Set session state
        st.session_state.categories = df['name'].tolist()
        st.session_state.thresholds = dict(zip(df['name'], df['threshold'].fillna(0).tolist()))
        st.session_state.category_colors = dict(zip(df['name'], df['color'].tolist()))
        st.session_state.category_icons = dict(zip(df['name'], df['icon'].tolist()))
    
    def _initialize_default_subcategories(self):
        """Initialize default subcategories"""
        
        # Get category IDs
        categories_df = self.handler.read_csv(self.categories_file)
        category_id_map = dict(zip(categories_df['name'], categories_df['id']))
        
        subcategories_data = {
            "id": list(range(1, 38)),
            "category_id": [
                1, 2, 2, 2, 2, 2, 2, 2, 2, 3, 3, 5, 5, 5, 5, 4, 4, 4, 4,
                6, 6, 6, 7, 7, 8, 8, 12, 12, 9, 10, 11, 11, 11, 11, 13, 14, 14
            ],
            "category_name": [
                "Housing", "Transportation", "Transportation", "Transportation",
                "Transportation", "Transportation", "Transportation", "Transportation",
                "Transportation", "Food", "Food", "Entertainment", "Entertainment",
                "Entertainment", "Entertainment", "Utilities", "Utilities", "Utilities",
                "Utilities", "Healthcare", "Healthcare", "Healthcare", "Insurance",
                "Insurance", "Personal", "Personal", "Education", "Education", "Debt",
                "Savings", "Gifts", "Gifts", "Gifts", "Gifts", "Income", "Subscriptions",
                "Subscriptions"
            ],
            "subcategory_name": [
                "Rent", "Public Transport", "Uber", "Car payment", "Gas", "Tires",
                "Maintenance and oil changes", "Parking fees", "Repairs", "Groceries",
                "Restaurants", "Movies", "Concerts", "Games", "Bar", "Electricity and Gas",
                "Water", "Internet", "Phone", "Dental Care", "Urgent Care", "Medications",
                "Health insurance", "House", "Gym membership", "Haircut", "Tuition",
                "Books", "Credit cards", "House Repairs", "Birthday", "Anniversary",
                "Wedding", "Christmas", "Monthly Salary", "Spotify", "Apple"
            ],
            "is_active": [1] * 37
        }
        
        df = pd.DataFrame(subcategories_data)
        self.handler.write_csv(self.subcategories_file, df)
        
        # Set session state
        st.session_state.sub_categories = {}
        for category in st.session_state.categories:
            subs = df[df['category_name'] == category]['subcategory_name'].tolist()
            if subs:
                st.session_state.sub_categories[category] = subs