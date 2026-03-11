"""
FastAPI Main Application for Aviation ERP
Connects to Supabase aviation_inventory table

Home Route: Returns time-based greeting
Inventory Route: Fetches items from aviation_inventory table with special handling
"""

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
from typing import Optional, List, Any
import pytz

from config import settings, get_supabase_client

# =============================================================================
# FASTAPI APP INITIALIZATION
# =============================================================================

app = FastAPI(
    title="Aviation ERP API",
    description="Backend API for Aviation ERP - Inventory Management",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# =============================================================================
# CORS MIDDLEWARE CONFIGURATION
# =============================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure as needed for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# TEMPLATES AND STATIC FILES
# =============================================================================

# Initialize Jinja2 templates
templates = Jinja2Templates(directory="templates")

# Mount static files (optional - CSS is loaded via CDN in templates)
# Create a static directory if needed
import os
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class InventoryItem(BaseModel):
    """Individual inventory item from aviation_inventory table."""
    part_number: str
    description: Optional[str] = None
    opening_stock: Optional[float] = None
    uom: Optional[str] = None
    cont: Optional[float] = None
    sold_stock: Optional[float] = None
    in_house: Optional[float] = None
    current_stock: float
    batch_no: Optional[str] = None
    dom: Optional[str] = None
    expiry_date: Optional[str] = None
    category: Optional[str] = None
    # Custom fields added by API
    stock_display: Optional[str] = Field(default=None, description="Stock with unit")
    is_available: bool = Field(default=False, description="Whether item is in stock")
    stock_unit: Optional[str] = Field(default=None, description="Stock unit (KG/L/Linear Meters)")
    notes: Optional[str] = Field(default=None, description="Additional notes for paint kits")
    display_name: Optional[str] = Field(default=None, description="Formatted display name for Carpet items: [COLOR/TYPE] - [DESCRIPTION]")
    is_expiring_soon: bool = Field(default=False, description="Whether item is within 30 days of expiring")


class InventoryResponse(BaseModel):
    """Response model for inventory endpoint."""
    success: bool
    message: str
    items: List[InventoryItem]
    total_count: int


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_greeting() -> str:
    """
    Get time-based greeting in Nairobi timezone.
    
    Returns:
        String with appropriate greeting based on time of day
    """
    nairobi_tz = pytz.timezone('Africa/Nairobi')
    current_hour = datetime.now(nairobi_tz).hour
    
    # 05:00-11:59 = Good Morning
    # 12:00-17:59 = Good Afternoon
    # Otherwise (18:00-04:59) = Good Evening
    if 5 <= current_hour < 12:
        return "Good Morning, AISL Aviation Team"
    elif 12 <= current_hour < 18:
        return "Good Afternoon"
    else:
        return "Good Evening"


def is_paint_kit(description: str, uom: str) -> bool:
    """
    Check if the product is a paint kit.
    
    Args:
        description: Product description
        uom: Unit of measurement
    
    Returns:
        True if product is a paint kit, False otherwise
    """
    if not description or not uom:
        return False
    
    description_upper = description.upper()
    uom_upper = uom.upper()
    
    # Check for paint kit indicators in description
    paint_kit_indicators = ['KIT', 'PAINT KIT', 'TOPCOAT', 'PRIMER', 'HARDENER', 'THINNER']
    
    # Must be KG and have paint-related keywords
    is_kg = uom_upper == 'KG'
    has_paint_keyword = any(indicator in description_upper for indicator in paint_kit_indicators)
    
    return is_kg and has_paint_keyword


def get_stock_unit(description: str, current_stock: float, uom: str) -> str:
    """
    Determine the stock unit for display.
    
    For AERMAT and CARPET items, use 'Linear Meters'.
    Otherwise, use the provided uom.
    
    Args:
        description: Product description
        current_stock: Current stock quantity
        uom: Unit of measurement
    
    Returns:
        Stock unit string
    """
    if not description:
        return uom or ""
    
    description_upper = description.upper()
    
    # Check for AERMAT or CARPET in description
    if 'AERMAT' in description_upper or 'CARPET' in description_upper:
        return "Linear Meters"
    
    return uom or ""


def get_carpet_display_name(description: str, category: str) -> Optional[str]:
    """
    Generate display_name for Carpet category items.
    
    Formats as: [COLOR/TYPE] - [DESCRIPTION]
    Examples:
    - 'BLUE - AERMAT 9000/8451'
    - 'WOVEN - CARPET'
    - 'GREY - AERMAT 9000/992'
    - 'ECONYL RIPS - CARPET'
    
    Args:
        description: Product description
        category: Product category
    
    Returns:
        Formatted display name or None if not a carpet item
    """
    if not description:
        return None
    
    # Check if item belongs to Carpet category
    category_lower = category.lower() if category else ""
    description_upper = description.upper()
    
    is_carpet_category = category_lower == "carpet"
    is_aermat_or_carpet = 'AERMAT' in description_upper or 'CARPET' in description_upper
    
    if not (is_carpet_category or is_aermat_or_carpet):
        return None
    
    # Determine the color/type prefix
    color_type = ""
    
    # Check for AERMAT colors
    if 'AERMAT' in description_upper:
        if 'BLUE' in description_upper or '8451' in description_upper:
            color_type = "BLUE"
        elif 'GREY' in description_upper or '992' in description_upper:
            color_type = "GREY"
        else:
            # Default to extracting from description
            if 'BLUE' in description_upper:
                color_type = "BLUE"
            elif 'GREY' in description_upper:
                color_type = "GREY"
    
    # Check for CARPET types
    if 'CARPET' in description_upper:
        if 'WOVEN' in description_upper:
            color_type = "WOVEN"
        elif 'ECONYL' in description_upper or 'RIPS' in description_upper:
            color_type = "ECONYL RIPS"
        else:
            # Default to extracting from description
            if 'WOVEN' in description_upper:
                color_type = "WOVEN"
            elif 'ECONYL' in description_upper:
                color_type = "ECONYL RIPS"
            elif 'RIPS' in description_upper:
                color_type = "ECONYL RIPS"
    
    # If we found a color/type, format the display name
    if color_type:
        return f"{color_type} - {description}"
    
    return None


def is_expiring_soon(expiry_date_str: str) -> bool:
    """
    Check if an item is expiring within 30 days using Africa/Nairobi timezone.
    
    Args:
        expiry_date_str: Expiry date string (ISO format YYYY-MM-DD)
    
    Returns:
        True if item is expiring within 30 days, False otherwise
    """
    if not expiry_date_str:
        return False
    
    try:
        # Use Nairobi timezone for date comparison
        nairobi_tz = pytz.timezone('Africa/Nairobi')
        now = datetime.now(nairobi_tz)
        
        # Parse expiry date
        if isinstance(expiry_date_str, str):
            expiry_date = datetime.strptime(expiry_date_str, "%Y-%m-%d")
            # Make it timezone-aware
            expiry_date = nairobi_tz.localize(expiry_date)
        else:
            return False
        
        # Check if expiry is within 30 days
        days_until_expiry = (expiry_date - now).days
        
        # Return True if expiring within 30 days (including expired items)
        return days_until_expiry <= 30
    except Exception:
        return False


def get_low_stock_items() -> List[dict]:
    """
    Get all items where current_stock <= min_threshold.
    Each item has its own min_threshold value (default 5 if not set).
    
    Returns:
        List of low stock items with part_number, description, current_stock, min_threshold, uom
    """
    supabase = get_supabase_client()
    
    try:
        # Universal Fail-Safe: Use .select('*') to get all columns
        response = supabase.table("aviation_inventory").select("*").execute()
        
        low_stock_items = []
        if response.data:
            for row in response.data:
                # Python Dictionary Fix: Use .get() with defaults for every column
                current_stock = float(row.get("current_stock", 0)) if row.get("current_stock") else 0
                min_threshold = float(row.get('min_threshold', 5))
                
                # Check if current_stock <= min_threshold
                if current_stock <= min_threshold:
                    item = {
                        "part_number": row.get("part_number", ""),
                        "description": row.get("description", ""),
                        "current_stock": current_stock,
                        "min_threshold": min_threshold,
                        "uom": row.get("uom", "units")
                    }
                    low_stock_items.append(item)
        
        return low_stock_items
    except Exception as e:
        print(f"Error fetching low stock items: {e}")
        # Return empty list instead of crashing
        return []


def build_inventory_items(rows: list) -> List[InventoryItem]:
    """
    Build inventory items from database rows with enhanced display fields.
    
    Args:
        rows: List of inventory rows from Supabase aviation_inventory table
        
    Returns:
        List of InventoryItem objects with calculated fields
    """
    items = []
    for row in rows:
        # Get current stock
        current_stock = float(row.get("current_stock", 0)) if row.get("current_stock") else 0
        uom = row.get("uom", "")
        description = row.get("description", "")
        
        # Determine stock unit (Linear Meters for AERMAT/CARPET)
        stock_unit = get_stock_unit(description, current_stock, uom)
        
        # Create stock_display with unit
        stock_display = f"{current_stock} {stock_unit}" if current_stock > 0 else "Out of Stock"
        
        # Check if it's a paint kit (KG + paint-related description)
        notes = None
        if is_paint_kit(description, uom):
            notes = "NOTE: This is a paint kit. The 1:1:1 ratio logic applies - for every 1KG of paint, 1KG of hardener and 1KG of thinner are required for proper mixing."
        
        # Get display_name for Carpet items
        category = row.get("category", "")
        display_name = get_carpet_display_name(description, category)
        
        # Create inventory item with all columns from aviation_inventory
        item = InventoryItem(
            part_number=row.get("part_number", ""),
            description=description,
            opening_stock=float(row.get("opening_stock")) if row.get("opening_stock") else None,
            uom=uom,
            cont=float(row.get("cont")) if row.get("cont") else None,
            sold_stock=float(row.get("sold_stock")) if row.get("sold_stock") else None,
            in_house=float(row.get("in_house")) if row.get("in_house") else None,
            current_stock=current_stock,
            batch_no=row.get("batch_no"),
            dom=str(row.get("dom")) if row.get("dom") else None,
            category=category,
            # Custom fields
            stock_display=stock_display,
            is_available=current_stock > 0,
            stock_unit=stock_unit,
            notes=notes,
            display_name=display_name
        )
        items.append(item)
    
    return items


# =============================================================================
# API ENDPOINTS
# =============================================================================

@app.get("/")
async def root(request: Request):
    """
    Root endpoint - returns HTML dashboard with time-based greeting.
    
    Universal Fail-Safe:
    - Uses .select('*') to get all columns
    - Uses .get() with defaults for every column
    - Never crashes even if table is empty or missing columns
    """
    # Use Nairobi timezone for accurate greeting
    nairobi_tz = pytz.timezone('Africa/Nairobi')
    current_hour = datetime.now(nairobi_tz).hour
    
    # 05:00-11:59 = Good Morning
    # 12:00-17:59 = Good Afternoon
    # Otherwise (18:00-04:59) = Good Evening
    if 5 <= current_hour < 12:
        greeting = "Good Morning, AISL Aviation Team"
    elif 12 <= current_hour < 18:
        greeting = "Good Afternoon"
    else:
        greeting = "Good Evening"
    
    # Universal Fail-Safe: Use .select('*') and .get() with defaults
    try:
        supabase = get_supabase_client()
        
        # Use .select('*') to get all columns
        response = supabase.table("aviation_inventory").select("*").execute()
        
        # Use .get() with defaults for every column that might be missing
        items = response.data or []
        low_stock_items = [
            item for item in items
            if float(item.get('current_stock', 0)) <= float(item.get('min_threshold', 5))
        ]
        low_stock_count = len(low_stock_items)
    except Exception as e:
        print(f"Error fetching low stock items: {e}")
        # Return empty list on error - fail-safe
        low_stock_items = []
        low_stock_count = 0
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "greeting": greeting,
        "low_stock_items": low_stock_items,
        "low_stock_count": low_stock_count
    })


