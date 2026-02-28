import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime
import sqlite3
import json

# --- 1. LOCAL BUFFER (OFFLINE DATABASE) ---
# This file stays on the device to save data if internet fails
local_conn = sqlite3.connect('offline_buffer.db', check_same_thread=False)
local_c = local_conn.cursor()
local_c.execute('''CREATE TABLE IF NOT EXISTS sync_queue 
                 (id INTEGER PRIMARY KEY, table_name TEXT, data_json TEXT, timestamp TEXT)''')
local_conn.commit()

# --- 2. CLOUD CONNECTION ---
# Replace these with your actual keys or use Streamlit Secrets
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

# Configuration (Change these!)
ADMIN_PW = "owner786"
STAFF_PW = "staff123"

auth = False
if role == "Admin" and pwd == ADMIN_PW: auth = True
elif role == "Operator" and pwd == STAFF_PW: auth = True

if not auth:
    st.info("Enter password in the sidebar to start.")
    st.stop()

# --- 4. GLOBAL TIME HELPERS ---
today = datetime.now().strftime("%Y-%m-%d")
this_month = datetime.now().strftime("%Y-%m")

# --- 5. CORE ENGINE FUNCTIONS ---
def save_entry(table, data):
    """The 'Safety Net' Save: Local First, then Cloud"""
    data_str = json.dumps(data)
    local_c.execute("INSERT INTO sync_queue (table_name, data_json, timestamp) VALUES (?,?,?)", 
                  (table, data_str, datetime.now().isoformat()))
    local_conn.commit()
    try:
        supabase.table(table).insert(data).execute()
        local_c.execute("DELETE FROM sync_queue WHERE table_name = ? AND data_json = ?", (table, data_str))
        local_conn.commit()
        st.success("✅ Recorded & Cloud Synced!")
    except:
        st.warning("⚠️ Offline: Saved on device. Please sync later.")

def get_cloud_data(table):
    """Fetches data from Supabase Cloud"""
    try:
        res = supabase.table(table).select("*").execute()
        return pd.DataFrame(res.data)
    except:
        return pd.DataFrame()

# --- 6. OFFLINE SYNC MANAGER ---
pending = local_c.execute("SELECT COUNT(*) FROM sync_queue").fetchone()[0]
if pending > 0:
    st.sidebar.error(f"📡 {pending} Items Offline")
    if st.sidebar.button("🔄 Sync Now (Requires Wi-Fi)"):
        rows = local_c.execute("SELECT id, table_name, data_json FROM sync_queue").fetchall()
        for rid, t_name, d_json in rows:
            try:
                payload = json.loads(d_json)
                supabase.table(t_name).insert(payload).execute()
                local_c.execute("DELETE FROM sync_queue WHERE id = ?", (rid,))
                local_conn.commit()
            except:
                st.sidebar.warning("Connection failed. Still offline.")
                break
        st.rerun()

# --- 7. DASHBOARD UI ---
st.title(f"🍎 Fresh Stock Dashboard - {role}")

# Navigation
if role == "Admin":
    menu = ["Sales", "Stock In", "Waste Log", "Expenses", "Customer Debt", "Profit Reports"]
else:
    menu = ["Sales", "Stock In", "Waste Log"]
choice = st.selectbox("Action Menu", menu)

# --- 8. FEATURE SECTIONS ---

if choice == "Sales":
    st.subheader("🛒 Record New Sale")
    with st.form("sale_form", clear_on_submit=True):
        item = st.text_input("Item Name (e.g., Tomato)")
        qty = st.number_input("Quantity", min_value=0.0)
        pr = st.number_input("Selling Price (per kg/unit)", min_value=0.0)
        mode = st.radio("Payment Type", ["Cash", "Credit"])
        
        # Customer select for credit sales
        c_list = ["N/A"]
        c_df = get_cloud_data("customers")
        if not c_df.empty: c_list += c_df['name'].tolist()
        cust = st.selectbox("Select Customer (for Credit)", c_list)
        
        if st.form_submit_button("Log Sale"):
            save_entry("sales", {"item":item,"qty":qty,"price":pr,"type":mode,"customer":cust,"date":today,"month":this_month})

