import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime
import sqlite3
import json

# --- 1. LOCAL BUFFER ---
local_conn = sqlite3.connect('offline_buffer.db', check_same_thread=False)
local_c = local_conn.cursor()
local_c.execute('''CREATE TABLE IF NOT EXISTS sync_queue 
                 (id INTEGER PRIMARY KEY, table_name TEXT, data_json TEXT, timestamp TEXT)''')
local_conn.commit()

# --- 2. CLOUD CONNECTION ---
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
except Exception:
    st.error("⚠️ Cloud Keys Missing! Go to Streamlit Settings > Secrets.")
    st.stop()

# --- 3. AUTHENTICATION ---
st.sidebar.title("🔐 Store Login")
role = st.sidebar.radio("Role", ["Operator", "Admin"])
pwd = st.sidebar.text_input("Password", type="password")

ADMIN_PW = "owner786"
STAFF_PW = "staff123"

if not ((role == "Admin" and pwd == ADMIN_PW) or (role == "Operator" and pwd == STAFF_PW)):
    st.info("Enter password in the sidebar to start.")
    st.stop()

# --- 4. TIME HELPERS ---
today = datetime.now().strftime("%Y-%m-%d")
this_month = datetime.now().strftime("%Y-%m")

# --- 5. CORE FUNCTIONS ---
def save_entry(table, data):
    data_str = json.dumps(data)
    local_c.execute("INSERT INTO sync_queue (table_name, data_json, timestamp) VALUES (?,?,?)", 
                  (table, data_str, datetime.now().isoformat()))
    local_conn.commit()
    try:
        supabase.table(table).insert(data).execute()
        local_c.execute("DELETE FROM sync_queue WHERE table_name = ? AND data_json = ?", (table, data_str))
        local_conn.commit()
        st.success("✅ Recorded & Synced!")
    except:
        st.warning("⚠️ Offline: Saved locally.")

def get_cloud_data(table):
    try:
        res = supabase.table(table).select("*").execute()
        return pd.DataFrame(res.data)
    except:
        return pd.DataFrame()

# --- 6. OFFLINE SYNC ---
pending = local_c.execute("SELECT COUNT(*) FROM sync_queue").fetchone()[0]
if pending > 0:
    st.sidebar.warning(f"📡 {pending} Items Waiting to Sync")
    if st.sidebar.button("🔄 Sync Now"):
        rows = local_c.execute("SELECT id, table_name, data_json FROM sync_queue").fetchall()
        for rid, t_name, d_json in rows:
            try:
                payload = json.loads(d_json)
                supabase.table(t_name).insert(payload).execute()
                local_c.execute("DELETE FROM sync_queue WHERE id = ?", (rid,))
                local_conn.commit()
            except: break
        st.rerun()

# --- 7. MAIN DASHBOARD ---
st.title(f"🍎 {role} Dashboard")

# UPDATED: Operator can no longer see 'Stock In' or 'Expenses'
if role == "Admin":
    menu = ["Sales", "Stock In", "Waste Log", "Expenses", "Customer Ledger", "Profit Reports"]
else:
    menu = ["Sales", "Waste Log"]
    
choice = st.selectbox("Action Menu", menu)

# --- 8. FEATURES ---

if choice == "Sales":
    st.subheader("🛒 Quick Sale")
    
    # FETCH ITEMS FROM PURCHASE HISTORY FOR DROPDOWN
    p_df = get_cloud_data("purchases")
    available_items = ["Select Item"]
    if not p_df.empty:
        available_items += sorted(p_df['item'].unique().tolist())
    
    with st.form("sale_form", clear_on_submit=True):
        item = st.selectbox("Select Fruit/Veg", available_items)
        qty = st.number_input("Quantity", min_value=0.0, step=0.5)
        pr = st.number_input("Selling Price", min_value=0.0, step=1.0)
        mode = st.radio("Payment Mode", ["Cash", "Credit"])
        
        # Smart Customer Logic
        cust = "N/A"
        if mode == "Credit":
            c_df = get_cloud_data("customers")
            c_list = c_df['name'].tolist() if not c_df.empty else ["No Customers Found"]
            cust = st.selectbox("Select Credit Customer", c_list)
        
        if st.form_submit_button("Log Sale"):
            if item == "Select Item":
                st.error("Please select an item first!")
            else:
                save_entry("sales", {"item":item,"qty":qty,"price":pr,"type":mode,"customer":cust,"date":today,"month":this_month})

elif choice == "Stock In":
    st.subheader("🚚 Wholesale Purchases (Admin Only)")
    with st.form("p_form", clear_on_submit=True):
        p_item = st.text_input("New Item Name (e.g. Apple)")
        p_qty = st.number_input("Qty Purchased", min_value=0.0)
        p_cost = st.number_input("Cost per Unit/kg", min_value=0.0)
        if st.form_submit_button("Add to Stock List"):
            save_entry("purchases", {"item":p_item,"qty":p_qty,"price":p_cost,"date":today,"month":this_month})

elif choice == "Waste Log":
    st.subheader("🗑️ Record Spoilage")
    with st.form("w_form", clear_on_submit=True):
        p_df = get_cloud_data("purchases")
        w_items = ["Select Item"]
        if not p_df.empty: w_items += sorted(p_df['item'].unique().tolist())
        
        w_item = st.selectbox("Item Name", w_items)
        w_qty = st.number_input("Qty Spoiled", min_value=0.0)
        w_cost = st.number_input("Original Cost Price (Reference)", min_value=0.0)
        if st.form_submit_button("Record Waste"):
            save_entry("waste", {"item":w_item,"qty":w_qty,"cost_price":w_cost,"date":today,"month":this_month})

elif choice == "Expenses":
    st.subheader("💸 Shop Expenses (Admin Only)")
    with st.form("e_form", clear_on_submit=True):
        cat = st.selectbox("Category", ["Business (Rent/Wages)", "Personal (Drawings)"])
        amt = st.number_input("Amount", min_value=0.0)
        note = st.text_input("Description")
        if st.form_submit_button("Save"):
            save_entry("expenses", {"category":cat,"amount":amt,"description":note,"date":today,"month":this_month})

elif choice == "Customer Ledger":
    t1, t2 = st.tabs(["Add Customer", "View Balances"])
    with t1:
        new_c = st.text_input("Full Name")
        if st.button("Register"):
            save_entry("customers", {"name": new_c})
    with t2:
        # Debt calculation logic would go here
        st.info("Check Supabase dashboard for full balances.")

elif choice == "Profit Reports":
    st.header("📈 Financial Performance")
    s_df = get_cloud_data("sales")
    if not s_df.empty:
        s_df['rev'] = s_df['qty'].astype(float) * s_df['price'].astype(float)
        st.metric("Total Revenue", f"${s_df['rev'].sum():,.2f}")
        st.bar_chart(s_df.groupby('item')['qty'].sum())
