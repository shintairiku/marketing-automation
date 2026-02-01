# -*- coding: utf-8 -*-
"""
Blog AI Domain - API Endpoints

ブログAI機能のAPIエンドポイント
- WordPress連携（サイト登録・接続テスト）
- ブログ生成（開始・状態取得・ユーザー入力・キャンセル）
- 画像アップロード
"""

import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from app.common.auth import get_current_user_id_from_token
from app.core.config import settings
import logging
from app.domains.blog.schemas import (
    BlogDraftResult,
    BlogGenerationHistoryItem,
    BlogGenerationStartRequest,
    BlogGenerationStateResponse,
    BlogGenerationUserInput,
    WordPressConnectionTestResult,
    WordPressSiteResponse,
    AIQuestionsRequest,
    UserAnswers,
)
from app.domains.blog.services.crypto_service import get_crypto_service
from app.domains.blog.services.image_utils import convert_and_save_as_webp
from app.domains.blog.services.wordpress_mcp_service import (
    WordPressMcpService,
    WordPressMcpClient,
    MCPError,
    clear_mcp_client_cache,
)
from app.domains.blog.services.generation_service import BlogGenerationService
from app.domains.usage.service import usage_service

logger = logging.getLogger(__name__)

router = APIRouter()
security = HTTPBearer(auto_error=False)


# =====================================================
# Supabaseクライアント取得
# =====================================================

def get_supabase_client():
    """Supabaseクライアントを取得（service_role）"""
    from supabase import create_client, Client

    return create_client(
        settings.supabase_url,
        settings.supabase_service_role_key,
    )


# =====================================================
# リクエスト/レスポンスモデル
# =====================================================

class WordPressSiteRegisterRequest(BaseModel):
    """WordPressサイト登録リクエスト（MCP連携コールバック用）"""
    site_url: str = Field(..., description="WordPressサイトURL")
    site_name: Optional[str] = Field(None, description="サイト名")
    mcp_endpoint: str = Field(..., description="MCPエンドポイントURL")
    access_token: str = Field(..., description="アクセストークン")
    api_key: Optional[str] = Field(None, description="APIキー")
    api_secret: Optional[str] = Field(None, description="APIシークレット")
    organization_id: Optional[str] = Field(None, description="紐付ける組織ID（nullで個人サイト）")


class WordPressRegistrationRequest(BaseModel):
    """WordPress MCP登録リクエスト（registration_codeで認証情報を取得）"""
    site_url: str = Field(..., description="WordPressサイトURL")
    site_name: Optional[str] = Field(None, description="サイト名")
    mcp_endpoint: str = Field(..., description="MCPエンドポイントURL")
    register_endpoint: str = Field(..., description="WordPress登録エンドポイント")
    registration_code: str = Field(..., description="登録コード")
    callback_url: Optional[str] = Field(None, description="WordPressコールバックURL")
    organization_id: Optional[str] = Field(None, description="紐付ける組織ID（nullで個人サイト）")


class WordPressSiteOrganizationUpdateRequest(BaseModel):
    """WordPressサイト組織変更リクエスト"""
    organization_id: Optional[str] = Field(None, description="組織ID（nullで個人サイトに変更）")


class WordPressSiteListResponse(BaseModel):
    """WordPressサイト一覧レスポンス"""
    sites: List[WordPressSiteResponse]
    total: int


class ImageUploadResponse(BaseModel):
    """画像アップロードレスポンス"""
    success: bool
    filename: str
    local_path: Optional[str] = None
    message: str


# =====================================================
# 認証ヘルパー
# =====================================================

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    """現在のユーザーIDを取得"""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="認証が必要です",
        )
    return get_current_user_id_from_token(credentials)


def _build_site_response(site: dict, org_name_map: Optional[Dict[str, str]] = None) -> WordPressSiteResponse:
    """サイトデータからWordPressSiteResponseを構築"""
    org_id = site.get("organization_id")
    org_name = None
    if org_id and org_name_map:
        org_name = org_name_map.get(org_id)
    return WordPressSiteResponse(
        id=site["id"],
        site_url=site["site_url"],
        site_name=site.get("site_name"),
        mcp_endpoint=site["mcp_endpoint"],
        connection_status=site["connection_status"],
        is_active=site.get("is_active", False),
        user_id=site.get("user_id"),
        organization_id=org_id,
        organization_name=org_name,
        last_connected_at=site.get("last_connected_at"),
        last_used_at=site.get("last_used_at"),
        last_error=site.get("last_error"),
        created_at=site["created_at"],
        updated_at=site["updated_at"],
    )


