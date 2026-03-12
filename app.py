"""
Aviation ERP Admin Portal - Professional Flask + Supabase
Tables: aviation_inventory, suppliers, sales, stock_logs
Features: Dashboard metrics, Issue Item (atomic), Stock w/ Suppliers dropdown, Order View, Stock History
Fixed Bootstrap import - uses CDN
Gunicorn production ready for Render deployment
"""

import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from database import get_supabase_service_client
from datetime import datetime
from dotenv import load_dotenv

# Load .env
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev-secret-change-me')
# Bootstrap via CDN in base.html - no flask_bootstrap needed

def get_supabase():
    """Get Supabase service client (SUPABASE_SERVICE_KEY)."""
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

@app.route('/')
def root():
    """Root landing."""
    return render_template('base.html', greeting=get_greeting(), page_title="Aviation ERP")

@app.route('/admin')
@app.route('/admin/dashboard')
def admin_dashboard():
    """Admin Dashboard - Metrics."""
    try:
        supabase = get_supabase()
        
        # Total inventory value
        inventory = supabase.table('aviation_inventory').select('SUM(current_stock * COALESCE(unit_price_usd, 0)) as total_value, COUNT(*) as item_count').execute()
        total_value = float(inventory.data[0]['total_value'] if inventory.data else 0)
        total_items = int(inventory.data[0]['item_count'] if inventory.data else 0)
        
        # Low stock alerts (current_stock < 10)
        low_stock = supabase.table('aviation_inventory').select('*').lt('current_stock', 10).execute().data or []
        
        context = {
            'greeting': get_greeting(),
            'total_inventory_value': f"${total_value:,.2f}",
            'total_items': total_items,
            'low_stock_count': len(low_stock),
            'low_stock_items': low_stock[:10]
        }
        return render_template('admin_dashboard.html', **context)
    except Exception as e:
        print(f"Dashboard error: {e}")
        flash(f'Dashboard error: {str(e)}', 'danger')
        return render_template('admin_dashboard.html', greeting=get_greeting())

@app.route('/stock-management', methods=['GET'])
def stock_management():
    # 1. Fetch suppliers from Supabase
    response = supabase.table('suppliers').select('id, supplier_name').execute()
    suppliers_list = response.data  # This is the list of suppliers
    
    # 2. Fetch current stock to show in the table
    stock_response = supabase.table('aviation_inventory').select('*').execute()
    inventory = stock_response.data

    # 3. PASS BOTH TO THE HTML
    return render_template('stock_management.html', 
                           suppliers=suppliers_list, 
                           inventory=inventory)

@app.route('/view-order/<order_id>')
@app.route('/print-order/<order_id>')
def view_order(order_id):
    """View/Print specific completed order from sales table."""
    try:
        supabase = get_supabase()
        
        # Query sales with aviation_inventory join using .eq('id', order_id)
        order_resp = supabase.table('sales').select('*, aviation_inventory(*)').eq('id', order_id).execute()
        
        if not order_resp.data:
            flash('Order ID ' + order_id + ' not found in Sales table.', 'warning')
            return redirect(url_for('root'))
        
        order = order_resp.data[0]
        return render_template('order_print.html', order=order)
    except Exception as e:
        print(f"View/Print order error: {e}")
        flash(f'Order view error: {str(e)}', 'warning')
        return redirect(url_for('root'))

@app.route('/stock-history')
def stock_history():
    """Stock history: all records from stock_logs (desc) joined with aviation_inventory for descriptions."""
    try:
        supabase = get_supabase()
        
        # Fetch all stock_logs ordered desc, with aviation_inventory join for description
        history_resp = supabase.table('stock_logs').select("""
            *,
            aviation_inventory(description)
        """).order('created_at', direction='desc').execute()
        history = history_resp.data or []
        
        return render_template('stock_logs.html', logs=history, greeting=get_greeting())
    except Exception as e:
        print(f"Stock history error: {e}")
        flash(f'Stock history error: {str(e)}', 'danger')
        return render_template('stock_logs.html', logs=[], greeting=get_greeting())

@app.route('/admin/stock')
def admin_stock():
    """Legacy redirect to new stock-management."""
    flash('Redirected to new stock management page', 'info')
    return redirect(url_for('stock_management'))

if __name__ == '__main__':
    print("🚀 Aviation ERP Admin Portal - Render Deployment Ready")
    print("📊 Dashboard: http://localhost:5000/admin")
    print("📦 Stock Mgmt: http://localhost:5000/stock-management") 
    print("📜 View Order: http://localhost:5000/view-order/[order_id]")
    print("📈 Stock History: http://localhost:5000/stock-history")
    print("📦 Deploy: gunicorn app:app")
    app.run(debug=True, host='0.0.0.0', port=5000)

