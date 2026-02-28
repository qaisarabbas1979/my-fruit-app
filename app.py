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
        st.title("👥 Customer & Khata Management")
        tab1, tab2 = st.tabs(["Register New", "💰 Debt Ledger"])
        
        cust_df = self.db.fetch("customers")

        with tab1:
            with st.form("reg_c", clear_on_submit=True):
                n, p = st.text_input("Customer Name"), st.text_input("Phone Number")
                if st.form_submit_button("Add Customer"):
                    if n: self.db.push("customers", {"name": n.strip(), "phone": p})
            st.dataframe(cust_df, use_container_width=True)

        with tab2:
            if self.role != "Admin":
                st.warning("Only the Owner can view the Debt Ledger.")
            else:
                st.subheader("Outstanding Balances")
                f_sales, g_sales, coll = self.db.fetch("sales"), self.db.fetch("gas_sales"), self.db.fetch("collections")

                f_d = f_sales[f_sales['type']=='Credit'].groupby('customer').apply(lambda x: (x['qty'].astype(float)*x['price'].astype(float)).sum()).reset_index(name='f_debt') if not f_sales.empty else pd.DataFrame(columns=['customer','f_debt'])
                g_d = g_sales[g_sales['payment_mode']=='Credit'].groupby('customer_name')['price_pkr'].sum().reset_index(name='g_debt') if not g_sales.empty else pd.DataFrame(columns=['customer_name','g_debt'])
                paid = coll.groupby('customer_name')['amount_paid'].sum().reset_index(name='p_amt') if not coll.empty else pd.DataFrame(columns=['customer_name','p_amt'])

                if not cust_df.empty:
                    res = pd.merge(cust_df[['name']], f_d, left_on='name', right_on='customer', how='left')
                    res = pd.merge(res, g_d, left_on='name', right_on='customer_name', how='left')
                    res = pd.merge(res, paid, left_on='name', right_on='customer_name', how='left').fillna(0)
                    res['Balance'] = res['f_debt'] + res['g_debt'] - res['p_amt']
                    debtors = res[res['Balance'] > 0]
                    st.dataframe(debtors[['name', 'Balance']], use_container_width=True)

                with st.form("pay_rec"):
                    c_list = cust_df['name'].tolist() if not cust_df.empty else []
                    c_sel = st.selectbox("Customer Paying", c_list)
                    amt = st.number_input("Amount Paid (PKR)", min_value=0.0)
                    if st.form_submit_button("Save Payment"):
                        self.db.push("collections", {"customer_name":c_sel, "amount_paid":amt, "date":datetime.now().strftime("%Y-%m-%d")})

# ==========================================
# 3. FRUIT MODULE
# ==========================================
class FruitModule:
    def __init__(self, db, today, month, role):
        self.db, self.today, self.month, self.role = db, today, month, role

    def render(self):
        st.title("🍎 Fruit Business")
        t_list = ["🛒 Sales"]
        if self.role == "Admin": t_list += ["📦 Stock In", "🗑️ Waste Log"]
        tabs = st.tabs(t_list)

        p_df = self.db.fetch("purchases")
        items = sorted(p_df['item'].unique().tolist()) if not p_df.empty else []

        with tabs[0]:
            sel = st.selectbox("Select Item", ["Select..."] + items)
            if sel != "Select...":
                s_df, w_df = self.db.fetch("sales"), self.db.fetch("waste")
                stock = float(p_df[p_df['item']==sel]['qty'].sum()) - \
                        float(s_df[s_df['item']==sel]['qty'].sum() if not s_df.empty else 0) - \
                        float(w_df[w_df['item']==sel]['qty'].sum() if not w_df.empty else 0)
                st.metric("Stock Available", f"{stock} kg")
                with st.form("f_sale"):
                    q, p = st.number_input("Quantity"), st.number_input("Price")
                    mode = st.radio("Mode", ["Cash", "Credit"], horizontal=True)
                    c_name = "N/A"
                    if mode == "Credit":
                        c_df = self.db.fetch("customers")
                        c_name = st.selectbox("Customer", c_df['name'].tolist() if not c_df.empty else [])
                    if st.form_submit_button("Sell"):
                        if 0 < q <= stock:
                            self.db.push("sales", {"item":sel, "qty":q, "price":p, "type":mode, "customer":c_name, "date":self.today, "month":self.month})
                        else: st.error("Stock Issue")

        if self.role == "Admin":
            with tabs[1]:
                with st.form("stk_in"):
                    i, q, pr = st.text_input("Item"), st.number_input("Qty In"), st.number_input("Cost")
                    if st.form_submit_button("Add Stock"):
                        self.db.push("purchases", {"item":i, "qty":q, "price":pr, "date":self.today, "month":self.month})
            with tabs[2]:
                with st.form("w_log"):
                    wi, wq = st.selectbox("Item Spoiled", items), st.number_input("Qty Lost")
                    if st.form_submit_button("Record Waste"):
                        self.db.push("waste", {"item":wi, "qty":wq, "date":self.today, "month":self.month})

# ==========================================
# 4. GAS MODULE
# ==========================================
class GasModule:
    def __init__(self, db, today, month, role):
        self.db, self.today, self.month, self.role = db, today, month, role

    def render(self):
        st.title("🔥 Gas Agency")
        t_list = ["⚡ Sales"]
        if self.role == "Admin": t_list += ["🚛 Supplier Ledger"]
        tabs = st.tabs(t_list)

        with tabs[0]:
            with st.form("g_sale"):
                c_df = self.db.fetch("customers")
                c_name = st.selectbox("Customer", c_df['name'].tolist() if not c_df.empty else ["Register First"])
                sz = st.selectbox("Cylinder", ["11.8kg", "45kg", "6kg"])
                pr, mode = st.number_input("Price"), st.radio("Payment", ["Cash", "Credit"], horizontal=True)
                swp
