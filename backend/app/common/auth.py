# -*- coding: utf-8 -*-
"""
Authentication utilities for Clerk integration

本番環境対応のJWT署名検証を実装:
- Clerk JWKSエンドポイントからの公開鍵取得
- RS256アルゴリズムによる署名検証
- トークン有効期限の検証
- 公開鍵のキャッシュ機能
"""
import jwt
from jwt import PyJWKClient, PyJWKClientError
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
import logging
import time

from app.core.config import settings

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)

# JWKSのキャッシュ有効期限（秒）
JWKS_CACHE_TTL = 3600  # 1時間


def _get_clerk_jwks_url() -> str:
    """
    Clerk JWKSエンドポイントURLを取得

    Clerk Publishable Keyから Frontend API URLを構築
    例: pk_test_xxx -> https://xxx.clerk.accounts.dev/.well-known/jwks.json
    """
    # まず環境変数から直接取得を試みる（最優先）
    if settings.clerk_frontend_api:
        jwks_url = f"https://{settings.clerk_frontend_api}/.well-known/jwks.json"
        logger.info(f"🔑 [AUTH] Using CLERK_FRONTEND_API: {jwks_url}")
        return jwks_url

    if not settings.clerk_publishable_key:
        raise ValueError("CLERK_PUBLISHABLE_KEY is not set")

    # Publishable keyからフロントエンドAPIを抽出
    # pk_test_xxxx or pk_live_xxxx 形式
    try:
        import base64
        # pk_test_ または pk_live_ プレフィックスを除去
        key_part = settings.clerk_publishable_key.replace("pk_test_", "").replace("pk_live_", "")

        # Base64デコード（パディング調整）
        # 必要に応じてパディングを追加
        padding_needed = 4 - (len(key_part) % 4)
        if padding_needed != 4:
            key_part += "=" * padding_needed

        decoded = base64.b64decode(key_part).decode("utf-8")

        # 末尾の $ を除去
        frontend_api = decoded.rstrip("$")

        if not frontend_api:
            raise ValueError("Decoded frontend API is empty")

        jwks_url = f"https://{frontend_api}/.well-known/jwks.json"
        logger.info(f"🔑 [AUTH] Decoded Clerk Frontend API: {jwks_url}")
        return jwks_url

    except Exception as e:
        logger.error(f"🔑 [AUTH] Could not decode publishable key: {e}")
        raise ValueError(f"Could not determine Clerk Frontend API URL: {e}")


class CachedJWKClient:
    """
    キャッシュ機能付きJWKクライアント

    JWKSの取得をキャッシュし、パフォーマンスを最適化
    """

    def __init__(self, jwks_url: str, cache_ttl: int = JWKS_CACHE_TTL):
        self.jwks_url = jwks_url
        self.cache_ttl = cache_ttl
        self._client: Optional[PyJWKClient] = None
        self._last_refresh: float = 0

    def _should_refresh(self) -> bool:
        """キャッシュの更新が必要かどうか"""
        return time.time() - self._last_refresh > self.cache_ttl

    def get_signing_key(self, token: str):
        """
        トークンから署名検証用の鍵を取得

        キャッシュが古い場合は自動的に更新
        """
        if self._client is None or self._should_refresh():
            try:
                self._client = PyJWKClient(self.jwks_url, cache_keys=True)
                self._last_refresh = time.time()
                logger.info("🔑 [AUTH] Refreshed JWKS from Clerk")
            except Exception as e:
                logger.error(f"🔑 [AUTH] Failed to fetch JWKS: {e}")
                raise

        return self._client.get_signing_key_from_jwt(token)


# グローバルJWKクライアント（遅延初期化）
_jwk_client: Optional[CachedJWKClient] = None


def _get_jwk_client() -> CachedJWKClient:
    """JWKクライアントを取得（シングルトン）"""
    global _jwk_client
    if _jwk_client is None:
        jwks_url = _get_clerk_jwks_url()
        _jwk_client = CachedJWKClient(jwks_url)
    return _jwk_client


