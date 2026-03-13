"""
# Deployment Sync: 2026-03-13
Aviation ERP Admin Portal - Professional Flask + Supabase
Tables: aviation_inventory, suppliers, sales, stock_logs
Features: Dashboard metrics, Issue Item (atomic), Stock w/ Suppliers dropdown, Order View, Stock History
Fixed Bootstrap import - uses CDN
Gunicorn production ready for Render deployment
"""

import os
import barcode
from barcode.writer import ImageWriter
from io import BytesIO
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
from database import get_supabase_service_client
from datetime import datetime
from dotenv import load_dotenv

# Load .env
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev-secret-change-me')
# Bootstrap via CDN in base.html - no flask_bootstrap needed

@app.route('/api/stock/v2/update', methods=['POST', 'OPTIONS'], strict_slashes=False)
def update_stock_v2():
    if request.method == 'OPTIONS':
        return '', 200

    print("DEBUG: Incoming request to /api/stock/v2/update")
    
    try:
        data = request.get_json() or request.form or {}
        print(f"DEBUG: Incoming data: {data}")
        
        part_number = data.get('part_number')
        if not part_number:
            print("ERROR: Missing part_number")
            return jsonify({"success": False, "error": "part_number is required"}), 400
        
        new_quantity = data.get('new_quantity') or data.get('quantity') or data.get('qty') or 0
        print(f"DEBUG: Updating part_number='{part_number}' to current_stock={new_quantity}")
        
        if new_quantity == 0 and not data.get('new_quantity'):
            print("WARNING: No valid quantity provided")
        
        supabase_client = get_supabase()
        
        print("DEBUG: Executing Supabase update...")
        result = supabase_client.table('aviation_inventory').update({'current_stock': new_quantity}).eq('part_number', part_number).execute()
        print(f"DEBUG: Database response: {result}")
        
        if result.data:
            print("DEBUG: Update successful")
            return jsonify({"success": True, "message": "Stock updated successfully"}), 200
        else:
            print("WARNING: No rows updated - part_number not found")
            return jsonify({"success": False, "message": "Part number not found"}), 404
            
    except Exception as e:
        print(f"ERROR: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

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

@app.route('/purchase-order')
@app.route('/stock-management')
def manage_stock_and_po():
    # Fetch from 'suppliers' (plural)
    supabase = get_supabase()
    suppliers = supabase.table('suppliers').select('*').execute().data
    # Fetch from 'aviation_inventory'
    inventory = supabase.table('aviation_inventory').select('*').execute().data
    
    # Check which page we are on and send the data
    if request.path == '/purchase-order':
        return render_template('purchase_order.html', suppliers=suppliers, inventory=inventory)
    return render_template('stock_management.html', suppliers=suppliers, inventory=inventory)

@app.route('/view-order/<order_id>')
def view_order(order_id):
    # We query 'sales' table. If order_id is a string (ORD-001), use 'order_number' column
    # If it is a number, use 'id' column.
    supabase = get_supabase()
    res = supabase.table('sales').select('*, aviation_inventory(*)').eq('id', order_id).execute()
    
    if not res.data:
        return "<h1>Error: Order Not Found</h1><p>Check if the ID exists in the 'sales' table.</p>", 404
        
    return render_template('view_order.html', order=res.data[0])

@app.route('/add-stock', methods=['POST'])
def add_stock():
    category = request.form.get('category')
    unit = request.form.get('unit_type')
    raw_qty = float(request.form.get('quantity', 0))
    
    # The Calculator: Convert Inches to Yards for Carpets
    if category == 'Carpet' and unit == 'Inches':
        final_qty = raw_qty / 36
        unit_label = 'Yards'
    else:
        final_qty = raw_qty
        unit_label = unit

    # Save to Supabase
    supabase = get_supabase()
    new_item = {
        "part_number": request.form.get('part_number'),
        "description": request.form.get('description'),
        "current_stock": final_qty,
        "uom": unit_label,
        "color_type": request.form.get('color_type') if category == 'Carpet' else None,
        "supplier_id": request.form.get('supplier_id'),
        "min_threshold": request.form.get('min_threshold', 10)
    }
    supabase.table('aviation_inventory').insert(new_item).execute()
    
    flash('Stock item added successfully!', 'success')
    return redirect(url_for('manage_stock_and_po'))

@app.route('/stock-history')
def stock_history():
    """Stock history: all records from stock_logs (desc) joined with aviation_inventory for descriptions."""
    try:
        supabase = get_supabase()
        
        # Fetch stock_logs with optional search on part_number, always joined with aviation_inventory(description)
        query = supabase.table('stock_logs').select("""
            *,
            aviation_inventory(description)
        """).order('created_at', direction='desc')
        
        search_query = request.args.get('search', '')
        if search_query:
            query = query.ilike('part_number', f'%{search_query}%')
        
        history_resp = query.execute()
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

@app.route('/quote-generator', methods=['GET'])
def quote_generator():
    """Quote Generator - explicitly fetch all aviation_inventory for dropdowns."""
    try:
        supabase = get_supabase()
        
        # Fetch all items so 745XA and others show up in the dropdown
        inventory_res = supabase.table('aviation_inventory').select('*').execute()
        
        # Fetch all suppliers for the dropdown
        suppliers_res = supabase.table('suppliers').select('*').execute()
        
        return render_template('quote_generator.html', 
                               inventory=inventory_res.data or [],
                               suppliers=suppliers_res.data or [],
                               greeting=get_greeting())
    except Exception as e:
        print(f"Quote generator error: {e}")
        flash(f'Quote generator error: {str(e)}', 'danger')
        return render_template('quote_generator.html', inventory=[], suppliers=[], greeting=get_greeting())

@app.route('/usage-reports')
def usage_reports():
    """Usage Reports Route: Query sales table, join inventory, render template w/ report_data (no JSON)."""
    try:
        supabase = get_supabase()
        
        # Query the sales table and join with inventory
        res = supabase.table('sales').select('*, aviation_inventory(part_number, description)').execute()
        
        if not res.data:
            return render_template('usage_reports.html', report_data=[])

        # Pass the actual data list, NOT a jsonify() object
        return render_template('usage_reports.html', report_data=res.data)
    except Exception as e:
        print(f"Usage reports error: {e}")
        flash(f'Usage reports error: {str(e)}', 'danger')
        return render_template('usage_reports.html', report_data=[])

@app.route('/generate-barcode/<part_number>')
def generate_barcode(part_number):
    # Create a Code128 barcode
    EAN = barcode.get_barcode_class('code128')
    ean = EAN(part_number, writer=ImageWriter())
    
    buffer = BytesIO()
    ean.write(buffer)
    buffer.seek(0)
    
    # Returns the barcode as an image for the browser to display or print
    return send_file(buffer, mimetype='image/png')



if __name__ == '__main__':

    print("🚀 Aviation ERP Admin Portal - Render Deployment Ready")
    print("📊 Dashboard: http://localhost:5000/admin")
    print("📦 Stock Mgmt: http://localhost:5000/stock-management") 
    print("📜 View Order: http://localhost:5000/view-order/[order_id]")
    print("📈 Stock History: http://localhost:5000/stock-history")
    print("📦 Deploy: gunicorn app:app")
    app.run(debug=True, host='0.0.0.0', port=5000)


