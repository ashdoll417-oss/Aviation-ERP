"""
FastAPI Main Application for Aviation ERP
Connects to Supabase inventory table

Home Route: Returns time-based greeting
Inventory Route: Fetches items from inventory table with filters
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List
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
# PYDANTIC MODELS
# =============================================================================

class InventoryItem(BaseModel):
    """Individual inventory item."""
    id: int
    part_number: str
    description: str
    category: str
    material_type: Optional[str] = None
    color: Optional[str] = None
    current_stock: float
    unit: str
    stock_display: str = Field(..., description="Stock with unit (e.g., '180 KG')")
    is_available: bool = Field(..., description="Whether item is in stock")


class InventoryResponse(BaseModel):
    """Response model for inventory endpoint."""
    success: bool
    message: str
    items: List[InventoryItem]
    total_count: int


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def build_inventory_items(rows: list) -> List[InventoryItem]:
    """
    Build inventory items from database rows with stock_display.
    
    Args:
        rows: List of inventory rows from Supabase
        
    Returns:
        List of InventoryItem objects
    """
    items = []
    for row in rows:
        current_stock = float(row.get("current_stock", 0)) if row.get("current_stock") else 0
        unit = row.get("unit", "")
        
        # Create stock_display with unit (e.g., "180 KG", "10 L")
        stock_display = f"{current_stock} {unit}" if current_stock > 0 else "Out of Stock"
        
        items.append(InventoryItem(
            id=row.get("id"),
            part_number=row.get("part_number", ""),
            description=row.get("description", ""),
            category=row.get("category", ""),
            material_type=row.get("material_type"),
            color=row.get("color"),
            current_stock=current_stock,
            unit=unit,
            stock_display=stock_display,
            is_available=current_stock > 0
        ))
    
    return items


# =============================================================================
# API ENDPOINTS
# =============================================================================

@app.get("/", response_model=dict)
async def root():
    """
    Root endpoint - returns time-based greeting.
    
    Before 12 PM: 'Good Morning, AISL Aviation Team'
    12 PM - 6 PM: 'Good Afternoon'
    After 6 PM: 'Good Evening'
    """
    now = datetime.now()
    current_hour = now.hour
    
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
        "docs": "/docs"
    }


@app.get("/inventory", response_model=InventoryResponse)
async def get_inventory(
    type: Optional[str] = Query(
        None, 
        description="Filter by type: 'carpet' or 'paint'"
    )
):
    """
    Get inventory items from the inventory table.
    
    Query Parameters:
    - type: Filter by 'carpet' or 'paint'
    
    Returns:
        Inventory items with stock_display showing unit (KG/L/M)
    
    Examples:
    - /inventory - All items
    - /inventory?type=carpet - Only Woven, Econyl, Aermat items
    - /inventory?type=paint - Only Primers and Hardeners
    """
    supabase = get_supabase_client()
    
    try:
        # Fetch all items from inventory table
        response = supabase.table("inventory").select("*").execute()
        
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
            # Filter for carpet items: Woven, Econyl, Aermat
            filtered_items = [
                item for item in response.data 
                if item.get("category", "").lower() == "carpet"
            ]
            message = f"Showing carpet items. Found {len(filtered_items)} item(s)."
            
        elif type and type.lower() == "paint":
            # Filter for paint items: Primers, Hardeners
            filtered_items = [
                item for item in response.data 
                if item.get("category", "").lower() == "paint"
            ]
            message = f"Showing paint items. Found {len(filtered_items)} item(s)."
            
        else:
            message = f"Showing all inventory items. Found {len(filtered_items)} item(s)."
        
        # Build inventory items with stock_display
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

