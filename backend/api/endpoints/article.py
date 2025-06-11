# -*- coding: utf-8 -*-
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status, Depends, HTTPException, Query
from typing import Any, List, Optional, Dict
import traceback
import json
import logging
from pydantic import ValidationError, BaseModel, Field

from services.article_service import ArticleGenerationService
from schemas.response import WebSocketMessage, ErrorPayload # エラー送信用
from core.auth import get_current_user_id_from_token

logger = logging.getLogger(__name__)

router = APIRouter()
article_service = ArticleGenerationService() # サービスインスタンス化

class ArticleUpdateRequest(BaseModel):
    """記事更新リクエスト"""
    title: Optional[str] = None
    content: Optional[str] = None
    shortdescription: Optional[str] = None
    target_audience: Optional[str] = None
    keywords: Optional[List[str]] = None

class AIEditRequest(BaseModel):
    """AIによるブロック編集リクエスト"""
    content: str = Field(..., description="元のHTMLブロック内容")
    instruction: str = Field(..., description="編集指示（カジュアルに書き換え等）")

@router.get("/", response_model=List[dict], status_code=status.HTTP_200_OK)
async def get_articles(
    user_id: str = Depends(get_current_user_id_from_token),
    status_filter: Optional[str] = Query(None, description="Filter by generation status (completed, error, etc.)"),
    limit: int = Query(20, description="Number of articles to return"),
    offset: int = Query(0, description="Number of articles to skip")
):
    """
    Get articles for the specified user.
    
    **Parameters:**
    - user_id: User ID (from authentication)
    - status_filter: Filter articles by status (optional)
    - limit: Maximum number of articles to return (default: 20)
    - offset: Number of articles to skip for pagination (default: 0)
    
    **Returns:**
    - List of articles with basic information
    """
    try:
        articles = await article_service.get_user_articles(
            user_id=user_id,
            status_filter=status_filter,
            limit=limit,
            offset=offset
        )
        return articles
    except Exception as e:
        logger.error(f"Error getting articles for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve articles"
        )

@router.get("/{article_id}", response_model=dict, status_code=status.HTTP_200_OK)
async def get_article(
    article_id: str,
    user_id: str = Depends(get_current_user_id_from_token)
):
    """
    Get detailed article information by ID.
    
    **Parameters:**
    - article_id: Article ID
    - user_id: User ID (from authentication)
    
    **Returns:**
    - Detailed article information including content
    """
    try:
        article = await article_service.get_article(article_id, user_id)
        if not article:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Article not found or access denied"
            )
        return article
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting article {article_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve article"
        )

@router.patch("/{article_id}", response_model=dict, status_code=status.HTTP_200_OK)
async def update_article(
    article_id: str,
    update_data: ArticleUpdateRequest,
    user_id: str = Depends(get_current_user_id_from_token)
):
    """
    記事を更新します。
    
    **Parameters:**
    - article_id: 記事ID
    - update_data: 更新するデータ
    - user_id: ユーザーID（認証から取得）
    
    **Returns:**
    - 更新された記事情報
    """
    try:
        # まず記事が存在し、ユーザーがアクセス権限を持つことを確認
        existing_article = await article_service.get_article(article_id, user_id)
        if not existing_article:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Article not found or access denied"
            )
        
        # 記事を更新
        updated_article = await article_service.update_article(
            article_id=article_id,
            user_id=user_id,
            update_data=update_data.dict(exclude_unset=True)
        )
        
        return updated_article
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating article {article_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update article"
        )

