import pandas as pd
import streamlit as st

from data.database import DatabaseError
from src.repository import CategoryRepository, CategoryTypeRepository, SubCategoryRepository

# Page config must be the very first Streamlit call
st.set_page_config(
    page_title="Categories and Subcategories",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="auto",
)

st.title("📊 Categories and Subcategories")

# PostgreSQL returns lowercase column names
CATEGORY_COLS = ["id", "name", "categorytypeid", "color", "icon", "monthlybudget"]
TYPE_COLS = ["id", "name"]
SUB_COLS = ["id", "name", "categoryid"]
TYPE_BADGE_COLORS = {"income": "green", "expense": "red", "transfer": "blue"}


# ==================== STATE & DATA ====================
def load_all_data():
    """Load categories, types and subcategories into session state."""
    ss = st.session_state
    try:
        ss.categories_df = pd.DataFrame(ss.categoryRepository.get_all_categories(), columns=CATEGORY_COLS)
        ss.category_types_df = pd.DataFrame(ss.categoryTypeRepository.get_category_types(), columns=TYPE_COLS)
        ss.sub_categories_df = pd.DataFrame(ss.subCategoryRepository.get_sub_categories(), columns=SUB_COLS)
        ss.categories_initialized = True
    except DatabaseError as e:
        st.error(str(e))
        ss.categories_df = pd.DataFrame(columns=CATEGORY_COLS)
        ss.category_types_df = pd.DataFrame(columns=TYPE_COLS)
        ss.sub_categories_df = pd.DataFrame(columns=SUB_COLS)


def init_session_state():
    ss = st.session_state
    defaults = {
        "categories_initialized": False,
        "categories_df": pd.DataFrame(columns=CATEGORY_COLS),
        "category_types_df": pd.DataFrame(columns=TYPE_COLS),
        "sub_categories_df": pd.DataFrame(columns=SUB_COLS),
        "categoryRepository": None,
        "categoryTypeRepository": None,
        "subCategoryRepository": None,
    }
    for key, default in defaults.items():
        if key not in ss:
            ss[key] = default

    # Other pages share these repositories through session state
    if ss.categoryRepository is None:
        ss.categoryRepository = CategoryRepository()
    if ss.categoryTypeRepository is None:
        ss.categoryTypeRepository = CategoryTypeRepository()
    if ss.subCategoryRepository is None:
        ss.subCategoryRepository = SubCategoryRepository()

    if not ss.categories_initialized:
        load_all_data()


def refresh_data():
    """Reload from the database and rerun (this also closes any open dialog)."""
    load_all_data()
    st.rerun()


def flash(kind: str, message: str):
    """Show a message after the next rerun (a dialog's own messages vanish when it closes)."""
    st.session_state.flash = (kind, message)


def show_flash():
    pending = st.session_state.pop("flash", None)
    if pending:
        getattr(st, pending[0])(pending[1])


def get_category_type_name(type_id) -> str:
    df = st.session_state.category_types_df
    match = df[df["id"] == type_id]
    return match.iloc[0]["name"] if not match.empty else "Unknown"


def get_type_id(type_name: str):
    df = st.session_state.category_types_df
    match = df[df["name"] == type_name]
    return int(match.iloc[0]["id"]) if not match.empty else None


def get_category(category_id: int):
    df = st.session_state.categories_df
    match = df[df["id"] == category_id]
    return match.iloc[0] if not match.empty else None


def get_subcategories_for_category(category_id) -> list[str]:
    df = st.session_state.sub_categories_df
    return df[df["categoryid"] == category_id]["name"].tolist()


init_session_state()
show_flash()


# ==================== DIALOGS ====================
# Dialogs are opened directly from button clicks (no show_* flags), so they
# no longer reopen after a successful save. st.rerun() closes them.

@st.dialog("➕ New Category")
def create_category_dialog():
    type_names = st.session_state.category_types_df["name"].tolist()
    if not type_names:
        st.error("No category types found in the database.")
        return

    with st.form("create_category_form"):
        name = st.text_input("Category Name *", placeholder="e.g., Groceries")
        cat_type = st.selectbox("Category Type *", options=type_names)
        col1, col2 = st.columns(2)
        with col1:
            color = st.color_picker("Category Color", value="#FF6B6B")
        with col2:
            icon = st.text_input("Icon (emoji)", value="📂", max_chars=10)
        monthly_budget = st.number_input(
            "Monthly budget (€, optional)", min_value=0.0, step=10.0, format="%.2f", value=0.0
        )
        submitted = st.form_submit_button("➕ Add Category", use_container_width=True, type="primary")

    if submitted:
        try:
            success, message = st.session_state.categoryRepository.add_category(
                name=name,
                categoryTypeId=get_type_id(cat_type),
                color=color,
                icon=icon.strip() or "📂",
                monthlyBudget=monthly_budget,
            )
        except DatabaseError as e:
            st.error(str(e))
            return
        if success:
            flash("success", message)
            refresh_data()
        else:
            st.error(message)


