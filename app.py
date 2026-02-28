import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime
import json

# --- CONNECTION ---
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
except:
    st.error("Check Secrets!")
    st.stop()

# --- AUTH & NAVIGATION ---
st.sidebar.title("🏪 Islamabad Multi-Shop")
role = st.sidebar.radio("Go To:", ["Fruit Store", "Gas Agency", "Admin Dashboard"])
pwd = st.sidebar.text_input("Password", type="password")

if not ((pwd == "owner786") or (pwd == "staff123")):
    st.info("Please login to continue.")
    st.stop()

today = datetime.now().strftime("%Y-%m-%d")

def get_data(table):
    res = supabase.table(table).select("*").execute()
    return pd.DataFrame(res.data)

def save_entry(table, data):
    supabase.table(table).insert(data).execute()
    st.success("✅ Recorded in Cloud")

# --- 🔥 GAS AGENCY TAB ---
if role == "Gas Agency":
    st.header("🔥 Gas Operations")
    tab1, tab2, tab3 = st.tabs(["Customer Sales", "Supplier Ledger", "Bottle Stock"])

    with tab1:
        st.subheader("New Sale / Swap")
        with st.form("gas_sale"):
            c_name = st.text_input("Customer Name")
            g_type = st.selectbox("Size", ["11.8kg", "45kg", "6kg"])
            g_qty = st.number_input("Qty", min_value=1)
            g_price = st.number_input("Price per Fill (Rs.)", min_value=0)
            g_mode = st.radio("Mode", ["Cash", "Credit"])
            empty_in = st.checkbox("Empty Received? (Swap)")
            if st.form_submit_button("Log Sale"):
                save_entry("gas_sales", {"customer_name":c_name, "cylinder_type":g_type, "qty":g_qty, "price_pkr":g_price, "payment_mode":g_mode, "empty_received":empty_in, "date":today})

    with tab2:
        st.subheader("🚛 Supplier Billing (Company Accounts)")
        if pwd == "owner786":
            with st.form("sup_bill"):
                s_name = st.text_input("Supplier/Company Name")
                b_amt = st.number_input("Bill Amount (Rs.)", min_value=0)
                p_amt = st.number_input("Amount Paid (Rs.)", min_value=0)
                bottles = st.number_input("Full Bottles Received", min_value=0)
                if st.form_submit_button("Save Supplier Bill"):
                    save_entry("gas_supplier_bills", {"supplier_name":s_name, "bill_amount":b_amt, "paid_amount":p_amt, "full_bottles_received":bottles, "date":today})
            
            st.divider()
            st.subheader("🔄 Return Empties to Supplier")
            with st.form("sup_return"):
                s_ret_name = st.text_input("Supplier Name")
                ret_qty = st.number_input("Empty Bottles Handed Over", min_value=1)
                if st.form_submit_button("Log Return"):
                    save_entry("gas_supplier_returns", {"supplier_name":s_ret_name, "empties_returned":ret_qty, "date":today})
        else:
            st.warning("Admin Access Required for Supplier Ledger.")

    with tab3:
        st.subheader("📊 Cylinder Inventory Status")
        bills = get_data("gas_supplier_bills")
        rets = get_data("gas_supplier_returns")
        sales = get_data("gas_sales")
        
        if not bills.empty:
            total_recv = bills['full_bottles_received'].sum()
            total_ret = rets['empties_returned'].sum() if not rets.empty else 0
            # Physical bottles currently at your shop (Full + Empty)
            at_shop = total_recv - total_ret 
            
            c1, c2 = st.columns(2)
            c1.metric("Bottles Owed to Supplier", f"{total_recv - total_ret} Units")
            c2.metric("Pending Payment to Supplier", f"Rs. {bills['bill_amount'].sum() - bills['paid_amount'].sum():,.0f}")

# --- 🍏 FRUIT STORE TAB ---
elif role == "Fruit Store":
    st.header("🍎 Fruit & Vegetable Shop")
    # Previous Sales logic...
    st.info("Fruit Store Mode Active.")

# --- 👑 ADMIN MASTER ---
elif role == "Admin Dashboard":
    if pwd == "owner786":
        st.header("📈 Master Business Overview")
        # Combined Cash summary logic here...
    else:
        st.error("Admin Password Required.")
