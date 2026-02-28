import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime

# ==========================================
# MODULE 1: DATABASE CORE
# ==========================================
class ShopDB:
    def __init__(self):
        try:
            self.client: Client = create_client(
                st.secrets["SUPABASE_URL"], 
                st.secrets["SUPABASE_KEY"]
            )
        except:
            st.error("⚠️ Connection Error: Check Streamlit Secrets.")
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
# MODULE 2: BUSINESS LOGIC CLASSES
# ==========================================
class FruitModule:
    def __init__(self, db, today, month):
        self.db = db
        self.today = today
        self.month = month

    def render(self):
        st.subheader("🍎 Fruit & Vegetable Management")
        sub_menu = st.tabs(["Sales", "Inventory", "Waste Log"])
        
        # --- Sales Tab ---
        with sub_menu[0]:
            p_df = self.db.fetch("purchases")
            items = sorted(p_df['item'].unique().tolist()) if not p_df.empty else []
            selected = st.selectbox("Select Item", ["Select..."] + items)
            if selected != "Select...":
                st.info(f"Checking Stock for {selected}...")
                # Sales Logic here...

        # --- Inventory Tab ---
        with sub_menu[1]:
            with st.form("fruit_stock"):
                i = st.text_input("Item Name")
                q = st.number_input("Qty Received", min_value=0.0)
                p = st.number_input("Purchase Price", min_value=0.0)
                if st.form_submit_button("Add Stock"):
                    self.db.push("purchases", {"item":i,"qty":q,"price":p,"date":self.today,"month":self.month})

class GasModule:
    def __init__(self, db, today):
        self.db = db
        self.today = today

    def render(self):
        st.subheader("🔥 Gas Agency Operations")
        sub_menu = st.tabs(["Cylinder Sales", "Supplier Ledger"])
        
        with sub_menu[0]:
            with st.form("gas_sale"):
                c_name = st.text_input("Customer Name")
                size = st.selectbox("Size", ["11.8kg", "45kg", "6kg"])
                if st.form_submit_button("Log Sale"):
                    # Gas Logic here...
                    pass

class CustomerModule:
    def __init__(self, db):
        self.db = db

    def render(self):
        st.subheader("👥 Customer Directory")
        name = st.text_input("Customer Name")
        phone = st.text_input("Phone")
        if st.button("Register New Customer"):
            self.db.push("customers", {"name": name, "phone": phone})
        
        st.divider()
        st.write("Current Registered Customers:")
        st.dataframe(self.db.fetch("customers"))

# ==========================================
# MAIN ROUTER & SESSION MANAGEMENT
# ==========================================
def main():
    st.set_page_config(page_title="Shop ERP", layout="centered")
    
    # Initialize Session States
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'business_choice' not in st.session_state:
        st.session_state.business_choice = None

    db = ShopDB()
    today = datetime.now().strftime("%Y-%m-%d")
    month = datetime.now().strftime("%Y-%m")

    # --- SCREEN 1: LOGIN ---
    if not st.session_state.logged_in:
        st.title("🔐 Shop Login")
        pwd = st.text_input("Enter Shop Password", type="password")
        if st.button("Login"):
            if pwd == "owner786" or pwd == "staff123":
                st.session_state.logged_in = True
                st.session_state.role = "Admin" if pwd == "owner786" else "Staff"
                st.rerun()
            else:
                st.error("Invalid Password")
        return

    # --- SCREEN 2: BUSINESS SELECTION (HUB) ---
    if st.session_state.business_choice is None:
        st.title(f"👋 Welcome, {st.session_state.role}")
        st.write("Choose the business you want to operate today:")
        
        col1, col2 = st.columns(2)
        if col1.button("🍎 Enter Fruit Business", use_container_width=True):
            st.session_state.business_choice = "Fruit"
            st.rerun()
        if col2.button("🔥 Enter Gas Business", use_container_width=True):
            st.session_state.business_choice = "Gas"
            st.rerun()
        
        st.divider()
        if st.button("🚪 Logout"):
            st.session_state.logged_in = False
            st.rerun()
        return

    # --- SCREEN 3: OPERATIONAL DASHBOARD ---
    st.sidebar.title(f"📍 {st.session_state.business_choice} Mode")
    
    # Context-Aware Sidebar Navigation
    if st.session_state.business_choice == "Fruit":
        nav = st.sidebar.radio("Navigation", ["Sales & Stock", "Customers", "Reports"])
        if st.sidebar.button("🔄 Switch Business"):
            st.session_state.business_choice = None
            st.rerun()
            
        if nav == "Sales & Stock":
            FruitModule(db, today, month).render()
        elif nav == "Customers":
            CustomerModule(db).render()
            
    elif st.session_state.business_choice == "Gas":
        nav = st.sidebar.radio("Navigation", ["Cylinder Ops", "Customers", "Reports"])
        if st.sidebar.button("🔄 Switch Business"):
            st.session_state.business_choice = None
            st.rerun()
            
        if nav == "Cylinder Ops":
            GasModule(db, today).render()
        elif nav == "Customers":
            CustomerModule(db).render()

if __name__ == "__main__":
    main()