@app.get("/inventory", response_model=InventoryResponse)
async def get_inventory(
    type: Optional[str] = Query(
        None, 
        description="Filter by type: 'carpet' or 'paint'"
    )
):
    """
    Get inventory items from the aviation_inventory table.
    
    Returns all columns from the Supabase aviation_inventory table with:
    - stock_display: Formatted stock with unit (e.g., '180 KG', '50 Linear Meters')
    - is_available: Boolean indicating if item is in stock
    - stock_unit: The unit to display (KG/L/Linear Meters)
    - notes: Additional notes for paint kits (1:1:1 ratio logic)
    
    Special handling:
    - AERMAT/CARPET items: Stock displayed in 'Linear Meters'
    - Paint kits (KG + paint keywords): Includes 1:1:1 ratio note
    
    Query Parameters:
    - type: Filter by 'carpet' or 'paint'
    
    Returns:
        Inventory items with all columns and calculated fields
    
    Examples:
    - /inventory - All items
    - /inventory?type=carpet - Only carpet items
    - /inventory?type=paint - Only paint items
    """
    supabase = get_supabase_client()
    
    try:
        # Explicitly select columns to avoid error 42703 (undefined column)
        response = supabase.table("aviation_inventory").select(
            "id, part_number, description, opening_stock, uom, cont, sold_stock, in_house, current_stock, min_threshold, batch_no, dom, expiry_date, category, barcode_number, preferred_supplier_id, unit_price_usd"
        ).execute()
        
        if not response.data:
            return InventoryResponse(
                success=True,
                message="No inventory items found",
                items=[],
                total_count=0
            )
        
        # Filter by type if specified
        filtered_items = response.data
        
        if type and type.lower() == "carpet":
            # Filter for carpet items: Aermat, Carpet
            filtered_items = [
                item for item in response.data 
                if item.get("category", "").lower() == "carpet" or
                   (item.get("description") and 
                    ('AERMAT' in item.get("description", "").upper() or 
                     'CARPET' in item.get("description", "").upper()))
            ]
            message = f"Showing carpet items. Found {len(filtered_items)} item(s)."
            
        elif type and type.lower() == "paint":
            # Filter for paint items
            filtered_items = [
                item for item in response.data 
                if item.get("category", "").lower() == "paint"
            ]
            message = f"Showing paint items. Found {len(filtered_items)} item(s)."
            
        else:
            message = f"Showing all inventory items. Found {len(filtered_items)} item(s)."
        
        # Build inventory items with enhanced display fields
        inventory_items = build_inventory_items(filtered_items)
        
        return InventoryResponse(
            success=True,
            message=message,
            items=inventory_items,
            total_count=len(inventory_items)
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error fetching inventory: {str(e)}"
        )


