# -*- coding: utf-8 -*-
"""
Authentication utilities for Clerk integration
"""
import jwt
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
import logging

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