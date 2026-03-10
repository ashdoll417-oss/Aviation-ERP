# Aviation ERP Route Update Task

## Steps to Complete:

- [x] 1. Update main.py with new routes (/stock, /sales, /purchase-orders, /completed-orders, /reports, /quote, /add-item)
- [x] 2. Create sales.html template
- [x] 3. Create completed_orders.html template
- [x] 4. Create reports.html template
- [x] 5. Add Manual Entry Form to stock.html template

## Details:

### Routes added in main.py:
1. GET /stock - Render stock.html with Manual Entry Form + inventory data
2. GET /sales - Render sales.html
3. GET /purchase-orders - Render purchase_order.html
4. GET /completed-orders - Render completed_orders.html
5. GET /reports - Render reports.html
6. GET /quote - Render quote.html
7. POST /add-item - Insert form data into Supabase aviation_inventory table

### Templates created:
1. templates/sales.html
2. templates/completed_orders.html
3. templates/reports.html

### Templates updated:
1. templates/stock.html - Added Manual Entry Form at the top with Part Number, Description, and Category fields

