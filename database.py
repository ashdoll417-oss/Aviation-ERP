"""
Shared Database Module for Aviation ERP
Used by both Render and Contabo deployments.

Provides:
- Pydantic Product model
- Supabase client initialization
- Atomic stock update with race condition prevention
"""

import os
from typing import Optional, List
from pydantic import BaseModel, Field
from supabase import create_client, Client


# =============================================================================
# SUPABASE CLIENT INITIALIZATION
# =============================================================================

def get_supabase_client() -> Client:
    """
    Initialize and return Supabase client using environment variables.
    
    Returns:
        Supabase Client instance
        
    Raises:
        ValueError: If SUPABASE_URL or SUPABASE_KEY is not set
    """
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    
    if not supabase_url:
        raise ValueError("SUPABASE_URL environment variable is not set")
    if not supabase_key:
        raise ValueError("SUPABASE_KEY environment variable is not set")
    
    return create_client(supabase_url, supabase_key)


def get_supabase_service_client() -> Client:
    """
    Initialize and return Supabase service client (with service role key).
    Used for admin operations that bypass RLS.
    
    Returns:
        Supabase Client with service role key
        
    Raises:
        ValueError: If SUPABASE_URL or SUPABASE_SERVICE_KEY is not set
    """
    supabase_url = os.getenv("SUPABASE_URL")
    service_key = os.getenv("SUPABASE_SERVICE_KEY")
    
    if not supabase_url:
        raise ValueError("SUPABASE_URL environment variable is not set")
    if not service_key:
        raise ValueError("SUPABASE_SERVICE_KEY environment variable is not set")
    
    return create_client(supabase_url, service_key)


# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class UnitInfo(BaseModel):
    """Unit information for a product."""
    id: str
    name: str
    symbol: str
    category: str


class Product(BaseModel):
    """
    Product model for Aviation ERP.
    
    Includes all fields needed for inventory management:
    - Basic product info
    - Unit management (purchase_unit, sale_unit)
    - Product type flags (is_kit, is_tint)
    - Stock level
    """
    # Product ID
    id: str = Field(..., description="UUID of the product")
    
    # Basic Product Information
    sku: str = Field(..., description="Stock Keeping Unit")
    name: str = Field(..., description="Product name")
    description: Optional[str] = Field(default=None, description="Product description")
    
    # Unit Management
    purchase_unit_id: Optional[str] = Field(default=None, description="UUID of purchase unit")
    purchase_unit: Optional[str] = Field(default=None, description="Purchase unit symbol (e.g., 'L', 'kg')")
    sale_unit_id: Optional[str] = Field(default=None, description="UUID of sales unit")
    sale_unit: Optional[str] = Field(default=None, description="Sales unit symbol (e.g., 'L', 'kg')")
    base_unit_id: Optional[str] = Field(default=None, description="UUID of base unit")
    base_unit: Optional[str] = Field(default=None, description="Base unit symbol for stock tracking")
    
    # Conversion Rate
    conversion_rate: float = Field(default=1.0, description="Conversion rate from purchase to sales unit")
    
    # Pricing
    purchase_price: Optional[float] = Field(default=None, description="Purchase price")
    sales_price: Optional[float] = Field(default=None, description="Sales price")
    min_stock_level: float = Field(default=0, description="Minimum stock level")
    max_stock_level: Optional[float] = Field(default=None, description="Maximum stock level")
    
    # Product Types
    is_kit: bool = Field(default=False, description="Whether product is a kit")
    is_tint: bool = Field(default=False, description="Whether product is a tint/colorant")
    is_primary_color: bool = Field(default=False, description="Whether product is a primary color (tintable)")
    
    # Stock Tracking
    current_stock_level: float = Field(default=0, description="Current stock level in base unit")
    is_active: bool = Field(default=True, description="Whether product is active")
    is_tracked: bool = Field(default=True, description="Whether to track stock")
    
    # Metadata
    barcode: Optional[str] = Field(default=None, description="Product barcode")
    manufacturer: Optional[str] = Field(default=None, description="Manufacturer name")
    manufacturer_sku: Optional[str] = Field(default=None, description="Manufacturer SKU")
    
    # Timestamps
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")
    
    class Config:
        from_attributes = True


