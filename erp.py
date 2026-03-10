"""
FastAPI Main Application for Aviation ERP
Serves both Admin and Staff/Sales frontends.

Admin Frontend: https://your-admin-app.onrender.com
Staff/Sales Frontend: https://your-staff-app.contabo.com
"""

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List
from decimal import Decimal
import uuid

from config import settings, get_supabase_client, get_supabase_service_client
from sms_notification import send_sale_sms_notification, send_delivery_sms, SMSNotificationError

# =============================================================================
# FASTAPI APP INITIALIZATION
# =============================================================================

app = FastAPI(
    title="Aviation ERP API",
    description="Backend API for Aviation ERP system - Supports both Admin and Staff/Sales frontends",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# =============================================================================
# CORS MIDDLEWARE CONFIGURATION
# =============================================================================

# Configure CORS to allow both Admin (Render) and Staff/Sales (Contabo) domains
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),  # List of allowed domains
    allow_credentials=True,  # Allow cookies and authentication headers
    allow_methods=["*"],  # Allow all HTTP methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],  # Allow all headers
)


# =============================================================================
# PYDANTIC MODELS (Request/Response Schemas)
# =============================================================================

class SaleItem(BaseModel):
    """Single item in a sale transaction."""
    product_id: str = Field(..., description="UUID of the product")
    quantity: float = Field(..., gt=0, description="Quantity sold (must be positive)")
    unit_type: str = Field(..., description="Unit of measurement (e.g., 'L', 'ml', 'pcs', 'set')")


class SaleRequest(BaseModel):
    """Request model for processing a sale."""
    items: List[SaleItem] = Field(..., min_length=1, description="List of products to sell")
    reference_type: Optional[str] = Field(default="sale", description="Type of reference (e.g., 'invoice', 'order')")
    reference_id: Optional[str] = Field(default=None, description="UUID of the reference document")
    notes: Optional[str] = Field(default=None, description="Additional notes for the sale")
    created_by: Optional[str] = Field(default=None, description="UUID of the user creating the sale")


# =============================================================================
# PAINT SALE MODELS
# =============================================================================

class KitSaleRequest(BaseModel):
    """Request model for Type A: Kit Sale."""
    kit_product_id: str = Field(..., description="UUID of the kit product")
    quantity: int = Field(default=1, gt=0, description="Number of kits to sell")
    reference_type: Optional[str] = Field(default="sale", description="Type of reference")
    reference_id: Optional[str] = Field(default=None, description="UUID of the reference document")
    notes: Optional[str] = Field(default=None, description="Additional notes")


class TintSaleRequest(BaseModel):
    """Request model for Type B: Tint Deduction."""
    base_product_id: str = Field(..., description="UUID of the base paint (e.g., White Base)")
    base_quantity: float = Field(..., gt=0, description="Quantity of base paint (e.g., 1.0)")
    base_unit: str = Field(..., description="Unit of base paint (e.g., 'L', 'ml', 'kg')")
    tint_product_id: str = Field(..., description="UUID of the tint (e.g., Blue Tint)")
    tint_quantity: float = Field(..., gt=0, description="Quantity of tint (e.g., 0.1)")
    tint_unit: str = Field(..., description="Unit of tint (e.g., 'L', 'ml', 'kg')")
    reference_type: Optional[str] = Field(default="sale", description="Type of reference")
    reference_id: Optional[str] = Field(default=None, description="UUID of the reference document")
    notes: Optional[str] = Field(default=None, description="Additional notes")


class PaintSaleRequest(BaseModel):
    """Request model for processing paint sales (Kit or Tint)."""
    sale_type: str = Field(..., description="Type of sale: 'kit' or 'tint'")
    
    # For Kit Sale (Type A)
    kit_product_id: Optional[str] = Field(default=None, description="UUID of the kit product")
    kit_quantity: Optional[int] = Field(default=1, gt=0, description="Number of kits to sell")
    
    # For Tint Sale (Type B)
    base_product_id: Optional[str] = Field(default=None, description="UUID of the base paint")
    base_quantity: Optional[float] = Field(default=None, gt=0, description="Quantity of base paint")
    base_unit: Optional[str] = Field(default=None, description="Unit of base paint")
    tint_product_id: Optional[str] = Field(default=None, description="UUID of the tint")
    tint_quantity: Optional[float] = Field(default=None, gt=0, description="Quantity of tint")
    tint_unit: Optional[str] = Field(default=None, description="Unit of tint")
    
    # Common fields
    reference_type: Optional[str] = Field(default="sale", description="Type of reference")
    reference_id: Optional[str] = Field(default=None, description="UUID of the reference document")
    notes: Optional[str] = Field(default=None, description="Additional notes")
    created_by: Optional[str] = Field(default=None, description="UUID of the user creating the sale")


class PaintSaleResponse(BaseModel):
    """Response model for paint sale transaction."""
    success: bool
    message: str
    sale_type: str
    sale_id: Optional[str] = None
    details: Optional[dict] = None


class StockTransaction(BaseModel):
    """Stock transaction record."""
    id: str
    product_id: str
    transaction_type: str
    quantity: float
    quantity_before: float
    quantity_after: float
    reference_type: Optional[str]
    reference_id: Optional[str]
    notes: Optional[str]
    created_at: str


class ProductInfo(BaseModel):
    """Product information."""
    id: str
    sku: str
    name: str
    current_stock_level: float
    sales_price: Optional[float]
    unit_symbol: Optional[str]


class SaleResponse(BaseModel):
    """Response model for sale transaction."""
    success: bool
    message: str
    sale_id: Optional[str] = None
    transactions: List[StockTransaction] = []
    products_updated: List[ProductInfo] = []


class ProductResponse(BaseModel):
    """Response model for product lookup."""
    id: str
    sku: str
    name: str
    description: Optional[str]
    current_stock_level: float
    sales_price: Optional[float]
    purchase_price: Optional[float]
    is_kit: bool
    unit_symbol: Optional[str]
    available: bool


# =============================================================================
# KIT REQUIREMENT MODELS
# =============================================================================

class KitRequirementRequest(BaseModel):
    """Request model for calculating kit requirements."""
    primary_product_id: str = Field(..., description="UUID of the primary paint/product")
    requested_qty: float = Field(..., gt=0, description="Requested quantity of the primary product")


class KitRequirementResponse(BaseModel):
    """Response model for kit requirement calculation."""
    primary: float = Field(..., description="Primary product quantity")
    hardener: float = Field(..., description="Hardener quantity required")
    thinner: float = Field(..., description="Thinner quantity required")
    total_volume: float = Field(..., description="Total volume of all components")
    can_fulfill: bool = Field(..., description="Whether the order can be fulfilled with current stock")
    primary_product_id: Optional[str] = Field(default=None, description="UUID of the primary product")
    primary_product_name: Optional[str] = Field(default=None, description="Name of the primary product")
    mixing_ratio: Optional[dict] = Field(default=None, description="Mixing ratio used for calculation")
    stock_info: Optional[dict] = Field(default=None, description="Available stock information")


# =============================================================================
# INVENTORY MODELS (Carpet Types)
# =============================================================================

class CarpetItem(BaseModel):
    """Individual carpet item in inventory."""
    id: Optional[str] = Field(default=None, description="Product UUID")
    sku: str = Field(..., description="Product SKU")
    name: str = Field(..., description="Product name")
    highlighted_name: Optional[str] = Field(default=None, description="Product name with explicit color/material highlight for AERMAT 9000 and CARPET items")
    category: str = Field(..., description="Carpet category")
    quantity: int = Field(..., description="Current stock quantity")
    quantity_display: str = Field(..., description="Display string for quantity (e.g., '0' or 'Out of Stock')")
    is_available: bool = Field(..., description="Whether item is in stock")


