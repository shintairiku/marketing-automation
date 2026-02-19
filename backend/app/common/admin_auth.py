# -*- coding: utf-8 -*-
"""
Admin authentication utilities for @shintairiku.jp email domain check

管理者認証は通常のJWT検証に加えて、メールドメインの検証を行う
"""
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
import logging
import httpx

from app.core.config import settings
from app.common.auth import verify_clerk_token

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)

# デフォルト管理者ドメイン（常に許可）
DEFAULT_ADMIN_DOMAIN = '@shintairiku.jp'


def _get_allowed_emails() -> set[str]:
    """環境変数から許可されたメールアドレスのセットを取得"""
    raw = settings.admin_allowed_emails
    if not raw:
        return set()
    return {e.strip().lower() for e in raw.split(',') if e.strip()}


def _get_allowed_domains() -> set[str]:
    """環境変数から許可されたドメインのセットを取得（デフォルトドメイン含む）"""
    domains = {DEFAULT_ADMIN_DOMAIN.lower()}
    raw = settings.admin_allowed_domains
    if raw:
        for d in raw.split(','):
            d = d.strip().lower()
            if d:
                # @ が付いていなければ付与
                if not d.startswith('@'):
                    d = f'@{d}'
                domains.add(d)
    return domains


def is_admin_email(email: Optional[str]) -> bool:
    """Check if email is allowed admin access (domain match or explicit allowlist)"""
    if not email:
        return False
    email_lower = email.lower()
    # 1. 明示的なメール許可リスト
    if email_lower in _get_allowed_emails():
        return True
    # 2. ドメイン許可リスト（@shintairiku.jp + 環境変数追加分）
    for domain in _get_allowed_domains():
        if email_lower.endswith(domain):
            return True
    return False

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
            
    except HTTPException:
        # HTTPExceptionはそのまま再送出
        raise
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
        logger.info("🔒 [ADMIN_AUTH] Processing JWT token for admin check")

        # 共通のJWT検証関数を使用（署名検証あり）
        decoded_token = verify_clerk_token(token)

        # デバッグ: JWTの内容をログ出力
        user_id_from_jwt = decoded_token.get("sub")
        logger.info(f"🔒 [ADMIN_AUTH] JWT verified, user_id from 'sub': {user_id_from_jwt}")
        logger.info(f"🔒 [ADMIN_AUTH] JWT claims: iss={decoded_token.get('iss')}, azp={decoded_token.get('azp')}")
        logger.info(f"🔒 [ADMIN_AUTH] Decoded JWT token keys: {list(decoded_token.keys())}")
        
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
                detail="Admin access required. Your email is not authorized."
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

