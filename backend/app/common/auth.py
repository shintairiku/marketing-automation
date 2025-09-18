# -*- coding: utf-8 -*-
"""
Authentication utilities for Clerk integration
"""
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
import logging

from app.domains.admin.auth.clerk_validator import ClerkOrganizationValidator, AdminUser
from app.domains.admin.auth.exceptions import (
    AdminAuthenticationError,
    InvalidJWTTokenError,
    OrganizationMembershipRequiredError
)

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)

def get_current_user_id_from_token(authorization: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> str:
    """
    Extract user ID from Clerk JWT token
    
    Args:
        authorization: Authorization header with Bearer token
        
    Returns:
        User ID from Clerk
        
    Raises:
        HTTPException: If token is invalid or missing
    """
    # Require authorization header - no fallbacks
    if not authorization:
        logger.error("🔒 [AUTH] No authorization header found - authentication required")
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Authorization header required")
    
    try:
        token = authorization.credentials
        logger.info(f"🔒 [AUTH] Processing JWT token, length: {len(token)}, first 20 chars: {token[:20]}...")
        
        # Decode the JWT token without verification for now (for development)
        # In production, you should verify the token with Clerk's public key
        decoded_token = jwt.decode(token, options={"verify_signature": False})
        logger.info(f"🔒 [AUTH] JWT decoded successfully, keys: {list(decoded_token.keys())}")
        
        # Extract user ID from token
        user_id = decoded_token.get("sub")
        if not user_id:
            logger.warning("🔒 [AUTH] JWT token has no user ID in 'sub' field")
            logger.info(f"🔒 [AUTH] Available fields in JWT: {list(decoded_token.keys())}")
            # Try alternative fields that Clerk might use
            user_id = decoded_token.get("user_id") or decoded_token.get("clerk_user_id") or decoded_token.get("userId")
            if user_id:
                logger.info(f"🔒 [AUTH] Found user ID in alternative field: {user_id}")
                return user_id
            
            # No fallbacks - require valid user ID
            logger.error("🔒 [AUTH] Could not extract user ID from JWT token")
            from fastapi import HTTPException
            raise HTTPException(status_code=401, detail="Invalid token: no user ID found")
        
        logger.info(f"🔒 [AUTH] Successfully extracted user ID: {user_id}")
        return user_id
        
    except jwt.InvalidTokenError as e:
        logger.error(f"🔒 [AUTH] Invalid JWT token: {e}")
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail=f"Invalid JWT token: {e}")
    except Exception as e:
        logger.error(f"🔒 [AUTH] Unexpected error during authentication: {e}")
        logger.exception("🔒 [AUTH] Full exception details:")
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=f"Authentication error: {e}")

def get_current_user_id_from_header(authorization: Optional[str] = None) -> str:
    """
    Extract user ID from Authorization header string
    Used for WebSocket connections where we can't use Depends
    
    Args:
        authorization: Authorization header value
        
    Returns:
        User ID from Clerk
        
    Raises:
        ValueError: If authorization header is missing or invalid
    """
    if not authorization:
        logger.error("🔒 [AUTH] No authorization header found - authentication required")
        raise ValueError("Authorization header required")
    
    try:
        # Remove "Bearer " prefix
        if authorization.startswith("Bearer "):
            token = authorization[7:]
        else:
            token = authorization
            
        # Decode the JWT token without verification for now (for development)
        decoded_token = jwt.decode(token, options={"verify_signature": False})
        
        # Extract user ID from token
        user_id = decoded_token.get("sub")
        if not user_id:
            logger.warning("🔒 [AUTH] No user ID in token 'sub' field")
            # Try alternative fields that Clerk might use
            user_id = decoded_token.get("user_id") or decoded_token.get("clerk_user_id") or decoded_token.get("userId")
            if not user_id:
                logger.error("🔒 [AUTH] Could not extract user ID from JWT token")
                raise ValueError("Invalid token: no user ID found")
        
        logger.info(f"🔒 [AUTH] Successfully extracted user ID from header: {user_id}")        
        return user_id
        
    except Exception as e:
        logger.error(f"🔒 [AUTH] Error extracting user ID from header: {e}")
        raise ValueError(f"Authentication error: {e}")


# ===== ADMIN AUTHENTICATION FUNCTIONS =====

# Initialize admin validator
_admin_validator = None

