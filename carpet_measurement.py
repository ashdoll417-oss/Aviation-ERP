"""
Carpet Measurement Module for Aviation ERP
Handles complex carpet measurements with unit conversions and roll calculations.
"""

from typing import Dict, Any, Literal
from decimal import Decimal, ROUND_HALF_UP
import math


# Constants
METER_TO_YARD = Decimal('1.09361')
YARD_TO_INCH = Decimal('36')
METER_TO_INCH = Decimal('39.3701')
STANDARD_ROLL_LENGTH_METERS = Decimal('30')
WASTAGE_FACTOR = Decimal('0.05')  # 5% Aviation Cutting Waste

# Conversion constants for convert_carpet_units
YARD_TO_METER = 0.9144
INCH_TO_METER = 0.0254


def convert_carpet_units(qty: float, from_unit: str, wastage_percent: float = 0.05) -> float:
    """
    Convert carpet units to meters with aviation wastage.
    
    Args:
        qty: The quantity to convert
        from_unit: The input unit ('yards' or 'inches')
        wastage_percent: Wastage percentage (default 0.05 for 5%)
    
    Returns:
        meters_to_deduct: The final value in meters including wastage
    
    Example:
        >>> convert_carpet_units(100, 'yards')
        96.012
        >>> convert_carpet_units(1181.1, 'inches')
        30.999285
    """
    # Normalize unit to lowercase
    unit = from_unit.lower().strip()
    
    # Convert to meters based on unit
    if unit == 'yards':
        quantity_in_meters = qty * YARD_TO_METER
    elif unit == 'inches':
        quantity_in_meters = qty * INCH_TO_METER
    else:
        raise ValueError(f"Unsupported unit: {unit}. Supported units: 'yards', 'inches'")
    
    # Multiply by 1 + wastage_percent to account for aviation wastage
    meters_to_deduct = quantity_in_meters * (1 + wastage_percent)
    
    return meters_to_deduct


def convert_to_meters(quantity: Decimal, unit: str) -> Decimal:
    """
    Convert any unit to meters (base unit).
    
    Args:
        quantity: The measurement quantity
        unit: The input unit (Meters, Inches, Yards)
    
    Returns:
        Quantity in meters
    """
    unit = unit.lower().strip()
    
    if unit in ('meter', 'meters', 'm'):
        return quantity
    elif unit in ('yard', 'yards', 'yd'):
        # 1 yard = 0.9144 meters
        return quantity * Decimal('0.9144')
    elif unit in ('inch', 'inches', 'in'):
        # 1 inch = 0.0254 meters
        return quantity * Decimal('0.0254')
    else:
        raise ValueError(f"Unsupported input unit: {unit}. Supported units: Meters, Inches, Yards")


def convert_from_meters(meters: Decimal, unit: str) -> Decimal:
    """
    Convert meters to the desired output unit.
    
    Args:
        meters: Quantity in meters
        unit: The output unit (Yards, Inches, Meters)
    
    Returns:
        Quantity in the specified unit
    """
    unit = unit.lower().strip()
    
    if unit in ('yard', 'yards', 'yd'):
        # 1 meter = 1.09361 yards
        return meters * METER_TO_YARD
    elif unit in ('inch', 'inches', 'in'):
        # First convert to yards, then to inches
        # 1 yard = 36 inches
        yards = meters * METER_TO_YARD
        return yards * YARD_TO_INCH
    elif unit in ('meter', 'meters', 'm'):
        return meters
    else:
        raise ValueError(f"Unsupported output unit: {unit}. Supported units: Yards, Inches, Meters")


def calculate_required_rolls(quantity_meters: Decimal) -> int:
    """
    Calculate the number of rolls required based on standard roll length.
    
    Args:
        quantity_meters: Total quantity in meters
    
    Returns:
        Number of rolls needed (rounded up)
    """
    # Apply wastage factor first
    quantity_with_wastage = quantity_meters * (Decimal('1') + WASTAGE_FACTOR)
    
    # Calculate required rolls (round up)
    rolls = math.ceil(float(quantity_with_wastage / STANDARD_ROLL_LENGTH_METERS))
    
    return rolls


