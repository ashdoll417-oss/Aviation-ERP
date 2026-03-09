"""
Pydantic v2 Models for Aviation ERP
Provides data validation and serialization for product management.

Includes:
- Base Product Model with UUID, name, SKU, category
- Unit Conversion Fields (purchase_unit, sale_unit, conversion_factor)
- Kit Logic Fields (is_kit, hardener_ratio, thinner_id)
- Carpet Specifics (roll_width_inches)
- Validation for kit requirements
"""

import uuid
from enum import Enum
from typing import Optional, Any, Dict, List
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict


# =============================================================================
# ENUMS
# =============================================================================

class ProductCategory(str, Enum):
    """Product category enum for Aviation ERP."""
    PAINT = "Paint"
    CARPET = "Carpet"
    STRIPPER = "Stripper"


class UnitType(str, Enum):
    """
    Unit type enum for Aviation ERP products.
    Supports common measurement units for aviation materials.
    
    Length units: m (meters), yd (yards), in (inches), ft (feet), cm, mm
    Volume units: lts (liters), ml (milliliters), gal (gallons)
    Weight units: kg (kilograms), g (grams), lb (pounds), oz (ounces)
    Quantity units: pcs (pieces), set (sets), box (boxes)
    """
    # Length units
    METERS = "m"
    YARDS = "yd"
    INCHES = "in"
    FEET = "ft"
    CENTIMETERS = "cm"
    MILLIMETERS = "mm"
    
    # Volume units
    LITERS = "lts"
    MILLILITERS = "ml"
    GALLONS = "gal"
    
    # Weight units
    KILOGRAMS = "kg"
    GRAMS = "g"
    POUNDS = "lb"
    OUNCES = "oz"
    
    # Quantity units
    PIECES = "pcs"
    SETS = "set"
    BOXES = "box"
    
    @classmethod
    def get_length_units(cls) -> List[str]:
        """Get list of length unit values."""
        return [cls.METERS.value, cls.YARDS.value, cls.INCHES.value, cls.FEET.value, cls.CENTIMETERS.value, cls.MILLIMETERS.value]
    
    @classmethod
    def get_volume_units(cls) -> List[str]:
        """Get list of volume unit values."""
        return [cls.LITERS.value, cls.MILLILITERS.value, cls.GALLONS.value]
    
    @classmethod
    def get_weight_units(cls) -> List[str]:
        """Get list of weight unit values."""
        return [cls.KILOGRAMS.value, cls.GRAMS.value, cls.POUNDS.value, cls.OUNCES.value]
    
    @classmethod
    def get_all_units(cls) -> List[str]:
        """Get all unit values."""
        return [member.value for member in cls]


# =============================================================================
# BASE MODELS
# =============================================================================

class ProductBase(BaseModel):
    """
    Base Product Model for Aviation ERP.
    
    Contains the core fields required for all products:
    - id: Unique UUID identifier
    - name: Product name
    - sku: Stock Keeping Unit
    - category: Product category (Paint/Carpet/Stripper)
    - current_stock: Current stock level (float for precision)
    """
    model_config = ConfigDict(
        str_strip_whitespace=True,
        use_enum_values=False,  # Keep enum objects for serialization
        json_schema_extra={
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "White Epoxy Primer",
                "sku": "PRI-WH-001",
                "category": "Paint",
                "current_stock": 100.0
            }
        }
    )
    
    # Product ID (UUID)
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        description="Unique UUID identifier for the product"
    )
    
    # Product Name
    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Product name"
    )
    
    # Stock Keeping Unit
    sku: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Stock Keeping Unit - unique identifier for inventory"
    )
    
    # Product Category
    category: ProductCategory = Field(
        default=ProductCategory.PAINT,
        description="Product category: Paint, Carpet, or Stripper"
    )
    
    # Current Stock Level (float for precision with decimals)
    current_stock: float = Field(
        default=0.0,
        ge=0.0,
        description="Current stock level (float for precision)"
    )
    
    # Product Location (e.g., warehouse, shelf, bin)
    location: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Product storage location (e.g., Warehouse A, Shelf B3)"
    )


# =============================================================================
# UNIT CONVERSION MIXIN
# =============================================================================