@app.get("/health", response_model=dict)
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }


# =============================================================================
# LOW STOCK API ENDPOINTS (Real-time Polling)
# =============================================================================

@app.get("/api/low-stock/count")
async def get_low_stock_count():
    """
    API endpoint to get the count of low stock items.
    Used for real-time polling from the dashboard.
    
    Returns:
        JSON with count of items where current_stock <= 5 (hardcoded threshold)
    
    Completely fail-safe:
    - Try/except everything
    - Default to 0 if error
    - Fetch only current_stock and do manual calculation
    - Never returns 500 error
    - Returns {'count': 0} on failure (not the error dictionary)
    """
    try:
        supabase = get_supabase_client()
        
        # Use .select('*') for universal fail-safe
        response = supabase.table("aviation_inventory").select("*").execute()
        
        # Manual calculation: count items where current_stock <= 5
        low_stock_count = 0
        if response.data:
            for row in response.data:
                # Python Dictionary Fix: Use .get() with defaults
                current_stock = float(row.get("current_stock", 0)) if row.get("current_stock") else 0
                min_threshold = float(row.get('min_threshold', 5))
                # Check if current_stock <= min_threshold
                if current_stock <= min_threshold:
                    low_stock_count += 1
        
        return {"count": low_stock_count}
    except Exception as e:
        # Default to 0 on any error - return simple {'count': 0} as requested
        print(f"Error in /api/low-stock/count: {e}")
        return {"count": 0}


