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
        except:
            st.error("⚠️ Setup Missing: Add SUPABASE_URL and KEY to Streamlit Secrets!")
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
            st.success("✅ Recorded!")
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

        with active_tabs[0]:
            sel = st.selectbox("Select Item", ["Select..."] + items)
            if sel != "Select...":
                # Stock Math
                s_df = self.db.fetch("sales")
                w_df = self.db.fetch("waste")
                stock = float(p_df[p_df['item']==sel]['qty'].sum()) - \
                        float(s_df[s_df['item']==sel]['qty'].sum() if not s_df.empty else 0) - \
                        float(w_df[w_df['item']==sel]['qty'].sum() if not w_df.empty else 0)
                
                st.metric("Available Stock", f"{stock} kg")
                with st.form("fruit_sale_form", clear_on_submit=True):
                    qty = st.number_input("Quantity", min_value=0.0)
                    pr = st.number_input("Price", min_value=0.0)
                    mode = st.radio("Payment", ["Cash", "Credit"], horizontal=True)
                    
                    # FIX: Show Customer List if Credit
                    cust_name = "N/A"
                    if mode == "Credit":
                        c_df = self.db.fetch("customers")
                        cust_list = c_df['name'].tolist() if not c_df.empty else []
                        cust_name = st.selectbox("Select Customer from List", cust_list)
                    
                    if st.form_submit_button("Log Sale"):
                        if 0 < qty <= stock:
                            self.db.push("sales", {"item":sel, "qty":qty, "price":pr, "type":mode, "customer":cust_name, "date":self.today, "month":self.month})
                        else: st.error("Stock Error")

        if self.role == "Admin":
            with active_tabs[1]:
                with st.form("add_fruit_stock"):
                    i = st.text_input("Item")
                    q = st.number_input("Qty In", min_value=0.0)
                    p = st.number_input("Purchase Price", min_value=0.0)
                    if st.form_submit_button("Save"):
                        self.db.push("purchases", {"item":i, "qty":q, "price":p, "date":self.today, "month":self.month})
            with active_tabs[2]:
                with st.form("fruit_waste"):
                    wi = st.selectbox("Spoiled Item", items)
                    wq = st.number_input("Qty Lost", min_value=0.0)
                    if st.form_submit_button("Record Loss"):
                        self.db.push("waste", {"item":wi, "qty":wq, "date":self.today, "month":self.month})

# ==========================================
# 3. GAS MODULE (With Working Ledger)
# ==========================================
class GasModule:
    def __init__(self, db, today, role):
        self.db, self.today, self.role = db, today, role

    def render(self):
        st.title("🔥 Gas Agency")
        tabs = ["⚡ Sales"]
        if self.role == "Admin": tabs += ["🚛 Supplier Ledger"]
        active_tabs = st.tabs(tabs)

        with active_tabs[0]:
            with st.form("gas_sale"):
                # FIX: Show customer names here too
                c_df = self.db.fetch("customers")
                cust_list = c_df['name'].tolist() if not c_df.empty else []
                c_name = st.selectbox("Customer", cust_list)
                sz = st.selectbox("Size", ["11.8kg", "45kg", "6kg"])
                pr = st.number_input("Price", min_value=0)
                swp = st.checkbox("Empty Received?")
                if st.form_submit_button("Log Sale"):
                    self.db.push("gas_sales", {"customer_name":c_name, "cylinder_type":sz, "price_pkr":pr, "empty_received":swp, "date":self.today})

        if self.role == "Admin":
            with active_tabs[1]:
                st.subheader("Manage Supplier (Company) Account")
                with st.form("sup_ledger"):
                    s_name = st.text_input("Supplier/Company Name")
                    ret = st.number_input("Empty Bottles Returned", min_value=0)
                    pay = st.number_input("Payment Made to Company", min_value=0)
                    if st.form_submit_button("Update Ledger"):
                        self.db.push("gas_supplier_ledger", {"supplier_name":s_name, "bottles_returned":ret, "payment_made":pay, "date":self.today})
                
                st.divider()
                st.write("Recent Supplier Transactions")
                st.dataframe(self.db.fetch("gas_supplier_ledger"))

# ==========================================
# 4. CUSTOMER MODULE
# ==========================================
class CustomerModule:
    def __init__(self, db): self.db = db
    def render(self):
        st.title("👥 Customer List")
        with st.form("reg_cust"):
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
        st.title("🔐 Shop Login")
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
    nav = ["Operations"]
    if st.session_state.role == "Admin": nav.append("Customers")
    nav.append("Switch Business")
    choice = st.sidebar.radio("Navigation", nav)

    if choice == "Switch Business": st.session_state.biz = None; st.rerun()
    elif choice == "Customers": CustomerModule(db).render()
    else:
        if st.session_state.biz == "Fruit": FruitModule(db, today, month, st.session_state.role).render()
        else: GasModule(db, today, st.session_state.role).render()

if __name__ == "__main__":
    main()