class UnitConversionMixin(BaseModel):
    """
    Mixin for unit conversion fields.
    
    Fields:
    - purchase_unit: Unit for purchasing (e.g., 'm', 'yd', 'in', 'lts', 'kg')
    - sale_unit: Unit for selling (e.g., 'm', 'yd', 'in', 'lts', 'kg')
    - conversion_factor: Factor to convert between purchase and sale units
    """
    model_config = ConfigDict(
        use_enum_values=False
    )
    
    # Purchase Unit
    purchase_unit: Optional[UnitType] = Field(
        default=None,
        description="Unit for purchasing (e.g., 'm', 'yd', 'in', 'lts', 'kg')"
    )
    
    # Sale Unit
    sale_unit: Optional[UnitType] = Field(
        default=None,
        description="Unit for selling (e.g., 'm', 'yd', 'in', 'lts', 'kg')"
    )
    
    # Conversion Factor
    conversion_factor: float = Field(
        default=1.0,
        gt=0.0,
        description="Conversion factor between purchase and sale units"
    )
    
    @field_validator('conversion_factor')
    @classmethod
    def validate_conversion_factor(cls, v: float) -> float:
        """Validate that conversion factor is positive."""
        if v <= 0:
            raise ValueError("conversion_factor must be greater than 0")
        return v


# =============================================================================
# KIT LOGIC MIXIN
# =============================================================================

class KitLogicMixin(BaseModel):
    """
    Mixin for kit logic fields.
    
    Fields:
    - is_kit: Boolean flag indicating if product is a kit
    - hardener_ratio: Ratio of hardener to primary product (required if is_kit=True)
    - thinner_id: UUID of the thinner product associated with this kit
    """
    model_config = ConfigDict(
        use_enum_values=False
    )
    
    # Kit Flag
    is_kit: bool = Field(
        default=False,
        description="Boolean flag indicating if product is a kit"
    )
    
    # Hardener Ratio
    hardener_ratio: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Ratio of hardener to primary product (e.g., 1.0 means 1:1 ratio)"
    )
    
    # Thinner ID (UUID)
    thinner_id: Optional[uuid.UUID] = Field(
        default=None,
        description="UUID of the thinner product associated with this kit"
    )
    
    @model_validator(mode='after')
    def validate_kit_requirements(self) -> 'KitLogicMixin':
        """
        Validate that if is_kit is True, hardener_ratio must be greater than 0.
        
        This validator ensures that kit products have proper mixing ratios defined.
        """
        if self.is_kit:
            if self.hardener_ratio is None or self.hardener_ratio <= 0:
                raise ValueError(
                    "hardener_ratio must be greater than 0 when is_kit is True. "
                    f"Got: {self.hardener_ratio}"
                )
        return self


# =============================================================================
# CARPET SPECIFICS MIXIN
# =============================================================================

class CarpetSpecificsMixin(BaseModel):
    """
    Mixin for carpet-specific fields.
    
    Fields:
    - roll_width_inches: Roll width in inches for aviation carpet calculations
    """
    
    # Roll Width in Inches (for aviation carpet calculations)
    roll_width_inches: Optional[float] = Field(
        default=None,
        gt=0.0,
        le=120.0,  # Maximum reasonable roll width for aviation carpet
        description="Roll width in inches for aviation carpet calculations"
    )


# =============================================================================
# COMPLETE PRODUCT MODEL
# =============================================================================

