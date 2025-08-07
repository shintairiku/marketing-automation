# -*- coding: utf-8 -*-
"""
SEO記事生成ドメイン - APIエンドポイント (統合版)

This module provides:
- Article WebSocket generation endpoints
- Article CRUD operations  
- Article Flow Management API Endpoints
- AI editing capabilities
"""

from fastapi import APIRouter, status, Depends, HTTPException, Query, BackgroundTasks, Request
from typing import List, Optional, Dict, Any
import logging
from pydantic import BaseModel, Field

# 新しいインポートパス（修正版）
from .services.generation_service import ArticleGenerationService
from .schemas import GenerateArticleRequest
# from .services.flow_service import (  # 後で実装
#     article_flow_service,
#     ArticleFlowCreate,
#     ArticleFlowRead,
#     GeneratedArticleStateRead,
#     FlowExecutionRequest
# )
from app.common.auth import get_current_user_id_from_token
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer(auto_error=False)

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

# Define models first
class ArticleFlowCreate(BaseModel):
    name: str = "stub"
    description: Optional[str] = None
    is_template: bool = False
    steps: List[Dict[str, Any]] = []
    
class _StubStep(BaseModel):
    step_order: int = 0
    step_type: str = "stub"
    agent_name: str = "stub"
    prompt_template_id: str = "stub"
    tool_config: Dict[str, Any] = {}
    output_schema: Dict[str, Any] = {}
    is_interactive: bool = False
    skippable: bool = False
    config: Dict[str, Any] = {}

class ArticleFlowRead(BaseModel):
    id: str = "stub"
    name: str = "stub"
    is_template: bool = False
    steps: List[_StubStep] = []

# Flow service stubs
class ArticleFlowService:
    async def create_flow(self, user_id: str, organization_id: Optional[str], flow_data: Any) -> Dict[str, Any]: return {}
    async def get_user_flows(self, user_id: str, organization_id: Optional[str] = None) -> List[ArticleFlowRead]: return []
    async def get_flow(self, flow_id: str, user_id: str) -> Optional[ArticleFlowRead]: return None
    async def update_flow(self, flow_id: str, user_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]: return {}
    async def delete_flow(self, flow_id: str, user_id: str) -> bool: return False
    async def start_flow_execution(self, user_id: str, execution_request: Any) -> Optional[str]: return None
    async def get_generation_state(self, process_id: str, user_id: str) -> Optional[Dict[str, Any]]: return None
    async def pause_generation(self, process_id: str, user_id: str) -> bool: return False
    async def cancel_generation(self, process_id: str, user_id: str) -> bool: return False

article_flow_service = ArticleFlowService()
    
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
    status: Optional[str] = Field(None, description="記事の公開状態 (draft, published)")

class ArticleStatusUpdateRequest(BaseModel):
    """記事公開状態更新専用リクエスト"""
    status: str = Field(..., description="記事の公開状態 (draft, published)")

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
    request: Request,
    process_id: str,
    user_id: str = Depends(get_current_user_id_from_token),
    authorization: Optional[HTTPAuthorizationCredentials] = Depends(security)
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
        # Debug raw request headers
        auth_header_raw = request.headers.get("Authorization")
        logger.info(f"🔐 [ENDPOINT] Raw Authorization header: {auth_header_raw[:30] if auth_header_raw else 'None'}...")
        logger.info(f"🔐 [ENDPOINT] All headers: {dict(request.headers)}")
        
        # Extract JWT token for RLS enforcement
        user_jwt = authorization.credentials if authorization else None
        logger.info(f"🔐 [ENDPOINT] Getting process {process_id} for user {user_id} with JWT: {user_jwt is not None}")
        
        process_state = await article_service.get_generation_process_state(process_id, user_id, user_jwt)
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

