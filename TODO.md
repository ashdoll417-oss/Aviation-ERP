# TODO - Staff Sales Site - Complete Implementation

## Task
Create the Staff Sales Site with HTML5 form including:
- Searchable dropdown for 149 Products
- Unit Type toggle (Lts, Kg, Yards, Inches, Meters)
- Kit Preview section (hidden unless is_kit is true)
- PO Number and Delivery Note Number fields
- Tailwind CSS for mobile responsiveness
- Stock Status badge with real-time updates

## Steps Completed

### 1. Create handleSaleInput.js
- [x] Main `handleSaleInput` function with logic for Paint Kits and Carpets
- [x] Paint Kit Logic: Fetches mixing_ratio from product data, calculates hardener_required and thinner_required
- [x] Carpet Logic: Converts yards to meters with 5% wastage (20 yards = 18.288m + 5% = 19.20m)
- [x] Stock Validation: Compares calculated total vs current_stock, turns text red and disables confirm button
- [x] Helper functions: yardsToMeters, inchesToMeter, calculateWithWastage, isCarpetCategory, isYardsUnit
- [x] UI Update Functions: updateKitFields, updateCarpetFields, updateStockWarning, disableConfirmButton, enableConfirmButton
- [x] Event Listener Setup: setupSaleInputListeners for automatic triggering on input changes
- [x] Initialization: initSaleInputHandler for easy setup
- [x] Example HTML markup documentation

### 2. Create staff_sales_form.html
- [x] HTML5 form with Tailwind CSS styling (mobile-responsive)
- [x] Searchable dropdown using Select2 for 149 products
- [x] Unit Type dropdown: Lts, Kg, Yards, Inches, Meters
- [x] Kit Preview section (hidden unless is_kit = true)
- [x] Purchase Order (PO) Number field
- [x] Delivery Note (DN) Number field
- [x] Stock Status badge with real-time updates
- [x] Carpet Preview section (shows meters with 5% wastage)
- [x] Stock warning messages (red/green)
- [x] Confirm Sale button (disabled when insufficient stock)
- [x] Form submission to /sales/confirm API

## Files Created
- `handleSaleInput.js` - JavaScript logic for calculations and validation
- `staff_sales_form.html` - Complete HTML5 form with Tailwind CSS

## Usage

### 1. Include the JavaScript
```html
<script src="handleSaleInput.js"></script>
```

### 2. Initialize the form
```javascript
// The form auto-initializes on page load
// Products are fetched from /api/products endpoint
```

### Key Features
- **Searchable Product Dropdown**: Uses Select2 for fuzzy search
- **Real-time Stock Status**: Updates badge when product is selected
- **Kit Preview**: Shows hardener/thinner required fields when is_kit=true
- **Carpet Calculation**: Auto-converts yards to meters + 5% wastage
- **Stock Validation**: Disables confirm button if insufficient stock
- **Mobile Responsive**: Works on all screen sizes with Tailwind CSS

---

# TODO - Extend Product Model with Location Field

## Task
Extend the Product model to include a location field for tracking product storage locations.

## Steps Completed

### 1. Update models.py
- [x] Add `location` field to `ProductBase` class (optional string, max_length=255)
- [x] Add `location` field to `ProductCreate` class
- [x] Add `location` field to `ProductUpdate` class
- [x] Add `location` field to `ProductSummary` class
- [x] Update JSON schema examples in Product class

### 2. Update schema.sql
- [x] Add `location` VARCHAR(255) column to products table
- [x] Add index for location field (idx_products_location)
- [x] Add comment for documentation

### 3. Update process_kit_sale.sql
- [x] Not needed - process_kit_sale.sql is a separate function file, no table definitions

## Implementation Notes
- Location is an optional field (default=None)
- Max length: 255 characters
- Field type: str (Optional)
- Use case: Track where products are stored (e.g., warehouse, shelf, bin)

