import streamlit as st

# Page config must be the very first Streamlit call
st.set_page_config(
    page_title="Categories and Subcategories", 
    page_icon=":📊",
    layout="wide",
    initial_sidebar_state="auto"
)

st.title("📊 Categories and Subcategories")

categories_data = Category(dict())

st.write(categories_data.categories)

st.sidebar.header("🔧 Operations")

st.sidebar.subheader("➕ Create Category")
new_cat = st.sidebar.text_input("Name")
new_type: Type = st.sidebar.selectbox(
    label="Type",
    options=list(Type),
    format_func=lambda t: t.name.capitalize()
)
new_color: str = st.sidebar.color_picker(label="Color")
new_icon: str = st.sidebar.text_input(label="Icon")
new_threshold: float = st.sidebar.number_input("Thrsehold", min_value=0.0)
new_sub = st.sidebar.text_input("First subcategory (optional)")
if st.sidebar.button("Add Category"):
    if new_cat.strip():
        success, msg = categories_data.add_category(
            new_cat.strip(), 
            new_type,
            new_color,
            new_icon,
            new_threshold,
            new_sub.strip())
        (st.sidebar.success if success else st.sidebar.error)(msg)
    else:
        st.sidebar.error("Category name cannot be empty.")

st.sidebar.subheader("🗑️ Remove Category")
cat_to_remove = st.sidebar.selectbox(
    "Select category", 
    categories_data.categories.keys(),
    key="remove_cat")
if st.sidebar.button("Remove Category"):
    success, msg = categories_data.remove_category(cat_to_remove)
    (st.sidebar.success if success else st.sidebar.error)(msg)

st.sidebar.subheader("⚙️ Update Category Attributes")
cat_to_update = st.sidebar.selectbox(
    "Category to update",
    categories_data.get_categories(),
    key="update_attr")

update_threshold: float = st.sidebar.number_input("Thrsehold", min_value=0.0)
if st.sidebar.button("Update Threshold"):
    val = update_threshold if update_threshold > 0 else None
    success, msg = categories_data.update_threshold(
        cat_to_update,
        val)
    (st.sidebar.success if success else st.sidebar.error)(msg)

update_color: str = st.sidebar.color_picker(label="Color")
if st.sidebar.button("Update Color"):
    success, msg = categories_data.update_color(cat_to_update, update_color)
    (st.sidebar.success if success else st.sidebar.error)(msg)

update_icon = st.sidebar.text_input(label="Icon")
if st.sidebar.button("Update Icon"):
    if new_icon.strip():
        success, msg = categories_data.update_icon(
            cat_to_update, 
            new_icon.strip())
        (st.sidebar.success if success else st.sidebar.error)(msg)
    else:
        st.sidebar.error("Icon cannot be empty.")

# --- Add Subcategory ---
# st.sidebar.subheader("📌 Add Subcategory")
# cat_for_sub = st.sidebar.selectbox("Category", categories_data.get_categories(), key="cat_for_sub")
# new_subcat = st.sidebar.text_input("Subcategory name")
# if st.sidebar.button("Add Subcategory"):
#     if new_subcat.strip():
#         success, msg = Category.add_sub_category(cat_for_sub, new_subcat.strip())
#         (st.sidebar.success if success else st.sidebar.error)(msg)
#     else:
#         st.sidebar.error("Subcategory name cannot be empty.")

# --- Remove Subcategory ---
# st.sidebar.subheader("❌ Remove Subcategory")
# cat_for_rem_sub = st.sidebar.selectbox("Category", categories.get_all_category_data(), key="cat_for_rem_sub")
# subs = categories.get_sub_categories(cat_for_rem_sub)
# if subs:
#     sub_to_remove = st.sidebar.selectbox("Subcategory", subs)
#     if st.sidebar.button("Remove Subcategory"):
#         success, msg = categories.remove_sub_category(cat_for_rem_sub, sub_to_remove)
#         (st.sidebar.success if success else st.sidebar.error)(msg)
# else:
#     st.sidebar.info("This category has no subcategories.")

# -------------------------------
# Main: Category grid
# -------------------------------
st.header("📋 Current Categories")
categories_data = categories_data.get_categories()

cols = st.columns(3)
for idx, (cat, info) in enumerate(categories_data.items()):
    with cols[idx % 3]:
        st.markdown(f"### {info['icon']} {cat}")
        st.markdown(f"**Color:** `{info['color']}`")
        if info["threshold"] is not None:
            st.markdown(f"**Threshold:** €{info['threshold']:.2f}")
        else:
            st.markdown("**Threshold:** *not set*")
        if info["subcategories"]:
            st.markdown("**Subcategories:**")
            for sub in info["subcategories"]:
                st.markdown(f"- {sub}")
        else:
            st.markdown("*No subcategories*")
        st.markdown("---")

with st.expander("🔍 Raw Data (JSON)"):
    st.json(categories_data)