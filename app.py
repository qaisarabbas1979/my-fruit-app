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
        if not df.empty:
            # Clean item names to prevent spelling/case errors
            if 'item' in df.columns:
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
    menu = ["Sales", "Stock In", "Waste Log", "Expenses", "Customer Ledger", "Supplier Billing", "Profit Reports"]
else:
    menu = ["Sales", "Waste Log"]
choice = st.selectbox("Action Menu", menu)

# --- 7. FEATURES ---

if choice == "Sales":
    st.subheader("🛒 Quick Sale")
    
    # FETCH ALL DATA
    p_df = get_cloud_data("purchases")
    s_df = get_cloud_data("sales")
    w_df = get_cloud_data("waste")
    
    available_items = ["Select Item"]
    if not p_df.empty:
        available_items += sorted(p_df['item'].unique().tolist())
    
    # 1. ITEM SELECTION (Outside the form to allow stock calculation to refresh)
    selected_item = st.selectbox("Select Fruit/Veg", available_items)
    
    # 2. CALCULATION
    current_stock = 0.0
    if selected_item != "Select Item":
        # Sum Purchases
        total_p = p_df[p_df['item'] == selected_item]['qty'].sum() if not p_df.empty else 0
        # Sum Sales
        total_s = s_df[s_df['item'] == selected_item]['qty'].sum() if not s_df.empty else 0
        # Sum Waste
        total_w = w_df[w_df['item'] == selected_item]['qty'].sum() if not w_df.empty else 0
        
        current_stock = float(total_p) - float(total_s) - float(total_w)
        
        # Display Stock Box
        if current_stock <= 0:
            st.error(f"❌ **OUT OF STOCK** | Current: {current_stock} kg")
        elif current_stock < 10:
            st.warning(f"⚠️ **LOW STOCK** | Only {current_stock} kg left!")
        else:
            st.info(f"✅ **IN STOCK** | Available: {current_stock} kg")

    # 3. SALE FORM
    with st.form("sale_form", clear_on_submit=True):
        qty_to_sell = st.number_input("Quantity to Sell", min_value=0.0, step=0.5)
        price_per = st.number_input("Selling Price (Total)", min_value=0.0, step=1.0)
        mode = st.radio("Payment Mode", ["Cash", "Credit"])
        
        cust = "N/A"
        if mode == "Credit":
            c_df = get_cloud_data("customers")
            c_list = c_df['name'].tolist() if not c_df.empty else ["No Customers Registered"]
            cust = st.selectbox("Select Customer", c_list)
        
        if st.form_submit_button("Confirm Sale"):
            if selected_item == "Select Item":
                st.error("Please select an item first!")
            elif qty_to_sell > current_stock:
                st.error(f"Transaction Denied: Not enough stock ({current_stock} available).")
            elif qty_to_sell <= 0:
                st.error("Quantity must be greater than 0.")
            else:
                sale_data = {"item":selected_item,"qty":qty_to_sell,"price":price_per,"type":mode,"customer":cust,"date":today,"month":this_month}
                save_entry("sales", sale_data)
                st.rerun()

# --- OTHER SECTIONS (STOCK IN, WASTE, ETC) STAY THE SAME ---
elif choice == "Stock In":
    st.subheader("🚚 Wholesale Purchases")
    with st.form("p_form", clear_on_submit=True):
        p_item = st.text_input("Item Name (e.g. Mango)").strip()
        p_qty = st.number_input("Qty Purchased", min_value=0.0)
        p_cost = st.number_input("Purchase Price (Per Unit)", min_value=0.0)
        if st.form_submit_button("Add to Stock"):
            save_entry("purchases", {"item":p_item,"qty":p_qty,"price":p_cost,"date":today,"month":this_month})

elif choice == "Waste Log":
    st.subheader("🗑️ Record Spoilage")
    with st.form("w_form", clear_on_submit=True):
        p_df = get_cloud_data("purchases")
        w_items = ["Select Item"]
        if not p_df.empty: w_items += sorted(p_df['item'].unique().tolist())
        w_item = st.selectbox("Item", w_items)
        w_qty = st.number_input("Qty", min_value=0.0)
        w_cost = st.number_input("Cost Price", min_value=0.0)
        if st.form_submit_button("Log Waste"):
            save_entry("waste", {"item":w_item,"qty":w_qty,"cost_price":w_cost,"date":today,"month":this_month})
