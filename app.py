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

# --- 4. DATA HELPERS ---
def get_cloud_data(table):
    try:
        res = supabase.table(table).select("*").execute()
        df = pd.DataFrame(res.data)
        if not df.empty and 'item' in df.columns:
            df['item'] = df['item'].str.strip()
        return df
    except:
        return pd.DataFrame()

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

# --- 6. ADMIN CASH SUMMARY (PKR) ---
if role == "Admin":
    st.markdown("### 💰 Today's Cash Position (PKR)")
    s_all = get_cloud_data("sales")
    e_all = get_cloud_data("expenses")
    c_all = get_cloud_data("collections")
    
    cash_sales = 0.0
    expenses = 0.0
    debt_collected = 0.0
    
    if not s_all.empty:
        day_s = s_all[s_all['date'] == today]
        cash_sales = (day_s[day_s['type'] == 'Cash']['qty'].astype(float) * day_s[day_s['type'] == 'Cash']['price'].astype(float)).sum()
    
    if not e_all.empty:
        expenses = e_all[e_all['date'] == today]['amount'].sum()
        
    if not c_all.empty:
        debt_collected = c_all[c_all['date_paid'] == today]['amount'].sum()
        
    net_cash = cash_sales + debt_collected - expenses
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Cash Sales", f"Rs. {cash_sales:,.0f}")
    col2.metric("Expenses Paid", f"-Rs. {expenses:,.0f}", delta_color="inverse")
    col3.metric("Net Cash in Drawer", f"Rs. {net_cash:,.0f}")
    st.divider()

# --- 7. NAVIGATION ---
if role == "Admin":
    menu = ["Sales", "Stock In", "Waste Log", "Stock Adjustment", "Expenses", "Customer Ledger", "Supplier Billing", "Profit Reports"]
else:
    menu = ["Sales"]
choice = st.selectbox("Action Menu", menu)

# --- 8. FEATURES ---

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
    
    current_stock = 0.0
    if selected_item != "Select Item":
        if not a_df.empty and selected_item in a_df['item'].values:
            last_adj = a_df[a_df['item'] == selected_item].sort_values(by='id', ascending=False).iloc[0]
            base_qty = float(last_adj['new_quantity'])
            adj_date = last_adj['date']
            sold = s_df[(s_df['item'] == selected_item) & (s_df['date'] >= adj_date)]['qty'].sum() if not s_df.empty else 0
            wasted = w_df[(w_df['item'] == selected_item) & (w_df['date'] >= adj_date)]['qty'].sum() if not w_df.empty else 0
            purchased = p_df[(p_df['item'] == selected_item) & (p_df['date'] > adj_date)]['qty'].sum() if not p_df.empty else 0
            current_stock = base_qty + purchased - sold - wasted
        else:
            p_sum = p_df[p_df['item'] == selected_item]['qty'].sum() if not p_df.empty else 0
            s_sum = s_df[s_df['item'] == selected_item]['qty'].sum() if not s_df.empty else 0
            w_sum = w_df[w_df['item'] == selected_item]['qty'].sum() if not w_df.empty else 0
            current_stock = float(p_sum) - float(s_sum) - float(w_sum)
        
        st.info(f"📦 Stock Level: **{current_stock} kg**")

    with st.form("sale_form", clear_on_submit=True):
        qty_to_sell = st.number_input("Quantity", min_value=0.0, step=0.5)
        price_per = st.number_input("Selling Price (PKR)", min_value=0.0, step=10.0)
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

elif choice == "Waste Log":
    st.subheader("🗑️ Record Spoilage")
    p_df = get_cloud_data("purchases")
    
    if p_df.empty:
        st.warning("No purchase records found. Add stock first to log waste.")
    else:
        # Auto-calculate cost based on latest purchase
        w_item_list = sorted(p_df['item'].unique().tolist())
        selected_w_item = st.selectbox("Item Spoiled", w_item_list)
        
        # Get the latest purchase price for this item
        latest_price = p_df[p_df['item'] == selected_w_item].sort_values(by='id', ascending=False).iloc[0]['price']
        st.write(f"ℹ️ Current Purchase Price: **Rs. {latest_price}**")

        with st.form("waste_form", clear_on_submit=True):
            w_qty = st.number_input("Quantity Spoiled (kg/unit)", min_value=0.0, step=0.1)
            # Automatic hidden calculation
            total_loss = w_qty * float(latest_price)
            st.info(f"💰 Calculated Loss: **Rs. {total_loss:,.0f}**")
            
            if st.form_submit_button("Log Spoilage"):
                save_entry("waste", {"item":selected_w_item, "qty":w_qty, "cost_price":latest_price, "date":today, "month":this_month})

elif choice == "Expenses":
    st.subheader("💸 Record Shop Expenses")
    with st.form("exp_form", clear_on_submit=True):
        amt = st.number_input("Amount Paid Out (PKR)", min_value=0.0, step=10.0)
        desc = st.text_input("Reason (e.g. Rent, Bags, Fuel)")
        if st.form_submit_button("Save Expense"):
            save_entry("expenses", {"amount":amt, "description":desc, "date":today, "month":this_month})

elif choice == "Profit Reports":
    st.header("📈 Financial Report (PKR)")
    s_df = get_cloud_data("sales")
    if not s_df.empty:
        s_df['rev'] = s_df['qty'].astype(float) * s_df['price'].astype(float)
        st.metric("Total Monthly Revenue", f"Rs. {s_df[s_df['month']==this_month]['rev'].sum():,.0f}")
        st.bar_chart(s_df.groupby('item')['rev'].sum())