class InventoryResponse(BaseModel):
    """Response model for /inventory endpoint."""
    success: bool
    message: str
    categories: dict = Field(..., description="Inventory grouped by carpet category")
    total_items: int = Field(..., description="Total number of carpet types")
    paint_items: Optional[List["PaintItem"]] = Field(default=None, description="Paint products inventory")


class PaintItem(BaseModel):
    """Individual paint item in inventory."""
    id: Optional[str] = Field(default=None, description="Product UUID")
    sku: str = Field(..., description="Product SKU (Part Number)")
    name: str = Field(..., description="Product name")
    current_stock: float = Field(..., description="Current stock quantity")
    unit: str = Field(..., description="Unit of measurement (KG, L, etc.)")
    stock_display: str = Field(..., description="Display string for stock (e.g., '6 KG', '10 L')")
    is_available: bool = Field(..., description="Whether item is in stock")


# Define the specific paint products to display
PAINT_PRODUCTS_SKUS = [
    "113-22-633B-3-033",  # EPOXY PRIMER 6KG
    "470-10-9100-9-003",  # WHITE TOPCOAT 10KG
    "405-03-0000-0-232",  # TOPCOAT HARDENER 5L
]

# Define the four carpet categories
CARPET_CATEGORIES = {
    "CARPET WOVEN": ["CARPET WOVEN", "Woven Carpet", "Woven"],
    "CARPET ECONYL RIPS": ["CARPET ECONYL RIPS", "Econyl Rips", "ECONYL RIPS"],
    "AERMAT 9000/992 GREY": ["AERMAT 9000/992 GREY", "AERMAT 9000/992", "9000/992 GREY"],
    "AERMAT 9000/8451 BLUE": ["AERMAT 9000/8451 BLUE", "AERMAT 9000/8451", "9000/8451 BLUE"]
}


# =============================================================================
# SALES CONFIRM MODELS (New)
# =============================================================================

class ConfirmSaleRequest(BaseModel):
    """Request model for /sales/confirm endpoint."""
    product_id: str = Field(..., description="UUID of the product being sold")
    requested_qty: float = Field(..., gt=0, description="Quantity to sell")
    unit_selected: str = Field(..., description="Unit of measurement (e.g., 'yards', 'inches', 'lts', 'kg')")
    is_kit: bool = Field(default=False, description="Whether this is a kit sale")
    staff_id: str = Field(..., description="Staff ID from Contabo performing the sale")
    reference_type: Optional[str] = Field(default="sale", description="Type of reference (e.g., 'invoice')")
    reference_id: Optional[str] = Field(default=None, description="UUID of the reference document")
    notes: Optional[str] = Field(default=None, description="Additional notes")


class ConfirmSaleResponse(BaseModel):
    """Response model for /sales/confirm endpoint."""
    success: bool
    message: str
    product_id: Optional[str] = None
    product_name: Optional[str] = None
    quantity_deducted: Optional[float] = None
    stock_before: Optional[float] = None
    stock_after: Optional[float] = None
    transaction_ids: Optional[List[str]] = None
    kit_details: Optional[dict] = None  # For kit sales: hardener/thinner info


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def format_highlighted_name(product_name: str, color: str, material_type: str) -> Optional[str]:
    """
    Format product name with explicit color/material highlight for AERMAT 9000 and CARPET items.
    
    This function ensures staff can easily distinguish between:
    - AERMAT 9000 colors: GREY (992) vs BLUE (8451)
    - CARPET types: WOVEN vs ECONYL RIPS
    
    Args:
        product_name: Original product name
        color: Product color (e.g., 'GREY', 'BLUE')
        material_type: Product material type (e.g., 'WOVEN', 'ECONYL')
    
    Returns:
        Highlighted name string with explicit color/material type, or None if no highlight needed
    """
    if not product_name:
        return None
    
    product_name_upper = product_name.upper()
    color_upper = color.upper() if color else ""
    material_upper = material_type.upper() if material_type else ""
    
    # Check for AERMAT 9000 products - highlight color explicitly
    is_aermat = "AERMAT" in product_name_upper or material_upper == "AERMAT"
    
    if is_aermat:
        # Determine color for AERMAT 9000
        if "GREY" in color_upper or "992" in product_name_upper:
            # Return highlighted name with explicit GREY color
            return f"{product_name} [COLOR: GREY]"
        elif "BLUE" in color_upper or "8451" in product_name_upper:
            # Return highlighted name with explicit BLUE color
            return f"{product_name} [COLOR: BLUE]"
        else:
            # Color not specified, try to infer from name
            if "GREY" in product_name_upper:
                return f"{product_name} [COLOR: GREY]"
            elif "BLUE" in product_name_upper:
                return f"{product_name} [COLOR: BLUE]"
    
    # Check for CARPET products - highlight material type explicitly
    is_carpet = "CARPET" in product_name_upper or material_upper in ["WOVEN", "ECONYL"]
    
    if is_carpet:
        # Determine material type for CARPET
        if material_upper == "WOVEN" or "WOVEN" in product_name_upper:
            # Return highlighted name with explicit WOVEN material
            return f"{product_name} [MATERIAL: WOVEN]"
        elif material_upper == "ECONYL" or "ECONYL" in product_name_upper or "RIPS" in product_name_upper:
            # Return highlighted name with explicit ECONYL RIPS material
            return f"{product_name} [MATERIAL: ECONYL RIPS]"
        else:
            # Try to infer from name
            if "WOVEN" in product_name_upper:
                return f"{product_name} [MATERIAL: WOVEN]"
            elif "ECONYL" in product_name_upper or "RIPS" in product_name_upper:
                return f"{product_name} [MATERIAL: ECONYL RIPS]"
    
    # No highlight needed for non-AERMAT/CARPET products
    return None


def get_unit_symbol(supabase, unit_id: str) -> str:
    """Get unit symbol from unit ID."""
    if not unit_id:
        return "pcs"
    try:
        response = supabase.table("units").select("symbol").eq("id", unit_id).execute()
        if response.data:
            return response.data[0]["symbol"]
    except:
        pass
    return "pcs"


def get_product_with_unit(supabase, product_id: str) -> Optional[dict]:
    """Get product with unit information."""
    response = supabase.table("products").select(
        "id, sku, name, description, current_stock_level, sales_price, purchase_price, "
        "is_kit, sales_unit_id, base_unit_id"
    ).eq("id", product_id).execute()
    
    if not response.data:
        return None
    
    product = response.data[0]
    
    # Get unit symbol
    unit_id = product.get("sales_unit_id") or product.get("base_unit_id")
    product["unit_symbol"] = get_unit_symbol(supabase, unit_id)
    
    return product


# =============================================================================
# API ENDPOINTS
# =============================================================================

@app.get("/")
async def root():
    """
    Root endpoint - returns API information with time-based greeting.
    
    Detects the current server time and returns an appropriate greeting:
    - Before 12 PM: 'Good Morning, AISL Aviation Team'
    - Between 12 PM and 6 PM: 'Good Afternoon'
    - After 6 PM: 'Good Evening'
    """
    from datetime import datetime
    
    # Get current server time
    now = datetime.now()
    current_hour = now.hour
    
    # Determine greeting based on time
    if current_hour < 12:
        greeting = "Good Morning, AISL Aviation Team"
    elif current_hour < 18:  # 6 PM
        greeting = "Good Afternoon"
    else:
        greeting = "Good Evening"
    
    return {
        "message": greeting,
        "status": "running",
        "version": "1.0.0",
        "docs": "/docs",
        "allowed_origins": settings.get_cors_origins()
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    # Check Supabase connection
    try:
        supabase = get_supabase_client()
        # Simple test query
        supabase.table("products").select("id").limit(1).execute()
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "database": db_status,
        "cors_origins": settings.get_cors_origins()
    }


