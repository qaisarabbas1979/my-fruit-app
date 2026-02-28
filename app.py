import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime

# ==========================================
# 1. DATABASE CORE
# ==========================================
class ShopDB:
    def __init__(self):
        try:
            self.client: Client = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
        except:
            st.error("⚠️ Connection Error: Check Streamlit Secrets.")
            st.stop()

    def fetch(self, table):
        try:
            res = self.client.table(table).select("*").execute()
            return pd.DataFrame(res.data)
        except Exception:
            return pd.DataFrame()

    def push(self, table, data):
        try:
            self.client.table(table).insert(data).execute()
            return True
        except Exception as e:
            st.error(f"❌ Error: {e}")
            return False

# ==========================================
# 2. MODULES (Simplified for Stability)
# ==========================================
def render_customers(db, role):
    st.title("👥 Customers & Khata")
    tab1, tab2 = st.tabs(["Register", "💰 Debt Ledger"])
    cust_df = db.fetch("customers")
    
    with tab1:
        with st.form("reg_c", clear_on_submit=True):
            n, p = st.text_input("Name"), st.text_input("Phone")
            if st.form_submit_button("Add"):
                if n: db.push("customers", {"name": n.strip(), "phone": p})
                st.rerun()
        st.dataframe(cust_df, use_container_width=True)

def render_fruit(db, role, today, month):
    st.title("🍎 Fruit Store")
    t_list = ["🛒 Sales"]
    if role == "Admin": t_list += ["📦 Stock In", "🗑️ Waste Log"]
    tabs = st.tabs(t_list)

    p_df = db.fetch("purchases")
    items = sorted(p_df['item'].unique().tolist()) if not p_df.empty else []

    with tabs[0]:
        sel = st.selectbox("Select Item", ["Select..."] + items)
        if sel != "Select...":
            # Real-time stock calculation
            s_df, w_df = db.fetch("sales"), db.fetch("waste")
            in_q = p_df[p_df['item']==sel]['qty'].sum()
            out_q = s_df[s_df['item']==sel]['qty'].sum() if not s_df.empty else 0
            lost_q = w_df[w_df['item']==sel]['qty'].sum() if not w_df.empty else 0
            stock = float(in_q) - float(out_q) - float(lost_q)
            
            st.metric("Stock Available", f"{stock} kg")
            with st.form("f_sale"):
                q, p = st.number_input("Qty"), st.number_input("Price")
                m = st.radio("Mode", ["Cash", "Credit"], horizontal=True)
                c_name = "N/A"
                if m == "Credit":
                    c_df = db.fetch("customers")
                    c_name = st.selectbox("Customer", c_df['name'].tolist() if not c_df.empty else [])
                if st.form_submit_button("Complete Sale"):
                    if 0 < q <= stock:
                        db.push("sales", {"item":sel, "qty":q, "price":p, "type":m, "customer":c_name, "date":today, "month":month})
                        st.success("Sold!")
                        st.rerun()

def render_gas(db, role, today, month):
    st.title("🔥 Gas Agency")
    t_list = ["⚡ Sales"]
    if role == "Admin": t_list += ["🚛 Supplier Ledger"]
    tabs = st.tabs(t_list)
    
    with tabs[0]:
        with st.form("g_sale"):
            c_df = db.fetch("customers")
            c_name = st.selectbox("Customer", c_df['name'].tolist() if not c_df.empty else ["Register First"])
            sz = st.selectbox("Cylinder", ["11.8kg", "45kg", "6kg"])
            pr, mode = st.number_input("Price"), st.radio("Mode", ["Cash", "Credit"], horizontal=True)
            if st.form_submit_button("Log Transaction"):
                db.push("gas_sales", {"customer_name":c_name, "cylinder_type":sz, "price_pkr":pr, "payment_mode":mode, "date":today, "month":month})
                st.success("Logged!")
                st.rerun()

# ==========================================
# 3. MAIN ROUTER (Anti-Freeze Logic)
# ==========================================
def main():
    # Initialize state
    if 'logged_in' not in st.session_state: st.session_state.logged_in = False
    if 'biz' not in st.session_state: st.session_state.biz = None
    if 'role' not in st.session_state: st.session_state.role = None

    db = ShopDB()
    today, month = datetime.now().strftime("%Y-%m-%d"), datetime.now().strftime("%Y-%m")

    # 1. LOGIN SCREEN
    if not st.session_state.logged_in:
        st.title("🔐 Shop Login")
        pwd = st.text_input("Password", type="password")
        if st.button("Login"):
            if pwd == "owner786":
                st.session_state.logged_in, st.session_state.role = True, "Admin"
                st.rerun()
            elif pwd == "staff123":
                st.session_state.logged_in, st.session_state.role = True, "Operator"
                st.rerun()
            else:
                st.error("Invalid")
        return

    # 2. HUB SCREEN
    if st.session_state.biz is None:
        st.title(f"👋 {st.session_state.role} Dashboard")
        col1, col2 = st.columns(2)
        if col1.button("🍎 Fruit Business", use_container_width=True):
            st.session_state.biz = "Fruit"
            st.rerun()
        if col2.button("🔥 Gas Business", use_container_width=True):
            st.session_state.biz = "Gas"
            st.rerun()
        st.divider()
        if st.button("🚪 Logout"):
            st.session_state.logged_in = False
            st.rerun()
        return

    # 3. OPERATION SCREEN
    st.sidebar.title(f"📍 {st.session_state.biz}")
    nav_options = ["Operations"]
    if st.session_state.role == "Admin":
        nav_options.append("Customers")
    nav_options.append("Switch Business")
    
    choice = st.sidebar.radio("Go to:", nav_options)

    if choice == "Switch Business":
        st.session_state.biz = None
        st.rerun()
    elif choice == "Customers":
        render_customers(db, st.session_state.role)
    else:
        if st.session_state.biz == "Fruit":
            render_fruit(db, st.session_state.role, today, month)
        else:
            render_gas(db, st.session_state.role, today, month)

if __name__ == "__main__":
    main()
