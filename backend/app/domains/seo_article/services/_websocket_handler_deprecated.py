# -*- coding: utf-8 -*-
import asyncio
import json
import time
import traceback
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Union
from fastapi import WebSocket, WebSocketDisconnect, status
from starlette.websockets import WebSocketState
from openai import AsyncOpenAI, BadRequestError, InternalServerError, AuthenticationError
from openai.types.responses import ResponseTextDeltaEvent, ResponseCompletedEvent
from agents import Runner, RunConfig, Agent, trace
from agents.exceptions import AgentsException, MaxTurnsExceeded, ModelBehaviorError, UserError
from agents.tracing import custom_span
from rich.console import Console
from pydantic import ValidationError, BaseModel

# 内部モジュールのインポート
from app.core.config import settings
from app.domains.seo_article.schemas import (
    GenerateArticleRequest,
    # Server event payloads
    StatusUpdatePayload, ThemeProposalPayload, ResearchPlanPayload, ResearchProgressPayload,
    ResearchCompletePayload, OutlinePayload, SectionChunkPayload, EditingStartPayload, ImagePlaceholderData,
    FinalResultPayload, GeneratedPersonasPayload, SerpKeywordAnalysisPayload, SerpAnalysisArticleData,
    # Client response payloads
    SelectThemePayload, ApprovePayload, SelectPersonaPayload, GeneratedPersonaData, 
    EditAndProceedPayload, EditThemePayload, EditPlanPayload, EditOutlinePayload,
    # Data models
    ThemeProposalData, ResearchPlanData, ResearchPlanQueryData, OutlineData, OutlineSectionData
)
from app.common.schemas import (
    WebSocketMessage, ServerEventMessage, ClientResponseMessage,
    ErrorPayload, UserInputRequestPayload, UserInputType
)
from app.domains.seo_article.context import ArticleContext

console = Console()
logger = logging.getLogger(__name__)

# ステップ分類定数（WebSocket handler用）
AUTONOMOUS_STEPS = {
    'keyword_analyzing', 'persona_generating', 'theme_generating',
    'research_planning', 'researching', 'research_synthesizing', 
    'writing_sections', 'editing'
}

USER_INPUT_STEPS = {
    'persona_generated', 'theme_proposed', 
    'research_plan_generated', 'outline_generated'
}

# 切断後も処理を継続できるステップ
DISCONNECTION_RESILIENT_STEPS = {
    'research_planning', 'researching', 'research_synthesizing',
    'writing_sections', 'editing'
}

def is_disconnection_resilient(step: str) -> bool:
    """WebSocket切断時でも処理継続可能なステップかどうかを判定"""
    return step in DISCONNECTION_RESILIENT_STEPS