class ProductSummary(BaseModel):
    """Simplified product model for listings."""
    id: str
    sku: str
    name: str
    current_stock_level: float
    sales_price: Optional[float]
    purchase_price: Optional[float]
    is_kit: bool
    is_tint: bool
    is_primary_color: bool
    is_active: bool
    sale_unit: Optional[str]
    base_unit: Optional[str]
    available: bool = Field(..., description="Whether product is in stock")


# =============================================================================
# DATABASE FUNCTIONS
# =============================================================================

# SQL function for atomic stock update with race condition prevention
UPDATE_STOCK_SQL = """
CREATE OR REPLACE FUNCTION update_stock_atomic(
    p_product_id UUID,
    p_amount_to_deduct NUMERIC(18, 6),
    p_reference_type VARCHAR DEFAULT 'sale',
    p_reference_id UUID DEFAULT NULL,
    p_notes TEXT DEFAULT NULL,
    p_created_by UUID DEFAULT NULL
) RETURNS TABLE (
    success BOOLEAN,
    message TEXT,
    quantity_before NUMERIC(18, 6),
    quantity_after NUMERIC(18, 6),
    transaction_id UUID
) AS $$
DECLARE
    v_product RECORD;
    v_quantity_before NUMERIC(18, 6);
    v_quantity_after NUMERIC(18, 6);
    v_transaction_id UUID;
BEGIN
    -- Lock the row for update to prevent race conditions
    SELECT * INTO v_product
    FROM products
    WHERE id = p_product_id
    FOR UPDATE;
    
    IF v_product IS NULL THEN
        RETURN QUERY SELECT FALSE, 'Product not found', NULL, NULL, NULL;
    END IF;
    
    IF NOT v_product.is_tracked THEN
        RETURN QUERY SELECT TRUE, 'Stock tracking disabled for this product', 
            v_product.current_stock_level, v_product.current_stock_level, NULL;
    END IF;
    
    v_quantity_before := v_product.current_stock_level;
    v_quantity_after := v_quantity_before - p_amount_to_deduct;
    
    -- Check for sufficient stock
    IF v_quantity_after < 0 THEN
        RETURN QUERY SELECT FALSE, 
            format('Insufficient stock. Current: %s, Requested: %s', 
                v_quantity_before, p_amount_to_deduct),
            v_quantity_before, NULL, NULL;
    END IF;
    
    -- Update the stock level
    UPDATE products
    SET current_stock_level = v_quantity_after,
        updated_at = NOW()
    WHERE id = p_product_id;
    
    -- Create stock transaction record
    INSERT INTO stock_transactions (
        product_id,
        transaction_type,
        quantity,
        quantity_before,
        quantity_after,
        reference_type,
        reference_id,
        notes,
        created_by
    ) VALUES (
        p_product_id,
        'sale',
        p_amount_to_deduct,
        v_quantity_before,
        v_quantity_after,
        p_reference_type,
        p_reference_id,
        p_notes,
        p_created_by
    ) RETURNING id INTO v_transaction_id;
    
    RETURN QUERY SELECT TRUE, 'Stock updated successfully',
        v_quantity_before, v_quantity_after, v_transaction_id;
END;
$$ LANGUAGE plpgsql;
"""

