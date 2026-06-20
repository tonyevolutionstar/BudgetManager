import streamlit as st

# -------------------------------
# INITIAL DATA (only once)
# -------------------------------
def initialize_categories():
    """Initialize all category-related data in session_state."""
    if "categories_initialized" in st.session_state:
        return
    
    st.session_state.categories = [
        "Housing", "Transportation", "Food", "Utilities", "Entertainment",
        "Healthcare", "Insurance", "Personal", "Debt", "Savings", "Gifts",
        "Education", "Income", "Subscriptions", "Others"
    ]
    
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
    
    st.session_state.thresholds = {
        "Housing": 1000.0, "Transportation": 500.0, "Food": 300.0,
        "Utilities": 200.0, "Entertainment": 150.0, "Healthcare": 200.0,
        "Insurance": 300.0, "Personal": 100.0, "Debt": 400.0,
        "Savings": 500.0, "Gifts": 100.0, "Education": 400.0,
        "Subscriptions": 50.0
    }
    
    st.session_state.category_colors = {
        "Housing": "blue", "Transportation": "green", "Food": "orange",
        "Utilities": "purple", "Entertainment": "red", "Healthcare": "pink",
        "Insurance": "cyan", "Personal": "magenta", "Debt": "brown",
        "Savings": "teal", "Gifts": "yellow", "Education": "gray",
        "Income": "black", "Subscriptions": "indigo", "Others": "lightgray"
    }
 
    st.session_state.category_icons = {
        "Housing": "🏠", "Transportation": "🚗", "Food": "🍔",
        "Utilities": "💡", "Entertainment": "🎉", "Healthcare": "💊",
        "Insurance": "🛡️", "Personal": "👤", "Debt": "💳",
        "Savings": "💰", "Gifts": "🎁", "Education": "📚",
        "Income": "💼", "Subscriptions": "📱", "Others": "❓"
    }
    st.session_state.categories_initialized = True

# -------------------------------
# GETTER FUNCTIONS
# -------------------------------
def get_categories():
    return st.session_state.categories

def get_sub_categories(category=None):
    if category:
        return st.session_state.sub_categories.get(category, [])
    return st.session_state.sub_categories

def get_threshold(category):
    return st.session_state.thresholds.get(category)

def get_all_thresholds():
    return st.session_state.thresholds

def get_category_color(category):
    return st.session_state.category_colors.get(category, "gray")

def get_category_icon(category):
    return st.session_state.category_icons.get(category, "❓")

def get_all_category_data():
    """Return a dict with all info for each category."""
    data = {}
    for cat in st.session_state.categories:
        data[cat] = {
            "subcategories": st.session_state.sub_categories.get(cat, []),
            "color": st.session_state.category_colors.get(cat, "gray"),
            "icon": st.session_state.category_icons.get(cat, "❓"),
            "threshold": st.session_state.thresholds.get(cat, None)
        }
    return data

# -------------------------------
# MODIFIER FUNCTIONS
# -------------------------------
def add_category(category, sub_category=""):
    """Add new category with optional initial subcategory."""
    if category in st.session_state.categories:
        return False, f"Category '{category}' already exists."
    
    st.session_state.categories.append(category)
    st.session_state.sub_categories[category] = [sub_category] if sub_category else []
    st.session_state.thresholds[category] = None
    st.session_state.category_colors[category] = "gray"
    st.session_state.category_icons[category] = "❓"
    return True, f"Category '{category}' added successfully."

def remove_category(category):
    if category not in st.session_state.categories:
        return False, "Category not found."
    
    st.session_state.categories.remove(category)
    st.session_state.sub_categories.pop(category, None)
    st.session_state.thresholds.pop(category, None)
    st.session_state.category_colors.pop(category, None)
    st.session_state.category_icons.pop(category, None)
    return True, f"Category '{category}' removed."

def add_sub_category(category, sub_category):
    if category not in st.session_state.categories:
        return False, "Category does not exist."
    
    if sub_category in st.session_state.sub_categories.get(category, []):
        return False, "Subcategory already exists."
    
    st.session_state.sub_categories.setdefault(category, []).append(sub_category)
    return True, f"Subcategory '{sub_category}' added to '{category}'."

def remove_sub_category(category, sub_category):
    if category not in st.session_state.categories:
        return False, "Category does not exist."
    
    if sub_category not in st.session_state.sub_categories.get(category, []):
        return False, "Subcategory not found."
    
    st.session_state.sub_categories[category].remove(sub_category)
    return True, f"Subcategory '{sub_category}' removed from '{category}'."

def update_threshold(category, new_threshold):
    if category not in st.session_state.categories:
        return False, "Category not found."
    
    st.session_state.thresholds[category] = new_threshold
    return True, f"Threshold for '{category}' updated to {new_threshold}."

def update_color(category, new_color):
    if category not in st.session_state.categories:
        return False, "Category not found."
    
    st.session_state.category_colors[category] = new_color
    return True, f"Color for '{category}' updated to {new_color}."

def update_icon(category, new_icon):
    if category not in st.session_state.categories:
        return False, "Category not found."
    
    st.session_state.category_icons[category] = new_icon
    return True, f"Icon for '{category}' updated to {new_icon}."