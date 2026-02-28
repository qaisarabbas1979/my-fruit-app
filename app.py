import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime

# ==========================================
# 1. DATABASE CORE (Must be defined first!)
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
            st.success("✅ Recorded!")
            return True
        except Exception as e:
            st.error(f"❌ Error: {e}")
            return False

# ==========================================
# 2. CUSTOMER MODULE
# ==========================================
class CustomerModule:
    def __init__(self, db):
        self.db = db

    def render(self):
        st.title("👥 Customer Management")
        with st.form("cust_reg"):
            n = st.text_input("Customer Name")
            p = st.text_input("Phone")
            if st.form_submit_button("Add Customer"):
                self.db.push("customers", {"name": n, "phone": p})
        
        df = self.db.fetch("customers")
        if not df.empty:
            st.dataframe(df)

# ==========================================
# 3. FRUIT MODULE (With Security)
# ==========================================
class FruitModule:
    def __init__(self, db, today, month, role):
        self.db = db
        self.today = today
        self.month = month
        self.role = role

    def render(self):
        st.title("🍎 Fruit Business")
        
        # Tabs based on role
        tab_list = ["🛒 Sales"]
        if self.role == "Admin":
            tab_list += ["📦 Inventory", "🗑️ Waste Log"]
        
        tabs = st.tabs(tab_list)

        with tabs[0]:
            p_df = self.db.fetch("purchases")
            items = sorted(p_df['item'].unique().tolist()) if not p_df.empty else []
            sel = st.selectbox("Select Fruit", ["Select..."] + items)
            if sel != "Select...":
                # Basic Stock logic here...
                st.info(f"Selling {sel}...")
                with st.form("sale_f"):
                    q = st.number_input("Qty", min_value=0.0)
                    pr = st.number_input("Price", min_value=0.0)
                    if st.form_submit_button("Sell"):
                        self.db.push("sales", {"item":sel, "qty":q, "price":pr, "date":self.today, "month":self.month})

        if self.role == "Admin":
            with tabs[1]:
                with st.form("stock_f"):
                    i = st.text_input("Item Name")
                    q = st.number_input("Qty In", min_value=0.0)
                    p = st.number_input("Cost", min_value=0.0)
                    if st.form_submit_button("Add Stock"):
                        self.db.push("purchases", {"item":i, "qty":q, "price":p, "date":self.today, "month":self.month})
            with tabs[2]:
                st.subheader("🗑️ Waste Log")
                # Waste logic here...

# ==========================================
# 4. MAIN ROUTER
# ==========================================
def main():
    if 'logged_in' not in st.session_state: st.session_state.logged_in = False
    if 'biz' not in st.session_state: st.session_state.biz = None
    if 'role' not in st.session_state: st.session_state.role = None

    db = ShopDB() # Defined now!
    today = datetime.now().strftime("%Y-%m-%d")
    month = datetime.now().strftime("%Y-%m")

    if not st.session_state.logged_in:
        st.title("🔐 Login")
        pwd = st.text_input("Password", type="password")
        if st.button("Enter"):
            if pwd == "owner786":
                st.session_state.logged_in = True
                st.session_state.role = "Admin"
                st.rerun()
            elif pwd == "staff123":
                st.session_state.logged_in = True
                st.session_state.role = "Operator"
                st.rerun()
            else: st.error("Wrong Password")
        return

    if st.session_state.biz is None:
        st.title("Hub")
        c1, c2 = st.columns(2)
        if c1.button("Fruit"): st.session_state.biz = "Fruit"; st.rerun()
        if c2.button("Gas"): st.session_state.biz = "Gas"; st.rerun()
        if st.button("Logout"): st.session_state.logged_in = False; st.rerun()
        return

    # Operations Sidebar
    st.sidebar.title(f"Role: {st.session_state.role}")
    nav_items = ["Store"]
    if st.session_state.role == "Admin":
        nav_items.append("Customers")
    nav_items.append("Switch Business")
    
    choice = st.sidebar.radio("Menu", nav_items)

    if choice == "Switch Business":
        st.session_state.biz = None
        st.rerun()
    elif choice == "Customers":
        CustomerModule(db).render()
    else:
        if st.session_state.biz == "Fruit":
            FruitModule(db, today, month, st.session_state.role).render()

if __name__ == "__main__":
    main()
