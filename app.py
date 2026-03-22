import streamlit as st
import requests
import pandas as pd
import uuid
import datetime
import time
import os

# --- Configuration & Styling ---
API_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")
st.set_page_config(page_title="E-Commerce Admin", page_icon="🛍️", layout="wide", initial_sidebar_state="expanded")

# --- Sidebar Navigation ---
st.sidebar.title("🛍️ Admin Panel")
st.sidebar.markdown("Manage your store inventory.")
menu = st.sidebar.radio("Navigation", ["📊 Dashboard Overview", "📦 Manage Products", "⚙️ System Health"])

# --- Helper Function ---
# @st.cache_data(ttl=5)
def fetch_products():
    try:
        res = requests.get(f"{API_URL}/products?limit=1000")
        if res.status_code == 200:
            return res.json().get("items", [])
    except:
        return None
    return []

# ==========================================
# PAGE 1: DASHBOARD OVERVIEW
# ==========================================
if menu == "📊 Dashboard Overview":
    st.title("Dashboard Overview")
    
    # # Add a page selector in the UI
    # page_number = st.number_input("Page", min_value=1, value=1)
    
    # # Calculate offset (Page 1 = 0 offset, Page 2 = 100 offset)
    # current_offset = (page_number - 1) * 100 
    
    # # Fetch exactly that page's data
    # res = requests.get(f"{API_URL}/products?limit=100&offset={current_offset}")
    # products = res.json().get("items", []) if res.status_code == 200 else []
    
    products = fetch_products()
    
    if products is None:
        st.error("🚨 Cannot connect to FastAPI backend. Is it running?")
    elif not products:
        st.info("No products in inventory. Go to 'Manage Products' to add some.")
    else:
        # Calculate KPIs
        total_products = len(products)
        total_value = sum(p.get("price", 0) * p.get("stock", 0) for p in products)
        out_of_stock = sum(1 for p in products if p.get("stock", 0) == 0)
        
        # Display Metric Cards
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Products", total_products)
        col2.metric("Total Inventory Value", f"₹ {total_value:,.2f}")
        col3.metric("Out of Stock Items", out_of_stock, delta="- Restock Needed" if out_of_stock > 0 else "Healthy", delta_color="inverse")
        
        st.divider()

       # Display Clean Data Table
        st.subheader("Current Inventory")
        df = pd.DataFrame(products)
        
        # 1. Create a dynamic 'Status' column
        def get_status(row):
            if row['stock'] == 0 or not row.get('is_active', True):
                return "🔴 Out of Stock"
            elif row['stock'] < 5:
                return f"🟠 Low Stock ({row['stock']})"
            else:
                return f"🟢 In Stock ({row['stock']})"
                
        df['Status'] = df.apply(get_status, axis=1)

        # 2. Reorganize the columns for a clean UI
        display_cols = ["id", "sku", "name", "category", "price", "Status", "rating"]
        existing_cols = [c for c in display_cols if c in df.columns]
        
        # 3. Display the upgraded table
        st.dataframe(
            df[existing_cols], 
            use_container_width=True, 
            hide_index=True
        )

# ==========================================
# PAGE 2: MANAGE PRODUCTS (CRUD)
# ==========================================
elif menu == "📦 Manage Products":
    st.title("Product Management")
    
    # Use Tabs for cleaner UI
    tab_add, tab_edit, tab_delete = st.tabs(["➕ Add Product", "✏️ Edit Product", "🗑️ Delete Product"])
    
    # --- ADD PRODUCT TAB ---
    with tab_add:
        st.subheader("Create New Product")
        with st.form("create_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                c_name = st.text_input("Product Name", placeholder="e.g. Xiaomi Model Pro")
                c_brand = st.text_input("Brand", placeholder="e.g. Xiaomi")
                c_category = st.text_input("Category", placeholder="e.g. laptops")
            with col2:
                c_price = st.number_input("Price (₹)", min_value=1.0, value=15000.0)
                c_stock = st.number_input("Initial Stock", min_value=0, value=10)
                c_rating = st.slider("Initial Rating", 0.0, 5.0, 4.5)
            
            c_instock = st.checkbox("Set as Active", value=True)
            submit_create = st.form_submit_button("🚀 Create Product", type="primary")
            
            if submit_create:
                payload = {
                    "id": str(uuid.uuid4()),  # 👈 Added ID
                    "created_at": datetime.datetime.utcnow().isoformat() + "Z", # 👈 Added Timestamp
                    "sku": f"DUMO-{uuid.uuid4().hex[:3].upper()}-001", 
                    "name": c_name,
                    "description": "Auto-generated dummy description for UI creation.",
                    "category": c_category,
                    "brand": c_brand,
                    "price": c_price,
                    "rating": c_rating,
                    "stock": c_stock,
                    "is_active": c_instock,
                    "tags": ["demo"],
                    "image_urls": ["https://cdn.example.com/dummy.png"],
                    "dimensions_cm": {"length": 10.0, "width": 10.0, "height": 10.0},
                    "seller": {
                        "id": str(uuid.uuid4()),
                        "name": "Mi Store",
                        "email": "support@mistore.in", 
                        "website": "https://www.mistore.in"
                    }
                }
                res = requests.post(f"{API_URL}/products", json=payload)
                if res.status_code == 201:
                    st.success(f"Successfully added {c_name}!")
                    # st.cache_data.clear()
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(f"Error: {res.text}")

    # --- EDIT PRODUCT TAB ---
    with tab_edit:
        st.subheader("Update Existing Product")
        ud_id = st.text_input("Enter Product UUID to Edit")
        if ud_id:
            with st.form("update_form"):
                u_name = st.text_input("New Name (leave blank to skip)")
                u_price = st.number_input("New Price (set to 0 to skip)", min_value=0.0, value=0.0)
                u_stock = st.number_input("Update Stock (set to -1 to skip)", min_value=-1, value=-1)
                u_active = st.selectbox("Set Active Status", options=["(skip)", "True", "False"])
                
                submit_update = st.form_submit_button("💾 Save Changes")
                if submit_update:
                    update_payload = {}
                    if u_name: update_payload["name"] = u_name
                    if u_price > 0: update_payload["price"] = u_price
                    
                    if u_stock != -1: 
                        update_payload["stock"] = u_stock
                    if u_active != "(skip)": 
                        update_payload["is_active"] = True if u_active == "True" else False
                    
                    if update_payload:
                        res = requests.put(f"{API_URL}/products/{ud_id}", json=update_payload)
                        if res.status_code == 200:
                            st.success("Product updated successfully!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error(f"Update failed: {res.text}")
                    else:
                        st.warning("No changes provided.")

    # --- DELETE PRODUCT TAB ---
    with tab_delete:
        st.subheader("Danger Zone")
        del_id = st.text_input("Enter Product UUID to Delete")
        if st.button("🗑️ Permanently Delete Product", type="primary"):
            if del_id:
                res = requests.delete(f"{API_URL}/products/{del_id}")
                if res.status_code == 200:
                    st.success("Product deleted.")
                    # st.cache_data.clear()
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(f"Delete failed: {res.text}")

# ==========================================
# PAGE 3: SYSTEM HEALTH
# ==========================================
elif menu == "⚙️ System Health":
    st.title("System Diagnostics")
    if st.button("Run Health Check"):
        try:
            res = requests.get(f"{API_URL}/")
            st.success("🟢 FastAPI Backend is Online")
            st.json(res.json())
        except Exception as e:
            st.error(f"🔴 Backend Offline: {e}")