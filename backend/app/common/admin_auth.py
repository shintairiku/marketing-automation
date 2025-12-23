# -*- coding: utf-8 -*-
"""
Admin authentication utilities for @shintairiku.jp email domain check
"""
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
import logging

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)

# Admin email domain
ADMIN_EMAIL_DOMAIN = '@shintairiku.jp'

def is_admin_email(email: Optional[str]) -> bool:
    """Check if email belongs to admin domain"""
    if not email:
        return False
    return email.lower().endswith(ADMIN_EMAIL_DOMAIN.lower())

def get_admin_user_email_from_token(
    authorization: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> str:
    """
    Extract user email from Clerk JWT token and verify admin access
    
    Args:
        authorization: Authorization header with Bearer token
        
    Returns:
        User email address
        
    Raises:
        HTTPException: If token is invalid, missing, or user is not admin
    """
    if not authorization:
        logger.error("🔒 [ADMIN_AUTH] No authorization header found")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required"
        )
    
    try:
        token = authorization.credentials
        logger.info(f"🔒 [ADMIN_AUTH] Processing JWT token for admin check")
        
        # Decode the JWT token without verification for now (for development)
        # In production, you should verify the token with Clerk's public key
        decoded_token = jwt.decode(token, options={"verify_signature": False})
        
        # Extract email from token
        email = decoded_token.get("email")
        if not email:
            logger.warning("🔒 [ADMIN_AUTH] JWT token has no email field")
            logger.info(f"🔒 [ADMIN_AUTH] Available fields in JWT: {list(decoded_token.keys())}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: no email found"
            )
        
        # Check admin email domain
        if not is_admin_email(email):
            logger.warning(f"🔒 [ADMIN_AUTH] Access denied for email: {email}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required. Only @shintairiku.jp email addresses are allowed."
            )
        
        logger.info(f"🔒 [ADMIN_AUTH] Admin access granted for: {email}")
        return email
        
    except HTTPException:
        raise
    except jwt.InvalidTokenError as e:
        logger.error(f"🔒 [ADMIN_AUTH] Invalid JWT token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid JWT token: {e}"
        )
    except Exception as e:
        logger.error(f"🔒 [ADMIN_AUTH] Unexpected error during admin authentication: {e}")
        logger.exception("🔒 [ADMIN_AUTH] Full exception details:")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Authentication error: {e}"
        )