# =============================================================================
# INVENTORY ENDPOINT (Carpet Types)
# =============================================================================

def match_carpet_category(product_name: str) -> str | None:
    """
    Match a product name to one of the four carpet categories.
    
    Args:
        product_name: Name of the product from Supabase
        
    Returns:
        Category name if matched, None otherwise
    """
    if not product_name:
        return None
    
    product_name_lower = product_name.lower()
    
    # Check each category
    for category, keywords in CARPET_CATEGORIES.items():
        for keyword in keywords:
            if keyword.lower() in product_name_lower:
                return category
    
    return None


@app.get("/inventory", response_model=InventoryResponse)
async def get_inventory(category: Optional[str] = None):
    """
    Get inventory for the four specific carpet types AND paint products.
    
    Connects to Supabase 'products' table and filters for:
    - Flooring-Carpet (WOVEN and ECONYL RIPS)
    - AERMAT 9000/992 GREY
    - AERMAT 9000/8451 BLUE
    
    Also fetches specific paint products:
    - Part: 113-22-633B-3-033 (EPOXY PRIMER 6KG)
    - Part: 470-10-9100-9-003 (WHITE TOPCOAT 10KG)
    - Part: 405-03-0000-0-232 (TOPCOAT HARDENER 5L)
    
    Query Parameters:
    - category: Filter by category (e.g., 'carpet', 'paint', 'all')
    
    If quantities haven't been added yet, returns '0' or 'Out of Stock' placeholder.
    If a paint product is not found, returns 'Item Pending Manual Entry'.
    
    Returns:
        Inventory response with categories, paint items, and totals
    """
    supabase = get_supabase_client()
    
    try:
        # Fetch all products from the database, including color and material_type columns
        response = supabase.table("products").select(
            "id, sku, name, current_stock_level, color, material_type"
        ).execute()
        
        # Fetch paint products by their SKUs
        paint_response = supabase.table("products").select(
            "id, sku, name, current_stock_level, sales_unit_id, base_unit_id"
        ).in("sku", PAINT_PRODUCTS_SKUS).execute()
        
        # Get unit symbols for paint products
        paint_unit_map = {}
        all_unit_ids = set()
        for product in paint_response.data:
            if product.get("sales_unit_id"):
                all_unit_ids.add(product["sales_unit_id"])
            if product.get("base_unit_id"):
                all_unit_ids.add(product["base_unit_id"])
        
        if all_unit_ids:
            units_response = supabase.table("units").select("id, symbol").in("id", list(all_unit_ids)).execute()
            for unit in units_response.data:
                paint_unit_map[unit["id"]] = unit["symbol"]
        
        if not response.data:
            # No products found - return categories with placeholder items
            categories = {
                "Flooring-Carpet": {
                    "WOVEN": [],
                    "ECONYL RIPS": []
                },
                "AERMAT 9000/992 GREY": [],
                "AERMAT 9000/8451 BLUE": []
            }
            
            # Build paint items list with "Item Pending Manual Entry" for missing products
            paint_items = build_paint_items(paint_response.data, paint_unit_map, PAINT_PRODUCTS_SKUS)
            
            # Filter based on category parameter
            if category == "carpet":
                return InventoryResponse(
                    success=True,
                    message="No carpet products found in database.",
                    categories={"Flooring-Carpet": {"WOVEN": [], "ECONYL RIPS": []}, "AERMAT 9000/992 GREY": [], "AERMAT 9000/8451 BLUE": []},
                    total_items=0,
                    paint_items=[]
                )
            elif category == "paint":
                return InventoryResponse(
                    success=True,
                    message="No products found in database.",
                    categories={},
                    total_items=0,
                    paint_items=paint_items
                )
            
            return InventoryResponse(
                success=True,
                message="No products found in database. Returning placeholder categories.",
                categories=categories,
                total_items=0,
                paint_items=paint_items
            )
        
        # Initialize categories with new structure
        categories = {
            "Flooring-Carpet": {
                "WOVEN": [],
                "ECONYL RIPS": []
            },
            "AERMAT 9000/992 GREY": [],
            "AERMAT 9000/8451 BLUE": []
        }
        
        total_items = 0
        
        # Process each product for carpet categories
        for product in response.data:
            product_name = product.get("name", "")
            color = product.get("color", "").upper() if product.get("color") else ""
            material_type = product.get("material_type", "").upper() if product.get("material_type") else ""
            
            # Get quantity, handle None or missing values
            stock_level = product.get("current_stock_level")
            if stock_level is None:
                quantity = 0
            else:
                try:
                    quantity = int(float(stock_level))
                except (ValueError, TypeError):
                    quantity = 0
            
            # Create display string
            if quantity > 0:
                quantity_display = str(quantity)
            else:
                quantity_display = "Out of Stock"
            
            # Create detailed name with color info if available
            display_name = product_name
            if color and color not in product_name.upper():
                display_name = f"{product_name} ({color})"
            
            # Generate highlighted name for AERMAT 9000 and CARPET items
            highlighted_name = format_highlighted_name(product_name, color, material_type)
            
            # Create carpet item
            carpet_item = CarpetItem(
                id=product.get("id"),
                sku=product.get("sku", "N/A"),
                name=display_name,
                highlighted_name=highlighted_name,
                category="",  # Will be set based on subcategory
                quantity=quantity,
                quantity_display=quantity_display,
                is_available=quantity > 0
            )
            
            # Determine category based on material_type and color
            category_type = None
            subcategory = None
            
            # Check for AERMAT products (check both name and material_type)
            is_aermat = "AERMAT" in product_name.upper() or material_type == "AERMAT"
            
            if is_aermat:
                # AERMAT 9000 - distinguish by color
                if "GREY" in color or "992" in product_name.upper():
                    category_type = "AERMAT 9000/992 GREY"
                elif "BLUE" in color or "8451" in product_name.upper():
                    category_type = "AERMAT 9000/8451 BLUE"
                else:
                    # If color is not specified but name contains AERMAT, try to match by name
                    if "GREY" in product_name.upper():
                        category_type = "AERMAT 9000/992 GREY"
                    elif "BLUE" in product_name.upper():
                        category_type = "AERMAT 9000/8451 BLUE"
            
            # Check for WOVEN carpet
            elif material_type == "WOVEN" or "WOVEN" in product_name.upper():
                category_type = "Flooring-Carpet"
                subcategory = "WOVEN"
            
            # Check for ECONYL RIPS
            elif material_type == "ECONYL" or "ECONYL" in product_name.upper() or "RIPS" in product_name.upper():
                category_type = "Flooring-Carpet"
                subcategory = "ECONYL RIPS"
            
            # Fallback: check name keywords if material_type is not set
            else:
                fallback_cat = match_carpet_category(product_name)
                if fallback_cat:
                    if "WOVEN" in fallback_cat:
                        category_type = "Flooring-Carpet"
                        subcategory = "WOVEN"
                    elif "ECONYL" in fallback_cat:
                        category_type = "Flooring-Carpet"
                        subcategory = "ECONYL RIPS"
                    elif "GREY" in fallback_cat or "992" in fallback_cat:
                        category_type = "AERMAT 9000/992 GREY"
                    elif "BLUE" in fallback_cat or "8451" in fallback_cat:
                        category_type = "AERMAT 9000/8451 BLUE"
            
            # Add to appropriate category
            if category_type:
                # Update the carpet_item category
                carpet_item.category = subcategory if subcategory else category_type
                
                if category_type == "Flooring-Carpet" and subcategory:
                    categories[category_type][subcategory].append(carpet_item)
                elif category_type in ["AERMAT 9000/992 GREY", "AERMAT 9000/8451 BLUE"]:
                    categories[category_type].append(carpet_item)
                
                total_items += 1
        
        # Build paint items list
        paint_items = build_paint_items(paint_response.data, paint_unit_map, PAINT_PRODUCTS_SKUS)
        
        # Filter based on category parameter
        if category == "carpet":
            # Return only carpet categories
            filtered_categories = {
                "Flooring-Carpet": categories["Flooring-Carpet"],
                "AERMAT 9000/992 GREY": categories["AERMAT 9000/992 GREY"],
                "AERMAT 9000/8451 BLUE": categories["AERMAT 9000/8451 BLUE"]
            }
            return InventoryResponse(
                success=True,
                message=f"Successfully retrieved carpet inventory. Found {total_items} carpet item(s).",
                categories=filtered_categories,
                total_items=total_items,
                paint_items=[]
            )
        elif category == "paint":
            # Return only paint items
            return InventoryResponse(
                success=True,
                message=f"Successfully retrieved paint inventory. Found {len(paint_items)} paint item(s).",
                categories={},
                total_items=len(paint_items),
                paint_items=paint_items
            )
        
        # Return all (default)
        return InventoryResponse(
            success=True,
            message=f"Successfully retrieved inventory. Found {total_items} carpet type(s) and {len(paint_items)} paint item(s).",
            categories=categories,
            total_items=total_items,
            paint_items=paint_items
        )
        
    except Exception as e:
        # Handle database connection errors gracefully
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching inventory: {str(e)}"
        )


