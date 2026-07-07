import streamlit as st
import pandas as pd
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Now use absolute imports
from src.repository import CategoryRepository, CategoryTypeRepository, SubCategoryRepository

# Page config must be the very first Streamlit call
st.set_page_config(
    page_title="Categories and Subcategories",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="auto"
)

st.title("📊 Categories and Subcategories")

# ==================== INITIALIZATION ====================
def init_session_state():
    """Initialize all session state variables."""
    defaults = {
        "categories_initialized": False,
        "categories_df": pd.DataFrame(),
        "category_types_df": pd.DataFrame(),
        "sub_categories_df": pd.DataFrame(),
        "categoryRepository": None,
        "categoryTypeRepository": None,
        "subCategoryRepository": None,
        "show_create_dialog": False,
        "show_update_dialog": False,
        "show_remove_dialog": False,
        "editing_category": None
    }
    for key, default in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default
    
    # Initialize repositories only once
    if st.session_state.categoryRepository is None:
        st.session_state.categoryRepository = CategoryRepository()
        st.session_state.categoryTypeRepository = CategoryTypeRepository()
        st.session_state.subCategoryRepository = SubCategoryRepository()
    
    # Load data if not already loaded
    if not st.session_state.categories_initialized:
        load_all_data()

def load_all_data():
    """Load all data from repositories."""
    try:
        # Load categories
        categories = st.session_state.categoryRepository.get_all_categories()
        if categories:
            st.session_state.categories_df = pd.DataFrame(categories)
        else:
            st.session_state.categories_df = pd.DataFrame(columns=['id', 'name', 'categoryTypeId', 'color', 'icon', 'threshold'])
        
        # Load category types
        types = st.session_state.categoryTypeRepository.get_category_types()
        if types:
            st.session_state.category_types_df = pd.DataFrame(types)
        else:
            st.session_state.category_types_df = pd.DataFrame(columns=['id', 'name'])
        
        # Load subcategories
        subs = st.session_state.subCategoryRepository.get_sub_categories()
        if subs:
            st.session_state.sub_categories_df = pd.DataFrame(subs)
        else:
            st.session_state.sub_categories_df = pd.DataFrame(columns=['id', 'categoryId', 'name'])
        
        st.session_state.categories_initialized = True
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        st.session_state.categories_df = pd.DataFrame(columns=['id', 'name', 'categoryTypeId', 'color', 'icon', 'threshold'])
        st.session_state.category_types_df = pd.DataFrame(columns=['id', 'name'])
        st.session_state.sub_categories_df = pd.DataFrame(columns=['id', 'categoryId', 'name'])

def get_category_type_name(type_id):
    """Get category type name from ID."""
    if st.session_state.category_types_df.empty:
        return "Unknown"
    result = st.session_state.category_types_df[st.session_state.category_types_df['id'] == type_id]
    if not result.empty:
        return result.iloc[0]['name']
    return "Unknown"

def get_subcategories_for_category(category_id):
    """Get subcategories for a specific category."""
    if st.session_state.sub_categories_df.empty:
        return []
    subs = st.session_state.sub_categories_df[st.session_state.sub_categories_df['categoryId'] == category_id]
    return subs['name'].tolist()

def refresh_data():
    """Refresh all data from database."""
    load_all_data()
    st.rerun()

# Initialize session state
init_session_state()

# ==================== SIDEBAR ====================
st.sidebar.header("🔧 Operations")

# Refresh button
if st.sidebar.button("🔄 Refresh Data", use_container_width=True):
    refresh_data()

st.sidebar.divider()

# Create Category Button
if st.sidebar.button("➕ Create Category", use_container_width=True, type="primary"):
    st.session_state.show_create_dialog = True
    st.rerun()

# Update Category Button
if st.sidebar.button("✏️ Update Category", use_container_width=True):
    if st.session_state.categories_df.empty:
        st.sidebar.warning("No categories to update")
    else:
        st.session_state.show_update_dialog = True
        st.rerun()

# Remove Category Button
if st.sidebar.button("🗑️ Remove Category", use_container_width=True):
    if st.session_state.categories_df.empty:
        st.sidebar.warning("No categories to remove")
    else:
        st.session_state.show_remove_dialog = True
        st.rerun()

