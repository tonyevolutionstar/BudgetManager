from Home import *

st.title("📊 Transactions")

# -------------------------------
# Sidebar: Create new Transaction
# -------------------------------
st.sidebar.header("Create new Transaction")

def reset_amount():
    # Clear the amount value when toggling expense/income
    st.session_state.amount = 0.0

with st.sidebar.form("transaction_form", clear_on_submit=True, enter_to_submit=False):
    # Widgets
    transaction_date = st.date_input("Date")
    description = st.text_input("Description")
    st.checkbox(label="Is Expense?", value=True, key="is_expense", on_change=reset_amount())
    
    # Initialize session state for amount if not present
    if "amount" not in st.session_state:
        reset_amount()
    
    if st.session_state.is_expense:
        amount = st.number_input("Expense Amount", min_value=0.0, step=0.5, format="%.2f", icon=":material/euro_symbol:")
    else:
        amount = st.number_input("Income Amount", min_value=0.0, step=0.5, format="%.2f", icon=":material/euro_symbol:")
    
    # Category suggestion
    suggested = "Others"
    if description:
        suggested = ctgAI.predict_category(model, description)
    category = st.selectbox("Category", ctg.get_categories(), index=ctg.get_categories().index(suggested))
    
    submitted = st.form_submit_button("Add Transaction")
    
    if submitted:
        if description and amount > 0:
            new_row = pd.DataFrame([{
                file.CSV_COLUMNS[0]: transaction_date.strftime("%d/%m/%Y"),
                file.CSV_COLUMNS[1]: transaction_date.strftime("%d/%m/%Y"),
                file.CSV_COLUMNS[2]: description,
                file.CSV_COLUMNS[3]: amount if st.session_state.is_expense else 0.0,
                file.CSV_COLUMNS[4]: amount if not st.session_state.is_expense else 0.0,
                file.CSV_COLUMNS[5]: (df["Income"][-1].sub(df["Expense"][-1])).cumsum(),
                file.CSV_COLUMNS[6]: 0.0,
                file.CSV_COLUMNS[7]: category
            }])
            st.session_state.df = pd.concat([st.session_state.df, new_row], ignore_index=True)
            file.save_dataframe(st.session_state.df)
            st.success("Transaction added successfully!")
            # Clear model cache to retrain with new data
            st.cache_resource.clear()
            st.rerun()
        else:
            st.error("Please enter a valid description and positive amount.")