def _get_org_name_map(supabase, org_ids: List[str]) -> Dict[str, str]:
    """組織IDリストから {org_id: org_name} マップを取得"""
    if not org_ids:
        return {}
    result = supabase.table("organizations").select("id, name").in_("id", org_ids).execute()
    return {org["id"]: org["name"] for org in (result.data or [])}


def _get_org_site(supabase, site_id: str, user_id: str):
    """組織メンバーとしてWordPressサイトにアクセスできるか確認"""
    org_memberships = supabase.table("organization_members").select(
        "organization_id"
    ).eq("user_id", user_id).execute()

    if org_memberships.data:
        org_ids = [m["organization_id"] for m in org_memberships.data]
        return supabase.table("wordpress_sites").select("*").eq(
            "id", site_id
        ).in_("organization_id", org_ids).execute()

    class EmptyResult:
        data = []
    return EmptyResult()


# =====================================================
# WordPress連携エンドポイント
# =====================================================

@router.get(
    "/connect/wordpress",
    summary="WordPress連携開始（リダイレクト）",
    description="WordPressプラグインからのOAuth風コールバックを受け取り、フロントエンドにリダイレクト",
)
async def connect_wordpress_redirect(
    action: Optional[str] = Query(None),
    site_url: Optional[str] = Query(None),
    site_name: Optional[str] = Query(None),
    mcp_endpoint: Optional[str] = Query(None),
    register_endpoint: Optional[str] = Query(None),
    registration_code: Optional[str] = Query(None),
    callback_url: Optional[str] = Query(None),
):
    """WordPressプラグインからのリクエストをフロントエンドにリダイレクト"""
    from fastapi.responses import RedirectResponse
    import urllib.parse

    logger.info(f"WordPress連携リダイレクト: site_url={site_url}, action={action}")

    # フロントエンドの連携確認ページにリダイレクト
    # クエリパラメータを引き継ぐ
    frontend_url = settings.frontend_url

    params = {
        "site_url": site_url or "",
        "site_name": site_name or "",
        "mcp_endpoint": mcp_endpoint or "",
        "register_endpoint": register_endpoint or "",
        "registration_code": registration_code or "",
        "callback_url": callback_url or "",
    }

    query_string = urllib.parse.urlencode(params)
    redirect_url = f"{frontend_url}/settings/integrations/wordpress/connect?{query_string}"

    return RedirectResponse(url=redirect_url, status_code=302)


@router.post(
    "/connect/wordpress",
    response_model=WordPressSiteResponse,
    summary="WordPress連携コールバック",
    description="WordPressプラグインからの連携コールバックを処理し、サイトを登録",
)
async def connect_wordpress(
    request: WordPressSiteRegisterRequest,
    user_id: str = Depends(get_current_user),
):
    """WordPress MCP連携コールバック"""
    logger.info(f"WordPress連携リクエスト: user={user_id}, site={request.site_url}")

    supabase = get_supabase_client()
    crypto = get_crypto_service()

    # 認証情報を暗号化
    encrypted_credentials = crypto.encrypt({
        "access_token": request.access_token,
        "api_key": request.api_key,
        "api_secret": request.api_secret,
    })

    # リクエストで指定された organization_id を使用（指定なしは個人サイト）
    org_id = request.organization_id

    # 組織IDが指定された場合、ユーザーがその組織に所属しているか確認
    if org_id:
        org_check = supabase.table("organization_members").select(
            "organization_id"
        ).eq("user_id", user_id).eq("organization_id", org_id).execute()
        if not org_check.data:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="指定された組織に所属していません",
            )

    # 既存サイトを確認
    existing = supabase.table("wordpress_sites").select("id").eq(
        "user_id", user_id
    ).eq("site_url", request.site_url).execute()

    site_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    if existing.data:
        # 既存サイトを更新
        site_id = existing.data[0]["id"]
        update_data = {
            "site_name": request.site_name,
            "mcp_endpoint": request.mcp_endpoint,
            "encrypted_credentials": encrypted_credentials,
            "connection_status": "connected",
            "last_connected_at": now,
            "last_error": None,
            "updated_at": now,
        }
        if org_id:
            update_data["organization_id"] = org_id
        result = supabase.table("wordpress_sites").update(update_data).eq("id", site_id).execute()
    else:
        # 新規サイトを登録
        insert_data = {
            "id": site_id,
            "user_id": user_id,
            "site_url": request.site_url,
            "site_name": request.site_name,
            "mcp_endpoint": request.mcp_endpoint,
            "encrypted_credentials": encrypted_credentials,
            "connection_status": "connected",
            "is_active": True,
            "last_connected_at": now,
            "created_at": now,
            "updated_at": now,
        }
        if org_id:
            insert_data["organization_id"] = org_id
        result = supabase.table("wordpress_sites").insert(insert_data).execute()

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="サイト登録に失敗しました",
        )

    site_data = result.data[0]
    org_name_map = _get_org_name_map(supabase, [org_id]) if org_id else {}
    return _build_site_response(site_data, org_name_map)


