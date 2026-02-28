import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime

# ==========================================
# MODULE 1: DATABASE & CORE ENGINE
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
            df = pd.DataFrame(res.data)
            return df
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
# MODULE 2: CUSTOMER & CREDIT MANAGEMENT
# ==========================================
class CustomerModule:
    def __init__(self, db):
        self.db = db

    def render_registration(self):
        st.subheader("👥 Register New Customer")
        with st.form("cust_reg", clear_on_submit=True):
            name = st.text_input("Full Name")
            phone = st.text_input("Phone Number")
            if st.form_submit_button("Register Customer"):
                if name:
                    self.db.push("customers", {"name": name.strip(), "phone": phone})
                else:
                    st.error("Name is required.")

    def get_customer_list(self):
        df = self.db.fetch("customers")
        if not df.empty:
            return sorted(df['name'].unique().tolist())
        return ["No Registered Customers"]

# ==========================================
# MODULE 3: FRUIT STORE
# ==========================================
class FruitModule:
    def __init__(self, db, today, month, customers):
        self.db = db
        self.today = today
        self.month = month
        self.customers = customers

    def render(self):
        st.header("🍎 Fruit & Vegetable Sales")
        p_df = self.db.fetch("purchases")
        s_df = self.db.fetch("sales")
        w_df = self.db.fetch("waste")
        
        items = sorted(p_df['item'].unique().tolist()) if not p_df.empty else []
        selected = st.selectbox("Select Item", ["Select..."] + items)

        if selected != "Select...":
            # Safe Stock Logic
            in_q = p_df[p_df['item'] == selected]['qty'].sum() if not p_df.empty else 0
            out_q = s_df[s_df['item'] == selected]['qty'].sum() if not s_df.empty else 0
            w_q = w_df[w_df['item'] == selected]['qty'].sum() if not w_df.empty else 0
            stock = float(in_q) - float(out_q) - float(w_q)
            
            st.info(f"📦 Stock: **{stock} kg**")

            with st.form("fruit_sale", clear_on_submit=True):
                q = st.number_input("Qty (kg)", min_value=0.0, step=0.1)
                p = st.number_input("Price (PKR)", min_value=0.0, step=10.0)
                mode = st.radio("Mode", ["Cash", "Credit"], horizontal=True)
                
                cust_list = self.customers.get_customer_list()
                cust = st.selectbox("Select Customer", cust_list) if mode == "Credit" else "N/A"
                
                if st.form_submit_button("Sale"):
                    if 0 < q <= stock:
                        self.db.push("sales", {"item":selected,"qty":q,"price":p,"type":mode,"customer":cust,"date":self.today,"month":self.month})
                    else:
                        st.error("Check Quantity!")

# ==========================================
# MODULE 4: GAS AGENCY
# ==========================================
class GasModule:
    def __init__(self, db, today, customers):
        self.db = db
        self.today = today
        self.customers = customers

    def render(self):
        st.header("🔥 Gas Cylinder Tracking")
        with st.form("gas_form", clear_on_submit=True):
            cust_list = self.customers.get_customer_list()
            name = st.selectbox("Customer", cust_list)
            size = st.selectbox("Size", ["11.8kg", "45kg", "6kg"])
            qty = st.number_input("Qty", min_value=1)
            pr = st.number_input("Price (PKR)", min_value=0)
            mode = st.radio("Payment", ["Cash", "Credit"], horizontal=True)
            swap = st.checkbox("Empty Bottle Received?")
            
            if st.form_submit_button("Record Gas Sale"):
                self.db.push("gas_sales", {
                    "customer_name": name, "cylinder_type": size, 
                    "qty": qty, "price_pkr": pr, "payment_mode": mode,
                    "empty_received": swap, "date": self.today
                })

# ==========================================
# MODULE 5: ADMIN & REPORTS (WITH ERROR FIX)
# ==========================================
class AdminModule:
    def __init__(self, db, today, month):
        self.db = db
        self.today = today
        self.month = month

    def render(self):
        st.header("📈 Admin Dashboard")
        choice = st.selectbox("Action", ["Financial Report", "Add Stock", "Waste Log", "Expenses"])
        
        if choice == "Financial Report":
            sales = self.db.fetch("sales")
            gas = self.db.fetch("gas_sales")
            
            rev_f = 0
            if not sales.empty and 'qty' in sales.columns:
                rev_f = (sales['qty'].astype(float) * sales['price'].astype(float)).sum()
            
            rev_g = 0
            if not gas.empty and 'price_pkr' in gas.columns:
                rev_g = gas['price_pkr'].astype(float).sum()
            
            st.metric("Total Revenue (PKR)", f"{rev_f + rev_g:,.0f}")
            
        elif choice == "Add Stock":
            with st.form("stock_in"):
                i = st.text_input("Item Name")
                q = st.number_input("Qty", min_value=0.0)
                p = st.number_input("Cost Price", min_value=0.0)
                if st.form_submit_button("Save"):
                    self.db.push("purchases", {"item":i,"qty":q,"price":p,"date":self.today,"month":self.month})

# ==========================================
# MAIN APP EXECUTION
# ==========================================
def main():
    st.set_page_config(page_title="Islamabad ERP", layout="wide")
    db = ShopDB()
    cust_mod = CustomerModule(db)
    today = datetime.now().strftime("%Y-%m-%d")
    month = datetime.now().strftime("%Y-%m")

    st.sidebar.title("🏪 Navigation")
    menu = st.sidebar.selectbox("Go To", ["🍎 Fruit Store", "🔥 Gas Agency", "👥 Customers", "👑 Admin"])
    pwd = st.sidebar.text_input("Password", type="password")

    if not (pwd == "staff123" or pwd == "owner786"):
        st.info("Enter password to begin.")
        return

    if menu == "🍎 Fruit Store":
        FruitModule(db, today, month, cust_mod).render()
    elif menu == "🔥 Gas Agency":
        GasModule(db, today, cust_mod).render()
    elif menu == "👥 Customers":
        cust_mod.render_registration()
    elif menu == "👑 Admin":
        if pwd == "owner786":
            AdminModule(db, today, month).render()
        else:
            st.error("Admin Access Required.")

if __name__ == "__main__":
    main()