class Product(ProductBase, UnitConversionMixin, KitLogicMixin, CarpetSpecificsMixin):
    """
    Complete Product Model for Aviation ERP.
    
    Combines all mixins and adds additional common fields:
    - Description
    - Pricing (purchase_price, sales_price)
    - Stock management (min_stock_level, max_stock_level)
    - Status flags (is_active, is_tracked)
    - Metadata (barcode, manufacturer)
    
    The model includes:
    1. Base fields: id, name, sku, category, current_stock
    2. Unit conversion: purchase_unit, sale_unit, conversion_factor
    3. Kit logic: is_kit, hardener_ratio, thinner_id
    4. Carpet specifics: roll_width_inches
    
    Validation:
    - If is_kit is True, hardener_ratio must be > 0
    """
    model_config = ConfigDict(
        str_strip_whitespace=True,
        use_enum_values=False,
        json_schema_extra={
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "White Topcoat Kit - Complete",
                "sku": "KIT-TOPCOAT-WH",
                "category": "Paint",
                "current_stock": 50.0,
                "purchase_unit": "lts",
                "sale_unit": "set",
                "conversion_factor": 1.0,
                "is_kit": True,
                "hardener_ratio": 0.5,
                "thinner_id": "223e4567-e89b-12d3-a456-426614174001",
                "roll_width_inches": None,
                "description": "Complete kit: 1L Topcoat + 500ml Hardener + 500ml Thinner",
                "purchase_price": 45.00,
                "sales_price": 75.00,
                "min_stock_level": 10.0,
                "is_active": True,
                "is_tracked": True
            }
        }
    )
    
    # Optional: Description
    description: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Product description"
    )
    
    # Pricing
    purchase_price: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Purchase price per unit"
    )
    
    sales_price: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Sales price per unit"
    )
    
    # Stock Management
    min_stock_level: float = Field(
        default=0.0,
        ge=0.0,
        description="Minimum stock level for alerts"
    )
    
    max_stock_level: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Maximum stock level"
    )
    
    # Status Flags
    is_active: bool = Field(
        default=True,
        description="Whether the product is active"
    )
    
    is_tracked: bool = Field(
        default=True,
        description="Whether to track stock for this product"
    )
    
    # Metadata
    barcode: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Product barcode"
    )
    
    manufacturer: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Manufacturer name"
    )
    
    manufacturer_sku: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Manufacturer SKU"
    )


# =============================================================================
# SIMPLIFIED MODELS FOR LISTINGS
# =============================================================================

class ProductSummary(BaseModel):
    """
    Simplified product model for listings.
    
    Used for list views and search results where full product details
    are not needed.
    """
    model_config = ConfigDict(
        use_enum_values=False
    )
    
    id: uuid.UUID
    sku: str
    name: str
    category: ProductCategory
    current_stock: float
    is_kit: bool
    is_active: bool
    sales_price: Optional[float] = None
    location: Optional[str] = None
    
    @property
    def available(self) -> bool:
        """Check if product is available (has stock)."""
        return self.current_stock > 0


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class ProductCreate(BaseModel):
    """
    Model for creating a new product.
    
    All required fields for product creation.
    """
    name: str = Field(..., min_length=1, max_length=255)
    sku: str = Field(..., min_length=1, max_length=50)
    category: ProductCategory = ProductCategory.PAINT
    current_stock: float = Field(default=0.0, ge=0.0)
    
    # Location
    location: Optional[str] = Field(default=None, max_length=255)
    
    # Unit Conversion
    purchase_unit: Optional[UnitType] = None
    sale_unit: Optional[UnitType] = None
    conversion_factor: float = Field(default=1.0, gt=0.0)
    
    # Kit Logic
    is_kit: bool = Field(default=False)
    hardener_ratio: Optional[float] = Field(default=None, ge=0.0)
    thinner_id: Optional[uuid.UUID] = None
    
    # Carpet Specifics
    roll_width_inches: Optional[float] = Field(default=None, gt=0.0, le=120.0)
    
    # Additional Fields
    description: Optional[str] = None
    purchase_price: Optional[float] = Field(default=None, ge=0.0)
    sales_price: Optional[float] = Field(default=None, ge=0.0)
    min_stock_level: float = Field(default=0.0, ge=0.0)
    max_stock_level: Optional[float] = Field(default=None, ge=0.0)
    is_active: bool = Field(default=True)
    is_tracked: bool = Field(default=True)
    barcode: Optional[str] = None
    manufacturer: Optional[str] = None
    manufacturer_sku: Optional[str] = None
    
    @model_validator(mode='after')
    def validate_create(self) -> 'ProductCreate':
        """Validate product creation requirements."""
        if self.is_kit:
            if self.hardener_ratio is None or self.hardener_ratio <= 0:
                raise ValueError(
                    "hardener_ratio must be greater than 0 when is_kit is True"
                )
        return self


