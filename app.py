import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime

# (ShopDB and other modules remain the same as previous stable version)

class FruitModule:
    def __init__(self, db, today, month):
        self.db = db
        self.today = today
        self.month = month

    def render(self):
        st.title("🍎 Fruit & Vegetable Shop")
        tab1, tab2, tab3 = st.tabs(["🛒 Sales", "📦 Inventory", "🗑️ Waste Log"])

        # --- 🛒 SALES TAB ---
        with tab1:
            p_df = self.db.fetch("purchases")
            items = sorted(p_df['item'].unique().tolist()) if not p_df.empty else []
            selected = st.selectbox("Select Item to Sell", ["Select..."] + items, key="sale_select")
            
            if selected != "Select...":
                s_df = self.db.fetch("sales")
                w_df = self.db.fetch("waste")
                # Stock Logic: Purchases - Sales - Waste
                in_q = p_df[p_df['item'] == selected]['qty'].sum()
                out_q = s_df[s_df['item'] == selected]['qty'].sum() if not s_df.empty else 0
                lost_q = w_df[w_df['item'] == selected]['qty'].sum() if not w_df.empty else 0
                stock = float(in_q) - float(out_q) - float(lost_q)
                
                st.info(f"Available Stock: **{stock} kg**")
                with st.form("fruit_sale"):
                    q = st.number_input("Qty (kg)", min_value=0.0)
                    p = st.number_input("Price (PKR)", min_value=0.0)
                    if st.form_submit_button("Complete Sale"):
                        if 0 < q <= stock:
                            self.db.push("sales", {"item":selected, "qty":q, "price":p, "date":self.today, "month":self.month})
                        else: st.error("Insufficient Stock!")

        # --- 📦 INVENTORY TAB ---
        with tab2:
            st.subheader("Add New Stock Received")
            with st.form("fruit_stock"):
                i = st.text_input("Item Name (e.g., Apple, Banana)")
                q = st.number_input("Qty Received (kg)", min_value=0.0)
                p = st.number_input("Purchase Price (Per kg)", min_value=0.0)
                if st.form_submit_button("Save Stock"):
                    if i and q > 0:
                        self.db.push("purchases", {"item":i.strip(), "qty":q, "price":p, "date":self.today, "month":self.month})
                    else: st.error("Please enter valid item and quantity")

        # --- 🗑️ WASTE LOG TAB (FIXED) ---
        with tab3:
            st.subheader("Log Spoiled/Wasted Items")
            p_df = self.db.fetch("purchases")
            
            if p_df.empty:
                st.warning("No items in inventory to log waste.")
            else:
                items = sorted(p_df['item'].unique().tolist())
                with st.form("waste_form"):
                    w_item = st.selectbox("Which item was wasted?", items)
                    w_qty = st.number_input("Quantity Wasted (kg)", min_value=0.0, step=0.1)
                    
                    # Automatically find the latest purchase price to calculate loss
                    item_purchases = p_df[p_df['item'] == w_item].sort_values(by='id', ascending=False)
                    latest_cost = float(item_purchases.iloc[0]['price']) if not item_purchases.empty else 0
                    
                    st.caption(f"Estimated Loss: Rs. {w_qty * latest_cost:,.0f} (Based on latest purchase price)")
                    
                    if st.form_submit_button("Record Waste"):
                        if w_qty > 0:
                            waste_data = {
                                "item": w_item,
                                "qty": w_qty,
                                "cost_price": latest_cost,
                                "date": self.today,
                                "month": self.month
                            }
                            self.db.push("waste", waste_data)
                        else:
                            st.error("Quantity must be greater than 0")

# (Rest of the Router/Main code remains the same)