@router.post(
    "/connect/wordpress/register",
    response_model=WordPressSiteResponse,
    summary="WordPress MCP登録完了",
    description="registration_codeを使ってWordPressと連携を完了",
)
async def register_wordpress_site(
    request: WordPressRegistrationRequest,
    user_id: str = Depends(get_current_user),
):
    """WordPress MCPプラグインとの登録を完了"""
    import httpx

    logger.info(f"WordPress登録リクエスト: user={user_id}, site={request.site_url}")

    supabase = get_supabase_client()
    crypto = get_crypto_service()

    # WordPressの登録エンドポイントを呼び出して認証情報を取得
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            register_response = await client.post(
                request.register_endpoint,
                json={
                    "registration_code": request.registration_code,
                    "client_name": "Marketing Automation Blog AI",
                    "client_version": "1.0.0",
                },
            )

            if register_response.status_code != 200:
                logger.error(f"WordPress登録エラー: {register_response.status_code} - {register_response.text}")
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"WordPress登録に失敗しました: {register_response.text}",
                )

            register_data = register_response.json()
            access_token = register_data.get("access_token") or register_data.get("token")

            if not access_token:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="WordPressからアクセストークンを取得できませんでした",
                )

            # デバッグ: トークンのハッシュをログに記録
            import hashlib
            token_hash = hashlib.sha256(access_token.encode()).hexdigest()
            logger.info(
                f"WordPress登録成功: token_prefix={access_token[:8]}..., "
                f"token_sha256={token_hash[:16]}..., "
                f"token_len={len(access_token)}"
            )

    except httpx.RequestError as e:
        logger.error(f"WordPress登録リクエストエラー: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"WordPressへの接続に失敗しました: {str(e)}",
        )

    # 認証情報を暗号化
    encrypted_credentials = crypto.encrypt({
        "access_token": access_token,
        "api_key": register_data.get("api_key"),
        "api_secret": register_data.get("api_secret"),
    })

    # リクエストで指定された organization_id を使用（指定なしは個人サイト）
    org_id = request.organization_id

    # 組織IDが指定された場合、ユーザーがその組織に所属しているか確認
    if org_id:
        org_check = supabase.table("organization_members").select(
            "organization_id"
        ).eq("user_id", user_id).eq("organization_id", org_id).execute()
        if not org_check.data:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="指定された組織に所属していません",
            )

    # サイトを登録
    site_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    # 既存サイトを確認
    existing = supabase.table("wordpress_sites").select("id").eq(
        "user_id", user_id
    ).eq("site_url", request.site_url).execute()

    if existing.data:
        site_id = existing.data[0]["id"]
        update_data = {
            "site_name": request.site_name,
            "mcp_endpoint": request.mcp_endpoint,
            "encrypted_credentials": encrypted_credentials,
            "connection_status": "connected",
            "last_connected_at": now,
            "last_error": None,
            "updated_at": now,
        }
        if org_id is not None:
            update_data["organization_id"] = org_id
        result = supabase.table("wordpress_sites").update(update_data).eq("id", site_id).execute()
    else:
        insert_data = {
            "id": site_id,
            "user_id": user_id,
            "site_url": request.site_url,
            "site_name": request.site_name,
            "mcp_endpoint": request.mcp_endpoint,
            "encrypted_credentials": encrypted_credentials,
            "connection_status": "connected",
            "is_active": True,
            "last_connected_at": now,
            "created_at": now,
            "updated_at": now,
        }
        if org_id:
            insert_data["organization_id"] = org_id
        result = supabase.table("wordpress_sites").insert(insert_data).execute()

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="サイト登録に失敗しました",
        )

    # WordPressにコールバックを送信（連携完了通知）
    if request.callback_url:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(
                    request.callback_url,
                    json={
                        "status": "connected",
                        "site_id": site_id,
                        "message": "連携が完了しました",
                    },
                )
        except Exception as e:
            logger.warning(f"WordPressコールバック送信失敗: {e}")
            # コールバック失敗は無視（連携自体は成功）

    site_data = result.data[0]
    org_name_map = _get_org_name_map(supabase, [org_id]) if org_id else {}
    return _build_site_response(site_data, org_name_map)


