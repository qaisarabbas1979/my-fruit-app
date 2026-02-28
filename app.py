import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime
import json

# --- 1. SETUP & DATABASE CONNECTION ---
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
except:
    st.error("⚠️ Setup Missing: Add SUPABASE_URL and KEY to Streamlit Secrets!")
    st.stop()

# --- 2. AUTHENTICATION ---
st.sidebar.title("🏪 Islamabad Multi-Shop")
role = st.sidebar.radio("Select Business:", ["Fruit Store", "Gas Agency", "Admin Dashboard"])
pwd = st.sidebar.text_input("Password", type="password")

if not ((pwd == "owner786") or (pwd == "staff123")):
    st.info("Please login with your password to continue.")
    st.stop()

today = datetime.now().strftime("%Y-%m-%d")
this_month = datetime.now().strftime("%Y-%m")

# --- 3. DATA HELPERS ---
def get_data(table):
    try:
        res = supabase.table(table).select("*").execute()
        df = pd.DataFrame(res.data)
        if not df.empty and 'item' in df.columns:
            df['item'] = df['item'].str.strip()
        return df
    except:
        return pd.DataFrame()

def save_entry(table, data):
    try:
        supabase.table(table).insert(data).execute()
        st.success("✅ Transaction Recorded!")
        return True
    except Exception as e:
        st.error(f"❌ Error: {e}")
        return False

# --- 4. 🍎 FRUIT STORE SECTION ---
if role == "Fruit Store":
    st.header("🍎 Fruit & Vegetable Shop")
    
    # Fetch Data for Stock Calculation
    p_df = get_data("purchases")
    s_df = get_data("sales")
    w_df = get_data("waste")
    a_df = get_data("stock_adjustments")
    
    items = ["Select Item"] + (sorted(p_df['item'].unique().tolist()) if not p_df.empty else [])
    selected_item = st.selectbox("Select Fruit/Veg", items)
    
    current_stock = 0.0
    if selected_item != "Select Item":
        # Stock Calculation Logic
        p_sum = p_df[p_df['item'] == selected_item]['qty'].sum() if not p_df.empty else 0
        s_sum = s_df[s_df['item'] == selected_item]['qty'].sum() if not s_df.empty else 0
        w_sum = w_df[w_df['item'] == selected_item]['qty'].sum() if not w_df.empty else 0
        current_stock = float(p_sum) - float(s_sum) - float(w_sum)
        
        # Check Adjustments
        if not a_df.empty and selected_item in a_df['item'].values:
            last_adj = a_df[a_df['item'] == selected_item].sort_values(by='id', ascending=False).iloc[0]
            current_stock = float(last_adj['new_quantity']) # Use manual override
            
        st.info(f"📦 Current Stock: **{current_stock} kg**")

    with st.form("fruit_sale", clear_on_submit=False):
        qty = st.number_input("Quantity (kg)", min_value=0.0, step=0.5)
        pr = st.number_input("Selling Price (PKR)", min_value=0.0, step=10.0)
        mode = st.radio("Payment", ["Cash", "Credit"])
        cust = "N/A"
        if mode == "Credit":
            c_df = get_data("customers")
            cust = st.selectbox("Customer", c_df['name'].tolist() if not c_df.empty else ["No Customers"])
        
        if st.form_submit_button("Confirm Fruit Sale"):
            if selected_item != "Select Item" and qty <= current_stock and qty > 0:
                if save_entry("sales", {"item":selected_item,"qty":qty,"price":pr,"type":mode,"customer":cust,"date":today,"month":this_month}):
                    # WhatsApp Receipt
                    total_pkr = qty * pr
                    receipt = f"*FRUIT STORE RECEIPT*\n------------------\n📅 Date: {today}\n🍎 Item: {selected_item}\n⚖️ Qty: {qty} kg\n💵 Price: Rs.{pr}/kg\n------------------\n*TOTAL: Rs.{total_pkr:,.0f}*\nType: {mode}\n------------------\n_Thank you!_"
                    st.code(receipt, language="markdown")
            else:
                st.error("Invalid entry or Insufficient Stock!")

