"""
Admin Authentication Exception Classes

This module defines custom exceptions for admin authentication operations,
providing detailed error information for JWT token validation, organization
membership verification, and admin authorization failures.
"""

from typing import Optional, Dict, Any


class AdminAuthenticationError(Exception):
    """Base exception for admin authentication errors"""
    
    def __init__(self, message: str, error_code: str = "AUTH_ERROR", details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class InvalidJWTTokenError(AdminAuthenticationError):
    """Raised when JWT token is invalid, malformed, or expired"""
    
    def __init__(self, message: str = "Invalid or expired JWT token", token_error: Optional[str] = None):
        details = {"token_error": token_error} if token_error else {}
        super().__init__(
            message=message,
            error_code="INVALID_JWT_TOKEN",
            details=details
        )


class OrganizationMembershipRequiredError(AdminAuthenticationError):
    """Raised when user is not a member of the required admin organization"""
    
    def __init__(
        self, 
        message: str = "Admin organization membership required",
        user_id: Optional[str] = None,
        required_organization_id: Optional[str] = None,
        user_organizations: Optional[list] = None
    ):
        details = {
            "user_id": user_id,
            "required_organization_id": required_organization_id,
            "user_organizations": user_organizations or []
        }
        super().__init__(
            message=message,
            error_code="ORGANIZATION_MEMBERSHIP_REQUIRED",
            details=details
        )


class InvalidOrganizationError(AdminAuthenticationError):
    """Raised when organization data in token is invalid or missing"""
    
    def __init__(
        self, 
        message: str = "Invalid or missing organization information",
        organization_id: Optional[str] = None,
        validation_error: Optional[str] = None
    ):
        details = {
            "organization_id": organization_id,
            "validation_error": validation_error
        }
        super().__init__(
            message=message,
            error_code="INVALID_ORGANIZATION",
            details=details
        )


class ClerkAPIError(AdminAuthenticationError):
    """Raised when Clerk API calls fail"""
    
    def __init__(
        self, 
        message: str = "Clerk API error",
        api_endpoint: Optional[str] = None,
        status_code: Optional[int] = None,
        response_body: Optional[str] = None
    ):
        details = {
            "api_endpoint": api_endpoint,
            "status_code": status_code,
            "response_body": response_body
        }
        super().__init__(
            message=message,
            error_code="CLERK_API_ERROR",
            details=details
        )


class InsufficientPermissionsError(AdminAuthenticationError):
    """Raised when user has valid organization membership but insufficient admin permissions"""
    
    def __init__(
        self, 
        message: str = "Insufficient admin permissions",
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        required_role: Optional[str] = None,
        user_role: Optional[str] = None
    ):
        details = {
            "user_id": user_id,
            "organization_id": organization_id,
            "required_role": required_role,
            "user_role": user_role
        }
        super().__init__(
            message=message,
            error_code="INSUFFICIENT_PERMISSIONS",
            details=details
        )