@router.get(
    "/sites",
    response_model=WordPressSiteListResponse,
    summary="WordPress連携サイト一覧",
    description="ユーザーの連携済みWordPressサイト一覧を取得",
)
async def list_wordpress_sites(
    user_id: str = Depends(get_current_user),
):
    """連携済みWordPressサイト一覧を取得（自分のサイト + 所属組織のサイト）"""
    supabase = get_supabase_client()

    # ユーザー自身のサイト
    own_result = supabase.table("wordpress_sites").select("*").eq(
        "user_id", user_id
    ).order("created_at", desc=True).execute()

    all_sites_data = list(own_result.data) if own_result.data else []
    seen_ids = {site["id"] for site in all_sites_data}

    # ユーザーの所属組織を検索
    org_memberships = supabase.table("organization_members").select(
        "organization_id"
    ).eq("user_id", user_id).execute()

    if org_memberships.data:
        org_ids = [m["organization_id"] for m in org_memberships.data]
        org_sites_result = supabase.table("wordpress_sites").select("*").in_(
            "organization_id", org_ids
        ).order("created_at", desc=True).execute()

        if org_sites_result.data:
            for site in org_sites_result.data:
                if site["id"] not in seen_ids:
                    all_sites_data.append(site)
                    seen_ids.add(site["id"])

    # 組織名マップを構築
    all_org_ids = list({
        site.get("organization_id")
        for site in all_sites_data
        if site.get("organization_id")
    })
    org_name_map = _get_org_name_map(supabase, all_org_ids)

    sites = [
        _build_site_response(site, org_name_map)
        for site in all_sites_data
    ]

    return WordPressSiteListResponse(sites=sites, total=len(sites))


@router.post(
    "/sites/{site_id}/test",
    response_model=WordPressConnectionTestResult,
    summary="WordPress接続テスト",
    description="指定したWordPressサイトへの接続をテスト",
)
async def test_wordpress_connection(
    site_id: str,
    user_id: str = Depends(get_current_user),
):
    """WordPress接続テスト"""
    logger.info(f"WordPress接続テスト: site_id={site_id}")

    supabase = get_supabase_client()

    # サイト情報を取得（ユーザー自身 or 組織メンバー）
    result = supabase.table("wordpress_sites").select("*").eq(
        "id", site_id
    ).eq("user_id", user_id).execute()

    if not result.data:
        # 組織経由のアクセスを確認
        result = _get_org_site(supabase, site_id, user_id)

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="サイトが見つかりません",
        )

    site = result.data

    # MCPクライアントキャッシュをクリア（新鮮な接続でテスト）
    clear_mcp_client_cache(site_id)

    # MCP接続テスト
    try:
        mcp_client = WordPressMcpClient(site_id=site_id, user_id=user_id)
        test_result = await mcp_client.test_connection()

        # 接続状態を更新
        now = datetime.utcnow().isoformat()
        if test_result["success"]:
            supabase.table("wordpress_sites").update({
                "connection_status": "connected",
                "last_connected_at": now,
                "last_error": None,
                "updated_at": now,
            }).eq("id", site_id).execute()
        else:
            supabase.table("wordpress_sites").update({
                "connection_status": "error",
                "last_error": test_result["message"],
                "updated_at": now,
            }).eq("id", site_id).execute()

        return WordPressConnectionTestResult(
            success=test_result["success"],
            message=test_result["message"],
            server_info=test_result.get("server_info"),
            steps=test_result.get("steps", []),
        )
    except Exception as e:
        logger.error(f"接続テストエラー: {e}")
        now = datetime.utcnow().isoformat()
        supabase.table("wordpress_sites").update({
            "connection_status": "error",
            "last_error": str(e),
            "updated_at": now,
        }).eq("id", site_id).execute()

        return WordPressConnectionTestResult(
            success=False,
            message=f"接続エラー: {str(e)}",
            server_info=None,
            steps=[],
        )


@router.delete(
    "/sites/{site_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="WordPress連携解除",
    description="WordPressサイトの連携を解除（削除）",
)
async def delete_wordpress_site(
    site_id: str,
    user_id: str = Depends(get_current_user),
):
    """WordPress連携解除"""
    logger.info(f"WordPress連携解除: site_id={site_id}")

    supabase = get_supabase_client()

    # ユーザー自身のサイトを削除試行
    result = supabase.table("wordpress_sites").delete().eq(
        "id", site_id
    ).eq("user_id", user_id).execute()

    if not result.data:
        # 組織経由のアクセスを確認して削除
        org_check = _get_org_site(supabase, site_id, user_id)
        if org_check.data:
            result = supabase.table("wordpress_sites").delete().eq("id", site_id).execute()

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="サイトが見つかりません",
        )

    return None


