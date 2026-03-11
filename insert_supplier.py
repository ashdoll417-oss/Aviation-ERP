"""
Supabase Supplier Insert Function
Python function to insert a new supplier into the suppliers table
Uses environment variables for Supabase URL and Key
"""

import os
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def get_supabase_client() -> Client:
    """
    Initialize and return Supabase client using environment variables.
    
    Returns:
        Supabase Client instance
        
    Raises:
        ValueError: If SUPABASE_URL or SUPABASE_KEY is not set
    """
    supabase_url: str = os.environ.get("SUPABASE_URL", "")
    supabase_key: str = os.environ.get("SUPABASE_KEY", "")
    
    if not supabase_url or not supabase_key:
        raise ValueError(
            "SUPABASE_URL and SUPABASE_KEY must be set in environment variables"
        )
    
    return create_client(supabase_url, supabase_key)


def insert_supplier(
    supplier_name: str,
    email: str = None,
    phone: str = None,
    contact_person: str = None
) -> dict:
    """
    Insert a new supplier into the suppliers table.
    
    Args:
        supplier_name: Name of the supplier (required)
        email: Email address of the supplier (optional)
        phone: Phone number of the supplier (optional)
        contact_person: Contact person at the supplier (optional)
    
    Returns:
        Dictionary with success status and data or error message
        {
            "success": True,
            "data": {...}  # Inserted supplier data
        }
        or
        {
            "success": False,
            "error": "Error message"
        }
    """
    try:
        # Validate required field
        if not supplier_name or not supplier_name.strip():
            return {
                "success": False,
                "error": "supplier_name is required and cannot be empty"
            }
        
        # Get Supabase client
        supabase = get_supabase_client()
        
        # Prepare supplier data
        supplier_data = {
            "supplier_name": supplier_name.strip()
        }
        
        # Add optional fields if provided
        if email:
            supplier_data["email"] = email.strip()
        if phone:
            supplier_data["phone"] = phone.strip()
        if contact_person:
            supplier_data["contact_person"] = contact_person.strip()
        
        # Insert into suppliers table
        response = supabase.table("suppliers").insert(supplier_data).execute()
        
        # Check if insert was successful
        if response.data and len(response.data) > 0:
            return {
                "success": True,
                "data": response.data[0]
            }
        else:
            return {
                "success": False,
                "error": "Insert completed but no data returned"
            }
            
    except Exception as e:
        # Print specific error message
        error_message = str(e)
        print(f"Error inserting supplier: {error_message}")
        
        return {
            "success": False,
            "error": error_message
        }


def insert_supplier_simple(supplier_name: str, email: str = None, phone: str = None) -> bool:
    """
    Simple version of insert_supplier that just returns True/False.
    
    Args:
        supplier_name: Name of the supplier
        email: Email address (optional)
        phone: Phone number (optional)
    
    Returns:
        True if successful, False otherwise
    """
    result = insert_supplier(supplier_name, email, phone)
    return result.get("success", False)


# Example usage
if __name__ == "__main__":
    # Test the function
    result = insert_supplier(
        supplier_name="Test Supplier Ltd",
        email="contact@testsSupplier.com",
        phone="+254700000000",
        contact_person="John Doe"
    )
    
    if result["success"]:
        print(f"✓ Supplier inserted successfully!")
        print(f"  ID: {result['data'].get('id')}")
        print(f"  Name: {result['data'].get('supplier_name')}")
    else:
        print(f"✗ Failed to insert supplier: {result['error']}")

