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

today = datetime.now().strftime("%Y-%m-%d")
this_month = datetime.now().strftime("%Y-%m")

# --- 4. CORE FUNCTIONS ---
def save_entry(table, data):
    data_str = json.dumps(data)
    local_c.execute("INSERT INTO sync_queue (table_name, data_json, timestamp) VALUES (?,?,?)", 
                  (table, data_str, datetime.now().isoformat()))
    local_conn.commit()
    try:
        supabase.table(table).insert(data).execute()
        local_c.execute("DELETE FROM sync_queue WHERE table_name = ? AND data_json = ?", (table, data_str))
        local_conn.commit()
        st.success("✅ Saved & Synced!")
    except:
        st.warning("⚠️ Saved Locally (Offline).")

def get_cloud_data(table):
    try:
        res = supabase.table(table).select("*").execute()
        df = pd.DataFrame(res.data)
        if not df.empty and 'item' in df.columns:
            df['item'] = df['item'].str.strip()
        return df
    except:
        return pd.DataFrame()

# --- 5. SYNC MANAGER ---
pending = local_c.execute("SELECT COUNT(*) FROM sync_queue").fetchone()[0]
if pending > 0:
    st.sidebar.warning(f"📡 {pending} Items to Sync")
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

# --- 6. NAVIGATION ---
st.title(f"🍎 {role} Dashboard")

if role == "Admin":
    menu = ["Sales", "Stock In", "Stock Adjustment", "Waste Log", "Expenses", "Customer Ledger", "Supplier Billing", "Profit Reports"]
else:
    menu = ["Sales", "Waste Log"]
choice = st.selectbox("Action Menu", menu)

# --- 7. FEATURES ---

if choice == "Sales":
    st.subheader("🛒 Quick Sale")
    p_df = get_cloud_data("purchases")
    s_df = get_cloud_data("sales")
    w_df = get_cloud_data("waste")
    a_df = get_cloud_data("stock_adjustments")
    
    available_items = ["Select Item"]
    if not p_df.empty:
        available_items += sorted(p_df['item'].unique().tolist())
    
    selected_item = st.selectbox("Select Fruit/Veg", available_items)
    
    # --- CALCULATION WITH ADJUSTMENTS ---
    current_stock = 0.0
    if selected_item != "Select Item":
        # 1. Start with the most recent manual adjustment if it exists
        if not a_df.empty and selected_item in a_df['item'].values:
            last_adj = a_df[a_df['item'] == selected_item].sort_values(by='id', ascending=False).iloc[0]
            base_qty = float(last_adj['new_quantity'])
            adj_date = last_adj['date']
            
            # Only subtract sales/waste that happened AFTER the adjustment date
            sold = s_df[(s_df['item'] == selected_item) & (s_df['date'] >= adj_date)]['qty'].sum() if not s_df.empty else 0
            wasted = w_df[(w_df['item'] == selected_item) & (w_df['date'] >= adj_date)]['qty'].sum() if not w_df.empty else 0
            purchased = p_df[(p_df['item'] == selected_item) & (p_df['date'] > adj_date)]['qty'].sum() if not p_df.empty else 0
            current_stock = base_qty + purchased - sold - wasted
        else:
            # 2. Standard calculation if no manual adjustment exists
            p_sum = p_df[p_df['item'] == selected_item]['qty'].sum() if not p_df.empty else 0
            s_sum = s_df[s_df['item'] == selected_item]['qty'].sum() if not s_df.empty else 0
            w_sum = w_df[w_df['item'] == selected_item]['qty'].sum() if not w_df.empty else 0
            current_stock = float(p_sum) - float(s_sum) - float(w_sum)
        
        # UI Alerts
        if current_stock <= 0: st.error(f"❌ OUT OF STOCK | {current_stock} kg")
        elif current_stock < 10: st.warning(f"⚠️ LOW STOCK | {current_stock} kg")
        else: st.info(f"✅ IN STOCK | {current_stock} kg")

    with st.form("sale_form", clear_on_submit=True):
        qty_to_sell = st.number_input("Quantity", min_value=0.0, step=0.5)
        price_per = st.number_input("Selling Price", min_value=0.0, step=1.0)
        mode = st.radio("Payment", ["Cash", "Credit"])
        
        cust = "N/A"
        if mode == "Credit":
            c_df = get_cloud_data("customers")
            c_list = c_df['name'].tolist() if not c_df.empty else ["No Customers"]
            cust = st.selectbox("Customer", c_list)
        
        if st.form_submit_button("Confirm Sale"):
            if selected_item != "Select Item" and qty_to_sell <= current_stock:
                save_entry("sales", {"item":selected_item,"qty":qty_to_sell,"price":price_per,"type":mode,"customer":cust,"date":today,"month":this_month})
                st.rerun()

elif choice == "Stock Adjustment":
    st.subheader("🔧 Manual Inventory Override")
    st.write("Use this to correct the stock count to match what is physically in the shop.")
    p_df = get_cloud_data("purchases")
    if not p_df.empty:
        with st.form("adj_form", clear_on_submit=True):
            adj_item = st.selectbox("Item to Adjust", sorted(p_df['item'].unique().tolist()))
            new_val = st.number_input("Actual Physical Quantity in Shop", min_value=0.0)
            reason = st.text_input("Reason (e.g., Weight loss, Manual Count)")
            if st.form_submit_button("Force Update Stock"):
                save_entry("stock_adjustments", {"item":adj_item, "new_quantity":new_val, "reason":reason, "date":today})

# --- ALL OTHER ADMIN FEATURES (STOCK IN, BILLING, ETC.) REMAIN THE SAME ---