@router.patch(
    "/sites/{site_id}/activate",
    response_model=WordPressSiteResponse,
    summary="サイトをアクティブに設定",
    description="指定したサイトをアクティブに設定（他のサイトは非アクティブに）",
)
async def activate_wordpress_site(
    site_id: str,
    user_id: str = Depends(get_current_user),
):
    """サイトをアクティブに設定"""
    supabase = get_supabase_client()
    now = datetime.utcnow().isoformat()

    # すべてのサイトを非アクティブに（自分のサイト）
    supabase.table("wordpress_sites").update({
        "is_active": False,
        "updated_at": now,
    }).eq("user_id", user_id).execute()

    # 指定サイトをアクティブに（自分のサイト）
    result = supabase.table("wordpress_sites").update({
        "is_active": True,
        "updated_at": now,
    }).eq("id", site_id).eq("user_id", user_id).execute()

    if not result.data:
        # 組織経由のアクセスを確認
        org_check = _get_org_site(supabase, site_id, user_id)
        if org_check.data:
            result = supabase.table("wordpress_sites").update({
                "is_active": True,
                "updated_at": now,
            }).eq("id", site_id).execute()

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="サイトが見つかりません",
        )

    site = result.data[0]
    org_id = site.get("organization_id")
    org_name_map = _get_org_name_map(supabase, [org_id]) if org_id else {}
    return _build_site_response(site, org_name_map)


@router.patch(
    "/sites/{site_id}/organization",
    response_model=WordPressSiteResponse,
    summary="サイトの組織変更",
    description="WordPressサイトの所属組織を変更（個人 ↔ 組織）",
)
async def update_site_organization(
    site_id: str,
    request: WordPressSiteOrganizationUpdateRequest,
    user_id: str = Depends(get_current_user),
):
    """サイトの組織を変更（サイト所有者のみ）"""
    logger.info(f"サイト組織変更: site_id={site_id}, org_id={request.organization_id}")

    supabase = get_supabase_client()

    # サイト所有者であることを確認（user_id一致）
    site_result = supabase.table("wordpress_sites").select("*").eq(
        "id", site_id
    ).eq("user_id", user_id).execute()

    if not site_result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="サイトが見つかりません（所有者のみ変更可能）",
        )

    # 組織IDが指定された場合、ユーザーがその組織に所属しているか確認
    if request.organization_id:
        org_check = supabase.table("organization_members").select(
            "organization_id"
        ).eq("user_id", user_id).eq("organization_id", request.organization_id).execute()
        if not org_check.data:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="指定された組織に所属していません",
            )

    now = datetime.utcnow().isoformat()
    result = supabase.table("wordpress_sites").update({
        "organization_id": request.organization_id,
        "updated_at": now,
    }).eq("id", site_id).execute()

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="組織変更に失敗しました",
        )

    site = result.data[0]
    org_id = site.get("organization_id")
    org_name_map = _get_org_name_map(supabase, [org_id]) if org_id else {}
    return _build_site_response(site, org_name_map)


# =====================================================
# ブログ生成エンドポイント
# =====================================================

