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
from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime

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
    category: Optional[str] = None
    # Custom fields added by API
    stock_display: Optional[str] = Field(default=None, description="Stock with unit")
    is_available: bool = Field(default=False, description="Whether item is in stock")
    stock_unit: Optional[str] = Field(default=None, description="Stock unit (KG/L/Linear Meters)")
    notes: Optional[str] = Field(default=None, description="Additional notes for paint kits")
    display_name: Optional[str] = Field(default=None, description="Formatted display name for Carpet items: [COLOR/TYPE] - [DESCRIPTION]")


class InventoryResponse(BaseModel):
    """Response model for inventory endpoint."""
    success: bool
    message: str
    items: List[InventoryItem]
    total_count: int


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

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
    
    Time-based greeting:
    - 05:00-11:59: 'Good Morning, AISL Aviation Team'
    - 12:00-17:59: 'Good Afternoon'
    - Otherwise (18:00-04:59): 'Good Evening'
    """
    now = datetime.now()
    current_hour = now.hour
    
    # 05:00-11:59 = Good Morning
    # 12:00-17:59 = Good Afternoon
    # Otherwise (18:00-04:59) = Good Evening
    if 5 <= current_hour < 12:
        greeting = "Good Morning, AISL Aviation Team"
    elif 12 <= current_hour < 18:
        greeting = "Good Afternoon"
    else:
        greeting = "Good Evening"
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "greeting": greeting
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
        # Fetch all items from aviation_inventory table
        response = supabase.table("aviation_inventory").select("*").execute()
        
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
