# -*- coding: utf-8 -*-
"""
SEO記事生成ドメイン - APIエンドポイント (統合版)

This module provides:
- Article WebSocket generation endpoints
- Article CRUD operations  
- Article Flow Management API Endpoints
- AI editing capabilities
"""

from fastapi import APIRouter, WebSocket, status, Depends, HTTPException, Query, BackgroundTasks
from typing import List, Optional, Dict, Any
import logging
from pydantic import BaseModel, Field

# 新しいインポートパス（修正版）
from .services.generation_service import ArticleGenerationService
from .schemas import GenerateArticleRequest, ClientResponsePayload
# from .services.flow_service import (  # 後で実装
#     article_flow_service,
#     ArticleFlowCreate,
#     ArticleFlowRead,
#     GeneratedArticleStateRead,
#     FlowExecutionRequest
# )
from app.common.auth import get_current_user_id_from_token

# TODO: サービス実装完了後に有効化
# from app.infrastructure.external_apis.article_service import ArticleGenerationService
# from app.infrastructure.external_apis.article_flow_service import (
#     article_flow_service,
#     ArticleFlowCreate,
#     ArticleFlowRead,
#     GeneratedArticleStateRead,
#     FlowExecutionRequest
# )

# 実際のサービスインスタンスを使用
article_service = ArticleGenerationService()

# Flow service stubs
class ArticleFlowService:
    async def create_flow(self, **kwargs): return {}
    async def get_user_flows(self, **kwargs): return []
    async def get_flow(self, **kwargs): return None
    async def update_flow(self, **kwargs): return {}
    async def delete_flow(self, **kwargs): return False
    async def start_flow_execution(self, **kwargs): return None
    async def get_generation_state(self, **kwargs): return None
    async def pause_generation(self, **kwargs): return False
    async def cancel_generation(self, **kwargs): return False

article_flow_service = ArticleFlowService()


class ArticleFlowCreate(BaseModel):
    name: str = "stub"
    
class ArticleFlowRead(BaseModel):
    id: str = "stub"
    name: str = "stub"
    
class GeneratedArticleStateRead(BaseModel):
    status: str = "stub"
    
class FlowExecutionRequest(BaseModel):
    flow_id: str = "stub"

logger = logging.getLogger(__name__)

router = APIRouter()
# インスタンスは上記で作成済み

# --- Request/Response Models ---

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

# --- New Realtime Process Management Models ---

class UserInputRequest(BaseModel):
    """ユーザー入力データ"""
    response_type: str = Field(..., description="応答タイプ")
    payload: Dict[str, Any] = Field(..., description="応答データ")

class ProcessEventResponse(BaseModel):
    """プロセスイベント応答"""
    id: str
    process_id: str
    event_type: str
    event_data: Dict[str, Any]
    event_sequence: int
    created_at: str

# --- Article CRUD Endpoints ---

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

@router.get("/all-processes", response_model=List[dict], status_code=status.HTTP_200_OK)
async def get_all_processes(
    user_id: str = Depends(get_current_user_id_from_token),
    status_filter: Optional[str] = Query(None, description="Filter by status (completed, in_progress, error, etc.)"),
    limit: int = Query(20, description="Number of items to return"),
    offset: int = Query(0, description="Number of items to skip")
):
    """
    Get all processes (completed articles + in-progress/failed generation processes) for the user.
    
    **Parameters:**
    - user_id: User ID (from authentication)
    - status_filter: Filter by status (optional)
    - limit: Maximum number of items to return (default: 20)
    - offset: Number of items to skip for pagination (default: 0)
    
    **Returns:**
    - List of articles and generation processes with unified format
    """
    try:
        processes = await article_service.get_all_user_processes(
            user_id=user_id,
            status_filter=status_filter,
            limit=limit,
            offset=offset
        )
        return processes
    except Exception as e:
        logger.error(f"Error getting all processes for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve processes"
        )

