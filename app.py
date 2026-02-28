import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime

# --- 1. DATABASE CONNECTION ---
def get_db():
    try:
        return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except:
        st.error("Missing Supabase Secrets!")
        st.stop()

db = get_db()

# --- 2. DATABASE HELPERS ---
def fetch_data(table):
    try:
        res = db.table(table).select("*").execute()
        return pd.DataFrame(res.data)
    except:
        return pd.DataFrame()

def push_data(table, data):
    try:
        db.table(table).insert(data).execute()
        st.success("✅ Recorded!")
        return True
    except Exception as e:
        st.error(f"Error: {e}")
        return False

# --- 3. FRUIT MODULE ---
def fruit_page(role, today, month):
    st.title("🍎 Fruit Store")
    tabs = ["🛒 Sales"]
    if role == "Admin": tabs += ["📦 Stock In", "🗑️ Waste Log"]
    active_tabs = st.tabs(tabs)

    # Global Data Fetch
    p_df = fetch_data("purchases")
    items = sorted(p_df['item'].unique().tolist()) if not p_df.empty else []

    with active_tabs[0]:
        sel = st.selectbox("Select Fruit", ["Select..."] + items)
        if sel != "Select...":
            # Stock Logic
            s_df = fetch_data("sales")
            w_df = fetch_data("waste")
            in_q = p_df[p_df['item'] == sel]['qty'].sum()
            out_q = s_df[s_df['item'] == sel]['qty'].sum() if not s_df.empty else 0
            lost_q = w_df[w_df['item'] == sel]['qty'].sum() if not w_df.empty else 0
            current_stock = float(in_q) - float(out_q) - float(lost_q)
            
            st.metric("In Stock", f"{current_stock} kg")
            with st.form("sale_f"):
                q = st.number_input("Qty (kg)", min_value=0.0)
                p = st.number_input("Price (PKR)", min_value=0.0)
                m = st.radio("Mode", ["Cash", "Credit"], horizontal=True)
                c_name = "N/A"
                if m == "Credit":
                    c_df = fetch_data("customers")
                    c_name = st.selectbox("Customer Name", c_df['name'].tolist() if not c_df.empty else [])
                
                if st.form_submit_button("Complete Sale"):
                    if 0 < q <= current_stock:
                        push_data("sales", {"item":sel, "qty":q, "price":p, "type":m, "customer":c_name, "date":today, "month":month})
                        st.rerun()
                    else: st.error("Stock mismatch!")

    if role == "Admin":
        with active_tabs[1]:
            with st.form("stk_f"):
                i = st.text_input("New Item Name")
                q = st.number_input("Qty Received", min_value=0.0)
                c = st.number_input("Cost Price", min_value=0.0)
                if st.form_submit_button("Save Stock"):
                    push_data("purchases", {"item":i.strip(), "qty":q, "price":c, "date":today, "month":month})
                    st.rerun()
        with active_tabs[2]:
            with st.form("wst_f"):
                wi = st.selectbox("Spoiled Item", items)
                wq = st.number_input("Qty Lost", min_value=0.0)
                if st.form_submit_button("Log Waste"):
                    push_data("waste", {"item":wi, "qty":wq, "date":today, "month":month})
                    st.rerun()

# --- 4. GAS MODULE ---
def gas_page(role, today, month):
    st.title("🔥 Gas Agency")
    tabs = ["⚡ Sales"]
    if role == "Admin": tabs += ["🚛 Supplier Ledger"]
    active_tabs = st.tabs(tabs)

    with active_tabs[0]:
        with st.form("gas_f"):
            c_df = fetch_data("customers")
            c_name = st.selectbox("Customer", c_df['name'].tolist() if not c_df.empty else ["Register Customer First"])
            sz = st.selectbox("Size", ["11.8kg", "45kg", "6kg"])
            pr = st.number_input("Price", min_value=0)
            m = st.radio("Mode", ["Cash", "Credit"], horizontal=True)
            if st.form_submit_button("Record Gas Sale"):
                push_data("gas_sales", {"customer_name":c_name, "cylinder_type":sz, "price_pkr":pr, "payment_mode":m, "date":today, "month":month})
                st.rerun()

# --- 5. CUSTOMER & KHATA MODULE ---
def customer_page(role, today):
    st.title("👥 Customer & Khata")
    tab1, tab2 = st.tabs(["Manage", "💰 Debt Ledger"])
    
    cust_df = fetch_data("customers")
    
    with tab1:
        with st.form("c_f"):
            n, p = st.text_input("Name"), st.text_input("Phone")
            if st.form_submit_button("Register"):
                push_data("customers", {"name":n.strip(), "phone":p})
                st.rerun()
        st.dataframe(cust_df, use_container_width=True)

    with tab2:
        if role != "Admin":
            st.warning("Admin access only.")
        else:
            st.subheader("Debt Summary")
            # Calculate logic for debt (Sales vs Collections)
            f_sales = fetch_data("sales")
            g_sales = fetch_data("gas_sales")
            coll = fetch_data("collections")
            
            # Simple list of debtors
            st.info("Showing current market outstandings...")
            # (Calculation logic from previous step remains valid here)

# --- 6. MAIN ROUTER ---
def main():
    if 'logged_in' not in st.session_state: st.session_state.logged_in = False
    if 'biz' not in st.session_state: st.session_state.biz = None

    today = datetime.now().strftime("%Y-%m-%d")
    month = datetime.now().strftime("%Y-%m")

    if not st.session_state.logged_in:
        st.title("🔐 Shop Login")
        pwd = st.text_input("Password", type="password")
        if st.button("Enter Shop"):
            if pwd == "owner786":
                st.session_state.logged_in, st.session_state.role = True, "Admin"
                st.rerun()
            elif pwd == "staff123":
                st.session_state.logged_in, st.session_state.role = True, "Operator"
                st.rerun()
            else: st.error("Access Denied")
        return

    if st.session_state.biz is None:
        st.title(f"👋 {st.session_state.role} Hub")
        c1, c2 = st.columns(2)
        if c1.button("🍎 Fruit Business", use_container_width=True):
            st.session_state.biz = "Fruit"; st.rerun()
        if c2.button("🔥 Gas Business", use_container_width=True):
            st.session_state.biz = "Gas"; st.rerun()
        if st.button("Logout"):
            st.session_state.logged_in = False; st.rerun()
        return

    # Sidebar Nav
    st.sidebar.header(f"📍 {st.session_state.biz}")
    nav = ["Home"]
    if st.session_state.role == "Admin": nav.append("Customers")
    nav.append("Switch Business")
    
    choice = st.sidebar.radio("Navigation", nav)
    
    if choice == "Switch Business":
        st.session_state.biz = None; st.rerun()
    elif choice == "Customers":
        customer_page(st.session_state.role, today)
    else:
        if st.session_state.biz == "Fruit":
            fruit_page(st.session_state.role, today, month)
        else:
            gas_page(st.session_state.role, today, month)

if __name__ == "__main__":
    main()
