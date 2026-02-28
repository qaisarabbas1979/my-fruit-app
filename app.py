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
        except Exception:
            st.error("⚠️ Setup Missing: Add SUPABASE_URL and KEY to Streamlit Secrets!")
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
            st.success("✅ Recorded Successfully!")
            return True
        except Exception as e:
            st.error(f"❌ Database Error: {e}")
            return False

# ==========================================
# MODULE 2: FRUIT BUSINESS (With Fixed Waste Log)
# ==========================================
class FruitModule:
    def __init__(self, db, today, month):
        self.db = db
        self.today = today
        self.month = month

    def render(self):
        st.title("🍎 Fruit & Vegetable Shop")
        tab1, tab2, tab3 = st.tabs(["🛒 Sales", "📦 Inventory", "🗑️ Waste Log"])

        p_df = self.db.fetch("purchases")
        items = sorted(p_df['item'].unique().tolist()) if not p_df.empty else []

        # --- 🛒 SALES TAB ---
        with tab1:
            selected = st.selectbox("Select Item to Sell", ["Select..."] + items, key="fruit_sale_sel")
            if selected != "Select...":
                s_df = self.db.fetch("sales")
                w_df = self.db.fetch("waste")
                in_q = p_df[p_df['item'] == selected]['qty'].sum()
                out_q = s_df[s_df['item'] == selected]['qty'].sum() if not s_df.empty else 0
                lost_q = w_df[w_df['item'] == selected]['qty'].sum() if not w_df.empty else 0
                stock = float(in_q) - float(out_q) - float(lost_q)
                
                st.info(f"Available Stock: **{stock} kg**")
                with st.form("fruit_sale_form"):
                    q = st.number_input("Qty (kg)", min_value=0.0)
                    p = st.number_input("Price (PKR)", min_value=0.0)
                    if st.form_submit_button("Complete Sale"):
                        if 0 < q <= stock:
                            self.db.push("sales", {"item":selected, "qty":q, "price":p, "date":self.today, "month":self.month})
                        else: st.error("Insufficient Stock!")

        # --- 📦 INVENTORY TAB ---
        with tab2:
            with st.form("fruit_stock_form"):
                st.subheader("Add New Stock")
                i = st.text_input("Item Name")
                q = st.number_input("Qty Received", min_value=0.0)
                p = st.number_input("Purchase Price", min_value=0.0)
                if st.form_submit_button("Save Stock"):
                    self.db.push("purchases", {"item":i.strip(), "qty":q, "price":p, "date":self.today, "month":self.month})

        # --- 🗑️ WASTE LOG TAB (FIXED) ---
        with tab3:
            st.subheader("Log Spoiled Items")
            if not items:
                st.warning("No items in inventory to log waste.")
            else:
                with st.form("waste_log_form"):
                    w_item = st.selectbox("Item Spoiled", items)
                    w_qty = st.number_input("Quantity Wasted (kg)", min_value=0.0)
                    # Auto-find latest cost
                    latest_p = p_df[p_df['item'] == w_item].sort_values(by='id', ascending=False).iloc[0]['price']
                    if st.form_submit_button("Record Waste"):
                        if w_qty > 0:
                            self.db.push("waste", {"item":w_item, "qty":w_qty, "cost_price":latest_p, "date":self.today, "month":self.month})

# ==========================================
# MODULE 3: GAS BUSINESS
# ==========================================
class GasModule:
    def __init__(self, db, today):
        self.db = db
        self.today = today

    def render(self):
        st.title("🔥 Gas Agency")
        with st.form("gas_sale_form"):
            cust = st.text_input("Customer Name")
            size = st.selectbox("Size", ["11.8kg", "45kg", "6kg"])
            pr = st.number_input("Price (PKR)", min_value=0)
            if st.form_submit_button("Log Gas Sale"):
                self.db.push("gas_sales", {"customer_name":cust, "cylinder_type":size, "price_pkr":pr, "date":self.today})

# ==========================================
# MAIN ROUTER
# ==========================================
def main():
    if 'logged_in' not in st.session_state: st.session_state.logged_in = False
    if 'biz' not in st.session_state: st.session_state.biz = None

    db = ShopDB()
    today = datetime.now().strftime("%Y-%m-%d")
    month = datetime.now().strftime("%Y-%m")

    # SCREEN 1: LOGIN
    if not st.session_state.logged_in:
        st.title("🔐 Shop Login")
        pwd = st.text_input("Enter Password", type="password")
        if st.button("Enter Shop"):
            if pwd in ["owner786", "staff123"]:
                st.session_state.logged_in = True
                st.rerun()
            else: st.error("Incorrect Password")
        return

    # SCREEN 2: HUB
    if st.session_state.biz is None:
        st.title("👋 Welcome! Select a Business")
        c1, c2 = st.columns(2)
        if c1.button("🍎 Fruit Business", use_container_width=True):
            st.session_state.biz = "Fruit"
            st.rerun()
        if c2.button("🔥 Gas Business", use_container_width=True):
            st.session_state.biz = "Gas"
            st.rerun()
        if st.button("🚪 Logout"):
            st.session_state.logged_in = False
            st.rerun()
        return

    # SCREEN 3: OPERATION
    st.sidebar.title(f"📍 {st.session_state.biz} Mode")
    if st.sidebar.button("🔄 Switch Business"):
        st.session_state.biz = None
        st.rerun()

    if st.session_state.biz == "Fruit":
        FruitModule(db, today, month).render()
    else:
        GasModule(db, today).render()

if __name__ == "__main__":
    main()