@router.get("/recoverable-processes", response_model=List[dict], status_code=status.HTTP_200_OK)
async def get_recoverable_processes(
    user_id: str = Depends(get_current_user_id_from_token),
    limit: int = Query(10, description="Number of recoverable processes to return"),
):
    """
    Get recoverable processes for the user that can be resumed.
    
    **Parameters:**
    - user_id: User ID (from authentication)
    - limit: Maximum number of processes to return (default: 10)
    
    **Returns:**
    - List of recoverable generation processes with recovery metadata
    """
    try:
        processes = await article_service.get_recoverable_processes(
            user_id=user_id,
            limit=limit
        )
        return processes
    except Exception as e:
        logger.error(f"Error getting recoverable processes for user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve recoverable processes"
        )

@router.get("/generation/{process_id}", response_model=dict, status_code=status.HTTP_200_OK)
async def get_generation_process(
    process_id: str,
    user_id: str = Depends(get_current_user_id_from_token)
):
    """
    Get generation process state by ID.
    
    **Parameters:**
    - process_id: Generation process ID
    - user_id: User ID (from authentication)
    
    **Returns:**
    - Generation process state including image_mode and other context data
    """
    try:
        process_state = await article_service.get_generation_process_state(process_id, user_id)
        if not process_state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Generation process not found or access denied"
            )
        return process_state
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting generation process {process_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve generation process"
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

        from app.core.config import settings
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

# --- WebSocket Generation Endpoint ---

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
        from app.common.auth import get_current_user_id_from_header
        
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

# --- NEW: Supabase Realtime Process Management Endpoints ---

@router.post("/generation/start", response_model=dict, status_code=status.HTTP_201_CREATED)
async def start_generation_process(
    request: GenerateArticleRequest,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user_id_from_token),
    organization_id: Optional[str] = Query(None, description="Organization ID for multi-tenant support")
):
    """
    Start a new article generation process using background tasks and Supabase Realtime.
    
    **Parameters:**
    - request: Article generation request parameters
    - user_id: User ID (from authentication)
    - organization_id: Optional organization ID for multi-tenant support
    
    **Returns:**
    - process_id: Unique process identifier
    - realtime_channel: Supabase Realtime channel name for subscription
    - status: Initial process status
    """
    try:
        # Create process in database
        process_id = await article_service.create_generation_process(
            user_id=user_id,
            organization_id=organization_id,
            request_data=request
        )
        
        # Start background task
        background_tasks.add_task(
            article_service.run_generation_background_task,
            process_id=process_id,
            user_id=user_id,
            organization_id=organization_id,
            request_data=request
        )
        
        return {
            "process_id": process_id,
            "realtime_channel": f"process_{process_id}",
            "status": "started",
            "message": "Generation process started successfully",
            "subscription_info": {
                "table": "process_events",
                "filter": f"process_id=eq.{process_id}",
                "channel": f"process_events:process_id=eq.{process_id}"
            }
        }
        
    except Exception as e:
        logger.error(f"Error starting generation process: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start generation process"
        )

@router.post("/generation/{process_id}/resume", response_model=dict, status_code=status.HTTP_200_OK)
async def resume_generation_process(
    process_id: str,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user_id_from_token)
):
    """
    Resume a paused or failed generation process.
    
    **Parameters:**
    - process_id: Generation process ID to resume
    - user_id: User ID (from authentication)
    
    **Returns:**
    - process_id: Process identifier
    - status: Updated process status
    """
    try:
        # Validate process ownership and resumability
        process_state = await article_service.get_generation_process_state(process_id, user_id)
        if not process_state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Process not found or access denied"
            )
        
        # Check if process can be resumed
        resumable_statuses = ['user_input_required', 'paused', 'error']
        if process_state.get("status") not in resumable_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Process cannot be resumed from status: {process_state.get('status')}"
            )
        
        # Start resume background task
        background_tasks.add_task(
            article_service.resume_generation_background_task,
            process_id=process_id,
            user_id=user_id
        )
        
        return {
            "process_id": process_id,
            "status": "resuming",
            "message": "Generation process resume initiated",
            "realtime_channel": f"process_{process_id}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resuming generation {process_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to resume generation process"
        )