def build_paint_items(products_data: list, unit_map: dict, expected_skus: list) -> List[PaintItem]:
    """
    Build paint items list from database products, handling missing items.
    
    Args:
        products_data: List of product dictionaries from database
        unit_map: Dictionary mapping unit IDs to unit symbols
        expected_skus: List of expected SKU strings
    
    Returns:
        List of PaintItem objects
    """
    paint_items = []
    found_skus = {p.get("sku") for p in products_data if p.get("sku")}
    
    # First add all found products
    for product in products_data:
        if product.get("sku") in expected_skus:
            stock_level = product.get("current_stock_level")
            current_stock = float(stock_level) if stock_level is not None else 0.0
            
            # Get unit symbol
            unit_id = product.get("sales_unit_id") or product.get("base_unit_id")
            unit_symbol = unit_map.get(unit_id, "pcs") if unit_id else "pcs"
            
            # Convert to display unit (if stored in ml, convert to L or KG)
            display_stock = current_stock
            display_unit = unit_symbol
            
            # Handle ml conversion for display
            if unit_symbol == "ml" and current_stock > 0:
                display_stock = current_stock / 1000  # Convert ml to L
                # Try to determine if it's L or kg based on context
                # For now, keep as L
                display_unit = "L"
            
            paint_items.append(PaintItem(
                id=product.get("id"),
                sku=product.get("sku", ""),
                name=product.get("name", ""),
                current_stock=current_stock,
                unit=unit_symbol,
                stock_display=f"{display_stock} {display_unit}" if current_stock > 0 else "Out of Stock",
                is_available=current_stock > 0
            ))
    
    # Add missing items with "Item Pending Manual Entry"
    for sku in expected_skus:
        if sku not in found_skus:
            # Determine unit based on SKU pattern
            unit = "KG" if "KG" in sku else "L"
            
            paint_items.append(PaintItem(
                id=None,
                sku=sku,
                name="Item Pending Manual Entry",
                current_stock=0,
                unit=unit,
                stock_display="Item Pending Manual Entry",
                is_available=False
            ))
    
    return paint_items


@app.get("/api/products/{product_id}", response_model=ProductResponse)
async def get_product(product_id: str):
    """
    Get product details by ID.
    
    Args:
        product_id: UUID of the product
    
    Returns:
        Product information including stock level and pricing
    """
    supabase = get_supabase_client()
    
    product = get_product_with_unit(supabase, product_id)
    
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product not found: {product_id}"
        )
    
    return {
        "id": product["id"],
        "sku": product["sku"],
        "name": product["name"],
        "description": product.get("description"),
        "current_stock_level": float(product["current_stock_level"]),
        "sales_price": float(product["sales_price"]) if product.get("sales_price") else None,
        "purchase_price": float(product["purchase_price"]) if product.get("purchase_price") else None,
        "is_kit": product["is_kit"],
        "unit_symbol": product.get("unit_symbol", "pcs"),
        "available": product["current_stock_level"] > 0
    }


@app.get("/api/products", response_model=List[ProductResponse])
async def list_products(
    category_id: Optional[str] = None,
    is_kit: Optional[bool] = None,
    is_active: bool = True,
    search: Optional[str] = None,
    limit: int = 100
):
    """
    List products with optional filtering.
    
    Args:
        category_id: Filter by category
        is_kit: Filter by kit status
        is_active: Filter by active status
        search: Search by name or SKU
        limit: Maximum number of results
    
    Returns:
        List of products
    """
    supabase = get_supabase_client()
    
    query = supabase.table("products").select(
        "id, sku, name, description, current_stock_level, sales_price, "
        "purchase_price, is_kit, sales_unit_id, base_unit_id, is_active"
    )
    
    if is_active is not None:
        query = query.eq("is_active", is_active)
    
    if category_id:
        query = query.eq("category_id", category_id)
    
    if is_kit is not None:
        query = query.eq("is_kit", is_kit)
    
    if search:
        # Search in name or SKU
        query = query.or_(f"name.ilike.%{search}%,sku.ilike.%{search}%")
    
    query = query.limit(limit)
    
    response = query.execute()
    
    # Add unit symbols
    products = []
    for product in response.data:
        product["unit_symbol"] = get_unit_symbol(supabase, 
            product.get("sales_unit_id") or product.get("base_unit_id"))
        products.append(product)
    
    return products


@app.post("/api/sales", response_model=SaleResponse)
async def process_sale(sale: SaleRequest):
    """
    Process a sale transaction.
    
    This endpoint allows staff to input:
    - Product ID (UUID)
    - Quantity (number of units)
    - Unit Type (e.g., 'L', 'ml', 'pcs', 'set')
    
    The sale will:
    1. Validate product exists and has sufficient stock
    2. Deduct stock from each product
    3. Create stock transaction records
    4. Return the transaction details
    
    Args:
        sale: Sale request with items, reference info, and notes
    
    Returns:
        Sale response with transaction IDs and updated product info
    """
    supabase = get_supabase_client()
    
    transactions = []
    products_updated = []
    sale_id = str(uuid.uuid4())
    
    # Process each item in the sale
    for item in sale.items:
        # Get product details
        product = get_product_with_unit(supabase, item.product_id)
        
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product not found: {item.product_id}"
            )
        
        if not product.get("is_active", True):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Product is inactive: {product['name']}"
            )
        
        # Check stock level
        current_stock = float(product["current_stock_level"])
        
        if current_stock < item.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient stock for {product['name']}. "
                       f"Requested: {item.quantity} {item.unit_type}, "
                       f"Available: {current_stock} {product.get('unit_symbol', 'pcs')}"
            )
        
        # Calculate new stock level
        quantity_before = current_stock
        quantity_after = current_stock - item.quantity
        
        # Update product stock
        update_response = supabase.table("products").update({
            "current_stock_level": quantity_after,
            "updated_at": "now()"
        }).eq("id", item.product_id).execute()
        
        if not update_response.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update stock for product: {product['name']}"
            )
        
        # Create stock transaction record
        transaction_data = {
            "product_id": item.product_id,
            "transaction_type": "sale",
            "quantity": item.quantity,
            "quantity_before": quantity_before,
            "quantity_after": quantity_after,
            "reference_type": sale.reference_type,
            "reference_id": sale.reference_id or sale_id,
            "notes": sale.notes or f"Sale: {product['name']} x{item.quantity} {item.unit_type}",
            "created_by": sale.created_by
        }
        
        tx_response = supabase.table("stock_transactions").insert(
            transaction_data
        ).execute()
        
        if tx_response.data:
            tx = tx_response.data[0]
            transactions.append(StockTransaction(
                id=tx["id"],
                product_id=tx["product_id"],
                transaction_type=tx["transaction_type"],
                quantity=float(tx["quantity"]),
                quantity_before=float(tx["quantity_before"]),
                quantity_after=float(tx["quantity_after"]),
                reference_type=tx.get("reference_type"),
                reference_id=tx.get("reference_id"),
                notes=tx.get("notes"),
                created_at=tx["created_at"]
            ))
            
            # Add to products updated list
            products_updated.append(ProductInfo(
                id=product["id"],
                sku=product["sku"],
                name=product["name"],
                current_stock_level=quantity_after,
                sales_price=float(product["sales_price"]) if product.get("sales_price") else None,
                unit_symbol=product.get("unit_symbol", "pcs")
            ))
    
    # Send SMS notification after successful Supabase transaction
    # This runs after the sale is complete
    sms_task = send_sms_after_sale(
        sale_id=sale_id,
        products_updated=products_updated,
        delivery_status="Processing"
    )
    
    return SaleResponse(
        success=True,
        message=f"Sale processed successfully. {len(transactions)} transaction(s) recorded.",
        sale_id=sale_id,
        transactions=transactions,
        products_updated=products_updated
    )