# SQL function for atomic stock increase (e.g., for purchases/returns)
UPDATE_STOCK_INCREASE_SQL = """
CREATE OR REPLACE FUNCTION update_stock_atomic_increase(
    p_product_id UUID,
    p_amount_to_add NUMERIC(18, 6),
    p_reference_type VARCHAR DEFAULT 'purchase',
    p_reference_id UUID DEFAULT NULL,
    p_notes TEXT DEFAULT NULL,
    p_created_by UUID DEFAULT NULL
) RETURNS TABLE (
    success BOOLEAN,
    message TEXT,
    quantity_before NUMERIC(18, 6),
    quantity_after NUMERIC(18, 6),
    transaction_id UUID
) AS $$
DECLARE
    v_product RECORD;
    v_quantity_before NUMERIC(18, 6);
    v_quantity_after NUMERIC(18, 6);
    v_transaction_id UUID;
BEGIN
    -- Lock the row for update to prevent race conditions
    SELECT * INTO v_product
    FROM products
    WHERE id = p_product_id
    FOR UPDATE;
    
    IF v_product IS NULL THEN
        RETURN QUERY SELECT FALSE, 'Product not found', NULL, NULL, NULL;
    END IF;
    
    IF NOT v_product.is_tracked THEN
        RETURN QUERY SELECT TRUE, 'Stock tracking disabled for this product', 
            v_product.current_stock_level, v_product.current_stock_level, NULL;
    END IF;
    
    v_quantity_before := v_product.current_stock_level;
    v_quantity_after := v_quantity_before + p_amount_to_add;
    
    -- Check max stock level if set
    IF v_product.max_stock_level IS NOT NULL AND v_quantity_after > v_product.max_stock_level THEN
        RETURN QUERY SELECT FALSE, 
            format('Would exceed max stock level. Current: %s, Max: %s, Requested add: %s', 
                v_quantity_before, v_product.max_stock_level, p_amount_to_add),
            v_quantity_before, NULL, NULL;
    END IF;
    
    -- Update the stock level
    UPDATE products
    SET current_stock_level = v_quantity_after,
        updated_at = NOW()
    WHERE id = p_product_id;
    
    -- Create stock transaction record
    INSERT INTO stock_transactions (
        product_id,
        transaction_type,
        quantity,
        quantity_before,
        quantity_after,
        reference_type,
        reference_id,
        notes,
        created_by
    ) VALUES (
        p_product_id,
        p_reference_type,
        p_amount_to_add,
        v_quantity_before,
        v_quantity_after,
        p_reference_type,
        p_reference_id,
        p_notes,
        p_created_by
    ) RETURNING id INTO v_transaction_id;
    
    RETURN QUERY SELECT TRUE, 'Stock updated successfully',
        v_quantity_before, v_quantity_after, v_transaction_id;
END;
$$ LANGUAGE plpgsql;
"""


def setup_database_functions(supabase: Client) -> bool:
    """
    Set up the required SQL functions in Supabase.
    
    Args:
        supabase: Supabase client
        
    Returns:
        True if successful
    """
    try:
        supabase.rpc("exec_sql", {"query": UPDATE_STOCK_SQL}).execute()
        supabase.rpc("exec_sql", {"query": UPDATE_STOCK_INCREASE_SQL}).execute()
        return True
    except Exception as e:
        print(f"Note: SQL functions may need to be created manually: {e}")
        return False


def update_stock(
    supabase: Client,
    product_id: str,
    amount_to_deduct: float,
    reference_type: str = "sale",
    reference_id: Optional[str] = None,
    notes: Optional[str] = None,
    created_by: Optional[str] = None
) -> dict:
    """
    Atomically update stock level to prevent race conditions.
    
    Uses PostgreSQL's FOR UPDATE row locking to prevent two concurrent
    sales from both succeeding when there's only 1 item left.
    
    Args:
        supabase: Supabase client
        product_id: UUID of the product
        amount_to_deduct: Amount to deduct (must be positive)
        reference_type: Type of reference (e.g., 'sale', 'adjustment')
        reference_id: UUID of the reference document
        notes: Additional notes
        created_by: UUID of the user
        
    Returns:
        Dictionary with success status and transaction details
        
    Raises:
        ValueError: If update fails (e.g., insufficient stock)
    """
    # Try RPC call first
    try:
        result = supabase.rpc(
            "update_stock_atomic",
            {
                "p_product_id": product_id,
                "p_amount_to_deduct": amount_to_deduct,
                "p_reference_type": reference_type,
                "p_reference_id": reference_id,
                "p_notes": notes,
                "p_created_by": created_by
            }
        ).execute()
        
        if result.data and len(result.data) > 0:
            row = result.data[0]
            if not row.get("success"):
                raise ValueError(row.get("message", "Stock update failed"))
            return {
                "success": True,
                "message": row.get("message"),
                "quantity_before": float(row.get("quantity_before", 0)),
                "quantity_after": float(row.get("quantity_after", 0)),
                "transaction_id": row.get("transaction_id")
            }
    except Exception as e:
        if "function" in str(e).lower() and "does not exist" in str(e).lower():
            # Fall back to Python-level transaction
            return _update_stock_python(
                supabase, product_id, amount_to_deduct,
                reference_type, reference_id, notes, created_by
            )
        raise ValueError(f"Stock update failed: {str(e)}")
    
    # Fallback
    return _update_stock_python(
        supabase, product_id, amount_to_deduct,
        reference_type, reference_id, notes, created_by
    )