@router.post("/generation/{process_id}/user-input", response_model=dict, status_code=status.HTTP_200_OK)
async def submit_user_input(
    process_id: str,
    input_data: UserInputRequest,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user_id_from_token)
):
    """
    Submit user input for a process waiting for user interaction.
    
    **Parameters:**
    - process_id: Generation process ID
    - input_data: User input data (response_type and payload)
    - user_id: User ID (from authentication)
    
    **Returns:**
    - process_id: Process identifier
    - status: Updated process status
    """
    try:
        # Validate process state
        process_state = await article_service.get_generation_process_state(process_id, user_id)
        if not process_state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Process not found or access denied"
            )
        
        if not process_state.get("is_waiting_for_input"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Process is not waiting for user input"
            )
        
        # Validate input type matches expected
        expected_input_type = process_state.get("input_type")
        if expected_input_type and expected_input_type != input_data.response_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Expected input type '{expected_input_type}', got '{input_data.response_type}'"
            )
        
        # Store user input and update process state
        await article_service.process_user_input(
            process_id=process_id,
            user_id=user_id,
            input_data=input_data.dict()
        )
        
        # Continue processing in background
        background_tasks.add_task(
            article_service.continue_generation_after_input,
            process_id=process_id,
            user_id=user_id
        )
        
        return {
            "process_id": process_id,
            "status": "input_received",
            "message": "User input received, continuing generation",
            "input_type": input_data.response_type
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing user input for {process_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process user input"
        )

@router.post("/generation/{process_id}/pause", response_model=dict, status_code=status.HTTP_200_OK)
async def pause_generation_process(
    process_id: str,
    user_id: str = Depends(get_current_user_id_from_token)
):
    """
    Pause a running generation process.
    
    **Parameters:**
    - process_id: Generation process ID to pause
    - user_id: User ID (from authentication)
    
    **Returns:**
    - process_id: Process identifier
    - status: Updated process status
    """
    try:
        success = await article_service.pause_generation_process(process_id, user_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Process not found, access denied, or cannot be paused"
            )
        
        return {
            "process_id": process_id,
            "status": "paused",
            "message": "Generation process paused successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error pausing generation {process_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to pause generation process"
        )

@router.delete("/generation/{process_id}", response_model=dict, status_code=status.HTTP_200_OK)
async def cancel_generation_process(
    process_id: str,
    user_id: str = Depends(get_current_user_id_from_token)
):
    """
    Cancel a generation process.
    
    **Parameters:**
    - process_id: Generation process ID to cancel
    - user_id: User ID (from authentication)
    
    **Returns:**
    - process_id: Process identifier
    - status: Updated process status
    """
    try:
        success = await article_service.cancel_generation_process(process_id, user_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Process not found, access denied, or cannot be cancelled"
            )
        
        return {
            "process_id": process_id,
            "status": "cancelled",
            "message": "Generation process cancelled successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling generation {process_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel generation process"
        )

@router.get("/generation/{process_id}/events", response_model=List[ProcessEventResponse], status_code=status.HTTP_200_OK)
async def get_process_events(
    process_id: str,
    user_id: str = Depends(get_current_user_id_from_token),
    since_sequence: Optional[int] = Query(None, description="Get events after this sequence number"),
    limit: int = Query(50, description="Maximum events to return"),
    event_types: Optional[str] = Query(None, description="Comma-separated list of event types to filter")
):
    """
    Get process events for real-time synchronization and event history.
    
    **Parameters:**
    - process_id: Generation process ID
    - user_id: User ID (from authentication)
    - since_sequence: Get events after this sequence number (for incremental updates)
    - limit: Maximum number of events to return
    - event_types: Comma-separated list of event types to filter (optional)
    
    **Returns:**
    - List of process events ordered by sequence number
    """
    try:
        # Parse event types filter
        event_type_list = None
        if event_types:
            event_type_list = [t.strip() for t in event_types.split(",") if t.strip()]
        
        events = await article_service.get_process_events(
            process_id=process_id,
            user_id=user_id,
            since_sequence=since_sequence,
            limit=limit,
            event_types=event_type_list
        )
        
        return events
        
    except Exception as e:
        logger.error(f"Error getting process events for {process_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve process events"
        )

@router.post("/generation/{process_id}/events/{event_id}/acknowledge", response_model=dict, status_code=status.HTTP_200_OK)
async def acknowledge_event(
    process_id: str,
    event_id: str,
    user_id: str = Depends(get_current_user_id_from_token)
):
    """
    Acknowledge receipt of a specific event (for reliable delivery tracking).
    
    **Parameters:**
    - process_id: Generation process ID
    - event_id: Event ID to acknowledge
    - user_id: User ID (from authentication)
    
    **Returns:**
    - status: Acknowledgment status
    """
    try:
        success = await article_service.acknowledge_process_event(
            process_id=process_id,
            event_id=event_id,
            user_id=user_id
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found or access denied"
            )
        
        return {
            "status": "acknowledged",
            "event_id": event_id,
            "process_id": process_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error acknowledging event {event_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to acknowledge event"
        )

@router.get("/generation/{process_id}/realtime-info", response_model=dict, status_code=status.HTTP_200_OK)
async def get_realtime_subscription_info(
    process_id: str,
    user_id: str = Depends(get_current_user_id_from_token)
):
    """
    Get Supabase Realtime subscription information for a process.
    
    **Parameters:**
    - process_id: Generation process ID
    - user_id: User ID (from authentication)
    
    **Returns:**
    - Subscription configuration for Supabase Realtime client
    """
    try:
        # Validate process access
        process_state = await article_service.get_generation_process_state(process_id, user_id)
        if not process_state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Process not found or access denied"
            )
        
        return {
            "process_id": process_id,
            "subscription_config": {
                "channel_name": f"process_events:process_id=eq.{process_id}",
                "table": "process_events",
                "filter": f"process_id=eq.{process_id}",
                "event": "INSERT",
                "schema": "public"
            },
            "process_state_subscription": {
                "channel_name": f"process_state:{process_id}",
                "table": "generated_articles_state",
                "filter": f"id=eq.{process_id}",
                "event": "UPDATE",
                "schema": "public"
            },
            "current_status": process_state.get("status"),
            "last_updated": process_state.get("updated_at")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting realtime info for {process_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve realtime subscription info"
        )

# --- Article Flow Management Endpoints ---

# Flow CRUD操作用の認証ヘルパー（フロー管理専用）
# TODO: Add authentication dependency
# For now, we'll use a placeholder for user_id
# In production, this should come from JWT token validation
async def get_current_user_id_for_flows() -> str:
    """Get current user ID from authentication token (for flow management)"""
    # This is a placeholder - implement proper JWT validation
    return "placeholder-user-id"

@router.post("/flows/", response_model=ArticleFlowRead, status_code=status.HTTP_201_CREATED)
async def create_flow(
    flow_data: ArticleFlowCreate,
    organization_id: Optional[str] = Query(None, description="Organization ID for organization-level flows"),
    current_user_id: str = Depends(get_current_user_id_for_flows)
):
    """Create a new article generation flow"""
    try:
        flow = await article_flow_service.create_flow(current_user_id, organization_id, flow_data)
        return flow
    except Exception as e:
        logger.error(f"Error creating flow: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create flow"
        )

@router.get("/flows/", response_model=List[ArticleFlowRead])
async def get_flows(
    organization_id: Optional[str] = Query(None, description="Filter by organization ID"),
    include_templates: bool = Query(True, description="Include template flows"),
    current_user_id: str = Depends(get_current_user_id_for_flows)
):
    """Get flows accessible to the current user"""
    try:
        flows = await article_flow_service.get_user_flows(current_user_id, organization_id)
        
        # Filter templates if requested
        if not include_templates:
            flows = [flow for flow in flows if not flow.is_template]
        
        return flows
    except Exception as e:
        logger.error(f"Error getting flows: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve flows"
        )

@router.get("/flows/{flow_id}", response_model=ArticleFlowRead)
async def get_flow(
    flow_id: str,
    current_user_id: str = Depends(get_current_user_id_for_flows)
):
    """Get flow by ID"""
    try:
        flow = await article_flow_service.get_flow(flow_id, current_user_id)
        if not flow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Flow not found or access denied"
            )
        return flow
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting flow {flow_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve flow"
        )

@router.put("/flows/{flow_id}", response_model=ArticleFlowRead)
async def update_flow(
    flow_id: str,
    update_data: dict,
    current_user_id: str = Depends(get_current_user_id_for_flows)
):
    """Update flow (only owner or organization admin can update)"""
    try:
        flow = await article_flow_service.update_flow(flow_id, current_user_id, update_data)
        if not flow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Flow not found or access denied"
            )
        return flow
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating flow {flow_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update flow"
        )

