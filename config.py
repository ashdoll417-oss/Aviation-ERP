"""
Configuration module for Aviation ERP
Loads environment variables for Supabase and app settings.
"""

import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()


class Settings:
    """Application settings loaded from environment variables."""
    
    # Supabase Configuration
    SUPABASE_URL: str = os.environ.get("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.environ.get("SUPABASE_KEY", "")
    SUPABASE_SERVICE_KEY: str = os.environ.get("SUPABASE_SERVICE_KEY", "")  # For admin operations
    
    # FastAPI CORS - Frontend Domains
    ADMIN_DOMAIN: str = os.environ.get("ADMIN_DOMAIN", "")  # e.g., https://admin-aviation-erp.onrender.com
    STAFF_DOMAIN: str = os.environ.get("STAFF_DOMAIN", "")    # e.g., https://staff.example.com
    SALES_DOMAIN: str = os.environ.get("SALES_DOMAIN", "")   # e.g., https://sales.example.com
    
    # App Configuration
    APP_NAME: str = "Aviation ERP"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = os.environ.get("DEBUG", "False").lower() == "true"
    
    # Database
    DATABASE_URL: str = os.environ.get("DATABASE_URL", "")
    
    # Africa's Talking SMS Configuration
    AFRICAS_TALKING_API_KEY: str = os.environ.get("AFRICAS_TALKING_API_KEY", "")
    AFRICAS_TALKING_USERNAME: str = os.environ.get("AFRICAS_TALKING_USERNAME", "sandbox")  # Use 'sandbox' for testing
    AFRICAS_TALKING_SENDER_ID: str = os.environ.get("AFRICAS_TALKING_SENDER_ID", "")  # Short code or sender ID
    
    # Twilio SMS Configuration
    TWILIO_ACCOUNT_SID: str = os.environ.get("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN: str = os.environ.get("TWILIO_AUTH_TOKEN", "")
    TWILIO_PHONE_NUMBER: str = os.environ.get("TWILIO_PHONE_NUMBER", "")
    
    # SMS Recipient (for notifications)
    SMS_RECIPIENT: str = os.environ.get("SMS_RECIPIENT", "")  # Phone number to receive notifications
    
    # Default Delivery Location (for SMS notifications)
    DEFAULT_DELIVERY_LOCATION: str = os.environ.get("DEFAULT_DELIVERY_LOCATION", "Warehouse")  # e.g., 'Hangar', 'Kitchen', 'Warehouse'
    
    @classmethod
    def get_cors_origins(cls) -> list[str]:
        """
        Get list of CORS allowed origins.
        
        Returns:
            List of allowed domain URLs
        """
        origins = []
        
        if cls.ADMIN_DOMAIN:
            origins.append(cls.ADMIN_DOMAIN)
        if cls.STAFF_DOMAIN:
            origins.append(cls.STAFF_DOMAIN)
        if cls.SALES_DOMAIN:
            origins.append(cls.SALES_DOMAIN)
        
        # Add localhost for development
        origins.extend([
            "http://localhost:3000",
            "http://localhost:5173",
            "http://localhost:8000",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:8000",
        ])
        
        return list(set(origins))  # Remove duplicates
    
    @classmethod
    def validate(cls) -> bool:
        """
        Validate required configuration.
        
        Returns:
            True if all required settings are present
        """
        if not cls.SUPABASE_URL:
            print("Warning: SUPABASE_URL not set")
            return False
        if not cls.SUPABASE_KEY:
            print("Warning: SUPABASE_KEY not set")
            return False
        return True


# Create settings instance
settings = Settings()


def get_supabase_client():
    """
    Initialize and return Supabase client using environment variables.
    
    Returns:
        Supabase Client instance
    """
    from supabase import create_client
    
    if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
        raise ValueError(
            "SUPABASE_URL and SUPABASE_KEY must be set in environment variables"
        )
    
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)


def get_supabase_service_client():
    """
    Initialize and return Supabase service client (with service role key).
    Used for admin operations that bypass RLS.
    
    Returns:
        Supabase Client with service role key
    """
    from supabase import create_client
    
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_KEY:
        raise ValueError(
            "SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in environment variables"
        )
    
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)