elif choice == "Stock In":
    st.subheader("🚚 Purchase New Inventory")
    with st.form("p_form", clear_on_submit=True):
        p_item = st.text_input("Item Name")
        p_qty = st.number_input("Qty Purchased", min_value=0.0)
        p_cost = st.number_input("Wholesale Price (Total Cost)", min_value=0.0)
        if st.form_submit_button("Update Stock"):
            save_entry("purchases", {"item":p_item,"qty":p_qty,"price":p_cost,"date":today,"month":this_month})

elif choice == "Waste Log":
    st.subheader("🗑️ Record Spoilage/Damage")
    with st.form("w_form", clear_on_submit=True):
        w_item = st.text_input("Item Name")
        w_qty = st.number_input("Qty Spoiled", min_value=0.0)
        w_cost = st.number_input("Cost per unit", min_value=0.0)
        if st.form_submit_button("Record Waste"):
            save_entry("waste", {"item":w_item,"qty":w_qty,"cost_price":w_cost,"date":today,"month":this_month})

elif choice == "Expenses":
    st.subheader("💸 Record Shop Expenses")
    with st.form("e_form", clear_on_submit=True):
        cat = st.selectbox("Category", ["Business (Rent/Wages)", "Personal (Drawings)"])
        amt = st.number_input("Amount Paid", min_value=0.0)
        note = st.text_input("Description")
        if st.form_submit_button("Save Expense"):
            save_entry("expenses", {"category":cat,"amount":amt,"description":note,"date":today,"month":this_month})

elif choice == "Customer Debt":
    t1, t2, t3 = st.tabs(["Add Customer", "Receive Payment", "90-Day Statement"])
    with t1:
        new_c = st.text_input("Full Name")
        if st.button("Register New Customer"):
            save_entry("customers", {"name": new_c})
    with t2:
        c_df = get_cloud_data("customers")
        if not c_df.empty:
            target = st.selectbox("Paying Customer", c_df['name'].tolist())
            p_amt = st.number_input("Amount Received", min_value=0.0)
            if st.button("Log Payment"):
                save_entry("collections", {"customer":target, "amount":p_amt, "date_paid":today})
    with t3:
        st.info("Check customer balance and itemized history.")
        # Statement Logic
        all_s = get_cloud_data("sales")
        all_p = get_cloud_data("collections")
        if not all_s.empty:
            sel_c = st.selectbox("View History for:", c_df['name'].tolist() if not c_df.empty else [])
            c_history = all_s[(all_s['customer'] == sel_c) & (all_s['type'] == 'Credit')]
            total_owed = (c_history['qty'].astype(float) * c_history['price'].astype(float)).sum()
            total_paid = all_p[all_p['customer'] == sel_c]['amount'].sum() if not all_p.empty else 0
            st.metric("Balance Owed", f"${total_owed - total_paid:,.2f}")
            st.dataframe(c_history[['date', 'item', 'qty', 'price']])

elif choice == "Profit Reports":
    st.header("📈 Financial Performance")
    s_df = get_cloud_data("sales")
    p_df = get_cloud_data("purchases")
    
    if not s_df.empty:
        s_df['rev'] = s_df['qty'].astype(float) * s_df['price'].astype(float)
        st.metric("Total Revenue", f"${s_df['rev'].sum():,.2f}")
        st.subheader("Profit by Month")
        st.line_chart(s_df.groupby('month')['rev'].sum())
        
        # Leaderboard
        st.subheader("🏆 Top Selling Items")
        st.bar_chart(s_df.groupby('item')['qty'].sum())
    else:
        st.warning("No data found in cloud. Sync your offline items first.")
