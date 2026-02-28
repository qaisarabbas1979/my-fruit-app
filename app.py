import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime
import json

# --- 1. CONNECTION ---
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
except:
    st.error("⚠️ Setup Missing: Add SUPABASE_URL and KEY to Streamlit Secrets!")
    st.stop()

# --- 2. AUTH & NAVIGATION ---
st.sidebar.title("🏪 Islamabad Multi-Shop")
role = st.sidebar.radio("Go To:", ["Fruit Store", "Gas Agency", "Admin Dashboard"])
pwd = st.sidebar.text_input("Password", type="password")

# Access Control
if not ((pwd == "owner786") or (pwd == "staff123")):
    st.info("Please login with your password to continue.")
    st.stop()

today = datetime.now().strftime("%Y-%m-%d")

# Helper to fetch data
def get_data(table):
    try:
        res = supabase.table(table).select("*").execute()
        return pd.DataFrame(res.data)
    except:
        return pd.DataFrame()

# Helper to save data
def save_entry(table, data):
    try:
        supabase.table(table).insert(data).execute()
        st.success("✅ Recorded Successfully!")
        return True
    except Exception as e:
        st.error(f"❌ Error: {e}")
        return False

# --- 🔥 GAS AGENCY SECTION ---
if role == "Gas Agency":
    st.header("🔥 Gas Operations")
    tab1, tab2, tab3 = st.tabs(["Customer Sales & Returns", "Supplier Ledger", "Cylinder Inventory"])

    with tab1:
        colA, colB = st.columns(2)
        
        with colA:
            st.subheader("New Sale / Swap")
            with st.form("gas_sale", clear_on_submit=True):
                c_name = st.text_input("Customer Name")
                g_type = st.selectbox("Cylinder Size", ["11.8kg", "45kg", "6kg"])
                g_qty = st.number_input("Qty", min_value=1)
                g_price = st.number_input("Price (Rs.)", min_value=0)
                g_mode = st.radio("Payment", ["Cash", "Credit"])
                empty_in = st.checkbox("Empty Received? (Swap)")
                if st.form_submit_button("Log Sale"):
                    save_entry("gas_sales", {
                        "customer_name": c_name, "cylinder_type": g_type, 
                        "qty": g_qty, "price_pkr": g_price, 
                        "payment_mode": g_mode, "empty_received": empty_in, "date": today
                    })

        with colB:
            st.subheader("🔄 Return Empty Later")
            st.write("Mark bottles as returned for previous credit customers.")
            gas_df = get_data("gas_sales")
            if not gas_df.empty:
                # Filter for people who still owe an empty bottle
                pending_customers = gas_df[gas_df['empty_received'] == False]['customer_name'].unique().tolist()
                if pending_customers:
                    with st.form("return_form"):
                        ret_cust = st.selectbox("Select Customer", pending_customers)
                        ret_qty = st.number_input("Bottles Returned", min_value=1)
                        if st.form_submit_button("Update Return Status"):
                            # Logic to mark as received
                            save_entry("gas_supplier_returns", {"supplier_name": f"CUST:{ret_cust}", "empties_returned": ret_qty, "date": today})
                            st.info("Return logged in system.")
                else:
                    st.success("All customer empty bottles are accounted for!")

    with tab2:
        if pwd == "owner786":
            st.subheader("🚛 Supplier (Company) Accounts")
            with st.form("sup_bill"):
                s_name = st.text_input("Company Name (e.g., Shell, PSO)")
                b_amt = st.number_input("Bill Amount (Rs.)", min_value=0)
                p_amt = st.number_input("Amount Paid (Rs.)", min_value=0)
                bottles = st.number_input("Full Bottles Received", min_value=0)
                if st.form_submit_button("Save Bill"):
                    save_entry("gas_supplier_bills", {"supplier_name":s_name, "bill_amount":b_amt, "paid_amount":p_amt, "full_bottles_received":bottles, "date":today})
        else:
            st.warning("Only Admin can access Supplier Ledger.")

    with tab3:
        st.subheader("📊 Stock Position")
        bills = get_data("gas_supplier_bills")
        rets = get_data("gas_supplier_returns")
        
        if not bills.empty:
            total_recv = bills['full_bottles_received'].sum()
            total_ret = rets['empties_returned'].sum() if not rets.empty else 0
            
            c1, c2 = st.columns(2)
            # This shows how many empty bottles you need to give back to the company
            c1.metric("Empties Owed to Company", f"{total_recv - total_ret} Bottles")
            c2.metric("Balance to Pay Company", f"Rs. {bills['bill_amount'].sum() - bills['paid_amount'].sum():,.0f}")

# --- 🍏 FRUIT STORE SECTION ---
elif role == "Fruit Store":
    st.header("🍎 Fruit & Vegetable Shop")
    st.info("Fruit management active. All prices in PKR.")
    # (Your previous fruit sales code here)

# --- 👑 ADMIN MASTER ---
elif role == "Admin Dashboard":
    if pwd == "owner786":
        st.header("📈 Master Profit & Cash Report")
        # Admin summaries...
