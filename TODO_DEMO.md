# ERP Demo Updates TODO

## Approved Plan Steps:
- [x] Step 1: Update admin_dashboard.py /add-item: add unit_type handling, Inches->Yards carpet conversion (/36), save color_type for carpet
- [x] Step 2: Update admin_dashboard.py /api/stock/update: search .or_(part_number.eq, barcode_number.eq)
- [x] Step 3: Update templates/stock.html: add unit_type select by category JS, color_type input for carpet
- [ ] Step 4: Test APIs locally (uvicorn admin_dashboard:app:8000)
- [ ] Step 5: Git commit/push to Render
- [x] Step 6: Complete