def _update_stock_python(
    supabase: Client,
    product_id: str,
    amount_to_deduct: float,
    reference_type: str,
    reference_id: Optional[str],
    notes: Optional[str],
    created_by: Optional[str]
) -> dict:
    """
    Python-level stock update (fallback when RPC not available).
    
    Note: This does NOT provide true atomicity. Use the SQL function
    when possible for production systems.
    """
    # Get current stock
    response = supabase.table("products").select(
        "id, name, current_stock_level, is_tracked"
    ).eq("id", product_id).execute()
    
    if not response.data:
        raise ValueError(f"Product not found: {product_id}")
    
    product = response.data[0]
    
    if not product.get("is_tracked", True):
        return {
            "success": True,
            "message": "Stock tracking disabled for this product",
            "quantity_before": float(product["current_stock_level"]),
            "quantity_after": float(product["current_stock_level"]),
            "transaction_id": None
        }
    
    quantity_before = float(product["current_stock_level"])
    quantity_after = quantity_before - amount_to_deduct
    
    if quantity_after < 0:
        raise ValueError(
            f"Insufficient stock. Current: {quantity_before}, "
            f"Requested: {amount_to_deduct}"
        )
    
    # Update stock
    supabase.table("products").update({
        "current_stock_level": quantity_after,
        "updated_at": "now()"
    }).eq("id", product_id).execute()
    
    # Create transaction record
    tx_response = supabase.table("stock_transactions").insert({
        "product_id": product_id,
        "transaction_type": reference_type,
        "quantity": amount_to_deduct,
        "quantity_before": quantity_before,
        "quantity_after": quantity_after,
        "reference_type": reference_type,
        "reference_id": reference_id,
        "notes": notes,
        "created_by": created_by
    }).execute()
    
    return {
        "success": True,
        "message": "Stock updated successfully",
        "quantity_before": quantity_before,
        "quantity_after": quantity_after,
        "transaction_id": tx_response.data[0]["id"] if tx_response.data else None
    }


def get_product(supabase: Client, product_id: str) -> Optional[Product]:
    """
    Get a product by ID.
    
    Args:
        supabase: Supabase client
        product_id: UUID of the product
        
    Returns:
        Product object or None if not found
    """
    response = supabase.table("products").select(
        """
        id, sku, name, description,
        purchase_unit_id, sale_unit_id, base_unit_id,
        conversion_rate,
        purchase_price, sales_price,
        min_stock_level, max_stock_level,
        is_kit, is_tint, is_primary_color,
        current_stock_level,
        is_active, is_tracked,
        barcode, manufacturer, manufacturer_sku,
        created_at, updated_at
        """
    ).eq("id", product_id).execute()
    
    if not response.data:
        return None
    
    data = response.data[0]
    
    # Get unit symbols
    unit_ids = {
        data.get("purchase_unit_id"),
        data.get("sale_unit_id"),
        data.get("base_unit_id")
    }
    
    unit_symbols = {}
    for unit_id in unit_ids:
        if unit_id:
            try:
                unit_resp = supabase.table("units").select("symbol").eq("id", unit_id).execute()
                if unit_resp.data:
                    unit_symbols[unit_id] = unit_resp.data[0]["symbol"]
            except:
                pass
    
    return Product(
        id=data["id"],
        sku=data["sku"],
        name=data["name"],
        description=data.get("description"),
        purchase_unit_id=data.get("purchase_unit_id"),
        purchase_unit=unit_symbols.get(data.get("purchase_unit_id")),
        sale_unit_id=data.get("sale_unit_id"),
        sale_unit=unit_symbols.get(data.get("sale_unit_id")),
        base_unit_id=data.get("base_unit_id"),
        base_unit=unit_symbols.get(data.get("base_unit_id")),
        conversion_rate=float(data.get("conversion_rate", 1)),
        purchase_price=float(data["purchase_price"]) if data.get("purchase_price") else None,
        sales_price=float(data["sales_price"]) if data.get("sales_price") else None,
        min_stock_level=float(data.get("min_stock_level", 0)),
        max_stock_level=float(data["max_stock_level"]) if data.get("max_stock_level") else None,
        is_kit=data.get("is_kit", False),
        is_tint=data.get("is_tint", False),
        is_primary_color=data.get("is_primary_color", False),
        current_stock_level=float(data.get("current_stock_level", 0)),
        is_active=data.get("is_active", True),
        is_tracked=data.get("is_tracked", True),
        barcode=data.get("barcode"),
        manufacturer=data.get("manufacturer"),
        manufacturer_sku=data.get("manufacturer_sku"),
        created_at=data.get("created_at", ""),
        updated_at=data.get("updated_at", "")
    )


