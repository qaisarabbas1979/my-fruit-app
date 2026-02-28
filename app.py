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
            self.client: Client = create_client(
                st.secrets["SUPABASE_URL"], 
                st.secrets["SUPABASE_KEY"]
            )
        except Exception:
            st.error("⚠️ Connection Error: Check Streamlit Secrets!")
            st.stop()

    def fetch(self, table):
        try:
            res = self.client.table(table).select("*").execute()
            return pd.DataFrame(res.data)
        except:
            return pd.DataFrame()

    def push(self, table, data):
        try:
            self.client.table(table).insert(data).execute()
            st.success("✅ Recorded Successfully!")
            return True
        except Exception as e:
            st.error(f"❌ Error: {e}")
            return False

# ==========================================
# 2. FRUIT MODULE
# ==========================================
class FruitModule:
    def __init__(self, db, today, month, role):
        self.db, self.today, self.month, self.role = db, today, month, role

    def render(self):
        st.title("🍎 Fruit & Vegetable Shop")
        tabs = ["🛒 Sales"]
        if self.role == "Admin": tabs += ["📦 Inventory", "🗑️ Waste Log"]
        active_tabs = st.tabs(tabs)

        p_df = self.db.fetch("purchases")
        items = sorted(p_df['item'].unique().tolist()) if not p_df.empty else []

        # --- SALES ---
        with active_tabs[0]:
            sel = st.selectbox("Select Item", ["Select..."] + items, key="f_sale_sel")
            if sel != "Select...":
                s_df = self.db.fetch("sales")
                w_df = self.db.fetch("waste")
                stock = float(p_df[p_df['item']==sel]['qty'].sum()) - \
                        float(s_df[s_df['item']==sel]['qty'].sum() if not s_df.empty else 0) - \
                        float(w_df[w_df['item']==sel]['qty'].sum() if not w_df.empty else 0)
                
                st.metric("Available Stock", f"{stock} kg")
                with st.form("f_sale_form", clear_on_submit=True):
                    q = st.number_input("Quantity (kg)", min_value=0.0)
                    p = st.number_input("Price (PKR)", min_value=0.0)
                    mode = st.radio("Payment", ["Cash", "Credit"], horizontal=True)
                    cust = "N/A"
                    if mode == "Credit":
                        c_df = self.db.fetch("customers")
                        cust = st.selectbox("Customer", c_df['name'].tolist() if not c_df.empty else ["No Customers"])
                    
                    if st.form_submit_button("Confirm Sale"):
                        if 0 < q <= stock:
                            self.db.push("sales", {"item":sel, "qty":q, "price":p, "type":mode, "customer":cust, "date":self.today, "month":self.month})
                        else: st.error("Invalid Quantity/Stock")

        # --- ADMIN ONLY TABS ---
        if self.role == "Admin":
            with active_tabs[1]:
                with st.form("f_stock"):
                    i = st.text_input("New Item Name")
                    q = st.number_input("Qty In", min_value=0.0)
                    p = st.number_input("Cost Price", min_value=0.0)
                    if st.form_submit_button("Add Stock"):
                        self.db.push("purchases", {"item":i, "qty":q, "price":p, "date":self.today, "month":self.month})
            with active_tabs[2]:
                with st.form("f_waste"):
                    w_i = st.selectbox("Item Spoiled", items)
                    w_q = st.number_input("Qty Lost", min_value=0.0)
                    if st.form_submit_button("Log Waste"):
                        self.db.push("waste", {"item":w_i, "qty":w_q, "date":self.today, "month":self.month})

# ==========================================
# 3. GAS MODULE
# ==========================================
class GasModule:
    def __init__(self, db, today, role):
        self.db, self.today, self.role = db, today, role

    def render(self):
        st.title("🔥 Gas Agency")
        tabs = ["⚡ Sales & Swaps"]
        if self.role == "Admin": tabs += ["🚛 Supplier Ledger"]
        active_tabs = st.tabs(tabs)

        with active_tabs[0]:
            with st.form("g_sale", clear_on_submit=True):
                c = st.text_input("Customer Name")
                sz = st.selectbox("Size", ["11.8kg", "45kg", "6kg"])
                pr = st.number_input("Price", min_value=0)
                swp = st.checkbox("Empty Bottle Received?")
                if st.form_submit_button("Log Gas Sale"):
                    self.db.push("gas_sales", {"customer_name":c, "cylinder_type":sz, "price_pkr":pr, "empty_received":swp, "date":self.today})

# ==========================================
# 4. CUSTOMER MODULE
# ==========================================
class CustomerModule:
    def __init__(self, db): self.db = db
    def render(self):
        st.title("👥 Customers")
        with st.form("c_reg"):
            n, p = st.text_input("Name"), st.text_input("Phone")
            if st.form_submit_button("Register"): self.db.push("customers", {"name":n, "phone":p})
        st.dataframe(self.db.fetch("customers"))

# ==========================================
# 5. MAIN ROUTER
# ==========================================
def main():
    if 'logged_in' not in st.session_state: st.session_state.logged_in = False
    if 'biz' not in st.session_state: st.session_state.biz = None

    db = ShopDB()
    today, month = datetime.now().strftime("%Y-%m-%d"), datetime.now().strftime("%Y-%m")

    if not st.session_state.logged_in:
        st.title("🔐 Login")
        pwd = st.text_input("Password", type="password")
        if st.button("Enter"):
            if pwd == "owner786": st.session_state.logged_in, st.session_state.role = True, "Admin"
            elif pwd == "staff123": st.session_state.logged_in, st.session_state.role = True, "Operator"
            else: st.error("Wrong Password")
            if st.session_state.logged_in: st.rerun()
        return

    if st.session_state.biz is None:
        st.title(f"👋 {st.session_state.role} Hub")
        c1, c2 = st.columns(2)
        if c1.button("🍎 Fruit Business", use_container_width=True): st.session_state.biz = "Fruit"; st.rerun()
        if c2.button("🔥 Gas Business", use_container_width=True): st.session_state.biz = "Gas"; st.rerun()
        if st.button("Logout"): st.session_state.logged_in = False; st.rerun()
        return

    st.sidebar.title(f"📍 {st.session_state.biz}")
    nav = ["Home"]
    if st.session_state.role == "Admin": nav.append("Customers")
    nav.append("Switch Business")
    choice = st.sidebar.radio("Menu", nav)

    if choice == "Switch Business": st.session_state.biz = None; st.rerun()
    elif choice == "Customers": CustomerModule(db).render()
    else:
        if st.session_state.biz == "Fruit": FruitModule(db, today, month, st.session_state.role).render()
        else: GasModule(db, today, st.session_state.role).render()

if __name__ == "__main__":
    main()
