import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime

# (ShopDB and CustomerModule remain the same as previous clean versions)

# ==========================================
# MODULE 3: GAS AGENCY (With Safety Shield)
# ==========================================
class GasModule:
    def __init__(self, db, today, month, role):
        self.db, self.today, self.month, self.role = db, today, month, role

    def render(self):
        st.title("🔥 Gas Agency")
        
        # Check if table exists by trying a small fetch
        test_df = self.db.fetch("gas_sales")
        if test_df is None: # Custom error handling
            st.error("⚠️ Database Table 'gas_sales' missing! Please run the SQL fix provided.")
            return

        tabs = ["⚡ Sales"]
        if self.role == "Admin": tabs += ["🚛 Supplier Ledger"]
        active_tabs = st.tabs(tabs)

        with active_tabs[0]:
            with st.form("gas_sale_form", clear_on_submit=True):
                # Pull customer list for the dropdown
                c_df = self.db.fetch("customers")
                cust_list = c_df['name'].tolist() if not c_df.empty else ["Register Customer First"]
                
                c_name = st.selectbox("Customer", cust_list)
                sz = st.selectbox("Cylinder Size", ["11.8kg", "45kg", "6kg"])
                pr = st.number_input("Rate (PKR)", min_value=0)
                mode = st.radio("Payment", ["Cash", "Credit"], horizontal=True)
                swp = st.checkbox("Empty Bottle Received (Swap)?")
                
                if st.form_submit_button("Log Gas Sale"):
                    data = {
                        "customer_name": c_name, "cylinder_type": sz, 
                        "price_pkr": pr, "payment_mode": mode, 
                        "empty_received": swp, "date": self.today, "month": self.month
                    }
                    self.db.push("gas_sales", data)

        if self.role == "Admin" and len(active_tabs) > 1:
            with active_tabs[1]:
                st.subheader("Company / Supplier Account")
                with st.form("gas_sup"):
                    s_name = st.text_input("Supplier Name")
                    ret = st.number_input("Empties Returned to Company", min_value=0)
                    pay = st.number_input("Payment Made (PKR)", min_value=0)
                    if st.form_submit_button("Record Supplier Entry"):
                        self.db.push("gas_supplier_ledger", {
                            "supplier_name": s_name, "bottles_returned": ret, 
                            "payment_made": pay, "date": self.today
                        })
                
                st.divider()
                st.write("Recent Supplier History")
                st.dataframe(self.db.fetch("gas_supplier_ledger"), use_container_width=True)

# (Main Router logic remains the same)
