import streamlit as st
from enum import Enum
from data.database import execute_query

@st.cache_resource                                 
def get_category(name: str):    
    return execute_query(f"SELECT * FROM Category WHERE Name = {name};")

@st.cache_resource
def get_categories():   
    return execute_query("SELECT * FROM Category;")

@st.cache_resource
def exists_category(name):
    if name in st.session_state.categories:
        return False, f"Category '{name}' already exists."

@st.cache_resource
def add_category(name: str, typeId: int, color: str, icon, threshold, sub_category=""):
    st.session_state.categories[name] = dict(
        Type = type,
        Color = color,
        Icon = icon,
        Threshold = threshold,
    )
    return True, f"Category '{name}' added successfully."

@st.cache_resource
def remove_category( name):
    exists_category(name)
    st.session_state.categories.pop(name)      
    return True, f"Category '{name}' was removed."

@st.cache_resource
def update_threshold(name, new_threshold):
    exists_category(name)
    st.session_state.categories[name]["Threshold"] = new_threshold
    return True, f"Threshold for Category '{name}' was updated to {new_threshold}."

@st.cache_resource
def update_color(self, name, new_color):
    self.exists_category(name)
    st.session_state.categories[name]["Category"] = new_color
    return True, f"Color for Category '{name}' was updated to {new_color}."

@st.cache_resource
def update_icon(self, name, new_icon):
    self.exists_category(name)
    st.session_state.categories[name]["Icon"] = new_icon
    return True, f"Icon for Category' {name}' updated to {new_icon}."

# -------------------------------
# INITIAL DATA (only once)
# -------------------------------
@st.cache_data
def initialize_categories():
    st.write(st.session_state.categories)
    
    st.session_state.sub_categories = {
        "Housing": ["Rent"],
        "Transportation": ["Public Transport", "Uber", "Car payment", "Gas", "Tires",
                           "Maintenance and oil changes", "Parking fees", "Repairs"],
        "Food": ["Groceries", "Restaurants"],
        "Entertainment": ["Movies", "Concerts", "Games", "Bar"],
        "Utilities": ["Electricity and Gas", "Water", "Internet", "Phone"],
        "Healthcare": ["Dental Care", "Urgent Care", "Medications"],
        "Insurance": ["Health insurance", "House"],
        "Personal": ["Gym membership", "Haircut"],
        "Education": ["Tuition", "Books"],
        "Debt": ["Credit cards"],
        "Savings": ["House Repairs"],
        "Gifts": ["Birthday", "Anniversary", "Wedding", "Christmas"],
        "Income": ["Monthly Salary"],
        "Subscriptions": ["Spotify", "Apple"]
    }

    st.session_state.categories_initialized = True
    return st

@st.cache_data
def get_sub_categories(category=None):
    if category:
        return st.session_state.sub_categories.get(category, [])
    return st.session_state.sub_categories

# -------------------------------
# MODIFIER FUNCTIONS
# -------------------------------
@st.cache_data
def add_sub_category(category, sub_category):
    if category not in st.session_state.categories:
        return False, "Category does not exist."
    
    if sub_category in st.session_state.sub_categories.get(category, []):
        return False, "Subcategory already exists."
    
    st.session_state.sub_categories.setdefault(category, []).append(sub_category)
    return True, f"Subcategory '{sub_category}' added to '{category}'."

@st.cache_data
def remove_sub_category(category, sub_category):
    if category not in st.session_state.categories:
        return False, "Category does not exist."
    
    if sub_category not in st.session_state.sub_categories.get(category, []):
        return False, "Subcategory not found."
    
    st.session_state.sub_categories[category].remove(sub_category)
    return True, f"Subcategory '{sub_category}' removed from '{category}'."