class WebSocketHandler:
    """WebSocket接続管理とハートビート監視を担当するクラス"""
    
    def __init__(self, service):
        self.service = service  # ArticleGenerationServiceへの参照
        
    async def start_heartbeat_monitor(self, websocket: WebSocket, process_id: str, context: "ArticleContext") -> asyncio.Task:
        """WebSocket接続のハートビート監視を開始"""
        async def heartbeat_loop():
            connection_lost_count = 0
            max_connection_lost = 3
            
            try:
                while websocket.client_state == WebSocketState.CONNECTED:
                    try:
                        # 30秒間隔でハートビートを送信し、接続を確認
                        await asyncio.sleep(30)
                        if websocket.client_state == WebSocketState.CONNECTED:
                            # FastAPIのWebSocketではpingメソッドがないため、テキストメッセージを送信
                            await websocket.send_text('{"type":"heartbeat"}')
                        else:
                            logger.info(f"WebSocket not connected for process {process_id}, stopping heartbeat")
                            break
                    except Exception as e:
                        logger.warning(f"Heartbeat failed for process {process_id}: {e}")
                        connection_lost_count += 1
                        if connection_lost_count >= max_connection_lost:
                            logger.error(f"Max connection lost attempts reached for process {process_id}")
                            break
                        # 短い間隔で再試行
                        await asyncio.sleep(5)
                
                # 接続が切れた場合の処理
                await self.handle_disconnection(process_id, context)
                
            except asyncio.CancelledError:
                logger.info(f"Heartbeat monitor cancelled for process {process_id}")
            except Exception as e:
                logger.error(f"Heartbeat monitor error for process {process_id}: {e}")
                await self.handle_disconnection(process_id, context)
        
        task = asyncio.create_task(heartbeat_loop())
        self.service.active_heartbeats[process_id] = task
        return task

    async def handle_disconnection(self, process_id: str, context: "ArticleContext"):
        """WebSocket切断時の処理"""
        logger.info(f"Handling disconnection for process {process_id}, current step: {context.current_step}")
        
        try:
            # プロセス状態を一時停止として更新（disconnectedの代わりにpausedを使用）
            await self.service.persistence_service.update_process_status(
                process_id, 
                'paused',
                context.current_step,
                metadata={
                    'disconnected_at': datetime.now(timezone.utc).isoformat(),
                    'can_auto_resume': is_disconnection_resilient(context.current_step),
                    'progress_percentage': self.service.utils.calculate_progress_percentage(context),
                    'reason': 'websocket_disconnected'
                }
            )
            
            # 切断耐性があるステップの場合、バックグラウンド処理を継続
            if is_disconnection_resilient(context.current_step):
                logger.info(f"Starting background processing for disconnected process {process_id}")
                await self.start_background_processing(process_id, context)
            else:
                logger.info(f"Process {process_id} requires user input, pausing until reconnection")
                
        except Exception as e:
            logger.error(f"Error handling disconnection for process {process_id}: {e}")

    async def start_background_processing(self, process_id: str, context: "ArticleContext"):
        """切断されたプロセスのバックグラウンド処理を開始"""
        async def background_loop():
            try:
                logger.info(f"Starting background processing for process {process_id}")
                
                # WebSocketなしで処理継続
                context.websocket = None
                
                # RunConfigを適切に初期化（トレーシング情報を含む）
                run_config = RunConfig(
                    workflow_name="SEO記事生成ワークフロー（バックグラウンド）",
                    trace_id=f"bg_{process_id}",
                    group_id=process_id,
                    trace_metadata={
                        "process_id": process_id,
                        "background_processing": True,
                        "current_step": context.current_step
                    }
                )
                
                # ユーザーIDがcontextに設定されていることを確認
                user_id = context.user_id or "unknown"
                
                # バックグラウンド処理でもワークフローロガーを確保
                await self.service.flow_manager.ensure_workflow_logger(context, process_id, user_id)
                
                while (context.current_step not in USER_INPUT_STEPS and 
                       context.current_step not in ['completed', 'error']):
                    
                    logger.info(f"Background processing step: {context.current_step}")
                    
                    # ステップを実行
                    await self.service.flow_manager.execute_single_step(context, run_config, process_id, user_id=user_id)
                    
                    # 進捗を保存
                    await self.service.persistence_service.save_context_to_db(context, process_id=process_id, user_id=user_id)
                    
                    # 小さな遅延を追加（負荷軽減）
                    await asyncio.sleep(1)
                
                # 処理完了またはユーザー入力待ちになった場合
                if context.current_step in USER_INPUT_STEPS:
                    await self.service.persistence_service.update_process_status(
                        process_id,
                        'user_input_required',
                        context.current_step,
                        metadata={'background_completed_at': datetime.now(timezone.utc).isoformat()}
                    )
                    logger.info(f"Background processing paused at user input step: {context.current_step}")
                elif context.current_step == 'completed':
                    await self.service.persistence_service.update_process_status(
                        process_id,
                        'completed',
                        context.current_step,
                        metadata={'background_completed_at': datetime.now(timezone.utc).isoformat()}
                    )
                    logger.info(f"Background processing completed for process {process_id}")
                
            except asyncio.CancelledError:
                logger.info(f"Background processing cancelled for process {process_id}")
            except Exception as e:
                logger.error(f"Background processing error for process {process_id}: {e}")
                import traceback
                traceback.print_exc()
                context.current_step = 'error'
                context.error_message = str(e)
                try:
                    await self.service.persistence_service.save_context_to_db(context, process_id=process_id, user_id=user_id)
                except Exception as db_error:
                    logger.error(f"Failed to save error context: {db_error}")
        
        # 既存のバックグラウンドタスクがあればキャンセル
        if process_id in self.service.background_processes:
            self.service.background_processes[process_id].cancel()
        
        task = asyncio.create_task(background_loop())
        self.service.background_processes[process_id] = task
        return task

    async def get_process_lock(self, process_id: str) -> asyncio.Lock:
        """プロセスIDに対応するロックを取得または作成"""
        if process_id not in self.service.process_locks:
            self.service.process_locks[process_id] = asyncio.Lock()
        return self.service.process_locks[process_id]

    async def check_and_manage_existing_connection(self, process_id: str, new_websocket: WebSocket) -> bool:
        """既存の接続をチェックし、必要に応じて管理する"""
        if process_id in self.service.active_connections:
            existing_ws = self.service.active_connections[process_id]
            
            # 既存の接続が生きている場合
            if existing_ws.client_state == WebSocketState.CONNECTED:
                console.print(f"[yellow]Process {process_id} already has an active connection. Closing old connection.[/yellow]")
                try:
                    await existing_ws.close(code=status.WS_1008_POLICY_VIOLATION, reason="New connection established")
                except Exception as e:
                    logger.warning(f"Failed to close existing WebSocket for process {process_id}: {e}")
                
                # 古いハートビートも停止
                if process_id in self.service.active_heartbeats:
                    self.service.active_heartbeats[process_id].cancel()
                    del self.service.active_heartbeats[process_id]
            
            # バックグラウンド処理も停止
            if process_id in self.service.background_processes:
                self.service.background_processes[process_id].cancel()
                del self.service.background_processes[process_id]
        
        # 新しい接続を登録
        self.service.active_connections[process_id] = new_websocket
        return True

    async def handle_websocket_connection(self, websocket: WebSocket, process_id: Optional[str] = None, user_id: Optional[str] = None):
        """WebSocket接続を処理し、記事生成プロセスを実行"""
        await websocket.accept()
        context: Optional[ArticleContext] = None
        run_config: Optional[RunConfig] = None
        generation_task: Optional[asyncio.Task] = None
        heartbeat_task: Optional[asyncio.Task] = None
        is_initialized = False
        process_lock: Optional[asyncio.Lock] = None

        try:
            # 1. 既存プロセスの再開か新規作成かを判定
            if process_id:
                # プロセスロックを取得して重複処理を防ぐ
                process_lock = await self.get_process_lock(process_id)
                
                async with process_lock:
                    # 既存の接続をチェックし、必要に応じて管理
                    await self.check_and_manage_existing_connection(process_id, websocket)
                    
                    # 既存プロセスの再開
                    context = await self.service.persistence_service.load_context_from_db(process_id, user_id)
                    if not context:
                        await websocket.send_text(json.dumps({
                            "type": "server_event",
                            "payload": {
                                "error_message": f"Process {process_id} not found or access denied"
                            }
                        }))
                        return
                
                # WebSocketオブジェクトを再設定
                context.websocket = websocket
                context.user_response_event = asyncio.Event()
                
                # ユーザーIDとプロセスIDをcontextに設定（バックグラウンド処理で必要）
                if not context.user_id:
                    context.user_id = user_id
                if not context.process_id:
                    context.process_id = process_id
                
                console.print(f"[green]Resuming process {process_id} from step {context.current_step}[/green]")
                
                # プロセス状態を更新（再開中）
                await self.service.persistence_service.update_process_status(process_id, 'resuming', context.current_step)
                
                # ログセッションを復元または作成
                await self.service.flow_manager.restore_logging_session(context, process_id, user_id)
                
                # 既存の実行設定を再作成
                session_id = process_id
                trace_id = f"trace_{session_id.replace('-', '')[:32]}"
                
                run_config = RunConfig(
                    workflow_name="SEO記事生成ワークフロー",
                    trace_id=trace_id,
                    group_id=session_id,
                    trace_metadata={
                        "keywords": context.initial_keywords,
                        "target_length": context.target_length,
                        "persona_type": context.persona_type.value if context.persona_type else None,
                        "company_name": context.company_name,
                        "session_start_time": datetime.now(timezone.utc).timestamp(),
                        "workflow_version": "1.0.0",
                        "resumed": True
                    },
                    tracing_disabled=not settings.enable_tracing,
                    trace_include_sensitive_data=settings.trace_include_sensitive_data
                )
                is_initialized = True
                
                # 復帰時にユーザー入力待ちステップの場合、適切なユーザー入力要求を送信
                await self.handle_resumed_user_input_step(context, process_id, user_id)
            else:
                # 新規プロセスの開始
                # 最初のメッセージ(生成リクエスト)を受信
                initial_data = await websocket.receive_json()
                request = GenerateArticleRequest(**initial_data)

                # スタイルテンプレートの取得と設定
                style_template_settings = {}
                if request.style_template_id:
                    try:
                        from app.common.database import supabase
                        result = supabase.table("style_guide_templates").select("settings").eq("id", request.style_template_id).execute()
                        if result.data:
                            style_template_settings = result.data[0].get("settings", {})
                            console.print(f"[cyan]Loaded style template {request.style_template_id} with settings: {style_template_settings}[/cyan]")
                    except Exception as e:
                        logger.warning(f"Failed to load style template {request.style_template_id}: {e}")

                # コンテキストと実行設定を初期化
                context = ArticleContext(
                    initial_keywords=request.initial_keywords,
                    target_age_group=request.target_age_group,
                    persona_type=request.persona_type,
                    custom_persona=request.custom_persona,
                    target_length=request.target_length,
                    num_theme_proposals=request.num_theme_proposals,
                    num_research_queries=request.num_research_queries,
                    num_persona_examples=request.num_persona_examples,
                    company_name=request.company_name,
                    company_description=request.company_description,
                    company_style_guide=request.company_style_guide,
                    # 画像モード設定追加
                    image_mode=request.image_mode,
                    image_settings=request.image_settings or {},
                    # スタイルテンプレート設定追加
                    style_template_id=request.style_template_id,
                    style_template_settings=style_template_settings,
                    # SerpAPI設定追加
                    has_serp_api_key=bool(settings.serpapi_key),
                    websocket=websocket,
                    user_response_event=asyncio.Event(),
                    user_id=user_id
                )
                
                # デバッグ: 初期化直後のimage_modeの値をログ出力
                console.print(f"[green]DEBUG: Context initialized with image_mode = {context.image_mode} (from request.image_mode = {request.image_mode})[/green]")
                
                # 単一のトレースIDとグループIDを生成して、フロー全体をまとめる
                import uuid
                session_id = str(uuid.uuid4())
                trace_id = f"trace_{session_id.replace('-', '')[:32]}"
                
                # データベースに初期状態を保存してprocess_idを取得
                if user_id:
                    process_id = await self.service.persistence_service.save_context_to_db(context, user_id=user_id)
                    context.process_id = process_id
                    console.print(f"[cyan]Created new process {process_id}[/cyan]")
                    
                    # ログセッションを初期化
                    await self.service.flow_manager.initialize_logging_session(context, process_id, user_id, request)
                
                run_config = RunConfig(
                    workflow_name="SEO記事生成ワークフロー",
                    trace_id=trace_id,
                    group_id=session_id,
                    trace_metadata={
                        "keywords": request.initial_keywords,
                        "target_length": request.target_length,
                        "persona_type": request.persona_type.value if request.persona_type else None,
                        "company_name": request.company_name,
                        "session_start_time": datetime.now(timezone.utc).timestamp(),
                        "workflow_version": "1.0.0",
                        "user_agent": "unknown"
                    },
                    tracing_disabled=not settings.enable_tracing,
                    trace_include_sensitive_data=settings.trace_include_sensitive_data
                )
                is_initialized = True

            # 3. ハートビート監視を開始
            if process_id:
                heartbeat_task = await self.start_heartbeat_monitor(websocket, process_id, context)
            
            # 4. 単一のトレースコンテキスト内でバックグラウンド生成ループを開始
            with self.service.utils.safe_trace_context("SEO記事生成ワークフロー", trace_id, session_id):
                generation_task = asyncio.create_task(
                    self.service.flow_manager.run_generation_loop(context, run_config, process_id, user_id)
                )

                # 5. クライアントからの応答を待ち受けるループ
                await self.handle_client_responses(context, generation_task, is_initialized)

        except WebSocketDisconnect:
            console.print(f"[yellow]WebSocket disconnected for process {process_id}.[/yellow]")
            await self.handle_websocket_disconnect(context, generation_task, process_id, user_id)
        except ValidationError as e:
            await self.handle_validation_error(websocket, e)
        except Exception as e:
            await self.handle_unexpected_error(websocket, context, generation_task, e)
        finally:
            await self.cleanup_websocket_connection(generation_task, heartbeat_task, process_id, websocket)

    async def handle_client_responses(self, context: ArticleContext, generation_task: asyncio.Task, is_initialized: bool):
        """クライアントからの応答を処理するループ"""
        while True:
            try:
                # タイムアウトを設定してクライアントからの応答を待つ (例: 10分)
                response_data = await asyncio.wait_for(context.websocket.receive_json(), timeout=600.0)
                
                # Generation taskが完了している場合は制限された処理のみ
                if generation_task.done():
                    if context.current_step == "completed":
                        console.print("[green]記事生成が完了済み。接続は維持中...[/green]")
                        continue
                    elif context.current_step == "error":
                        console.print("[red]記事生成でエラーが発生済み。[/red]")
                        break
                
                # 初期化完了後のメッセージはクライアント応答として処理
                if is_initialized:
                    await self.process_client_response(context, response_data)
                else:
                    console.print("[red]Received message before initialization complete[/red]")
                    await self.service.utils.send_error(context, "System not ready for client responses")

            except asyncio.TimeoutError:
                await self.service.utils.send_error(context, "Client response timeout.")
                if generation_task:
                    generation_task.cancel()
                break
            except WebSocketDisconnect:
                console.print("[yellow]WebSocket disconnected by client.[/yellow]")
                if generation_task:
                    generation_task.cancel()
                break
            except (json.JSONDecodeError) as e:
                await self.service.utils.send_error(context, f"Invalid JSON format: {e}")
            except Exception as e:
                await self.service.utils.send_error(context, f"Error processing client message: {e}")
                if generation_task:
                    generation_task.cancel()
                break

    async def process_client_response(self, context: ArticleContext, response_data: dict):
        """個別のクライアント応答を処理"""
        try:
            message = ClientResponseMessage(**response_data)
            console.print(f"[blue]クライアント応答受信: {message.response_type}, current_step: {context.current_step}, expected: {context.expected_user_input}[/blue]")
        except ValidationError as ve:
            console.print(f"[red]Invalid client response format: {ve.errors()}[/red]")
            await self.service.utils.send_error(context, f"Invalid response format: {ve}")
            return

        if context.current_step in USER_INPUT_STEPS:
            console.print(f"[blue]ステップ確認OK: {context.current_step} は受け入れ可能なステップです[/blue]")
            valid_response_types = [
                UserInputType.SELECT_PERSONA, UserInputType.SELECT_THEME, 
                UserInputType.APPROVE_PLAN, UserInputType.APPROVE_OUTLINE, 
                UserInputType.REGENERATE, UserInputType.EDIT_AND_PROCEED,
                UserInputType.EDIT_PERSONA, UserInputType.EDIT_THEME, 
                UserInputType.EDIT_PLAN, UserInputType.EDIT_OUTLINE, UserInputType.EDIT_GENERIC
            ]
            
            if message.response_type in valid_response_types:
                console.print(f"[blue]応答タイプ確認OK: {message.response_type} は有効な応答タイプです[/blue]")
                
                # 期待される応答タイプ、または再生成・編集要求の場合
                if (context.expected_user_input == message.response_type or 
                    message.response_type in [UserInputType.REGENERATE, UserInputType.EDIT_AND_PROCEED, 
                                            UserInputType.EDIT_PERSONA, UserInputType.EDIT_THEME, 
                                            UserInputType.EDIT_PLAN, UserInputType.EDIT_OUTLINE, UserInputType.EDIT_GENERIC]):
                    
                    console.print(f"[green]応答タイプマッチ！ {message.response_type} を処理します[/green]")
                    context.user_response = message
                    console.print("[green]user_response_eventを設定中...[/green]")
                    context.user_response_event.set()
                    console.print("[green]user_response_eventが設定されました！[/green]")
                else:
                    console.print(f"[red]応答タイプ不一致: expected {context.expected_user_input}, got {message.response_type}[/red]")
                    await self.service.utils.send_error(context, f"Invalid response type '{message.response_type}' for current step '{context.current_step}' expecting '{context.expected_user_input}'.")
            else:
                console.print(f"[red]予期しない応答タイプ: {message.response_type}[/red]")
                await self.service.utils.send_error(context, f"Unexpected response type '{message.response_type}' received during user input step.")
        else:
            console.print(f"[yellow]Ignoring unexpected client message during step {context.current_step} (not in input-waiting steps)[/yellow]")

    async def handle_resumed_user_input_step(self, context: ArticleContext, process_id: str, user_id: str):
        """復帰時にユーザー入力待ちステップの場合の処理"""
        from app.common.schemas import UserInputRequestPayload, UserInputType
        from app.domains.seo_article.schemas import (
            GeneratedPersonasPayload, GeneratedPersonaData,
            ThemeProposalPayload, ThemeProposalData,
            ResearchPlanPayload, OutlinePayload
        )
        
        try:
            # 復帰時に現在ステップを通知
            await self.service.utils.send_server_event(context, StatusUpdatePayload(
                step=context.current_step, 
                message=f"プロセスが復帰しました。現在のステップ: {context.current_step}",
                image_mode=getattr(context, 'image_mode', False)
            ))
            
            # ユーザー入力待ちステップの場合、適切なペイロードを送信
            if context.current_step == "persona_generated":
                await self.handle_persona_generated_resume(context)
            elif context.current_step == "theme_proposed":
                await self.handle_theme_proposed_resume(context)
            elif context.current_step == "research_plan_generated":
                await self.handle_research_plan_generated_resume(context)
            elif context.current_step == "outline_generated":
                await self.handle_outline_generated_resume(context)
            
            # 状態の変更をDBに保存
            await self.service.persistence_service.save_context_to_db(context, process_id=process_id, user_id=user_id)
            
        except Exception as e:
            logger.error(f"復帰時のユーザー入力ステップ処理でエラー: {e}")
            console.print(f"[red]復帰時のユーザー入力ステップ処理でエラー: {e}[/red]")

    async def handle_persona_generated_resume(self, context: ArticleContext):
        """ペルソナ生成完了ステップの復帰処理"""
        from app.domains.seo_article.schemas import GeneratedPersonasPayload, GeneratedPersonaData
        from app.common.schemas import UserInputRequestPayload, UserInputType
        
        if context.generated_detailed_personas:
            personas_data = [
                GeneratedPersonaData(id=i, description=desc) 
                for i, desc in enumerate(context.generated_detailed_personas)
            ]
            payload = UserInputRequestPayload(
                request_type=UserInputType.SELECT_PERSONA,
                data=GeneratedPersonasPayload(personas=personas_data).model_dump()
            )
            await self.service.utils.send_server_event(context, payload)
            context.expected_user_input = UserInputType.SELECT_PERSONA
            console.print("[cyan]復帰: ペルソナ選択画面を再表示しました。[/cyan]")
        else:
            console.print("[yellow]復帰: ペルソナが見つからないため、生成ステップに戻します。[/yellow]")
            context.current_step = "persona_generating"
            await self.service.utils.send_server_event(context, StatusUpdatePayload(
                step=context.current_step, 
                message="ペルソナ生成を再開します",
                image_mode=getattr(context, 'image_mode', False)
            ))

    async def handle_theme_proposed_resume(self, context: ArticleContext):
        """テーマ提案ステップの復帰処理"""
        from app.domains.seo_article.schemas import ThemeProposalPayload, ThemeProposalData
        from app.common.schemas import UserInputRequestPayload, UserInputType
        
        if context.generated_themes:
            themes_data = [
                ThemeProposalData(title=theme.title, description=theme.description, keywords=theme.keywords)
                for theme in context.generated_themes
            ]
            payload = UserInputRequestPayload(
                request_type=UserInputType.SELECT_THEME,
                data=ThemeProposalPayload(themes=themes_data).model_dump()
            )
            await self.service.utils.send_server_event(context, payload)
            context.expected_user_input = UserInputType.SELECT_THEME
            console.print("[cyan]復帰: テーマ選択画面を再表示しました。[/cyan]")
        else:
            console.print("[yellow]復帰: テーマが見つからないため、生成ステップに戻します。[/yellow]")
            context.current_step = "theme_generating"
            await self.service.utils.send_server_event(context, StatusUpdatePayload(
                step=context.current_step, 
                message="テーマ生成を再開します",
                image_mode=getattr(context, 'image_mode', False)
            ))

    async def handle_research_plan_generated_resume(self, context: ArticleContext):
        """リサーチ計画生成ステップの復帰処理"""
        from app.domains.seo_article.schemas import ResearchPlanPayload, ResearchPlanData
        from app.common.schemas import UserInputRequestPayload, UserInputType
        
        if context.research_plan:
            plan_data = ResearchPlanData(**context.research_plan.model_dump())
            payload = UserInputRequestPayload(
                request_type=UserInputType.APPROVE_PLAN,
                data=ResearchPlanPayload(plan=plan_data).model_dump()
            )
            await self.service.utils.send_server_event(context, payload)
            context.expected_user_input = UserInputType.APPROVE_PLAN
            console.print("[cyan]復帰: リサーチ計画承認画面を再表示しました。[/cyan]")
        else:
            console.print("[yellow]復帰: リサーチ計画が見つからないため、生成ステップに戻します。[/yellow]")
            context.current_step = "research_planning"
            await self.service.utils.send_server_event(context, StatusUpdatePayload(
                step=context.current_step, 
                message="リサーチ計画の生成を再開します",
                image_mode=getattr(context, 'image_mode', False)
            ))

    async def handle_outline_generated_resume(self, context: ArticleContext):
        """アウトライン生成ステップの復帰処理"""
        from app.domains.seo_article.schemas import OutlinePayload, OutlineData, OutlineSectionData
        from app.common.schemas import UserInputRequestPayload, UserInputType
        
        if context.generated_outline:
            outline_data = OutlineData(
                title=context.generated_outline.title,
                suggested_tone=getattr(context.generated_outline, 'suggested_tone', '丁寧で読みやすい解説調'),
                sections=[
                    OutlineSectionData(
                        heading=section.heading,
                        estimated_chars=getattr(section, 'estimated_chars', None)
                    ) for section in context.generated_outline.sections
                ]
            )
            payload = UserInputRequestPayload(
                request_type=UserInputType.APPROVE_OUTLINE,
                data=OutlinePayload(outline=outline_data).model_dump()
            )
            await self.service.utils.send_server_event(context, payload)
            context.expected_user_input = UserInputType.APPROVE_OUTLINE
            console.print("[cyan]復帰: アウトライン承認画面を再表示しました。[/cyan]")
        else:
            console.print("[yellow]復帰: アウトラインが見つからないため、生成ステップに戻します。[/yellow]")
            context.current_step = "outline_generating"
            await self.service.utils.send_server_event(context, StatusUpdatePayload(
                step=context.current_step, 
                message="アウトライン生成を再開します",
                image_mode=getattr(context, 'image_mode', False)
            ))

    async def handle_websocket_disconnect(self, context: ArticleContext, generation_task: asyncio.Task, 
                                        process_id: str, user_id: str):
        """WebSocket切断時の処理"""
        # Check if current step is disconnection-resilient
        if context and context.current_step in DISCONNECTION_RESILIENT_STEPS:
            console.print(f"[cyan]Step '{context.current_step}' is disconnection-resilient. Continuing generation in background...[/cyan]")
            
            # Clear WebSocket reference to prevent further send attempts
            if context.websocket:
                context.websocket = None
                console.print("[dim]WebSocket reference cleared from context.[/dim]")
            
            # Let generation task continue running in background
            if generation_task and not generation_task.done():
                console.print(f"[cyan]Generation task will continue for process {process_id}. Process can be resumed later.[/cyan]")
                
                # Save current context state for later resumption
                if process_id and user_id:
                    try:
                        await self.service.persistence_service.save_context_to_db(context, process_id=process_id, user_id=user_id)
                        console.print(f"[dim]Context saved for process {process_id} before disconnection.[/dim]")
                    except Exception as save_err:
                        console.print(f"[yellow]Warning: Failed to save context before disconnection: {save_err}[/yellow]")
            else:
                console.print(f"[yellow]Generation task already completed for process {process_id}.[/yellow]")
        else:
            console.print(f"[yellow]Step '{context.current_step if context else 'unknown'}' is not disconnection-resilient. Cancelling generation task.[/yellow]")
            if generation_task and not generation_task.done():
                generation_task.cancel()

    async def handle_validation_error(self, websocket: WebSocket, e: ValidationError):
        """バリデーションエラーの処理"""
        error_payload = ErrorPayload(step="initialization", error_message=f"Invalid initial request: {e.errors()}")
        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.send_json(WebSocketMessage(type="server_event", payload=error_payload).model_dump())
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        console.print(f"[bold red]Invalid initial request:[/bold red] {e.errors()}")

    async def handle_unexpected_error(self, websocket: WebSocket, context: ArticleContext, 
                                    generation_task: asyncio.Task, e: Exception):
        """予期しないエラーの処理"""
        error_message = f"An unexpected error occurred: {type(e).__name__} - {str(e)}"
        console.print(f"[bold red]{error_message}[/bold red]")
        traceback.print_exc()
        
        if websocket.client_state == WebSocketState.CONNECTED:
            try:
                error_payload = ErrorPayload(step=context.current_step if context else "unknown", error_message=error_message)
                await websocket.send_json(WebSocketMessage(type="server_event", payload=error_payload).model_dump())
            except Exception as send_err:
                console.print(f"[bold red]Failed to send error message via WebSocket: {send_err}[/bold red]")
        
        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        if generation_task and not generation_task.done():
            generation_task.cancel()

    async def cleanup_websocket_connection(self, generation_task: asyncio.Task, heartbeat_task: asyncio.Task, 
                                         process_id: str, websocket: WebSocket):
        """WebSocket接続のクリーンアップ"""
        # クリーンアップ - 切断耐性ステップでは生成タスクを継続させる
        if generation_task and not generation_task.done():
            # Check if we should let the task continue running in background
            should_continue_background = False
            if hasattr(self.service, 'current_context') and self.service.current_context:
                should_continue_background = (
                    self.service.current_context.current_step in DISCONNECTION_RESILIENT_STEPS and
                    process_id  # Only continue if we have a process_id to track it
                )
            
            if should_continue_background:
                console.print(f"[cyan]Leaving generation task running in background for process {process_id}[/cyan]")
                if process_id and process_id not in self.service.background_tasks:
                    self.service.background_tasks[process_id] = generation_task
                    console.print(f"[dim]Background task stored for process {process_id}[/dim]")
            else:
                generation_task.cancel()
                try:
                    await generation_task
                except asyncio.CancelledError:
                    console.print("Generation task cancelled.")
        
        # ハートビートタスクのクリーンアップ
        if heartbeat_task and not heartbeat_task.done():
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except asyncio.CancelledError:
                console.print("Heartbeat task cancelled.")
        
        # タスク辞書からのクリーンアップ
        if process_id:
            self.service.active_heartbeats.pop(process_id, None)
            if process_id in self.service.active_connections and self.service.active_connections[process_id] == websocket:
                del self.service.active_connections[process_id]
            if process_id in self.service.process_locks:
                try:
                    if not self.service.process_locks[process_id].locked():
                        del self.service.process_locks[process_id]
                except Exception as e:
                    logger.warning(f"Error cleaning up process lock for {process_id}: {e}")
        
        # Clean up completed background tasks
        await self.cleanup_background_tasks()
        console.print("WebSocket connection closed.")

    async def cleanup_background_tasks(self):
        """Clean up completed background tasks"""
        completed_tasks = []
        for process_id, task in self.service.background_tasks.items():
            if task.done():
                completed_tasks.append(process_id)
                try:
                    await task
                    console.print(f"[green]Background task for process {process_id} completed successfully[/green]")
                except asyncio.CancelledError:
                    console.print(f"[yellow]Background task for process {process_id} was cancelled[/yellow]")
                except Exception as e:
                    logger.warning(f"Background task for process {process_id} completed with error: {e}")
                    console.print(f"[red]Background task for process {process_id} failed: {e}[/red]")
        
        # Remove completed tasks
        for process_id in completed_tasks:
            del self.service.background_tasks[process_id]
            console.print(f"[dim]Cleaned up completed background task for process {process_id}[/dim]")
    
    async def get_background_task_status(self, process_id: str) -> Optional[str]:
        """Get the status of a background task"""
        if process_id in self.service.background_tasks:
            task = self.service.background_tasks[process_id]
            if task.done():
                try:
                    await task
                    return "completed"
                except asyncio.CancelledError:
                    return "cancelled"
                except Exception:
                    return "error"
            else:
                return "running"
        return None