@app.get("/api/low-stock/details")
async def get_low_stock_details():
    """
    API endpoint to get detailed list of low stock items.
    Used for displaying the modal with part numbers and quantities.
    
    Returns:
        JSON with list of low stock items (part_number, description, current_stock, min_threshold, uom)
    """
    try:
        low_stock_items = get_low_stock_items()
        return {
            "success": True,
            "items": low_stock_items,
            "count": len(low_stock_items)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "items": [],
            "count": 0
        }


# =============================================================================
# PAGE ROUTES WITH TEMPLATES
# =============================================================================

@app.get("/stock")
async def stock_page(request: Request):
    """
    Stock Management page - renders stock.html with inventory data.
    Includes Manual Entry Form at the top.
    
    Universal Fail-Safe:
    - Uses .select('*') to get all columns
    - Uses .get() with defaults for every column
    """
    supabase = get_supabase_client()
    
    try:
        # Universal Fail-Safe: Use .select('*') to get all columns
        response = supabase.table("aviation_inventory").select("*").execute()
        
        # Separate paints and carpets
        paints = []
        carpets = []
        
        if response.data:
            for row in response.data:
                # Python Dictionary Fix: Use .get() with defaults for every column
                description = row.get("description", "").upper()
                category = row.get("category", "").lower() if row.get("category") else ""
                
                # Determine if it's carpet or paint
                is_carpet = category == "carpet" or "CARPET" in description or "AERMAT" in description
                
                # Get color_type for display
                color_type = None
                if "BLUE" in description or "8451" in description:
                    color_type = "BLUE"
                elif "GREY" in description or "992" in description:
                    color_type = "GREY"
                elif "WOVEN" in description:
                    color_type = "WOVEN"
                elif "ECONYL" in description or "RIPS" in description:
                    color_type = "ECONYL RIPS"
                
                # Get expiry date and check if expiring soon
                expiry_date = row.get("expiry_date")
                expiring_soon = is_expiring_soon(expiry_date)
                
                # Format expiry date for display
                expiry_display = None
                if expiry_date:
                    try:
                        # Format as DD/MM/YYYY for display
                        exp_date = datetime.strptime(str(expiry_date), "%Y-%m-%d")
                        expiry_display = exp_date.strftime("%d/%m/%Y")
                    except:
                        expiry_display = str(expiry_date)
                
                # Python Dictionary Fix: Use .get() with defaults
                item = {
                    "part_number": row.get("part_number", ""),
                    "description": row.get("description", ""),
                    "current_stock": float(row.get("current_stock", 0)) if row.get("current_stock") else 0,
                    "uom": row.get("uom", "KG"),
                    "category": row.get("category", ""),
                    "is_available": (row.get("current_stock", 0) or 0) > 0,
                    "color_type": color_type,
                    "batch_no": row.get("batch_no"),
                    "expiry_date": expiry_display,
                    "is_expiring_soon": expiring_soon
                }
                
                if is_carpet:
                    carpets.append(item)
                else:
                    paints.append(item)
        
        return templates.TemplateResponse("stock.html", {
            "request": request,
            "greeting": get_greeting(),
            "paints": paints,
            "carpets": carpets
        })
    except Exception as e:
        # Return empty lists on error - fail-safe
        return templates.TemplateResponse("stock.html", {
            "request": request,
            "greeting": get_greeting(),
            "paints": [],
            "carpets": []
        })


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
    batch_no = form_data.get("batch_no", "").strip()
    expiry_date = form_data.get("expiry_date", "").strip()
    barcode_number = form_data.get("barcode_number", "").strip()
    min_threshold = form_data.get("min_threshold", "5").strip()
    
    if not part_number or not description:
        # Redirect back to stock with error (could add error handling)
        return RedirectResponse(url="/stock", status_code=303)
    
    try:
        supabase = get_supabase_client()
        
        # Parse min_threshold, default to 5 if invalid, convert to integer
        try:
            min_threshold_value = int(min_threshold) if min_threshold else 5
        except ValueError:
            min_threshold_value = 5
        
        # Insert into aviation_inventory table
        new_item = {
            "part_number": part_number,
            "description": description,
            "category": category,
            "current_stock": 0,
            "opening_stock": 0,
            "uom": "KG",  # Default UOM
            "min_threshold": min_threshold_value
        }
        
        # Add batch number if provided
        if batch_no:
            new_item["batch_no"] = batch_no
        
        # Add expiry date if provided (validate format)
        if expiry_date:
            # Ensure date is in YYYY-MM-DD format for Supabase
            try:
                from datetime import datetime
                # Try to parse and reformat the date
                exp_date = datetime.strptime(expiry_date, "%Y-%m-%d")
                new_item["expiry_date"] = exp_date.strftime("%Y-%m-%d")
            except ValueError:
                # If already in correct format or invalid, just store as-is
                new_item["expiry_date"] = expiry_date
        
        # Add barcode number if provided
        if barcode_number:
            new_item["barcode_number"] = barcode_number
        
        supabase.table("aviation_inventory").insert(new_item).execute()
        
    except Exception as e:
        print(f"Error adding item: {e}")
    
    return RedirectResponse(url="/stock", status_code=303)