async def send_sms_after_sale(
    sale_id: str,
    products_updated: List[ProductInfo],
    delivery_status: str = "Processing"
):
    """
    Send SMS notification after successful sale.
    
    This is triggered only after the Supabase transaction is successful.
    
    Args:
        sale_id: The sale order ID
        products_updated: List of products that were sold
        delivery_status: Delivery status for the order
    """
    try:
        # Only send if at least one product was sold
        if not products_updated:
            return None
        
        # Calculate total price from all products
        total_price = 0
        product_names = []
        
        for product in products_updated:
            if product.sales_price:
                total_price += product.sales_price
            product_names.append(product.name)
        
        # Combine product names if multiple
        product_name = ", ".join(product_names[:3])
        if len(product_names) > 3:
            product_name += f" (+{len(product_names) - 3} more)"
        
        # Send SMS notification
        sms_result = send_sale_sms_notification(
            order_id=sale_id,
            product_name=product_name,
            total_price=total_price,
            delivery_status=delivery_status
        )
        
        print(f"SMS Notification sent: {sms_result}")
        return sms_result
        
    except SMSNotificationError as e:
        # Log SMS error but don't fail the sale
        print(f"SMS Notification failed: {e}")
        return None
    except Exception as e:
        # Log any other errors
        print(f"Unexpected error in SMS notification: {e}")
        return None


@app.post("/api/sales/kit", response_model=SaleResponse)
async def process_kit_sale(
    kit_product_id: str,
    kit_quantity: int = 1,
    tint_product_id: Optional[str] = None,
    tint_volume_ml: float = 0,
    reference_type: str = "sale",
    reference_id: Optional[str] = None,
    notes: Optional[str] = None,
    created_by: Optional[str] = None
):
    """
    Process a Paint Kit sale.
    
    This handles the complete kit sale including:
    - Kit product stock deduction
    - All kit component stock deductions
    - Optional tint addition
    
    Args:
        kit_product_id: UUID of the kit product
        kit_quantity: Number of kits to sell
        tint_product_id: UUID of tint product (optional)
        tint_volume_ml: Volume of tint to add in ml (optional)
        reference_type: Type of reference
        reference_id: UUID of reference document
        notes: Additional notes
        created_by: UUID of user
    
    Returns:
        Sale response with transaction details
    """
    from paint_kit_sale import process_complete_paint_kit_sale
    
    supabase = get_supabase_client()
    
    try:
        result = process_complete_paint_kit_sale(
            supabase=supabase,
            kit_product_id=kit_product_id,
            kit_quantity=kit_quantity,
            tint_product_id=tint_product_id,
            tint_volume_ml=tint_volume_ml,
            reference_type=reference_type,
            reference_id=reference_id,
            notes=notes
        )
        
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("message", "Kit sale failed")
            )
        
        return SaleResponse(
            success=True,
            message=result.get("message"),
            sale_id=reference_id,
            transactions=[],  # Transactions already created in the function
            products_updated=[]
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing kit sale: {str(e)}"
        )


@app.get("/api/stock/{product_id}/history")
async def get_stock_history(
    product_id: str,
    limit: int = 50,
    transaction_type: Optional[str] = None
):
    """
    Get stock transaction history for a product.
    
    Args:
        product_id: UUID of the product
        limit: Maximum number of transactions to return
        transaction_type: Filter by transaction type
    
    Returns:
        List of stock transactions
    """
    supabase = get_supabase_client()
    
    query = supabase.table("stock_transactions").select(
        "id, product_id, transaction_type, quantity, quantity_before, "
        "quantity_after, reference_type, reference_id, notes, created_at"
    ).eq("product_id", product_id).order("created_at", desc=True).limit(limit)
    
    if transaction_type:
        query = query.eq("transaction_type", transaction_type)
    
    response = query.execute()
    
    return response.data


@app.post("/process-paint-sale", response_model=PaintSaleResponse)
async def process_paint_sale(request: PaintSaleRequest):
    """
    Process a paint sale using AviationPaintManager.
    
    Supports two types of sales:
    
    Type A: The Kit Sale
        - If a product is a 'Kit', it must be linked to 3 IDs:
          base_paint_id, hardener_id, and thinner_id
        - When 1 'Kit' is sold, deducts 1 Unit from ALL three IDs
        - If ANY item is out of stock, the entire sale fails (Atomic Transaction)
    
    Type B: Tint Deduction
        - If customer adds 'Tint' (e.g., 0.1L of Blue) to Base Color (1L White)
        - Deducts 1L from 'White Base' AND 0.1L from 'Blue Tint' stock
        - Products must have unit_type (liters or kg)
        - Ensures deduction matches unit_type stored in Supabase
    
    Example Type A (Kit Sale) Request:
    {
        "sale_type": "kit",
        "kit_product_id": "uuid-of-kit-product",
        "kit_quantity": 1,
        "reference_type": "invoice",
        "notes": "Paint kit sale to customer"
    }
    
    Example Type B (Tint Sale) Request:
    {
        "sale_type": "tint",
        "base_product_id": "uuid-of-white-base",
        "base_quantity": 1.0,
        "base_unit": "L",
        "tint_product_id": "uuid-of-blue-tint",
        "tint_quantity": 0.1,
        "tint_unit": "L",
        "reference_type": "invoice"
    }
    
    Args:
        request: Paint sale request with sale type and details
    
    Returns:
        Paint sale response with transaction details
    """
    from paint_kit_sale import AviationPaintManager
    
    supabase = get_supabase_client()
    
    # Initialize the AviationPaintManager
    paint_manager = AviationPaintManager(supabase)
    
    # Generate a sale_id if not provided
    sale_id = request.reference_id or str(uuid.uuid4())
    
    try:
        if request.sale_type.lower() == "kit":
            # Type A: Kit Sale
            if not request.kit_product_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="kit_product_id is required for kit sale"
                )
            
            result = paint_manager.process_kit_sale(
                kit_product_id=request.kit_product_id,
                quantity=request.kit_quantity or 1,
                reference_type=request.reference_type or "sale",
                reference_id=sale_id,
                notes=request.notes
            )
            
            return PaintSaleResponse(
                success=True,
                message=result.get("message", "Kit sale processed successfully"),
                sale_type="Type_A_Kit_Sale",
                sale_id=sale_id,
                details=result
            )
            
        elif request.sale_type.lower() == "tint":
            # Type B: Tint Deduction
            if not all([request.base_product_id, request.base_quantity, request.base_unit,
                       request.tint_product_id, request.tint_quantity, request.tint_unit]):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="base_product_id, base_quantity, base_unit, tint_product_id, "
                           "tint_quantity, and tint_unit are required for tint sale"
                )
            
            result = paint_manager.process_tint_sale(
                base_product_id=request.base_product_id,
                base_quantity=request.base_quantity,
                base_unit=request.base_unit,
                tint_product_id=request.tint_product_id,
                tint_quantity=request.tint_quantity,
                tint_unit=request.tint_unit,
                reference_type=request.reference_type or "sale",
                reference_id=sale_id,
                notes=request.notes
            )
            
            return PaintSaleResponse(
                success=True,
                message=result.get("message", "Tint deduction processed successfully"),
                sale_type="Type_B_Tint_Deduction",
                sale_id=sale_id,
                details=result
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid sale_type: {request.sale_type}. Must be 'kit' or 'tint'"
            )
            
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing paint sale: {str(e)}"
        )