@router.delete("/flows/{flow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_flow(
    flow_id: str,
    current_user_id: str = Depends(get_current_user_id_for_flows)
):
    """Delete flow (only owner or organization admin can delete)"""
    try:
        success = await article_flow_service.delete_flow(flow_id, current_user_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Flow not found or access denied"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting flow {flow_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete flow"
        )

# Flow execution endpoints
@router.post("/flows/{flow_id}/execute")
async def execute_flow(
    flow_id: str,
    execution_request: FlowExecutionRequest,
    current_user_id: str = Depends(get_current_user_id_for_flows)
):
    """Start executing a flow"""
    try:
        # Set the flow_id from the path parameter
        execution_request.flow_id = flow_id
        
        process_id = await article_flow_service.start_flow_execution(current_user_id, execution_request)
        if not process_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Flow not found or access denied"
            )
        
        return {
            "process_id": process_id,
            "message": "Flow execution started",
            "status": "in_progress"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing flow {flow_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start flow execution"
        )

# Generation state management endpoints
@router.get("/flows/generations/{process_id}", response_model=GeneratedArticleStateRead)
async def get_generation_state(
    process_id: str,
    current_user_id: str = Depends(get_current_user_id_for_flows)
):
    """Get generation process state"""
    try:
        state = await article_flow_service.get_generation_state(process_id, current_user_id)
        if not state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Generation process not found or access denied"
            )
        return state
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting generation state {process_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve generation state"
        )

