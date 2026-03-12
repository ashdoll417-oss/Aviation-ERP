"""
Aviation ERP Admin Portal - Professional Flask + Supabase
Updated Stock Management w/ Suppliers Dropdown
"""

import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_bootstrap import Bootstrap5
from database import get_supabase_service_client
from datetime import datetime
from dotenv import load_dotenv

# Load .env
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev-secret-change-me')
bootstrap = Bootstrap5(app)

def get_supabase():
    """Get Supabase service client."""
    return get_supabase_service_client()

def get_greeting():
    """Time-based greeting."""
    hour = datetime.now().hour
    if 5 <= hour < 12:
        return "Good Morning, AISL Aviation Team"
    elif 12 <= hour < 18:
        return "Good Afternoon"
    else:
        return "Good Evening"

@app.route('/admin/stock')
def admin_stock():
    """Stock Management - Suppliers Dropdown + Inventory."""
    try:
        supabase = get_supabase()
        
        # 1. Fetch suppliers for dropdown
        suppliers_resp = supabase.table('suppliers').select('id, supplier_name').order('supplier_name').execute()
        suppliers = suppliers_resp.data or []
        
        # 2. Fetch inventory
        inventory_resp = supabase.table('aviation_inventory').select('*').order('part_number').execute()
        inventory = inventory_resp.data or []
        
        # 3. Add supplier names to inventory items (for display)
        supplier_map = {s['id']: s['supplier_name'] for s in suppliers}
        for item in inventory:
            item['supplier_name'] = supplier_map.get(item.get('preferred_supplier_id'), 'None')
        
        return render_template('stock.html',
                             greeting=get_greeting(),
                             suppliers=suppliers,  # Passed to template
                             inventory=inventory)  # For table display
        
    except Exception as e:
        flash(f'Error loading stock: {str(e)}', 'danger')
        return render_template('stock.html', suppliers=[], inventory=[])

# ... rest of existing routes (dashboard, issue-item, etc.) remain unchanged

if __name__ == '__main__':
    print("🚀 Aviation ERP - Stock Management Ready!")
    print("📱 Visit: http://localhost:5000/admin/stock")
    app.run(debug=True, host='0.0.0.0', port=5000)

