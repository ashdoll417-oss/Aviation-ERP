"""
SMS Notification Module for Aviation ERP
Uses Africa's Talking API to send SMS notifications for orders.
"""

import requests
import json
from typing import Optional, Dict, Any, List
from config import settings


class SMSNotificationError(Exception):
    """Custom exception for SMS notification errors."""
    pass


def send_sms_via_africas_talking(
    recipient: str,
    message: str,
    api_key: Optional[str] = None,
    username: Optional[str] = None,
    sender_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Send SMS via Africa's Talking API.
    
    Args:
        recipient: Phone number in international format (e.g., '+254712345678')
        message: SMS message content
        api_key: Africa's Talking API key (optional, uses settings if not provided)
        username: Africa's Talking username (optional, uses settings if not provided)
        sender_id: Sender ID or short code (optional, uses settings if not provided)
    
    Returns:
        Dictionary with response status and details
    
    Raises:
        SMSNotificationError: If SMS sending fails
    """
    # Use provided values or fall back to settings
    api_key = api_key or settings.AFRICAS_TALKING_API_KEY
    username = username or settings.AFRICAS_TALKING_USERNAME
    sender_id = sender_id or settings.AFRICAS_TALKING_SENDER_ID
    
    # Validate configuration
    if not api_key:
        raise SMSNotificationError("Africa's Talking API key is not configured")
    
    if not recipient:
        raise SMSNotificationError("Recipient phone number is required")
    
    # Format recipient number (ensure international format)
    formatted_recipient = format_phone_number(recipient)
    
    # Africa's Talking SMS API endpoint
    url = f"https://api.africastalking.com/version1/messaging"
    
    # Headers
    headers = {
        "ApiKey": api_key,
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json"
    }
    
    # Payload
    payload = {
        "username": username,
        "to": formatted_recipient,
        "message": message
    }
    
    if sender_id:
        payload["from"] = sender_id
    
    try:
        response = requests.post(url, headers=headers, data=payload, timeout=30)
        response.raise_for_status()
        
        result = response.json()
        
        # Check for API-level errors
        if "SMSMessageData" in result:
            message_data = result["SMSMessageData"]
            if "Recipients" in message_data:
                recipients = message_data["Recipients"]
                if recipients and recipients[0].get("status") != "Success":
                    error_message = recipients[0].get("message", "Unknown error")
                    raise SMSNotificationError(f"SMS failed: {error_message}")
            
            return {
                "success": True,
                "message": "SMS sent successfully",
                "message_id": message_data.get("MessageId"),
                "recipients": message_data.get("Recipients", [])
            }
        else:
            raise SMSNotificationError(f"Unexpected API response: {result}")
            
    except requests.exceptions.RequestException as e:
        raise SMSNotificationError(f"Failed to send SMS: {str(e)}")


def send_sms_via_twilio(
    recipient: str,
    message: str,
    account_sid: Optional[str] = None,
    auth_token: Optional[str] = None,
    sender_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Send SMS via Twilio API.
    
    Args:
        recipient: Phone number in international format (e.g., '+254712345678')
        message: SMS message content
        account_sid: Twilio Account SID (optional, uses settings if not provided)
        auth_token: Twilio Auth Token (optional, uses settings if not provided)
        sender_id: Twilio phone number (optional, uses settings if not provided)
    
    Returns:
        Dictionary with response status and details
    
    Raises:
        SMSNotificationError: If SMS sending fails
    """
    from twilio.rest import Client
    from twilio.base.exceptions import TwilioRestException
    
    # Use provided values or fall back to settings
    account_sid = account_sid or settings.TWILIO_ACCOUNT_SID
    auth_token = auth_token or settings.TWILIO_AUTH_TOKEN
    sender_id = sender_id or settings.TWILIO_PHONE_NUMBER
    
    # Validate configuration
    if not account_sid:
        raise SMSNotificationError("Twilio Account SID is not configured")
    
    if not auth_token:
        raise SMSNotificationError("Twilio Auth Token is not configured")
    
    if not sender_id:
        raise SMSNotificationError("Twilio phone number is not configured")
    
    if not recipient:
        raise SMSNotificationError("Recipient phone number is required")
    
    # Format recipient number
    formatted_recipient = format_phone_number(recipient)
    
    try:
        client = Client(account_sid, auth_token)
        twilio_message = client.messages.create(
            body=message,
            from_=sender_id,
            to=formatted_recipient
        )
        
        return {
            "success": True,
            "message": "SMS sent successfully",
            "message_id": twilio_message.sid,
            "status": twilio_message.status
        }
        
    except TwilioRestException as e:
        raise SMSNotificationError(f"Twilio error: {str(e)}")
    except Exception as e:
        raise SMSNotificationError(f"Failed to send SMS: {str(e)}")


def send_delivery_sms(
    delivery_note_number: str,
    quantity: float,
    unit: str,
    product_name: str,
    remaining_stock: float,
    location: str = "Warehouse",
    recipient: Optional[str] = None,
    use_twilio: bool = False
) -> Dict[str, Any]:
    """
    Send Delivery Note SMS notification after a successful sale.
    
    This function sends an SMS to notify about a delivery/issue of materials.
    The message uses the unit the staff selected (e.g., Yards) for customer clarity,
    even though the database deducted in base units (e.g., Meters).
    
    Message format:
    'Delivery Note [No]: [Qty] [Unit] of [Product] issued. Remaining Stock: [Stock]. Location: [Hangar/Kitchen].'
    
    Args:
        delivery_note_number: Delivery Note / DN number
        quantity: Quantity issued (in the staff-selected unit)
        unit: Unit selected by staff (e.g., 'Yards', 'Lts', 'Kg')
        product_name: Name of the product issued
        remaining_stock: Remaining stock after deduction
        location: Storage location (e.g., 'Hangar', 'Kitchen', 'Warehouse')
        recipient: Recipient phone number (optional, uses settings if not provided)
        use_twilio: Whether to use Twilio instead of Africa's Talking
    
    Returns:
        Dictionary with response status and details
    
    Example:
        >>> send_delivery_sms(
        ...     delivery_note_number="DN-2024-001",
        ...     quantity=20,
        ...     unit="Yards",
        ...     product_name="Aviation Carpet - Grey",
        ...     remaining_stock=80.5,
        ...     location="Hangar"
        ... )
        # Message: "Delivery Note DN-2024-001: 20 Yards of Aviation Carpet - Grey issued. Remaining Stock: 80.50. Location: Hangar."
    """
    recipient = recipient or settings.SMS_RECIPIENT
    
    if not recipient:
        raise SMSNotificationError(
            "No recipient specified. Set SMS_RECIPIENT in environment or pass recipient parameter."
        )
    
    # Format the delivery SMS message
    # Round values for display
    quantity_display = round(quantity, 2) if isinstance(quantity, float) else quantity
    stock_display = round(remaining_stock, 2) if isinstance(remaining_stock, float) else remaining_stock
    
    message = (
        f"Delivery Note {delivery_note_number}: "
        f"{quantity_display} {unit} of {product_name} issued. "
        f"Remaining Stock: {stock_display}. "
        f"Location: {location}."
    )
    
    # Send via selected provider
    if use_twilio:
        return send_sms_via_twilio(
            recipient=recipient,
            message=message
        )
    else:
        return send_sms_via_africas_talking(
            recipient=recipient,
            message=message
        )


def send_delivery_sms_from_sale(
    sale_result: Dict[str, Any],
    staff_selected_unit: str,
    recipient: Optional[str] = None,
    use_twilio: bool = False
) -> Dict[str, Any]:
    """
    Send Delivery Note SMS after a successful sale transaction.
    
    This helper function extracts the required information from the sale result
    and sends the delivery SMS.
    
    Args:
        sale_result: The result dictionary from a successful sale API call
        staff_selected_unit: The unit selected by staff (e.g., 'Yards', 'Lts')
        recipient: Recipient phone number (optional, uses settings if not provided)
        use_twilio: Whether to use Twilio instead of Africa's Talking
    
    Returns:
        Dictionary with SMS sending status and details
    
    Example:
        >>> # After a successful sale
        >>> sale_result = {
        ...     "product_name": "Aviation Carpet - Grey",
        ...     "quantity_deducted": 19.2,  # In meters (after conversion)
        ...     "stock_after": 80.5,
        ...     "product_id": "uuid-of-product"
        ... }
        >>> send_delivery_sms_from_sale(
        ...     sale_result=sale_result,
        ...     staff_selected_unit="Yards",
        ...     delivery_note_number="DN-001"
        ... )
    """
    # Extract sale details
    product_name = sale_result.get("product_name", "Unknown Product")
    stock_after = sale_result.get("stock_after", 0)
    
    # Get quantity in staff-selected unit (not the converted base unit)
    # The frontend should pass the original quantity, not the converted one
    quantity = sale_result.get("original_quantity") or sale_result.get("quantity_deducted", 0)
    
    # Get location - could be from product or settings
    location = sale_result.get("location") or settings.DEFAULT_DELIVERY_LOCATION or "Warehouse"
    
    # Get delivery note number
    delivery_note_number = sale_result.get("delivery_note_number") or sale_result.get("reference_id") or "N/A"
    
    return send_delivery_sms(
        delivery_note_number=delivery_note_number,
        quantity=quantity,
        unit=staff_selected_unit,
        product_name=product_name,
        remaining_stock=stock_after,
        location=location,
        recipient=recipient,
        use_twilio=use_twilio
    )


def format_phone_number(phone: str) -> str:
    """
    Format phone number to international format.
    
    Args:
        phone: Phone number in various formats
    
    Returns:
        Phone number in international format (e.g., '+254712345678')
    """
    # Remove all non-digit characters
    digits = ''.join(filter(str.isdigit, phone))
    
    # If starts with country code (254 for Kenya)
    if digits.startswith('254'):
        return f'+{digits}'
    
    # If starts with 0 (local format)
    if digits.startswith('0') and len(digits) == 10:
        return f'+254{digits[1:]}'
    
    # If it's already in international format without +
    if len(digits) >= 10:
        return f'+{digits}'
    
    return phone  # Return as-is if can't determine format


def send_order_sms_notification(
    order_id: str,
    product_name: str,
    total_price: float,
    delivery_status: str,
    recipient: Optional[str] = None
) -> Dict[str, Any]:
    """
    Send SMS notification for a Purchase Order or Delivery Note.
    
    Args:
        order_id: The ID of the order/delivery note
        product_name: Name of the product ordered
        total_price: Total price of the order
        delivery_status: Delivery status (e.g., 'Pending', 'Delivered', 'Processing')
        recipient: Recipient phone number (optional, uses settings if not provided)
    
    Returns:
        Dictionary with response status and details
    """
    recipient = recipient or settings.SMS_RECIPIENT
    
    if not recipient:
        raise SMSNotificationError(
            "No recipient specified. Set SMS_RECIPIENT in environment or pass recipient parameter."
        )
    
    # Format the message
    message = (
        f"Aviation ERP Notification\n"
        f"-------------------------\n"
        f"Order ID: {order_id}\n"
        f"Product: {product_name}\n"
        f"Total: KES {total_price:,.2f}\n"
        f"Status: {delivery_status}\n"
        f"-------------------------\n"
        f"Thank you for your order!"
    )
    
    return send_sms_via_africas_talking(
        recipient=recipient,
        message=message
    )


def send_sale_sms_notification(
    order_id: str,
    product_name: str,
    total_price: float,
    delivery_status: str = "Processing",
    recipient: Optional[str] = None
) -> Dict[str, Any]:
    """
    Send SMS notification for a Sale transaction.
    
    This is an alias for send_order_sms_notification with default status 'Processing'.
    
    Args:
        order_id: The ID of the sale order
        product_name: Name of the product sold
        total_price: Total price of the sale
        delivery_status: Delivery status (default: 'Processing')
        recipient: Recipient phone number (optional, uses settings if not provided)
    
    Returns:
        Dictionary with response status and details
    """
    return send_order_sms_notification(
        order_id=order_id,
        product_name=product_name,
        total_price=total_price,
        delivery_status=delivery_status,
        recipient=recipient
    )


def send_bulk_order_notifications(
    orders: List[Dict[str, Any]],
    recipient: Optional[str] = None
) -> Dict[str, Any]:
    """
    Send SMS notifications for multiple orders.
    
    Args:
        orders: List of order dictionaries with keys: order_id, product_name, total_price, delivery_status
        recipient: Recipient phone number (optional, uses settings if not provided)
    
    Returns:
        Dictionary with summary of sent and failed notifications
    """
    recipient = recipient or settings.SMS_RECIPIENT
    
    if not recipient:
        raise SMSNotificationError(
            "No recipient specified. Set SMS_RECIPIENT in environment or pass recipient parameter."
        )
    
    results = {
        "total": len(orders),
        "success": 0,
        "failed": 0,
        "details": []
    }
    
    for order in orders:
        try:
            result = send_order_sms_notification(
                order_id=order.get("order_id", "N/A"),
                product_name=order.get("product_name", "Unknown Product"),
                total_price=order.get("total_price", 0),
                delivery_status=order.get("delivery_status", "Pending"),
                recipient=recipient
            )
            results["success"] += 1
            results["details"].append({
                "order_id": order.get("order_id"),
                "status": "success",
                "message": result
            })
        except SMSNotificationError as e:
            results["failed"] += 1
            results["details"].append({
                "order_id": order.get("order_id"),
                "status": "failed",
                "error": str(e)
            })
    
    return results


def check_sms_configuration() -> Dict[str, bool]:
    """
    Check if SMS configuration is properly set.
    
    Returns:
        Dictionary with configuration status
    """
    return {
        "api_key_configured": bool(settings.AFRICAS_TALKING_API_KEY),
        "username_configured": bool(settings.AFRICAS_TALKING_USERNAME),
        "sender_id_configured": bool(settings.AFRICAS_TALKING_SENDER_ID),
        "recipient_configured": bool(settings.SMS_RECIPIENT),
        "fully_configured": all([
            settings.AFRICAS_TALKING_API_KEY,
            settings.AFRICAS_TALKING_USERNAME,
            settings.SMS_RECIPIENT
        ])
    }


# =============================================================================
# EXAMPLE USAGE AND TESTING
# =============================================================================

def demo_sms():
    """
    Demonstrate SMS notification functionality.
    """
    print("=" * 60)
    print("SMS Notification Module - Demo")
    print("=" * 60)
    
    # Check configuration
    config_status = check_sms_configuration()
    print("\nConfiguration Status:")
    for key, value in config_status.items():
        print(f"  {key}: {'✓' if value else '✗'}")
    
    print("\n" + "-" * 40)
    print("Example SMS Message:")
    print("-" * 40)
    
    example_message = (
        f"Aviation ERP Notification\n"
        f"-------------------------\n"
        f"Order ID: ORD-2024-001\n"
        f"Product: White Topcoat Kit\n"
        f"Total: KES 15,000.00\n"
        f"Status: Processing\n"
        f"-------------------------\n"
        f"Thank you for your order!"
    )
    
    print(example_message)
    
    print("\n" + "-" * 40)
    print("Phone Number Formatting Examples:")
    print("-" * 40)
    test_numbers = [
        "+254712345678",
        "0712345678",
        "254712345678",
        "07 123 456 78"
    ]
    
    for num in test_numbers:
        print(f"  {num} -> {format_phone_number(num)}")
    
    print("\n" + "=" * 60)
    print("To send actual SMS, configure environment variables:")
    print("  AFRICAS_TALKING_API_KEY=your_api_key")
    print("  AFRICAS_TALKING_USERNAME=your_username")
    print("  SMS_RECIPIENT=+254712345678")
    print("=" * 60)


if __name__ == "__main__":
    demo_sms()

