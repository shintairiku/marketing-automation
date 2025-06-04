# -*- coding: utf-8 -*-
"""
Clerk認証とSupabase統合のための認証システム
"""
import jwt
import httpx
import asyncio
from typing import Optional, Dict, Any, Union
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import create_client, Client as SupabaseClient
from core.config import settings
import logging

logger = logging.getLogger(__name__)

# Supabaseクライアント（サービスロール）
supabase_service_client: SupabaseClient = create_client(
    settings.supabase_url,
    settings.supabase_service_role_key
)

# HTTPBearer認証スキーム
security = HTTPBearer()

class ClerkJWTPayload:
    """Clerk JWTペイロードを表すクラス"""
    def __init__(self, payload: Dict[str, Any]):
        self.payload = payload
        self.user_id = payload.get('sub')
        self.session_id = payload.get('sid')
        self.organization_id = payload.get('org_id')
        self.organization_role = payload.get('org_role')
        self.organization_slug = payload.get('org_slug')
        self.organization_permissions = payload.get('org_permissions', [])
        
    @property
    def is_organization_context(self) -> bool:
        """組織コンテキストかどうか"""
        return self.organization_id is not None
        
    @property
    def is_organization_owner(self) -> bool:
        """組織のオーナーかどうか"""
        return self.organization_role == 'org:admin' or 'org:admin' in self.organization_permissions
        
    @property
    def is_organization_admin(self) -> bool:
        """組織の管理者かどうか"""
        return self.organization_role in ['org:admin', 'org:member'] and 'org:admin' in self.organization_permissions

# Clerk公開キーキャッシュ
_clerk_public_keys: Optional[Dict[str, Any]] = None
_keys_cache_timestamp: float = 0
KEYS_CACHE_DURATION = 3600  # 1時間

async def get_clerk_public_keys() -> Dict[str, Any]:
    """ClerkのJWKS公開キーを取得（キャッシュ付き）"""
    global _clerk_public_keys, _keys_cache_timestamp
    
    current_time = asyncio.get_event_loop().time()
    
    # キャッシュが有効かチェック
    if _clerk_public_keys and (current_time - _keys_cache_timestamp) < KEYS_CACHE_DURATION:
        return _clerk_public_keys
    
    try:
        # Clerk JWKS エンドポイントから公開キーを取得
        async with httpx.AsyncClient() as client:
            # Clerk Instance URLから推定（実際の環境では適切なURLに変更）
            jwks_url = "https://clerk.dev/.well-known/jwks.json"
            response = await client.get(jwks_url)
            response.raise_for_status()
            
            jwks_data = response.json()
            _clerk_public_keys = jwks_data
            _keys_cache_timestamp = current_time
            
            logger.info("Clerk公開キーを更新しました")
            return jwks_data
            
    except Exception as e:
        logger.error(f"Clerk公開キーの取得に失敗しました: {e}")
        if _clerk_public_keys:
            # キャッシュされた古いキーを返す
            logger.warning("キャッシュされた古い公開キーを使用します")
            return _clerk_public_keys
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="認証サービスに接続できません"
        )

async def verify_clerk_jwt(token: str) -> ClerkJWTPayload:
    """Clerk JWTトークンを検証"""
    try:
        # ヘッダーをデコードしてkidを取得
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get('kid')
        
        if not kid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="無効なJWTヘッダー"
            )
        
        # 公開キーを取得
        jwks = await get_clerk_public_keys()
        
        # 対応する公開キーを検索
        public_key = None
        for key in jwks.get('keys', []):
            if key.get('kid') == kid:
                public_key = jwt.algorithms.RSAAlgorithm.from_jwk(key)
                break
        
        if not public_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="対応する公開キーが見つかりません"
            )
        
        # JWTを検証・デコード
        payload = jwt.decode(
            token,
            public_key,
            algorithms=['RS256'],
            options={"verify_exp": True, "verify_iat": True}
        )
        
        return ClerkJWTPayload(payload)
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="トークンの有効期限が切れています"
        )
    except jwt.InvalidTokenError as e:
        logger.warning(f"無効なJWTトークン: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="無効なトークンです"
        )
    except Exception as e:
        logger.error(f"JWT検証エラー: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="認証処理中にエラーが発生しました"
        )

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> ClerkJWTPayload:
    """現在のユーザーを取得（認証が必要なエンドポイント用）"""
    token = credentials.credentials
    return await verify_clerk_jwt(token)

async def get_optional_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Optional[ClerkJWTPayload]:
    """現在のユーザーを取得（認証が任意のエンドポイント用）"""
    if not credentials:
        return None
    return await verify_clerk_jwt(credentials.credentials)

class UserContext:
    """ユーザーコンテキスト（組織含む）"""
    def __init__(self, jwt_payload: ClerkJWTPayload):
        self.jwt_payload = jwt_payload
        self.user_id = jwt_payload.user_id
        self.organization_id = jwt_payload.organization_id
        self.is_organization_context = jwt_payload.is_organization_context
        
    def get_supabase_client(self) -> SupabaseClient:
        """ユーザーコンテキストに応じたSupabaseクライアントを取得"""
        # サービスロールクライアントにRLSコンテキストを設定
        client = supabase_service_client
        
        # RLS用のコンテキスト設定
        headers = {
            'X-User-ID': self.user_id,
        }
        
        if self.organization_id:
            headers['X-Organization-ID'] = self.organization_id
            
        # クライアントのヘッダーを更新
        client.rest.headers.update(headers)
        
        return client
        
    async def check_organization_permission(self, required_role: str = 'member') -> bool:
        """組織での権限をチェック"""
        if not self.is_organization_context:
            return False
            
        role_hierarchy = {
            'member': 0,
            'admin': 1, 
            'owner': 2
        }
        
        user_role_level = role_hierarchy.get(self.jwt_payload.organization_role, 0)
        required_level = role_hierarchy.get(required_role, 0)
        
        return user_role_level >= required_level
        
    async def get_accessible_organizations(self) -> list:
        """ユーザーがアクセス可能な組織一覧を取得"""
        supabase = self.get_supabase_client()
        
        try:
            response = supabase.table('organization_memberships')\
                .select('organization_id, role, organizations(*)')\
                .eq('user_id', self.user_id)\
                .eq('status', 'active')\
                .execute()
                
            return response.data
        except Exception as e:
            logger.error(f"組織情報の取得に失敗: {e}")
            return []

async def get_user_context(jwt_payload: ClerkJWTPayload = Depends(get_current_user)) -> UserContext:
    """ユーザーコンテキストを取得"""
    return UserContext(jwt_payload)

# 組織権限チェック用のデコレータ
def require_organization_role(required_role: str = 'member'):
    """組織での特定の権限を要求するデコレータ"""
    async def check_role(user_context: UserContext = Depends(get_user_context)):
        if not user_context.is_organization_context:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="組織コンテキストが必要です"
            )
            
        if not await user_context.check_organization_permission(required_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"組織での{required_role}権限が必要です"
            )
            
        return user_context
    
    return check_role