# --- 5. 🔥 GAS AGENCY SECTION ---
elif role == "Gas Agency":
    st.header("🔥 Gas Cylinder Operations")
    g_tab1, g_tab2 = st.tabs(["Customer Sales", "Cylinder Returns"])

    with g_tab1:
        with st.form("gas_sale_form"):
            c_name = st.text_input("Customer Name")
            g_type = st.selectbox("Cylinder", ["11.8kg", "45kg", "6kg"])
            g_qty = st.number_input("Quantity", min_value=1)
            g_price = st.number_input("Price (PKR)", min_value=0)
            g_mode = st.radio("Payment", ["Cash", "Credit"])
            empty_in = st.checkbox("Empty Received? (Swap)")
            
            if st.form_submit_button("Log Gas Sale"):
                save_entry("gas_sales", {
                    "customer_name": c_name, "cylinder_type": g_type, 
                    "qty": g_qty, "price_pkr": g_price, 
                    "payment_mode": g_mode, "empty_received": empty_in, "date": today
                })

    with g_tab2:
        st.subheader("🔄 Return Empty Later")
        gas_df = get_data("gas_sales")
        if not gas_df.empty:
            pending = gas_df[gas_df['empty_received'] == False]['customer_name'].unique().tolist()
            if pending:
                with st.form("gas_return"):
                    r_cust = st.selectbox("Customer returning bottle", pending)
                    r_qty = st.number_input("Bottles Returned", min_value=1)
                    if st.form_submit_button("Record Return"):
                        save_entry("gas_supplier_returns", {"supplier_name": f"CUST:{r_cust}", "empties_returned": r_qty, "date": today})
            else:
                st.success("No pending empty bottles from customers!")

# --- 6. 👑 ADMIN DASHBOARD ---
elif role == "Admin Dashboard":
    if pwd == "owner786":
        st.header("📈 Admin Master Control")
        admin_choice = st.selectbox("Menu", ["Cash Summary", "Stock In", "Waste Log", "Supplier Bills"])
        
        if admin_choice == "Cash Summary":
            s_all = get_data("sales")
            g_all = get_data("gas_sales")
            
            f_cash = (s_all[(s_all['date'] == today) & (s_all['type'] == 'Cash')]['qty'].astype(float) * s_all[(s_all['date'] == today) & (s_all['type'] == 'Cash')]['price'].astype(float)).sum() if not s_all.empty else 0
            g_cash = (g_all[(g_all['date'] == today) & (g_all['payment_mode'] == 'Cash')]['qty'].astype(float) * g_all[(g_all['date'] == today) & (g_all['payment_mode'] == 'Cash')]['price_pkr'].astype(float)).sum() if not g_all.empty else 0
            
            st.metric("Total Fruit Cash Today", f"Rs. {f_cash:,.0f}")
            st.metric("Total Gas Cash Today", f"Rs. {g_cash:,.0f}")
            st.metric("Combined Cash", f"Rs. {f_cash + g_cash:,.0f}")

        elif admin_choice == "Stock In":
            with st.form("stock_in"):
                item = st.text_input("Item Name").strip()
                sqty = st.number_input("Qty", min_value=0.0)
                scost = st.number_input("Purchase Price", min_value=0.0)
                if st.form_submit_button("Add Stock"):
                    save_entry("purchases", {"item":item, "qty":sqty, "price":scost, "date":today, "month":this_month})
        
        elif admin_choice == "Waste Log":
            p_df = get_data("purchases")
            if not p_df.empty:
                with st.form("waste_log"):
                    w_item = st.selectbox("Item", p_df['item'].unique())
                    w_qty = st.number_input("Waste Qty", min_value=0.0)
                    # Use latest purchase price
                    w_pr = p_df[p_df['item'] == w_item].sort_values(by='id', ascending=False).iloc[0]['price']
                    if st.form_submit_button("Log Waste"):
                        save_entry("waste", {"item":w_item, "qty":w_qty, "cost_price":w_pr, "date":today, "month":this_month})

        elif admin_choice == "Supplier Bills":
            with st.form("sup_bill"):
                s_name = st.text_input("Supplier Name")
                b_amt = st.number_input("Bill Amount", min_value=0.0)
                p_amt = st.number_input("Paid Amount", min_value=0.0)
                if st.form_submit_button("Save Bill"):
                    save_entry("gas_supplier_bills", {"supplier_name":s_name, "bill_amount":b_amt, "paid_amount":p_amt, "date":today})

    else:
        st.error("Admin Access Only.")