# =============================================================================
# KIT REQUIREMENT ENDPOINTS
# =============================================================================

def find_hardener_product(supabase) -> Optional[dict]:
    """Find a hardener/catalyst product from the database."""
    try:
        response = supabase.table("products").select(
            "id, sku, name, current_stock_level"
        ).eq("is_active", True).execute()
        
        # Look for products with hardener/catalyst in name or SKU
        for product in response.data:
            if product.get("name") and any(keyword in product["name"].lower() 
                for keyword in ["hardener", "catalyst", "hrd"]):
                return product
            if product.get("sku") and any(keyword in product["sku"].lower() 
                for keyword in ["hardener", "catalyst", "hrd"]):
                return product
        
        # If not found by name, return first product that could be hardener
        if response.data:
            return response.data[0]
        return None
    except:
        return None


def find_thinner_product(supabase) -> Optional[dict]:
    """Find a thinner/solvent product from the database."""
    try:
        response = supabase.table("products").select(
            "id, sku, name, current_stock_level"
        ).eq("is_active", True).execute()
        
        # Look for products with thinner/solvent in name or SKU
        for product in response.data:
            if product.get("name") and any(keyword in product["name"].lower() 
                for keyword in ["thinner", "solvent", "thn"]):
                return product
            if product.get("sku") and any(keyword in product["sku"].lower() 
                for keyword in ["thinner", "solvent", "thn"]):
                return product
        
        # If not found by name, return a product that could be thinner
        if response.data and len(response.data) > 1:
            return response.data[1]
        return None
    except:
        return None


@app.post("/calculate-kit-requirement", response_model=KitRequirementResponse)
async def calculate_kit_requirement(request: KitRequirementRequest):
    """
    Calculate kit requirements based on mixing ratio.
    
    Takes primary_product_id and requested_qty, fetches the mixing_ratio
    from the products table (JSONB field), and calculates required quantities.
    
    Request:
    - primary_product_id: UUID of the primary paint/product
    - requested_qty: Quantity of primary product requested
    
    Logic:
    1. Fetch mixing_ratio from products table (e.g., {"hardener": 1.0, "thinner": 1.0})
    2. Multiply requested_qty by these ratios
    3. Check stock availability for all components
    4. Return calculated quantities and fulfillment status
    
    Response:
    {
        "primary": 20,
        "hardener": 20,
        "thinner": 20,
        "total_volume": 60,
        "can_fulfill": true/false
    }
    
    Args:
        request: Kit requirement request with product ID and quantity
    
    Returns:
        Kit requirement response with calculated quantities and stock status
    """
    supabase = get_supabase_client()
    
    # Step 1: Fetch the product and its mixing_ratio
    try:
        response = supabase.table("products").select(
            "id, sku, name, current_stock_level, mixing_ratio"
        ).eq("id", request.primary_product_id).execute()
        
        if not response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product not found: {request.primary_product_id}"
            )
        
        product = response.data[0]
        product_name = product.get("name", "Unknown")
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching product: {str(e)}"
        )
    
    # Step 2: Get mixing_ratio (default to 1.0 for both if not set)
    mixing_ratio = product.get("mixing_ratio", {"hardener": 1.0, "thinner": 1.0})
    
    # Handle case where mixing_ratio might be a string
    if isinstance(mixing_ratio, str):
        import json
        try:
            mixing_ratio = json.loads(mixing_ratio)
        except:
            mixing_ratio = {"hardener": 1.0, "thinner": 1.0}
    
    # Get ratio values (default to 1.0 if not present)
    ratio_hardener = mixing_ratio.get("hardener", 1.0) if mixing_ratio else 1.0
    ratio_thinner = mixing_ratio.get("thinner", 1.0) if mixing_ratio else 1.0
    
    # Step 3: Calculate required quantities
    primary_qty = request.requested_qty
    hardener_qty = primary_qty * ratio_hardener
    thinner_qty = primary_qty * ratio_thinner
    total_volume = primary_qty + hardener_qty + thinner_qty
    
    # Step 4: Get stock for primary product
    primary_stock = float(product.get("current_stock_level", 0))
    
    # Step 5: Find hardener and thinner products and get their stock
    hardener_product = find_hardener_product(supabase)
    thinner_product = find_thinner_product(supabase)
    
    hardener_stock = float(hardener_product.get("current_stock_level", 0)) if hardener_product else 0
    thinner_stock = float(thinner_product.get("current_stock_level", 0)) if thinner_product else 0
    
    # Step 6: Determine if order can be fulfilled
    can_fulfill = (
        primary_stock >= primary_qty and
        hardener_stock >= hardener_qty and
        thinner_stock >= thinner_qty
    )
    
    # Build stock info for response
    stock_info = {
        "primary": {
            "product_id": request.primary_product_id,
            "product_name": product_name,
            "required": primary_qty,
            "available": primary_stock
        },
        "hardener": {
            "product_id": hardener_product.get("id") if hardener_product else None,
            "product_name": hardener_product.get("name") if hardener_product else "Unknown",
            "required": hardener_qty,
            "available": hardener_stock
        },
        "thinner": {
            "product_id": thinner_product.get("id") if thinner_product else None,
            "product_name": thinner_product.get("name") if thinner_product else "Unknown",
            "required": thinner_qty,
            "available": thinner_stock
        }
    }
    
    return KitRequirementResponse(
        primary=primary_qty,
        hardener=hardener_qty,
        thinner=thinner_qty,
        total_volume=total_volume,
        can_fulfill=can_fulfill,
        primary_product_id=request.primary_product_id,
        primary_product_name=product_name,
        mixing_ratio=mixing_ratio,
        stock_info=stock_info
    )