@app.get("/sales")
async def sales_page(request: Request):
    """Sales page."""
    return templates.TemplateResponse("sales.html", {
        "request": request,
        "greeting": get_greeting()
    })


@app.get("/purchase-orders")
async def purchase_orders_page(request: Request):
    """
    Purchase Orders page.
    Supports pre-filling from query parameters (part_number, description)
    for quick PO generation from low stock alerts.
    """
    now = datetime.now()
    current_date = now.strftime("%Y-%m-%d")
    po_number = f"PO-{now.strftime('%y')}-{now.strftime('%m%d')}-{now.strftime('%H%M%S')}"
    
    # Get pre-fill parameters from query string
    prefill_part_number = request.query_params.get("part_number", "")
    prefill_description = request.query_params.get("description", "")
    
    return templates.TemplateResponse("purchase_order.html", {
        "request": request,
        "greeting": get_greeting(),
        "current_date": current_date,
        "po_number": po_number,
        "prefill_part_number": prefill_part_number,
        "prefill_description": prefill_description
    })


@app.get("/completed-orders")
async def completed_orders_page(request: Request):
    """Completed Orders page."""
    return templates.TemplateResponse("completed_orders.html", {
        "request": request,
        "greeting": get_greeting()
    })


@app.get("/reports")
async def reports_page(request: Request):
    """Reports page."""
    return templates.TemplateResponse("reports.html", {
        "request": request,
        "greeting": get_greeting()
    })


@app.get("/quote")
async def quote_page(request: Request):
    """Quote Generator page."""
    now = datetime.now()
    current_date = now.strftime("%d/%m/%Y")
    quote_number = f"QTE-{now.strftime('%Y%m%d')}-{now.strftime('%H%M%S')}"
    
    return templates.TemplateResponse("quote.html", {
        "request": request,
        "greeting": get_greeting(),
        "current_date": current_date,
        "quote_number": quote_number
    })


# =============================================================================
# ISSUE ITEM ROUTES (Barcode Scanning)
# =============================================================================

@app.get("/issue-item")
async def issue_item_page(request: Request):
    """
    Issue Item page - barcode scanner interface for staff to issue items.
    """
    return templates.TemplateResponse("issue_item.html", {
        "request": request,
        "greeting": get_greeting()
    })


