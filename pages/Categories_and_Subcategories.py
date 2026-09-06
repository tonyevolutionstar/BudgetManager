import streamlit as st
import pandas as pd
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
        # Define column names for consistency
        category_columns = st.session_state.categoryRepository.columns
        type_columns = st.session_state.categoryTypeRepository.columns
        sub_columns = st.session_state.subCategoryRepository.columns
        
        # Load categories
        categories = st.session_state.categoryRepository.get_all_categories()
        if categories and len(categories) > 0:
            st.session_state.categories_df = pd.DataFrame(categories)
        else:
            st.session_state.categories_df = pd.DataFrame(columns=category_columns)
        
        # Load category types
        types = st.session_state.categoryTypeRepository.get_category_types()
        if types and len(types) > 0:
            st.session_state.category_types_df = pd.DataFrame(types)
        else:
            st.session_state.category_types_df = pd.DataFrame(columns=type_columns)
        
        # Load subcategories
        subs = st.session_state.subCategoryRepository.get_sub_categories()
        if subs and len(subs) > 0:
            st.session_state.sub_categories_df = pd.DataFrame(subs)
        else:
            st.session_state.sub_categories_df = pd.DataFrame(columns=sub_columns)
        
        st.session_state.categories_initialized = True
        st.success("✅ Data loaded successfully!")
        
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        # Initialize empty DataFrames with proper columns
        st.session_state.categories_df = pd.DataFrame(columns=st.session_state.categoryRepository.columns)
        st.session_state.category_types_df = pd.DataFrame(columns=st.session_state.categoryTypeRepository.columns)
        st.session_state.sub_categories_df = pd.DataFrame(columns=st.session_state.subCategoryRepository.columns)

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
    subs = st.session_state.sub_categories_df[st.session_state.sub_categories_df['categoryid'] == category_id]
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
if st.sidebar.button("➕ New Category", use_container_width=True, type="primary"):
    st.session_state.show_create_dialog = True
    
# Create SubCategory Button
if st.sidebar.button("➕ New SubCategory", use_container_width=True, type="primary"):
    st.session_state.show_create_subcategory_dialog = True

# ==================== DIALOGS ====================
@st.dialog("➕ New Category")
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
                success, message = st.session_state.categoryRepository.add_category(
                    name=name.strip(),
                    categoryTypeId=type_id,
                    color=color,
                    icon=icon if icon else "📂",
                    threshold=threshold if threshold > 0 else 0
                )
                
                if success:
                    st.success(f"✅ {message}")
                    refresh_data()
                else:
                    st.error(f"❌ {message}")
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
                
                # Get current type
                current_type_id = category.get('categoryTypeId')
                current_type_name = get_category_type_name(current_type_id) if current_type_id else "Expense"
                
                # Ensure current_type_name is in type_names
                if current_type_name not in type_names and type_names:
                    current_type_name = type_names[0] if type_names else "Expense"
                
                cat_type = st.selectbox(
                    "Category Type *",
                    options=type_names if type_names else ["Expense"],
                    index=type_names.index(current_type_name) if current_type_name in type_names else 0
                )
                
                col1, col2 = st.columns(2)
                with col1:
                    color = st.color_picker("Color")
                with col2:
                    icon = st.text_input("Icon (emoji)")
                
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
                        success, message = st.session_state.categoryRepository.update_category(
                            id=category['id'],
                            name=name,
                            categoryTypeId=type_id,
                            color=color,
                            icon=icon,
                            threshold=threshold if threshold > 0 else 0
                        )
                        
                        if success:
                            st.success(f"✅ {message}")
                            refresh_data()
                        else:
                            st.error(f"❌ {message}")
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

@st.dialog("➕ New SubCategory")
def create_subcategory_dialog():
    """Dialog for creating new category."""
    with st.form("create_sub_category_form"):
        col1, col2 = st.columns(2)
        with col1:
            selected_category = st.selectbox(
                "Select Category",
                options=st.session_state.categories_df['name'].tolist(),
                key="sub_category_select"
            )        
        with col2:    
            new_sub = st.text_input("Subcategory Name", placeholder="e.g., Rent", key="new_sub_name")

        # Buttons
        col1, col2 = st.columns(2)
        with col1:
            submitted = st.form_submit_button("✅ Confirm", use_container_width=True, type="primary")
        with col2:
            canceled = st.form_submit_button("❌ Cancel", use_container_width=True)
        
        if submitted:
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
        
        if canceled:
            st.session_state.show_create_subcategory_dialog = False
            st.rerun()

# ==================== SHOW DIALOGS ====================
if st.session_state.get('show_create_dialog', False):
    create_category_dialog()

if st.session_state.get('show_update_dialog', False):
    update_category_dialog()

if st.session_state.get('show_remove_dialog', False):
    remove_category_dialog()
    
if st.session_state.get('show_create_subcategory_dialog', False):
    create_subcategory_dialog()

# ==================== MAIN CONTENT ====================
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
                name = row.get('name', 'Unknown')
                st.markdown(f"### {icon} {name}")
                
                # Type badge
                type_id = row['categorytypeid']
                type_name = get_category_type_name(type_id) if type_id else "Unknown"
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
                    for sub in subcategories:
                        st.badge(f"{sub}")
                else:
                    st.caption("No subcategories")
                                
                # Quick actions
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✏️ Edit", key=f"edit_{row['id']}", use_container_width=True):
                        st.session_state.editing_category = row['id']
                        st.session_state.show_update_dialog = True
                        st.rerun()
                with col2:
                    if st.button("🗑️ Remove", key=f"delete_{row['id']}", use_container_width=True):
                        st.session_state.show_remove_dialog = True
                        st.rerun()