@router.post(
    "/generation/start",
    response_model=BlogGenerationStateResponse,
    summary="ブログ生成開始",
    description="新しいブログ記事の生成プロセスを開始（画像アップロード対応）",
)
async def start_blog_generation(
    background_tasks: BackgroundTasks,
    user_prompt: str = Form(..., max_length=2000, description="どんな記事を作りたいか"),
    wordpress_site_id: str = Form(..., description="接続済みWordPressサイトID"),
    reference_url: Optional[str] = Form(None, description="参考記事のURL"),
    files: List[UploadFile] = File(default=[], description="記事に含めたい画像（最大5枚）"),
    user_id: str = Depends(get_current_user),
):
    """ブログ生成を開始（画像アップロード対応）"""
    logger.info(f"ブログ生成開始: user={user_id}, images={len(files)}")

    # 画像枚数制限
    if len(files) > 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="画像は最大5枚までです",
        )

    # 使用量プリチェック
    org_id = _get_user_org_for_usage(user_id)
    usage_result = usage_service.check_can_generate(user_id=user_id, organization_id=org_id)
    if not usage_result.allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "monthly_limit_exceeded",
                "current": usage_result.current,
                "limit": usage_result.limit,
                "message": f"月間記事生成上限（{usage_result.limit}記事）に達しました",
            },
        )

    supabase = get_supabase_client()

    # WordPressサイトを確認（ユーザー自身 or 組織メンバー）
    site_result = supabase.table("wordpress_sites").select("*").eq(
        "id", wordpress_site_id
    ).eq("user_id", user_id).execute()

    if not site_result.data:
        # 組織経由のアクセスを確認
        site_result = _get_org_site(supabase, wordpress_site_id, user_id)

    if not site_result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="WordPressサイトが見つかりません",
        )

    site = site_result.data[0]

    # 生成プロセスを作成
    process_id = str(uuid.uuid4())
    realtime_channel = f"blog_generation:{process_id}"
    now = datetime.utcnow().isoformat()

    # 画像をWebPに変換して保存
    uploaded_images = []
    for file in files:
        if file.filename and file.size and file.size > 0:
            try:
                content = await file.read()
                local_path = convert_and_save_as_webp(
                    content, file.filename or "image.jpg", process_id
                )
                uploaded_images.append({
                    "filename": os.path.basename(local_path),
                    "original_filename": file.filename,
                    "local_path": local_path,
                    "wp_media_id": None,
                    "wp_url": None,
                    "uploaded_at": now,
                })
            except Exception as e:
                logger.warning(f"画像変換エラー: {file.filename} - {e}")

    process_data = {
        "id": process_id,
        "user_id": user_id,
        "wordpress_site_id": wordpress_site_id,
        "status": "pending",
        "current_step_name": "初期化中",
        "progress_percentage": 0,
        "is_waiting_for_input": False,
        "blog_context": {},
        "user_prompt": user_prompt,
        "reference_url": reference_url,
        "uploaded_images": uploaded_images,
        "realtime_channel": realtime_channel,
        "created_at": now,
        "updated_at": now,
    }

    result = supabase.table("blog_generation_state").insert(process_data).execute()

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="生成プロセスの作成に失敗しました",
        )

    # バックグラウンドで生成を開始
    generation_service = BlogGenerationService()
    background_tasks.add_task(
        generation_service.run_generation,
        process_id=process_id,
        user_id=user_id,
        user_prompt=user_prompt,
        reference_url=reference_url,
        wordpress_site=site,
    )

    state = result.data[0]
    return BlogGenerationStateResponse(
        id=state["id"],
        user_id=state["user_id"],
        wordpress_site_id=state.get("wordpress_site_id"),
        status=state["status"],
        current_step_name=state.get("current_step_name"),
        progress_percentage=state.get("progress_percentage", 0),
        is_waiting_for_input=state.get("is_waiting_for_input", False),
        input_type=state.get("input_type"),
        blog_context=state.get("blog_context", {}),
        user_prompt=state.get("user_prompt"),
        reference_url=state.get("reference_url"),
        uploaded_images=[],
        draft_post_id=state.get("draft_post_id"),
        draft_preview_url=state.get("draft_preview_url"),
        draft_edit_url=state.get("draft_edit_url"),
        error_message=state.get("error_message"),
        created_at=state["created_at"],
        updated_at=state["updated_at"],
    )


# =====================================================
# 生成履歴エンドポイント（{process_id}より前に定義すること）
# =====================================================

@router.get(
    "/generation/history",
    response_model=List[BlogGenerationHistoryItem],
    summary="生成履歴取得",
    description="ユーザーのブログ生成履歴を取得（軽量版）",
)
async def get_generation_history(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user_id: str = Depends(get_current_user),
):
    """生成履歴を取得（blog_context等の大きなフィールドを除外）"""
    supabase = get_supabase_client()

    # 必要なカラムだけ取得 + wordpress_sites をJOINしてサイト名を取得
    columns = (
        "id, status, current_step_name, progress_percentage, "
        "user_prompt, reference_url, "
        "draft_post_id, draft_preview_url, draft_edit_url, "
        "error_message, uploaded_images, created_at, updated_at, "
        "wordpress_sites(site_name)"
    )

    result = supabase.table("blog_generation_state").select(
        columns
    ).eq(
        "user_id", user_id
    ).order("created_at", desc=True).range(offset, offset + limit - 1).execute()

    items = []
    for state in result.data:
        # wordpress_sites JOINの結果からサイト名を取得
        wp_site = state.get("wordpress_sites")
        site_name = wp_site.get("site_name") if isinstance(wp_site, dict) else None

        # uploaded_imagesの件数を計算
        uploaded_images = state.get("uploaded_images") or []
        image_count = len(uploaded_images) if isinstance(uploaded_images, list) else 0

        items.append(BlogGenerationHistoryItem(
            id=state["id"],
            status=state["status"],
            current_step_name=state.get("current_step_name"),
            progress_percentage=state.get("progress_percentage", 0),
            user_prompt=state.get("user_prompt"),
            reference_url=state.get("reference_url"),
            draft_post_id=state.get("draft_post_id"),
            draft_preview_url=state.get("draft_preview_url"),
            draft_edit_url=state.get("draft_edit_url"),
            error_message=state.get("error_message"),
            wordpress_site_name=site_name,
            image_count=image_count,
            created_at=state["created_at"],
            updated_at=state["updated_at"],
        ))

    return items


# =====================================================
# 生成状態取得エンドポイント
# =====================================================

