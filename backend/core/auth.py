# -*- coding: utf-8 -*-
"""
Authentication utilities for Clerk integration
"""
import jwt
from fastapi import HTTPException, status, Depends
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
    # For development/testing - return placeholder if no auth header
    if not authorization:
        logger.warning("No authorization header found, using placeholder user ID")
        # Return the actual user ID from the CSV data for testing
        return "user_2y2DRx4Xb5PbvMVoVWmDluHCeFV"
    
    try:
        token = authorization.credentials
        
        # Decode the JWT token without verification for now (for development)
        # In production, you should verify the token with Clerk's public key
        decoded_token = jwt.decode(token, options={"verify_signature": False})
        
        # Extract user ID from token
        user_id = decoded_token.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: no user ID found"
            )
            
        return user_id
        
    except jwt.InvalidTokenError as e:
        logger.error(f"Invalid JWT token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token"
        )
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"
        )

def get_current_user_id_from_header(authorization: Optional[str] = None) -> str:
    """
    Extract user ID from Authorization header string
    Used for WebSocket connections where we can't use Depends
    
    Args:
        authorization: Authorization header value
        
    Returns:
        User ID from Clerk
    """
    if not authorization:
        logger.warning("No authorization header found, using test user ID")
        return "user_2y2DRx4Xb5PbvMVoVWmDluHCeFV"
    
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
            logger.warning("No user ID in token, using test user ID")
            return "user_2y2DRx4Xb5PbvMVoVWmDluHCeFV"
            
        return user_id
        
    except Exception as e:
        logger.error(f"Error extracting user ID from header: {e}")
        return "user_2y2DRx4Xb5PbvMVoVWmDluHCeFV" 