@app.get("/staff/issue")
async def staff_issue_page(request: Request):
    """
    Staff Issue Stock page - dedicated simplified interface for staff to issue stock.
    Located at /staff/issue route with no sidebar, just Logout and Issue buttons.
    """
    return templates.TemplateResponse("staff_issue.html", {
        "request": request,
        "greeting": get_greeting()
    })


@app.get("/issue")
async def issue_page(request: Request):
    """
    Stock Issuing page - dedicated form for staff to issue stock.
    """
    return templates.TemplateResponse("issue.html", {
        "request": request,
        "greeting": get_greeting(),
        "success_message": None,
        "error_message": None
    })


@app.post("/issue")
async def issue_stock_post(request: Request):
    """
    Handle stock issue form submission.
    Validates barcode, updates stock, and logs transaction.
    """
    form_data = await request.form()
    staff_name = form_data.get("staff_name", "").strip()
    barcode_id = form_data.get("barcode_id", "").strip()
    quantity = form_data.get("quantity", "").strip()
    
    # Validation
    if not staff_name:
        return templates.TemplateResponse("issue.html", {
            "request": request,
            "greeting": get_greeting(),
            "success_message": None,
            "error_message": "Staff Name is required"
        })
    
    if not barcode_id:
        return templates.TemplateResponse("issue.html", {
            "request": request,
            "greeting": get_greeting(),
            "success_message": None,
            "error_message": "Barcode ID is required"
        })
    
    if not quantity:
        return templates.TemplateResponse("issue.html", {
            "request": request,
            "greeting": get_greeting(),
            "success_message": None,
            "error_message": "Quantity is required"
        })
    
    try:
        quantity_float = float(quantity)
    except ValueError:
        return templates.TemplateResponse("issue.html", {
            "request": request,
            "greeting": get_greeting(),
            "success_message": None,
            "error_message": "Invalid quantity"
        })
    
    if quantity_float <= 0:
        return templates.TemplateResponse("issue.html", {
            "request": request,
            "greeting": get_greeting(),
            "success_message": None,
            "error_message": "Quantity must be greater than 0"
        })
    
    supabase = get_supabase_client()
    
    # Find product by barcode
    try:
        response = supabase.table("aviation_inventory").select("*").eq("barcode_number", barcode_id).execute()
        
        if not response.data or len(response.data) == 0:
            return templates.TemplateResponse("issue.html", {
                "request": request,
                "greeting": get_greeting(),
                "success_message": None,
                "error_message": "Product not found with this Barcode ID"
            })
        
        product = response.data[0]
        part_number = product.get("part_number")
        description = product.get("description")
        current_stock = float(product.get("current_stock", 0)) if product.get("current_stock") else 0
        
        # Check if enough stock
        if quantity_float > current_stock:
            return templates.TemplateResponse("issue.html", {
                "request": request,
                "greeting": get_greeting(),
                "success_message": None,
                "error_message": f"Insufficient stock. Available: {current_stock}"
            })
        
        # Calculate new stock
        new_stock = current_stock - quantity_float
        
        # Update stock in aviation_inventory
        supabase.table("aviation_inventory").update({
            "current_stock": new_stock
        }).eq("part_number", part_number).execute()
        
        # Log transaction in stock_logs
        try:
            supabase.table("stock_logs").insert({
                "part_number": part_number,
                "transaction_type": "ISSUE",
                "quantity": quantity_float,
                "previous_stock": current_stock,
                "new_stock": new_stock,
                "notes": f"Issued by: {staff_name}"
            }).execute()
        except Exception as log_error:
            print(f"Error logging stock transaction: {log_error}")
        
        # Success!
        success_message = f"Item {part_number} issued by {staff_name}. Remaining stock: {new_stock}"
        
        return templates.TemplateResponse("issue.html", {
            "request": request,
            "greeting": get_greeting(),
            "success_message": success_message,
            "error_message": None
        })
        
    except Exception as e:
        return templates.TemplateResponse("issue.html", {
            "request": request,
            "greeting": get_greeting(),
            "success_message": None,
            "error_message": f"Error: {str(e)}"
        })