st.sidebar.divider()

# Statistics
st.sidebar.subheader("📊 Statistics")
if not st.session_state.categories_df.empty:
    total = len(st.session_state.categories_df)
    st.sidebar.metric("Total Categories", total)
    
    # Count by type
    if 'typeId' in st.session_state.categories_df.columns:
        expense_count = len(st.session_state.categories_df[st.session_state.categories_df['typeId'] == 1])
        income_count = len(st.session_state.categories_df[st.session_state.categories_df['typeId'] == 2])
        st.sidebar.metric("Expenses", expense_count)
        st.sidebar.metric("Incomes", income_count)
else:
    st.sidebar.info("No categories loaded")

# ==================== DIALOGS ====================
@st.dialog("➕ Create New Category")
def create_category_dialog():
    """Dialog for creating new category."""
    with st.form("create_category_form"):
        name = st.text_input("Category Name *", placeholder="e.g., Groceries")
        
        # Get type names for selectbox
        type_names = st.session_state.category_types_df['name'].tolist() if not st.session_state.category_types_df.empty else []
        cat_type = st.selectbox("Category Type *", options=type_names if type_names else ["Expense"])
        
        col1, col2 = st.columns(2)
        with col1:
            color = st.color_picker("Category Color", value="#FF6B6B")
        with col2:
            icon = st.text_input("Icon (emoji)", value="📂", placeholder="e.g., 🍔")
        
        threshold = st.number_input(
            "Threshold (optional)",
            min_value=0.0,
            step=10.0,
            format="%.2f",
            value=0.0
        )
        
        # Buttons
        col1, col2 = st.columns(2)
        with col1:
            submitted = st.form_submit_button("➕ Add Category", use_container_width=True, type="primary")
        with col2:
            canceled = st.form_submit_button("❌ Cancel", use_container_width=True)
        
        if submitted:
            if not name.strip():
                st.warning("⚠️ Please enter a category name")
                return
            
            if not cat_type:
                st.warning("⚠️ Please select a category type")
                return
            
            # Get type ID
            type_id = None
            if not st.session_state.category_types_df.empty:
                type_row = st.session_state.category_types_df[st.session_state.category_types_df['name'] == cat_type]
                if not type_row.empty:
                    type_id = type_row.iloc[0]['id']
            
            if type_id is None:
                st.error("❌ Category type not found")
                return
            
            try:
                # Add category
                success = st.session_state.categoryRepository.add_category(
                    name=name.strip(),
                    typeId=type_id,
                    color=color,
                    icon=icon if icon else "📂",
                    threshold=threshold if threshold > 0 else 0
                )
                
                if success:
                    st.success(f"✅ Category '{name}' created successfully!")
                    refresh_data()
                else:
                    st.error("❌ Failed to create category. It may already exist.")
            except Exception as e:
                st.error(f"❌ Error creating category: {str(e)}")
        
        if canceled:
            st.session_state.show_create_dialog = False
            st.rerun()

