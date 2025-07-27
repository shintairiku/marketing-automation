# -*- coding: utf-8 -*-
"""
記事生成サービスのファサード

このファイルは外部からのインポート互換性を維持するためのファサードとして機能します。
実際の実装は以下のファイルに分割されています:
- _websocket_handler.py: WebSocket関連の処理
- _generation_flow_manager.py: 生成フロー管理
- _process_persistence_service.py: データベース関連処理
- _generation_utils.py: ユーティリティ関数
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from ._websocket_handler import WebSocketHandler
from ._generation_flow_manager import GenerationFlowManager
from ._process_persistence_service import ProcessPersistenceService
from ._generation_utils import GenerationUtils
from .background_task_manager import BackgroundTaskManager

# ログ関連のインポート（オプション）
try:
    from app.infrastructure.logging.service import LoggingService
    from app.infrastructure.external_apis.notion_service import NotionService as NotionSyncService
    LOGGING_ENABLED = True
    NOTION_SYNC_ENABLED = True
except ImportError as e:
    LoggingService = None
    NotionSyncService = None
    LOGGING_ENABLED = False
    NOTION_SYNC_ENABLED = False

logger = logging.getLogger(__name__)

class ArticleGenerationService:
    """記事生成のコアロジックを提供し、WebSocket通信を処理するサービスクラス（ファサード）"""

    def __init__(self):
        # 各種管理用の辞書とタスク
        self.active_heartbeats: Dict[str, asyncio.Task] = {}
        self.background_processes: Dict[str, asyncio.Task] = {}
        self.background_tasks: Dict[str, asyncio.Task] = {}
        self.active_connections: Dict[str, Any] = {}  # WebSocket接続
        self.process_locks: Dict[str, asyncio.Lock] = {}
        self.workflow_loggers: Dict[str, Any] = {}

        # サービス初期化
        self.logging_service = LoggingService() if LOGGING_ENABLED else None
        self.notion_sync_service = NotionSyncService() if NOTION_SYNC_ENABLED else None

        # 各機能別のハンドラーを初期化
        self.websocket_handler = WebSocketHandler(self)
        self.flow_manager = GenerationFlowManager(self)
        self.persistence_service = ProcessPersistenceService(self)
        self.utils = GenerationUtils(self)
        self.background_task_manager = BackgroundTaskManager(self)

    # ============================================================================
    # 外部APIメソッド (互換性のために維持)
    # ============================================================================

    async def handle_websocket_connection(self, websocket, process_id: Optional[str] = None, user_id: Optional[str] = None):
        """WebSocket接続を処理し、記事生成プロセスを実行"""
        return await self.websocket_handler.handle_websocket_connection(websocket, process_id, user_id)

    async def get_generation_process_state(self, process_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Get generation process state from database"""
        return await self.persistence_service.get_generation_process_state(process_id, user_id)

    async def get_user_articles(
        self, 
        user_id: str, 
        status_filter: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get articles for a specific user."""
        return await self.persistence_service.get_user_articles(user_id, status_filter, limit, offset)

    async def get_article(self, article_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed article information by ID."""
        return await self.persistence_service.get_article(article_id, user_id)

    async def get_all_user_processes(
        self, 
        user_id: str, 
        status_filter: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get all processes (completed articles + in-progress/failed generation processes) for a user."""
        return await self.persistence_service.get_all_user_processes(user_id, status_filter, limit, offset)

    async def get_recoverable_processes(self, user_id: str, limit: int = 10) -> List[dict]:
        """Get processes that can be recovered/resumed for a user."""
        return await self.persistence_service.get_recoverable_processes(user_id, limit)

    async def update_article(
        self, 
        article_id: str, 
        user_id: str, 
        update_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """記事を更新します。"""
        return await self.persistence_service.update_article(article_id, user_id, update_data)

    async def get_background_task_status(self, process_id: str) -> Optional[str]:
        """Get the status of a background task"""
        return await self.websocket_handler.get_background_task_status(process_id)

    # ============================================================================
    # NEW: Supabase Realtime Migration Methods
    # ============================================================================

    async def create_generation_process(
        self, 
        user_id: str, 
        organization_id: Optional[str],
        request_data: Any
    ) -> str:
        """Create a new generation process in the database"""
        try:
            from ..schemas import GenerateArticleRequest
            from ..context import ArticleContext
            
            # Convert request data to proper format if needed
            if hasattr(request_data, 'dict'):
                request_dict = request_data.dict()
            elif hasattr(request_data, 'model_dump'):
                request_dict = request_data.model_dump()
            else:
                request_dict = dict(request_data) if request_data else {}
            
            # Create ArticleContext from request
            context = ArticleContext(
                initial_keywords=request_dict.get("initial_keywords", []),
                target_age_group=request_dict.get("target_age_group"),
                persona_type=request_dict.get("persona_type"),
                custom_persona=request_dict.get("custom_persona"),
                target_length=request_dict.get("target_length"),
                num_theme_proposals=request_dict.get("num_theme_proposals", 3),
                num_research_queries=request_dict.get("num_research_queries", 3),
                num_persona_examples=request_dict.get("num_persona_examples", 3),
                company_name=request_dict.get("company_name"),
                company_description=request_dict.get("company_description"),
                company_style_guide=request_dict.get("company_style_guide"),
                image_mode=request_dict.get("image_mode", False),
                image_settings=request_dict.get("image_settings", {}),
                style_template_id=request_dict.get("style_template_id"),
                websocket=None,  # Background mode
                user_response_event=None,  # Background mode
                user_id=user_id
            )
            
            # Save context to database and get process_id
            process_id = await self.persistence_service.save_context_to_db(
                context, 
                user_id=user_id, 
                organization_id=organization_id
            )
            
            logger.info(f"Created generation process {process_id} for user {user_id}")
            return process_id
            
        except Exception as e:
            logger.error(f"Error creating generation process: {e}")
            raise

    async def run_generation_background_task(
        self, 
        process_id: str, 
        user_id: str, 
        organization_id: Optional[str],
        request_data: Any
    ) -> None:
        """Run generation process as a background task"""
        try:
            await self.background_task_manager.start_generation_process(
                process_id=process_id,
                user_id=user_id,
                organization_id=organization_id,
                request_data=request_data
            )
        except Exception as e:
            logger.error(f"Error running generation background task for {process_id}: {e}")
            # Update process status to error
            try:
                await self.persistence_service.update_process_status(
                    process_id=process_id,
                    status="error",
                    metadata={"error_message": str(e)}
                )
            except:
                pass  # Don't raise on cleanup errors

    async def resume_generation_background_task(
        self, 
        process_id: str, 
        user_id: str
    ) -> None:
        """Resume generation process as a background task"""
        try:
            await self.background_task_manager.resume_generation_process(
                process_id=process_id,
                user_id=user_id
            )
        except Exception as e:
            logger.error(f"Error resuming generation background task for {process_id}: {e}")
            # Update process status to error
            try:
                await self.persistence_service.update_process_status(
                    process_id=process_id,
                    status="error",
                    metadata={"error_message": str(e)}
                )
            except:
                pass  # Don't raise on cleanup errors

    async def process_user_input(
        self, 
        process_id: str, 
        user_id: str, 
        input_data: Dict[str, Any]
    ) -> None:
        """Process user input and update process state"""
        try:
            # Load context
            context = await self.persistence_service.load_context_from_db(process_id, user_id)
            if not context:
                raise Exception(f"Process {process_id} not found")
            
            # Apply user input
            await self.background_task_manager._apply_user_input_to_context(context, input_data)
            
            # Save updated context
            await self.persistence_service.save_context_to_db(
                context, 
                process_id=process_id, 
                user_id=user_id
            )
            
            # Resolve user input waiting state using database function
            from .flow_service import get_supabase_client
            supabase = get_supabase_client()
            
            supabase.rpc('resolve_user_input', {
                'p_process_id': process_id,
                'p_user_response': input_data
            }).execute()
            
            logger.info(f"Processed user input for process {process_id}")
            
        except Exception as e:
            logger.error(f"Error processing user input for {process_id}: {e}")
            raise

    async def continue_generation_after_input(
        self, 
        process_id: str, 
        user_id: str
    ) -> None:
        """Continue generation after receiving user input"""
        try:
            # Get the most recent user input from database
            from .flow_service import get_supabase_client
            supabase = get_supabase_client()
            
            process_state = await self.persistence_service.get_generation_process_state(process_id, user_id)
            if not process_state:
                raise Exception(f"Process {process_id} not found")
            
            # Get interaction history to find last user input
            interaction_history = process_state.get("interaction_history", [])
            last_interaction = interaction_history[-1] if interaction_history else None
            
            if last_interaction and last_interaction.get("action") == "input_resolved":
                user_input = last_interaction.get("response", {})
            else:
                # Fallback: assume context already has the input applied
                user_input = {"response_type": "continue", "payload": {}}
            
            await self.background_task_manager.continue_generation_after_input(
                process_id=process_id,
                user_id=user_id,
                user_input=user_input
            )
            
        except Exception as e:
            logger.error(f"Error continuing generation after input for {process_id}: {e}")
            # Update process status to error
            try:
                await self.persistence_service.update_process_status(
                    process_id=process_id,
                    status="error",
                    metadata={"error_message": str(e)}
                )
            except:
                pass  # Don't raise on cleanup errors

    async def pause_generation_process(self, process_id: str, user_id: str) -> bool:
        """Pause a running generation process"""
        try:
            return await self.background_task_manager.pause_generation_process(process_id, user_id)
        except Exception as e:
            logger.error(f"Error pausing generation process {process_id}: {e}")
            return False

    async def cancel_generation_process(self, process_id: str, user_id: str) -> bool:
        """Cancel a generation process"""
        try:
            return await self.background_task_manager.cancel_generation_process(process_id, user_id)
        except Exception as e:
            logger.error(f"Error cancelling generation process {process_id}: {e}")
            return False

    async def get_process_events(
        self, 
        process_id: str, 
        user_id: str, 
        since_sequence: Optional[int] = None,
        limit: int = 50,
        event_types: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Get process events for real-time synchronization"""
        try:
            from .flow_service import get_supabase_client
            supabase = get_supabase_client()
            
            # Validate process access
            process_state = await self.persistence_service.get_generation_process_state(process_id, user_id)
            if not process_state:
                raise Exception("Process not found or access denied")
            
            # Build query
            query = supabase.table("process_events").select(
                "id, process_id, event_type, event_data, event_sequence, created_at"
            ).eq("process_id", process_id)
            
            if since_sequence is not None:
                query = query.gt("event_sequence", since_sequence)
            
            if event_types:
                query = query.in_("event_type", event_types)
            
            query = query.order("event_sequence", desc=False).limit(limit)
            
            result = query.execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            logger.error(f"Error getting process events for {process_id}: {e}")
            raise

    async def acknowledge_process_event(
        self, 
        process_id: str, 
        event_id: str, 
        user_id: str
    ) -> bool:
        """Acknowledge receipt of a specific event"""
        try:
            from .flow_service import get_supabase_client
            supabase = get_supabase_client()
            
            # Validate process access
            process_state = await self.persistence_service.get_generation_process_state(process_id, user_id)
            if not process_state:
                return False
            
            # Update event acknowledgment
            result = supabase.table("process_events").update({
                "acknowledged_by": supabase.rpc('array_append', {
                    'array_field': 'acknowledged_by',
                    'new_element': user_id
                })
            }).eq("id", event_id).eq("process_id", process_id).execute()
            
            return bool(result.data)
            
        except Exception as e:
            logger.error(f"Error acknowledging event {event_id}: {e}")
            return False

    # ============================================================================
    # 内部的に使用される旧メソッドのプロキシ (必要に応じて)
    # ============================================================================

    async def _start_heartbeat_monitor(self, websocket, process_id: str, context):
        """WebSocket接続のハートビート監視を開始 (旧メソッド互換性)"""
        return await self.websocket_handler.start_heartbeat_monitor(websocket, process_id, context)

    async def _handle_disconnection(self, process_id: str, context):
        """WebSocket切断時の処理 (旧メソッド互換性)"""
        return await self.websocket_handler.handle_disconnection(process_id, context)

    async def _start_background_processing(self, process_id: str, context):
        """切断されたプロセスのバックグラウンド処理を開始 (旧メソッド互換性)"""
        return await self.websocket_handler.start_background_processing(process_id, context)

    async def _get_process_lock(self, process_id: str):
        """プロセスIDに対応するロックを取得または作成 (旧メソッド互換性)"""
        return await self.websocket_handler.get_process_lock(process_id)

    async def _check_and_manage_existing_connection(self, process_id: str, new_websocket):
        """既存の接続をチェックし、必要に応じて管理する (旧メソッド互換性)"""
        return await self.websocket_handler.check_and_manage_existing_connection(process_id, new_websocket)

    async def _run_generation_loop(self, context, run_config, process_id: Optional[str] = None, user_id: Optional[str] = None):
        """記事生成のメインループ（WebSocketインタラクティブ版） (旧メソッド互換性)"""
        return await self.flow_manager.run_generation_loop(context, run_config, process_id, user_id)

    async def _execute_single_step(self, context, run_config, process_id: Optional[str] = None, user_id: Optional[str] = None):
        """単一ステップの実行（WebSocket不要版） (旧メソッド互換性)"""
        return await self.flow_manager.execute_single_step(context, run_config, process_id, user_id)

    async def _handle_user_input_step(self, context, process_id: Optional[str] = None, user_id: Optional[str] = None):
        """ユーザー入力ステップを処理し、適切な次のステップに遷移 (旧メソッド互換性)"""
        return await self.flow_manager.handle_user_input_step(context, process_id, user_id)

    async def _run_agent(self, agent, input_data, context, run_config):
        """エージェントを実行し、結果を返す（リトライ付き） (旧メソッド互換性)"""
        return await self.flow_manager.run_agent(agent, input_data, context, run_config)

    async def _save_context_to_db(self, context, process_id: Optional[str] = None, user_id: Optional[str] = None, organization_id: Optional[str] = None):
        """Save ArticleContext to database and return process_id (旧メソッド互換性)"""
        return await self.persistence_service.save_context_to_db(context, process_id, user_id, organization_id)

    async def _load_context_from_db(self, process_id: str, user_id: str):
        """Load context from database for process persistence (旧メソッド互換性)"""
        return await self.persistence_service.load_context_from_db(process_id, user_id)

    async def _send_server_event(self, context, payload):
        """WebSocket経由でサーバーイベントを送信するヘルパー関数 (旧メソッド互換性)"""
        return await self.utils.send_server_event(context, payload)

    async def _send_error(self, context, error_message: str, step: Optional[str] = None):
        """WebSocket経由でエラーイベントを送信するヘルパー関数 (旧メソッド互換性)"""
        return await self.utils.send_error(context, error_message, step)

    async def _request_user_input(self, context, request_type, data: Optional[Dict[str, Any]] = None):
        """クライアントに特定のタイプの入力を要求し、応答を待つ (旧メソッド互換性)"""
        return await self.utils.request_user_input(context, request_type, data)

    def _convert_payload_to_model(self, payload: Dict[str, Any], response_type):
        """Convert dictionary payload to appropriate Pydantic model based on response type (旧メソッド互換性)"""
        return self.utils.convert_payload_to_model(payload, response_type)

    async def _update_process_status(self, process_id: str, status: str, current_step: str = None, metadata: dict = None):
        """Update process status in database (旧メソッド互換性)"""
        return await self.persistence_service.update_process_status(process_id, status, current_step, metadata)

    async def _cleanup_background_tasks(self):
        """Clean up completed background tasks (旧メソッド互換性)"""
        return await self.websocket_handler.cleanup_background_tasks()

    async def _ensure_workflow_logger(self, context, process_id: Optional[str] = None, user_id: Optional[str] = None):
        """ワークフローロガーを確実に確保する (旧メソッド互換性)"""
        return await self.flow_manager.ensure_workflow_logger(context, process_id, user_id)

    async def _log_workflow_step(self, context, step_name: str, step_data: Dict[str, Any] = None):
        """ワークフローステップをログに記録 (旧メソッド互換性)"""
        return await self.flow_manager.log_workflow_step(context, step_name, step_data)

    async def finalize_workflow_logger(self, process_id: str, status: str = "completed"):
        """バックグラウンド処理完了時にワークフローロガーを最終化 (旧メソッド互換性)"""
        return await self.flow_manager.finalize_workflow_logger(process_id, status)

    def _extract_token_usage_from_result(self, result):
        """OpenAI Agents SDKの実行結果からトークン使用量を抽出 (旧メソッド互換性)"""
        return self.utils.extract_token_usage_from_result(result)

    def _extract_conversation_history_from_result(self, result, agent_input: str):
        """OpenAI Agents SDKの実行結果から会話履歴を詳細に抽出 (旧メソッド互換性)"""
        return self.utils.extract_conversation_history_from_result(result, agent_input)

    async def _log_tool_calls(self, execution_id: str, tool_calls: List[Dict[str, Any]]):
        """ツール呼び出しを詳細にログに記録 (旧メソッド互換性)"""
        return await self.utils.log_tool_calls(execution_id, tool_calls)

    def _estimate_cost(self, usage) -> float:
        """トークン使用量からコストを概算 (旧メソッド互換性)"""
        return self.utils.estimate_cost(usage)

    def _estimate_cost_from_metadata(self, metadata: Dict[str, Any]) -> float:
        """メタデータからコストを概算 (旧メソッド互換性)"""
        return self.utils.estimate_cost_from_metadata(metadata)

    async def _handle_resumed_user_input_step(self, context, process_id: str, user_id: str):
        """復帰時にユーザー入力待ちステップの場合の処理 (旧メソッド互換性)"""
        return await self.websocket_handler.handle_resumed_user_input_step(context, process_id, user_id)

    async def _save_image_placeholders_to_db(self, context, image_placeholders: list, section_index: int):
        """画像プレースホルダー情報をデータベースに保存 (旧メソッド互換性)"""
        return await self.persistence_service.save_image_placeholders_to_db(context, image_placeholders, section_index)

    async def _save_final_article_with_placeholders(self, context, process_id: str, user_id: str) -> str:
        """最終記事をデータベースに保存し、プレースホルダー情報も更新 (旧メソッド互換性)"""
        return await self.persistence_service.save_final_article_with_placeholders(context, process_id, user_id)

    async def _update_placeholders_article_id(self, context, article_id: str, process_id: str):
        """プレースホルダーのarticle_idを更新 (旧メソッド互換性)"""
        return await self.persistence_service.update_placeholders_article_id(context, article_id, process_id)

    async def _extract_and_save_placeholders(self, supabase, article_id: str, content: str):
        """記事内容から画像プレースホルダーを抽出してデータベースに保存する (旧メソッド互換性)"""
        return await self.persistence_service.extract_and_save_placeholders(supabase, article_id, content)

    async def _add_step_to_history(self, process_id: str, step_name: str, status: str, data: dict = None):
        """Add step to history using database function for process tracking (旧メソッド互換性)"""
        return await self.persistence_service.add_step_to_history(process_id, step_name, status, data)

    # ============================================================================
    # 古いメソッドの互換性メソッド（元のコードで使用されていた可能性があるもの）
    # ============================================================================

    def safe_trace_context(self, workflow_name: str, trace_id: str, group_id: str):
        """トレーシングエラーを安全にハンドリングするコンテキストマネージャー (旧メソッド互換性)"""
        return self.utils.safe_trace_context(workflow_name, trace_id, group_id)

    def safe_custom_span(self, name: str, data: dict = None):
        """カスタムスパンを安全にハンドリングするコンテキストマネージャー (旧メソッド互換性)"""
        return self.utils.safe_custom_span(name, data)

    def can_continue_autonomously(self, step: str) -> bool:
        """ステップが自動継続可能かどうかを判定 (旧メソッド互換性)"""
        return self.utils.can_continue_autonomously(step)

    def is_disconnection_resilient(self, step: str) -> bool:
        """WebSocket切断時でも処理継続可能なステップかどうかを判定 (旧メソッド互換性)"""
        return self.utils.is_disconnection_resilient(step)

    def requires_user_input(self, step: str) -> bool:
        """ユーザー入力が必要なステップかどうかを判定 (旧メソッド互換性)"""
        return self.utils.requires_user_input(step)

    def calculate_progress_percentage(self, context) -> int:
        """プロセスの進捗率を計算（より詳細な計算） (旧メソッド互換性)"""
        return self.utils.calculate_progress_percentage(context)