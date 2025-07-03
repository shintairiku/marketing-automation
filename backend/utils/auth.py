from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import httpx
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Clerkの設定
CLERK_SECRET_KEY = os.getenv("CLERK_SECRET_KEY")
CLERK_PEM_PUBLIC_KEY = os.getenv("CLERK_PEM_PUBLIC_KEY") 

security = HTTPBearer()

async def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """JWTトークンからユーザーIDを取得"""
    try:
        token = credentials.credentials
        
        # Clerkの公開エンドポイントを使用してトークンを検証
        # 本番環境では適切なJWT検証ライブラリを使用することを推奨
        async with httpx.AsyncClient() as client:
            headers = {
                "Authorization": f"Bearer {CLERK_SECRET_KEY}",
                "Content-Type": "application/json"
            }
            
            # ClerkのAPI経由でトークンを検証
            response = await client.get(
                f"https://api.clerk.com/v1/sessions/{token}",
                headers=headers
            )
            
            if response.status_code == 200:
                session_data = response.json()
                user_id = session_data.get("user_id")
                if user_id:
                    return user_id
            
        # Fallback: トークンから直接ユーザーIDを抽出（デモ用）
        # 実際の本番環境では適切なJWT検証を実装してください
        return extract_user_id_from_token(token)
        
    except Exception as e:
        logger.error(f"Failed to get user ID from token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

def extract_user_id_from_token(token: str) -> str:
    """トークンからユーザーIDを抽出（簡易実装）"""
    try:
        # JWTトークンをデコード（実際の本番環境では適切な検証が必要）
        import jwt
        
        # トークンをデコード（検証なし - デモ用）
        decoded = jwt.decode(token, options={"verify_signature": False})
        
        # Clerkのトークン構造に基づいてuser_idを取得
        user_id = decoded.get("sub")
        
        if not user_id:
            raise ValueError("User ID not found in token")
            
        return user_id
        
    except Exception as e:
        logger.error(f"Failed to extract user ID from token: {e}")
        # デモ用のフォールバック（本番環境では使用しない）
        return "demo_user_123"

def get_optional_user_id(credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))) -> Optional[str]:
    """オプショナルなユーザーID取得（認証が不要な場合に使用）"""
    if not credentials:
        return None
    
    try:
        return extract_user_id_from_token(credentials.credentials)
    except:
        return None