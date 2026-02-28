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
            if not df.empty and 'item' in df.columns:
                df['item'] = df['item'].str.strip()
            return df
        except:
            return pd.DataFrame()

    def push(self, table, data):
        try:
            self.client.table(table).insert(data).execute()
            st.success("✅ Recorded Successfully!")
            return True
        except Exception as e:
            st.error(f"❌ Database Error: {e}")
            return False

# ==========================================
# MODULE 2: FRUIT STORE FUNCTIONALITY
# ==========================================
class FruitModule:
    def __init__(self, db, today, month):
        self.db = db
        self.today = today
        self.month = month

    def render(self):
        st.header("🍎 Fruit & Vegetable Sales")
        p_df = self.db.fetch("purchases")
        s_df = self.db.fetch("sales")
        w_df = self.db.fetch("waste")
        
        if p_df.empty:
            st.warning("No stock available. Admin must add stock first.")
            return

        items = sorted(p_df['item'].unique().tolist())
        selected = st.selectbox("Select Item", ["Select..."] + items)

        if selected != "Select...":
            # Stock Logic
            in_qty = p_df[p_df['item'] == selected]['qty'].sum()
            out_qty = s_df[s_df['item'] == selected]['qty'].sum() if not s_df.empty else 0
            lost_qty = w_df[w_df['item'] == selected]['qty'].sum() if not w_df.empty else 0
            stock = float(in_qty) - float(out_qty) - float(lost_qty)
            
            st.info(f"📦 Stock: **{stock} kg**")

            with st.form("fruit_form", clear_on_submit=True):
                c1, c2 = st.columns(2)
                q = c1.number_input("Qty (kg)", min_value=0.0, step=0.1)
                p = c2.number_input("Price (PKR)", min_value=0.0, step=10.0)
                mode = st.radio("Mode", ["Cash", "Credit"], horizontal=True)
                cust = st.text_input("Customer") if mode == "Credit" else "N/A"
                
                if st.form_submit_button("Sale"):
                    if 0 < q <= stock:
                        self.db.push("sales", {"item":selected,"qty":q,"price":p,"type":mode,"customer":cust,"date":self.today,"month":self.month})
                    else:
                        st.error("Invalid Quantity!")

# ==========================================
# MODULE 3: GAS AGENCY FUNCTIONALITY
# ==========================================
class GasModule:
    def __init__(self, db, today):
        self.db = db
        self.today = today

    def render(self):
        st.header("🔥 Gas Cylinder Tracking")
        with st.form("gas_form", clear_on_submit=True):
            name = st.text_input("Customer")
            size = st.selectbox("Size", ["11.8kg", "45kg", "6kg"])
            qty = st.number_input("Qty", min_value=1)
            pr = st.number_input("Price (PKR)", min_value=0)
            swap = st.checkbox("Empty Bottle Received?")
            
            if st.form_submit_button("Record Gas Sale"):
                self.db.push("gas_sales", {
                    "customer_name": name, "cylinder_type": size, 
                    "qty": qty, "price_pkr": pr, "empty_received": swap, "date": self.today
                })

# ==========================================
# MODULE 4: ADMIN & REPORTS
# ==========================================
class AdminModule:
    def __init__(self, db, today, month):
        self.db = db
        self.today = today
        self.month = month

    def render(self):
        st.header("📈 Admin Dashboard")
        choice = st.selectbox("Action", ["Reports", "Add Fruit Stock", "Waste Log", "Expenses"])
        
        if choice == "Reports":
            # Simplified Profit/Loss
            sales = self.db.fetch("sales")
            gas = self.db.fetch("gas_sales")
            st.subheader(f"Total Revenue: PKR {(sales['qty'].astype(float)*sales['price'].astype(float)).sum() + gas['price_pkr'].sum():,.0f}")
            
        elif choice == "Add Fruit Stock":
            with st.form("stock_in"):
                i = st.text_input("Item Name")
                q = st.number_input("Qty", min_value=0.0)
                p = st.number_input("Cost Price", min_value=0.0)
                if st.form_submit_button("Save Stock"):
                    self.db.push("purchases", {"item":i,"qty":q,"price":p,"date":self.today,"month":self.month})

# ==========================================
# MAIN APP EXECUTION
# ==========================================
def main():
    st.set_page_config(page_title="Islamabad Shop ERP", layout="wide")
    
    # Init Core Services
    db = ShopDB()
    now = datetime.now()
    today_str = now.strftime("%Y-%m-%d")
    month_str = now.strftime("%Y-%m")

    # Sidebar Login
    st.sidebar.title("🏪 Navigation")
    menu = st.sidebar.selectbox("Go To", ["🍎 Fruit Store", "🔥 Gas Agency", "👑 Admin"])
    pwd = st.sidebar.text_input("Password", type="password")

    if not (pwd == "staff123" or pwd == "owner786"):
        st.info("Enter password to begin.")
        return

    # Routing Logic
    if menu == "🍎 Fruit Store":
        FruitModule(db, today_str, month_str).render()
    elif menu == "🔥 Gas Agency":
        GasModule(db, today_str).render()
    elif menu == "👑 Admin":
        if pwd == "owner786":
            AdminModule(db, today_str, month_str).render()
        else:
            st.error("Admin Access Required.")

if __name__ == "__main__":
    main()