class ProductUpdate(BaseModel):
    """
    Model for updating an existing product.
    
    All fields are optional for partial updates.
    """
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    sku: Optional[str] = Field(default=None, min_length=1, max_length=50)
    category: Optional[ProductCategory] = None
    current_stock: Optional[float] = Field(default=None, ge=0.0)
    
    # Location
    location: Optional[str] = Field(default=None, max_length=255)
    
    # Unit Conversion
    purchase_unit: Optional[UnitType] = None
    sale_unit: Optional[UnitType] = None
    conversion_factor: Optional[float] = Field(default=None, gt=0.0)
    
    # Kit Logic
    is_kit: Optional[bool] = None
    hardener_ratio: Optional[float] = Field(default=None, ge=0.0)
    thinner_id: Optional[uuid.UUID] = None
    
    # Carpet Specifics
    roll_width_inches: Optional[float] = Field(default=None, gt=0.0, le=120.0)
    
    # Additional Fields
    description: Optional[str] = None
    purchase_price: Optional[float] = Field(default=None, ge=0.0)
    sales_price: Optional[float] = Field(default=None, ge=0.0)
    min_stock_level: Optional[float] = Field(default=None, ge=0.0)
    max_stock_level: Optional[float] = Field(default=None, ge=0.0)
    is_active: Optional[bool] = None
    is_tracked: Optional[bool] = None
    barcode: Optional[str] = None
    manufacturer: Optional[str] = None
    manufacturer_sku: Optional[str] = None


# =============================================================================
# KIT PRODUCT MODEL
# =============================================================================

class KitProduct(Product):
    """
    Specialized Product model for Kit products.
    
    This model ensures that is_kit is always True and
    hardener_ratio is always set with proper validation.
    """
    
    is_kit: bool = Field(default=True, constant=True)
    hardener_ratio: float = Field(..., gt=0.0)
    thinner_id: uuid.UUID
    
    @model_validator(mode='after')
    def validate_kit(self) -> 'KitProduct':
        """Ensure kit product has required fields."""
        if self.hardener_ratio <= 0:
            raise ValueError("hardener_ratio must be greater than 0 for kit products")
        return self


# =============================================================================
# CARPET PRODUCT MODEL
# =============================================================================

class CarpetProduct(Product):
    """
    Specialized Product model for Carpet products.
    
    This model includes roll_width_inches for aviation
    carpet calculations.
    """
    
    category: ProductCategory = Field(
        default=ProductCategory.CARPET,
        constant=True
    )
    roll_width_inches: float = Field(..., gt=0.0, le=120.0)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def validate_unit_conversion(
    purchase_unit: str,
    sale_unit: str,
    conversion_factor: float
) -> Dict[str, Any]:
    """
    Validate unit conversion parameters.
    
    Args:
        purchase_unit: The unit for purchasing
        sale_unit: The unit for selling
        conversion_factor: The conversion factor between units
    
    Returns:
        Dictionary with validation result
    
    Raises:
        ValueError: If validation fails
    """
    # Check units are valid
    valid_units = UnitType.get_all_units()
    
    if purchase_unit not in valid_units:
        raise ValueError(
            f"Invalid purchase_unit: {purchase_unit}. "
            f"Valid units: {valid_units}"
        )
    
    if sale_unit not in valid_units:
        raise ValueError(
            f"Invalid sale_unit: {sale_unit}. "
            f"Valid units: {valid_units}"
        )
    
    # Check conversion factor
    if conversion_factor <= 0:
        raise ValueError(
            f"conversion_factor must be greater than 0. Got: {conversion_factor}"
        )
    
    return {
        "valid": True,
        "purchase_unit": purchase_unit,
        "sale_unit": sale_unit,
        "conversion_factor": conversion_factor
    }


def convert_quantity(
    quantity: float,
    from_unit: str,
    to_unit: str,
    conversion_factor: float = 1.0
) -> float:
    """
    Convert quantity from one unit to another.
    
    Args:
        quantity: The quantity to convert
        from_unit: Source unit
        to_unit: Target unit
        conversion_factor: Additional conversion factor
    
    Returns:
        Converted quantity
    
    Example:
        >>> convert_quantity(10, 'm', 'yd', 1.0)
        10.9361
    """
    # Basic conversion - can be extended with proper unit conversion tables
    return quantity * conversion_factor


# =============================================================================
# EXAMPLE USAGE AND TESTING
# =============================================================================

