"""
Helper Utilities
Common helper functions
"""
from typing import Any, Dict
from datetime import datetime


def format_response(data: Any, message: str = "Success") -> Dict[str, Any]:
    """
    Format API response in a consistent structure
    
    Args:
        data: Response data
        message: Response message
        
    Returns:
        Formatted response dictionary
    """
    return {
        "message": message,
        "data": data,
        "timestamp": datetime.utcnow().isoformat()
    }


def validate_input(value: Any, field_name: str) -> None:
    """
    Basic input validation helper
    
    Args:
        value: Value to validate
        field_name: Name of the field
        
    Raises:
        ValueError: If validation fails
    """
    if value is None:
        raise ValueError(f"{field_name} cannot be None")
    if isinstance(value, str) and not value.strip():
        raise ValueError(f"{field_name} cannot be empty")