@router.get(
    "/generation/{process_id}",
    response_model=BlogGenerationStateResponse,
    summary="生成状態取得",
    description="ブログ生成プロセスの現在の状態を取得",
)
async def get_generation_state(
    process_id: str,
    user_id: str = Depends(get_current_user),
):
    """生成プロセスの状態を取得"""
    supabase = get_supabase_client()

    result = supabase.table("blog_generation_state").select("*").eq(
        "id", process_id
    ).eq("user_id", user_id).single().execute()

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="生成プロセスが見つかりません",
        )

    state = result.data
    return BlogGenerationStateResponse(
        id=state["id"],
        user_id=state["user_id"],
        wordpress_site_id=state.get("wordpress_site_id"),
        status=state["status"],
        current_step_name=state.get("current_step_name"),
        progress_percentage=state.get("progress_percentage", 0),
        is_waiting_for_input=state.get("is_waiting_for_input", False),
        input_type=state.get("input_type"),
        blog_context=state.get("blog_context", {}),
        user_prompt=state.get("user_prompt"),
        reference_url=state.get("reference_url"),
        uploaded_images=state.get("uploaded_images", []),
        draft_post_id=state.get("draft_post_id"),
        draft_preview_url=state.get("draft_preview_url"),
        draft_edit_url=state.get("draft_edit_url"),
        error_message=state.get("error_message"),
        created_at=state["created_at"],
        updated_at=state["updated_at"],
    )


@router.get(
    "/generation/{process_id}/events",
    summary="生成イベント取得",
    description="ブログ生成プロセスのイベント一覧を取得",
)
async def get_generation_events(
    process_id: str,
    user_id: str = Depends(get_current_user),
):
    """生成プロセスのイベント一覧を取得（アクティビティフィード用）"""
    supabase = get_supabase_client()

    # プロセスの所有権を確認
    process_check = supabase.table("blog_generation_state").select("id").eq(
        "id", process_id
    ).eq("user_id", user_id).execute()

    if not process_check.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="生成プロセスが見つかりません",
        )

    # イベントを取得（event_sequence順）
    result = supabase.table("blog_process_events").select(
        "id, process_id, event_type, event_data, event_sequence, created_at"
    ).eq(
        "process_id", process_id
    ).order("event_sequence").execute()

    return result.data or []


@router.post(
    "/generation/{process_id}/user-input",
    response_model=BlogGenerationStateResponse,
    summary="ユーザー入力送信",
    description="AIからの質問に対するユーザーの回答を送信",
)
async def submit_user_input(
    process_id: str,
    user_input: UserAnswers,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user),
):
    """ユーザー入力を送信して生成を継続"""
    logger.info(f"ユーザー入力受信: process_id={process_id}")

    supabase = get_supabase_client()

    # 現在の状態を取得
    result = supabase.table("blog_generation_state").select("*").eq(
        "id", process_id
    ).eq("user_id", user_id).single().execute()

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="生成プロセスが見つかりません",
        )

    state = result.data

    if not state.get("is_waiting_for_input"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="現在ユーザー入力を待機していません",
        )

    # コンテキストを更新
    blog_context = state.get("blog_context", {})
    existing_answers = blog_context.get("user_answers", {})
    existing_answers.update(user_input.answers)
    blog_context["user_answers"] = existing_answers

    now = datetime.utcnow().isoformat()
    supabase.table("blog_generation_state").update({
        "blog_context": blog_context,
        "is_waiting_for_input": False,
        "input_type": None,
        "status": "in_progress",
        "updated_at": now,
    }).eq("id", process_id).execute()

    # WordPressサイト情報を取得
    site_result = supabase.table("wordpress_sites").select("*").eq(
        "id", state["wordpress_site_id"]
    ).single().execute()

    # バックグラウンドで生成を継続
    generation_service = BlogGenerationService()
    background_tasks.add_task(
        generation_service.continue_generation,
        process_id=process_id,
        user_id=user_id,
        user_answers=user_input.answers,
        wordpress_site=site_result.data,
    )

    # 更新後の状態を返す
    updated_result = supabase.table("blog_generation_state").select("*").eq(
        "id", process_id
    ).single().execute()

    state = updated_result.data
    return BlogGenerationStateResponse(
        id=state["id"],
        user_id=state["user_id"],
        wordpress_site_id=state.get("wordpress_site_id"),
        status=state["status"],
        current_step_name=state.get("current_step_name"),
        progress_percentage=state.get("progress_percentage", 0),
        is_waiting_for_input=state.get("is_waiting_for_input", False),
        input_type=state.get("input_type"),
        blog_context=state.get("blog_context", {}),
        user_prompt=state.get("user_prompt"),
        reference_url=state.get("reference_url"),
        uploaded_images=state.get("uploaded_images", []),
        draft_post_id=state.get("draft_post_id"),
        draft_preview_url=state.get("draft_preview_url"),
        draft_edit_url=state.get("draft_edit_url"),
        error_message=state.get("error_message"),
        created_at=state["created_at"],
        updated_at=state["updated_at"],
    )