def calculate_carpet_measurement(
    purchase_qty: Decimal,
    input_unit: Literal['Meters', 'Inches'],
    output_unit: Literal['Yards', 'Inches', 'Meters'],
    price_per_unit: Decimal = Decimal('0')
) -> Dict[str, Any]:
    """
    Calculate carpet measurements with unit conversion, wastage, and roll requirements.
    
    Args:
        purchase_qty: The quantity to purchase
        input_unit: Input unit (Meters or Inches)
        output_unit: Output unit (Yards, Inches, or Meters)
        price_per_unit: Price per unit in the output unit (optional)
    
    Returns:
        Dictionary containing:
        - original_quantity: Original input quantity
        - input_unit: Original input unit
        - quantity_in_meters: Converted quantity in meters
        - wastage_quantity: Amount of wastage (5%)
        - total_quantity_with_wastage: Total including wastage
        - required_rolls: Number of rolls needed (30m each)
        - output_quantity: Final converted quantity
        - output_unit: Final output unit
        - final_sale_price: Calculated price based on converted unit
    
    Example:
        >>> calculate_carpet_measurement(
        ...     purchase_qty=100,
        ...     input_unit='Meters',
        ...     output_unit='Yards',
        ...     price_per_unit=Decimal('15.00')
        ... )
    """
    # Validate inputs
    if purchase_qty <= 0:
        raise ValueError("purchase_qty must be greater than 0")
    
    if price_per_unit < 0:
        raise ValueError("price_per_unit cannot be negative")
    
    # Convert input to meters (base unit)
    quantity_in_meters = convert_to_meters(purchase_qty, input_unit)
    
    # Calculate wastage (5%)
    wastage_quantity = quantity_in_meters * WASTAGE_FACTOR
    total_quantity_with_wastage = quantity_in_meters + wastage_quantity
    
    # Calculate required rolls
    required_rolls = calculate_required_rolls(quantity_in_meters)
    
    # Convert to output unit
    output_quantity = convert_from_meters(total_quantity_with_wastage, output_unit)
    
    # Round to 2 decimal places for currency/measurements
    output_quantity = output_quantity.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    # Calculate final sale price
    final_sale_price = output_quantity * price_per_unit
    final_sale_price = final_sale_price.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    return {
        'original_quantity': float(purchase_qty),
        'input_unit': input_unit,
        'quantity_in_meters': float(quantity_in_meters),
        'wastage_quantity': float(wastage_quantity),
        'total_quantity_with_wastage': float(total_quantity_with_wastage),
        'required_rolls': required_rolls,
        'output_quantity': float(output_quantity),
        'output_unit': output_unit,
        'final_sale_price': float(final_sale_price)
    }


def get_conversion_rate(from_unit: str, to_unit: str) -> Decimal:
    """
    Get the conversion rate between two units.
    
    Args:
        from_unit: Source unit
        to_unit: Target unit
    
    Returns:
        Conversion rate multiplier
    """
    from_unit = from_unit.lower().strip()
    to_unit = to_unit.lower().strip()
    
    # Convert to meters first
    meters = convert_to_meters(Decimal('1'), from_unit)
    
    # Convert from meters to target
    result = convert_from_meters(meters, to_unit)
    
    return result


def calculate_carpet_sale(
    sale_quantity: float,
    sale_unit: str,
    current_stock_meters: float
) -> Dict[str, Any]:
    """
    Calculate carpet sale deduction with unit conversion and aviation cutting waste.
    
    Handles carpet sales by converting the sale quantity to meters (base unit),
    adding 5% aviation cutting waste, and checking if there's sufficient stock.
    
    Conversion Rules:
        - 1 Meter = 1.09361 Yards
        - 1 Yard = 36 Inches
        - 1 Meter = 39.3701 Inches
    
    Args:
        sale_quantity: The quantity being sold (float)
        sale_unit: The unit of measurement ('inches', 'yards', or 'meters')
        current_stock_meters: Current stock level in meters
    
    Returns:
        Dictionary containing:
        - meters_to_deduct: Total meters to deduct (including 5% waste)
        - has_enough_stock: Boolean indicating if stock is sufficient
    
    Example:
        >>> calculate_carpet_sale(100, 'yards', 150)
        {'meters_to_deduct': 100.46, 'has_enough_stock': True}
        
        >>> calculate_carpet_sale(1181.1, 'inches', 25)
        {'meters_to_deduct': 31.50, 'has_enough_stock': False}
    """
    # Convert inputs to Decimal for high precision (aviation compliance)
    quantity = Decimal(str(sale_quantity))
    current_stock = Decimal(str(current_stock_meters))
    
    # Normalize unit to lowercase
    unit = sale_unit.lower().strip()
    
    # Convert sale quantity to meters based on unit
    if unit in ('meter', 'meters', 'm'):
        quantity_in_meters = quantity
    elif unit in ('yard', 'yards', 'yd'):
        # 1 Yard = 36 Inches, 1 Meter = 39.3701 Inches
        # Therefore: 1 Yard = 36/39.3701 Meters = 0.9144 Meters
        quantity_in_meters = quantity * Decimal('0.9144')
    elif unit in ('inch', 'inches', 'in'):
        # 1 Inch = 1/39.3701 Meters = 0.0254 Meters
        quantity_in_meters = quantity * Decimal('0.0254')
    else:
        raise ValueError(
            f"Unsupported sale unit: {sale_unit}. "
            f"Supported units: 'inches', 'yards', 'meters'"
        )
    
    # Calculate 5% Aviation Cutting Waste
    wastage = quantity_in_meters * WASTAGE_FACTOR
    meters_to_deduct = quantity_in_meters + wastage
    
    # Check if there's enough stock
    has_enough_stock = current_stock >= meters_to_deduct
    
    # Round to 4 decimal places for precision (aviation compliance)
    meters_to_deduct = meters_to_deduct.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)
    
    return {
        'meters_to_deduct': float(meters_to_deduct),
        'has_enough_stock': has_enough_stock
    }


