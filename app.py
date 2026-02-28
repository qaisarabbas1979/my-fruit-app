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
# 2. CUSTOMER & DEBT MODULE
# ==========================================
class CustomerModule:
    def __init__(self, db, role):
        self.db, self.role = db, role

    def render(self):
        st.title("👥 Customer & Khata")
        tab1, tab2 = st.tabs(["Register", "💰 Debt Summary"])
        
        cust_df = self.db.fetch("customers")

        with tab1:
            with st.form("reg_c"):
                n, p = st.text_input("Name"), st.text_input("Phone")
                if st.form_submit_button("Add Customer"):
                    self.db.push("customers", {"name": n.strip(), "phone": p})
            st.dataframe(cust_df)

        with tab2:
            if self.role != "Admin":
                st.warning("Only Admin can view the Debt Ledger.")
            else:
                st.subheader("Outstanding Balances")
                f_sales = self.db.fetch("sales")
                g_sales = self.db.fetch("gas_sales")
                coll = self.db.fetch("collections")

                # Debt Math
                f_debt = f_sales[f_sales['type']=='Credit'].groupby('customer').apply(lambda x: (x['qty'].astype(float)*x['price'].astype(float)).sum()).reset_index(name='f_d') if not f_sales.empty else pd.DataFrame(columns=['customer','f_d'])
                g_debt = g_sales[g_sales['payment_mode']=='Credit'].groupby('customer_name')['price_pkr'].sum().reset_index(name='g_d') if not g_sales.empty else pd.DataFrame(columns=['customer_name','g_d'])
                paid = coll.groupby('customer_name')['amount_paid'].sum().reset_index(name='p') if not coll.empty else pd.DataFrame(columns=['customer_name','p'])

                # Merge
                res = pd.merge(cust_df[['name']], f_debt, left_on='name', right_on='customer', how='left')
                res = pd.merge(res, g_debt, left_on='name', right_on='customer_name', how='left')
                res = pd.merge(res, paid, left_on='name', right_on='customer_name', how='left').fillna(0)
                res['Balance'] = res['f_d'] + res['g_d'] - res['p']
                
                st.dataframe(res[['name', 'Balance']][res['Balance'] > 0])

                with st.form("pay_form"):
                    c = st.selectbox("Customer", cust_df['name'].tolist() if not cust_df.empty else [])
                    amt = st.number_input("Amount Paid", min_value=0.0)
                    if st.form_submit_button("Record Payment"):
                        self.db.push("collections", {"customer_name":c, "amount_paid":amt, "date":datetime.now().strftime("%Y-%m-%d")})

# ==========================================
# 3. FRUIT MODULE
# ==========================================
class FruitModule:
    def __init__(self, db, today, month, role):
        self.db, self.today, self.month, self.role = db, today, month, role

    def render(self):
        st.title("🍎 Fruit Store")
        tabs = ["Sales"]
        if self.role == "Admin": tabs += ["Stock", "Waste"]
        active = st.tabs(tabs)

        with active[0]:
            p_df = self.db.fetch("purchases")
            items = p_df['item'].unique().tolist() if not p_df.empty else []
            sel = st.selectbox("Item", ["Select..."] + items)
            if sel != "Select...":
                with st.form("f_s"):
                    q = st.number_input("Qty")
                    p = st.number_input("Price")
                    m = st.radio("Mode", ["Cash", "Credit"])
                    c_name = "N/A"
                    if m == "Credit":
                        c_df = self.db.fetch("customers")
                        c_name = st.selectbox("Customer", c_df['name'].tolist() if not c_df.empty else [])
                    if st.form_submit_button("Sell"):
                        self.db.push("sales", {"item":sel, "qty":q, "price":p, "type":m, "customer":c_name, "date":self.today, "month":self.month})

# ==========================================
# 4. MAIN ROUTER
# ==========================================
def main():
    if 'logged_in' not in st.session_state: st.session_state.logged_in = False
    if 'biz' not in st.session_state: st.session_state.biz = None

    db = ShopDB()
    today, month = datetime.now().strftime("%Y-%m-%d"), datetime.now().strftime("%Y-%
