# -*- coding: utf-8 -*-
"""
Admin/Privileged authentication using Clerk publicMetadata roles.

認証フロー:
1. JWT の metadata.role クレームを確認（最速、API不要）
2. role が見つからない場合は Clerk API でメールドメインを確認（移行期間のフォールバック）

ロール体系:
- admin: 管理者ダッシュボード + 全特権機能
- privileged: 未公開機能（SEO/Dashboard等）、サブスク不要
- None/未設定: 一般ユーザー
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
import logging
import httpx

from app.core.config import settings
from app.common.auth import verify_clerk_token

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)

# 有効なロール値
VALID_ROLES = {"admin", "privileged"}

# フォールバック用: 移行期間中のメールドメインチェック
ADMIN_EMAIL_DOMAIN = '@shintairiku.jp'


def _extract_role_from_jwt(decoded_token: dict) -> Optional[str]:
    """
    JWT claims から role を抽出。

    Clerk session token のカスタマイズで以下を設定:
    { "metadata": "{{user.public_metadata}}" }

    これにより decoded_token["metadata"]["role"] にアクセス可能。
    """
    metadata = decoded_token.get("metadata")
    if isinstance(metadata, dict):
        role = metadata.get("role")
        if role in VALID_ROLES:
            return role
    return None


def is_admin_email(email: Optional[str]) -> bool:
    """Check if email belongs to admin domain (fallback only)"""
    if not email:
        return False
    return email.lower().endswith(ADMIN_EMAIL_DOMAIN.lower())


async def get_user_email_from_clerk_api(user_id: str) -> str:
    """
    Clerk API からユーザーのメールアドレスを取得。
    検証済みのプライマリメールのみを返す。
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

            # Find primary email
            primary_email = None
            for email_addr in email_addresses:
                if email_addr.get("id") == user_data.get("primary_email_address_id"):
                    # 検証済みメールのみ受け入れ
                    verification = email_addr.get("verification", {})
                    if verification.get("status") == "verified":
                        primary_email = email_addr
                    break

            if not primary_email:
                # プライマリが未検証の場合、検証済みメールの中から探す
                for email_addr in email_addresses:
                    verification = email_addr.get("verification", {})
                    if verification.get("status") == "verified":
                        primary_email = email_addr
                        break

            if not primary_email:
                logger.warning(f"🔒 [ADMIN_AUTH] No verified email found for user: {user_id}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="No verified email address found"
                )

            email = primary_email.get("email_address")
            if not email:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid email address"
                )

            logger.info(f"🔒 [ADMIN_AUTH] Retrieved verified email from Clerk API: {email}")
            return email

    except HTTPException:
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


async def _verify_token_and_extract(
    authorization: Optional[HTTPAuthorizationCredentials],
) -> tuple[dict, str]:
    """共通: トークン検証 + user_id 抽出"""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required"
        )

    token = authorization.credentials
    decoded_token = verify_clerk_token(token)

    user_id = decoded_token.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: no user ID found"
        )

    return decoded_token, user_id


async def get_admin_user_from_token(
    authorization: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> dict:
    """
    管理者認証: admin ロールを要求。

    Returns:
        dict with keys: user_id, role, email (email is optional)
    """
    decoded_token, user_id = await _verify_token_and_extract(authorization)

    # 第1優先: JWT claims の role
    role = _extract_role_from_jwt(decoded_token)
    if role == "admin":
        logger.info(f"🔒 [ADMIN_AUTH] Admin access granted via JWT role for user: {user_id}")
        return {"user_id": user_id, "role": "admin"}

    if role == "privileged":
        # privileged は admin ではない
        logger.warning(f"🔒 [ADMIN_AUTH] Privileged user {user_id} attempted admin access")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    # フォールバック: Clerk API でメールドメインチェック（移行期間）
    try:
        email = await get_user_email_from_clerk_api(user_id)
        if is_admin_email(email):
            logger.info(f"🔒 [ADMIN_AUTH] Admin access granted via email fallback for: {email}")
            return {"user_id": user_id, "role": "admin", "email": email}
    except HTTPException:
        pass

    logger.warning(f"🔒 [ADMIN_AUTH] Access denied for user: {user_id}")
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Admin access required"
    )


async def get_privileged_user_from_token(
    authorization: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> dict:
    """
    特権認証: admin または privileged ロールを要求。

    Returns:
        dict with keys: user_id, role
    """
    decoded_token, user_id = await _verify_token_and_extract(authorization)

    # 第1優先: JWT claims の role
    role = _extract_role_from_jwt(decoded_token)
    if role in ("admin", "privileged"):
        logger.info(f"🔒 [ADMIN_AUTH] Privileged access granted via JWT role '{role}' for user: {user_id}")
        return {"user_id": user_id, "role": role}

    # フォールバック: Clerk API でメールドメインチェック（移行期間）
    try:
        email = await get_user_email_from_clerk_api(user_id)
        if is_admin_email(email):
            logger.info(f"🔒 [ADMIN_AUTH] Privileged access granted via email fallback for: {email}")
            return {"user_id": user_id, "role": "admin", "email": email}
    except HTTPException:
        pass

    logger.warning(f"🔒 [ADMIN_AUTH] Privileged access denied for user: {user_id}")
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Privileged access required"
    )


# 後方互換性: 旧 get_admin_user_email_from_token の代替
async def get_admin_user_email_from_token(
    authorization: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> str:
    """
    後方互換: 管理者メールアドレスを返す。
    既存の admin エンドポイントが email: str を期待しているため維持。

    新規コードは get_admin_user_from_token を使用すること。
    """
    result = await get_admin_user_from_token(authorization)
    # email がある場合はそれを返す、なければ user_id を返す
    return result.get("email", result["user_id"])