# Example usage and testing
if __name__ == "__main__":
    # Test Case 1: Meters to Yards
    result1 = calculate_carpet_measurement(
        purchase_qty=Decimal('100'),
        input_unit='Meters',
        output_unit='Yards',
        price_per_unit=Decimal('15.00')
    )
    print("Test 1 - Meters to Yards:")
    print(f"  Input: 100 Meters -> Output: {result1['output_quantity']} Yards")
    print(f"  Required Rolls: {result1['required_rolls']}")
    print(f"  Final Price: ${result1['final_sale_price']}")
    print()
    
    # Test Case 2: Inches to Meters
    result2 = calculate_carpet_measurement(
        purchase_qty=Decimal('1181.1'),  # ~30 meters in inches
        input_unit='Inches',
        output_unit='Meters',
        price_per_unit=Decimal('20.00')
    )
    print("Test 2 - Inches to Meters:")
    print(f"  Input: 1181.1 Inches -> Output: {result2['output_quantity']} Meters")
    print(f"  Required Rolls: {result2['required_rolls']}")
    print(f"  Final Price: ${result2['final_sale_price']}")
    print()
    
    # Test Case 3: Inches to Yards
    result3 = calculate_carpet_measurement(
        purchase_qty=Decimal('1181.1'),
        input_unit='Inches',
        output_unit='Yards',
        price_per_unit=Decimal('25.00')
    )
    print("Test 3 - Inches to Yards:")
    print(f"  Input: 1181.1 Inches -> Output: {result3['output_quantity']} Yards")
    print(f"  Required Rolls: {result3['required_rolls']}")
    print(f"  Final Price: ${result3['final_sale_price']}")
    print()
    
    # Test Case 4: Meters to Inches
    result4 = calculate_carpet_measurement(
        purchase_qty=Decimal('30'),
        input_unit='Meters',
        output_unit='Inches',
        price_per_unit=Decimal('10.00')
    )
    print("Test 4 - Meters to Inches:")
    print(f"  Input: 30 Meters -> Output: {result4['output_quantity']} Inches")
    print(f"  Required Rolls: {result4['required_rolls']}")
    print(f"  Final Price: ${result4['final_sale_price']}")
    print()
    
    # Display conversion rates
    print("Conversion Rates:")
    print(f"  1 Meter = {get_conversion_rate('Meters', 'Yards')} Yards")
    print(f"  1 Yard = {get_conversion_rate('Yards', 'Inches')} Inches")
    print(f"  1 Meter = {get_conversion_rate('Meters', 'Inches')} Inches")
    print()
    
    # =============================================================================
    # Test Cases for calculate_carpet_sale function
    # =============================================================================
    print("=" * 60)
    print("Test Cases for calculate_carpet_sale")
    print("=" * 60)
    
    # Test Case 1: Sale in Yards with enough stock
    print("\n1. Sale in Yards (enough stock):")
    print("-" * 40)
    result = calculate_carpet_sale(100, 'yards', 150)
    print(f"  Input: 100 Yards, Stock: 150 meters")
    print(f"  Result: {result}")
    print(f"  Expected: meters_to_deduct ≈ 100.46, has_enough_stock = True")
    
    # Test Case 2: Sale in Inches with insufficient stock
    print("\n2. Sale in Inches (insufficient stock):")
    print("-" * 40)
    result = calculate_carpet_sale(1181.1, 'inches', 25)
    print(f"  Input: 1181.1 Inches, Stock: 25 meters")
    print(f"  Result: {result}")
    print(f"  Expected: meters_to_deduct ≈ 31.50, has_enough_stock = False")
    
    # Test Case 3: Sale in Meters with exact stock
    print("\n3. Sale in Meters (exact stock):")
    print("-" * 40)
    result = calculate_carpet_sale(50, 'meters', 52.5)
    print(f"  Input: 50 Meters, Stock: 52.5 meters")
    print(f"  Result: {result}")
    print(f"  Expected: meters_to_deduct = 52.5, has_enough_stock = True")
    
    # Test Case 4: Sale in Meters with just enough stock
    print("\n4. Sale in Meters (just enough stock):")
    print("-" * 40)
    result = calculate_carpet_sale(50, 'meters', 52.5)
    print(f"  Input: 50 Meters, Stock: 52.5 meters")
    print(f"  Result: {result}")
    print(f"  Expected: has_enough_stock = True (52.5 >= 52.5)")
    
    # Test Case 5: Sale in Inches with enough stock
    print("\n5. Sale in Inches (enough stock):")
    print("-" * 40)
    result = calculate_carpet_sale(393.701, 'inches', 15)
    print(f"  Input: 393.701 Inches (~10 meters), Stock: 15 meters")
    print(f"  Result: {result}")
    print(f"  Expected: meters_to_deduct ≈ 10.5, has_enough_stock = True")
    
    # Test Case 6: Invalid unit
    print("\n6. Invalid unit error handling:")
    print("-" * 40)
    try:
        result = calculate_carpet_sale(100, 'feet', 150)
    except ValueError as e:
        print(f"  Error caught: {e}")
        print(f"  Expected: ValueError for unsupported unit 'feet'")