def get_admin_validator() -> ClerkOrganizationValidator:
    """Get or create the admin validator singleton"""
    global _admin_validator
    if _admin_validator is None:
        _admin_validator = ClerkOrganizationValidator()
    return _admin_validator


def get_current_admin_user(authorization: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> AdminUser:
    """
    Extract and validate admin user from Clerk JWT token with organization membership verification.
    
    This function performs comprehensive admin authentication:
    1. Validates JWT token structure and signature
    2. Extracts organization membership data from token claims
    3. Verifies membership in the admin organization
    4. Validates admin permissions within the organization
    
    Args:
        authorization: Authorization header with Bearer token
        
    Returns:
        AdminUser object with validated admin access and organization membership
        
    Raises:
        HTTPException: If token is invalid, user lacks admin organization membership, 
                      or has insufficient permissions
    """
    if not authorization:
        logger.error("🛡️  [ADMIN_AUTH] No authorization header found - admin authentication required")
        raise HTTPException(
            status_code=401, 
            detail="Admin authorization header required"
        )
    
    try:
        token = authorization.credentials
        logger.info(f"🛡️  [ADMIN_AUTH] Validating admin token for user authentication")
        
        validator = get_admin_validator()
        admin_user = validator.validate_token_and_extract_admin_user(token)
        
        logger.info(f"✅ [ADMIN_AUTH] Admin authentication successful")
        logger.info(f"   User ID: {admin_user.user_id}")
        logger.info(f"   Email: {admin_user.email}")
        logger.info(f"   Admin Org: {admin_user.admin_organization_membership.organization_id}")
        logger.info(f"   Role: {admin_user.admin_organization_membership.role}")
        
        return admin_user
        
    except InvalidJWTTokenError as e:
        logger.error(f"❌ [ADMIN_AUTH] Invalid JWT token: {e.message}")
        raise HTTPException(
            status_code=401, 
            detail=f"Invalid admin token: {e.message}"
        )
        
    except OrganizationMembershipRequiredError as e:
        logger.error(f"❌ [ADMIN_AUTH] Organization membership required: {e.message}")
        logger.error(f"   User organizations: {e.details.get('user_organizations', [])}")
        logger.error(f"   Required organization: {e.details.get('required_organization_id')}")
        raise HTTPException(
            status_code=403, 
            detail="Admin organization membership required"
        )
        
    except AdminAuthenticationError as e:
        logger.error(f"❌ [ADMIN_AUTH] Admin authentication error: {e.message}")
        logger.error(f"   Error code: {e.error_code}")
        logger.error(f"   Details: {e.details}")
        
        # Map admin errors to HTTP status codes
        status_code = 403 if e.error_code == "INSUFFICIENT_PERMISSIONS" else 401
        raise HTTPException(
            status_code=status_code, 
            detail=e.message
        )
        
    except Exception as e:
        logger.error(f"❌ [ADMIN_AUTH] Unexpected admin authentication error: {e}")
        logger.exception("[ADMIN_AUTH] Full exception details:")
        raise HTTPException(
            status_code=500, 
            detail="Admin authentication system error"
        )


def get_current_admin_user_id(authorization: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> str:
    """
    Extract admin user ID from validated admin token.
    
    Args:
        authorization: Authorization header with Bearer token
        
    Returns:
        User ID of authenticated admin user
        
    Raises:
        HTTPException: If admin authentication fails
    """
    admin_user = get_current_admin_user(authorization)
    return admin_user.user_id


def verify_admin_organization_membership(token: str) -> bool:
    """
    Verify if a JWT token belongs to a user with admin organization membership.
    
    Args:
        token: JWT token string
        
    Returns:
        True if user has valid admin organization membership, False otherwise
    """
    try:
        validator = get_admin_validator()
        validator.validate_token_and_extract_admin_user(token)
        return True
    except Exception as e:
        logger.debug(f"🔍 [ADMIN_AUTH] Admin membership verification failed: {e}")
        return False


def get_user_admin_organizations(token: str) -> list:
    """
    Get list of organizations where the user has admin privileges.
    
    Args:
        token: JWT token string
        
    Returns:
        List of organization IDs where user has admin access
    """
    try:
        validator = get_admin_validator()
        organizations = validator.get_user_organizations(token)
        
        # For now, return all organizations since we're primarily checking admin org membership
        # In the future, this could be enhanced to check admin roles in multiple organizations
        return organizations
    except Exception as e:
        logger.error(f"❌ [ADMIN_AUTH] Error getting user admin organizations: {e}")
        return []