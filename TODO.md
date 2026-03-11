# TODO: Update min_threshold to be bulletproof

## Changes Required:

### 1. main.py Updates
- [ ] 1.1 Update `get_low_stock_items()` function - change default from 10 to 5
- [ ] 1.2 Update `/add-item` route - convert min_threshold to integer, default to 5
- [ ] 1.3 Update `/api/product/issue` endpoint - change default from 10 to 5
- [ ] 1.4 Update `/api/staff/issue` endpoint - change default from 10 to 5

### 2. admin_dashboard.py Updates
- [ ] 2.1 Update `get_inventory_data()` function - change default from 10 to 5
- [ ] 2.2 Update `/stock` endpoint - already uses 5 (verified)
- [ ] 2.3 Update `/add-item` route - change float to int conversion, default to 5
- [ ] 2.4 Update `/api/staff/issue` endpoint - change default from 10 to 5

## Completion Criteria:
- All min_threshold defaults are now 5
- Low stock filter uses explicit .get('min_threshold', 5)
- Add item routes convert min_threshold to integer