def verify_clerk_token(token: str) -> dict:
    """
    Clerk JWTトークンを検証

    Args:
        token: Bearer トークン

    Returns:
        デコードされたトークンペイロード

    Raises:
        HTTPException: トークンが無効な場合
    """
    try:
        # JWKクライアントから署名鍵を取得
        jwk_client = _get_jwk_client()
        signing_key = jwk_client.get_signing_key(token)

        # トークンを検証・デコード
        decoded = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            options={
                "verify_signature": True,
                "verify_exp": True,  # 有効期限を検証
                "verify_iat": True,  # 発行時刻を検証
                "require": ["exp", "iat", "sub"],  # 必須クレーム
            }
        )

        user_id = decoded.get('sub', 'unknown')
        logger.info(f"🔒 [AUTH] Token verified successfully for user: {user_id}")
        logger.info(f"🔒 [AUTH] JWT claims: iss={decoded.get('iss')}, azp={decoded.get('azp')}, exp={decoded.get('exp')}")
        return decoded

    except jwt.ExpiredSignatureError:
        logger.warning("🔒 [AUTH] Token has expired")
        raise HTTPException(status_code=401, detail="Token has expired")

    except jwt.InvalidTokenError as e:
        logger.error(f"🔒 [AUTH] Invalid token: {e}")
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")

    except PyJWKClientError as e:
        logger.error(f"🔒 [AUTH] JWKS fetch error: {e}")
        raise HTTPException(status_code=503, detail="Authentication service temporarily unavailable")

    except Exception as e:
        logger.error(f"🔒 [AUTH] Unexpected authentication error: {e}")
        raise HTTPException(status_code=500, detail="Authentication error")


def get_current_user_id_from_token(
    authorization: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> str:
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
        raise HTTPException(status_code=401, detail="Authorization header required")

    try:
        token = authorization.credentials
        logger.info(f"🔒 [AUTH] Processing JWT token, length: {len(token)}")

        # トークンを検証
        decoded_token = verify_clerk_token(token)
        logger.debug(f"🔒 [AUTH] JWT decoded successfully, keys: {list(decoded_token.keys())}")

        # Extract user ID from token
        user_id = decoded_token.get("sub")
        if not user_id:
            logger.warning("🔒 [AUTH] JWT token has no user ID in 'sub' field")
            logger.info(f"🔒 [AUTH] Available fields in JWT: {list(decoded_token.keys())}")
            # Try alternative fields that Clerk might use
            user_id = (
                decoded_token.get("user_id") or
                decoded_token.get("clerk_user_id") or
                decoded_token.get("userId")
            )
            if user_id:
                logger.info(f"🔒 [AUTH] Found user ID in alternative field: {user_id}")
                return user_id

            # No fallbacks - require valid user ID
            logger.error("🔒 [AUTH] Could not extract user ID from JWT token")
            raise HTTPException(status_code=401, detail="Invalid token: no user ID found")

        logger.info(f"🔒 [AUTH] Successfully extracted user ID: {user_id}")
        return user_id

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except jwt.InvalidTokenError as e:
        logger.error(f"🔒 [AUTH] Invalid JWT token: {e}")
        raise HTTPException(status_code=401, detail=f"Invalid JWT token: {e}")
    except Exception as e:
        logger.error(f"🔒 [AUTH] Unexpected error during authentication: {e}")
        logger.exception("🔒 [AUTH] Full exception details:")
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

        # トークンを検証
        decoded_token = verify_clerk_token(token)

        # Extract user ID from token
        user_id = decoded_token.get("sub")
        if not user_id:
            logger.warning("🔒 [AUTH] No user ID in token 'sub' field")
            # Try alternative fields that Clerk might use
            user_id = (
                decoded_token.get("user_id") or
                decoded_token.get("clerk_user_id") or
                decoded_token.get("userId")
            )
            if not user_id:
                logger.error("🔒 [AUTH] Could not extract user ID from JWT token")
                raise ValueError("Invalid token: no user ID found")

        logger.info(f"🔒 [AUTH] Successfully extracted user ID from header: {user_id}")
        return user_id

    except HTTPException as e:
        # Convert HTTPException to ValueError for WebSocket compatibility
        raise ValueError(e.detail)
    except Exception as e:
        logger.error(f"🔒 [AUTH] Error extracting user ID from header: {e}")
        raise ValueError(f"Authentication error: {e}")


# Optional: トークン検証ユーティリティ（テスト用）
def validate_token_without_signature(token: str) -> dict:
    """
    署名検証なしでトークンをデコード（デバッグ・テスト用）

    ⚠️ 本番環境では使用しないこと
    """
    logger.warning("⚠️ [AUTH] validate_token_without_signature called - FOR TESTING ONLY")
    return jwt.decode(token, options={"verify_signature": False})