if __name__ == "__main__":
    import json
    
    print("=" * 60)
    print("Aviation ERP Models - Example Usage")
    print("=" * 60)
    
    # Example 1: Create a Paint product
    print("\n1. Creating a Paint product:")
    paint_product = Product(
        id=uuid.uuid4(),
        name="White Epoxy Primer",
        sku="PRI-WH-001",
        category=ProductCategory.PAINT,
        current_stock=100.0,
        purchase_unit=UnitType.LITERS,
        sale_unit=UnitType.LITERS,
        conversion_factor=1.0,
        purchase_price=25.00,
        sales_price=45.00,
        is_active=True,
        is_tracked=True
    )
    print(f"   Name: {paint_product.name}")
    print(f"   SKU: {paint_product.sku}")
    print(f"   Category: {paint_product.category}")
    print(f"   Current Stock: {paint_product.current_stock}")
    print(f"   Purchase Unit: {paint_product.purchase_unit}")
    
    # Example 2: Create a Kit product (with validation)
    print("\n2. Creating a Kit product:")
    kit_product = Product(
        id=uuid.uuid4(),
        name="White Topcoat Kit - Complete",
        sku="KIT-TOPCOAT-WH",
        category=ProductCategory.PAINT,
        current_stock=50.0,
        purchase_unit=UnitType.LITERS,
        sale_unit=UnitType.SETS,
        conversion_factor=1.0,
        is_kit=True,
        hardener_ratio=0.5,
        thinner_id=uuid.uuid4(),
        purchase_price=45.00,
        sales_price=75.00,
        is_active=True,
        is_tracked=True
    )
    print(f"   Name: {kit_product.name}")
    print(f"   SKU: {kit_product.sku}")
    print(f"   Is Kit: {kit_product.is_kit}")
    print(f"   Hardener Ratio: {kit_product.hardener_ratio}")
    print(f"   Thinner ID: {kit_product.thinner_id}")
    
    # Example 3: Create a Carpet product with roll width
    print("\n3. Creating a Carpet product:")
    carpet_product = Product(
        id=uuid.uuid4(),
        name="Aviation Carpet - Grey",
        sku="CAR-GRY-001",
        category=ProductCategory.CARPET,
        current_stock=500.0,
        purchase_unit=UnitType.METERS,
        sale_unit=UnitType.YARDS,
        conversion_factor=1.09361,
        roll_width_inches=72.0,
        purchase_price=15.00,
        sales_price=25.00,
        is_active=True,
        is_tracked=True
    )
    print(f"   Name: {carpet_product.name}")
    print(f"   SKU: {carpet_product.sku}")
    print(f"   Category: {carpet_product.category}")
    print(f"   Roll Width (inches): {carpet_product.roll_width_inches}")
    print(f"   Sale Unit: {carpet_product.sale_unit}")
    
    # Example 4: Test validation (should fail for kit without hardener_ratio)
    print("\n4. Testing validation (kit without hardener_ratio):")
    try:
        invalid_kit = Product(
            name="Invalid Kit",
            sku="KIT-INV-001",
            category=ProductCategory.PAINT,
            is_kit=True,
            hardener_ratio=0.0  # Invalid - must be > 0
        )
        print("   ERROR: Should have raised validation error!")
    except ValueError as e:
        print(f"   ✓ Validation Error Caught: {e}")
    
    # Example 5: Test ProductCreate
    print("\n5. Testing ProductCreate:")
    new_product = ProductCreate(
        name="Test Paint Product",
        sku="TEST-PAINT-001",
        category=ProductCategory.PAINT,
        current_stock=100.0,
        purchase_unit=UnitType.LITERS,
        sale_unit=UnitType.LITERS,
        conversion_factor=1.0,
        is_kit=False,
        sales_price=50.00
    )
    print(f"   Created: {new_product.name}")
    print(f"   SKU: {new_product.sku}")
    
    # Example 6: JSON Serialization
    print("\n6. JSON Serialization:")
    json_output = json.dumps(
        paint_product.model_dump(mode='json'),
        indent=2,
        default=str
    )
    print(f"   JSON output (first 200 chars): {json_output[:200]}...")
    
    print("\n" + "=" * 60)
    print("All examples completed successfully!")
    print("=" * 60)