@router.websocket("/ws/generate")
async def generate_article_websocket_endpoint(websocket: WebSocket, process_id: str = None, token: str = None):
    """
    WebSocket接続を確立し、インタラクティブな記事生成プロセスを開始します。

    **パラメータ:**
    - process_id: 既存プロセスの再開用ID（新規作成の場合はNone）
    - token: Clerk認証トークン（認証システムから取得）

    **認証:**
    接続時にClerk認証トークンが必要です。トークンが無効な場合、接続は拒否されます。

    **接続後の流れ:**

    1.  **クライアント -> サーバー:** 接続後、最初のメッセージとして記事生成のリクエストパラメータをJSON形式で送信します (`GenerateArticleRequest` スキーマ参照)。
        ```json
        {
          "initial_keywords": ["札幌", "注文住宅", "自然素材"],
          "target_persona": "30代夫婦",
          // ... 他のパラメータ
        }
        ```
    2.  **サーバー -> クライアント:** サーバーは記事生成プロセスを開始し、進捗状況、ユーザーに入力を求める要求、最終結果などを `ServerEventMessage` 形式で送信します。
        ```json
        {
          "type": "server_event",
          "payload": {
            "event_type": "status_update", // または theme_proposal, user_input_request など
            // ... 各イベントタイプに応じたペイロード
          }
        }
        ```
    3.  **クライアント -> サーバー (応答):** サーバーから `user_input_request` イベントを受信した場合、クライアントは対応する応答を `ClientResponseMessage` 形式で送信します。
        ```json
        {
          "type": "client_response",
          "response_type": "select_theme", // または approve_plan など
          "payload": {
            "selected_index": 0 // または approved: true など
          }
        }
        ```
    4.  **最終結果:** 生成が完了すると、サーバーは `final_result` イベントを送信します。
    5.  **エラー:** エラーが発生した場合、サーバーは `error` イベントを送信します。

    接続は、生成完了時、エラー発生時、またはクライアント/サーバーからの切断要求時に閉じられます。
    """
    try:
        # WebSocket用の認証処理
        from core.auth import get_current_user_id_from_header
        
        # Authorizationヘッダーからトークンを取得
        auth_header = None
        if token:
            auth_header = f"Bearer {token}"
        else:
            # Headerからも確認
            headers = dict(websocket.headers)
            auth_header = headers.get("authorization") or headers.get("Authorization")
        
        # ユーザーIDを取得（認証失敗時はuser_2y2DRx4Xb5PbvMVoVWmDluHCeFVを返す）
        user_id = get_current_user_id_from_header(auth_header)
        
        logger.info(f"WebSocket connection authenticated for user: {user_id}")
        
    except Exception as e:
        logger.error(f"WebSocket authentication failed: {e}")
        await websocket.close(code=1008, reason="Authentication failed")
        return
    
    await article_service.handle_websocket_connection(websocket, process_id, user_id)

@router.post("/{article_id}/ai-edit", response_model=dict, status_code=status.HTTP_200_OK)
async def ai_edit_block(
    article_id: str,
    req: AIEditRequest,
    user_id: str = Depends(get_current_user_id_from_token)
):
    """
    ブロック内容を OpenAI で編集して返す。
    
    **Parameters**
    - article_id: 記事ID（アクセス制御用）
    - req: AIEditRequest (content, instruction)
    - user_id: Clerk認証ユーザーID
    """
    try:
        # ユーザーが記事にアクセスできるかチェック
        article = await article_service.get_article(article_id, user_id)
        if not article:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found or access denied")

        from core.config import settings
        from openai import AsyncOpenAI
        client = AsyncOpenAI(api_key=settings.openai_api_key)

        system_prompt = (
            "あなたは優秀なSEOライターです。ユーザーの指示に従ってHTMLブロックを編集し、" \
            "結果を同じタグ構造で返してください。不要なタグや装飾は追加しないでください。"
        )
        user_prompt = (
            f"### 編集指示\n{req.instruction}\n\n" \
            f"### 元のHTMLブロック\n{req.content}\n\n" \
            "### 出力形式:\n編集後のHTMLブロックのみを返す。余計な説明は不要。"
        )

        completion = await client.chat.completions.create(
            model=settings.editing_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
        )

        new_content = completion.choices[0].message.content.strip()

        return {"new_content": new_content}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"AI edit error for article {article_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="AI edit failed")

