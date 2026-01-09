# -*- coding: utf-8 -*-
"""
Admin authentication utilities for @shintairiku.jp email domain check
"""
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
import logging
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)

# Admin email domain
ADMIN_EMAIL_DOMAIN = '@shintairiku.jp'

def is_admin_email(email: Optional[str]) -> bool:
    """Check if email belongs to admin domain"""
    if not email:
        return False
    return email.lower().endswith(ADMIN_EMAIL_DOMAIN.lower())

async def get_user_email_from_clerk_api(user_id: str) -> str:
    """
    Get user email from Clerk API using user ID
    
    Args:
        user_id: Clerk user ID
        
    Returns:
        User email address
        
    Raises:
        HTTPException: If user not found or API error
    """
    try:
        clerk_secret_key = settings.clerk_secret_key
        if not clerk_secret_key:
            logger.error("🔒 [ADMIN_AUTH] Clerk secret key not configured")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Server configuration error"
            )
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"https://api.clerk.com/v1/users/{user_id}",
                headers={
                    "Authorization": f"Bearer {clerk_secret_key}",
                    "Content-Type": "application/json"
                }
            )
            
            if response.status_code == 404:
                logger.warning(f"🔒 [ADMIN_AUTH] User not found in Clerk: {user_id}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found"
                )
            
            response.raise_for_status()
            user_data = response.json()
            
            # Extract primary email
            email_addresses = user_data.get("email_addresses", [])
            if not email_addresses:
                logger.warning(f"🔒 [ADMIN_AUTH] No email addresses found for user: {user_id}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="No email address found for user"
                )
            
            # Find primary email or use first email
            primary_email = None
            for email_addr in email_addresses:
                if email_addr.get("id") == user_data.get("primary_email_address_id"):
                    primary_email = email_addr
                    break
            
            if not primary_email:
                primary_email = email_addresses[0]
            
            email = primary_email.get("email_address")
            if not email:
                logger.warning(f"🔒 [ADMIN_AUTH] No email address in primary email for user: {user_id}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid email address"
                )
            
            logger.info(f"🔒 [ADMIN_AUTH] Retrieved email from Clerk API: {email}")
            return email
            
    except httpx.HTTPStatusError as e:
        logger.error(f"🔒 [ADMIN_AUTH] Clerk API error: {e.response.status_code} - {e.response.text}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service error"
        )
    except Exception as e:
        logger.error(f"🔒 [ADMIN_AUTH] Error fetching user from Clerk API: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service error"
        )

async def get_admin_user_email_from_token(
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
        
        logger.info(f"🔒 [ADMIN_AUTH] Decoded JWT token keys: {list(decoded_token.keys())}")
        logger.info(f"🔒 [ADMIN_AUTH] Decoded JWT token (first 500 chars): {str(decoded_token)[:500]}")
        
        # Extract user_id from token - Clerk JWT has 'sub' field
        user_id = decoded_token.get("sub")
        if not user_id:
            logger.warning("🔒 [ADMIN_AUTH] JWT token has no sub field")
            logger.info(f"🔒 [ADMIN_AUTH] Available fields in JWT: {list(decoded_token.keys())}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: no user ID found"
            )
        
        # Get email from Clerk API using user_id
        email = await get_user_email_from_clerk_api(user_id)
        
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