@st.dialog("✏️ Update Category")
def update_category_dialog():
    """Dialog for updating category."""
    if st.session_state.categories_df.empty:
        st.warning("No categories available to update")
        if st.button("Close", use_container_width=True):
            st.session_state.show_update_dialog = False
            st.rerun()
        return
    
    # Select category to edit
    category_names = st.session_state.categories_df['name'].tolist()
    selected_name = st.selectbox("Select Category", options=category_names)
    
    if selected_name:
        # Get category data
        category_data = st.session_state.categories_df[st.session_state.categories_df['name'] == selected_name]
        if not category_data.empty:
            category = category_data.iloc[0]
            
            with st.form("update_category_form"):
                name = st.text_input("Category Name *", value=category['name'])
                
                # Get type names
                type_names = st.session_state.category_types_df['name'].tolist() if not st.session_state.category_types_df.empty else []
                current_type = get_category_type_name(category['typeId'])
                cat_type = st.selectbox(
                    "Category Type *",
                    options=type_names if type_names else ["Expense"],
                    index=type_names.index(current_type) if current_type in type_names else 0
                )
                
                col1, col2 = st.columns(2)
                with col1:
                    color = st.color_picker("Category Color", value=category.get('color', '#FF6B6B'))
                with col2:
                    icon = st.text_input("Icon (emoji)", value=category.get('icon', '📂'))
                
                threshold = st.number_input(
                    "Threshold (optional)",
                    min_value=0.0,
                    step=10.0,
                    format="%.2f",
                    value=float(category.get('threshold', 0.0))
                )
                
                col1, col2 = st.columns(2)
                with col1:
                    submitted = st.form_submit_button("💾 Update Category", use_container_width=True, type="primary")
                with col2:
                    canceled = st.form_submit_button("❌ Cancel", use_container_width=True)
                
                if submitted:
                    if not name.strip():
                        st.warning("⚠️ Please enter a category name")
                        return
                    
                    # Get type ID
                    type_id = None
                    if not st.session_state.category_types_df.empty:
                        type_row = st.session_state.category_types_df[st.session_state.category_types_df['name'] == cat_type]
                        if not type_row.empty:
                            type_id = type_row.iloc[0]['id']
                    
                    if type_id is None:
                        st.error("❌ Category type not found")
                        return
                    
                    try:
                        success = st.session_state.categoryRepository.update_category(
                            id=category['id'],
                            name=name.strip(),
                            typeId=type_id,
                            color=color,
                            icon=icon if icon else "📂",
                            threshold=threshold if threshold > 0 else 0
                        )
                        
                        if success:
                            st.success(f"✅ Category '{name}' updated successfully!")
                            refresh_data()
                        else:
                            st.error("❌ Failed to update category")
                    except Exception as e:
                        st.error(f"❌ Error updating category: {str(e)}")
                
                if canceled:
                    st.session_state.show_update_dialog = False
                    st.rerun()

@st.dialog("🗑️ Remove Category")
def remove_category_dialog():
    """Dialog for removing category."""
    if st.session_state.categories_df.empty:
        st.warning("No categories available to remove")
        if st.button("Close", use_container_width=True):
            st.session_state.show_remove_dialog = False
            st.rerun()
        return
    
    # Select category to remove
    category_names = st.session_state.categories_df['name'].tolist()
    selected_name = st.selectbox("Select Category to Remove", options=category_names)
    
    if selected_name:
        category_data = st.session_state.categories_df[st.session_state.categories_df['name'] == selected_name]
        if not category_data.empty:
            category = category_data.iloc[0]
            
            # Show warning
            st.warning(f"⚠️ Are you sure you want to remove '{selected_name}'? This action cannot be undone.")
            
            # Check if category has subcategories
            subcategories = get_subcategories_for_category(category['id'])
            if subcategories:
                st.warning(f"This category has {len(subcategories)} subcategories that will also be removed.")
                with st.expander("View subcategories"):
                    for sub in subcategories:
                        st.write(f"- {sub}")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🗑️ Remove Category", use_container_width=True, type="primary"):
                    try:
                        success = st.session_state.categoryRepository.remove_category(category['id'])
                        if success:
                            st.success(f"✅ Category '{selected_name}' removed successfully!")
                            refresh_data()
                        else:
                            st.error("❌ Failed to remove category")
                    except Exception as e:
                        st.error(f"❌ Error removing category: {str(e)}")
            
            with col2:
                if st.button("❌ Cancel", use_container_width=True):
                    st.session_state.show_remove_dialog = False
                    st.rerun()

# ==================== SHOW DIALOGS ====================
if st.session_state.get('show_create_dialog', False):
    create_category_dialog()

if st.session_state.get('show_update_dialog', False):
    update_category_dialog()

if st.session_state.get('show_remove_dialog', False):
    remove_category_dialog()

# ==================== MAIN CONTENT ====================
st.header("📋 Current Categories")

if st.session_state.categories_df.empty:
    st.info("No categories found. Create your first category using the sidebar!")
