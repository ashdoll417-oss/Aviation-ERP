import os
from flask import Flask, render_template, request, jsonify
from database import get_supabase_service_client
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev-secret')

def get_supabase():
    return get_supabase_service_client()

# 1. FIX THE 404 UPDATE ROUTE
@app.route('/api/stock/update', methods=['POST', 'OPTIONS'], strict_slashes=False)
def update_stock():
    if request.method == 'OPTIONS': return '', 200
    try:
        data = request.get_json() or request.form
        p_num = data.get('part_number')
        new_qty = data.get('new_quantity')
        
        # Using 'current_stock' and 'part_number' from your screenshot
        res = get_supabase().table('aviation_inventory').update({'current_stock': new_qty}).eq('part_number', p_num).execute()
        return jsonify({"success": True}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# 2. FIX THE 500 INVENTORY ROUTE
@app.route('/inventory')
def get_inventory():
    try:
        res = get_supabase().table('aviation_inventory').select('*').execute()
        return render_template('stock_management.html', inventory=res.data or [])
    except Exception as e:
        return f"Error: {str(e)}", 500

# 3. FIX THE SALES/QUOTES ROUTE (Matching your screenshot 'sales_quotes')
@app.route('/sales')
def sales_view():
    try:
        res = get_supabase().table('sales_quotes').select('*, aviation_inventory(part_number)').execute()
        return render_template('sales.html', sales=res.data or [])
    except Exception as e:
        return f"Error: {str(e)}", 500

@app.route('/')
def index():
    return "<h1>Aviation ERP Live</h1><a href='/inventory'>Go to Inventory</a>"

if __name__ == '__main__':
    app.run(debug=True)

