"""
FastAPI Admin Dashboard Application
Uses Jinja2 templates for rendering the admin interface
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from pydantic import BaseModel

from config import settings, get_supabase_client, get_supabase_service_client

# =============================================================================
# FASTAPI APP INITIALIZATION
# =============================================================================

app = FastAPI(
    title="Aviation ERP Admin Dashboard",
    description="Admin Dashboard for Aviation ERP System",
    version="1.0.0",
)

# =============================================================================
# CORS MIDDLEWARE
# =============================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# TEMPLATES CONFIGURATION
# =============================================================================

# Get the directory where this file is located
BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=BASE_DIR / "templates")

# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class StockUpdateRequest(BaseModel):
    """Request model for updating stock."""
    part_number: str
    new_quantity: float
    operation: str  # 'set', 'add', 'subtract'


class QuoteItemRequest(BaseModel):
    """Request model for quote item."""
    part_number: str
    description: str
    quantity: float
    unit_cost: float


class SaveQuoteRequest(BaseModel):
    """Request model for saving a quote."""
    quote_number: str
    customer_name: str
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None
    items: List[QuoteItemRequest]
    subtotal: float
    vat_rate: float = 0.16
    grand_total: float


class POItemRequest(BaseModel):
    """Request model for purchase order item."""
    part_number: str
    description: str
    quantity: float
    uom: str
    unit_price_usd: float


class SavePORequest(BaseModel):
    """Request model for saving a purchase order."""
    po_number: str
    supplier: str
    po_date: str
    items: List[POItemRequest]
    total_usd: float
    status: str = "PENDING"


class UpdatePOStatusRequest(BaseModel):
    """Request model for updating PO status."""
    po_id: str
    status: str  # 'APPROVED' or 'REJECTED'
    notes: Optional[str] = None


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_time_greeting() -> str:
    """
    Get time-based greeting.
    
    Returns:
        Greeting message based on current hour
    """
    now = datetime.now()
    current_hour = now.hour
    
    # 05:00-11:59 = Good Morning
    # 12:00-17:59 = Good Afternoon
    # Otherwise (18:00-04:59) = Good Evening
    if 5 <= current_hour < 12:
        return "Good Morning, AISL Aviation Team"
    elif 12 <= current_hour < 18:
        return "Good Afternoon, AISL Aviation Team"
    else:
        return "Good Evening, AISL Aviation Team"


def get_inventory_data() -> Dict[str, List[Dict[str, Any]]]:
    """
    Fetch inventory data from Supabase and group by category.
    
    Returns:
        Dictionary with 'paints' and 'carpets' lists
    """
    supabase = get_supabase_client()
    
    try:
        # Explicitly select columns to avoid error 42703 (undefined column)
        response = supabase.table("aviation_inventory").select(
            "id, part_number, description, current_stock, min_threshold, uom, category, preferred_supplier_id"
        ).execute()
        
        if not response.data:
            return {"paints": [], "carpets": [], "low_stock": []}
        
        paints = []
        carpets = []
        low_stock = []
        
        for item in response.data:
            description = item.get("description", "").upper()
            category = item.get("category", "").lower()
            current_stock = float(item.get("current_stock", 0)) if item.get("current_stock") else 0
            # Use default min_threshold=5 if missing
            min_threshold = float(item.get("min_threshold", 5)) if item.get("min_threshold") else 5
            uom = item.get("uom", "")
            
            # Determine stock unit
            stock_unit = uom
            if 'AERMAT' in description or 'CARPET' in description:
                stock_unit = "Linear Meters"
            
            # Check if it's a carpet/flooring item
            is_carpet = category == "carpet" or 'AERMAT' in description or 'CARPET' in description
            
            # Check if low stock (below min_threshold)
            is_low_stock = current_stock <= min_threshold
            
            item_data = {
                "part_number": item.get("part_number", ""),
                "description": item.get("description", ""),
                "current_stock": current_stock,
                "min_threshold": min_threshold,
                "uom": uom,
                "stock_unit": stock_unit,
                "stock_display": f"{current_stock} {stock_unit}" if current_stock > 0 else "Out of Stock",
                "is_available": current_stock > 0,
                "is_low_stock": is_low_stock,
                "preferred_supplier_id": item.get("preferred_supplier_id"),
                "preferred_supplier_name": None,
                # For carpets, add color/type info
                "color_type": get_carpet_color_type(item.get("description", ""))
            }
            
            if is_carpet:
                carpets.append(item_data)
                if is_low_stock:
                    low_stock.append(item_data)
            else:
                paints.append(item_data)
                if is_low_stock:
                    low_stock.append(item_data)
        
        return {
            "paints": paints,
            "carpets": carpets,
            "low_stock": low_stock
        }
        
    except Exception as e:
        print(f"Error fetching inventory: {e}")
        # Return empty dict instead of crashing
        return {"paints": [], "carpets": [], "low_stock": []}


def get_carpet_color_type(description: str) -> str:
    """
    Extract color/type from carpet description.
    
    Args:
        description: Product description
    
    Returns:
        Color/type string (e.g., 'BLUE', 'GREY', 'WOVEN', 'ECONYL RIPS')
    """
    if not description:
        return ""
    
    desc_upper = description.upper()
    
    # Check for AERMAT colors
    if 'AERMAT' in desc_upper:
        if 'BLUE' in desc_upper or '8451' in desc_upper:
            return 'BLUE'
        elif 'GREY' in desc_upper or '992' in desc_upper:
            return 'GREY'
    
    # Check for CARPET types
    if 'CARPET' in desc_upper:
        if 'WOVEN' in desc_upper:
            return 'WOVEN'
        elif 'ECONYL' in desc_upper or 'RIPS' in desc_upper:
            return 'ECONYL RIPS'
    
    return ""


# =============================================================================
# DASHBOARD ROUTES
# =============================================================================

@app.get("/")
async def dashboard(request: Request):
    """
    Main Dashboard page.
    
    Displays welcome message and quick stats.
    Fail-Safe: Wrapped in try/except to prevent page crashes.
    Uses explicit table name 'aviation_inventory' (lowercase).
    Uses item.get('min_threshold', 5) for low-stock calculation.
    """
    greeting = get_time_greeting()
    supabase = get_supabase_client()
    
    # Total Safety: Wrap stock fetching in try/except to prevent page crashes
    # Explicit columns EXCLUDING min_threshold to avoid error 42703
    try:
        # Fetch items with EXPLICIT columns - EXCLUDING min_threshold
        response = supabase.table("aviation_inventory").select(
            "id, part_number, description, current_stock"
        ).execute()
        
        # Python Filtering: Manually add min_threshold with default 5
        all_items = response.data if response.data else []
        for item in all_items:
            item['min_threshold'] = item.get('min_threshold', 5)
        
        # Filter in Python using the manually added min_threshold
        low_stock_items = [
            item for item in all_items 
            if float(item.get('current_stock', 0)) <= float(item.get('min_threshold', 5))
        ]
        
        return templates.TemplateResponse(
            "dashboard.html",
            {
                "request": request,
                "greeting": greeting,
                "low_stock_items": low_stock_items,
                "low_stock_count": len(low_stock_items)
            }
        )
    except Exception as e:
        print(f"Error fetching dashboard data: {e}")
        return templates.TemplateResponse(
            "dashboard.html",
            {
                "request": request,
                "greeting": greeting,
                "low_stock_items": [],
                "low_stock_count": 0
            }
        )


@app.get("/sales")
async def sales(request: Request):
    """Sales page."""
    greeting = get_time_greeting()
    return templates.TemplateResponse(
        "page.html",
        {
            "request": request,
            "greeting": greeting,
            "page_title": "Sales",
            "page_icon": "cart3"
        }
    )


@app.get("/purchase-orders")
async def purchase_orders(request: Request):
    """Purchase Orders page for Aero Instrument Service Ltd."""
    greeting = get_time_greeting()
    
    # Generate PO number
    now = datetime.now()
    po_number = f"PO-{now.strftime('%y')}-{now.strftime('%m')}{now.strftime('%d')}-{now.strftime('%H%M%S')}"
    
    # Get current date
    current_date = now.strftime('%Y-%m-%d')
    
    return templates.TemplateResponse(
        "purchase_order.html",
        {
            "request": request,
            "greeting": greeting,
            "page_title": "Purchase Orders",
            "page_icon": "basket",
            "po_number": po_number,
            "current_date": current_date
        }
    )


@app.post("/api/purchase-order/save")
async def save_purchase_order(request: SavePORequest):
    """
    Save purchase order to purchase_orders table in Supabase.
    
    Args:
        request: SavePORequest with PO details and items
    
    Returns:
        Success message with PO ID
    """
    supabase = get_supabase_service_client()
    
    try:
        # Create PO record
        po_data = {
            "po_number": request.po_number,
            "supplier": request.supplier,
            "po_date": request.po_date,
            "total_usd": request.total_usd,
            "status": "PENDING",
            "created_at": datetime.now().isoformat()
        }
        
        po_response = supabase.table("purchase_orders").insert(po_data).execute()
        
        if not po_response.data:
            raise Exception("Failed to create purchase order")
        
        po_id = po_response.data[0].get("id")
        
        # Insert PO items
        for item in request.items:
            item_data = {
                "po_id": po_id,
                "part_number": item.part_number,
                "description": item.description,
                "quantity": item.quantity,
                "uom": item.uom,
                "unit_price_usd": item.unit_price_usd,
                "total_usd": item.quantity * item.unit_price_usd
            }
            supabase.table("purchase_order_items").insert(item_data).execute()
        
        return {
            "success": True,
            "message": f"PO {request.po_number} has been submitted for approval. You will be notified once the Admin signs off.",
            "po_id": po_id,
            "po_number": request.po_number
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving purchase order: {str(e)}")


@app.get("/completed-orders")
async def completed_orders(request: Request):
    """Completed Orders page."""
    greeting = get_time_greeting()
    return templates.TemplateResponse(
        "page.html",
        {
            "request": request,
            "greeting": greeting,
            "page_title": "Completed Orders",
            "page_icon": "check2-circle"
        }
    )


@app.get("/reports")
async def reports(request: Request):
    """Reports page."""
    greeting = get_time_greeting()
    return templates.TemplateResponse(
        "reports.html",
        {
            "request": request,
            "greeting": greeting,
            "page_title": "Reports",
            "page_icon": "graph-up"
        }
    )


@app.get("/usage-reports")
async def usage_reports(request: Request):
    """Monthly Usage Reports page - shows stock issues from last 30 days."""
    greeting = get_time_greeting()
    supabase = get_supabase_client()
    
    try:
        # Calculate date 30 days ago
        from datetime import timedelta
        thirty_days_ago = (datetime.now() - timedelta(days=30)).isoformat()
        
        # Query stock_logs for ISSUEs in the last 30 days
        logs_response = supabase.table("stock_logs").select(
            "part_number, quantity, created_at"
        ).gte("created_at", thirty_days_ago).eq("transaction_type", "ISSUE").execute()
        
        # Group by part_number and sum quantities
        usage_dict = {}
        for log in logs_response.data:
            part_number = log.get("part_number")
            quantity = float(log.get("quantity", 0))
            if part_number in usage_dict:
                usage_dict[part_number] += quantity
            else:
                usage_dict[part_number] = quantity
        
        # Get inventory details for each part number
        inventory_response = supabase.table("aviation_inventory").select(
            "part_number, description, current_stock, unit_price_usd"
        ).execute()
        
        inventory_dict = {item.get("part_number"): item for item in inventory_response.data}
        
        # Build usage data with inventory details
        usage_data = []
        total_issued = 0
        total_cost = 0.0
        
        for part_number, total_qty in usage_dict.items():
            inventory_item = inventory_dict.get(part_number, {})
            description = inventory_item.get("description", "Unknown")
            current_stock = float(inventory_item.get("current_stock", 0))
            unit_price = float(inventory_item.get("unit_price_usd", 0) or 0)
            cost_analysis = total_qty * unit_price
            
            usage_data.append({
                "part_number": part_number,
                "description": description,
                "total_issued": total_qty,
                "current_stock": current_stock,
                "unit_price_usd": unit_price,
                "cost_analysis": round(cost_analysis, 2)
            })
            
            total_issued += total_qty
            total_cost += cost_analysis
        
        # Sort by total_issued descending
        usage_data.sort(key=lambda x: x["total_issued"], reverse=True)
        
        # Get top 5 for chart
        top_5_items = usage_data[:5]
        
        # Get unique items count
        unique_items = len(usage_data)
        
        return templates.TemplateResponse(
            "usage_reports.html",
            {
                "request": request,
                "greeting": greeting,
                "page_title": "Usage Reports",
                "page_icon": "bar-chart",
                "usage_data": usage_data,
                "top_5_items": top_5_items,
                "total_issued": round(total_issued, 2),
                "unique_items": unique_items,
                "total_cost": round(total_cost, 2),
                "usage_data_json": usage_data
            }
        )
        
    except Exception as e:
        print(f"Error fetching usage reports: {e}")
        return templates.TemplateResponse(
            "usage_reports.html",
            {
                "request": request,
                "greeting": greeting,
                "page_title": "Usage Reports",
                "page_icon": "bar-chart",
                "usage_data": [],
                "top_5_items": [],
                "total_issued": 0,
                "unique_items": 0,
                "total_cost": 0,
                "usage_data_json": []
            }
        )


# =============================================================================
# ADMIN APPROVALS ROUTES
# =============================================================================

@app.get("/admin/approvals")
async def admin_approvals(request: Request):
    """Admin Approvals page - shows pending POs for approval."""
    greeting = get_time_greeting()
    return templates.TemplateResponse(
        "admin_approvals.html",
        {
            "request": request,
            "greeting": greeting,
            "page_title": "Admin Approvals",
            "page_icon": "bi-check2-square"
        }
    )


@app.get("/api/admin/pending-pos")
async def get_pending_pos():
    """Get all pending purchase orders from Supabase."""
    supabase = get_supabase_client()
    
    try:
        # Fetch pending POs
        pos_response = supabase.table("purchase_orders").select(
            "id, po_number, supplier, po_date, total_usd, status, created_at"
        ).eq("status", "PENDING").order("created_at", desc=True).execute()
        
        return {
            "success": True,
            "purchase_orders": pos_response.data
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "purchase_orders": []
        }


@app.get("/api/admin/po/{po_id}")
async def get_po_details(po_id: str):
    """Get full PO details including items."""
    supabase = get_supabase_client()
    
    try:
        # Get PO header
        po_response = supabase.table("purchase_orders").select("*").eq("id", po_id).execute()
        
        if not po_response.data:
            return {"success": False, "error": "PO not found"}
        
        # Get PO items
        items_response = supabase.table("purchase_order_items").select("*").eq("po_id", po_id).execute()
        
        return {
            "success": True,
            "po": po_response.data[0],
            "items": items_response.data
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@app.post("/api/admin/po/update-status")
async def update_po_status(request: UpdatePOStatusRequest):
    """Update PO status (APPROVED or REJECTED)."""
    supabase = get_supabase_service_client()
    
    try:
        # Update PO status
        update_response = supabase.table("purchase_orders").update({
            "status": request.status,
            "notes": request.notes,
            "updated_at": datetime.now().isoformat()
        }).eq("id", request.po_id).execute()
        
        if not update_response.data:
            raise Exception("Failed to update PO status")
        
        # Get updated PO
        po_response = supabase.table("purchase_orders").select("*").eq("id", request.po_id).execute()
        po = po_response.data[0] if po_response.data else None
        
        message = ""
        if request.status == "APPROVED":
            message = f"PO {po['po_number']} has been approved. The PO has been sent to the supplier and a PDF will be generated for email."
        else:
            message = f"PO {po['po_number']} has been rejected."
        
        return {
            "success": True,
            "message": message,
            "po": po
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating PO status: {str(e)}")


@app.get("/stock")
async def stock(request: Request):
    """Stock page - displays inventory from Supabase."""
    greeting = get_time_greeting()
    supabase = get_supabase_client()
    
    try:
        # Fetch inventory including min_threshold
        response = supabase.table("aviation_inventory").select(
            "*, suppliers(id, supplier_name)"
        ).execute()
        
        items = []
        if response.data:
            for item in response.data:
                description = item.get("description", "").upper()
                category = item.get("category", "").lower()
                current_stock = float(item.get("current_stock", 0)) if item.get("current_stock") else 0
                min_threshold = float(item.get("min_threshold", 5)) if item.get("min_threshold") else 5
                uom = item.get("uom", "")
                
                # Get supplier info
                suppliers = item.get("suppliers", [])
                preferred_supplier_id = item.get("preferred_supplier_id")
                preferred_supplier_name = None
                if isinstance(suppliers, list) and len(suppliers) > 0:
                    preferred_supplier_name = suppliers[0].get("supplier_name")
                elif isinstance(suppliers, dict):
                    preferred_supplier_name = suppliers.get("supplier_name")
                
                # Determine stock unit
                stock_unit = uom
                if 'AERMAT' in description or 'CARPET' in description:
                    stock_unit = "Linear Meters"
                
                # Check if it's a carpet/flooring item
                is_carpet = category == "carpet" or 'AERMAT' in description or 'CARPET' in description
                
                # Check if low stock (below min_threshold)
                is_low_stock = current_stock <= min_threshold
                
                # Determine color/type for display
                color_type = ""
                if 'AERMAT' in description:
                    if 'BLUE' in description or '8451' in description:
                        color_type = 'BLUE'
                    elif 'GREY' in description or '992' in description:
                        color_type = 'GREY'
                if 'CARPET' in description:
                    if 'WOVEN' in description:
                        color_type = 'WOVEN'
                    elif 'ECONYL' in description or 'RIPS' in description:
                        color_type = 'ECONYL RIPS'
                
                item_data = {
                    "part_number": item.get("part_number", ""),
                    "description": item.get("description", ""),
                    "current_stock": current_stock,
                    "min_threshold": min_threshold,
                    "uom": uom,
                    "stock_unit": stock_unit,
                    "stock_display": f"{current_stock} {stock_unit}" if current_stock > 0 else "Out of Stock",
                    "is_available": current_stock > 0,
                    "is_low_stock": is_low_stock,
                    "preferred_supplier_id": preferred_supplier_id,
                    "preferred_supplier_name": preferred_supplier_name,
                    "color_type": color_type,
                    "category": category
                }
                items.append(item_data)
        
        # Get suppliers list for preferred supplier dropdown
        try:
            suppliers_response = supabase.table("suppliers").select("id, supplier_name").execute()
            suppliers_list = suppliers_response.data if suppliers_response.data else []
        except Exception as e:
            print(f"Error fetching suppliers: {e}")
            suppliers_list = []
        
        return templates.TemplateResponse(
            "stock.html",
            {
                "request": request,
                "greeting": greeting,
                "page_title": "Stock Management",
                "page_icon": "box-seam",
                "items": items,
                "suppliers_list": suppliers_list,
                "suppliers": suppliers_list  # Keep for backward compatibility
            }
        )
        
    except Exception as e:
        print(f"Error fetching stock: {e}")
        return templates.TemplateResponse(
            "stock.html",
            {
                "request": request,
                "greeting": greeting,
                "page_title": "Stock Management",
                "page_icon": "box-seam",
                "items": [],
                "suppliers_list": [],
                "suppliers": []
            }
        )


@app.post("/add-item")
async def add_item(request: Request):
    """
    Add new item to aviation_inventory table via form submission.
    Redirects back to /stock after insertion.
    """
    from fastapi.responses import RedirectResponse
    
    # Get form data
    form_data = await request.form()
    part_number = form_data.get("part_number", "").strip()
    description = form_data.get("description", "").strip()
    category = form_data.get("category", "").strip()
    current_stock = form_data.get("current_stock", "0").strip()
    batch_no = form_data.get("batch_no", "").strip()
    expiry_date = form_data.get("expiry_date", "").strip()
    barcode_id = form_data.get("barcode_id", "").strip()
    min_threshold = form_data.get("min_threshold", "").strip()
    uom = form_data.get("uom", "KG").strip()
    preferred_supplier_id = form_data.get("preferred_supplier_id", "").strip()
    
    if not part_number or not description:
        return RedirectResponse(url="/stock", status_code=303)
    
    try:
        supabase = get_supabase_client()
        
        # Parse values, default to 0 for current_stock, and 5 for min_threshold if blank
        try:
            current_stock_value = float(current_stock) if current_stock else 0
        except ValueError:
            current_stock_value = 0
            
        # Default to 5 if min_threshold is blank or invalid, convert to integer
        if not min_threshold:
            min_threshold_value = 5
        else:
            try:
                min_threshold_value = int(min_threshold)
            except ValueError:
                min_threshold_value = 5
        
        # Insert into aviation_inventory table with correct column names
        new_item = {
            "part_number": part_number,
            "description": description,
            "category": category,
            "current_stock": current_stock_value,
            "opening_stock": current_stock_value,
            "uom": uom,
            "min_threshold": min_threshold_value
        }
        
        # Add preferred supplier if selected
        if preferred_supplier_id:
            new_item["preferred_supplier_id"] = preferred_supplier_id
        
        # Add batch number if provided
        if batch_no:
            new_item["batch_no"] = batch_no
        
        # Add expiry date if provided (validate format)
        if expiry_date:
            try:
                from datetime import datetime
                exp_date = datetime.strptime(expiry_date, "%Y-%m-%d")
                new_item["expiry_date"] = exp_date.strftime("%Y-%m-%d")
            except ValueError:
                new_item["expiry_date"] = expiry_date
        
        # Add barcode_id if provided
        if barcode_id:
            new_item["barcode_id"] = barcode_id
        
        supabase.table("aviation_inventory").insert(new_item).execute()
        
    except Exception as e:
        error_msg = str(e)
        print(f"Error adding item: {error_msg}")
        # Return the error message to help debug - URL encode the error
        from urllib.parse import quote
        encoded_error = quote(error_msg)
        return RedirectResponse(url=f"/stock?error={encoded_error}", status_code=303)
    
    return RedirectResponse(url="/stock", status_code=303)


@app.post("/add-supplier")
async def add_supplier(request: Request):
    """
    Add new supplier to suppliers table via form submission.
    Redirects back to /suppliers after insertion.
    """
    from fastapi.responses import RedirectResponse
    
    # Get form data
    form_data = await request.form()
    supplier_name = form_data.get("supplier_name", "").strip()
    contact_person = form_data.get("contact_person", "").strip()
    email = form_data.get("email", "").strip()
    phone = form_data.get("phone", "").strip()
    
    if not supplier_name:
        return RedirectResponse(url="/suppliers", status_code=303)
    
    try:
        supabase = get_supabase_client()
        
        # Insert into suppliers table
        new_supplier = {
            "supplier_name": supplier_name
        }
        
        if contact_person:
            new_supplier["contact_person"] = contact_person
        if email:
            new_supplier["email"] = email
        if phone:
            new_supplier["phone"] = phone
        
        supabase.table("suppliers").insert(new_supplier).execute()
        
    except Exception as e:
        print(f"Error adding supplier: {e}")
    
    return RedirectResponse(url="/suppliers", status_code=303)


@app.get("/api/suppliers")
async def get_suppliers():
    """Get all suppliers for dropdown selection."""
    supabase = get_supabase_client()
    
    try:
        response = supabase.table("suppliers").select("id, supplier_name").order("supplier_name").execute()
        
        return {
            "success": True,
            "suppliers": response.data
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "suppliers": []
        }


@app.post("/api/inventory/update-supplier")
async def update_preferred_supplier(part_number: str, supplier_id: str):
    """Update preferred supplier for an inventory item."""
    supabase = get_supabase_service_client()
    
    try:
        update_response = supabase.table("aviation_inventory").update({
            "preferred_supplier_id": supplier_id
        }).eq("part_number", part_number).execute()
        
        if not update_response.data:
            raise Exception("Failed to update preferred supplier")
        
        return {
            "success": True,
            "message": "Preferred supplier updated successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating supplier: {str(e)}")


@app.get("/quote")
async def quote(request: Request):
    """Quote Generator page for Aero Instrument Service Ltd."""
    greeting = get_time_greeting()
    
    # Generate quote number
    now = datetime.now()
    quote_number = f"QTE-{now.strftime('%Y%m%d')}-{now.strftime('%H%M%S')}"
    
    # Get current date
    current_date = now.strftime('%d/%m/%Y')
    
    return templates.TemplateResponse(
        "quote.html",
        {
            "request": request,
            "greeting": greeting,
            "page_title": "Quote Generator",
            "page_icon": "file-earmark-text",
            "quote_number": quote_number,
            "current_date": current_date
        }
    )


@app.get("/api/inventory/search")
async def search_inventory(q: str = ""):
    """
    Search inventory items from Supabase aviation_inventory table.
    
    Args:
        q: Search query string
    
    Returns:
        List of matching inventory items
    """
    supabase = get_supabase_client()
    
    try:
        # Search in part_number and description
        response = supabase.table("aviation_inventory").select(
            "part_number, description, current_stock, uom"
        ).or_(
            f"part_number.ilike.%{q}%,description.ilike.%{q}%"
        ).limit(20).execute()
        
        return {
            "success": True,
            "items": response.data
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "items": []
        }


@app.get("/api/product/search")
async def search_product(q: str = ""):
    """
    Search for a product by barcode number or part number.
    Used by the staff issuing page.
    """
    supabase = get_supabase_client()
    
    try:
        # Search by barcode_number OR part_number
        response = supabase.table("aviation_inventory").select("*").or_(
            f"barcode_number.eq.{q},part_number.eq.{q}"
        ).execute()
        
        if response.data and len(response.data) > 0:
            product = response.data[0]
            return {
                "success": True,
                "product": {
                    "part_number": product.get("part_number"),
                    "description": product.get("description"),
                    "category": product.get("category"),
                    "current_stock": float(product.get("current_stock", 0)) if product.get("current_stock") else 0,
                    "uom": product.get("uom", "units"),
                    "barcode_number": product.get("barcode_number")
                }
            }
        else:
            return {
                "success": False,
                "message": "Product not found"
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@app.post("/api/quote/save")
async def save_quote(request: SaveQuoteRequest):
    """
    Save quote to sales_quotes table in Supabase.
    
    Args:
        request: SaveQuoteRequest with quote details and items
    
    Returns:
        Success message with quote ID
    """
    supabase = get_supabase_service_client()
    
    try:
        # Create quote record
        quote_data = {
            "quote_number": request.quote_number,
            "customer_name": request.customer_name,
            "customer_email": request.customer_email,
            "customer_phone": request.customer_phone,
            "subtotal": request.subtotal,
            "vat_rate": request.vat_rate,
            "grand_total": request.grand_total,
            "status": "pending",
            "created_at": datetime.now().isoformat()
        }
        
        quote_response = supabase.table("sales_quotes").insert(quote_data).execute()
        
        if not quote_response.data:
            raise Exception("Failed to create quote")
        
        quote_id = quote_response.data[0].get("id")
        
        # Insert quote items
        for item in request.items:
            item_data = {
                "quote_id": quote_id,
                "part_number": item.part_number,
                "description": item.description,
                "quantity": item.quantity,
                "unit_cost": item.unit_cost,
                "total": item.quantity * item.unit_cost
            }
            supabase.table("sales_quote_items").insert(item_data).execute()
        
        return {
            "success": True,
            "message": "Quote saved successfully",
            "quote_id": quote_id,
            "quote_number": request.quote_number
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving quote: {str(e)}")


@app.get("/logout")
async def logout(request: Request):
    """
    Logout - clears session cookies and redirects to home page.
    
    Clears authentication tokens (access_token, refresh_token) from cookies
    and redirects user to the home greeting page.
    """
    from fastapi.responses import RedirectResponse
    
    # Create response with redirect to home
    response = RedirectResponse(url="/", status_code=302)
    
    # Clear authentication cookies
    cookie_options = {
        "path": "/",
        "httponly": True,
        "secure": False,  # Set to True in production with HTTPS
        "samesite": "lax"
    }
    
    # Clear common Supabase auth cookies
    response.delete_cookie("access_token", **cookie_options)
    response.delete_cookie("refresh_token", **cookie_options)
    response.delete_cookie("id_token", **cookie_options)
    response.delete_cookie("session", **cookie_options)
    response.delete_cookie("sb-access-token", **cookie_options)
    response.delete_cookie("sb-refresh-token", **cookie_options)
    
    return response


# =============================================================================
# SUPPLIERS AND STAFF ISSUE ROUTES
# =============================================================================

@app.get("/suppliers")
async def suppliers(request: Request):
    """
    Suppliers Management page - renders suppliers.html with supplier data.
    """
    greeting = get_time_greeting()
    supabase = get_supabase_client()
    
    try:
        # Fetch all suppliers from the suppliers table
        response = supabase.table("suppliers").select("*").order("supplier_name").execute()
        
        suppliers = []
        if response.data:
            suppliers = response.data
        
        return templates.TemplateResponse(
            "suppliers.html",
            {
                "request": request,
                "greeting": greeting,
                "page_title": "Suppliers",
                "page_icon": "truck",
                "suppliers": suppliers
            }
        )
    except Exception as e:
        print(f"Error fetching suppliers: {e}")
        return templates.TemplateResponse(
            "suppliers.html",
            {
                "request": request,
                "greeting": greeting,
                "page_title": "Suppliers",
                "page_icon": "truck",
                "suppliers": []
            }
        )


@app.get("/staff/issue")
async def staff_issue_page(request: Request):
    """
    Staff Issue Stock page - dedicated simplified interface for staff to issue stock.
    Located at /staff/issue route with no sidebar, just Logout and Issue buttons.
    """
    return templates.TemplateResponse("staff_issue.html", {
        "request": request,
        "greeting": get_time_greeting()
    })


# =============================================================================
# API ENDPOINTS (for AJAX calls)
# =============================================================================

@app.get("/api/greeting")
async def api_greeting():
    """API endpoint to get current greeting."""
    return {"greeting": get_time_greeting()}


@app.get("/api/inventory")
async def api_inventory():
    """API endpoint to get inventory data."""
    inventory = get_inventory_data()
    return {
        "success": True,
        "paints": inventory["paints"],
        "carpets": inventory["carpets"]
    }


@app.post("/api/stock/update")
async def update_stock(request: StockUpdateRequest):
    """
    API endpoint to update stock quantity.
    
    Args:
        request: StockUpdateRequest with part_number, new_quantity, and operation
    
    Returns:
        Success message with updated stock
    """
    supabase = get_supabase_service_client()
    
    try:
        # Get current stock
        response = supabase.table("aviation_inventory").select("current_stock").eq("part_number", request.part_number).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail=f"Item not found: {request.part_number}")
        
        current_stock = float(response.data[0].get("current_stock", 0))
        
        # Calculate new stock based on operation
        if request.operation == "set":
            new_stock = request.new_quantity
        elif request.operation == "add":
            new_stock = current_stock + request.new_quantity
        elif request.operation == "subtract":
            new_stock = max(0, current_stock - request.new_quantity)
        else:
            raise HTTPException(status_code=400, detail="Invalid operation. Use 'set', 'add', or 'subtract'")
        
        # Update stock in database
        update_response = supabase.table("aviation_inventory").update({
            "current_stock": new_stock
        }).eq("part_number", request.part_number).execute()
        
        if not update_response.data:
            raise HTTPException(status_code=500, detail="Failed to update stock")
        
        return {
            "success": True,
            "message": f"Stock updated successfully for {request.part_number}",
            "old_stock": current_stock,
            "new_stock": new_stock
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating stock: {str(e)}")


@app.post("/api/staff/issue")
async def staff_issue_product(request: Request):
    """
    Staff Issue API - Process stock issue with staff name logging.
    Used by the dedicated Staff Issuing Page at /staff/issue.
    
    Request body:
    {
        "staff_name": "John Doe",
        "part_number": "123-456",
        "quantity": 1
    }
    
    Returns:
    {
        "success": true/false,
        "message": "...",
        "new_stock": 5,
        "low_stock": true/false
    }
    """
    from fastapi.responses import JSONResponse
    
    try:
        body = await request.json()
        staff_name = body.get("staff_name", "").strip()
        part_number = body.get("part_number", "").strip()
        quantity = float(body.get("quantity", 0))
        
        # Validation
        if not staff_name:
            return JSONResponse(
                status_code=400,
                content={"success": False, "detail": "Staff Name is required"}
            )
        
        if not part_number:
            return JSONResponse(
                status_code=400,
                content={"success": False, "detail": "Part number is required"}
            )
        
        if quantity <= 0:
            return JSONResponse(
                status_code=400,
                content={"success": False, "detail": "Quantity must be greater than 0"}
            )
        
        supabase = get_supabase_client()
        
        # Get current stock and min_threshold
        response = supabase.table("aviation_inventory").select("current_stock, min_threshold, description").eq("part_number", part_number).execute()
        
        if not response.data or len(response.data) == 0:
            return JSONResponse(
                status_code=404,
                content={"success": False, "detail": "Product not found"}
            )
        
        product = response.data[0]
        current_stock = float(product.get("current_stock", 0)) if product.get("current_stock") else 0
        min_threshold = float(product.get("min_threshold", 5)) if product.get("min_threshold") else 5
        description = product.get("description", "")
        
        # Check if enough stock
        if quantity > current_stock:
            return JSONResponse(
                status_code=400,
                content={"success": False, "detail": f"Insufficient stock. Available: {current_stock}"}
            )
        
        new_stock = current_stock - quantity
        
        # Ensure stock doesn't go negative
        if new_stock < 0:
            new_stock = 0
        
        # Update the stock in aviation_inventory
        supabase.table("aviation_inventory").update({
            "current_stock": new_stock
        }).eq("part_number", part_number).execute()
        
        # Record transaction in stock_logs with Staff Name
        try:
            supabase.table("stock_logs").insert({
                "part_number": part_number,
                "transaction_type": "ISSUE",
                "quantity": quantity,
                "previous_stock": current_stock,
                "new_stock": new_stock,
                "notes": f"Issued by: {staff_name}"
            }).execute()
        except Exception as log_error:
            print(f"Error logging stock transaction: {log_error}")
        
        # Check if stock is now low (trigger Low Stock flag for Admin)
        is_low_stock = new_stock <= min_threshold
        
        return {
            "success": True,
            "message": f"Successfully issued {quantity} units of {part_number}",
            "part_number": part_number,
            "description": description,
            "new_stock": new_stock,
            "previous_stock": current_stock,
            "issued_quantity": quantity,
            "staff_name": staff_name,
            "low_stock": is_low_stock
        }
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "detail": str(e)}
        )


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    
    print("=" * 60)
    print("Aviation ERP Admin Dashboard Starting...")
    print("=" * 60)
    print(f"\nTemplates Directory: {BASE_DIR / 'templates'}")
    print(f"\nDashboard URL: http://localhost:8000/")
    print(f"Stock Management URL: http://localhost:8000/stock")
    print("=" * 60)
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