@router.patch("/{article_id}/status", response_model=dict, status_code=status.HTTP_200_OK)
async def update_article_status(
    article_id: str,
    status_data: ArticleStatusUpdateRequest,
    user_id: str = Depends(get_current_user_id_from_token)
):
    """
    記事の公開状態を更新します。
    
    **Parameters:**
    - article_id: 記事ID
    - status_data: 公開状態データ (draft または published)
    - user_id: ユーザーID（認証から取得）
    
    **Returns:**
    - 更新された記事情報
    """
    try:
        # ステータス値の検証
        valid_statuses = ['draft', 'published']
        if status_data.status not in valid_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
            )
        
        # まず記事が存在し、ユーザーがアクセス権限を持つことを確認
        existing_article = await article_service.get_article(article_id, user_id)
        if not existing_article:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Article not found or access denied"
            )
        
        # 記事の公開状態を更新
        updated_article = await article_service.update_article(
            article_id=article_id,
            user_id=user_id,
            update_data={"status": status_data.status}
        )
        
        return {
            "id": article_id,
            "status": status_data.status,
            "message": f"記事の状態を「{status_data.status}」に更新しました",
            "updated_at": updated_article.get("updated_at") if updated_article else None
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating article status {article_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update article status"
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

        content = completion.choices[0].message.content
        new_content = content.strip() if content else ""

        return {"edited_content": new_content}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"AI edit error for article {article_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="AI edit failed")

# --- WebSocket Generation Endpoint (DEPRECATED) ---
# NOTE: WebSocket endpoint has been removed in favor of Supabase Realtime.
# Use the new HTTP endpoints for generation management: /generation/start, /generation/{id}/user-input, etc.

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
        logger.info(f"🎯 [ENDPOINT] Starting generation process for user: {user_id}")
        
        # Create process in database
        logger.info("📝 [ENDPOINT] Creating process in database")
        process_id = await article_service.create_generation_process(
            user_id=user_id,
            organization_id=organization_id,
            request_data=request
        )
        logger.info(f"✅ [ENDPOINT] Process created with ID: {process_id}")
        
        # Start background task
        logger.info("🚀 [ENDPOINT] Adding background task to FastAPI BackgroundTasks")
        background_tasks.add_task(
            article_service.run_generation_background_task,
            process_id=process_id,
            user_id=user_id,
            organization_id=organization_id,
            request_data=request
        )
        logger.info(f"✅ [ENDPOINT] Background task added successfully for process {process_id}")
        
        response_data = {
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
        logger.info(f"🏁 [ENDPOINT] Returning response for process {process_id}")
        return response_data
        
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
        logger.info(f"🔍 [SUBMIT_INPUT] Processing user input for process {process_id}, user {user_id}")
        logger.info(f"📝 [SUBMIT_INPUT] Input data: {input_data.dict()}")
        
        # Validate process state
        process_state = await article_service.get_generation_process_state(process_id, user_id)
        if not process_state:
            logger.error(f"❌ [SUBMIT_INPUT] Process {process_id} not found for user {user_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Process not found or access denied"
            )
        
        logger.info(f"📊 [SUBMIT_INPUT] Process state: {process_state}")
        
        if not process_state.get("is_waiting_for_input"):
            logger.error(f"❌ [SUBMIT_INPUT] Process {process_id} is not waiting for input: {process_state.get('is_waiting_for_input')}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Process is not waiting for user input"
            )
        
        # Validate input type matches expected (skip validation for special request types)
        expected_input_type = process_state.get("input_type")
        special_request_types = ["regenerate", "edit_and_proceed"]
        
        if (expected_input_type and 
            expected_input_type != input_data.response_type and 
            input_data.response_type not in special_request_types):
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
        logger.error(f"💥 [SUBMIT_INPUT] Error processing user input for {process_id}: {e}")
        logger.exception(f"[SUBMIT_INPUT] Full exception details for process {process_id}:")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process user input: {str(e)}"
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

# Flow CRUD操作用の認証（フロー管理専用）
# Use proper Clerk JWT authentication for flows
from app.common.auth import get_current_user_id_from_token as get_current_user_id_for_flows

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