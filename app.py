import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime

# (ShopDB class remains the same)

# ==========================================
# MODULE 2: FRUIT BUSINESS (Role-Aware)
# ==========================================
class FruitModule:
    def __init__(self, db, today, month, role):
        self.db = db
        self.today = today
        self.month = month
        self.role = role

    def render(self):
        st.title("🍎 Fruit & Vegetable Shop")
        
        # Operators ONLY see Sales. Admins see everything.
        tabs = ["🛒 Sales"]
        if self.role == "Admin":
            tabs += ["📦 Inventory", "🗑️ Waste Log"]
            
        active_tabs = st.tabs(tabs)

        # --- SALES TAB (Always Visible) ---
        with active_tabs[0]:
            p_df = self.db.fetch("purchases")
            items = sorted(p_df['item'].unique().tolist()) if not p_df.empty else []
            selected = st.selectbox("Select Item", ["Select..."] + items)
            # ... (Sales logic code remains same)

        # --- ADMIN ONLY TABS ---
        if self.role == "Admin":
            with active_tabs[1]:
                st.subheader("Add Stock")
                # ... (Inventory logic code)
            with active_tabs[2]:
                st.subheader("Waste Log")
                # ... (Waste logic code)

# ==========================================
# MAIN ROUTER (The Security Gate)
# ==========================================
def main():
    if 'logged_in' not in st.session_state: st.session_state.logged_in = False
    if 'biz' not in st.session_state: st.session_state.biz = None
    if 'role' not in st.session_state: st.session_state.role = None

    db = ShopDB()
    today = datetime.now().strftime("%Y-%m-%d")
    month = datetime.now().strftime("%Y-%m")

    # SCREEN 1: LOGIN
    if not st.session_state.logged_in:
        st.title("🔐 Shop Login")
        pwd = st.text_input("Enter Password", type="password")
        if st.button("Enter Shop"):
            if pwd == "owner786":
                st.session_state.logged_in = True
                st.session_state.role = "Admin"
                st.rerun()
            elif pwd == "staff123":
                st.session_state.logged_in = True
                st.session_state.role = "Operator"
                st.rerun()
            else:
                st.error("Invalid Password")
        return

    # SCREEN 2: HUB
    if st.session_state.biz is None:
        st.title(f"👋 {st.session_state.role} Dashboard")
        c1, c2 = st.columns(2)
        if c1.button("🍎 Fruit Business"):
            st.session_state.biz = "Fruit"
            st.rerun()
        if c2.button("🔥 Gas Business"):
            st.session_state.biz = "Gas"
            st.rerun()
        if st.button("🚪 Logout"):
            st.session_state.logged_in = False
            st.rerun()
        return

    # SCREEN 3: OPERATION
    st.sidebar.title(f"📍 {st.session_state.biz}")
    
    # Hide Customer Nav from Operator
    nav_options = ["Store Operations"]
    if st.session_state.role == "Admin":
        nav_options.append("Customers")
    nav_options.append("Switch Business")

    nav = st.sidebar.radio("Menu", nav_options)

    if nav == "Switch Business":
        st.session_state.biz = None
        st.rerun()
    elif nav == "Customers":
        CustomerModule(db).render()
    elif nav == "Store Operations":
        if st.session_state.biz == "Fruit":
            # Passing 'role' to the module to hide internal tabs
            FruitModule(db, today, month, st.session_state.role).render()
        else:
            GasModule(db, today, st.session_state.role).render()

if __name__ == "__main__":
    main()