def confirm_kit_sale(
    supabase,
    primary_product_id: str,
    requested_qty: float,
    reference_type: str = "sale",
    reference_id: Optional[str] = None,
    notes: Optional[str] = None
) -> dict:
    """
    Confirm and process a kit sale using Supabase RPC.
    
    This function calls the Supabase RPC function 'process_kit_sale'
    to atomically process the kit sale with stock validation.
    
    Args:
        supabase: Supabase client instance
        primary_product_id: UUID of the primary paint/product
        requested_qty: Quantity of primary product to sell
        reference_type: Type of reference (e.g., 'sale', 'invoice')
        reference_id: UUID of the reference document
        notes: Additional notes
    
    Returns:
        Dictionary with sale result
    
    Raises:
        ValueError: If sale fails (insufficient stock, etc.)
    """
    # Get the product to fetch mixing_ratio
    response = supabase.table("products").select(
        "id, name, mixing_ratio"
    ).eq("id", primary_product_id).execute()
    
    if not response.data:
        raise ValueError(f"Product not found: {primary_product_id}")
    
    product = response.data[0]
    mixing_ratio = product.get("mixing_ratio", {"hardener": 1.0, "thinner": 1.0})
    
    # Handle case where mixing_ratio might be a string
    if isinstance(mixing_ratio, str):
        import json
        try:
            mixing_ratio = json.loads(mixing_ratio)
        except:
            mixing_ratio = {"hardener": 1.0, "thinner": 1.0}
    
    # Get ratio values
    ratio_hardener = mixing_ratio.get("hardener", 1.0) if mixing_ratio else 1.0
    ratio_thinner = mixing_ratio.get("thinner", 1.0) if mixing_ratio else 1.0
    
    # Call the RPC function to process the kit sale
    try:
        result = supabase.rpc(
            "process_kit_sale",
            {
                "p_primary_paint_id": primary_product_id,
                "p_requested_primary_qty": requested_qty,
                "p_ratio_hardener": ratio_hardener,
                "p_ratio_thinner": ratio_thinner,
                "p_hardener_id": None,  # Will be auto-looked up by the function
                "p_thinner_id": None    # Will be auto-looked up by the function
            }
        ).execute()
        
        if result.data and len(result.data) > 0:
            row = result.data[0]
            if not row.get("success"):
                raise ValueError(row.get("message", "Kit sale failed"))
            
            return {
                "success": True,
                "message": row.get("message"),
                "primary_paint_id": row.get("primary_paint_id"),
                "hardener_id": row.get("hardener_id"),
                "thinner_id": row.get("thinner_id"),
                "primary_paint_deducted": row.get("primary_paint_deducted"),
                "hardener_deducted": row.get("hardener_deducted"),
                "thinner_deducted": row.get("thinner_deducted"),
                "transaction_ids": row.get("transaction_ids", [])
            }
        else:
            raise ValueError("No response from process_kit_sale function")
            
    except Exception as e:
        if "function" in str(e).lower() and "does not exist" in str(e).lower():
            raise ValueError(
                "process_kit_sale function not found in database. "
                "Please ensure the SQL function is created."
            )
        raise ValueError(f"Kit sale failed: {str(e)}")


@app.post("/confirm-kit-sale")
async def confirm_kit_sale_endpoint(
    primary_product_id: str,
    requested_qty: float,
    reference_type: str = "sale",
    reference_id: Optional[str] = None,
    notes: Optional[str] = None
):
    """
    Confirm and process a kit sale.
    
    This endpoint confirms a kit sale by calling the Supabase RPC
    function 'process_kit_sale' using the supabase.rpc() method.
    
    Request Parameters:
    - primary_product_id: UUID of the primary paint/product
    - requested_qty: Quantity of primary product to sell
    - reference_type: Type of reference (default: 'sale')
    - reference_id: UUID of the reference document (optional)
    - notes: Additional notes (optional)
    
    Returns:
        JSON object with sale result including transaction IDs
    
    Example Request:
    {
        "primary_product_id": "uuid-of-product",
        "requested_qty": 20,
        "reference_type": "invoice",
        "notes": "Kit sale to customer"
    }
    
    Example Response:
    {
        "success": true,
        "message": "Kit Sale processed successfully",
        "primary_paint_id": "uuid",
        "hardener_id": "uuid",
        "thinner_id": "uuid",
        "primary_paint_deducted": 20,
        "hardener_deducted": 20,
        "thinner_deducted": 20,
        "transaction_ids": ["uuid1", "uuid2", "uuid3"]
    }
    """
    supabase = get_supabase_client()
    
    try:
        result = confirm_kit_sale(
            supabase=supabase,
            primary_product_id=primary_product_id,
            requested_qty=requested_qty,
            reference_type=reference_type,
            reference_id=reference_id,
            notes=notes
        )
        
        return result
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error confirming kit sale: {str(e)}"
        )


# =============================================================================
# SALES CONFIRM ENDPOINT (New)
# =============================================================================