def get_products(
    supabase: Client,
    is_kit: Optional[bool] = None,
    is_tint: Optional[bool] = None,
    is_active: bool = True,
    search: Optional[str] = None,
    limit: int = 100
) -> List[ProductSummary]:
    """
    Get list of products with optional filtering.
    
    Args:
        supabase: Supabase client
        is_kit: Filter by kit status
        is_tint: Filter by tint status
        is_active: Filter by active status
        search: Search by name or SKU
        limit: Maximum number of results
        
    Returns:
        List of ProductSummary objects
    """
    query = supabase.table("products").select(
        """
        id, sku, name,
        sales_price, purchase_price,
        is_kit, is_tint, is_primary_color,
        is_active, is_tracked,
        current_stock_level,
        sale_unit_id, base_unit_id
        """
    )
    
    if is_active is not None:
        query = query.eq("is_active", is_active)
    
    if is_kit is not None:
        query = query.eq("is_kit", is_kit)
    
    if is_tint is not None:
        query = query.eq("is_tint", is_tint)
    
    if search:
        query = query.or_(f"name.ilike.%{search}%,sku.ilike.%{search}%")
    
    query = query.limit(limit)
    response = query.execute()
    
    # Get unit symbols
    products = []
    for data in response.data:
        # Get unit symbol
        unit_id = data.get("sale_unit_id") or data.get("base_unit_id")
        unit_symbol = "pcs"
        if unit_id:
            try:
                unit_resp = supabase.table("units").select("symbol").eq("id", unit_id).execute()
                if unit_resp.data:
                    unit_symbol = unit_resp.data[0]["symbol"]
            except:
                pass
        
        base_unit_id = data.get("base_unit_id")
        base_unit_symbol = unit_symbol
        if base_unit_id and base_unit_id != unit_id:
            try:
                unit_resp = supabase.table("units").select("symbol").eq("id", base_unit_id).execute()
                if unit_resp.data:
                    base_unit_symbol = unit_resp.data[0]["symbol"]
            except:
                pass
        
        products.append(ProductSummary(
            id=data["id"],
            sku=data["sku"],
            name=data["name"],
            current_stock_level=float(data.get("current_stock_level", 0)),
            sales_price=float(data["sales_price"]) if data.get("sales_price") else None,
            purchase_price=float(data["purchase_price"]) if data.get("purchase_price") else None,
            is_kit=data.get("is_kit", False),
            is_tint=data.get("is_tint", False),
            is_primary_color=data.get("is_primary_color", False),
            is_active=data.get("is_active", True),
            sale_unit=unit_symbol,
            base_unit=base_unit_symbol,
            available=data.get("current_stock_level", 0) > 0
        ))
    
    return products


# =============================================================================
# EXAMPLE USAGE
# =============================================================================

if __name__ == "__main__":
    # Example usage
    print("=" * 60)
    print("Database Module - Example Usage")
    print("=" * 60)
    
    # This would work in production with proper environment variables
    # supabase = get_supabase_client()
    
    print("\n1. Get Supabase Client:")
    print("   supabase = get_supabase_client()")
    print("   # Uses SUPABASE_URL and SUPABASE_KEY env vars")
    
    print("\n2. Get Product:")
    print("   product = get_product(supabase, 'product-uuid')")
    print("   # Returns Product pydantic model")
    
    print("\n3. Update Stock (Atomic):")
    print("   result = update_stock(")
    print("       supabase,")
    print("       product_id='uuid',")
    print("       amount_to_deduct=1.0")
    print("   )")
    print("   # Uses FOR UPDATE to prevent race conditions")
    
    print("\n4. Get Products:")
    print("   products = get_products(supabase, is_kit=True)")
    print("   # Returns list of ProductSummary")