@router.post("/flows/generations/{process_id}/pause")
async def pause_generation(
    process_id: str,
    current_user_id: str = Depends(get_current_user_id_for_flows)
):
    """Pause generation process"""
    try:
        success = await article_flow_service.pause_generation(process_id, current_user_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Generation process not found or access denied"
            )
        
        return {"message": "Generation process paused"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error pausing generation {process_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to pause generation"
        )

@router.post("/flows/generations/{process_id}/cancel")
async def cancel_generation(
    process_id: str,
    current_user_id: str = Depends(get_current_user_id_for_flows)
):
    """Cancel generation process"""
    try:
        success = await article_flow_service.cancel_generation(process_id, current_user_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Generation process not found or access denied"
            )
        
        return {"message": "Generation process cancelled"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling generation {process_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel generation"
        )

# Template flow endpoints
@router.get("/flows/templates/", response_model=List[ArticleFlowRead])
async def get_template_flows(
    current_user_id: str = Depends(get_current_user_id_for_flows)
):
    """Get all template flows available for copying"""
    try:
        flows = await article_flow_service.get_user_flows(current_user_id)
        template_flows = [flow for flow in flows if flow.is_template]
        return template_flows
    except Exception as e:
        logger.error(f"Error getting template flows: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve template flows"
        )

@router.post("/flows/templates/{template_id}/copy", response_model=ArticleFlowRead)
async def copy_template_flow(
    template_id: str,
    name: str = Query(..., description="Name for the new flow"),
    organization_id: Optional[str] = Query(None, description="Organization ID for organization-level flow"),
    current_user_id: str = Depends(get_current_user_id_for_flows)
):
    """Copy a template flow to create a new customizable flow"""
    try:
        # Get template flow
        template = await article_flow_service.get_flow(template_id, current_user_id)
        if not template or not template.is_template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Template flow not found"
            )
        
        # Create flow data from template
        flow_data = ArticleFlowCreate(
            name=name,
            description=f"Copied from template: {template.name}",
            is_template=False,
            steps=[
                {
                    "step_order": step.step_order,
                    "step_type": step.step_type,
                    "agent_name": step.agent_name,
                    "prompt_template_id": step.prompt_template_id,
                    "tool_config": step.tool_config,
                    "output_schema": step.output_schema,
                    "is_interactive": step.is_interactive,
                    "skippable": step.skippable,
                    "config": step.config
                }
                for step in template.steps
            ]
        )
        
        # Create new flow
        new_flow = await article_flow_service.create_flow(current_user_id, organization_id, flow_data)
        return new_flow
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error copying template flow {template_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to copy template flow"
        )