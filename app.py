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
                f_sales = self.db.fetch("sales")
                g_sales = self.db.fetch("gas_sales")
                coll = self.db.fetch("collections")

                # Debt Math (Fruit + Gas - Payments)
                f_d = f_sales[f_sales['type']=='Credit'].groupby('customer').apply(lambda x: (x['qty'].astype(float)*x['price'].astype(float)).sum()).reset_index(name='f_debt') if not f_sales.empty else pd.DataFrame(columns=['customer','f_debt'])
                g_d = g_sales[g_sales['payment_mode']=='Credit'].groupby('customer_name')['price_pkr'].sum().reset_index(name='g_debt') if not g_sales.empty else pd.DataFrame(columns=['customer_name','g_debt'])
                paid = coll.groupby('customer_name')['amount_paid'].sum().reset_index(name='p') if not coll.empty else pd.DataFrame(columns=['customer_name','p'])

                res = pd.merge(cust_df[['name']], f_d, left_on='name', right_on='customer', how='left')
                res = pd.merge(res, g_d, left_on='name', right_on='customer_name', how='left')
                res = pd.merge(res, paid, left_on='name', right_on='customer_name', how='left').fillna(0)
                res['Total Balance'] = res['f_debt'] + res['g_debt'] - res['p']
                
                st.dataframe(res[res['Total Balance'] > 0][['name', 'Total Balance']], use_container_width=True)

                with st.form("pay_rec"):
                    c = st.selectbox("Customer Paying", cust_df['name'].tolist() if not cust_df.empty else [])
                    amt = st.number_input("Amount Received", min_value=0.0)
                    if st.form_submit_button("Record Payment"):
                        self.db.push("collections", {"customer_name":c, "amount_paid":amt, "date":datetime.now().strftime("%Y-%m-%d")})

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

        with tabs[0]:
            p_df = self.db.fetch("purchases")
            items = sorted(p_df['item'].unique().tolist()) if not p_df.empty else []
            sel = st.selectbox("Select Item", ["Select..."] + items)
            if sel != "Select...":
                # Stock Logic
                s_df, w_df = self.db.fetch("sales"), self.db.fetch("waste")
                stock = float(p_df[p_df['item']==sel]['qty'].sum()) - \
                        float(s_df[s_df['item']==sel]['qty'].sum() if not s_df.empty else 0) - \
                        float(w_df[w_df['item']==sel]['qty'].sum() if not w_df.empty else 0)
                
                st.metric("Stock Available", f"{stock} kg")
                with st.form("f_sale"):
                    q = st.number_input("Quantity", min_value=0.0)
                    p = st.number_input("Price", min_value=0.0)
                    mode = st.radio("Mode", ["Cash", "Credit"], horizontal=True)
                    c_name = "N/A"
                    if mode == "Credit":
                        c_df = self.db.fetch("customers")
                        c_name = st.selectbox("Select Customer", c_df['name'].tolist() if not c_df.empty else [])
                    if st.form_submit_button("Complete Sale"):
                        if 0 < q <= stock:
                            self.db.push("sales", {"item":sel, "qty":q, "price":p, "type":mode, "customer":c_name, "date":self.today, "month":self.month})
                        else: st.error("Check Stock Quantity")

# ==========================================
# 4. GAS MODULE
# ==========================================
class GasModule:
    def __init__(self, db, today, role):
        self.db, self.today, self.role = db, today, role

    def render(self):
        st.title("🔥 Gas Agency")
        t_list = ["⚡ Sales & Swaps"]
        if self.role == "Admin": t_list += ["🚛 Supplier Ledger"]
        tabs = st.tabs(t_list)

        with tabs[0]:
            with st.form("g_sale"):
                c_df = self.db.fetch("customers")
                c_name = st.selectbox("Customer", c_df['name'].tolist() if not c_df.empty else ["Register Customer First"])
                sz = st.selectbox("Cylinder", ["11.8kg", "45kg", "6kg"])
                pr = st.number_input("Price", min_value=0)
                mode = st.radio("Payment", ["Cash", "Credit"], horizontal=True)
                swp = st.checkbox("Empty Received?")
                if st.form_submit_button("Record Gas Transaction"):
                    self.db.push("gas_sales", {"customer_name":c_name, "cylinder_type":sz, "price_pkr":pr, "payment_mode":mode, "empty_received":swp, "date":self.today})

        if self.role == "Admin":
            with tabs[1]:
                with st.form("sup_l"):
                    s_name = st.text_input("Company Name")
                    ret = st.number_input("Empties Returned", min_value=0)
                    pay = st.number_input("Cash Paid to Company", min_value=0)
                    if st.form_submit_button("Update Supplier Account"):
                        self.db.push("gas_supplier_ledger", {"supplier_name":s_name, "bottles_returned":ret, "payment_made":pay, "date":self.today})

# ==========================================
# 5. MAIN ROUTER
# ==========================================
def main():
    if 'logged_in' not in st.session_state: st.session_state.logged_in = False
    if 'biz' not in st.session_state: st.session_state.biz = None

    db = ShopDB()
    # FIXED LINE:
    today = datetime.now().strftime("%Y-%m-%d")
    month = datetime.now().strftime("%Y-%m")

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
            else: st.error("Wrong Password")
        return

    if st.session_state.biz is None:
        st.title(f"👋 {st.session_state.role} Hub")
        c1, c2 = st.columns(2)
        if c1.button("🍎 Fruit Business", use_container_width=True): st.session_state.biz = "Fruit"; st.rerun()
        if c2.button("🔥 Gas Business", use_container_width=True): st.session_state.biz = "Gas"; st.rerun()
        if st.button("🚪 Logout"): st.session_state.logged_in = False; st.rerun()
        return

    st.sidebar.title(f"📍 {st.session_state.biz}")
    nav = ["Ops"]
    if st.session_state.role == "Admin": nav.append("Customers")
    nav.append("Switch Business")
    choice = st.sidebar.radio("Navigation", nav)

    if choice == "Switch Business":
        st.session_state.biz = None
        st.rerun()
    elif choice == "Customers":
        CustomerModule(db, st.session_state.role).render()
    else:
        if st.session_state.biz == "Fruit":
            FruitModule(db, today, month, st.session_state.role).render()
        elif st.session_state.biz == "Gas":
            GasModule(db, today, st.session_state.role).render()

if __name__ == "__main__":
    main()
