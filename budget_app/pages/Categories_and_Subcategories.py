from Home import *

st.title("📊 Categories and Subcategories")

# Initialize categories data
ctg.initialize_categories()

# Sidebar operations
st.sidebar.header("🔧 Operations")

# --- Add Category ---
st.sidebar.subheader("➕ Create Category")
new_cat = st.sidebar.text_input("Name")
new_sub = st.sidebar.text_input("Subcategory (optional)")
if st.sidebar.button("Add"):
    if new_cat.strip():
        success, msg = ctg.add_category(new_cat.strip(), new_sub.strip())
        if success:
            st.sidebar.success(msg)
        else:
            st.sidebar.error(msg)
    else:
        st.sidebar.error("Category name cannot be empty.")

# --- Remove Category ---
st.sidebar.subheader("🗑️ Remove Category")
cat_to_remove = st.sidebar.selectbox("Select category", ctg.get_categories())
if st.sidebar.button("Remove Category"):
    success, msg = ctg.remove_category(cat_to_remove)
    if success:
        st.sidebar.success(msg)
    else:
        st.sidebar.error(msg)

# --- Add Subcategory ---
st.sidebar.subheader("📌 Add Subcategory")
cat_for_sub = st.sidebar.selectbox("Category", ctg.get_categories(), key="cat_for_sub")
new_subcat = st.sidebar.text_input("Subcategory name")
if st.sidebar.button("Add Subcategory"):
    if new_subcat.strip():
        success, msg = ctg.add_sub_category(cat_for_sub, new_subcat.strip())
        if success:
            st.sidebar.success(msg)
        else:
            st.sidebar.error(msg)
    else:
        st.sidebar.error("Subcategory cannot be empty.")

# --- Remove Subcategory ---
st.sidebar.subheader("❌ Remove Subcategory")
cat_for_rem_sub = st.sidebar.selectbox("Category", ctg.get_categories(), key="cat_for_rem_sub")
subs = ctg.get_sub_categories(cat_for_rem_sub)
if subs:
    sub_to_remove = st.sidebar.selectbox("Subcategory", subs)
    if st.sidebar.button("Remove Subcategory"):
        success, msg = ctg.remove_sub_category(cat_for_rem_sub, sub_to_remove)
        if success:
            st.sidebar.success(msg)
        else:
            st.sidebar.error(msg)
else:
    st.sidebar.info("This category has no subcategories.")

# --- Update Threshold, Color, Icon ---
st.sidebar.subheader("⚙️ Update Category Attributes")
cat_to_update = st.sidebar.selectbox("Category to update", ctg.get_categories(), key="update_attr")

# Threshold
new_limit = st.sidebar.number_input("New threshold (0 to remove)", value=0.0, step=10.0)
if st.sidebar.button("Update Threshold"):
    if new_limit > 0:
        success, msg = ctg.update_threshold(cat_to_update, new_limit)
    else:
        success, msg = ctg.update_threshold(cat_to_update, None)
    if success:
        st.sidebar.success(msg)
    else:
        st.sidebar.error(msg)

# Color
all_colors = ["blue", "green", "orange", "purple", "red", "pink", "cyan", "magenta", 
              "brown", "teal", "yellow", "gray", "black", "lightgray"]
current_color = ctg.get_category_color(cat_to_update)
new_color = st.sidebar.selectbox("New color", all_colors, 
                                 index=all_colors.index(current_color) if current_color in all_colors else 0)
if st.sidebar.button("Update Color"):
    success, msg = ctg.update_color(cat_to_update, new_color)
    if success:
        st.sidebar.success(msg)
    else:
        st.sidebar.error(msg)

# Icon
current_icon = ctg.get_category_icon(cat_to_update)
new_icon = st.sidebar.text_input("New icon (emoji or text)", value=current_icon)
if st.sidebar.button("Update Icon"):
    if new_icon.strip():
        success, msg = ctg.update_icon(cat_to_update, new_icon.strip())
        if success:
            st.sidebar.success(msg)
        else:
            st.sidebar.error(msg)
    else:
        st.sidebar.error("Icon cannot be empty.")

# -------------------------------
# MAIN DISPLAY
# -------------------------------
st.header("📋 Current Categories")
categories_data = ctg.get_all_category_data()

cols = st.columns(3)
for idx, (cat, info) in enumerate(categories_data.items()):
    with cols[idx % 3]:
        icon = info["icon"]
        color = info["color"]
        threshold_val = info["threshold"]
        subcats = info["subcategories"]
        
        st.markdown(f"### {icon} {cat}")
        st.markdown(f"**Color:** `{color}`")
        if threshold_val is not None:
            st.markdown(f"**Threshold:** €{threshold_val:.2f}")
        else:
            st.markdown("**Threshold:** *not set*")
        if subcats:
            st.markdown("**Subcategories:**")
            for sub in subcats:
                st.markdown(f"- {sub}")
        else:
            st.markdown("*No subcategories*")
        st.markdown("---")

with st.expander("🔍 Raw Data (JSON)"):
    st.json(categories_data)