else:
    # Display categories as cards
    cols = st.columns(4)
    
    for idx, (_, row) in enumerate(st.session_state.categories_df.iterrows()):
        with cols[idx % 4]:
            with st.container(border=True):
                # Header with icon and name
                icon = row.get('icon', '📂')
                name = row['name']
                st.markdown(f"### {icon} {name}")
                
                # Type badge
                type_name = get_category_type_name(row['typeId'])
                badge_color = "green" if type_name.lower() == "income" else "red"
                st.markdown(f":{badge_color}-badge[{type_name}]")
                
                # Color
                color = row.get('color', '#808080')
                st.color_picker(
                    label="Color",
                    value=color,
                    key=f"color_{row['id']}",
                    disabled=True,
                    label_visibility="collapsed"
                )
                
                # Threshold
                threshold = row.get('threshold', 0.0)
                if threshold > 0:
                    st.metric("Threshold", f"€{threshold:.2f}")
                else:
                    st.caption("No threshold set")
                
                # Subcategories count
                subcategories = get_subcategories_for_category(row['id'])
                if subcategories:
                    st.caption(f"📌 {len(subcategories)} subcategories")
                    with st.expander(f"View subcategories"):
                        for sub in subcategories:
                            st.write(f"- {sub}")
                else:
                    st.caption("No subcategories")
                
                st.markdown("---")
                
                # Quick actions
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✏️ Edit", key=f"edit_{row['id']}", use_container_width=True):
                        st.session_state.editing_category = row['id']
                        st.session_state.show_update_dialog = True
                        st.rerun()
                with col2:
                    if st.button("🗑️", key=f"delete_{row['id']}", use_container_width=True):
                        st.session_state.show_remove_dialog = True
                        # Pre-select this category
                        st.rerun()

# ==================== SUB-CATEGORIES SECTION ====================
st.divider()
st.header("📌 Subcategories")

if not st.session_state.categories_df.empty:
    # Add subcategory
    with st.expander("➕ Add Subcategory", expanded=False):
        col1, col2 = st.columns([2, 1])
        with col1:
            selected_category = st.selectbox(
                "Select Category",
                options=st.session_state.categories_df['name'].tolist(),
                key="sub_category_select"
            )
        with col2:
            new_sub = st.text_input("Subcategory Name", placeholder="e.g., Rent", key="new_sub_name")
        
        if st.button("➕ Add Subcategory", use_container_width=True):
            if new_sub.strip() and selected_category:
                # Get category ID
                cat_data = st.session_state.categories_df[st.session_state.categories_df['name'] == selected_category]
                if not cat_data.empty:
                    category_id = cat_data.iloc[0]['id']
                    try:
                        success = st.session_state.subCategoryRepository.add_sub_category(
                            categoryId=category_id,
                            name=new_sub.strip()
                        )
                        if success:
                            st.success(f"✅ Subcategory '{new_sub}' added to '{selected_category}'")
                            refresh_data()
                        else:
                            st.error("❌ Failed to add subcategory")
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
            else:
                st.warning("⚠️ Please enter a subcategory name")
    
    # Display subcategories
    if not st.session_state.sub_categories_df.empty:
        # Join with categories
        sub_cats = st.session_state.sub_categories_df.merge(
            st.session_state.categories_df[['id', 'name']],
            left_on='categoryId',
            right_on='id',
            suffixes=('_sub', '_cat')
        )
        
        if not sub_cats.empty:
            # Group by category
            for category_name in st.session_state.categories_df['name']:
                category_subs = sub_cats[sub_cats['name_cat'] == category_name]
                if not category_subs.empty:
                    with st.expander(f"📂 {category_name} ({len(category_subs)} subcategories)", expanded=False):
                        for _, sub in category_subs.iterrows():
                            col1, col2 = st.columns([4, 1])
                            with col1:
                                st.write(f"• {sub['name_sub']}")
                            with col2:
                                if st.button("🗑️", key=f"del_sub_{sub['id_sub']}"):
                                    try:
                                        success = st.session_state.subCategoryRepository.remove_sub_category(sub['id_sub'])
                                        if success:
                                            st.success(f"✅ Removed: {sub['name_sub']}")
                                            refresh_data()
                                    except Exception as e:
                                        st.error(f"❌ Error: {str(e)}")
else:
    st.info("Create categories first to add subcategories")
