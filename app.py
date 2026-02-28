import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime

# --- 1. SETUP ---
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
except:
    st.error("⚠️ Setup Missing: Add SUPABASE_URL and KEY to Streamlit Secrets!")
    st.stop()

# --- 2. AUTHENTICATION ---
st.sidebar.title("🏪 Islamabad Multi-Shop")
role = st.sidebar.radio("Select Business:", ["Fruit Store", "Gas Agency", "Admin Dashboard"])
pwd = st.sidebar.text_input("Password", type="password")

if not ((pwd == "owner786") or (pwd == "staff123")):
    st.info("Please login with your password to continue.")
    st.stop()

today = datetime.now().strftime("%Y-%m-%d")
this_month = datetime.now().strftime("%Y-%m")

# --- 3. DATA HELPERS ---
def get_data(table):
    try:
        res = supabase.table(table).select("*").execute()
        return pd.DataFrame(res.data)
    except: return pd.DataFrame()

def save_entry(table, data):
    try:
        supabase.table(table).insert(data).execute()
        st.success("✅ Recorded!")
        return True
    except: return False

# --- 4. ADMIN DASHBOARD (PROFIT & LOSS) ---
if role == "Admin Dashboard":
    if pwd == "owner786":
        st.header(f"📈 Business Performance ({this_month})")
        menu = st.selectbox("Menu", ["Profit & Loss Report", "Daily Cash", "Credit Ledger", "Inventory & Expenses"])

        if menu == "Profit & Loss Report":
            # Fetch all necessary data
            sales = get_data("sales")
            gas = get_data("gas_sales")
            purchases = get_data("purchases")
            waste = get_data("waste")
            expenses = get_data("shop_expenses")

            # 1. Revenue (Sales)
            rev_f = (sales[sales['month'] == this_month]['qty'].astype(float) * sales[sales['month'] == this_month]['price'].astype(float)).sum() if not sales.empty else 0
            rev_g = (gas[gas['date'].str.contains(this_month)]['qty'].astype(float) * gas[gas['date'].str.contains(this_month)]['price_pkr'].astype(float)).sum() if not gas.empty else 0
            total_rev = rev_f + rev_g

            # 2. Expenses & Waste
            total_exp = expenses[expenses['month'] == this_month]['amount'].sum() if not expenses.empty else 0
            total_waste = (waste[waste['month'] == this_month]['qty'].astype(float) * waste[waste['month'] == this_month]['cost_price'].astype(float)).sum() if not waste.empty else 0
            
            # 3. Cost of Goods (Simplified)
            # (In a real scenario, this would be based on qty sold * purchase price)
            
            st.metric("Total Monthly Revenue", f"Rs. {total_rev:,.0f}")
            
            col1, col2 = st.columns(2)
            col1.error(f"Waste Loss: Rs. {total_waste:,.0f}")
            col2.error(f"Shop Expenses: Rs. {total_exp:,.0f}")
            
            net_profit = total_rev - total_waste - total_exp # Simplified net
            st.success(f"### Estimated Net Profit: Rs. {net_profit:,.0f}")
            st.caption("Note: Profit calculation here is Revenue minus Waste and Expenses.")

        elif menu == "Inventory & Expenses":
            tab1, tab2 = st.tabs(["Stock In", "Shop Expenses"])
            with tab1:
                with st.form("stock_in"):
                    item = st.text_input("Item Name")
                    sqty = st.number_input("Qty In", min_value=0.0)
                    spr = st.number_input("Purchase Price (Rs)", min_value=0.0)
                    if st.form_submit_button("Add Stock"):
                        save_entry("purchases", {"item":item, "qty":sqty, "price":spr, "date":today, "month":this_month})
            with tab2:
                with st.form("exp_form"):
                    desc = st.text_input("Expense Description (e.g. Electricity)")
                    amt = st.number_input("Amount (Rs)", min_value=0.0)
                    cat = st.selectbox("Category", ["Rent", "Bills", "Staff", "Other"])
                    if st.form_submit_button("Record Expense"):
                        save_entry("shop_expenses", {"description":desc, "amount":amt, "category":cat, "date":today, "month":this_month})

        elif menu == "Daily Cash":
            # (Daily Cash logic as before)
            st.write("Today's cash reconciliation...")

        elif menu == "Credit Ledger":
            # (Credit Ledger logic as before)
            st.write("Customer debt management...")

    else: st.error("Admin Only")

# --- 5. FRUIT & GAS MENUS (Previous working code remains here) ---
elif role == "Fruit Store":
    st.header("🍎 Fruit Sales")
    # ... (Insert your stable Fruit Sales code here)
elif role == "Gas Agency":
    st.header("🔥 Gas Sales")
    # ... (Insert your stable Gas Sales code here)
