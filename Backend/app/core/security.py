"""
Security utilities for sanitizing sensitive data in logs
"""

from typing import Dict, List, Any, Optional
import copy


# Default list of sensitive fields that should never be logged
SENSITIVE_FIELDS = [
    'password',
    'current_password',
    'new_password',
    'confirm_password',
    'two_factor_code',
    'secret',
    'backup_codes',
    'hashed_password',
    'token',
    'access_token',
    'refresh_token',
    'api_key',
    'secret_key',
    'private_key',
    'authorization',
    'auth_token',
]


def sanitize_for_logging(data: Dict[str, Any], exclude: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Remove sensitive fields from a dictionary for safe logging.
    
    Args:
        data: Dictionary to sanitize
        exclude: Additional fields to exclude (merged with SENSITIVE_FIELDS)
    
    Returns:
        A new dictionary with sensitive fields removed or masked
    """
    if not isinstance(data, dict):
        return data
    
    # Create a deep copy to avoid modifying the original
    sanitized = copy.deepcopy(data)
    
    # Combine default sensitive fields with user-provided exclude list
    fields_to_exclude = set(SENSITIVE_FIELDS)
    if exclude:
        fields_to_exclude.update(exclude)
    
    # Recursively sanitize nested dictionaries
    def sanitize_dict(d: Dict[str, Any]) -> Dict[str, Any]:
        result = {}
        for key, value in d.items():
            # Check if key should be excluded (case-insensitive)
            key_lower = key.lower()
            should_exclude = any(
                sensitive_field.lower() in key_lower 
                for sensitive_field in fields_to_exclude
            )
            
            if should_exclude:
                # Mask the value instead of removing it (for debugging)
                result[key] = "***REDACTED***"
            elif isinstance(value, dict):
                # Recursively sanitize nested dictionaries
                result[key] = sanitize_dict(value)
            elif isinstance(value, list):
                # Sanitize list items if they are dictionaries
                result[key] = [
                    sanitize_dict(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                result[key] = value
        
        return result
    
    return sanitize_dict(sanitized)


def safe_log_request(request_data: Dict[str, Any], exclude: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Helper function to safely log request data.
    
    Args:
        request_data: Request data dictionary
        exclude: Additional fields to exclude
    
    Returns:
        Sanitized request data safe for logging
    """
    return sanitize_for_logging(request_data, exclude=exclude)


def safe_log_response(response_data: Dict[str, Any], exclude: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Helper function to safely log response data.
    
    Args:
        response_data: Response data dictionary
        exclude: Additional fields to exclude
    
    Returns:
        Sanitized response data safe for logging
    """
    return sanitize_for_logging(response_data, exclude=exclude)