@router.post(
    "/generation/{process_id}/cancel",
    response_model=BlogGenerationStateResponse,
    summary="生成キャンセル",
    description="進行中のブログ生成プロセスをキャンセル",
)
async def cancel_generation(
    process_id: str,
    user_id: str = Depends(get_current_user),
):
    """生成プロセスをキャンセル"""
    logger.info(f"生成キャンセル: process_id={process_id}")

    supabase = get_supabase_client()
    now = datetime.utcnow().isoformat()

    result = supabase.table("blog_generation_state").update({
        "status": "cancelled",
        "updated_at": now,
    }).eq("id", process_id).eq("user_id", user_id).execute()

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="生成プロセスが見つかりません",
        )

    state = result.data[0]
    return BlogGenerationStateResponse(
        id=state["id"],
        user_id=state["user_id"],
        wordpress_site_id=state.get("wordpress_site_id"),
        status=state["status"],
        current_step_name=state.get("current_step_name"),
        progress_percentage=state.get("progress_percentage", 0),
        is_waiting_for_input=state.get("is_waiting_for_input", False),
        input_type=state.get("input_type"),
        blog_context=state.get("blog_context", {}),
        user_prompt=state.get("user_prompt"),
        reference_url=state.get("reference_url"),
        uploaded_images=state.get("uploaded_images", []),
        draft_post_id=state.get("draft_post_id"),
        draft_preview_url=state.get("draft_preview_url"),
        draft_edit_url=state.get("draft_edit_url"),
        error_message=state.get("error_message"),
        created_at=state["created_at"],
        updated_at=state["updated_at"],
    )


# =====================================================
# 画像アップロードエンドポイント
# =====================================================

@router.post(
    "/generation/{process_id}/upload-image",
    response_model=ImageUploadResponse,
    summary="画像アップロード",
    description="生成プロセスに画像をアップロード",
)
async def upload_image(
    process_id: str,
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user),
):
    """画像をアップロード（WebP変換対応）"""
    logger.info(f"画像アップロード: process_id={process_id}, filename={file.filename}")

    supabase = get_supabase_client()

    # プロセスを確認
    result = supabase.table("blog_generation_state").select("uploaded_images").eq(
        "id", process_id
    ).eq("user_id", user_id).single().execute()

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="生成プロセスが見つかりません",
        )

    # 画像を読み込み → WebP 変換 → 保存
    content = await file.read()
    try:
        local_path = convert_and_save_as_webp(
            content, file.filename or "image.jpg", process_id
        )
    except Exception as e:
        logger.error(f"WebP変換エラー: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"画像の処理に失敗しました: {str(e)}",
        )

    webp_filename = os.path.basename(local_path)

    # uploaded_imagesを更新
    uploaded_images = result.data.get("uploaded_images", [])
    now = datetime.utcnow().isoformat()
    uploaded_images.append({
        "filename": webp_filename,
        "original_filename": file.filename,
        "local_path": local_path,
        "wp_media_id": None,
        "wp_url": None,
        "uploaded_at": now,
    })

    supabase.table("blog_generation_state").update({
        "uploaded_images": uploaded_images,
        "updated_at": now,
    }).eq("id", process_id).execute()

    return ImageUploadResponse(
        success=True,
        filename=webp_filename,
        local_path=local_path,
        message="画像がアップロードされました（WebP形式）",
    )


# =====================================================
# ヘルパー関数
# =====================================================

def _get_user_org_for_usage(user_id: str) -> Optional[str]:
    """ユーザーの使用量追跡対象の組織IDを取得"""
    try:
        from app.common.database import supabase as db

        # 1. upgraded_to_org_id を確認
        sub = db.table("user_subscriptions").select(
            "upgraded_to_org_id"
        ).eq("user_id", user_id).maybe_single().execute()
        if sub.data and sub.data.get("upgraded_to_org_id"):
            return sub.data["upgraded_to_org_id"]

        # 2. organization_members でアクティブな組織サブスクを探す
        memberships = db.table("organization_members").select(
            "organization_id"
        ).eq("user_id", user_id).execute()
        if memberships.data:
            org_ids = [m["organization_id"] for m in memberships.data]
            org_subs = db.table("organization_subscriptions").select(
                "organization_id"
            ).in_("organization_id", org_ids).eq("status", "active").limit(1).execute()
            if org_subs.data:
                return org_subs.data[0]["organization_id"]

        return None
    except Exception:
        return None
