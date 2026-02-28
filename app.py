import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime

# (ShopDB class remains at the top as before)

# ==========================================
# 2. UPDATED CUSTOMER MODULE (With Debt Tracker)
# ==========================================
class CustomerModule:
    def __init__(self, db, role):
        self.db = db
        self.role = role

    def render(self):
        st.title("👥 Customer & Debt Management")
        
        tab1, tab2 = st.tabs(["Register/View Customers", "💰 Debt Ledger (Admin Only)"])
        
        with tab1:
            with st.form("reg_cust", clear_on_submit=True):
                n, p = st.text_input("Full Name"), st.text_input("Phone")
                if st.form_submit_button("Register New Customer"):
                    if n: self.db.push("customers", {"name":n.strip(), "phone":p})
            
            st.divider()
            cust_df = self.db.fetch("customers")
            if not cust_df.empty:
                st.write("Registered Customers:")
                st.dataframe(cust_df[['name', 'phone']], use_container_width=True)

        with tab2:
            if self.role != "Admin":
                st.error("Access Denied. Only the Owner can view debt summaries.")
            else:
                st.subheader("📊 Outstanding Balances (Khata)")
                
                # Fetch all relevant data
                f_sales = self.db.fetch("sales")
                g_sales = self.db.fetch("gas_sales")
                collections = self.db.fetch("collections")
                
                # Filter for Credit only
                f_credit = f_sales[f_sales['type'] == 'Credit'] if not f_sales.empty else pd.DataFrame()
                g_credit = g_sales[g_sales['payment_mode'] == 'Credit'] if not g_sales.empty else pd.DataFrame()
                
                # 1. Calculate Total Debt (Fruit + Gas)
                # Fruit Debt
                f_debt = f_credit.groupby('customer').apply(lambda x: (x['qty'].astype(float) * x['price'].astype(float)).sum()).reset_index()
                f_debt.columns = ['name', 'fruit_debt']
                
                # Gas Debt
                g_debt = g_credit.groupby('customer_name')['price_pkr'].sum().reset_index()
                g_debt.columns = ['name', 'gas_debt']
                
                # 2. Calculate Total Payments
                payments = collections.groupby('customer_name')['amount_paid'].sum().reset_index() if not collections.empty else pd.DataFrame(columns=['name', 'amount_paid'])
                payments.columns = ['name', 'total_paid']
                
                # 3. Merge everything into a master report
                report = pd.merge(cust_df[['name']], f_debt, on='name', how='left')
                report = pd.merge(report, g_debt, on='name', how='left')
                report = pd.merge(report, payments, on='name', how='left').fillna(0)
                
                report['Total Debt'] = report['fruit_debt'] + report['gas_debt']
                report['Remaining Balance'] = report['Total Debt'] - report['total_paid']
                
                # Only show customers who owe money
                debtors = report[report['Remaining Balance'] > 0]
                
                if not debtors.empty:
                    st.dataframe(debtors[['name', 'fruit_debt', 'gas_debt', 'total_paid', 'Remaining Balance']], use_container_width=True)
                    st.warning(f"Total Market Debt: Rs. {debtors['Remaining Balance'].sum():,.0f}")
                else:
                    st.success("All debts are cleared! Everyone has paid.")

                # Record a payment received
                st.divider()
                st.subheader("💵 Record a Payment Received")
                with st.form("collect_pay"):
                    c_sel = st.selectbox("Customer Paying", cust_df['name'].tolist() if not cust_df.empty else [])
                    amt = st.number_input("Amount Paid (PKR)", min_value=0.0)
                    b_type = st.radio("Source", ["Fruit", "Gas", "General"])
                    if st.form_submit_button("Save Payment"):
                        self.db.push("collections", {"customer_name":c_sel, "amount_paid":amt, "business_type":b_type, "date":datetime.now().strftime("%Y-%m-%d")})

# ==========================================
# FRUIT, GAS & ROUTER Logic (Remains the same)
# ==========================================
# ... in main() router ...
    elif choice == "Customers":
        CustomerModule(db, st.session_state.role).render()