@app.get("/api/product/search")
async def search_product(q: str = Query(..., description="Search query (barcode or part number)")):
    """
    Search for a product by barcode number or part number.
    Used by the barcode scanner interface.
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


@app.get("/api/barcode/check")
async def check_barcode_exists(barcode: str = Query(..., description="Barcode to check")):
    """
    Check if a barcode already exists in the database.
    Used for smart validation when adding new products.
    """
    supabase = get_supabase_client()
    
    try:
        # Search by barcode_number only
        response = supabase.table("aviation_inventory").select("part_number, description").eq("barcode_number", barcode).execute()
        
        if response.data and len(response.data) > 0:
            product = response.data[0]
            return {
                "exists": True,
                "part_number": product.get("part_number"),
                "description": product.get("description")
            }
        else:
            return {
                "exists": False
            }
    except Exception as e:
        return {
            "exists": False,
            "error": str(e)
        }


@app.post("/api/product/issue")
async def issue_product(request: Request):
    """
    Issue/Subtract stock from a product.
    Used by the barcode scanner interface.
    Records the transaction in stock_logs table.
    """
    from fastapi.responses import JSONResponse
    
    try:
        body = await request.json()
        part_number = body.get("part_number", "").strip()
        quantity = float(body.get("quantity", 0))
        
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
        
        # Get current stock
        response = supabase.table("aviation_inventory").select("current_stock, min_threshold").eq("part_number", part_number).execute()
        
        if not response.data or len(response.data) == 0:
            return JSONResponse(
                status_code=404,
                content={"success": False, "detail": "Product not found"}
            )
        
        current_stock = float(response.data[0].get("current_stock", 0)) if response.data[0].get("current_stock") else 0
        min_threshold = float(response.data[0].get("min_threshold", 5)) if response.data[0].get("min_threshold") else 5
        new_stock = current_stock - quantity
        
        # Ensure stock doesn't go negative
        if new_stock < 0:
            new_stock = 0
        
        # Update the stock
        supabase.table("aviation_inventory").update({
            "current_stock": new_stock
        }).eq("part_number", part_number).execute()
        
        # Record transaction in stock_logs
        try:
            supabase.table("stock_logs").insert({
                "part_number": part_number,
                "transaction_type": "ISSUE",
                "quantity": quantity,
                "previous_stock": current_stock,
                "new_stock": new_stock,
                "notes": f"Issued via staff portal"
            }).execute()
        except Exception as log_error:
            print(f"Error logging stock transaction: {log_error}")
        
        # Check if stock is now low
        is_low_stock = new_stock <= min_threshold
        
        return {
            "success": True,
            "message": f"Successfully issued {quantity} units",
            "new_stock": new_stock,
            "previous_stock": current_stock,
            "issued_quantity": quantity,
            "low_stock": is_low_stock
        }
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "detail": str(e)}
        )


# =============================================================================
# STAFF ISSUE API ENDPOINT
# =============================================================================

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
# SUPPLIERS ROUTES
# =============================================================================

@app.get("/suppliers")
async def suppliers_page(request: Request):
    """
    Suppliers Management page - renders suppliers.html with supplier data.
    """
    supabase = get_supabase_client()
    
    try:
        # Fetch all suppliers from the suppliers table
        response = supabase.table("suppliers").select("*").order("supplier_name").execute()
        
        suppliers = []
        if response.data:
            suppliers = response.data
        
        return templates.TemplateResponse("suppliers.html", {
            "request": request,
            "greeting": get_greeting(),
            "suppliers": suppliers
        })
    except Exception as e:
        return templates.TemplateResponse("suppliers.html", {
            "request": request,
            "greeting": get_greeting(),
            "suppliers": []
        })


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
async def get_suppliers_api():
    """
    API endpoint to get all suppliers for dropdown integration.
    """
    supabase = get_supabase_client()
    
    try:
        response = supabase.table("suppliers").select("id, supplier_name").order("supplier_name").execute()
        
        return {
            "success": True,
            "suppliers": response.data if response.data else []
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@app.delete("/api/supplier/{supplier_id}")
async def delete_supplier(supplier_id: str):
    """
    Delete a supplier by ID.
    """
    supabase = get_supabase_client()
    
    try:
        supabase.table("suppliers").delete().eq("id", supplier_id).execute()
        
        return {
            "success": True,
            "message": "Supplier deleted successfully"
        }
    except Exception as e:
        return {
            "success": False,
            "detail": str(e)
        }


# =============================================================================
# ORDER VIEW/PRINT ROUTES
# =============================================================================

@app.get("/orders/view/{order_id}")
async def view_order(request: Request, order_id: str):
    """
    View and print order details - renders order_print.html with order data.
    """
    supabase = get_supabase_client()
    
    try:
        # Try to fetch from purchase_orders table first
        response = supabase.table("purchase_orders").select("*").eq("id", order_id).execute()
        
        if response.data and len(response.data) > 0:
            order = response.data[0]
            
            # Fetch order items
            items_response = supabase.table("purchase_order_items").select("*").eq("po_id", order_id).execute()
            items = items_response.data if items_response.data else []
            
            # Format dates
            po_date = order.get("po_date", "")
            if po_date:
                try:
                    dt = datetime.strptime(po_date, "%Y-%m-%d")
                    po_date = dt.strftime("%d/%m/%Y")
                except:
                    pass
            
            created_at = order.get("created_at", "")
            if created_at:
                try:
                    dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    created_at = dt.strftime("%d/%m/%Y %H:%M")
                except:
                    pass
            
            order_data = {
                "order_number": order.get("po_number", ""),
                "order_date": po_date,
                "supplier": order.get("supplier", ""),
                "total": float(order.get("total_usd", 0)) if order.get("total_usd") else 0,
                "status": order.get("status", ""),
                "created_at": created_at,
                "items": items,
                "order_type": "Purchase Order"
            }
            
            return templates.TemplateResponse("order_print.html", {
                "request": request,
                "greeting": get_greeting(),
                "order": order_data
            })
        
        # Try sales_quotes table
        quote_response = supabase.table("sales_quotes").select("*").eq("id", order_id).execute()
        
        if quote_response.data and len(quote_response.data) > 0:
            quote = quote_response.data[0]
            
            # Fetch quote items
            items_response = supabase.table("sales_quote_items").select("*").eq("quote_id", order_id).execute()
            items = items_response.data if items_response.data else []
            
            # Format dates
            quote_date = quote.get("created_at", "")
            if quote_date:
                try:
                    dt = datetime.fromisoformat(quote_date.replace('Z', '+00:00'))
                    quote_date = dt.strftime("%d/%m/%Y %H:%M")
                except:
                    pass
            
            order_data = {
                "order_number": quote.get("quote_number", ""),
                "order_date": quote_date,
                "customer": quote.get("customer_name", ""),
                "customer_email": quote.get("customer_email", ""),
                "customer_phone": quote.get("customer_phone", ""),
                "total": float(quote.get("grand_total", 0)) if quote.get("grand_total") else 0,
                "status": quote.get("status", ""),
                "created_at": quote_date,
                "items": items,
                "order_type": "Sales Quote"
            }
            
            return templates.TemplateResponse("order_print.html", {
                "request": request,
                "greeting": get_greeting(),
                "order": order_data
            })
        
        # Order not found
        return templates.TemplateResponse("order_print.html", {
            "request": request,
            "greeting": get_greeting(),
            "order": None,
            "error": "Order not found"
        })
        
    except Exception as e:
        return templates.TemplateResponse("order_print.html", {
            "request": request,
            "greeting": get_greeting(),
            "order": None,
            "error": str(e)
        })


# =============================================================================
# STOCK LOGS ROUTES
# =============================================================================

@app.get("/admin/logs")
async def stock_logs_page(request: Request):
    """
    Stock Logs page - displays all stock transaction logs.
    Supports search by staff name or part number.
    """
    from urllib.parse import urlencode
    
    # Get search query from URL
    search_query = request.query_params.get("search", "").strip()
    
    supabase = get_supabase_client()
    
    try:
        # Fetch all stock logs ordered by date descending
        if search_query:
            # Search by part_number or notes (which contains staff name)
            response = supabase.table("stock_logs").select("*").or_(
                f"part_number.ilike.%{search_query}%,notes.ilike.%{search_query}%"
            ).order("created_at", desc=True).execute()
        else:
            response = supabase.table("stock_logs").select("*").order("created_at", desc=True).execute()
        
        logs = []
        if response.data:
            for row in response.data:
                # Format the created_at timestamp
                created_at = row.get("created_at")
                if created_at:
                    try:
                        dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        formatted_date = dt.strftime("%d/%m/%Y %H:%M")
                    except:
                        formatted_date = str(created_at)
                else:
                    formatted_date = "-"
                
                log_entry = {
                    "created_at": formatted_date,
                    "part_number": row.get("part_number", ""),
                    "transaction_type": row.get("transaction_type", ""),
                    "quantity": float(row.get("quantity", 0)) if row.get("quantity") else 0,
                    "previous_stock": float(row.get("previous_stock", 0)) if row.get("previous_stock") else 0,
                    "new_stock": float(row.get("new_stock", 0)) if row.get("new_stock") else 0,
                    "notes": row.get("notes", "")
                }
                logs.append(log_entry)
        
        return templates.TemplateResponse("stock_logs.html", {
            "request": request,
            "greeting": get_greeting(),
            "logs": logs,
            "search_query": search_query
        })
    except Exception as e:
        return templates.TemplateResponse("stock_logs.html", {
            "request": request,
            "greeting": get_greeting(),
            "logs": [],
            "search_query": search_query
        })


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    
    print("=" * 60)
    print("Aviation ERP API Starting...")
    print("=" * 60)
    print(f"\nSupabase URL: {settings.SUPABASE_URL or 'Not configured'}")
    print(f"\nAPI Docs: http://localhost:8000/docs")
    print("=" * 60)
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