@st.dialog("✏️ Update Category")
def update_category_dialog(category_id: int):
    category = get_category(category_id)
    if category is None:
        st.warning("This category no longer exists.")
        return

    type_names = st.session_state.category_types_df["name"].tolist()
    current_type = get_category_type_name(category["categorytypeid"])
    type_index = type_names.index(current_type) if current_type in type_names else 0

    with st.form("update_category_form"):
        name = st.text_input("Category Name *", value=category["name"])
        cat_type = st.selectbox("Category Type *", options=type_names, index=type_index)
        col1, col2 = st.columns(2)
        with col1:
            # Prefilled, so saving without touching them no longer wipes color/icon
            color = st.color_picker("Color", value=category["color"] or "#808080")
        with col2:
            icon = st.text_input("Icon (emoji)", value=category["icon"] or "", max_chars=10)
        monthly_budget = st.number_input(
            "Monthly budget (€)", min_value=0.0, step=10.0, format="%.2f",
            value=float(category["monthlybudget"] or 0.0),
        )
        submitted = st.form_submit_button("💾 Update Category", use_container_width=True, type="primary")

    if submitted:
        try:
            success, message = st.session_state.categoryRepository.update_category(
                id=int(category["id"]),
                name=name,
                categoryTypeId=get_type_id(cat_type),
                color=color,
                icon=icon.strip() or None,
                monthlyBudget=monthly_budget,
            )
        except DatabaseError as e:
            st.error(str(e))
            return
        if success:
            flash("success", message)
            refresh_data()
        else:
            st.error(message)


@st.dialog("🗑️ Remove Category")
def remove_category_dialog(category_id: int):
    category = get_category(category_id)
    if category is None:
        st.warning("This category no longer exists.")
        return

    st.warning(f"Remove '{category['name']}'? This action cannot be undone.")
    subcategories = get_subcategories_for_category(category_id)
    if subcategories:
        st.warning(f"Its {len(subcategories)} subcategories will also be removed.")
        with st.expander("View subcategories"):
            for sub in subcategories:
                st.write(f"- {sub}")

    if st.button("🗑️ Remove Category", use_container_width=True, type="primary"):
        try:
            success, message = st.session_state.categoryRepository.remove_category(int(category["id"]))
        except DatabaseError as e:
            st.error(str(e))
            return
        if success:
            flash("success", message)
            refresh_data()
        else:
            # e.g. still used by transactions: shown inside the dialog
            st.error(message)


@st.dialog("➕ New SubCategory")
def create_subcategory_dialog():
    categories = st.session_state.categories_df
    if categories.empty:
        st.warning("Create a category first.")
        return

    with st.form("create_sub_category_form"):
        selected_category = st.selectbox("Category", options=categories["name"].tolist())
        new_sub = st.text_input("Subcategory Name", placeholder="e.g., Rent", max_chars=200)
        submitted = st.form_submit_button("✅ Confirm", use_container_width=True, type="primary")

    if submitted:
        category_id = int(categories[categories["name"] == selected_category].iloc[0]["id"])
        try:
            success, message = st.session_state.subCategoryRepository.add_sub_category(
                categoryId=category_id, name=new_sub
            )
        except DatabaseError as e:
            st.error(str(e))
            return
        if success:
            flash("success", f"{message} (in '{selected_category}')")
            refresh_data()
        else:
            st.error(message)


# ==================== SIDEBAR ====================
st.sidebar.header("🔧 Operations")

if st.sidebar.button("🔄 Refresh Data", use_container_width=True):
    refresh_data()

st.sidebar.divider()

if st.sidebar.button("➕ New Category", use_container_width=True, type="primary"):
    create_category_dialog()

if st.sidebar.button("➕ New SubCategory", use_container_width=True, type="primary"):
    create_subcategory_dialog()


# ==================== MAIN CONTENT ====================
if st.session_state.categories_df.empty:
    st.info("No categories found. Create your first category using the sidebar!")
else:
    cols = st.columns(4)

    for idx, (_, row) in enumerate(st.session_state.categories_df.iterrows()):
        category_id = int(row["id"])
        with cols[idx % 4]:
            with st.container(border=True):
                st.markdown(f"### {row['icon'] or '📂'} {row['name']}")

                type_name = get_category_type_name(row["categorytypeid"])
                st.markdown(f":{TYPE_BADGE_COLORS.get(type_name.lower(), 'gray')}-badge[{type_name}]")

                st.color_picker(
                    label="Color",
                    value=row["color"] or "#808080",
                    key=f"color_{category_id}",
                    disabled=True,
                    label_visibility="collapsed",
                )

                budget = float(row["monthlybudget"] or 0.0)
                if budget > 0:
                    st.metric("Monthly budget", f"€{budget:,.2f}")
                else:
                    st.caption("No budget set")

                subcategories = get_subcategories_for_category(category_id)
                if subcategories:
                    for sub in subcategories:
                        st.badge(sub)
                else:
                    st.caption("No subcategories")

                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✏️ Edit", key=f"edit_{category_id}", use_container_width=True):
                        update_category_dialog(category_id)
                with col2:
                    if st.button("🗑️ Remove", key=f"delete_{category_id}", use_container_width=True):
                        remove_category_dialog(category_id)