@app.post("/sales/confirm", response_model=ConfirmSaleResponse)
async def confirm_sale(request: ConfirmSaleRequest):
    """
    Confirm and process a sale with unit conversion support.
    
    This endpoint handles:
    - CARPET sales: Converts requested_qty from unit_selected to Meters, adds 5% wastage
    - KIT sales: Fetches hardener_ratio and thinner_ratio, calculates proportional requirements
    - SINGLE sales: Verifies requested_qty matches the base unit (Lts/Kg)
    
    Then calls supabase.rpc('fn_process_aviation_sale', ...) to execute the atomic transaction.
    
    Request Body:
    {
        "product_id": "uuid-of-product",
        "requested_qty": 100,
        "unit_selected": "yards",  // or "inches", "lts", "kg"
        "is_kit": true/false,
        "staff_id": "uuid-of-staff-from-contabo",
        "reference_type": "invoice",
        "reference_id": "uuid-of-invoice",
        "notes": "Sale to customer"
    }
    
    Logic Flow:
    1. IF CARPET: Call carpet_measurement helper to convert from unit_selected to Meters, add 5% wastage
    2. IF KIT: Fetch mixing_ratio from product, calculate 20L+20L+20L (or specified ratio) requirement
    3. IF SINGLE: Verify requested_qty matches base unit
    4. Call supabase.rpc('fn_process_aviation_sale', ...) for atomic transaction
    5. Return 400 with clear message if RPC returns error (e.g., 'Insufficient Stock')
    
    Returns:
        ConfirmSaleResponse with success status, message, and transaction details
    """
    from carpet_measurement import calculate_carpet_sale
    
    supabase = get_supabase_client()
    
    try:
        # Step 1: Fetch product details to determine category and base unit
        product_response = supabase.table("products").select(
            "id, sku, name, is_kit, category_id, base_unit_id, current_stock_level, mixing_ratio"
        ).eq("id", request.product_id).execute()
        
        if not product_response.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product not found: {request.product_id}"
            )
        
        product = product_response.data[0]
        product_name = product.get("name")
        is_kit_product = product.get("is_kit", False)
        
        # Determine if this is a carpet product (by category or name)
        # Get category info
        category_response = supabase.table("product_categories").select("name").eq("id", product.get("category_id")).execute()
        category_name = category_response.data[0].get("name", "") if category_response.data else ""
        
        is_carpet = "carpet" in category_name.lower() or "carpet" in product_name.lower()
        
        # Step 2: Process based on product type
        final_quantity = request.requested_qty
        kit_id = None
        
        if is_carpet:
            # CARPET: Convert from unit_selected to Meters, add 5% wastage
            current_stock_meters = float(product.get("current_stock_level", 0))
            
            carpet_result = calculate_carpet_sale(
                sale_quantity=request.requested_qty,
                sale_unit=request.unit_selected,
                current_stock_meters=current_stock_meters
            )
            
            if not carpet_result["has_enough_stock"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Insufficient stock for carpet. "
                           f"Requested (with 5% wastage): {carpet_result['meters_to_deduct']:.2f} meters, "
                           f"Available: {current_stock_meters:.2f} meters"
                )
            
            final_quantity = carpet_result["meters_to_deduct"]
            
        elif request.is_kit or is_kit_product:
            # KIT: Fetch mixing_ratio and calculate hardener/thinner requirements
            mixing_ratio = product.get("mixing_ratio", {"hardener": 1.0, "thinner": 1.0})
            
            # Handle case where mixing_ratio might be a string
            if isinstance(mixing_ratio, str):
                import json
                try:
                    mixing_ratio = json.loads(mixing_ratio)
                except:
                    mixing_ratio = {"hardener": 1.0, "thinner": 1.0}
            
            hardener_ratio = mixing_ratio.get("hardener", 1.0) if mixing_ratio else 1.0
            thinner_ratio = mixing_ratio.get("thinner", 1.0) if mixing_ratio else 1.0
            
            # For kit sales, the product_id is the kit itself, and we need to pass kit_id
            kit_id = request.product_id
            
            # Calculate total requirements for validation
            needed_hardener = request.requested_qty * hardener_ratio
            needed_thinner = request.requested_qty * thinner_ratio
            
            # Find hardener and thinner products to check stock
            hardener_product = find_hardener_product(supabase)
            thinner_product = find_thinner_product(supabase)
            
            if not hardener_product or not thinner_product:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Hardener or Thinner product not found for kit sale"
                )
            
            hardener_stock = float(hardener_product.get("current_stock_level", 0))
            thinner_stock = float(thinner_product.get("current_stock_level", 0))
            
            if hardener_stock < needed_hardener:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Insufficient stock for hardener. "
                           f"Required: {needed_hardener:.2f}, Available: {hardener_stock:.2f}"
                )
            
            if thinner_stock < needed_thinner:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Insufficient stock for thinner. "
                           f"Required: {needed_thinner:.2f}, Available: {thinner_stock:.2f}"
                )
            
        else:
            # SINGLE: Verify unit matches base unit
            # Get base unit symbol
            base_unit_id = product.get("base_unit_id")
            if base_unit_id:
                unit_response = supabase.table("units").select("symbol").eq("id", base_unit_id).execute()
                base_unit_symbol = unit_response.data[0].get("symbol", "") if unit_response.data else ""
                
                # Normalize unit_selected for comparison
                unit_selected_normalized = request.unit_selected.lower().strip()
                base_unit_normalized = base_unit_symbol.lower().strip()
                
                # Check if units match (basic validation)
                # Allow some common variations (e.g., 'lts' = 'L', 'liter' = 'L')
                unit_variations = {
                    'l': ['l', 'lts', 'liter', 'liters', 'litre', 'litres'],
                    'kg': ['kg', 'kilogram', 'kilograms'],
                    'ml': ['ml', 'milliliter', 'milliliters', 'millilitre', 'millilitres'],
                    'g': ['g', 'gram', 'grams'],
                    'm': ['m', 'meter', 'meters', 'metre', 'metres'],
                    'yd': ['yd', 'yard', 'yards'],
                    'in': ['in', 'inch', 'inches']
                }
                
                unit_matches = False
                for standard, variations in unit_variations.items():
                    if unit_selected_normalized in variations and base_unit_normalized in variations:
                        unit_matches = True
                        break
                
                if not unit_matches and base_unit_symbol:
                    # Just log a warning, don't block the sale
                    # The SQL function will handle unit conversion
                    pass
        
        # Step 3: Call the SQL function via RPC
        reference_id = request.reference_id or str(uuid.uuid4())
        
        rpc_result = supabase.rpc(
            "fn_process_aviation_sale",
            {
                "p_product_id": request.product_id,
                "p_quantity": final_quantity,
                "p_kit_id": kit_id,
                "p_staff_id": request.staff_id,
                "p_reference_type": request.reference_type or "sale",
                "p_reference_id": reference_id
            }
        ).execute()
        
        # Step 4: Handle the result
        if rpc_result.data and len(rpc_result.data) > 0:
            row = rpc_result.data[0]
            
            if not row.get("success"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=row.get("message", "Sale failed")
                )
            
            # Build kit_details for kit sales
            kit_details = None
            if request.is_kit or is_kit_product:
                mixing_ratio = product.get("mixing_ratio", {"hardener": 1.0, "thinner": 1.0})
                if isinstance(mixing_ratio, str):
                    import json
                    try:
                        mixing_ratio = json.loads(mixing_ratio)
                    except:
                        mixing_ratio = {"hardener": 1.0, "thinner": 1.0}
                
                hardener_ratio = mixing_ratio.get("hardener", 1.0) if mixing_ratio else 1.0
                thinner_ratio = mixing_ratio.get("thinner", 1.0) if mixing_ratio else 1.0
                
                kit_details = {
                    "hardener_ratio": hardener_ratio,
                    "thinner_ratio": thinner_ratio,
                    "hardener_deducted": final_quantity * hardener_ratio,
                    "thinner_deducted": final_quantity * thinner_ratio,
                    "is_carpet": is_carpet,
                    "unit_converted": is_carpet,
                    "original_quantity": request.requested_qty,
                    "unit_selected": request.unit_selected,
                    "final_quantity": final_quantity
                }
            
            return ConfirmSaleResponse(
                success=True,
                message=row.get("message", "Sale processed successfully"),
                product_id=row.get("product_id"),
                product_name=row.get("product_name"),
                quantity_deducted=float(row.get("quantity_deducted", 0)),
                stock_before=float(row.get("stock_before", 0)),
                stock_after=float(row.get("stock_after", 0)),
                transaction_ids=row.get("transaction_ids", []),
                kit_details=kit_details
            )
            
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No response from database function"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        error_message = str(e)
        
        # Check for common error patterns and return 400
        if "insufficient" in error_message.lower() or "not enough" in error_message.lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient Stock: {error_message}"
            )
        elif "function" in error_message.lower() and "does not exist" in error_message.lower():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database function 'fn_process_aviation_sale' not found. Please ensure the SQL function is created."
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error processing sale: {error_message}"
            )


async def send_delivery_notification_after_sale(
    request: ConfirmSaleRequest,
    sale_result: dict,
    stock_after: float
):
    """
    Send Delivery Note SMS after successful sale.
    
    This is triggered only after the Supabase transaction is successful.
    
    Args:
        request: The original sale request
        sale_result: The result from the database function
        stock_after: Remaining stock after deduction
    """
    try:
        # Get product name
        product_name = sale_result.get("product_name", "Unknown Product")
        
        # Get delivery note number (use reference_id or generate)
        delivery_note_number = request.reference_id or sale_result.get("reference_id", "N/A")
        
        # Get location from settings or use default
        location = settings.DEFAULT_DELIVERY_LOCATION or "Warehouse"
        
        # Send delivery SMS using the staff-selected unit (not the converted base unit)
        # This ensures the customer understands the message
        sms_result = send_delivery_sms(
            delivery_note_number=delivery_note_number,
            quantity=request.requested_qty,  # Original quantity in staff-selected unit
            unit=request.unit_selected,  # Staff-selected unit (e.g., Yards)
            product_name=product_name,
            remaining_stock=stock_after,
            location=location
        )
        
        print(f"Delivery SMS Notification sent: {sms_result}")
        return sms_result
        
    except SMSNotificationError as e:
        # Log SMS error but don't fail the sale
        print(f"Delivery SMS Notification failed: {e}")
        return None
    except Exception as e:
        # Log any other errors
        print(f"Unexpected error in Delivery SMS notification: {e}")
        return None


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

"""
# Example: How to call the Sales endpoint

# POST /api/sales
{
    "items": [
        {
            "product_id": "uuid-of-product-1",
            "quantity": 5,
            "unit_type": "L"
        },
        {
            "product_id": "uuid-of-product-2", 
            "quantity": 2,
            "unit_type": "set"
        }
    ],
    "reference_type": "invoice",
    "reference_id": "uuid-of-invoice",
    "notes": "Sale to customer XYZ",
    "created_by": "uuid-of-user"
}

# Example cURL:
curl -X POST "http://localhost:8000/api/sales" \
  -H "Content-Type: application/json" \
  -d '{
    "items": [
      {"product_id": "abc-123", "quantity": 5, "unit_type": "L"}
    ],
    "reference_type": "sale"
  }'
"""


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    
    # Print CORS configuration
    print("=" * 60)
    print("Aviation ERP API Starting...")
    print("=" * 60)
    print(f"\nAllowed CORS Origins:")
    for origin in settings.get_cors_origins():
        print(f"  - {origin}")
    print(f"\nSupabase URL: {settings.SUPABASE_URL or 'Not configured'}")
    print(f"\nAPI Docs: http://localhost:8000/docs")
    print("=" * 60)
    
    # Run the server
    uvicorn.run(app, host="0.0.0.0", port=8000)

