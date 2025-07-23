# -*- coding: utf-8 -*-
import asyncio
import json
import time
import traceback
import logging  # ログ追加
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Union
from fastapi import WebSocket, WebSocketDisconnect, status # <<< status をインポート
from starlette.websockets import WebSocketState # WebSocketStateをインポート
from openai import AsyncOpenAI, BadRequestError, InternalServerError, AuthenticationError
from openai.types.responses import ResponseTextDeltaEvent, ResponseCompletedEvent
from agents import Runner, RunConfig, Agent, trace
from agents.exceptions import AgentsException, MaxTurnsExceeded, ModelBehaviorError, UserError
from agents.tracing import custom_span
from rich.console import Console # ログ出力用
from pydantic import ValidationError, BaseModel # <<< BaseModel をインポート

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
from app.domains.seo_article.schemas import (
    ThemeProposal, ResearchPlan, ResearchQueryResult, ResearchReport, Outline, OutlineSection,
    RevisedArticle, ClarificationNeeded, StatusUpdate, ArticleSection, GeneratedPersonasResponse, ResearchQuery,
    ThemeProposal as ThemeIdea, # ThemeIdea を追加（エイリアス）
    SerpKeywordAnalysisReport, # SerpAPIキーワード分析レポート用のモデル追加
    ArticleSectionWithImages # 画像プレースホルダー対応モデル追加
)
from app.domains.seo_article.agents.definitions import (
    theme_agent, research_planner_agent, researcher_agent, research_synthesizer_agent,
    outline_agent, section_writer_agent, editor_agent, persona_generator_agent, # persona_generator_agent を追加
    serp_keyword_analysis_agent, # SerpAPIキーワード分析エージェント追加
    section_writer_with_images_agent # 画像プレースホルダー対応セクションライター追加
)

console = Console() # ログ出力用

# ログ設定
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # LLMログ詳細出力のためDEBUGレベルに設定

try:
    from app.infrastructure.logging.service import LoggingService # ログサービス追加
    from app.infrastructure.logging.agents_logging_integration import MultiAgentWorkflowLogger # ログ統合追加
    from app.infrastructure.external_apis.notion_service import NotionService as NotionSyncService # Notion同期追加
    from app.infrastructure.analysis.cost_calculation_service import CostCalculationService # コスト計算サービス追加
    LOGGING_ENABLED = True
    NOTION_SYNC_ENABLED = True
except ImportError as e:
    logger.warning(f"Logging system not available: {e}")
    LoggingService = None
    MultiAgentWorkflowLogger = None
    NotionSyncService = None
    CostCalculationService = None
    LOGGING_ENABLED = False
    NOTION_SYNC_ENABLED = False

# OpenAIクライアントの初期化 (ファイルスコープに戻す)
async_client = AsyncOpenAI(api_key=settings.openai_api_key)

# ステップ分類定数
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

def safe_trace_context(workflow_name: str, trace_id: str, group_id: str):
    """トレーシングエラーを安全にハンドリングするコンテキストマネージャー"""
    try:
        return trace(workflow_name=workflow_name, trace_id=trace_id, group_id=group_id)
    except Exception as e:
        logger.warning(f"トレーシング初期化に失敗しました: {e}")
        # トレーシングが失敗しても処理を続行するため、何もしないコンテキストマネージャーを返す
        from contextlib import nullcontext
        return nullcontext()

def safe_custom_span(name: str, data: dict[str, Any] | None = None):
    """カスタムスパンを安全にハンドリングするコンテキストマネージャー"""
    try:
        return custom_span(name=name, data=data)
    except Exception as e:
        logger.warning(f"カスタムスパン作成に失敗しました: {e}")
        # トレーシングが失敗しても処理を続行するため、何もしないコンテキストマネージャーを返す
        from contextlib import nullcontext
        return nullcontext()

def can_continue_autonomously(step: str) -> bool:
    """ステップが自動継続可能かどうかを判定"""
    return step in AUTONOMOUS_STEPS

def is_disconnection_resilient(step: str) -> bool:
    """WebSocket切断時でも処理継続可能なステップかどうかを判定"""
    return step in DISCONNECTION_RESILIENT_STEPS

def requires_user_input(step: str) -> bool:
    """ユーザー入力が必要なステップかどうかを判定"""
    return step in USER_INPUT_STEPS

def calculate_progress_percentage(context: "ArticleContext") -> int:
    """プロセスの進捗率を計算（より詳細な計算）"""
    step_weights = {
        'start': 0,
        'keyword_analyzing': 5,
        'keyword_analyzed': 8,
        'persona_generating': 10,
        'persona_generated': 15,
        'theme_generating': 18,
        'theme_proposed': 25,
        'research_planning': 30,
        'research_plan_generated': 35,
        'research_plan_approved': 38,
        'researching': 40,
        'research_synthesizing': 60,
        'outline_generating': 65,
        'outline_generated': 70,
        'writing_sections': 75,
        'editing': 95,
        'completed': 100,
        'error': 0
    }
    
    base_progress = step_weights.get(context.current_step, 0)
    
    # より詳細な進捗計算
    if context.current_step == 'researching' and hasattr(context, 'research_progress'):
        # リサーチ進捗を考慮
        if context.research_progress and 'current_query' in context.research_progress:
            query_progress = (context.research_progress['current_query'] / 
                            len(context.research_plan.queries) if context.research_plan else 0) * 20
            base_progress += query_progress
    
    elif context.current_step == 'writing_sections' and hasattr(context, 'sections_progress'):
        # セクション執筆進捗を考慮
        if context.sections_progress and 'current_section' in context.sections_progress:
            section_progress = (context.sections_progress['current_section'] / 
                              len(context.generated_outline.sections) if context.generated_outline else 0) * 20
            base_progress += section_progress
    
    return min(100, int(base_progress))

class ArticleGenerationService:
    """記事生成のコアロジックを提供し、WebSocket通信を処理するサービスクラス"""

    def __init__(self):
        self.active_heartbeats: Dict[str, asyncio.Task] = {}
        self.background_processes: Dict[str, asyncio.Task] = {}
        self.background_tasks: Dict[str, asyncio.Task] = {}  # Background generation tasks
        self.active_connections: Dict[str, WebSocket] = {}  # プロセスIDごとのアクティブ接続
        self.process_locks: Dict[str, asyncio.Lock] = {}    # プロセスごとのロック
        self.logging_service = LoggingService() if LOGGING_ENABLED else None  # ログサービス追加
        self.notion_sync_service = NotionSyncService() if NOTION_SYNC_ENABLED else None  # Notion同期サービス追加
        self.workflow_loggers: Dict[str, Any] = {}  # プロセスIDごとのワークフローログ

    async def _start_heartbeat_monitor(self, websocket: WebSocket, process_id: str, context: "ArticleContext") -> asyncio.Task:
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
                await self._handle_disconnection(process_id, context)
                
            except asyncio.CancelledError:
                logger.info(f"Heartbeat monitor cancelled for process {process_id}")
            except Exception as e:
                logger.error(f"Heartbeat monitor error for process {process_id}: {e}")
                await self._handle_disconnection(process_id, context)
        
        task = asyncio.create_task(heartbeat_loop())
        self.active_heartbeats[process_id] = task
        return task

    async def _handle_disconnection(self, process_id: str, context: "ArticleContext"):
        """WebSocket切断時の処理"""
        logger.info(f"Handling disconnection for process {process_id}, current step: {context.current_step}")
        
        try:
            # プロセス状態を一時停止として更新（disconnectedの代わりにpausedを使用）
            await self._update_process_status(
                process_id, 
                'paused',
                context.current_step,
                metadata={
                    'disconnected_at': datetime.now(timezone.utc).isoformat(),
                    'can_auto_resume': is_disconnection_resilient(context.current_step),
                    'progress_percentage': calculate_progress_percentage(context),
                    'reason': 'websocket_disconnected'
                }
            )
            
            # 切断耐性があるステップの場合、バックグラウンド処理を継続
            if is_disconnection_resilient(context.current_step):
                logger.info(f"Starting background processing for disconnected process {process_id}")
                await self._start_background_processing(process_id, context)
            else:
                logger.info(f"Process {process_id} requires user input, pausing until reconnection")
                
        except Exception as e:
            logger.error(f"Error handling disconnection for process {process_id}: {e}")

    async def _start_background_processing(self, process_id: str, context: "ArticleContext"):
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
                await self._ensure_workflow_logger(context, process_id, user_id)
                
                while (context.current_step not in USER_INPUT_STEPS and 
                       context.current_step not in ['completed', 'error']):
                    
                    logger.info(f"Background processing step: {context.current_step}")
                    
                    # ステップを実行
                    await self._execute_single_step(context, run_config, process_id, user_id=user_id)
                    
                    # 進捗を保存
                    await self._save_context_to_db(context, process_id=process_id, user_id=user_id)
                    
                    # 小さな遅延を追加（負荷軽減）
                    await asyncio.sleep(1)
                
                # 処理完了またはユーザー入力待ちになった場合
                if context.current_step in USER_INPUT_STEPS:
                    await self._update_process_status(
                        process_id,
                        'user_input_required',
                        context.current_step,
                        metadata={'background_completed_at': datetime.now(timezone.utc).isoformat()}
                    )
                    logger.info(f"Background processing paused at user input step: {context.current_step}")
                elif context.current_step == 'completed':
                    await self._update_process_status(
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
                    await self._save_context_to_db(context, process_id=process_id, user_id=user_id)
                except Exception as db_error:
                    logger.error(f"Failed to save error context: {db_error}")
        
        # 既存のバックグラウンドタスクがあればキャンセル
        if process_id in self.background_processes:
            self.background_processes[process_id].cancel()
        
        task = asyncio.create_task(background_loop())
        self.background_processes[process_id] = task
        return task

    async def _execute_single_step(self, context: "ArticleContext", run_config: RunConfig, process_id: Optional[str] = None, user_id: Optional[str] = None):
        """単一ステップの実行（WebSocket不要版）"""
        current_agent: Optional[Agent["ArticleContext"]] = None
        agent_input: Union[str, List[Dict[str, Any]]]
        
        # ワークフローロガーの確保（_ensure_workflow_loggerで既に処理済み）
        await self._ensure_workflow_logger(context, process_id, user_id)
        
        # データベースに現在の状態を保存
        if process_id and user_id:
            await self._save_context_to_db(context, process_id=process_id, user_id=user_id)
        
        # WebSocketがある場合のみイベント送信
        if context.websocket:
            await self._send_server_event(context, StatusUpdatePayload(step=context.current_step, message=f"Starting step: {context.current_step}", image_mode=getattr(context, 'image_mode', False)))
        
        console.rule(f"[bold yellow]Background Step: {context.current_step}[/bold yellow]")

        # --- ステップに応じた処理（WebSocket不要な処理のみ） ---
        if context.current_step == "start":
            context.current_step = "keyword_analyzing"
            await self._log_workflow_step(context, "keyword_analyzing", {
                "has_serp_api": context.has_serp_api_key,
                "initial_keywords": context.initial_keywords
            })
            if context.websocket:
                await self._send_server_event(context, StatusUpdatePayload(step=context.current_step, message="Starting keyword analysis with SerpAPI...", image_mode=getattr(context, 'image_mode', False)))

        elif context.current_step == "keyword_analyzing":
            current_agent = serp_keyword_analysis_agent
            agent_input = f"キーワード: {', '.join(context.initial_keywords)}"
            console.print(f"🤖 {current_agent.name} にSerpAPIキーワード分析を依頼します...")
            agent_output = await self._run_agent(current_agent, agent_input, context, run_config)

            if isinstance(agent_output, SerpKeywordAnalysisReport):
                context.serp_analysis_report = agent_output
                context.current_step = "keyword_analyzed"
                await self._log_workflow_step(context, "keyword_analyzed", {
                    "analyzed_articles_count": len(agent_output.analyzed_articles),
                    "main_themes_count": len(agent_output.main_themes),
                    "content_gaps_count": len(agent_output.content_gaps)
                })
                console.print("[green]SerpAPIキーワード分析が完了しました。[/green]")
                
                # 推奨目標文字数をコンテキストに設定
                if not context.target_length:
                    context.target_length = agent_output.recommended_target_length
                    console.print(f"[cyan]推奨目標文字数を設定しました: {context.target_length}文字[/cyan]")
                
                # 次のステップに進む
                context.current_step = "persona_generating"
                if context.websocket:
                    await self._send_server_event(context, StatusUpdatePayload(step=context.current_step, message="Keyword analysis completed, proceeding to persona generation.", image_mode=getattr(context, 'image_mode', False)))
            else:
                console.print("[red]SerpAPIキーワード分析中に予期しないエージェント出力タイプを受け取りました。[/red]")
                context.current_step = "error"
                return
        
        elif context.current_step == "persona_generating":
            current_agent = persona_generator_agent
            agent_input = f"キーワード: {context.initial_keywords}, 年代: {context.target_age_group}, 属性: {context.persona_type}, 独自ペルソナ: {context.custom_persona}, 生成数: {context.num_persona_examples}"
            console.print(f"🤖 {current_agent.name} に具体的なペルソナ生成を依頼します...")
            agent_output = await self._run_agent(current_agent, agent_input, context, run_config)

            if isinstance(agent_output, GeneratedPersonasResponse):
                context.generated_detailed_personas = [p.description for p in agent_output.personas]
                context.current_step = "persona_generated"
                await self._log_workflow_step(context, "persona_generated", {
                    "personas_count": len(context.generated_detailed_personas),
                    "personas_preview": [p[:100] + "..." for p in context.generated_detailed_personas]
                })
                console.print(f"[cyan]{len(context.generated_detailed_personas)}件の具体的なペルソナを生成しました。[/cyan]")
                # ユーザー入力が必要なのでここで停止
                return
            else:
                console.print("[red]ペルソナ生成中に予期しないエージェント出力タイプを受け取りました。[/red]")
                context.current_step = "error"
                return

        elif context.current_step == "theme_generating":
            if not context.selected_detailed_persona:
                console.print("[red]ペルソナが選択されていません。テーマ生成をスキップします。[/red]")
                context.current_step = "error"
                return

            current_agent = theme_agent
            agent_input = f"選択されたペルソナ「{context.selected_detailed_persona}」に向けた、キーワード「{', '.join(context.initial_keywords)}」に関するテーマを{context.num_theme_proposals}件提案してください。"
            console.print(f"🤖 {current_agent.name} にテーマ提案を依頼します...")
            agent_output = await self._run_agent(current_agent, agent_input, context, run_config)

            if isinstance(agent_output, ThemeProposal):
                context.generated_themes = agent_output.themes  # theme_proposalsからgenerated_themesに変更
                context.current_step = "theme_proposed"
                console.print(f"[cyan]{len(context.generated_themes)}件のテーマを提案しました。[/cyan]")
                
                # Save context after theme generation
                if process_id and user_id:
                    try:
                        await self._save_context_to_db(context, process_id=process_id, user_id=user_id)
                        logger.info("Context saved successfully after theme generation")
                    except Exception as save_err:
                        logger.error(f"Failed to save context after theme generation: {save_err}")
                
                # ユーザー入力要求を送信
                themes_data_for_client = [
                    ThemeProposalData(title=idea.title, description=idea.description, keywords=idea.keywords)
                    for idea in context.generated_themes
                ]
                user_response_message = await self._request_user_input(
                    context,
                    UserInputType.SELECT_THEME,
                    ThemeProposalPayload(themes=themes_data_for_client).model_dump()
                )
                
                # ユーザー応答を処理
                if user_response_message:
                    response_type = user_response_message.response_type
                    payload = user_response_message.payload

                    if response_type == UserInputType.SELECT_THEME and isinstance(payload, SelectThemePayload):
                        selected_index = payload.selected_index
                        if 0 <= selected_index < len(context.generated_themes):
                            context.selected_theme = context.generated_themes[selected_index]
                            context.current_step = "theme_selected"
                            console.print(f"[green]クライアントがテーマ「{context.selected_theme.title}」を選択しました。[/green]")
                            await self._send_server_event(context, StatusUpdatePayload(step=context.current_step, message=f"Theme selected: {context.selected_theme.title}", image_mode=getattr(context, 'image_mode', False)))
                            
                            # Save context after user theme selection
                            if process_id and user_id:
                                try:
                                    await self._save_context_to_db(context, process_id=process_id, user_id=user_id)
                                    logger.info("Context saved successfully after theme selection")
                                except Exception as save_err:
                                    logger.error(f"Failed to save context after theme selection: {save_err}")
                            
                            console.print(f"[blue]テーマ選択処理完了。次のステップ: {context.current_step}[/blue]")
                            console.print(f"[blue]ループを継続します... (process_id: {process_id})[/blue]")
                            # ループ継続のため、何もしない（次のイテレーションで theme_selected が処理される）
                        else:
                            await self._send_error(context, f"無効なテーマインデックスが選択されました: {selected_index}")
                            context.current_step = "theme_generating"  # テーマ生成からやり直し
                    elif response_type == UserInputType.REGENERATE:
                        console.print("[yellow]クライアントがテーマの再生成を要求しました。[/yellow]")
                        context.current_step = "theme_generating" 
                        context.generated_themes = [] 
                    else:
                        await self._send_error(context, f"予期しない応答 ({response_type}) がテーマ選択で受信されました。")
                        context.current_step = "theme_generating"  # テーマ生成からやり直し
                else:
                    console.print("[red]テーマ選択でクライアントからの応答がありませんでした。[/red]")
                    context.current_step = "theme_generating"  # テーマ生成からやり直し
            else:
                console.print("[red]テーマ生成中に予期しないエージェント出力タイプを受け取りました。[/red]")
                context.current_step = "error"
                return

        elif context.current_step == "research_planning":
            console.print(f"[blue]research_planningステップを開始します。selected_theme: {context.selected_theme.title if context.selected_theme else 'None'}[/blue]")
            if not context.selected_theme:
                console.print("[red]テーマが選択されていません。リサーチ計画作成をスキップします。[/red]")
                context.current_step = "error"
                return

            current_agent = research_planner_agent
            agent_input = f"選択されたテーマ「{context.selected_theme.title}」についてのリサーチ計画を作成してください。"
            console.print(f"🤖 {current_agent.name} にリサーチ計画作成を依頼します...")
            agent_output = await self._run_agent(current_agent, agent_input, context, run_config)

            if isinstance(agent_output, ResearchPlan):
                context.research_plan = agent_output
                context.current_step = "research_plan_generated"
                console.print("[cyan]リサーチ計画を生成しました。[/cyan]")
                # ユーザー入力が必要なのでここで停止
                return
            else:
                console.print("[red]リサーチ計画生成中に予期しないエージェント出力タイプを受け取りました。[/red]")
                context.current_step = "error"
                return

        elif context.current_step == "researching":
            if not context.research_plan:
                console.print("[red]承認されたリサーチ計画がありません。リサーチをスキップします。[/red]")
                context.current_step = "error"
                return

            context.research_results = []
            total_queries = len(context.research_plan.queries)
            
            for i, query in enumerate(context.research_plan.queries):
                console.print(f"🔍 リサーチクエリ {i+1}/{total_queries}: {query.query}")
                
                current_agent = researcher_agent
                agent_input = query.query
                agent_output = await self._run_agent(current_agent, agent_input, context, run_config)

                if isinstance(agent_output, ResearchQueryResult):
                    context.research_results.append(agent_output)
                    console.print(f"[green]クエリ {i+1} のリサーチが完了しました。[/green]")
                    
                    # 進捗更新
                    context.research_progress = {
                        'current_query': i + 1,
                        'total_queries': total_queries,
                        'completed_queries': i + 1
                    }
                    
                    if context.websocket:
                        await self._send_server_event(context, ResearchProgressPayload(
                            current_query=i + 1,
                            total_queries=total_queries,
                            query_text=query.query,
                            completed=False
                        ))
                else:
                    console.print(f"[red]リサーチクエリ {i+1} で予期しないエージェント出力タイプを受け取りました。[/red]")
                    context.current_step = "error"
                    return

            context.current_step = "research_synthesizing"
            console.print("[cyan]全てのリサーチクエリが完了しました。[/cyan]")

        elif context.current_step == "research_synthesizing":
            if not context.research_results:
                console.print("[red]リサーチ結果がありません。合成をスキップします。[/red]")
                context.current_step = "error"
                return

            current_agent = research_synthesizer_agent
            agent_input = f"テーマ: {context.selected_theme.title}\nリサーチ結果: {json.dumps([r.model_dump() for r in context.research_results], ensure_ascii=False, indent=2)}"
            console.print(f"🤖 {current_agent.name} にリサーチ結果の統合を依頼します...")
            agent_output = await self._run_agent(current_agent, agent_input, context, run_config)

            if isinstance(agent_output, ResearchReport):
                context.research_report = agent_output
                context.current_step = "outline_generating"
                console.print("[cyan]リサーチ報告書が完成しました。[/cyan]")
                if context.websocket:
                    await self._send_server_event(context, ResearchCompletePayload(
                        summary=agent_output.summary,
                        key_findings=agent_output.key_findings,
                        sources_used=len(context.research_results)
                    ))
            else:
                console.print("[red]リサーチ合成中に予期しないエージェント出力タイプを受け取りました。[/red]")
                context.current_step = "error"
                return

        elif context.current_step == "outline_generating":
            if not context.research_report:
                console.print("[red]リサーチ報告書がありません。アウトライン生成をスキップします。[/red]")
                context.current_step = "error"
                return

            current_agent = outline_agent
            agent_input = f"テーマ: {context.selected_theme.title}\nペルソナ: {context.selected_detailed_persona}\nリサーチ報告書: {context.research_report.model_dump_json(ensure_ascii=False, indent=2)}\n目標文字数: {context.target_length}"
            console.print(f"🤖 {current_agent.name} にアウトライン生成を依頼します...")
            agent_output = await self._run_agent(current_agent, agent_input, context, run_config)

            if isinstance(agent_output, Outline):
                context.generated_outline = agent_output
                context.current_step = "outline_generated"
                console.print(f"[cyan]アウトライン（{len(agent_output.sections)}セクション）を生成しました。[/cyan]")
                # ユーザー入力が必要なのでここで停止
                return
            else:
                console.print("[red]アウトライン生成中に予期しないエージェント出力タイプを受け取りました。[/red]")
                context.current_step = "error"
                return

        elif context.current_step == "writing_sections":
            if not context.generated_outline:
                console.print("[red]承認されたアウトラインがありません。セクション執筆をスキップします。[/red]")
                context.current_step = "error"
                return

            context.generated_sections = []
            sections = context.generated_outline.sections
            total_sections = len(sections)
            
            # 画像モードの判定
            is_image_mode = getattr(context, 'image_mode', False)
            console.print(f"[cyan]{'画像モード' if is_image_mode else '通常モード'}でセクションを執筆します。[/cyan]")
            
            for i, section in enumerate(sections):
                console.print(f"✍️ セクション {i+1}/{total_sections}: {section.heading}")
                
                # コンテキストの現在のセクションインデックスを設定
                context.current_section_index = i
                
                # 画像モードに応じてエージェントを選択
                if is_image_mode:
                    current_agent = section_writer_with_images_agent
                    console.print(f"[cyan]画像プレースホルダー対応エージェント ({current_agent.name}) を使用します。[/cyan]")
                else:
                    current_agent = section_writer_agent
                    console.print(f"[cyan]通常エージェント ({current_agent.name}) を使用します。[/cyan]")
                
                # エージェント実行に必要な情報をコンテキストに設定
                agent_input = "セクション執筆を開始します。"  # 動的プロンプトのためダミー入力
                agent_output = await self._run_agent(current_agent, agent_input, context, run_config)

                # 画像モードの場合はArticleSectionWithImagesを期待
                console.print(f"[yellow]🔍 Agent output type: {type(agent_output)}, is_image_mode: {is_image_mode}[/yellow]")
                if hasattr(agent_output, 'html_content'):
                    console.print(f"[yellow]🔍 Agent output html_content length: {len(agent_output.html_content)}[/yellow]")
                if hasattr(agent_output, 'image_placeholders'):
                    console.print(f"[yellow]🔍 Agent output image_placeholders count: {len(agent_output.image_placeholders)}[/yellow]")
                if is_image_mode and isinstance(agent_output, ArticleSectionWithImages):
                    # ArticleSectionWithImagesをArticleSectionに変換
                    article_section = ArticleSection(
                        section_index=agent_output.section_index,
                        heading=agent_output.heading,
                        html_content=agent_output.html_content
                    )
                    context.generated_sections.append(article_section)
                    
                    # 画像プレースホルダー情報をコンテキストに保存
                    if not hasattr(context, 'image_placeholders'):
                        context.image_placeholders = []
                    context.image_placeholders.extend(agent_output.image_placeholders)
                    
                    console.print(f"[green]セクション {i+1} が完了しました（画像プレースホルダー {len(agent_output.image_placeholders)} 個含む）。[/green]")
                    
                elif not is_image_mode and isinstance(agent_output, ArticleSection):
                    context.generated_sections.append(agent_output)
                    console.print(f"[green]セクション {i+1} が完了しました。[/green]")
                    
                elif isinstance(agent_output, str):
                    # 従来のHTML文字列形式の場合（旧形式対応）
                    article_section = ArticleSection(
                        section_index=i,
                        heading=section.heading,
                        html_content=agent_output
                    )
                    context.generated_sections.append(article_section)
                    console.print(f"[green]セクション {i+1} が完了しました（HTML文字列形式）。[/green]")
                    
                else:
                    console.print(f"[red]セクション {i+1} で予期しないエージェント出力タイプを受け取りました: {type(agent_output)}[/red]")
                    context.current_step = "error"
                    return
                
                # 進捗更新
                context.sections_progress = {
                    'current_section': i + 1,
                    'total_sections': total_sections,
                    'completed_sections': i + 1
                }
                
                # WebSocketでセクション完了を通知（画像モード対応）
                console.print(f"[yellow]🔍 WebSocket check: websocket={context.websocket is not None}, is_image_mode={is_image_mode}, is_ArticleSectionWithImages={isinstance(agent_output, ArticleSectionWithImages)}[/yellow]")
                if context.websocket:
                    if is_image_mode and isinstance(agent_output, ArticleSectionWithImages):
                        # 画像モードの場合：セクション完了時に完全なコンテンツと画像プレースホルダー情報を送信
                        
                        image_placeholders_data = [
                            ImagePlaceholderData(
                                placeholder_id=placeholder.placeholder_id,
                                description_jp=placeholder.description_jp,
                                prompt_en=placeholder.prompt_en,
                                alt_text=placeholder.alt_text
                            )
                            for placeholder in agent_output.image_placeholders
                        ]
                        
                        payload = SectionChunkPayload(
                            section_index=i,
                            heading=section.heading,
                            html_content_chunk="",  # 画像モードではチャンクではなく完了時に送信
                            is_complete=True,
                            section_complete_content=agent_output.html_content,
                            image_placeholders=image_placeholders_data,
                            is_image_mode=True
                        )
                        console.print(f"[cyan]📤 Sending SectionChunkPayload for image mode: section_index={i}, heading='{section.heading}', is_image_mode=True, content_length={len(agent_output.html_content)}, placeholders={len(image_placeholders_data)}[/cyan]")
                        await self._send_server_event(context, payload)
                    else:
                        console.print(f"[yellow]⚠️ Not sending SectionChunkPayload - falling back to normal mode. is_image_mode={is_image_mode}, agent_output_type={type(agent_output)}[/yellow]")
                        # 通常モードの場合：従来通りのプレビュー送信
                        content_preview = ""
                        if hasattr(agent_output, 'html_content'):
                            content_preview = agent_output.html_content[:200] + "..." if len(agent_output.html_content) > 200 else agent_output.html_content
                        elif isinstance(agent_output, str):
                            content_preview = agent_output[:200] + "..." if len(agent_output) > 200 else agent_output
                        
                        await self._send_server_event(context, SectionChunkPayload(
                            section_index=i,
                            heading=section.heading,
                            html_content_chunk=content_preview,
                            is_complete=True,
                            is_image_mode=False
                        ))

            # 全セクション完了
            context.current_step = "editing"
            console.print("[cyan]全セクションの執筆が完了しました。[/cyan]")

        elif context.current_step == "editing":
            if not context.generated_sections:
                console.print("[red]生成されたセクションがありません。編集をスキップします。[/red]")
                context.current_step = "error"
                return

            current_agent = editor_agent
            combined_content = "\n\n".join([section.content for section in context.generated_sections])
            agent_input = f"タイトル: {context.generated_outline.title}\nコンテンツ: {combined_content}\nペルソナ: {context.selected_detailed_persona}\n目標文字数: {context.target_length}"
            console.print(f"🤖 {current_agent.name} に最終編集を依頼します...")
            
            if context.websocket:
                await self._send_server_event(context, EditingStartPayload(message="記事の最終編集を開始しています..."))
            
            agent_output = await self._run_agent(current_agent, agent_input, context, run_config)

            if isinstance(agent_output, RevisedArticle):
                context.final_article = agent_output
                context.current_step = "completed"
                await self._log_workflow_step(context, "completed", {
                    "final_article_length": len(agent_output.final_html_content),
                    "sections_count": len(context.generated_sections) if hasattr(context, 'generated_sections') else 0,
                    "total_tokens_used": getattr(context, 'total_tokens_used', 0)
                })
                console.print("[green]記事の編集が完了しました！[/green]")
                
                # ワークフローロガーを最終化（記事編集完了）
                if hasattr(context, 'process_id') and context.process_id:
                    await self.finalize_workflow_logger(context.process_id, "completed")
            else:
                console.print("[red]編集中に予期しないエージェント出力タイプを受け取りました。[/red]")
                context.current_step = "error"
                return

        else:
            # ユーザー入力が必要なステップの場合は処理しない
            if context.current_step in USER_INPUT_STEPS:
                console.print(f"[yellow]ステップ {context.current_step} はユーザー入力が必要です。バックグラウンド処理を一時停止。[/yellow]")
                return
            else:
                console.print(f"[red]未定義または処理不可能なステップ: {context.current_step}[/red]")
                context.current_step = "error"
                return

    async def _get_process_lock(self, process_id: str) -> asyncio.Lock:
        """プロセスIDに対応するロックを取得または作成"""
        if process_id not in self.process_locks:
            self.process_locks[process_id] = asyncio.Lock()
        return self.process_locks[process_id]

    async def _check_and_manage_existing_connection(self, process_id: str, new_websocket: WebSocket) -> bool:
        """既存の接続をチェックし、必要に応じて管理する"""
        if process_id in self.active_connections:
            existing_ws = self.active_connections[process_id]
            
            # 既存の接続が生きている場合
            if existing_ws.client_state == WebSocketState.CONNECTED:
                console.print(f"[yellow]Process {process_id} already has an active connection. Closing old connection.[/yellow]")
                try:
                    await existing_ws.close(code=status.WS_1008_POLICY_VIOLATION, reason="New connection established")
                except Exception as e:
                    logger.warning(f"Failed to close existing WebSocket for process {process_id}: {e}")
                
                # 古いハートビートも停止
                if process_id in self.active_heartbeats:
                    self.active_heartbeats[process_id].cancel()
                    del self.active_heartbeats[process_id]
            
            # バックグラウンド処理も停止
            if process_id in self.background_processes:
                self.background_processes[process_id].cancel()
                del self.background_processes[process_id]
        
        # 新しい接続を登録
        self.active_connections[process_id] = new_websocket
        return True

    async def handle_websocket_connection(self, websocket: WebSocket, process_id: Optional[str] = None, user_id: Optional[str] = None):
        """WebSocket接続を処理し、記事生成プロセスを実行"""
        await websocket.accept()
        context: Optional[ArticleContext] = None
        run_config: Optional[RunConfig] = None
        generation_task: Optional[asyncio.Task] = None
        heartbeat_task: Optional[asyncio.Task] = None  # 初期化
        is_initialized = False  # 初期化完了フラグ
        process_lock: Optional[asyncio.Lock] = None

        try:
            # 1. 既存プロセスの再開か新規作成かを判定
            if process_id:
                # プロセスロックを取得して重複処理を防ぐ
                process_lock = await self._get_process_lock(process_id)
                
                async with process_lock:
                    # 既存の接続をチェックし、必要に応じて管理
                    await self._check_and_manage_existing_connection(process_id, websocket)
                    
                    # 既存プロセスの再開
                    context = await self._load_context_from_db(process_id, user_id)
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
                await self._update_process_status(process_id, 'resuming', context.current_step)
                
                # ログセッションを復元または作成
                console.print(f"[debug]Process restoration - LOGGING_ENABLED: {LOGGING_ENABLED}, MultiAgentWorkflowLogger: {MultiAgentWorkflowLogger is not None}[/debug]")
                console.print(f"[debug]Current workflow_loggers keys: {list(self.workflow_loggers.keys())}[/debug]")
                console.print(f"[debug]process_id {process_id} in workflow_loggers: {process_id in self.workflow_loggers}[/debug]")
                
                if LOGGING_ENABLED and MultiAgentWorkflowLogger:
                    try:
                        console.print(f"[debug]Checking workflow logger for process {process_id}. Current loggers: {list(self.workflow_loggers.keys())}[/debug]")
                        if process_id not in self.workflow_loggers:
                            console.print(f"[green]Creating new workflow logger for restored process {process_id} with user_id {user_id}[/green]")
                            console.print(f"[debug]LoggingService available: {self.logging_service is not None}[/debug]")
                            # 既存のログセッションを復元しようと試行
                            # コンテキストから初期設定を復元
                            initial_config = {
                                "initial_keywords": context.initial_keywords,
                                "seo_keywords": context.initial_keywords,
                                "image_mode_enabled": getattr(context, 'image_mode', False),
                                "article_style_info": getattr(context, 'style_template_settings', {}),
                                "generation_theme_count": getattr(context, 'num_theme_proposals', 3),
                                "target_age_group": context.target_age_group.value if context.target_age_group else None,
                                "persona_settings": {
                                    "persona_type": context.persona_type.value if context.persona_type else None,
                                    "custom_persona": context.custom_persona,
                                    "num_persona_examples": getattr(context, 'num_persona_examples', 3)
                                },
                                "company_info": {
                                    "company_name": context.company_name,
                                    "company_description": context.company_description,
                                    "company_style_guide": context.company_style_guide
                                },
                                "target_length": context.target_length,
                                "num_research_queries": getattr(context, 'num_research_queries', 5),
                                "current_step": context.current_step,
                                "restored": True
                            }
                            
                            console.print(f"[debug]Creating MultiAgentWorkflowLogger with config: {initial_config}[/debug]")
                            workflow_logger = MultiAgentWorkflowLogger(
                                article_uuid=process_id,
                                user_id=user_id,
                                organization_id=getattr(context, 'organization_id', None),
                                initial_config=initial_config
                            )
                            console.print(f"[debug]MultiAgentWorkflowLogger created. Has logging_service: {workflow_logger.logging_service is not None}[/debug]")
                            
                            # データベースに既存のログセッションがあるかチェック
                            from app.common.database import supabase
                            existing_session = supabase.table("agent_log_sessions").select("id").eq("article_uuid", process_id).execute()
                            
                            if existing_session.data:
                                # 既存のセッションIDを使用
                                workflow_logger.session_id = existing_session.data[0]["id"]
                                console.print(f"[cyan]Found existing log session {workflow_logger.session_id} for process {process_id}[/cyan]")
                            else:
                                # 新しいログセッションを作成
                                try:
                                    log_session_id = workflow_logger.initialize_session()
                                    console.print(f"[cyan]Created new log session {log_session_id} for restored process {process_id}[/cyan]")
                                except Exception as init_err:
                                    logger.error(f"Failed to initialize log session: {init_err}")
                                    console.print(f"[red]Failed to initialize log session: {init_err}[/red]")
                                    # セッション初期化に失敗してもロガーは保存する
                                
                            self.workflow_loggers[process_id] = workflow_logger
                            console.print(f"[green]Workflow logger for process {process_id} stored successfully[/green]")
                    except Exception as e:
                        logger.error(f"Failed to restore logging session: {e}")
                
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
                is_initialized = True  # 既存プロセスは既に初期化済み
                
                # 復帰時にユーザー入力待ちステップの場合、適切なユーザー入力要求を送信
                await self._handle_resumed_user_input_step(context, process_id, user_id)
            else:
                # 新規プロセスの開始
                # 最初のメッセージ(生成リクエスト)を受信
                initial_data = await websocket.receive_json()
                request = GenerateArticleRequest(**initial_data) # バリデーション

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
                websocket=websocket, # WebSocketオブジェクトをコンテキストに追加
                    user_response_event=asyncio.Event(), # ユーザー応答待ちイベント
                    user_id=user_id # ユーザーIDを設定
                )
                
                # デバッグ: 初期化直後のimage_modeの値をログ出力
                console.print(f"[green]DEBUG: Context initialized with image_mode = {context.image_mode} (from request.image_mode = {request.image_mode})[/green]")
                
                # 単一のトレースIDとグループIDを生成して、フロー全体をまとめる
                import uuid
                session_id = str(uuid.uuid4())
                trace_id = f"trace_{session_id.replace('-', '')[:32]}"
                
                # データベースに初期状態を保存してprocess_idを取得
                if user_id:
                    process_id = await self._save_context_to_db(context, user_id=user_id)
                    context.process_id = process_id  # contextにprocess_idを設定
                    console.print(f"[cyan]Created new process {process_id}[/cyan]")
                    
                    # ログセッションを初期化
                    console.print(f"[debug]LOGGING_ENABLED: {LOGGING_ENABLED}, MultiAgentWorkflowLogger: {MultiAgentWorkflowLogger is not None}[/debug]")
                    if LOGGING_ENABLED and MultiAgentWorkflowLogger:
                        try:
                            console.print(f"[green]Creating workflow logger for process {process_id} with user_id {user_id}[/green]")
                            console.print(f"[debug]Creating workflow logger for new process {process_id}[/debug]")
                            workflow_logger = MultiAgentWorkflowLogger(
                                article_uuid=process_id,
                                user_id=user_id,
                                organization_id=getattr(context, 'organization_id', None),
                                initial_config={
                                    "initial_keywords": request.initial_keywords,
                                    "seo_keywords": request.initial_keywords,
                                    "image_mode_enabled": request.image_mode,
                                    "article_style_info": style_template_settings,
                                    "generation_theme_count": request.num_theme_proposals,
                                    "target_age_group": request.target_age_group.value if request.target_age_group else None,
                                    "persona_settings": {
                                        "persona_type": request.persona_type.value if request.persona_type else None,
                                        "custom_persona": request.custom_persona,
                                        "num_persona_examples": request.num_persona_examples
                                    },
                                    "company_info": {
                                        "company_name": request.company_name,
                                        "company_description": request.company_description,
                                        "company_style_guide": request.company_style_guide
                                    },
                                    "target_length": request.target_length,
                                    "num_research_queries": request.num_research_queries,
                                    "style_template_id": request.style_template_id,
                                    "image_settings": request.image_settings or {}
                                }
                            )
                            console.print(f"[debug]MultiAgentWorkflowLogger created. Has logging_service: {workflow_logger.logging_service is not None}[/debug]")
                            try:
                                log_session_id = workflow_logger.initialize_session()
                                console.print(f"[cyan]Initialized log session {log_session_id} for process {process_id}[/cyan]")
                            except Exception as init_err:
                                logger.error(f"Failed to initialize log session for new process: {init_err}")
                                console.print(f"[red]Failed to initialize log session: {init_err}[/red]")
                                
                            self.workflow_loggers[process_id] = workflow_logger
                            console.print(f"[green]Workflow logger stored in self.workflow_loggers[{process_id}][/green]")
                        except Exception as e:
                            logger.error(f"Failed to initialize logging session: {e}")
                            # ログ初期化エラーでもプロセスは継続
                
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
                    "user_agent": "unknown"  # ユーザーエージェント情報があれば追加
                },
                tracing_disabled=not settings.enable_tracing,
                trace_include_sensitive_data=settings.trace_include_sensitive_data
                )
                is_initialized = True  # 初期化完了

            # 3. ハートビート監視を開始
            if process_id:
                heartbeat_task = await self._start_heartbeat_monitor(websocket, process_id, context)
            
            # 4. 単一のトレースコンテキスト内でバックグラウンド生成ループを開始
            with safe_trace_context("SEO記事生成ワークフロー", trace_id, session_id):
                generation_task = asyncio.create_task(
                    self._run_generation_loop(context, run_config, process_id, user_id)
                )

                # 5. クライアントからの応答を待ち受けるループ - generation taskが実行中か完了かに関わらず継続
                while True:
                    try:
                        # タイムアウトを設定してクライアントからの応答を待つ (例: 5分)
                        response_data = await asyncio.wait_for(websocket.receive_json(), timeout=600.0) # タイムアウトを10分に延長
                        
                        # Generation taskが完了している場合は制限された処理のみ
                        if generation_task.done():
                            if context.current_step == "completed":
                                console.print("[green]記事生成が完了済み。接続は維持中...[/green]")
                                continue  # 完了後は新しいメッセージを無視
                            elif context.current_step == "error":
                                console.print("[red]記事生成でエラーが発生済み。[/red]")
                                break  # エラーの場合は接続を終了
                        
                        # 初期化完了後のメッセージはクライアント応答として処理
                        if is_initialized:
                            try:
                                message = ClientResponseMessage(**response_data) # バリデーション
                                console.print(f"[blue]クライアント応答受信: {message.response_type}, current_step: {context.current_step}, expected: {context.expected_user_input}[/blue]")
                            except ValidationError as ve:
                                console.print(f"[red]Invalid client response format: {ve.errors()}[/red]")
                                await self._send_error(context, f"Invalid response format: {ve}")
                                continue

                            if context.current_step in ["persona_generated", "theme_proposed", "research_plan_generated", "outline_generated"]:
                                console.print(f"[blue]ステップ確認OK: {context.current_step} は受け入れ可能なステップです[/blue]")
                                if message.response_type in [UserInputType.SELECT_PERSONA, UserInputType.SELECT_THEME, UserInputType.APPROVE_PLAN, UserInputType.APPROVE_OUTLINE, UserInputType.REGENERATE, UserInputType.EDIT_AND_PROCEED, UserInputType.EDIT_PERSONA, UserInputType.EDIT_THEME, UserInputType.EDIT_PLAN, UserInputType.EDIT_OUTLINE, UserInputType.EDIT_GENERIC]:
                                    console.print(f"[blue]応答タイプ確認OK: {message.response_type} は有効な応答タイプです[/blue]")
                                    # 期待される応答タイプ、または再生成・編集要求の場合
                                    if context.expected_user_input == message.response_type or \
                                       message.response_type in [UserInputType.REGENERATE, UserInputType.EDIT_AND_PROCEED, UserInputType.EDIT_PERSONA, UserInputType.EDIT_THEME, UserInputType.EDIT_PLAN, UserInputType.EDIT_OUTLINE, UserInputType.EDIT_GENERIC]:
                                        
                                        console.print(f"[green]応答タイプマッチ！ {message.response_type} を処理します[/green]")
                                        console.print(f"[yellow]generation_task.done(): {generation_task.done()}[/yellow]")
                                        context.user_response = message # 応答全体をコンテキストに保存 (payloadだけでなくtypeも含む)
                                        console.print("[green]user_response_eventを設定中...[/green]")
                                        context.user_response_event.set() # 待機中のループに応答があったことを通知
                                        console.print("[green]user_response_eventが設定されました！[/green]")
                                    else:
                                        # 期待する具体的な選択/承認タイプと異なる場合 (例: SELECT_THEMEを期待しているときにAPPROVE_PLANが来たなど)
                                        console.print(f"[red]応答タイプ不一致: expected {context.expected_user_input}, got {message.response_type}[/red]")
                                        await self._send_error(context, f"Invalid response type '{message.response_type}' for current step '{context.current_step}' expecting '{context.expected_user_input}'.")
                                else:
                                    # 予期しない応答タイプ (承認/選択/再生成/編集以外)
                                    console.print(f"[red]予期しない応答タイプ: {message.response_type}[/red]")
                                    await self._send_error(context, f"Unexpected response type '{message.response_type}' received during user input step.")
                            else:
                                # ユーザー入力待ちでないときにメッセージが来た場合
                                console.print(f"[yellow]Ignoring unexpected client message during step {context.current_step} (not in input-waiting steps)[/yellow]")
                        else:
                            # まだ初期化されていない場合（通常はここに来ることはない）
                            console.print("[red]Received message before initialization complete[/red]")
                            await self._send_error(context, "System not ready for client responses")

                    except asyncio.TimeoutError:
                        await self._send_error(context, "Client response timeout.")
                        if generation_task:
                            generation_task.cancel()
                        break
                    except WebSocketDisconnect:
                        console.print("[yellow]WebSocket disconnected by client.[/yellow]")
                        if generation_task:
                            generation_task.cancel()
                        break
                    except (json.JSONDecodeError) as e:
                        await self._send_error(context, f"Invalid JSON format: {e}")
                        # 不正なメッセージを受け取った場合、処理を続ける
                    except Exception as e: # その他の予期せぬエラー
                        await self._send_error(context, f"Error processing client message: {e}")
                        if generation_task:
                            generation_task.cancel()
                        break

        except WebSocketDisconnect:
            console.print(f"[yellow]WebSocket disconnected for process {process_id}.[/yellow]")
            
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
                            await self._save_context_to_db(context, process_id=process_id, user_id=user_id)
                            console.print(f"[dim]Context saved for process {process_id} before disconnection.[/dim]")
                        except Exception as save_err:
                            console.print(f"[yellow]Warning: Failed to save context before disconnection: {save_err}[/yellow]")
                    
                    # Don't cancel the generation task - let it continue
                    # The finally block will handle cleanup only if the task is already done
                else:
                    console.print(f"[yellow]Generation task already completed for process {process_id}.[/yellow]")
            else:
                console.print(f"[yellow]Step '{context.current_step if context else 'unknown'}' is not disconnection-resilient. Cancelling generation task.[/yellow]")
                if generation_task and not generation_task.done():
                    generation_task.cancel()
        except ValidationError as e: # 初期リクエストのバリデーションエラー
            error_payload = ErrorPayload(step="initialization", error_message=f"Invalid initial request: {e.errors()}")
            # WebSocketが接続状態か確認してから送信
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.send_json(WebSocketMessage(type="server_event", payload=error_payload).model_dump())
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION) # <<< status をインポートしたのでOK
            console.print(f"[bold red]Invalid initial request:[/bold red] {e.errors()}")
        except Exception as e:
            error_message = f"An unexpected error occurred: {type(e).__name__} - {str(e)}"
            console.print(f"[bold red]{error_message}[/bold red]")
            traceback.print_exc()
            # WebSocket接続が確立していればエラーメッセージを送信試行
            if websocket.client_state == WebSocketState.CONNECTED:
                 try:
                     error_payload = ErrorPayload(step=context.current_step if context else "unknown", error_message=error_message)
                     await websocket.send_json(WebSocketMessage(type="server_event", payload=error_payload).model_dump())
                 except Exception as send_err:
                     console.print(f"[bold red]Failed to send error message via WebSocket: {send_err}[/bold red]")
            # 接続を閉じる
            if websocket.client_state == WebSocketState.CONNECTED:
                 await websocket.close(code=status.WS_1011_INTERNAL_ERROR) # <<< status をインポートしたのでOK
            if generation_task and not generation_task.done():
                generation_task.cancel()
        finally:
            # クリーンアップ - 切断耐性ステップでは生成タスクを継続させる
            if generation_task and not generation_task.done():
                # Check if we should let the task continue running in background
                should_continue_background = (
                    context and 
                    context.current_step in DISCONNECTION_RESILIENT_STEPS and
                    process_id  # Only continue if we have a process_id to track it
                )
                
                if should_continue_background:
                    console.print(f"[cyan]Leaving generation task running in background for process {process_id}[/cyan]")
                    # Don't cancel - let it run in background
                    # Store the task reference for potential cleanup later
                    if process_id and process_id not in self.background_tasks:
                        self.background_tasks[process_id] = generation_task
                        console.print(f"[dim]Background task stored for process {process_id}[/dim]")
                else:
                    # Cancel the task as normal
                    generation_task.cancel()
                    try:
                        await generation_task # キャンセル完了を待つ
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
                self.active_heartbeats.pop(process_id, None)
                # アクティブ接続からも削除
                if process_id in self.active_connections and self.active_connections[process_id] == websocket:
                    del self.active_connections[process_id]
                # プロセスロックも必要に応じてクリーンアップ（他の接続がない場合）
                if process_id in self.process_locks:
                    try:
                        # ロックが取得されていないことを確認してから削除
                        if not self.process_locks[process_id].locked():
                            del self.process_locks[process_id]
                    except Exception as e:
                        logger.warning(f"Error cleaning up process lock for {process_id}: {e}")
                
            # Clean up completed background tasks
            await self._cleanup_background_tasks()
            
            # WebSocket終了処理は既に上で実行済みなので重複を避ける
            console.print("WebSocket connection closed.")

    async def _cleanup_background_tasks(self):
        """Clean up completed background tasks"""
        completed_tasks = []
        for process_id, task in self.background_tasks.items():
            if task.done():
                completed_tasks.append(process_id)
                try:
                    # Get the result or exception to clean up the task
                    await task
                    console.print(f"[green]Background task for process {process_id} completed successfully[/green]")
                except asyncio.CancelledError:
                    console.print(f"[yellow]Background task for process {process_id} was cancelled[/yellow]")
                except Exception as e:
                    logger.warning(f"Background task for process {process_id} completed with error: {e}")
                    console.print(f"[red]Background task for process {process_id} failed: {e}[/red]")
        
        # Remove completed tasks
        for process_id in completed_tasks:
            del self.background_tasks[process_id]
            console.print(f"[dim]Cleaned up completed background task for process {process_id}[/dim]")
    
    async def get_background_task_status(self, process_id: str) -> Optional[str]:
        """Get the status of a background task"""
        if process_id in self.background_tasks:
            task = self.background_tasks[process_id]
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

    async def _send_server_event(self, context: ArticleContext, payload: BaseModel): # <<< BaseModel をインポートしたのでOK
        """WebSocket経由でサーバーイベントを送信するヘルパー関数"""
        if context.websocket:
            try:
                # Check WebSocket state before attempting to send
                if context.websocket.client_state == WebSocketState.CONNECTED:
                    message = ServerEventMessage(payload=payload)
                    await context.websocket.send_json(message.model_dump())
                else:
                    console.print("[yellow]WebSocket not connected, skipping message send.[/yellow]")
            except WebSocketDisconnect:
                console.print("[yellow]WebSocket disconnected while trying to send message.[/yellow]")
                # Don't re-raise - handle gracefully and continue execution
                context.websocket = None  # Clear the reference to prevent further attempts
            except Exception as e:
                console.print(f"[bold red]Error sending WebSocket message: {e}[/bold red]")
                # Don't re-raise general exceptions either - log and continue
        else:
            console.print(f"[Warning] WebSocket not available. Event discarded: {payload.model_dump_json(indent=2)}")

    async def _send_error(self, context: ArticleContext, error_message: str, step: Optional[str] = None):
        """WebSocket経由でエラーイベントを送信するヘルパー関数"""
        current_step = step or (context.current_step if context else "unknown")
        payload = ErrorPayload(step=current_step, error_message=error_message)
        await self._send_server_event(context, payload)

    async def _handle_resumed_user_input_step(self, context: ArticleContext, process_id: str, user_id: str):
        """復帰時にユーザー入力待ちステップの場合の処理"""
        from app.common.schemas import UserInputRequestPayload, UserInputType
        from app.domains.seo_article.schemas import (
            GeneratedPersonasPayload, GeneratedPersonaData,
            ThemeProposalPayload, ThemeProposalData,
            ResearchPlanPayload, OutlinePayload
        )
        
        try:
            # 復帰時に現在ステップを通知
            await self._send_server_event(context, StatusUpdatePayload(
                step=context.current_step, 
                message=f"プロセスが復帰しました。現在のステップ: {context.current_step}",
                image_mode=getattr(context, 'image_mode', False)
            ))
            
            # ユーザー入力待ちステップの場合、適切なペイロードを送信
            if context.current_step == "persona_generated":
                if context.generated_detailed_personas:
                    personas_data = [
                        GeneratedPersonaData(id=i, description=desc) 
                        for i, desc in enumerate(context.generated_detailed_personas)
                    ]
                    # 復帰時もUserInputRequestPayload形式で送信する
                    payload = UserInputRequestPayload(
                        request_type=UserInputType.SELECT_PERSONA,
                        data=GeneratedPersonasPayload(personas=personas_data).model_dump()
                    )
                    await self._send_server_event(context, payload)
                    # 復帰時にexpected_user_inputを設定
                    context.expected_user_input = UserInputType.SELECT_PERSONA
                    console.print("[cyan]復帰: ペルソナ選択画面を再表示しました。[/cyan]")
                else:
                    # ペルソナがない場合は生成ステップに戻す
                    console.print("[yellow]復帰: ペルソナが見つからないため、生成ステップに戻します。[/yellow]")
                    context.current_step = "persona_generating"
                    await self._send_server_event(context, StatusUpdatePayload(
                        step=context.current_step, 
                        message="ペルソナ生成を再開します",
                        image_mode=getattr(context, 'image_mode', False)
                    ))
                    
            elif context.current_step == "theme_proposed":
                if context.generated_themes:
                    themes_data = [
                        ThemeProposalData(title=theme.title, description=theme.description, keywords=theme.keywords)
                        for theme in context.generated_themes
                    ]
                    # 復帰時もUserInputRequestPayload形式で送信する
                    payload = UserInputRequestPayload(
                        request_type=UserInputType.SELECT_THEME,
                        data=ThemeProposalPayload(themes=themes_data).model_dump()
                    )
                    await self._send_server_event(context, payload)
                    # 復帰時にexpected_user_inputを設定
                    context.expected_user_input = UserInputType.SELECT_THEME
                    console.print("[cyan]復帰: テーマ選択画面を再表示しました。[/cyan]")
                else:
                    # テーマがない場合は生成ステップに戻す
                    console.print("[yellow]復帰: テーマが見つからないため、生成ステップに戻します。[/yellow]")
                    context.current_step = "theme_generating"
                    await self._send_server_event(context, StatusUpdatePayload(
                        step=context.current_step, 
                        message="テーマ生成を再開します",
                        image_mode=getattr(context, 'image_mode', False)
                    ))
                    
            elif context.current_step == "research_plan_generated":
                if context.research_plan:
                    from app.domains.seo_article.schemas import ResearchPlanData
                    plan_data = ResearchPlanData(**context.research_plan.model_dump())
                    # 復帰時もUserInputRequestPayload形式で送信する
                    payload = UserInputRequestPayload(
                        request_type=UserInputType.APPROVE_PLAN,
                        data=ResearchPlanPayload(plan=plan_data).model_dump()
                    )
                    await self._send_server_event(context, payload)
                    # 復帰時にexpected_user_inputを設定
                    context.expected_user_input = UserInputType.APPROVE_PLAN
                    console.print("[cyan]復帰: リサーチ計画承認画面を再表示しました。[/cyan]")
                else:
                    # リサーチ計画がない場合は生成ステップに戻す
                    console.print("[yellow]復帰: リサーチ計画が見つからないため、生成ステップに戻します。[/yellow]")
                    context.current_step = "research_planning"
                    await self._send_server_event(context, StatusUpdatePayload(
                        step=context.current_step, 
                        message="リサーチ計画の生成を再開します",
                        image_mode=getattr(context, 'image_mode', False)
                    ))
                    
            elif context.current_step == "outline_generated":
                if context.generated_outline:
                    from app.domains.seo_article.schemas import OutlineData, OutlineSectionData
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
                    # 復帰時もUserInputRequestPayload形式で送信する
                    payload = UserInputRequestPayload(
                        request_type=UserInputType.APPROVE_OUTLINE,
                        data=OutlinePayload(outline=outline_data).model_dump()
                    )
                    await self._send_server_event(context, payload)
                    # 復帰時にexpected_user_inputを設定
                    context.expected_user_input = UserInputType.APPROVE_OUTLINE
                    console.print("[cyan]復帰: アウトライン承認画面を再表示しました。[/cyan]")
                else:
                    # アウトラインがない場合は生成ステップに戻す
                    console.print("[yellow]復帰: アウトラインが見つからないため、生成ステップに戻します。[/yellow]")
                    context.current_step = "outline_generating"
                    await self._send_server_event(context, StatusUpdatePayload(
                        step=context.current_step, 
                        message="アウトライン生成を再開します",
                        image_mode=getattr(context, 'image_mode', False)
                    ))
            
            # 状態の変更をDBに保存
            await self._save_context_to_db(context, process_id=process_id, user_id=user_id)
            
        except Exception as e:
            logger.error(f"復帰時のユーザー入力ステップ処理でエラー: {e}")
            console.print(f"[red]復帰時のユーザー入力ステップ処理でエラー: {e}[/red]")


    async def _request_user_input(self, context: ArticleContext, request_type: UserInputType, data: Optional[Dict[str, Any]] = None):
        """クライアントに特定のタイプの入力を要求し、応答を待つ"""
        context.expected_user_input = request_type
        context.user_response = None # 前回の応答をクリア
        context.user_response_event.clear() # イベントをリセット

        payload = UserInputRequestPayload(request_type=request_type, data=data)
        await self._send_server_event(context, payload)

        # クライアントからの応答を待つ (タイムアウトは handle_websocket_connection で処理)
        console.print(f"[blue]ユーザー応答を待機中... (request_type: {request_type})[/blue]")
        await context.user_response_event.wait()
        console.print("[blue]ユーザー応答を受信しました！[/blue]")

        response = context.user_response
        context.user_response = None # 応答をクリア
        context.expected_user_input = None # 期待する入力をクリア
        console.print(f"[blue]ユーザー応答処理完了: {response.response_type if response else 'None'}[/blue]")
        return response

    async def _handle_user_input_step(self, context: ArticleContext, process_id: Optional[str] = None, user_id: Optional[str] = None):
        """ユーザー入力ステップを処理し、適切な次のステップに遷移"""
        from app.common.schemas import UserInputType
        from app.domains.seo_article.schemas import (
            GeneratedPersonasPayload, GeneratedPersonaData,
            ThemeProposalPayload, ThemeProposalData,
            ResearchPlanPayload, OutlinePayload,
            SelectPersonaPayload, SelectThemePayload, ApprovePayload,
            EditAndProceedPayload
        )
        from pydantic import ValidationError
        
        console.print(f"[blue]ユーザー入力ステップを処理中: {context.current_step}[/blue]")
        
        if context.current_step == "persona_generated":
            if context.generated_detailed_personas:
                personas_data_for_client = [GeneratedPersonaData(id=i, description=desc) for i, desc in enumerate(context.generated_detailed_personas)]
                
                user_response_message = await self._request_user_input(
                    context,
                    UserInputType.SELECT_PERSONA,
                    GeneratedPersonasPayload(personas=personas_data_for_client).model_dump()
                )
                
                if user_response_message:
                    response_type = user_response_message.response_type
                    payload = user_response_message.payload

                    if response_type == UserInputType.SELECT_PERSONA and isinstance(payload, SelectPersonaPayload):
                        selected_id = payload.selected_id
                        if 0 <= selected_id < len(context.generated_detailed_personas):
                            context.selected_detailed_persona = context.generated_detailed_personas[selected_id]
                            context.current_step = "persona_selected"
                            console.print(f"[green]ペルソナが選択されました: {context.selected_detailed_persona[:100]}...[/green]")
                            await self._send_server_event(context, StatusUpdatePayload(step=context.current_step, message="Persona selected, proceeding to theme generation.", image_mode=getattr(context, 'image_mode', False)))
                            
                            # Save context after persona selection
                            if process_id and user_id:
                                try:
                                    await self._save_context_to_db(context, process_id=process_id, user_id=user_id)
                                    logger.info("Context saved successfully after persona selection")
                                except Exception as save_err:
                                    logger.error(f"Failed to save context after persona selection: {save_err}")
                        else:
                            await self._send_error(context, f"無効なペルソナインデックス: {selected_id}")
                            context.current_step = "error"
                    elif response_type == UserInputType.REGENERATE:
                        console.print("[yellow]ペルソナの再生成が要求されました。[/yellow]")
                        context.current_step = "persona_generating"
                        context.generated_detailed_personas = []
                    elif response_type == UserInputType.EDIT_AND_PROCEED and isinstance(payload, EditAndProceedPayload):
                        try:
                            edited_persona_data = payload.edited_content
                            console.print(f"[blue]EditAndProceedPayload received for persona: {edited_persona_data}[/blue]")
                            
                            # Handle different payload formats
                            description = None
                            if isinstance(edited_persona_data, dict):
                                description = edited_persona_data.get("description")
                            elif isinstance(edited_persona_data, str):
                                description = edited_persona_data
                            
                            if description and isinstance(description, str) and description.strip():
                                context.selected_detailed_persona = description.strip()
                                context.current_step = "persona_selected"
                                console.print(f"[green]ペルソナが編集され選択されました: {description[:100]}...[/green]")
                                await self._send_server_event(context, StatusUpdatePayload(step=context.current_step, message="Persona edited and selected.", image_mode=getattr(context, 'image_mode', False)))
                                
                                # Save context after persona editing
                                if process_id and user_id:
                                    try:
                                        await self._save_context_to_db(context, process_id=process_id, user_id=user_id)
                                        logger.info("Context saved successfully after persona editing")
                                    except Exception as save_err:
                                        logger.error(f"Failed to save context after persona editing: {save_err}")
                            else:
                                await self._send_error(context, f"編集されたペルソナの形式が無効です。受信データ: {edited_persona_data}")
                                context.current_step = "error"
                        except (ValidationError, TypeError, AttributeError) as e:
                            await self._send_error(context, f"ペルソナ編集エラー: {e}")
                            context.current_step = "error"
                    else:
                        await self._send_error(context, f"予期しない応答タイプ: {response_type}")
                        context.current_step = "error"
                else:
                    console.print("[red]ペルソナ選択でユーザー応答がありませんでした。[/red]")
                    context.current_step = "error"
            else:
                console.print("[yellow]ペルソナが見つからないため生成ステップに戻します。[/yellow]")
                context.current_step = "persona_generating"
        
        elif context.current_step == "theme_proposed":
            if context.generated_themes:
                themes_data = [
                    ThemeProposalData(title=theme.title, description=theme.description, keywords=theme.keywords)
                    for theme in context.generated_themes
                ]
                
                user_response_message = await self._request_user_input(
                    context,
                    UserInputType.SELECT_THEME,
                    ThemeProposalPayload(themes=themes_data).model_dump()
                )
                
                if user_response_message:
                    response_type = user_response_message.response_type
                    payload = user_response_message.payload

                    if response_type == UserInputType.SELECT_THEME and isinstance(payload, SelectThemePayload):
                        selected_index = payload.selected_index
                        if 0 <= selected_index < len(context.generated_themes):
                            context.selected_theme = context.generated_themes[selected_index]
                            context.current_step = "theme_selected"
                            console.print(f"[green]テーマ「{context.selected_theme.title}」が選択されました。[/green]")
                            await self._send_server_event(context, StatusUpdatePayload(step=context.current_step, message=f"Theme selected: {context.selected_theme.title}", image_mode=getattr(context, 'image_mode', False)))
                            
                            # Save context after theme selection
                            if process_id and user_id:
                                try:
                                    await self._save_context_to_db(context, process_id=process_id, user_id=user_id)
                                    logger.info("Context saved successfully after theme selection")
                                except Exception as save_err:
                                    logger.error(f"Failed to save context after theme selection: {save_err}")
                        else:
                            await self._send_error(context, f"無効なテーマインデックス: {selected_index}")
                            context.current_step = "error"
                    elif response_type == UserInputType.REGENERATE:
                        console.print("[yellow]テーマの再生成が要求されました。[/yellow]")
                        context.current_step = "theme_generating"
                        context.generated_themes = []
                    elif response_type == UserInputType.EDIT_AND_PROCEED and isinstance(payload, EditAndProceedPayload):
                        try:
                            edited_theme_data = payload.edited_content
                            if isinstance(edited_theme_data.get("title"), str) and \
                               isinstance(edited_theme_data.get("description"), str) and \
                               isinstance(edited_theme_data.get("keywords"), list):
                                context.selected_theme = ThemeIdea(**edited_theme_data)
                                context.current_step = "theme_selected"
                                console.print(f"[green]テーマが編集され選択されました: {context.selected_theme.title}[/green]")
                                await self._send_server_event(context, StatusUpdatePayload(step=context.current_step, message="Theme edited and selected.", image_mode=getattr(context, 'image_mode', False)))
                                
                                # Save context after theme editing
                                if process_id and user_id:
                                    try:
                                        await self._save_context_to_db(context, process_id=process_id, user_id=user_id)
                                        logger.info("Context saved successfully after theme editing")
                                    except Exception as save_err:
                                        logger.error(f"Failed to save context after theme editing: {save_err}")
                            else:
                                await self._send_error(context, "編集されたテーマの形式が無効です。")
                                context.current_step = "error"
                        except (ValidationError, TypeError, AttributeError) as e:
                            await self._send_error(context, f"テーマ編集エラー: {e}")
                            context.current_step = "error"
                    elif response_type == UserInputType.EDIT_THEME and isinstance(payload, EditThemePayload):
                        try:
                            edited_theme_data = payload.edited_theme
                            if isinstance(edited_theme_data.get("title"), str) and \
                               isinstance(edited_theme_data.get("description"), str) and \
                               isinstance(edited_theme_data.get("keywords"), list):
                                context.selected_theme = ThemeIdea(**edited_theme_data)
                                context.current_step = "theme_selected"
                                console.print(f"[green]テーマが編集され選択されました: {context.selected_theme.title}[/green]")
                                await self._send_server_event(context, StatusUpdatePayload(step=context.current_step, message="Theme edited and selected.", image_mode=getattr(context, 'image_mode', False)))
                                
                                # Save context after theme editing
                                if process_id and user_id:
                                    try:
                                        await self._save_context_to_db(context, process_id=process_id, user_id=user_id)
                                        logger.info("Context saved successfully after theme editing")
                                    except Exception as save_err:
                                        logger.error(f"Failed to save context after theme editing: {save_err}")
                            else:
                                await self._send_error(context, "編集されたテーマの形式が無効です。")
                                context.current_step = "error"
                        except (ValidationError, TypeError, AttributeError) as e:
                            await self._send_error(context, f"テーマ編集エラー: {e}")
                            context.current_step = "error"
                    elif response_type == UserInputType.EDIT_GENERIC:
                        try:
                            # EDIT_GENERIC - generic edit handler for theme step
                            console.print(f"[yellow]EDIT_GENERIC received for theme step. Payload: {payload}[/yellow]")
                            if hasattr(payload, 'edited_content'):
                                edited_theme_data = payload.edited_content
                                if isinstance(edited_theme_data.get("title"), str) and \
                                   isinstance(edited_theme_data.get("description"), str) and \
                                   isinstance(edited_theme_data.get("keywords"), list):
                                    context.selected_theme = ThemeIdea(**edited_theme_data)
                                    context.current_step = "theme_selected"
                                    console.print(f"[green]テーマが編集され選択されました（EDIT_GENERIC）: {context.selected_theme.title}[/green]")
                                    await self._send_server_event(context, StatusUpdatePayload(step=context.current_step, message="Theme edited and selected.", image_mode=getattr(context, 'image_mode', False)))
                                    
                                    # Save context after theme editing
                                    if process_id and user_id:
                                        try:
                                            await self._save_context_to_db(context, process_id=process_id, user_id=user_id)
                                            logger.info("Context saved successfully after theme editing")
                                        except Exception as save_err:
                                            logger.error(f"Failed to save context after theme editing: {save_err}")
                                else:
                                    await self._send_error(context, "EDIT_GENERIC: 編集されたテーマの形式が無効です。")
                                    context.current_step = "error"
                            else:
                                await self._send_error(context, "EDIT_GENERIC: 編集されたテーマの形式が無効です。")
                                context.current_step = "error"
                        except Exception as e:
                            await self._send_error(context, f"EDIT_GENERIC テーマ編集エラー: {e}")
                            context.current_step = "error"
                    else:
                        await self._send_error(context, f"予期しない応答タイプ: {response_type}")
                        context.current_step = "error"
                else:
                    console.print("[red]テーマ選択でユーザー応答がありませんでした。[/red]")
                    context.current_step = "error"
            else:
                console.print("[yellow]テーマが見つからないため生成ステップに戻します。[/yellow]")
                context.current_step = "theme_generating"
        
        elif context.current_step == "outline_generated":
            if context.generated_outline:
                from app.domains.seo_article.schemas import OutlineData, OutlineSectionData
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
                
                user_response_message = await self._request_user_input(
                    context,
                    UserInputType.APPROVE_OUTLINE,
                    OutlinePayload(outline=outline_data).model_dump()
                )
                
                if user_response_message:
                    response_type = user_response_message.response_type
                    payload = user_response_message.payload

                    if response_type == UserInputType.APPROVE_OUTLINE and isinstance(payload, ApprovePayload):
                        if payload.approved:
                            context.current_step = "outline_approved"
                            console.print("[green]アウトラインが承認されました。記事執筆を開始します。[/green]")
                            await self._send_server_event(context, StatusUpdatePayload(step=context.current_step, message="Outline approved, starting article writing.", image_mode=getattr(context, 'image_mode', False)))
                            
                            # Save context after outline approval
                            if process_id and user_id:
                                try:
                                    await self._save_context_to_db(context, process_id=process_id, user_id=user_id)
                                    logger.info("Context saved successfully after outline approval")
                                except Exception as save_err:
                                    logger.error(f"Failed to save context after outline approval: {save_err}")
                        else:
                            console.print("[yellow]アウトラインが却下されました。再生成します。[/yellow]")
                            context.current_step = "outline_generating"
                    elif response_type == UserInputType.REGENERATE:
                        console.print("[yellow]アウトラインの再生成が要求されました。[/yellow]")
                        context.current_step = "outline_generating"
                    elif response_type == UserInputType.EDIT_OUTLINE and isinstance(payload, EditOutlinePayload):
                        try:
                            edited_outline_data = payload.edited_outline
                            console.print("[green]アウトラインが編集されました（EditOutlinePayload）。[/green]")
                            # 編集されたアウトラインを適用
                            if isinstance(edited_outline_data.get("title"), str) and \
                               isinstance(edited_outline_data.get("sections"), list):
                                from app.domains.seo_article.schemas import Outline, OutlineSection
                                edited_sections = []
                                for section_data in edited_outline_data["sections"]:
                                    if isinstance(section_data.get("heading"), str):
                                        edited_sections.append(OutlineSection(
                                            heading=section_data["heading"],
                                            estimated_chars=section_data.get("estimated_chars", 400)
                                        ))
                                
                                context.generated_outline = Outline(
                                    status="outline",
                                    title=edited_outline_data["title"],
                                    suggested_tone=edited_outline_data.get("suggested_tone", "丁寧で読みやすい解説調"),
                                    sections=edited_sections
                                )
                                context.current_step = "outline_approved"
                                console.print("[green]編集されたアウトラインが適用されました（EditOutlinePayload）。[/green]")
                                await self._send_server_event(context, StatusUpdatePayload(step=context.current_step, message="Edited outline applied and approved.", image_mode=getattr(context, 'image_mode', False)))
                                
                                # Save context after outline editing
                                if process_id and user_id:
                                    try:
                                        await self._save_context_to_db(context, process_id=process_id, user_id=user_id)
                                        logger.info("Context saved successfully after outline editing")
                                    except Exception as save_err:
                                        logger.error(f"Failed to save context after outline editing: {save_err}")
                            else:
                                await self._send_error(context, "編集されたアウトラインの形式が無効です。")
                                context.current_step = "error"
                        except (ValidationError, TypeError, AttributeError) as e:
                            await self._send_error(context, f"アウトライン編集エラー: {e}")
                            context.current_step = "error"
                    elif response_type == UserInputType.EDIT_AND_PROCEED and isinstance(payload, EditAndProceedPayload):
                        try:
                            edited_outline_data = payload.edited_content
                            console.print("[green]アウトラインが編集されました（EditAndProceedPayload）。[/green]")
                            # 編集されたアウトラインを適用
                            if isinstance(edited_outline_data.get("title"), str) and \
                               isinstance(edited_outline_data.get("sections"), list):
                                from app.domains.seo_article.schemas import Outline, OutlineSection
                                edited_sections = []
                                for section_data in edited_outline_data["sections"]:
                                    if isinstance(section_data.get("heading"), str):
                                        edited_sections.append(OutlineSection(
                                            heading=section_data["heading"],
                                            estimated_chars=section_data.get("estimated_chars", 400)
                                        ))
                                
                                context.generated_outline = Outline(
                                    status="outline",
                                    title=edited_outline_data["title"],
                                    suggested_tone=edited_outline_data.get("suggested_tone", "丁寧で読みやすい解説調"),
                                    sections=edited_sections
                                )
                                context.current_step = "outline_approved"
                                console.print("[green]編集されたアウトラインが適用されました（EditAndProceedPayload）。[/green]")
                                await self._send_server_event(context, StatusUpdatePayload(step=context.current_step, message="Edited outline applied and approved.", image_mode=getattr(context, 'image_mode', False)))
                                
                                # Save context after outline editing
                                if process_id and user_id:
                                    try:
                                        await self._save_context_to_db(context, process_id=process_id, user_id=user_id)
                                        logger.info("Context saved successfully after outline editing")
                                    except Exception as save_err:
                                        logger.error(f"Failed to save context after outline editing: {save_err}")
                            else:
                                await self._send_error(context, "編集されたアウトラインの形式が無効です。")
                                context.current_step = "error"
                        except (ValidationError, TypeError, AttributeError) as e:
                            await self._send_error(context, f"アウトライン編集エラー: {e}")
                            context.current_step = "error"
                    elif response_type == UserInputType.EDIT_GENERIC:
                        try:
                            # EDIT_GENERIC - generic edit handler for outline step
                            console.print(f"[yellow]EDIT_GENERIC received for outline step. Payload: {payload}[/yellow]")
                            if hasattr(payload, 'edited_content'):
                                edited_outline_data = payload.edited_content
                                if isinstance(edited_outline_data.get("title"), str) and \
                                   isinstance(edited_outline_data.get("sections"), list):
                                    from app.domains.seo_article.schemas import Outline, OutlineSection
                                    edited_sections = []
                                    for section_data in edited_outline_data["sections"]:
                                        if isinstance(section_data.get("heading"), str):
                                            edited_sections.append(OutlineSection(
                                                heading=section_data["heading"],
                                                estimated_chars=section_data.get("estimated_chars", 400)
                                            ))
                                    
                                    context.generated_outline = Outline(
                                        status="outline",
                                        title=edited_outline_data["title"],
                                        suggested_tone=edited_outline_data.get("suggested_tone", "丁寧で読みやすい解説調"),
                                        sections=edited_sections
                                    )
                                    context.current_step = "outline_approved"
                                    console.print("[green]編集されたアウトラインが適用されました（EDIT_GENERIC）。[/green]")
                                    await self._send_server_event(context, StatusUpdatePayload(step=context.current_step, message="Edited outline applied and approved.", image_mode=getattr(context, 'image_mode', False)))
                                    
                                    # Save context after outline editing
                                    if process_id and user_id:
                                        try:
                                            await self._save_context_to_db(context, process_id=process_id, user_id=user_id)
                                            logger.info("Context saved successfully after outline editing")
                                        except Exception as save_err:
                                            logger.error(f"Failed to save context after outline editing: {save_err}")
                                else:
                                    await self._send_error(context, "EDIT_GENERIC: 編集されたアウトラインの形式が無効です。")
                                    context.current_step = "error"
                            else:
                                await self._send_error(context, "EDIT_GENERIC: 編集されたアウトラインの形式が無効です。")
                                context.current_step = "error"
                        except Exception as e:
                            await self._send_error(context, f"EDIT_GENERIC アウトライン編集エラー: {e}")
                            context.current_step = "error"
                    else:
                        await self._send_error(context, f"予期しない応答タイプ: {response_type}")
                        context.current_step = "error"
                else:
                    console.print("[red]アウトライン承認でユーザー応答がありませんでした。[/red]")
                    context.current_step = "error"
            else:
                console.print("[yellow]アウトラインが見つからないため生成ステップに戻します。[/yellow]")
                context.current_step = "outline_generating"
        
        
        elif context.current_step == "research_plan_generated":
            if context.research_plan:
                from app.domains.seo_article.schemas import ResearchPlanData
                plan_data = ResearchPlanData(
                    topic=context.research_plan.topic,
                    queries=[{"query": q.query, "focus": q.focus} for q in context.research_plan.queries]
                )
                
                user_response_message = await self._request_user_input(
                    context,
                    UserInputType.APPROVE_PLAN,
                    ResearchPlanPayload(plan=plan_data).model_dump()
                )
                
                if user_response_message:
                    response_type = user_response_message.response_type
                    payload = user_response_message.payload

                    if response_type == UserInputType.APPROVE_PLAN and isinstance(payload, ApprovePayload):
                        if payload.approved:
                            context.current_step = "research_plan_approved"
                            console.print("[green]リサーチプランが承認されました。リサーチを開始します。[/green]")
                            await self._send_server_event(context, StatusUpdatePayload(step=context.current_step, message="Research plan approved, starting research.", image_mode=getattr(context, 'image_mode', False)))
                            
                            # Save context after plan approval
                            if process_id and user_id:
                                try:
                                    await self._save_context_to_db(context, process_id=process_id, user_id=user_id)
                                    logger.info("Context saved successfully after research plan approval")
                                except Exception as save_err:
                                    logger.error(f"Failed to save context after research plan approval: {save_err}")
                        else:
                            console.print("[yellow]リサーチプランが却下されました。再生成します。[/yellow]")
                            context.current_step = "research_planning"
                    elif response_type == UserInputType.REGENERATE:
                        console.print("[yellow]リサーチプランの再生成が要求されました。[/yellow]")
                        context.current_step = "research_planning"
                    elif response_type == UserInputType.EDIT_PLAN and isinstance(payload, EditPlanPayload):
                        try:
                            edited_plan_data = payload.edited_plan
                            if isinstance(edited_plan_data.get("topic"), str) and isinstance(edited_plan_data.get("queries"), list):
                                from app.domains.seo_article.schemas import ResearchPlan, ResearchQuery
                                queries = [ResearchQuery(query=q.get("query", ""), focus=q.get("focus", "")) 
                                          for q in edited_plan_data["queries"] if isinstance(q, dict)]
                                context.research_plan = ResearchPlan(
                                    status="research_plan",
                                    topic=edited_plan_data["topic"],
                                    queries=queries
                                )
                                context.current_step = "research_plan_approved"
                                console.print("[green]リサーチプランが編集され承認されました。[/green]")
                                await self._send_server_event(context, StatusUpdatePayload(step=context.current_step, message="Research plan edited and approved.", image_mode=getattr(context, 'image_mode', False)))
                                
                                # Save context after plan editing
                                if process_id and user_id:
                                    try:
                                        await self._save_context_to_db(context, process_id=process_id, user_id=user_id)
                                        logger.info("Context saved successfully after research plan editing")
                                    except Exception as save_err:
                                        logger.error(f"Failed to save context after research plan editing: {save_err}")
                            else:
                                await self._send_error(context, "編集されたリサーチプランの形式が無効です。")
                                context.current_step = "error"
                        except (ValidationError, TypeError, AttributeError) as e:
                            await self._send_error(context, f"リサーチプラン編集エラー: {e}")
                            context.current_step = "error"
                    elif response_type == UserInputType.EDIT_AND_PROCEED and isinstance(payload, EditAndProceedPayload):
                        try:
                            edited_plan_data = payload.edited_content
                            if isinstance(edited_plan_data.get("topic"), str) and isinstance(edited_plan_data.get("queries"), list):
                                from app.domains.seo_article.schemas import ResearchPlan, ResearchQuery
                                queries = [ResearchQuery(query=q.get("query", ""), focus=q.get("focus", "")) 
                                          for q in edited_plan_data["queries"] if isinstance(q, dict)]
                                context.research_plan = ResearchPlan(
                                    status="research_plan",
                                    topic=edited_plan_data["topic"],
                                    queries=queries
                                )
                                context.current_step = "research_plan_approved"
                                console.print("[green]リサーチプランが編集され承認されました（EditAndProceedPayload）。[/green]")
                                await self._send_server_event(context, StatusUpdatePayload(step=context.current_step, message="Research plan edited and approved.", image_mode=getattr(context, 'image_mode', False)))
                                
                                # Save context after plan editing
                                if process_id and user_id:
                                    try:
                                        await self._save_context_to_db(context, process_id=process_id, user_id=user_id)
                                        logger.info("Context saved successfully after research plan editing")
                                    except Exception as save_err:
                                        logger.error(f"Failed to save context after research plan editing: {save_err}")
                            else:
                                await self._send_error(context, "編集されたリサーチプランの形式が無効です。")
                                context.current_step = "error"
                        except (ValidationError, TypeError, AttributeError) as e:
                            await self._send_error(context, f"リサーチプラン編集エラー: {e}")
                            context.current_step = "error"
                    elif response_type == UserInputType.EDIT_GENERIC:
                        try:
                            # EDIT_GENERIC - generic edit handler for research plan step
                            console.print(f"[yellow]EDIT_GENERIC received for research plan step. Payload: {payload}[/yellow]")
                            if hasattr(payload, 'edited_content'):
                                edited_plan_data = payload.edited_content
                                if isinstance(edited_plan_data.get("topic"), str) and isinstance(edited_plan_data.get("queries"), list):
                                    from app.domains.seo_article.schemas import ResearchPlan, ResearchQuery
                                    queries = [ResearchQuery(query=q.get("query", ""), focus=q.get("focus", "")) 
                                              for q in edited_plan_data["queries"] if isinstance(q, dict)]
                                    context.research_plan = ResearchPlan(
                                        status="research_plan",
                                        topic=edited_plan_data["topic"],
                                        queries=queries
                                    )
                                    context.current_step = "research_plan_approved"
                                    console.print("[green]リサーチプランが編集され承認されました（EDIT_GENERIC）。[/green]")
                                    await self._send_server_event(context, StatusUpdatePayload(step=context.current_step, message="Research plan edited and approved.", image_mode=getattr(context, 'image_mode', False)))
                                else:
                                    await self._send_error(context, "EDIT_GENERIC: 編集されたリサーチプランの形式が無効です。")
                                    context.current_step = "error"
                            else:
                                await self._send_error(context, "EDIT_GENERIC: 編集されたリサーチプランの形式が無効です。")
                                context.current_step = "error"
                        except Exception as e:
                            await self._send_error(context, f"EDIT_GENERIC リサーチプラン編集エラー: {e}")
                            context.current_step = "error"
                    else:
                        await self._send_error(context, f"予期しない応答タイプ: {response_type}")
                        context.current_step = "error"
                else:
                    console.print("[red]リサーチプラン承認でユーザー応答がありませんでした。[/red]")
                    context.current_step = "error"
            else:
                console.print("[yellow]リサーチプランが見つからないため生成ステップに戻します。[/yellow]")
                context.current_step = "research_planning"
        
        elif context.current_step == "outline_generated":
            if context.generated_outline:
                from app.domains.seo_article.schemas import OutlineData, OutlineSectionData
                outline_data = OutlineData(
                    title=context.generated_outline.title,
                    suggested_tone=getattr(context.generated_outline, 'suggested_tone', '丁寧で読みやすい解説調'),
                    sections=[
                        OutlineSectionData(
                            heading=section.heading,
                            estimated_chars=getattr(section, 'estimated_chars', None),
                            subsections=[
                                OutlineSectionData(
                                    heading=sub.heading,
                                    estimated_chars=getattr(sub, 'estimated_chars', None)
                                ) for sub in (section.subsections or [])
                            ] if hasattr(section, 'subsections') and section.subsections else None
                        ) for section in context.generated_outline.sections
                    ]
                )
                
                user_response_message = await self._request_user_input(
                    context,
                    UserInputType.APPROVE_OUTLINE,
                    OutlinePayload(outline=outline_data).model_dump()
                )
                
                if user_response_message:
                    response_type = user_response_message.response_type
                    payload = user_response_message.payload

                    if response_type == UserInputType.APPROVE_OUTLINE and isinstance(payload, ApprovePayload):
                        if payload.approved:
                            context.current_step = "outline_approved"
                            console.print("[green]アウトラインが承認されました。[/green]")
                            await self._send_server_event(context, StatusUpdatePayload(step=context.current_step, message="Outline approved, proceeding to content generation.", image_mode=getattr(context, 'image_mode', False)))
                            
                            # Save context after outline approval
                            if process_id and user_id:
                                try:
                                    await self._save_context_to_db(context, process_id=process_id, user_id=user_id)
                                    logger.info("Context saved successfully after outline approval")
                                except Exception as save_err:
                                    logger.error(f"Failed to save context after outline approval: {save_err}")
                        else:
                            console.print("[yellow]アウトラインが承認されませんでした。再生成します。[/yellow]")
                            context.current_step = "outline_generating"
                            context.generated_outline = None
                    elif response_type == UserInputType.REGENERATE:
                        console.print("[yellow]アウトラインの再生成が要求されました。[/yellow]")
                        context.current_step = "outline_generating"
                        context.generated_outline = None
                    elif response_type == UserInputType.EDIT_AND_PROCEED and isinstance(payload, EditAndProceedPayload):
                        try:
                            edited_outline_data = payload.edited_content
                            from app.domains.seo_article.schemas import Outline, OutlineSection
                            def convert_edited_section_to_model(data):
                                subsections_data = data.get('subsections', [])
                                return OutlineSection(
                                    heading=data['heading'],
                                    estimated_chars=data.get('estimated_chars'),
                                    subsections=[convert_edited_section_to_model(s) for s in subsections_data] if subsections_data else None
                                )
                            if isinstance(edited_outline_data.get("title"), str) and \
                               isinstance(edited_outline_data.get("suggested_tone"), str) and \
                               isinstance(edited_outline_data.get("sections"), list):
                                context.generated_outline = Outline(
                                    title=edited_outline_data['title'],
                                    suggested_tone=edited_outline_data['suggested_tone'],
                                    sections=[convert_edited_section_to_model(s_data) for s_data in edited_outline_data['sections']],
                                    status="outline"
                                )
                                context.current_step = "outline_approved"
                                console.print("[green]アウトラインが編集され承認されました。[/green]")
                                await self._send_server_event(context, StatusUpdatePayload(step=context.current_step, message="Outline edited and approved.", image_mode=getattr(context, 'image_mode', False)))
                                
                                # Save context after outline editing
                                if process_id and user_id:
                                    try:
                                        await self._save_context_to_db(context, process_id=process_id, user_id=user_id)
                                        logger.info("Context saved successfully after outline editing")
                                    except Exception as save_err:
                                        logger.error(f"Failed to save context after outline editing: {save_err}")
                            else:
                                await self._send_error(context, "編集されたアウトラインの形式が無効です。")
                                context.current_step = "error"
                        except (ValidationError, TypeError, AttributeError) as e:
                            await self._send_error(context, f"アウトライン編集エラー: {e}")
                            context.current_step = "error"
                    else:
                        await self._send_error(context, f"予期しない応答タイプ: {response_type}")
                        context.current_step = "error"
                else:
                    console.print("[red]アウトライン承認でユーザー応答がありませんでした。[/red]")
                    context.current_step = "error"
            else:
                console.print("[yellow]アウトラインが見つからないため生成ステップに戻します。[/yellow]")
                context.current_step = "outline_generating"
        
        else:
            console.print(f"[red]未実装のユーザー入力ステップ: {context.current_step}[/red]")
            context.current_step = "error"


    def _extract_token_usage_from_result(self, result) -> Optional[Dict[str, Any]]:
        """OpenAI Agents SDKの実行結果からトークン使用量を抽出"""
        try:
            # デバッグ情報（開発用）
            if logger.isEnabledFor(logging.DEBUG):
                console.print(f"[debug]Result type: {type(result)}")
                if hasattr(result, '__dict__'):
                    console.print(f"[debug]Result.__dict__ keys: {list(result.__dict__.keys())}")
            
            # RunResult._raw_responses から ModelResponse を取得
            raw_responses = None
            # 最も可能性の高い属性名から順番に試行
            candidate_attrs = [
                '_raw_responses', 'raw_responses', '_responses', 'responses',
                '_RunResult__raw_responses', '__raw_responses', 
                'new_items', '_new_items'  # RunItemsかもしれない
            ]
            
            for attr_name in candidate_attrs:
                if hasattr(result, attr_name):
                    attr_value = getattr(result, attr_name)
                    if logger.isEnabledFor(logging.DEBUG):
                        console.print(f"[debug]Checking {attr_name}: {type(attr_value)}")
                    if attr_value and hasattr(attr_value, '__len__') and len(attr_value) > 0:
                        # リストの最初の要素をチェック
                        first_item = attr_value[0]
                        if hasattr(first_item, 'usage') or 'ModelResponse' in str(type(first_item)):
                            raw_responses = attr_value
                            if logger.isEnabledFor(logging.DEBUG):
                                console.print(f"[debug]✅ Found raw_responses via {attr_name}")
                            break
            
            if raw_responses:
                # 最後のModelResponseから使用量を取得
                last_response = raw_responses[-1]
                if hasattr(last_response, 'usage') and last_response.usage:
                    usage = last_response.usage
                    
                    # トークン使用量を抽出
                    input_tokens = getattr(usage, 'input_tokens', 0)
                    output_tokens = getattr(usage, 'output_tokens', 0)
                    cache_tokens = getattr(usage.input_tokens_details, 'cached_tokens', 0) if hasattr(usage, 'input_tokens_details') and usage.input_tokens_details else 0
                    reasoning_tokens = getattr(usage.output_tokens_details, 'reasoning_tokens', 0) if hasattr(usage, 'output_tokens_details') and usage.output_tokens_details else 0
                    total_tokens = getattr(usage, 'total_tokens', 0)
                    
                    # 実際のモデル名を取得（可能であれば）
                    model_name = getattr(last_response, 'model', 'gpt-4o')
                    
                    # 新しいコスト計算サービスを使用
                    if CostCalculationService:
                        cost_info = CostCalculationService.calculate_cost(
                            model_name=model_name,
                            prompt_tokens=input_tokens,
                            completion_tokens=output_tokens,
                            cached_tokens=cache_tokens,
                            reasoning_tokens=reasoning_tokens,
                            total_tokens=total_tokens
                        )
                        estimated_cost = cost_info["cost_breakdown"]["total_cost_usd"]
                    else:
                        # フォールバック: 古いコスト計算方法
                        estimated_cost = self._estimate_cost(usage)
                    
                    return {
                        "model": model_name,
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "cache_tokens": cache_tokens,
                        "reasoning_tokens": reasoning_tokens,
                        "total_tokens": total_tokens,
                        "estimated_cost": estimated_cost
                    }
            
            # フォールバック: デフォルト値を使用
            logger.warning("No usage data found in result, using fallback values")
            
            # 新しいコスト計算サービスを使用
            if CostCalculationService:
                cost_info = CostCalculationService.calculate_cost(
                    model_name="gpt-4o",
                    prompt_tokens=100,  # 概算値
                    completion_tokens=50,   # 概算値
                    cached_tokens=0,
                    reasoning_tokens=0,
                    total_tokens=150
                )
                estimated_cost = cost_info["cost_breakdown"]["total_cost_usd"]
            else:
                estimated_cost = 0.001
            
            return {
                "model": "gpt-4o",
                "input_tokens": 100,  # 概算値
                "output_tokens": 50,   # 概算値
                "cache_tokens": 0,
                "reasoning_tokens": 0,
                "total_tokens": 150,
                "estimated_cost": estimated_cost
            }
        except Exception as e:
            logger.warning(f"Failed to extract token usage: {e}")
            return None

    def _estimate_cost(self, usage) -> float:
        """トークン使用量からコストを概算"""
        try:
            input_tokens = getattr(usage, 'input_tokens', 0)
            output_tokens = getattr(usage, 'output_tokens', 0)
            # GPT-4o の概算料金 (2025年1月時点)
            input_cost = input_tokens * 0.0000025   # $2.50 per 1M tokens
            output_cost = output_tokens * 0.00001    # $10.00 per 1M tokens
            return input_cost + output_cost
        except Exception:
            return 0.001  # デフォルト値

    def _estimate_cost_from_metadata(self, metadata: Dict[str, Any]) -> float:
        """メタデータからコストを概算"""
        try:
            input_tokens = metadata.get('input_tokens', 0)
            output_tokens = metadata.get('output_tokens', 0)
            cache_tokens = metadata.get('cache_tokens', 0)
            reasoning_tokens = metadata.get('reasoning_tokens', 0)
            model_name = metadata.get('model', 'gpt-4o')
            
            # 新しいコスト計算サービスを使用
            if CostCalculationService:
                cost_info = CostCalculationService.calculate_cost(
                    model_name=model_name,
                    prompt_tokens=input_tokens,
                    completion_tokens=output_tokens,
                    cached_tokens=cache_tokens,
                    reasoning_tokens=reasoning_tokens
                )
                return cost_info["cost_breakdown"]["total_cost_usd"]
            else:
                # フォールバック: 古いコスト計算方法
                input_cost = input_tokens * 0.0000025
                output_cost = output_tokens * 0.00001
                return input_cost + output_cost
        except Exception:
            return 0.001

    def _extract_conversation_history_from_result(self, result, agent_input: str) -> Dict[str, Any]:
        """OpenAI Agents SDKの実行結果から会話履歴を詳細に抽出"""
        try:
            console.print(f"[debug]Starting conversation history extraction. Agent input type: {type(agent_input)}")
            conversation_data = {
                "system_prompt": "",
                "user_prompt": str(agent_input) if agent_input else "",
                "assistant_response": "",
                "tool_calls": [],
                "reasoning": "",
                "full_output": []
            }
            console.print(f"[debug]Initial conversation_data created: {type(conversation_data)}")

            # まず、resultの構造をデバッグ出力
            if logger.isEnabledFor(logging.DEBUG):
                console.print(f"[debug]Result type: {type(result)}")
                if hasattr(result, '__dict__'):
                    console.print(f"[debug]Result attributes: {list(result.__dict__.keys())}")

            # RunResultから生の応答を取得（より多くの候補を試行）
            raw_responses = None
            candidate_attrs = [
                '_RunResult__raw_responses', 'raw_responses', '_raw_responses', '_responses', 'responses',
                'new_items', '_new_items', 'items', '_items', 'messages', '_messages'
            ]
            
            for attr_name in candidate_attrs:
                if hasattr(result, attr_name):
                    attr_value = getattr(result, attr_name)
                    console.print(f"[debug]Checking {attr_name}: {type(attr_value)}")
                    if attr_value:
                        raw_responses = attr_value
                        console.print(f"[debug]Found raw_responses via {attr_name}")
                        break
            
            if not raw_responses:
                raw_responses = []
                console.print("[debug]No raw_responses found, using empty list")

            # raw_responsesの内容を解析
            if raw_responses:
                console.print(f"[debug]Processing {len(raw_responses)} raw responses")
                for i, response in enumerate(raw_responses):
                    console.print(f"[debug]Response {i}: {type(response)}")
                    
                    # ModelResponseオブジェクトから内容を抽出
                    if hasattr(response, 'output') and response.output:
                        console.print(f"[debug]Response {i} has output: {len(response.output)} items")
                        for j, output_item in enumerate(response.output):
                            console.print(f"[debug]Output item {j}: {type(output_item)}")
                            
                            # メッセージコンテンツの抽出
                            if hasattr(output_item, 'type'):
                                item_type = getattr(output_item, 'type', 'unknown')
                                console.print(f"[debug]Item type: {item_type}")
                                
                                if item_type == 'message' or 'message' in str(item_type):
                                    content = ""
                                    if hasattr(output_item, 'content'):
                                        content = getattr(output_item, 'content', '')
                                        if isinstance(content, list):
                                            # リストの場合、各要素を結合
                                            content_parts = []
                                            for part in content:
                                                if hasattr(part, 'text'):
                                                    content_parts.append(str(part.text))
                                                else:
                                                    content_parts.append(str(part))
                                            content = '\n'.join(content_parts)
                                        conversation_data["assistant_response"] += str(content)
                                        console.print(f"[debug]Added message content: {len(str(content))} chars")
                                
                                elif 'tool_call' in str(item_type):
                                    tool_call_data = {
                                        "type": item_type,
                                        "name": getattr(output_item, 'name', ''),
                                        "arguments": getattr(output_item, 'arguments', {}),
                                        "result": getattr(output_item, 'result', None)
                                    }
                                    conversation_data["tool_calls"].append(tool_call_data)
                                    console.print(f"[debug]Added tool call: {tool_call_data['name']}")
                                
                                elif item_type == 'reasoning':
                                    reasoning_content = getattr(output_item, 'content', '')
                                    if isinstance(reasoning_content, list):
                                        reasoning_content = '\n'.join([str(r) for r in reasoning_content])
                                    conversation_data["reasoning"] += str(reasoning_content)
                                    console.print(f"[debug]Added reasoning: {len(str(reasoning_content))} chars")
                            
                            # 全出力を記録
                            conversation_data["full_output"].append({
                                "type": getattr(output_item, 'type', 'unknown'),
                                "content": str(output_item)[:500]
                            })
                    
                    # システムプロンプトの抽出試行
                    if hasattr(response, 'system') and response.system:
                        conversation_data["system_prompt"] = str(response.system)
                        console.print(f"[debug]Found system prompt: {len(conversation_data['system_prompt'])} chars")

            # エージェントの指示をシステムプロンプトとして記録
            if not conversation_data["system_prompt"]:
                if hasattr(result, '_last_agent') and result._last_agent:
                    agent = result._last_agent
                    if hasattr(agent, 'instructions'):
                        instructions = agent.instructions
                        if callable(instructions):
                            # 動的指示の場合は、実行時に解決された値を使用
                            conversation_data["system_prompt"] = "Dynamic instructions (resolved at runtime)"
                            console.print(f"[debug]Marked system prompt as dynamic for agent: {agent.name}")
                        else:
                            conversation_data["system_prompt"] = str(instructions)
                            console.print(f"[debug]Set static system prompt from agent: {len(conversation_data['system_prompt'])} chars")

            # 最終出力も記録
            if hasattr(result, 'final_output') and result.final_output:
                conversation_data["final_output"] = str(result.final_output)[:1000]

            # assistant_responseが空の場合、final_outputを使用
            if not conversation_data["assistant_response"] and conversation_data.get("final_output"):
                conversation_data["assistant_response"] = conversation_data["final_output"]
                console.print(f"[debug]Used final_output as assistant_response: {len(conversation_data['assistant_response'])} chars")

            console.print("[debug]Final conversation data:")
            console.print(f"[debug]  System prompt: {len(conversation_data['system_prompt'])} chars")
            console.print(f"[debug]  User prompt: {len(conversation_data['user_prompt'])} chars")
            console.print(f"[debug]  Assistant response: {len(conversation_data['assistant_response'])} chars")
            console.print(f"[debug]  Tool calls: {len(conversation_data['tool_calls'])}")
            console.print(f"[debug]  Reasoning: {len(conversation_data['reasoning'])} chars")
            
            return conversation_data
            
        except Exception as e:
            logger.warning(f"Failed to extract conversation history: {e}")
            import traceback
            logger.debug(f"Conversation history extraction traceback: {traceback.format_exc()}")
            console.print(f"[red]Conversation history extraction failed: {e}[/red]")
            return {
                "system_prompt": "Unknown",
                "user_prompt": str(agent_input) if agent_input else "",
                "assistant_response": str(result.final_output) if hasattr(result, 'final_output') else "",
                "tool_calls": [],
                "reasoning": "",
                "full_output": []
            }

    async def _log_tool_calls(self, execution_id: str, tool_calls: List[Dict[str, Any]]) -> None:
        """ツール呼び出しを詳細にログに記録"""
        if not self.logging_service or not tool_calls:
            return
        
        try:
            for i, tool_call in enumerate(tool_calls):
                tool_name = tool_call.get("name", "unknown")
                tool_type = tool_call.get("type", "unknown")
                tool_arguments = tool_call.get("arguments", {})
                tool_result = tool_call.get("result", None)
                
                # ツール名からfunction名を推定
                tool_function = "unknown"
                if "websearch" in tool_name.lower() or "search" in tool_name.lower():
                    tool_function = "web_search"
                elif "serpapi" in tool_name.lower():
                    tool_function = "serp_api_search"
                elif "scrape" in tool_name.lower():
                    tool_function = "web_scraping"
                elif "fetch" in tool_name.lower():
                    tool_function = "web_fetch"
                else:
                    tool_function = tool_name.lower().replace(" ", "_")
                
                # データサイズを概算
                data_size_bytes = len(str(tool_result)) if tool_result else 0
                
                # API呼び出し回数を推定（WebSearchやSerpAPIは複数回呼び出すことがある）
                api_calls_count = 1
                if isinstance(tool_arguments, dict):
                    # 複数URLやクエリがある場合
                    urls = tool_arguments.get("urls", [])
                    queries = tool_arguments.get("queries", [])
                    if urls and isinstance(urls, list):
                        api_calls_count = len(urls)
                    elif queries and isinstance(queries, list):
                        api_calls_count = len(queries)
                
                tool_call_id = self.logging_service.create_tool_call_log(
                    execution_id=execution_id,
                    tool_name=tool_name,
                    tool_function=tool_function,
                    call_sequence=i + 1,
                    input_parameters=tool_arguments,
                    output_data={"result": str(tool_result)[:1000] if tool_result else ""},
                    status="completed",
                    data_size_bytes=data_size_bytes,
                    api_calls_count=api_calls_count,
                    tool_metadata={
                        "tool_type": tool_type,
                        "result_length": len(str(tool_result)) if tool_result else 0,
                        "arguments_count": len(tool_arguments) if isinstance(tool_arguments, dict) else 0
                    }
                )
                
                console.print(f"[cyan]🔧 Tool call logged: {tool_call_id} ({tool_name})[/cyan]")
                console.print(f"[dim]  API calls: {api_calls_count}, Data size: {data_size_bytes} bytes[/dim]")
                
        except Exception as e:
            logger.warning(f"Failed to log tool calls: {e}")
            console.print(f"[red]❌ Tool call logging failed: {e}[/red]")

    async def _run_generation_loop(self, context: ArticleContext, run_config: RunConfig, process_id: Optional[str] = None, user_id: Optional[str] = None):
        """記事生成のメインループ（WebSocketインタラクティブ版）"""
        current_agent: Optional[Agent[ArticleContext]] = None
        agent_input: Union[str, List[Dict[str, Any]]]

        # ワークフローロガーを確実に確保
        await self._ensure_workflow_logger(context, process_id, user_id)

        try:
            while context.current_step not in ["completed", "error"]:
                console.print(f"[green]生成ループ開始: {context.current_step} (process_id: {process_id})[/green]")
                
                # 非同期yield pointを追加してWebSocketループに制御を戻す
                await asyncio.sleep(0.1)
                
                # データベースに現在の状態を保存
                if process_id and user_id:
                    await self._save_context_to_db(context, process_id=process_id, user_id=user_id)
                
                await self._send_server_event(context, StatusUpdatePayload(
                    step=context.current_step, 
                    message=f"Starting step: {context.current_step}",
                    image_mode=getattr(context, 'image_mode', False)
                ))
                console.rule(f"[bold yellow]API Step: {context.current_step}[/bold yellow]")

                # --- ステップに応じた処理 ---
                if context.current_step == "start":
                    context.current_step = "keyword_analyzing"  # SerpAPIキーワード分析から開始
                    await self._send_server_event(context, StatusUpdatePayload(
                        step=context.current_step, 
                        message="Starting keyword analysis with SerpAPI...",
                        image_mode=getattr(context, 'image_mode', False)
                    ))
                    # エージェント実行なし、次のループで処理

                elif context.current_step == "keyword_analyzing":
                    # SerpAPIキーワード分析エージェントを実行
                    current_agent = serp_keyword_analysis_agent
                    agent_input = f"キーワード: {', '.join(context.initial_keywords)}"
                    console.print(f"🤖 {current_agent.name} にSerpAPIキーワード分析を依頼します...")
                    agent_output = await self._run_agent(current_agent, agent_input, context, run_config)

                    if isinstance(agent_output, SerpKeywordAnalysisReport):
                        # 必要なフィールドが設定されているかチェックし、不足している場合はデフォルト値を設定
                        if not hasattr(agent_output, 'search_query') or not agent_output.search_query:
                            agent_output.search_query = ', '.join(context.initial_keywords)
                        if not hasattr(agent_output, 'keyword') or not agent_output.keyword:
                            agent_output.keyword = ', '.join(context.initial_keywords)
                        if not hasattr(agent_output, 'total_results'):
                            agent_output.total_results = 0
                        if not hasattr(agent_output, 'analyzed_articles'):
                            agent_output.analyzed_articles = []
                        if not hasattr(agent_output, 'average_article_length'):
                            agent_output.average_article_length = 0
                        if not hasattr(agent_output, 'recommended_target_length'):
                            agent_output.recommended_target_length = context.target_length or 3000
                        if not hasattr(agent_output, 'main_themes'):
                            agent_output.main_themes = []
                        if not hasattr(agent_output, 'common_headings'):
                            agent_output.common_headings = []
                        if not hasattr(agent_output, 'content_gaps'):
                            agent_output.content_gaps = []
                        if not hasattr(agent_output, 'competitive_advantages'):
                            agent_output.competitive_advantages = []
                        if not hasattr(agent_output, 'user_intent_analysis'):
                            agent_output.user_intent_analysis = ""
                        if not hasattr(agent_output, 'content_strategy_recommendations'):
                            agent_output.content_strategy_recommendations = []
                            
                        context.serp_analysis_report = agent_output
                        context.current_step = "keyword_analyzed"
                        console.print("[green]SerpAPIキーワード分析が完了しました。[/green]")
                        
                        # Save context after keyword analysis completion
                        if process_id and user_id:
                            try:
                                await self._save_context_to_db(context, process_id=process_id, user_id=user_id)
                                logger.info("Context saved successfully after keyword analysis completion")
                            except Exception as save_err:
                                logger.error(f"Failed to save context after keyword analysis: {save_err}")
                                # Continue processing even if save fails
                        
                        # 分析結果をクライアントに送信
                        analysis_data = SerpKeywordAnalysisPayload(
                            search_query=agent_output.search_query,
                            total_results=agent_output.total_results,
                            analyzed_articles=[
                                SerpAnalysisArticleData(
                                    url=article.url,
                                    title=article.title,
                                    headings=article.headings,
                                    content_preview=article.content_preview,
                                    char_count=article.char_count,
                                    image_count=article.image_count,
                                    source_type=article.source_type,
                                    position=article.position,
                                    question=article.question
                                ) for article in agent_output.analyzed_articles
                            ],
                            average_article_length=agent_output.average_article_length,
                            recommended_target_length=agent_output.recommended_target_length,
                            main_themes=agent_output.main_themes,
                            common_headings=agent_output.common_headings,
                            content_gaps=agent_output.content_gaps,
                            competitive_advantages=agent_output.competitive_advantages,
                            user_intent_analysis=agent_output.user_intent_analysis,
                            content_strategy_recommendations=agent_output.content_strategy_recommendations
                        )
                        await self._send_server_event(context, analysis_data)
                        
                        # 推奨目標文字数をコンテキストに設定（ユーザー指定がない場合）
                        if not context.target_length:
                            context.target_length = agent_output.recommended_target_length
                            console.print(f"[cyan]推奨目標文字数を設定しました: {context.target_length}文字[/cyan]")
                        
                        # 次のステップに進む（ペルソナ生成）
                        context.current_step = "persona_generating"
                        await self._send_server_event(context, StatusUpdatePayload(step=context.current_step, message="Keyword analysis completed, proceeding to persona generation.", image_mode=getattr(context, 'image_mode', False)))
                        
                        # Save context after step transition
                        if process_id and user_id:
                            try:
                                await self._save_context_to_db(context, process_id=process_id, user_id=user_id)
                                logger.info("Context saved successfully after step transition to persona_generating")
                            except Exception as save_err:
                                logger.error(f"Failed to save context after step transition to persona_generating: {save_err}")
                    else:
                        await self._send_error(context, f"SerpAPIキーワード分析中に予期しないエージェント出力タイプ ({type(agent_output)}) を受け取りました。")
                        context.current_step = "error"
                        continue

                
                elif context.current_step == "persona_generating":
                    current_agent = persona_generator_agent
                    agent_input = f"キーワード: {context.initial_keywords}, 年代: {context.target_age_group}, 属性: {context.persona_type}, 独自ペルソナ: {context.custom_persona}, 生成数: {context.num_persona_examples}"
                    console.print(f"🤖 {current_agent.name} に具体的なペルソナ生成を依頼します...")
                    agent_output = await self._run_agent(current_agent, agent_input, context, run_config)

                    if isinstance(agent_output, GeneratedPersonasResponse):
                        context.generated_detailed_personas = [p.description for p in agent_output.personas]
                        context.current_step = "persona_generated"
                        console.print(f"[cyan]{len(context.generated_detailed_personas)}件の具体的なペルソナを生成しました。クライアントの選択を待ちます...[/cyan]")
                        
                        # Save context after persona generation
                        if process_id and user_id:
                            try:
                                await self._save_context_to_db(context, process_id=process_id, user_id=user_id)
                                logger.info("Context saved successfully after persona generation")
                            except Exception as save_err:
                                logger.error(f"Failed to save context after persona generation: {save_err}")
                        
                        personas_data_for_client = [GeneratedPersonaData(id=i, description=desc) for i, desc in enumerate(context.generated_detailed_personas)]
                        user_response_message = await self._request_user_input( # ClientResponseMessage全体が返るように変更
                            context,
                            UserInputType.SELECT_PERSONA,
                            GeneratedPersonasPayload(personas=personas_data_for_client).model_dump() # dataとして送信
                        )
                        if user_response_message: # ClientResponseMessage が None でないことを確認
                            response_type = user_response_message.response_type
                            payload = user_response_message.payload

                            if response_type == UserInputType.SELECT_PERSONA and isinstance(payload, SelectPersonaPayload):
                                selected_id = payload.selected_id
                                if 0 <= selected_id < len(context.generated_detailed_personas):
                                    context.selected_detailed_persona = context.generated_detailed_personas[selected_id]
                                    context.current_step = "persona_selected"
                                    console.print(f"[green]クライアントがペルソナID {selected_id} を選択しました。[/green]")
                                    await self._send_server_event(context, StatusUpdatePayload(step=context.current_step, message=f"Detailed persona selected: {context.selected_detailed_persona[:50]}...", image_mode=getattr(context, 'image_mode', False)))
                                    
                                    # Save context after user persona selection
                                    if process_id and user_id:
                                        try:
                                            await self._save_context_to_db(context, process_id=process_id, user_id=user_id)
                                            logger.info("Context saved successfully after persona selection")
                                        except Exception as save_err:
                                            logger.error(f"Failed to save context after persona selection: {save_err}")
                                    continue  # ★重要: continueでループの次のイテレーションへ
                                else:
                                    raise ValueError(f"無効なペルソナIDが選択されました: {selected_id}")
                            elif response_type == UserInputType.REGENERATE:
                                console.print("[yellow]クライアントがペルソナの再生成を要求しました。[/yellow]")
                                context.current_step = "persona_generating" # 生成ステップに戻る
                                context.generated_detailed_personas = [] # 生成済みペルソナをクリア
                                # ループの先頭に戻り、再度ペルソナ生成が実行される
                                continue # ★重要: continueでループの次のイテレーションへ
                            elif response_type == UserInputType.EDIT_AND_PROCEED and isinstance(payload, EditAndProceedPayload):
                                edited_persona_description = payload.edited_content.get("description")
                                if edited_persona_description and isinstance(edited_persona_description, str):
                                    context.selected_detailed_persona = edited_persona_description
                                    context.current_step = "persona_selected" # 編集されたもので選択完了扱い
                                    console.print(f"[green]クライアントがペルソナを編集し、選択しました: {context.selected_detailed_persona[:50]}...[/green]")
                                    await self._send_server_event(context, StatusUpdatePayload(step=context.current_step, message="Detailed persona edited and selected.", image_mode=getattr(context, 'image_mode', False)))
                                    
                                    # Save context after user persona editing
                                    if process_id and user_id:
                                        try:
                                            await self._save_context_to_db(context, process_id=process_id, user_id=user_id)
                                            logger.info("Context saved successfully after persona editing and selection")
                                        except Exception as save_err:
                                            logger.error(f"Failed to save context after persona editing: {save_err}")
                                    continue  # ★重要: continueでループの次のイテレーションへ
                                else:
                                    # 不正な編集内容
                                    await self._send_error(context, "Invalid edited persona content.")
                                    context.current_step = "persona_generated" # 選択待ちに留まる
                                    continue
                            else:
                                # 予期しない応答タイプやペイロード
                                await self._send_error(context, f"予期しない応答 ({response_type}, {type(payload)}) がペルソナ選択で受信されました。")
                                context.current_step = "persona_generated" # 選択待ちに留まる
                                continue
                        else:
                            # 応答がない場合 (タイムアウトなど、上位で処理されるはずだが念のため)
                            console.print("[red]ペルソナ選択でクライアントからの応答がありませんでした。[/red]")
                            # エラーにするか、リトライを促すかなど検討。ここではループを継続（上位のタイムアウト処理に任せる）
                            context.current_step = "persona_generated" # 選択待ちに留まる
                            continue

                elif context.current_step == "persona_selected":
                    context.current_step = "theme_generating"  # テーマ生成ステップに移行
                    await self._send_server_event(context, StatusUpdatePayload(step=context.current_step, message="Persona selected, proceeding to theme generation.", image_mode=getattr(context, 'image_mode', False)))

                elif context.current_step == "theme_generating":
                    current_agent = theme_agent
                    if not context.selected_detailed_persona: # selected_detailed_persona が存在することを確認
                        await self._send_error(context, "詳細ペルソナが選択されていません。テーマ生成をスキップします。", "theme_generating")
                        context.current_step = "error" # または適切なフォールバック処理
                        continue
                    
                    # SerpAPI分析結果を含めたプロンプト作成
                    agent_input_base = f"キーワード「{', '.join(context.initial_keywords)}」と、以下のペルソナに基づいて、{context.num_theme_proposals}個のテーマ案を生成してください。\\n\\nペルソナ詳細:\\n{context.selected_detailed_persona}"
                    
                    # SerpAPI分析結果がある場合は、競合情報とSEO戦略を追加
                    if context.serp_analysis_report:
                        seo_context = f"""

\\n\\n=== SEO分析結果（競合記事分析） ===
検索クエリ: {context.serp_analysis_report.search_query}
分析記事数: {len(context.serp_analysis_report.analyzed_articles)}
推奨文字数: {context.serp_analysis_report.recommended_target_length}文字

主要テーマ（競合で頻出）: {', '.join(context.serp_analysis_report.main_themes)}
共通見出しパターン: {', '.join(context.serp_analysis_report.common_headings[:5])}
コンテンツギャップ（差別化チャンス）: {', '.join(context.serp_analysis_report.content_gaps)}
競合優位性のポイント: {', '.join(context.serp_analysis_report.competitive_advantages)}

ユーザー検索意図: {context.serp_analysis_report.user_intent_analysis}

\\n上記の競合分析結果を活用し、検索上位を狙えるかつ差別化されたテーマを提案してください。"""
                        agent_input = agent_input_base + seo_context
                    else:
                        agent_input = agent_input_base
                    
                    console.print(f"🤖 {current_agent.name} にテーマ提案を依頼します...")
                    agent_output = await self._run_agent(current_agent, agent_input, context, run_config)

                    if isinstance(agent_output, ThemeProposal):
                        context.generated_themes = agent_output.themes # List[ThemeIdea]
                        if context.generated_themes: # テーマが1つ以上生成されたか確認
                            context.current_step = "theme_proposed" # ユーザー選択待ちステップへ
                            console.print(f"[cyan]{len(context.generated_themes)}件のテーマ案を生成しました。クライアントの選択を待ちます...[/cyan]")
                            
                            # Save context after theme generation
                            if process_id and user_id:
                                try:
                                    await self._save_context_to_db(context, process_id=process_id, user_id=user_id)
                                    logger.info("Context saved successfully after theme generation")
                                except Exception as save_err:
                                    logger.error(f"Failed to save context after theme generation: {save_err}")
                            
                            themes_data_for_client = [
                                ThemeProposalData(title=idea.title, description=idea.description, keywords=idea.keywords)
                                for idea in context.generated_themes
                            ]
                            user_response_message = await self._request_user_input(
                                context,
                                UserInputType.SELECT_THEME,
                                ThemeProposalPayload(themes=themes_data_for_client).model_dump()
                            )
                            if user_response_message:
                                response_type = user_response_message.response_type
                                payload = user_response_message.payload

                                if response_type == UserInputType.SELECT_THEME and isinstance(payload, SelectThemePayload):
                                    selected_index = payload.selected_index
                                    if 0 <= selected_index < len(context.generated_themes):
                                        context.selected_theme = context.generated_themes[selected_index]
                                        context.current_step = "theme_selected"
                                        console.print(f"[green]クライアントがテーマ「{context.selected_theme.title}」を選択しました。[/green]")
                                        await self._send_server_event(context, StatusUpdatePayload(step=context.current_step, message=f"Theme selected: {context.selected_theme.title}", image_mode=getattr(context, 'image_mode', False)))
                                        
                                        # Save context after user theme selection
                                        if process_id and user_id:
                                            try:
                                                await self._save_context_to_db(context, process_id=process_id, user_id=user_id)
                                                logger.info("Context saved successfully after theme selection")
                                            except Exception as save_err:
                                                logger.error(f"Failed to save context after theme selection: {save_err}")
                                        
                                        console.print(f"[blue]テーマ選択処理完了。次のステップ: {context.current_step}[/blue]")
                                        console.print(f"[blue]ループを継続します... (process_id: {process_id})[/blue]")
                                        continue  # ★重要: continueでループの次のイテレーションへ
                                    else:
                                        await self._send_error(context, f"無効なテーマインデックスが選択されました: {selected_index}")
                                        context.current_step = "theme_proposed" 
                                        continue
                                elif response_type == UserInputType.REGENERATE:
                                    console.print("[yellow]クライアントがテーマの再生成を要求しました。[/yellow]")
                                    context.current_step = "theme_generating" 
                                    context.generated_themes = [] 
                                    continue 
                                elif response_type == UserInputType.EDIT_AND_PROCEED and isinstance(payload, EditAndProceedPayload):
                                    try:
                                        edited_theme_data = payload.edited_content
                                        if isinstance(edited_theme_data.get("title"), str) and \
                                           isinstance(edited_theme_data.get("description"), str) and \
                                           isinstance(edited_theme_data.get("keywords"), list):
                                            # context.selected_theme の型は ThemeIdea (services.models より)
                                            context.selected_theme = ThemeIdea(**edited_theme_data)
                                            context.current_step = "theme_selected"
                                            console.print(f"[green]クライアントがテーマを編集し、選択しました: {context.selected_theme.title}[/green]")
                                            await self._send_server_event(context, StatusUpdatePayload(step=context.current_step, message="Theme edited and selected.", image_mode=getattr(context, 'image_mode', False)))
                                            
                                            # Save context after user theme editing
                                            if process_id and user_id:
                                                try:
                                                    await self._save_context_to_db(context, process_id=process_id, user_id=user_id)
                                                    logger.info("Context saved successfully after theme editing and selection")
                                                except Exception as save_err:
                                                    logger.error(f"Failed to save context after theme editing: {save_err}")
                                            continue  # ★重要: continueでループの次のイテレーションへ
                                        else:
                                            await self._send_error(context, "Invalid edited theme content structure.")
                                            context.current_step = "theme_proposed" 
                                            continue
                                    except (ValidationError, TypeError, AttributeError) as e:
                                        await self._send_error(context, f"Error processing edited theme: {e}")
                                        context.current_step = "theme_proposed" 
                                        continue
                                else:
                                    await self._send_error(context, f"予期しない応答 ({response_type}, {type(payload)}) がテーマ選択で受信されました。")
                                    context.current_step = "theme_proposed"
                                    continue
                            else:
                                console.print("[red]テーマ選択でクライアントからの応答がありませんでした。[/red]")
                                context.current_step = "theme_proposed"
                                continue
                        else: # agent_output.themes が空の場合
                            await self._send_error(context, "テーマ案がエージェントによって生成されませんでした。再試行します。")
                            context.current_step = "theme_generating" # 再度テーマ生成を試みる
                            continue
                    elif isinstance(agent_output, ClarificationNeeded): # エージェントが明確化を求めた場合
                        await self._send_error(context, f"テーマ生成で明確化が必要です: {agent_output.message}")
                        context.current_step = "error" # または適切なフォールバック
                        continue
                    else: # 予期しないエージェント出力
                        await self._send_error(context, f"テーマ生成中に予期しないエージェント出力タイプ ({type(agent_output)}) を受け取りました。")
                        context.current_step = "error"
                        continue
                
                elif context.current_step == "theme_selected":
                    console.print(f"[blue]theme_selectedステップを処理中... (process_id: {process_id})[/blue]")
                    context.current_step = "research_planning"
                    console.print("[blue]theme_selectedからresearch_planningに遷移します...[/blue]")
                    await self._send_server_event(context, StatusUpdatePayload(step=context.current_step, message="Moving to research planning.", image_mode=getattr(context, 'image_mode', False)))
                    console.print(f"[blue]research_planningステップに移行完了。継続中... (process_id: {process_id})[/blue]")
                    # エージェント実行なし、次のループで research_planning が処理される

                elif context.current_step == "research_plan_generated":
                    # リサーチ計画生成後、ユーザーの承認を待つ状態
                    # 実際の処理は research_planning ステップで行われる
                    # このステップではユーザー入力を待つだけ
                    plan_data_for_client = ResearchPlanData(
                        topic=context.research_plan.topic if context.research_plan else "No plan available",
                        queries=[ResearchPlanQueryData(query=q.query, focus=q.focus) for q in context.research_plan.queries] if context.research_plan else []
                    )
                    user_response_message = await self._request_user_input(
                        context,
                        UserInputType.APPROVE_PLAN,
                        ResearchPlanPayload(plan=plan_data_for_client).model_dump()
                    )

                    if user_response_message:
                        response_type = user_response_message.response_type
                        payload = user_response_message.payload

                        if response_type == UserInputType.APPROVE_PLAN and isinstance(payload, ApprovePayload):
                            if payload.approved:
                                context.current_step = "research_plan_approved"
                                console.print("[green]クライアントがリサーチ計画を承認しました。[/green]")
                                await self._send_server_event(context, StatusUpdatePayload(step=context.current_step, message="Research plan approved.", image_mode=getattr(context, 'image_mode', False)))
                                
                                # Save context after research plan approval
                                if process_id and user_id:
                                    try:
                                        await self._save_context_to_db(context, process_id=process_id, user_id=user_id)
                                        logger.info("Context saved successfully after research plan approval")
                                    except Exception as save_err:
                                        logger.error(f"Failed to save context after research plan approval: {save_err}")
                                continue  # ★重要: continueでループの次のイテレーションへ
                            else:
                                console.print("[yellow]クライアントがリサーチ計画を否認しました。再生成を試みます。[/yellow]")
                                context.current_step = "research_planning"
                                context.research_plan = None
                                continue
                        elif response_type == UserInputType.REGENERATE:
                            console.print("[yellow]クライアントがリサーチ計画の再生成を要求しました。[/yellow]")
                            context.current_step = "research_planning"
                            context.research_plan = None
                            continue
                        elif response_type == UserInputType.EDIT_AND_PROCEED and isinstance(payload, EditAndProceedPayload):
                            try:
                                edited_plan_data = payload.edited_content
                                if isinstance(edited_plan_data.get("topic"), str) and isinstance(edited_plan_data.get("queries"), list):
                                    context.research_plan = ResearchPlan(
                                        topic=edited_plan_data['topic'],
                                        queries=[ResearchQuery(**q_data) for q_data in edited_plan_data['queries']],
                                        status="research_plan"
                                    )
                                    context.current_step = "research_plan_approved"
                                    console.print("[green]クライアントがリサーチ計画を編集し、承認しました。[/green]")
                                    await self._send_server_event(context, StatusUpdatePayload(step=context.current_step, message="Research plan edited and approved.", image_mode=getattr(context, 'image_mode', False)))
                                    
                                    # Save context after research plan editing and approval
                                    if process_id and user_id:
                                        try:
                                            await self._save_context_to_db(context, process_id=process_id, user_id=user_id)
                                            logger.info("Context saved successfully after research plan editing and approval")
                                        except Exception as save_err:
                                            logger.error(f"Failed to save context after research plan editing: {save_err}")
                                    continue  # ★重要: continueでループの次のイテレーションへ
                                else:
                                    await self._send_error(context, "Invalid edited research plan content structure.")
                                    continue
                            except (ValidationError, TypeError, AttributeError, KeyError) as e:
                                await self._send_error(context, f"Error processing edited research plan: {e}")
                                continue
                        else:
                            await self._send_error(context, f"予期しない応答 ({response_type}) がリサーチ計画承認で受信されました。")
                            continue
                    else:
                        console.print("[red]リサーチ計画の承認/編集でクライアントからの応答がありませんでした。[/red]")
                        # タイムアウトの場合、上位の handle_websocket_connection で処理される
                        continue

                elif context.current_step == "research_planning":
                    current_agent = research_planner_agent
                    if not context.selected_theme: 
                        await self._send_error(context, "テーマが選択されていません。リサーチ計画作成をスキップします。", "research_planning")
                        context.current_step = "error"
                        continue

                    agent_input = f"選択されたテーマ「{context.selected_theme.title}」についてのリサーチ計画を作成してください。"
                    console.print(f"🤖 {current_agent.name} にリサーチ計画作成を依頼します...")
                    agent_output = await self._run_agent(current_agent, agent_input, context, run_config)

                    if isinstance(agent_output, ResearchPlan):
                        context.research_plan = agent_output # エージェントが生成した計画を context.research_plan に保存
                        context.current_step = "research_plan_generated" 
                        console.print("[cyan]リサーチ計画を生成しました。クライアントの承認/編集/再生成を待ちます...[/cyan]")
                        
                        # Save context after research plan generation
                        if process_id and user_id:
                            try:
                                await self._save_context_to_db(context, process_id=process_id, user_id=user_id)
                                logger.info("Context saved successfully after research plan generation")
                            except Exception as save_err:
                                logger.error(f"Failed to save context after research plan generation: {save_err}")
                        
                        # 次のループで research_plan_generated ステップで処理される
                        continue
                    elif isinstance(agent_output, ClarificationNeeded):
                        await self._send_error(context, f"リサーチ計画作成で明確化が必要です: {agent_output.message}")
                        context.current_step = "error"
                        continue
                    else:
                        await self._send_error(context, f"リサーチ計画作成中に予期しないエージェント出力タイプ ({type(agent_output)}) を受け取りました。")
                        context.current_step = "error"
                        continue
                
                elif context.current_step == "research_plan_approved":
                    context.current_step = "researching"
                    console.print("リサーチ実行ステップに進みます...")
                    await self._send_server_event(context, StatusUpdatePayload(step=context.current_step, message="Moving to research execution.", image_mode=getattr(context, 'image_mode', False)))
                    # エージェント実行なし

                elif context.current_step == "researching":
                    if not context.research_plan:
                        raise ValueError("リサーチ計画がありません。")
                    if context.current_research_query_index >= len(context.research_plan.queries):
                        context.current_step = "research_synthesizing"
                        console.print("[green]全クエリのリサーチが完了しました。要約ステップに移ります。[/green]")
                        await self._send_server_event(context, StatusUpdatePayload(step=context.current_step, message="All research queries completed, synthesizing results.", image_mode=getattr(context, 'image_mode', False)))
                        continue

                    current_agent = researcher_agent
                    current_query_obj = context.research_plan.queries[context.current_research_query_index]
                    
                    # リサーチクエリ実行をカスタムスパンでラップ
                    with safe_custom_span("research_query", data={
                        "query_index": context.current_research_query_index,
                        "total_queries": len(context.research_plan.queries),
                        "query": current_query_obj.query,
                        "focus": current_query_obj.focus
                    }):
                        agent_input = f"リサーチ計画のクエリ {context.current_research_query_index + 1}「{current_query_obj.query}」について調査し、結果を詳細に抽出・要約してください。"
                        console.print(f"🤖 {current_agent.name} にクエリ {context.current_research_query_index + 1}/{len(context.research_plan.queries)} の詳細リサーチを依頼します...")
                        # WebSocketで進捗を送信
                        await self._send_server_event(context, ResearchProgressPayload(
                            query_index=context.current_research_query_index,
                            total_queries=len(context.research_plan.queries),
                            query=current_query_obj.query
                        ))

                        # --- Retry logic start ---
                        MAX_RETRY_ATTEMPTS = 3
                        for attempt in range(1, MAX_RETRY_ATTEMPTS + 1):
                            agent_output = await self._run_agent(current_agent, agent_input, context, run_config)

                            # 成功条件: 正しいクエリ結果が返る
                            if isinstance(agent_output, ResearchQueryResult) and agent_output.query == current_query_obj.query:
                                context.add_query_result(agent_output)
                                console.print(
                                    f"[green]クエリ「{agent_output.query}」の詳細リサーチ結果を処理しました。[/green]"
                                )
                                context.current_research_query_index += 1

                                # Save context after each research query completion
                                if process_id and user_id:
                                    try:
                                        await self._save_context_to_db(
                                            context, process_id=process_id, user_id=user_id
                                        )
                                        logger.info(
                                            f"Context saved successfully after research query {context.current_research_query_index}/{len(context.research_plan.queries)} completion"
                                        )
                                    except Exception as save_err:
                                        logger.error(
                                            f"Failed to save context after research query completion: {save_err}"
                                        )
                                # 正常に処理できたので retry ループから抜ける
                                break

                            # 失敗した場合の処理
                            console.print(
                                f"[yellow]予期しないリサーチ結果 (attempt {attempt}/{MAX_RETRY_ATTEMPTS}) を受け取りました。リトライします...[/yellow]"
                            )

                            # 最後の試行であればエラーを送出
                            if attempt == MAX_RETRY_ATTEMPTS:
                                if isinstance(agent_output, ResearchQueryResult):
                                    error_query = agent_output.query
                                else:
                                    error_query = getattr(agent_output, "query", "<unknown>")
                                raise ValueError(
                                    f"予期しないクエリ「{error_query}」の結果を {MAX_RETRY_ATTEMPTS} 回受け取りました。処理を中断します。"
                                )

                            # 少し待ってから再試行（API レート制限などの軽減）
                            await asyncio.sleep(1)
                        # --- Retry logic end ---

                elif context.current_step == "research_synthesizing":
                    current_agent = research_synthesizer_agent
                    agent_input = "収集された詳細なリサーチ結果を分析し、記事執筆のための詳細な要約レポートを作成してください。"
                    console.print(f"🤖 {current_agent.name} に詳細リサーチ結果の要約を依頼します...")
                    agent_output = await self._run_agent(current_agent, agent_input, context, run_config)

                    if isinstance(agent_output, ResearchReport):
                        context.research_report = agent_output
                        context.current_step = "research_report_generated" # 次のステップへ直接移行 (承認は任意)
                        console.print("[green]リサーチレポートを生成しました。[/green]")
                        # WebSocketでレポートを送信 (承認は求めず、情報提供のみ)
                        report_data = agent_output.model_dump()
                        await self._send_server_event(context, ResearchCompletePayload(report=report_data))
                        
                        # Save context after research report generation
                        if process_id and user_id:
                            try:
                                await self._save_context_to_db(context, process_id=process_id, user_id=user_id)
                                logger.info("Context saved successfully after research report generation")
                            except Exception as save_err:
                                logger.error(f"Failed to save context after research report generation: {save_err}")
                        
                        # すぐにアウトライン生成へ
                        context.current_step = "outline_generating" # ★ ステップ名修正
                        await self._send_server_event(context, StatusUpdatePayload(step=context.current_step, message="Research report generated, generating outline.", image_mode=getattr(context, 'image_mode', False)))
                    else:
                        raise TypeError(f"予期しないAgent出力タイプ: {type(agent_output)}")

                elif context.current_step == "outline_generating": # ★ ステップ名修正
                    current_agent = outline_agent
                    if not context.research_report: 
                        await self._send_error(context, "リサーチレポートがありません。アウトライン作成をスキップします。", "outline_generating")
                        context.current_step = "error"
                        continue
                    
                    instruction_text = f"詳細リサーチレポートに基づいてアウトラインを作成してください。テーマ: {context.selected_theme.title if context.selected_theme else '未選択'}, 目標文字数 {context.target_length or '指定なし'}"
                    research_report_json_str = json.dumps(context.research_report.model_dump(), ensure_ascii=False, indent=2) # インデントありの方が見やすいかも

                    # 会話履歴形式のリストを作成
                    agent_input_list_for_outline = [
                        {
                            "role": "user",
                            "content": [
                                {"type": "input_text", "text": instruction_text},
                                {"type": "input_text", "text": f"\n\n---参照リサーチレポート開始---\n{research_report_json_str}\n---参照リサーチレポート終了---"}
                            ]
                        }
                    ]
                    console.print(f"🤖 {current_agent.name} にアウトライン作成を依頼します...")
                    agent_output = await self._run_agent(current_agent, agent_input_list_for_outline, context, run_config)

                    if isinstance(agent_output, Outline):
                        context.generated_outline = agent_output # エージェントが生成したアウトラインを context.generated_outline に保存
                        context.current_step = "outline_generated" 
                        console.print("[cyan]アウトラインを生成しました。クライアントの承認/編集/再生成を待ちます...[/cyan]")
                        
                        # Save context after outline generation
                        if process_id and user_id:
                            try:
                                await self._save_context_to_db(context, process_id=process_id, user_id=user_id)
                                logger.info("Context saved successfully after outline generation")
                            except Exception as save_err:
                                logger.error(f"Failed to save context after outline generation: {save_err}")
                        
                        def convert_section_to_data(section: OutlineSection) -> OutlineSectionData:
                            return OutlineSectionData(
                                heading=section.heading,
                                estimated_chars=section.estimated_chars,
                                subsections=[convert_section_to_data(s) for s in section.subsections] if section.subsections else None
                            )
                        
                        outline_data_for_client = OutlineData(
                            title=context.generated_outline.title, # context.outline_generated_by_agent から context.generated_outline に変更
                            suggested_tone=context.generated_outline.suggested_tone, # context.outline_generated_by_agent から context.generated_outline に変更
                            sections=[convert_section_to_data(s) for s in context.generated_outline.sections] # context.outline_generated_by_agent から context.generated_outline に変更
                        )
                        user_response_message = await self._request_user_input(
                            context,
                            UserInputType.APPROVE_OUTLINE,
                            OutlinePayload(outline=outline_data_for_client).model_dump()
                        )
                        
                        if user_response_message:
                            response_type = user_response_message.response_type
                            payload = user_response_message.payload

                            if response_type == UserInputType.APPROVE_OUTLINE and isinstance(payload, ApprovePayload):
                                if payload.approved:
                                    # context.generated_outline は既に設定済みなので、ここでは何もしない
                                    context.current_step = "outline_approved"
                                    console.print("[green]クライアントがアウトラインを承認しました。[/green]")
                                    await self._send_server_event(context, StatusUpdatePayload(step=context.current_step, message="Outline approved, proceeding to writing.", image_mode=getattr(context, 'image_mode', False)))
                                    
                                    # Save context after outline approval
                                    if process_id and user_id:
                                        try:
                                            await self._save_context_to_db(context, process_id=process_id, user_id=user_id)
                                            logger.info("Context saved successfully after outline approval")
                                        except Exception as save_err:
                                            logger.error(f"Failed to save context after outline approval: {save_err}")
                                    continue  # ★重要: continueでループの次のイテレーションへ
                                else:
                                    console.print("[yellow]クライアントがアウトラインを否認しました。再生成を試みます。[/yellow]")
                                    context.current_step = "outline_generating"
                                    context.generated_outline = None # 承認されなかったのでクリア
                                    continue
                            elif response_type == UserInputType.REGENERATE:
                                console.print("[yellow]クライアントがアウトラインの再生成を要求しました。[/yellow]")
                                context.current_step = "outline_generating"
                                context.generated_outline = None # 再生成するのでクリア
                                continue
                            elif response_type == UserInputType.EDIT_AND_PROCEED and isinstance(payload, EditAndProceedPayload):
                                try:
                                    edited_outline_data = payload.edited_content
                                    def convert_edited_section_to_model(data: Dict[str, Any]) -> OutlineSection:
                                        subsections_data = data.get("subsections")
                                        return OutlineSection(
                                            heading=data['heading'],
                                            estimated_chars=data.get('estimated_chars'),
                                            subsections=[convert_edited_section_to_model(s) for s in subsections_data] if subsections_data else None
                                        )
                                    if isinstance(edited_outline_data.get("title"), str) and \
                                       isinstance(edited_outline_data.get("suggested_tone"), str) and \
                                       isinstance(edited_outline_data.get("sections"), list):
                                        context.generated_outline = Outline(
                                            title=edited_outline_data['title'],
                                            suggested_tone=edited_outline_data['suggested_tone'],
                                            sections=[convert_edited_section_to_model(s_data) for s_data in edited_outline_data['sections']],
                                            status="outline"  # "approved_by_user_edit" から "outline" に修正
                                        )
                                        context.current_step = "outline_approved"
                                        console.print("[green]クライアントがアウトラインを編集し、承認しました。[/green]")
                                        await self._send_server_event(context, StatusUpdatePayload(step=context.current_step, message="Outline edited and approved.", image_mode=getattr(context, 'image_mode', False)))
                                        
                                        # Save context after outline editing and approval
                                        if process_id and user_id:
                                            try:
                                                await self._save_context_to_db(context, process_id=process_id, user_id=user_id)
                                                logger.info("Context saved successfully after outline editing and approval")
                                            except Exception as save_err:
                                                logger.error(f"Failed to save context after outline editing: {save_err}")
                                        continue  # ★重要: continueでループの次のイテレーションへ
                                    else:
                                        await self._send_error(context, "Invalid edited outline content structure.")
                                        context.current_step = "outline_generated"
                                        continue
                                except (ValidationError, TypeError, AttributeError, KeyError) as e:
                                    await self._send_error(context, f"Error processing edited outline: {e}")
                                    context.current_step = "outline_generated"
                                    continue
                            else:
                                await self._send_error(context, f"予期しない応答 ({response_type}) がアウトライン承認で受信されました。")
                                context.current_step = "outline_generated"
                                continue
                        else:
                            console.print("[red]アウトラインの承認/編集でクライアントからの応答がありませんでした。[/red]")
                            context.current_step = "outline_generated"
                            continue
                    elif isinstance(agent_output, ClarificationNeeded):
                        await self._send_error(context, f"アウトライン生成で確認が必要になりました: {agent_output.message}")
                        context.current_step = "error"
                        continue
                    else:
                        raise TypeError(f"予期しないAgent出力タイプ: {type(agent_output)}") # エラー送信の方が良い

                elif context.current_step == "outline_approved": # ★ 新しいステップの開始
                    # context.generated_outline を context.outline_approved に基づいて設定 (あるいは承認されたものがそのまま使われる)
                    # if not context.outline_approved: raise ValueError("承認済みアウトラインがありません。")
                    console.print("記事執筆ステップに進みます...")
                    
                    # セクションライティングの初期化（重要：current_section_indexを0にリセット）
                    context.current_section_index = 0
                    context.generated_sections_html = []
                    context.section_writer_history = []
                    
                    console.print(f"[yellow]セクションライティング初期化: {len(context.generated_outline.sections)}セクションを実行予定[/yellow]")
                    
                    context.current_step = "writing_sections" 

                elif context.current_step == "writing_sections":
                    if not context.generated_outline:
                        raise ValueError("承認済みアウトラインがありません。")
                    
                    # セクション完了判定を厳密化
                    total_sections = len(context.generated_outline.sections)
                    generated_sections_count = len([s for s in context.generated_sections_html if s and s.strip()])
                    
                    console.print(f"[yellow]セクション進捗: {context.current_section_index}/{total_sections}, 生成済み: {generated_sections_count}[/yellow]")
                    
                    if context.current_section_index >= total_sections:
                        # 実際にすべてのセクションが生成されているかを確認
                        if generated_sections_count < total_sections:
                            console.print(f"[red]エラー: セクションインデックス({context.current_section_index})は完了を示しているが、実際の生成セクション数({generated_sections_count})が不足[/red]")
                            console.print("[yellow]セクションライティングを再開します[/yellow]")
                            # 不足分から再開
                            context.current_section_index = generated_sections_count
                        else:
                            # 画像モードの場合は記事全体に最低1つの画像プレースホルダーがあることを確認
                            if getattr(context, 'image_mode', False):
                                total_placeholders = len(getattr(context, 'image_placeholders', []))
                                if total_placeholders == 0:
                                    raise ValueError("画像モードで記事を生成しましたが、記事全体に画像プレースホルダーが1つも含まれていません。記事全体で最低1つの画像プレースホルダーが必要です。")
                                console.print(f"[green]画像プレースホルダー検証OK: 記事全体で{total_placeholders}個のプレースホルダーが含まれています[/green]")
                            
                            context.full_draft_html = context.get_full_draft()
                            
                            # 空のドラフトチェック
                            if not context.full_draft_html or len(context.full_draft_html.strip()) < 100:
                                console.print(f"[red]エラー: 生成されたドラフトが空または短すぎます（{len(context.full_draft_html) if context.full_draft_html else 0}文字）[/red]")
                                raise ValueError("セクションライティングが正常に完了していません。ドラフトが空です。")
                            
                            context.current_step = "editing"
                            console.print(f"[green]全{total_sections}セクションの執筆が完了しました（{len(context.full_draft_html)}文字）。編集ステップに移ります。[/green]")
                            await self._send_server_event(context, EditingStartPayload())
                            continue

                    # 画像モードかどうかでエージェントを選択
                    if getattr(context, 'image_mode', False):
                        current_agent = section_writer_with_images_agent
                        console.print(f"[cyan]画像モードが有効: {current_agent.name} を使用[/cyan]")
                    else:
                        current_agent = section_writer_agent
                    target_index = context.current_section_index
                    target_heading = context.generated_outline.sections[target_index].heading # context.outline_approved から context.generated_outline に変更

                    # セクション執筆処理をカスタムスパンでラップ
                    with safe_custom_span("section_writing", data={
                        "section_index": target_index,
                        "section_heading": target_heading,
                        "total_sections": len(context.generated_outline.sections)
                    }):
                        user_request = f"前のセクション（もしあれば）に続けて、アウトラインのセクション {target_index + 1}「{target_heading}」の内容をHTMLで執筆してください。提供された詳細リサーチ情報を参照し、必要に応じて出典へのリンクを含めてください。"
                        current_input_messages: List[Dict[str, Any]] = list(context.section_writer_history)
                        current_input_messages.append({"role": "user", "content": [{"type": "input_text", "text": user_request}]})
                        agent_input = current_input_messages

                        # 画像モードの場合は通常のエージェント実行、そうでなければストリーミング実行
                        if getattr(context, 'image_mode', False):
                            # 画像モード: 通常のエージェント実行（structured output対応）
                            console.print(f"🤖 {current_agent.name} にセクション {target_index + 1} の執筆を依頼します (画像モード)...")
                            await self._send_server_event(context, StatusUpdatePayload(step=context.current_step, message=f"Writing section {target_index + 1}: {target_heading} (with images)", image_mode=True))
                            
                            agent_output = await self._run_agent(current_agent, agent_input, context, run_config)
                            
                            if isinstance(agent_output, ArticleSectionWithImages):
                                # 画像プレースホルダーが含まれている場合はログ出力するが、必須ではない
                                if agent_output.image_placeholders and len(agent_output.image_placeholders) > 0:
                                    console.print(f"[cyan]セクション {target_index + 1} に画像プレースホルダーが含まれています: {len(agent_output.image_placeholders)}個[/cyan]")
                                else:
                                    console.print(f"[yellow]セクション {target_index + 1} には画像プレースホルダーが含まれていません（記事全体で1つ以上あれば問題ありません）[/yellow]")
                                
                                generated_section = ArticleSection(
                                    section_index=target_index, 
                                    heading=target_heading, 
                                    html_content=agent_output.html_content
                                )
                                console.print(f"[green]セクション {target_index + 1}「{generated_section.heading}」を画像プレースホルダー付きで生成しました。（{len(agent_output.html_content)}文字、画像{len(agent_output.image_placeholders)}個）[/green]")
                                
                                # 画像プレースホルダー情報をコンテキストに保存
                                if not hasattr(context, 'image_placeholders'):
                                    context.image_placeholders = []
                                context.image_placeholders.extend(agent_output.image_placeholders)
                                
                                # プレースホルダー情報をデータベースに保存
                                await self._save_image_placeholders_to_db(context, agent_output.image_placeholders, target_index)
                                
                                # セクション内容をcontextに保存
                                if len(context.generated_sections_html) <= target_index:
                                    context.generated_sections_html.extend([""] * (target_index + 1 - len(context.generated_sections_html)))
                                
                                context.generated_sections_html[target_index] = generated_section.html_content
                                context.last_agent_output = generated_section
                                
                                # 会話履歴更新
                                last_user_request_item = agent_input[-1] if isinstance(agent_input, list) else None
                                if last_user_request_item and last_user_request_item.get('role') == 'user':
                                    user_request_text = last_user_request_item['content'][0]['text']
                                    context.add_to_section_writer_history("user", user_request_text)
                                context.add_to_section_writer_history("assistant", generated_section.html_content)
                                
                                # セクション完了後にインデックスを更新
                                context.current_section_index = target_index + 1
                                
                                # Save context after each section completion（必須）
                                if process_id and user_id:
                                    try:
                                        await self._save_context_to_db(context, process_id=process_id, user_id=user_id)
                                        logger.info(f"Context saved successfully after section {context.current_section_index}/{len(context.generated_outline.sections)} completion")
                                    except Exception as save_err:
                                        logger.error(f"Failed to save context after section completion: {save_err}")
                                
                                console.print(f"[blue]セクション {target_index + 1} 完了。次のセクション: {context.current_section_index + 1}[/blue]")
                                
                                # WebSocketでセクション完了を通知（画像モード）
                                console.print(f"[magenta]🔍 WebSocket notification check: websocket={context.websocket is not None}, target_index={target_index}, target_heading='{target_heading}'[/magenta]")
                                if context.websocket:
                                    try:
                                        
                                        console.print(f"[magenta]🔍 Agent output has image_placeholders: {hasattr(agent_output, 'image_placeholders')}, count: {len(getattr(agent_output, 'image_placeholders', []))}[/magenta]")
                                        
                                        image_placeholders_data = [
                                            ImagePlaceholderData(
                                                placeholder_id=placeholder.placeholder_id,
                                                description_jp=placeholder.description_jp,
                                                prompt_en=placeholder.prompt_en,
                                                alt_text=placeholder.alt_text
                                            )
                                            for placeholder in agent_output.image_placeholders
                                        ]
                                        
                                        payload = SectionChunkPayload(
                                            section_index=target_index,
                                            heading=target_heading,
                                            html_content_chunk="",  # 画像モードではチャンクではなく完了時に送信
                                            is_complete=True,
                                            section_complete_content=generated_section.html_content,
                                            image_placeholders=image_placeholders_data,
                                            is_image_mode=True
                                        )
                                        console.print(f"[cyan]📤 Sending SectionChunkPayload for image mode: section_index={target_index}, heading='{target_heading}', is_image_mode=True, content_length={len(generated_section.html_content)}, placeholders={len(image_placeholders_data)}[/cyan]")
                                        await self._send_server_event(context, payload)
                                        console.print(f"[green]✅ SectionChunkPayload sent successfully for section {target_index}[/green]")
                                    except Exception as e:
                                        console.print(f"[red]❌ Failed to send SectionChunkPayload for section {target_index}: {e}[/red]")
                                        console.print(f"[red]Traceback: {traceback.format_exc()}[/red]")
                                else:
                                    console.print(f"[yellow]⚠️ No WebSocket connection available for section {target_index} notification[/yellow]")
                            else:
                                raise TypeError(f"画像モードで予期しないAgent出力タイプ: {type(agent_output)}")
                        else:
                            # 通常モード: ストリーミング実行
                            console.print(f"🤖 {current_agent.name} にセクション {target_index + 1} の執筆を依頼します (Streaming)...")
                            await self._send_server_event(context, StatusUpdatePayload(step=context.current_step, message=f"Writing section {target_index + 1}: {target_heading}", image_mode=False))

                            accumulated_html = ""
                            stream_result = None
                            last_exception = None
                            start_time = time.time()  # start_time変数を定義

                            for attempt in range(settings.max_retries):
                                try:
                                    console.print(f"[dim]ストリーミング開始 (試行 {attempt + 1}/{settings.max_retries})...[/dim]")
                                    stream_result = Runner.run_streamed(
                                        starting_agent=current_agent, input=agent_input, context=context, run_config=run_config, max_turns=10
                                    )
                                    console.print(f"[dim]ストリーム開始: セクション {target_index + 1}「{target_heading}」[/dim]")
                                    accumulated_html = ""

                                    async for event in stream_result.stream_events():
                                        if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
                                            delta = event.data.delta
                                            accumulated_html += delta
                                            # WebSocketでHTMLチャンクを送信（切断時は無視して継続）
                                            try:
                                                await self._send_server_event(context, SectionChunkPayload(
                                                    section_index=target_index,
                                                    heading=target_heading,
                                                    html_content_chunk=delta,
                                                    is_complete=False
                                                ))
                                            except Exception as ws_err:
                                                # WebSocket送信エラーは無視して処理を継続
                                                console.print(f"[dim]WebSocket送信エラー（処理継続）: {ws_err}[/dim]")
                                                # WebSocket参照をクリアして今後の送信を防ぐ
                                                if context.websocket:
                                                    context.websocket = None
                                        elif event.type == "run_item_stream_event" and event.item.type == "tool_call_item":
                                            console.print(f"\n[dim]ツール呼び出し: {event.item.name}[/dim]")
                                        elif event.type == "raw_response_event" and isinstance(event.data, ResponseCompletedEvent):
                                             console.print("\n[dim]レスポンス完了イベント受信[/dim]")

                                    console.print(f"\n[dim]ストリーム終了: セクション {target_index + 1}「{target_heading}」[/dim]")
                                    last_exception = None
                                    break
                                except (InternalServerError, BadRequestError, MaxTurnsExceeded, ModelBehaviorError, AgentsException, UserError, AuthenticationError, Exception) as e:
                                    last_exception = e
                                    attempt_time = time.time() - start_time
                                    error_type = type(e).__name__
                                    
                                    # エラーメトリクス記録
                                    logger.warning(f"ストリーミング実行エラー (試行 {attempt + 1}/{settings.max_retries}): {error_type} - {e}, 経過時間: {attempt_time:.2f}秒")
                                    
                                    console.print(f"\n[yellow]ストリーミング中にエラー発生 (試行 {attempt + 1}/{settings.max_retries}): {error_type} - {e}[/yellow]")
                                    if isinstance(e, (BadRequestError, MaxTurnsExceeded, ModelBehaviorError, UserError, AuthenticationError)):
                                        break # リトライしないエラー
                                    if attempt < settings.max_retries - 1:
                                        delay = settings.initial_retry_delay * (2 ** attempt)
                                        await asyncio.sleep(delay)
                                    else:
                                        context.error_message = f"ストリーミングエラー: {str(e)}"
                                        context.current_step = "error"
                                        break

                            if context.current_step == "error": 
                                break
                            if last_exception: 
                                raise last_exception

                            # セクション完全性をチェック
                            if accumulated_html and len(accumulated_html.strip()) > 50:  # 最小長チェック
                                generated_section = ArticleSection(
                                    section_index=target_index, heading=target_heading, html_content=accumulated_html.strip()
                                )
                                console.print(f"[green]セクション {target_index + 1}「{generated_section.heading}」のHTMLをストリームから構築しました。（{len(accumulated_html)}文字）[/green]")
                                
                                # 完了イベントを送信（WebSocket切断時は無視される）
                                try:
                                    await self._send_server_event(context, SectionChunkPayload(
                                        section_index=target_index, heading=target_heading, html_content_chunk="", is_complete=True
                                    ))
                                except Exception as ws_err:
                                    console.print(f"[dim]セクション完了イベント送信エラー（処理継続）: {ws_err}[/dim]")
                                
                                # セクション内容をcontextに保存
                                if len(context.generated_sections_html) <= target_index:
                                    # リストを拡張
                                    context.generated_sections_html.extend([""] * (target_index + 1 - len(context.generated_sections_html)))
                                
                                context.generated_sections_html[target_index] = generated_section.html_content
                                context.last_agent_output = generated_section
                                
                                # 会話履歴更新
                                last_user_request_item = agent_input[-1] if isinstance(agent_input, list) else None
                                if last_user_request_item and last_user_request_item.get('role') == 'user':
                                    user_request_text = last_user_request_item['content'][0]['text']
                                    context.add_to_section_writer_history("user", user_request_text)
                                context.add_to_section_writer_history("assistant", generated_section.html_content)
                                
                                # セクション完了後にインデックスを更新
                                context.current_section_index = target_index + 1
                                
                                # Save context after each section completion（必須）
                                if process_id and user_id:
                                    try:
                                        await self._save_context_to_db(context, process_id=process_id, user_id=user_id)
                                        logger.info(f"Context saved successfully after section {context.current_section_index}/{len(context.generated_outline.sections)} completion")
                                    except Exception as save_err:
                                        logger.error(f"Failed to save context after section completion: {save_err}")
                                        # セーブに失敗しても処理は継続
                                
                                console.print(f"[blue]セクション {target_index + 1} 完了。次のセクション: {context.current_section_index + 1}[/blue]")
                            else:
                                # セクションが不完全な場合はエラーとしてリトライ
                                error_msg = f"セクション {target_index + 1} のHTMLコンテンツが不完全または空です（{len(accumulated_html) if accumulated_html else 0}文字）"
                                console.print(f"[red]{error_msg}[/red]")
                                raise ValueError(error_msg)

                elif context.current_step == "editing":
                    current_agent = editor_agent
                    if not context.full_draft_html:
                        raise ValueError("編集対象のドラフトがありません。")
                    agent_input = "記事ドラフト全体をレビューし、詳細リサーチ情報に基づいて推敲・編集してください。特にリンクの適切性を確認してください。"
                    console.print(f"🤖 {current_agent.name} に最終編集を依頼します...")
                    await self._send_server_event(context, StatusUpdatePayload(step=context.current_step, message="Starting final editing...", image_mode=getattr(context, 'image_mode', False)))
                    agent_output = await self._run_agent(current_agent, agent_input, context, run_config)

                    if isinstance(agent_output, RevisedArticle):
                        context.final_article_html = agent_output.final_html_content
                        context.current_step = "completed"
                        console.print("[green]記事の編集が完了しました！[/green]")
                        
                        # ワークフローロガーを最終化（最終編集完了）
                        if process_id:
                            await self.finalize_workflow_logger(process_id, "completed")
                        
                        # Save context after final article completion
                        if process_id and user_id:
                            try:
                                await self._save_context_to_db(context, process_id=process_id, user_id=user_id)
                                logger.info("Context saved successfully after final article completion")
                            except Exception as save_err:
                                logger.error(f"Failed to save context after final article completion: {save_err}")

                        # --- 1. DBへ保存して article_id を取得 ---
                        article_id: Optional[str] = None
                        if process_id and user_id:
                            try:
                                # 先に保存処理を実行（articles への INSERT を含む）
                                await self._save_context_to_db(context, process_id=process_id, user_id=user_id)

                                # 保存後に generated_articles_state から article_id を取得
                                from app.domains.seo_article.services.flow_service import get_supabase_client
                                supabase = get_supabase_client()
                                state_res = supabase.table("generated_articles_state").select("article_id").eq("id", process_id).execute()
                                if state_res.data and state_res.data[0].get("article_id"):
                                    article_id = state_res.data[0]["article_id"]
                            except Exception as fetch_err:
                                console.print(f"[yellow]Warning: article_id の取得に失敗しました: {fetch_err}[/yellow]")

                        # --- 2. WebSocketで最終結果を送信（article_id 付き） ---
                        await self._send_server_event(context, FinalResultPayload(
                            title=agent_output.title,
                            final_html_content=agent_output.final_html_content,
                            article_id=article_id
                        ))
                         
                         # ループ終了時のステータス更新は _run_generation_loop の finally で行う
                         
                         # context は最新だが、この段階で article_id を保持していなくてもよい
                    else:
                        raise TypeError(f"予期しないAgent出力タイプ: {type(agent_output)}")

                else:
                    # ユーザー入力が必要なステップの場合、ユーザー応答を待機して処理
                    if context.current_step in USER_INPUT_STEPS:
                        console.print(f"[yellow]ステップ {context.current_step} はユーザー入力が必要です。ユーザー応答を処理します。[/yellow]")
                        await self._handle_user_input_step(context, process_id, user_id)
                        continue  # 処理後にループを継続
                    else:
                        raise ValueError(f"未定義のステップ: {context.current_step}")

        except asyncio.CancelledError:
             console.print("[yellow]Generation loop cancelled.[/yellow]")
             await self._send_error(context, "Generation process cancelled.", context.current_step)
        except Exception as e:
            context.current_step = "error"
            error_message = f"記事生成プロセス中にエラーが発生しました: {type(e).__name__} - {str(e)}"
            context.error_message = error_message
            console.print(f"[bold red]Error in generation loop:[/bold red] {error_message}")
            traceback.print_exc()
            
            # ワークフローロガーを最終化（エラー状態）
            if process_id:
                await self.finalize_workflow_logger(process_id, "failed")
            
            # WebSocketでエラーイベントを送信
            await self._send_error(context, error_message, context.current_step) # stepを指定
        finally:
            # ログセッションを完了（ただし、切断耐性ステップの場合はロガーを保持）
            if LOGGING_ENABLED and process_id in self.workflow_loggers:
                try:
                    workflow_logger = self.workflow_loggers[process_id]
                    
                    # 最終記事内容を取得
                    if hasattr(context, 'final_html_content') and context.final_html_content:
                        pass
                    elif hasattr(context, 'revised_article') and context.revised_article and hasattr(context.revised_article, 'final_html_content'):
                        pass
                    
                    # 切断耐性ステップかどうかを確認
                    is_disconnection_resilient = context.current_step in DISCONNECTION_RESILIENT_STEPS
                    
                    # セッション状態を決定
                    session_status = "completed" if context.current_step == "completed" else "failed"
                    
                    if is_disconnection_resilient and context.current_step != "completed" and context.current_step != "error":
                        # 切断耐性ステップでは、まだ処理が継続する可能性があるためログセッションを維持
                        console.print(f"[cyan]Keeping log session active for disconnection-resilient step: {context.current_step}[/cyan]")
                        # ワークフロステップをログに記録
                        workflow_logger.log_workflow_step(f"background_processing_{context.current_step}", {
                            "step": context.current_step,
                            "background_processing": True,
                            "websocket_disconnected": context.websocket is None
                        })
                    else:
                        # 完了または切断耐性でないステップの場合は、ログセッションを完了しロガーを削除
                        workflow_logger.finalize_session(session_status)
                        console.print(f"[cyan]Finalized log session for process {process_id} with status: {session_status}[/cyan]")
                        
                        # Notionに自動同期（完了したセッションのみ）
                        if NOTION_SYNC_ENABLED and self.notion_sync_service and session_status == "completed":
                            try:
                                console.print(f"[yellow]🔄 Notionに自動同期開始: {process_id}[/yellow]")
                                sync_success = self.notion_sync_service.sync_session_to_notion(workflow_logger.session_id)
                                if sync_success:
                                    console.print(f"[green]✅ Notion自動同期完了: {process_id}[/green]")
                                else:
                                    console.print(f"[red]❌ Notion自動同期失敗: {process_id}[/red]")
                            except Exception as sync_err:
                                logger.warning(f"Notion auto-sync failed: {sync_err}")
                                console.print(f"[red]❌ Notion自動同期エラー: {sync_err}[/red]")
                        
                        # クリーンアップ
                        del self.workflow_loggers[process_id]
                        console.print(f"[cyan]Workflow logger cleaned up for process {process_id}[/cyan]")
                    
                except Exception as log_err:
                    logger.error(f"Failed to finalize logging session: {log_err}")
            
            # ループ終了時に特別なメッセージを送る (任意) - ユーザー入力待ちの場合は送信しない
            if context.current_step == "completed":
                 await self._send_server_event(context, StatusUpdatePayload(step="finished", message="Article generation completed successfully.", image_mode=getattr(context, 'image_mode', False)))
            elif context.current_step == "error":
                 await self._send_server_event(context, StatusUpdatePayload(step="finished", message=f"Article generation finished with error: {context.error_message}", image_mode=getattr(context, 'image_mode', False)))
            elif context.current_step in USER_INPUT_STEPS:
                 # ユーザー入力待ちの場合は finished メッセージを送信しない
                 console.print(f"[yellow]Generation loop stopped at user input step: {context.current_step}[/yellow]")
            else:
                 # キャンセルされた場合など
                 await self._send_server_event(context, StatusUpdatePayload(step="finished", message="Article generation finished unexpectedly.", image_mode=getattr(context, 'image_mode', False)))


    async def _run_agent(
        self,
        agent: Agent[ArticleContext],
        input_data: Union[str, List[Dict[str, Any]]],
        context: ArticleContext,
        run_config: RunConfig
    ) -> Any:
        """エージェントを実行し、結果を返す（リトライ付き）"""
        last_exception = None
        start_time = time.time()
        execution_log_id = None
        
        # プロセスIDを取得してログを開始
        process_id = context.process_id
        console.print(f"[dim]Agent execution - process_id: {process_id}, workflow_loggers keys: {list(self.workflow_loggers.keys())}[/dim]")
        
        # ワークフローロガーの取得・作成を確実に行う
        workflow_logger = self.workflow_loggers.get(process_id) if process_id else None
        if not workflow_logger and process_id and LOGGING_ENABLED and MultiAgentWorkflowLogger:
            console.print(f"[yellow]⚠️ No workflow logger found for process {process_id}, creating one now[/yellow]")
            try:
                await self._ensure_workflow_logger(context, process_id, getattr(context, 'user_id', 'unknown'))
                workflow_logger = self.workflow_loggers.get(process_id)
                console.print(f"[green]✅ Successfully created workflow logger for process {process_id}[/green]")
            except Exception as e:
                console.print(f"[red]❌ Failed to create workflow logger for process {process_id}: {e}[/red]")
        
        console.print(f"[dim]workflow_logger found: {workflow_logger is not None}[/dim]")
        
        if not workflow_logger and process_id:
            console.print(f"[red]❌ No workflow logger found for process {process_id}! This will prevent logging.[/red]")
            console.print(f"[yellow]Available workflow logger keys: {list(self.workflow_loggers.keys())}[/yellow]")
            console.print(f"[yellow]LOGGING_ENABLED: {LOGGING_ENABLED}[/yellow]")
        elif workflow_logger:
            console.print(f"[green]✅ Workflow logger found: session_id={workflow_logger.session_id}, current_step={workflow_logger.current_step}[/green]")
        
        # エージェントから実際のモデル情報を取得（関数全体で使用するため外に移動）
        agent_model = getattr(agent, 'model', 'unknown')
        
        # モデル設定から環境変数のモデル名も取得
        model_from_config = None
        if agent.name == "ThemeAgent":
            model_from_config = settings.default_model
        elif agent.name in ["ResearchPlannerAgent", "ResearcherAgent", "ResearchSynthesizerAgent", "SerpKeywordAnalysisAgent"]:
            model_from_config = settings.research_model
        elif agent.name in ["SectionWriterAgent", "SectionWriterWithImagesAgent", "OutlineAgent"]:
            model_from_config = settings.writing_model
        elif agent.name == "EditorAgent":
            model_from_config = settings.editing_model
        elif agent.name == "PersonaGeneratorAgent":
            model_from_config = settings.default_model
        else:
            model_from_config = settings.default_model
        
        # 実際に使用されるモデル名（agent.modelを優先、フォールバックで設定から）
        actual_model = agent_model if agent_model != 'unknown' else model_from_config
        
        # システムプロンプトの取得（関数全体で使用するため外に移動）
        system_prompt = ""
        if hasattr(agent, 'instructions'):
            if callable(agent.instructions):
                # 動的指示の場合、run_contextを使って取得
                try:
                    from agents import RunContextWrapper
                    run_context = RunContextWrapper(context=context)
                    system_prompt = await agent.instructions(run_context, agent)
                    console.print(f"[green]✅ Dynamic system prompt extracted successfully for {agent.name} ({len(system_prompt)} chars)[/green]")
                    # デバッグ用にシステムプロンプトの一部を出力
                    if logger.isEnabledFor(logging.DEBUG):
                        console.print(f"[debug]System prompt preview: {system_prompt[:300]}...")
                except Exception as e:
                    logger.warning(f"Failed to get dynamic instructions for {agent.name}: {e}")
                    system_prompt = f"Dynamic instructions (failed to resolve: {str(e)})"
                    console.print(f"[yellow]⚠️ Dynamic system prompt extraction failed for {agent.name}: {e}[/yellow]")
            else:
                system_prompt = str(agent.instructions)
                console.print(f"[green]✅ Static system prompt extracted for {agent.name} ({len(system_prompt)} chars)[/green]")
        else:
            system_prompt = "No instructions found"
            console.print(f"[yellow]⚠️ No instructions found for {agent.name}[/yellow]")
        
        # システムプロンプトをログに出力（デバッグ用）
        if logger.isEnabledFor(logging.DEBUG):
            console.print(f"[debug]System prompt for {agent.name}: {system_prompt[:200]}..." if len(system_prompt) > 200 else f"[debug]System prompt for {agent.name}: {system_prompt}")
        
        try:
            if LOGGING_ENABLED and workflow_logger and self.logging_service:
                console.print(f"[yellow]Creating execution log for agent {agent.name} in session {workflow_logger.session_id}[/yellow]")
                
                execution_log_id = self.logging_service.create_execution_log(
                    session_id=workflow_logger.session_id,
                    agent_name=agent.name,
                    agent_type=context.current_step,
                    step_number=workflow_logger.current_step,
                    input_data={
                        "input_data": str(input_data)[:2000] if input_data else "",
                        "input_type": type(input_data).__name__,
                        "context_step": context.current_step,
                        "system_prompt": system_prompt[:2000] if system_prompt else "",
                        "full_system_prompt_length": len(system_prompt) if system_prompt else 0
                    },
                    llm_model=actual_model,
                    execution_metadata={
                        "trace_id": run_config.trace_id,
                        "group_id": run_config.group_id,
                        "max_retries": settings.max_retries,
                        "agent_model_attribute": agent_model,
                        "model_from_config": model_from_config,
                        "actual_model_used": actual_model,
                        "system_prompt_length": len(system_prompt) if system_prompt else 0,
                        "system_prompt_type": "dynamic" if callable(getattr(agent, 'instructions', None)) else "static",
                        "agent_class": str(type(agent).__name__)
                    }
                )
                console.print(f"[green]Created execution log {execution_log_id} for agent {agent.name}[/green]")
                
                # ワークフローステップもログに記録
                workflow_step_id = workflow_logger.log_workflow_step(
                    step_name=f"agent_execution_{agent.name.lower()}",
                    step_data={
                        "agent_name": agent.name,
                        "agent_type": context.current_step,
                        "input_summary": str(input_data)[:500] if input_data else "",
                        "execution_attempt": 1,
                        "model": actual_model
                    },
                    primary_execution_id=execution_log_id
                )
                console.print(f"[cyan]📋 Workflow step logged: {workflow_step_id}[/cyan]")
                
        except Exception as log_err:
            logger.warning(f"Failed to create execution log: {log_err}")
            console.print(f"[red]Failed to create execution log: {log_err}[/red]")
            execution_log_id = None
            workflow_step_id = None
        
        # エージェント実行をカスタムスパンでラップ
        with safe_custom_span("agent_execution", data={
            "agent_name": agent.name,
            "current_step": context.current_step,
            "max_retries": settings.max_retries,
            "input_type": type(input_data).__name__,
            "input_length": len(str(input_data)) if input_data else 0,
            "execution_start_time": start_time,
            "execution_log_id": execution_log_id
        }):
            for attempt in range(settings.max_retries):
                try:
                    console.print(f"[dim]エージェント {agent.name} 実行開始 (試行 {attempt + 1}/{settings.max_retries})...[/dim]")
                    
                    # エージェント実行
                    result = await Runner.run(
                        starting_agent=agent,
                        input=input_data,
                        context=context,
                        run_config=run_config,
                        max_turns=10
                    )
                    
                    console.print(f"[dim]エージェント {agent.name} 実行完了。[/dim]")

                    # LLM呼び出し統計と会話履歴を詳細記録
                    if LOGGING_ENABLED and execution_log_id and self.logging_service and result:
                        try:
                            # トークン使用量と会話履歴を抽出
                            token_usage = self._extract_token_usage_from_result(result)
                            console.print(f"[debug]Token usage extraction result: {type(token_usage)}")
                            
                            conversation_history = self._extract_conversation_history_from_result(result, str(input_data))
                            console.print(f"[debug]Conversation history extraction result: {type(conversation_history)}")
                            console.print(f"[debug]Conversation history keys: {list(conversation_history.keys()) if isinstance(conversation_history, dict) else 'Not a dict'}")
                            
                            # LLM呼び出しログを常に作成（条件を緩和）
                            console.print(f"[debug]Creating LLM call log: token_usage={token_usage is not None}, conversation_history={isinstance(conversation_history, dict)}")
                            
                            # 基本的なログデータを準備
                            system_prompt_text = ""
                            user_prompt_text = str(input_data)[:2000] if input_data else ""
                            response_text = ""
                            
                            if isinstance(conversation_history, dict):
                                # 会話履歴から詳細情報を取得
                                conversation_system_prompt = conversation_history.get("system_prompt", "")
                                # 動的に取得したシステムプロンプトを優先使用
                                system_prompt_text = system_prompt if system_prompt else conversation_system_prompt
                                user_prompt_text = conversation_history.get("user_prompt", user_prompt_text)
                                response_text = conversation_history.get("assistant_response", "")
                                
                                console.print(f"[debug]Using conversation history - system: {len(system_prompt_text)} chars, user: {len(user_prompt_text)} chars, response: {len(response_text)} chars")
                            else:
                                # フォールバック: 動的に取得したシステムプロンプトを使用
                                system_prompt_text = system_prompt if system_prompt else ""
                                response_text = str(result.final_output) if hasattr(result, 'final_output') else ""
                                
                                console.print(f"[debug]Using fallback data - system: {len(system_prompt_text)} chars, user: {len(user_prompt_text)} chars, response: {len(response_text)} chars")
                            
                            # トークン使用量（デフォルト値を使用）
                            input_tokens = token_usage.get("input_tokens", 0) if token_usage else 100
                            output_tokens = token_usage.get("output_tokens", 0) if token_usage else 50
                            total_tokens = token_usage.get("total_tokens", 0) if token_usage else (input_tokens + output_tokens)
                            cached_tokens = token_usage.get("cache_tokens", 0) if token_usage else 0
                            reasoning_tokens = token_usage.get("reasoning_tokens", 0) if token_usage else 0
                            estimated_cost = token_usage.get("estimated_cost", 0.0) if token_usage else 0.001
                            
                            # 常にLLM呼び出しログを作成
                            llm_call_id = self.logging_service.create_llm_call_log(
                                execution_id=execution_log_id,
                                call_sequence=1,
                                api_type="chat_completions",
                                model_name=actual_model,
                                provider="openai",
                                system_prompt=system_prompt_text,
                                user_prompt=user_prompt_text,
                                response_content=response_text,
                                prompt_tokens=input_tokens,
                                completion_tokens=output_tokens,
                                total_tokens=total_tokens,
                                cached_tokens=cached_tokens,
                                reasoning_tokens=reasoning_tokens,
                                estimated_cost_usd=estimated_cost,
                                full_prompt_data={
                                    "agent_name": agent.name,
                                    "attempt_number": attempt + 1,
                                    "max_turns": 10,
                                    "trace_id": run_config.trace_id,
                                    "tool_calls": conversation_history.get("tool_calls", []) if isinstance(conversation_history, dict) else [],
                                    "reasoning": conversation_history.get("reasoning", "")[:1000] if isinstance(conversation_history, dict) else "",
                                    "actual_model_used": actual_model,
                                    "model_from_config": model_from_config,
                                    "full_system_prompt": system_prompt_text,
                                    "conversation_history_type": str(type(conversation_history)),
                                    "token_usage_available": token_usage is not None
                                },
                                response_data={
                                    "final_output": conversation_history.get("final_output", "")[:1000] if isinstance(conversation_history, dict) else "",
                                    "full_conversation": conversation_history.get("full_output", []) if isinstance(conversation_history, dict) else [],
                                    "result_type": str(type(result)),
                                    "result_has_final_output": hasattr(result, 'final_output')
                                }
                            )
                            
                            console.print(f"[green]✅ LLM call log created: {llm_call_id}[/green]")
                            
                            # ツール呼び出しログを記録
                            if isinstance(conversation_history, dict) and conversation_history.get("tool_calls"):
                                await self._log_tool_calls(execution_log_id, conversation_history.get("tool_calls", []))
                                
                            # 成功時のログ表示（両方のケース共通）
                            if 'llm_call_id' in locals() and llm_call_id:
                                console.print(f"[cyan]📋 LLM call logged: {llm_call_id}[/cyan]")
                                console.print(f"[dim]  Tokens: {token_usage.get('input_tokens', 0)} input + {token_usage.get('output_tokens', 0)} output = {token_usage.get('total_tokens', 0)} total[/dim]")
                                console.print(f"[dim]  Cost: ${token_usage.get('estimated_cost', 0.0):.6f}[/dim]")
                                if isinstance(conversation_history, dict):
                                    if conversation_history.get("tool_calls"):
                                        console.print(f"[dim]  Tool calls: {len(conversation_history.get('tool_calls', []))}[/dim]")
                                    if conversation_history.get("reasoning"):
                                        console.print(f"[dim]  Reasoning: {len(conversation_history.get('reasoning', ''))} chars[/dim]")
                                    # 実際のプロンプトとレスポンスの長さも表示
                                    console.print(f"[dim]  System prompt: {len(conversation_history.get('system_prompt', ''))} chars[/dim]")
                                    console.print(f"[dim]  User prompt: {len(conversation_history.get('user_prompt', ''))} chars[/dim]")
                                    console.print(f"[dim]  Assistant response: {len(conversation_history.get('assistant_response', ''))} chars[/dim]")
                            else:
                                console.print("[yellow]⚠️ LLM call not logged - no valid token usage or conversation history[/yellow]")
                                console.print(f"[yellow]  Token usage type: {type(token_usage)}, value: {token_usage}[/yellow]")
                                console.print(f"[yellow]  Conversation history type: {type(conversation_history)}[/yellow]")
                        except Exception as llm_log_err:
                            logger.warning(f"Failed to log LLM call: {llm_log_err}")
                            console.print(f"[red]❌ LLM logging failed: {llm_log_err}[/red]")

                    if result and result.final_output:
                         output = result.final_output
                         execution_time = time.time() - start_time
                         
                         # 成功時のメトリクス記録
                         logger.info(f"エージェント {agent.name} 実行成功: {execution_time:.2f}秒, 試行回数: {attempt + 1}")
                         
                         # 成功時のログ更新（トークン統計含む）
                         if LOGGING_ENABLED and execution_log_id and self.logging_service:
                             try:
                                 # トークン統計を取得
                                 token_usage = self._extract_token_usage_from_result(result)
                                 
                                 self.logging_service.update_execution_log(
                                     execution_id=execution_log_id,
                                     status="completed",
                                     output_data={
                                         "output_type": type(output).__name__,
                                         "output_summary": str(output)[:500] if output else "",
                                         "attempt_count": attempt + 1,
                                         "success": True
                                     },
                                     duration_ms=int(execution_time * 1000),
                                     input_tokens=token_usage.get("input_tokens", 0) if token_usage else 0,
                                     output_tokens=token_usage.get("output_tokens", 0) if token_usage else 0,
                                     cache_tokens=token_usage.get("cache_tokens", 0) if token_usage else 0,
                                     reasoning_tokens=token_usage.get("reasoning_tokens", 0) if token_usage else 0
                                 )
                             except Exception as log_err:
                                 logger.warning(f"Failed to update execution log: {log_err}")
                         
                         # ワークフローステップの状態も更新
                         if LOGGING_ENABLED and workflow_logger and 'workflow_step_id' in locals():
                             try:
                                 workflow_logger.update_workflow_step_status(
                                     step_id=workflow_step_id,
                                     status="completed",
                                     step_output={
                                         "agent_name": agent.name,
                                         "output_type": type(output).__name__,
                                         "output_summary": str(output)[:500] if output else "",
                                         "success": True,
                                         "attempt_count": attempt + 1,
                                         "token_usage": token_usage if 'token_usage' in locals() else {}
                                     },
                                     duration_ms=int(execution_time * 1000)
                                 )
                                 console.print(f"[cyan]📋 Workflow step completed: {workflow_step_id}[/cyan]")
                             except Exception as workflow_err:
                                 logger.warning(f"Failed to update workflow step: {workflow_err}")
                         
                         if isinstance(output, (ThemeProposal, Outline, RevisedArticle, ClarificationNeeded, StatusUpdate, ResearchPlan, ResearchQueryResult, ResearchReport, GeneratedPersonasResponse, SerpKeywordAnalysisReport, ArticleSectionWithImages)):
                             return output
                         elif isinstance(output, str):
                             try:
                                 parsed_output = json.loads(output)
                                 status_val = parsed_output.get("status") # 変数名を変更
                                 output_model_map = {
                                     "theme_proposal": ThemeProposal, "outline": Outline, "revised_article": RevisedArticle,
                                     "clarification_needed": ClarificationNeeded, "status_update": StatusUpdate,
                                     "research_plan": ResearchPlan, "research_query_result": ResearchQueryResult, "research_report": ResearchReport,
                                     "generated_personas_response": GeneratedPersonasResponse, "serp_keyword_analysis_report": SerpKeywordAnalysisReport,
                                     "article_section_with_images": ArticleSectionWithImages
                                 }
                                 if status_val in output_model_map:
                                     model_cls = output_model_map[status_val]
                                     return model_cls.model_validate(parsed_output)
                                 else:
                                     console.print(f"[yellow]警告: 不明なstatus '{status_val}' を含むJSON応答。[/yellow]")
                                     return parsed_output
                             except (json.JSONDecodeError, ValidationError) as parse_error:
                                 console.print(f"[yellow]警告: Agent応答のJSONパース/バリデーション失敗。内容: {output[:100]}... エラー: {parse_error}[/yellow]")
                                 raise ModelBehaviorError(f"Failed to parse/validate agent output: {parse_error}") from parse_error
                         else:
                             console.print(f"[yellow]警告: Agent応答が予期した型でない。型: {type(output)}[/yellow]")
                             raise ModelBehaviorError(f"Unexpected output type from agent: {type(output)}")
                    else:
                        console.print(f"[yellow]エージェント {agent.name} から有効な出力が得られませんでした。[/yellow]")
                        raise ModelBehaviorError(f"No valid final output from agent {agent.name}")

                except (InternalServerError, BadRequestError, MaxTurnsExceeded, ModelBehaviorError, AgentsException, UserError, AuthenticationError, Exception) as e:
                    last_exception = e
                    attempt_time = time.time() - start_time
                    error_type = type(e).__name__
                    
                    # エラーメトリクス記録
                    logger.warning(f"エージェント {agent.name} 実行エラー (試行 {attempt + 1}/{settings.max_retries}): {error_type} - {e}, 経過時間: {attempt_time:.2f}秒")
                    
                    # エラー時のログ更新（最後の試行の場合のみ）
                    if LOGGING_ENABLED and execution_log_id and self.logging_service and (attempt == settings.max_retries - 1 or isinstance(e, (BadRequestError, MaxTurnsExceeded, ModelBehaviorError, UserError, AuthenticationError))):
                        try:
                            self.logging_service.update_execution_log(
                                execution_id=execution_log_id,
                                status="failed",
                                duration_ms=int(attempt_time * 1000),
                                error_message=str(e),
                                error_details={
                                    "error_type": error_type,
                                    "attempt_count": attempt + 1,
                                    "max_retries": settings.max_retries,
                                    "is_retryable": not isinstance(e, (BadRequestError, MaxTurnsExceeded, ModelBehaviorError, UserError, AuthenticationError))
                                }
                            )
                        except Exception as log_err:
                            logger.warning(f"Failed to update execution log with error: {log_err}")
                    
                    # エラー時のワークフローステップ更新（最後の試行の場合のみ）
                    if LOGGING_ENABLED and workflow_logger and 'workflow_step_id' in locals() and (attempt == settings.max_retries - 1 or isinstance(e, (BadRequestError, MaxTurnsExceeded, ModelBehaviorError, UserError, AuthenticationError))):
                        try:
                            workflow_logger.update_workflow_step_status(
                                step_id=workflow_step_id,
                                status="failed",
                                step_output={
                                    "agent_name": agent.name,
                                    "error_type": error_type,
                                    "error_message": str(e),
                                    "attempt_count": attempt + 1,
                                    "success": False,
                                    "is_retryable": not isinstance(e, (BadRequestError, MaxTurnsExceeded, ModelBehaviorError, UserError, AuthenticationError))
                                },
                                duration_ms=int(attempt_time * 1000)
                            )
                            console.print(f"[red]📋 Workflow step failed: {workflow_step_id}[/red]")
                        except Exception as workflow_err:
                            logger.warning(f"Failed to update workflow step with error: {workflow_err}")
                    
                    console.print(f"[yellow]エージェント {agent.name} 実行中にエラー (試行 {attempt + 1}/{settings.max_retries}): {error_type} - {e}[/yellow]")
                    if isinstance(e, (BadRequestError, MaxTurnsExceeded, ModelBehaviorError, UserError, AuthenticationError)):
                        break
                    if attempt < settings.max_retries - 1:
                        delay = settings.initial_retry_delay * (2 ** attempt)
                        await asyncio.sleep(delay)
                    else:
                        break

            if last_exception:
                total_time = time.time() - start_time
                logger.error(f"エージェント {agent.name} の実行に失敗しました（リトライ上限到達）: 総実行時間 {total_time:.2f}秒, 最終エラー: {type(last_exception).__name__}")
                console.print(f"[bold red]エージェント {agent.name} の実行に失敗しました（リトライ上限到達）。[/bold red]")
                raise last_exception
            
            total_time = time.time() - start_time
            logger.error(f"エージェント {agent.name} execution finished unexpectedly: 総実行時間 {total_time:.2f}秒")
            raise RuntimeError(f"Agent {agent.name} execution finished unexpectedly.")

    async def _log_tool_calls(self, execution_id: str, tool_calls: List[Dict[str, Any]]):
        """ツール呼び出しログを記録"""
        if not LOGGING_ENABLED or not self.logging_service:
            return
        
        try:
            for i, tool_call in enumerate(tool_calls):
                tool_name = tool_call.get("name", "unknown_tool")
                tool_type = tool_call.get("type", "tool_call")
                arguments = tool_call.get("arguments", {})
                result = tool_call.get("result")
                
                # ツール固有の情報を抽出
                api_calls_count = 1
                data_size_bytes = None
                
                if tool_name == "web_search":
                    # WebSearch固有の統計
                    if isinstance(result, dict):
                        result.get("results", [])
                        api_calls_count = 1  # SerpAPIは通常1回の呼び出し
                        data_size_bytes = len(str(result))
                elif tool_name in ["analyze_competitors", "get_company_data"]:
                    # その他のツール統計
                    if result:
                        data_size_bytes = len(str(result))
                
                # ツール呼び出しログを作成
                tool_call_id = self.logging_service.create_tool_call_log(
                    execution_id=execution_id,
                    tool_name=tool_name,
                    tool_function=tool_type,
                    call_sequence=i + 1,
                    input_parameters=arguments,
                    output_data={"result": result} if result else {},
                    status="completed",
                    api_calls_count=api_calls_count,
                    data_size_bytes=data_size_bytes,
                    tool_metadata={
                        "tool_type": tool_type,
                        "has_result": result is not None,
                        "result_type": type(result).__name__ if result else None
                    }
                )
                
                console.print(f"[cyan]🔧 Tool call logged: {tool_call_id} ({tool_name})[/cyan]")
                
        except Exception as e:
            logger.warning(f"Failed to log tool calls: {e}")
            console.print(f"[red]❌ Tool call logging failed: {e}[/red]")

    async def _log_workflow_step(self, context: ArticleContext, step_name: str, step_data: Dict[str, Any] = None):
        """ワークフローステップをログに記録"""
        if not LOGGING_ENABLED:
            return
        
        try:
            process_id = context.process_id
            workflow_logger = self.workflow_loggers.get(process_id) if process_id else None
            
            if workflow_logger and self.logging_service:
                # ステップタイプを決定
                step_type = "autonomous"
                if step_name in USER_INPUT_STEPS:
                    step_type = "user_input"
                elif step_name in ["error", "completed"]:
                    step_type = "terminal"
                
                step_id = self.logging_service.create_workflow_step_log(
                    session_id=workflow_logger.session_id,
                    step_name=step_name,
                    step_type=step_type,
                    step_order=workflow_logger.current_step,
                    step_input=step_data or {},
                    step_metadata={
                        "process_id": process_id,
                        "context_step": step_name,
                        "timestamp": datetime.now().isoformat(),
                        "step_category": step_type
                    }
                )
                
                console.print(f"[cyan]📊 Workflow step logged: {step_id} ({step_name})[/cyan]")
                
        except Exception as e:
            logger.warning(f"Failed to log workflow step: {e}")
            console.print(f"[red]❌ Workflow step logging failed: {e}[/red]")

    async def _ensure_workflow_logger(self, context: ArticleContext, process_id: Optional[str] = None, user_id: Optional[str] = None):
        """ワークフローロガーを確実に確保する"""
        if not process_id or not LOGGING_ENABLED:
            console.print(f"[yellow]Workflow logger not needed: process_id={process_id}, LOGGING_ENABLED={LOGGING_ENABLED}[/yellow]")
            return
        
        # 既存のワークフローロガーをチェック
        workflow_logger = self.workflow_loggers.get(process_id)
        if workflow_logger:
            console.print(f"[green]✅ Workflow logger already exists for process {process_id} (session: {workflow_logger.session_id})[/green]")
            return
        
        # ワークフローロガーを作成
        console.print(f"[yellow]🔄 Creating workflow logger for process {process_id}[/yellow]")
        try:
            # コンテキストから設定を構築
            initial_config = {
                "initial_input": {
                    "keywords": getattr(context, 'initial_keywords', []),
                    "persona_type": context.persona_type.value if hasattr(context, 'persona_type') and context.persona_type else None,
                    "target_age_group": context.target_age_group.value if hasattr(context, 'target_age_group') and context.target_age_group else None,
                    "custom_persona": getattr(context, 'custom_persona', "")
                },
                "seo_keywords": getattr(context, 'initial_keywords', []),
                "image_mode_enabled": getattr(context, 'image_mode', False),
                "article_style_info": getattr(context, 'style_template_settings', {}),
                "generation_theme_count": getattr(context, 'num_theme_proposals', 3),
                "target_age_group": context.target_age_group.value if hasattr(context, 'target_age_group') and context.target_age_group else None,
                "persona_settings": {
                    "persona_type": context.persona_type.value if hasattr(context, 'persona_type') and context.persona_type else None,
                    "custom_persona": getattr(context, 'custom_persona', ""),
                    "num_persona_examples": getattr(context, 'num_persona_examples', 3)
                },
                "company_info": {
                    "company_name": getattr(context, 'company_name', ""),
                    "company_description": getattr(context, 'company_description', ""),
                    "company_style_guide": getattr(context, 'company_style_guide', "")
                },
                "target_length": getattr(context, 'target_length', None),
                "num_research_queries": getattr(context, 'num_research_queries', 5),
                "current_step": context.current_step
            }
            
            workflow_logger = MultiAgentWorkflowLogger(
                article_uuid=process_id,
                user_id=user_id or getattr(context, 'user_id', 'unknown'),
                organization_id=getattr(context, 'organization_id', None),
                initial_config=initial_config
            )
            
            # 既存のログセッションを検索
            from app.common.database import supabase
            existing_session = supabase.table("agent_log_sessions").select("id").eq("article_uuid", process_id).execute()
            
            if existing_session.data:
                # 既存セッションを復元
                workflow_logger.session_id = existing_session.data[0]["id"]
                
                # 既存のワークフローステップ数に基づいてcurrent_stepを設定
                steps_count = supabase.table("workflow_step_logs").select("step_order").eq("session_id", workflow_logger.session_id).execute()
                if steps_count.data:
                    workflow_logger.current_step = len(steps_count.data) + 1
                else:
                    workflow_logger.current_step = 1
                    
                console.print(f"[cyan]✅ Restored log session {workflow_logger.session_id} for process {process_id} (step: {workflow_logger.current_step})[/cyan]")
            else:
                # 新しいログセッションを作成
                log_session_id = workflow_logger.initialize_session()
                console.print(f"[cyan]✅ Created new log session {log_session_id} for process {process_id}[/cyan]")
            
            # ワークフローロガーを保存
            self.workflow_loggers[process_id] = workflow_logger
            console.print(f"[green]✅ Workflow logger stored for process {process_id}[/green]")
            console.print(f"[debug]Workflow logger details: session_id={workflow_logger.session_id}, current_step={workflow_logger.current_step}, logging_service={workflow_logger.logging_service is not None}[/debug]")
            
        except Exception as e:
            logger.error(f"Failed to ensure workflow logger for process {process_id}: {e}")
            console.print(f"[red]❌ Failed to create workflow logger: {e}[/red]")
            import traceback
            console.print(f"[red]Traceback: {traceback.format_exc()}[/red]")

    async def _save_context_to_db(self, context: ArticleContext, process_id: Optional[str] = None, user_id: Optional[str] = None, organization_id: Optional[str] = None) -> str:
        """Save ArticleContext to database and return process_id"""
        try:
            from app.domains.seo_article.services.flow_service import get_supabase_client
            from datetime import datetime, timezone
            import json
            supabase = get_supabase_client()
            
            def safe_serialize_value(value):
                """Recursively serialize any object to JSON-serializable format"""
                if value is None:
                    return None
                elif isinstance(value, (str, int, float, bool)):
                    return value
                elif isinstance(value, list):
                    return [safe_serialize_value(item) for item in value]
                elif isinstance(value, dict):
                    return {k: safe_serialize_value(v) for k, v in value.items()}
                elif hasattr(value, "model_dump"):
                    # Pydantic models
                    return value.model_dump()
                elif hasattr(value, "__dict__"):
                    # Regular objects with attributes
                    return {k: safe_serialize_value(v) for k, v in value.__dict__.items()}
                else:
                    # Fallback to string representation
                    return str(value)
            
            # Convert context to dict (excluding WebSocket and asyncio objects)
            context_dict = {}
            for key, value in context.__dict__.items():
                if key not in ["websocket", "user_response_event"]:
                    try:
                        context_dict[key] = safe_serialize_value(value)
                        # デバッグ: image_mode の値をログ出力
                        if key == "image_mode":
                            console.print(f"[cyan]DEBUG: Saving image_mode = {value} (type: {type(value)})[/cyan]")
                    except Exception as e:
                        console.print(f"[yellow]Warning: Failed to serialize {key}: {e}. Using string representation.[/yellow]")
                        context_dict[key] = str(value)
            
            # Verify JSON serialization works
            try:
                json.dumps(context_dict)
            except Exception as e:
                console.print(f"[red]Error: Context still not JSON serializable after processing: {e}[/red]")
                raise e
            
            # Map current_step to valid generation_status enum values
            def map_step_to_status(step: str) -> str:
                """Map context step to valid generation_status enum value"""
                if step in ["start", "keyword_analyzing", "keyword_analyzed", "persona_generating", 
                           "persona_selected", "theme_generating", "theme_selected", "research_planning", 
                           "research_plan_approved", "researching", "research_synthesizing", 
                           "outline_generating", "writing_sections", "editing"]:
                    return "in_progress"
                elif step == "completed":
                    return "completed"
                elif step == "error":
                    return "error"
                elif step in ["persona_generated", "theme_proposed", "research_plan_generated", 
                             "outline_generated"]:
                    return "user_input_required"
                else:
                    return "in_progress"  # Default fallback
            
            if process_id:
                # Update existing state
                update_data = {
                    "article_context": context_dict,
                    "status": map_step_to_status(context.current_step),
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
                
                # Add error message if in error state
                if context.current_step == "error" and hasattr(context, 'error_message'):
                    update_data["error_message"] = context.error_message
                    
                # Add final article if completed
                if context.current_step == "completed" and hasattr(context, 'final_article_html'):
                    article_data = {
                        "user_id": user_id,
                        "organization_id": organization_id,
                        "generation_process_id": process_id,
                        "title": context.generated_outline.title if context.generated_outline else "Generated Article",
                        "content": context.final_article_html,
                        "keywords": context.initial_keywords,
                        "target_audience": context.selected_detailed_persona,
                        "status": "completed"
                    }
                    
                    try:
                        # 手動でのチェック・挿入・更新（UPSERT制約に依存しない）
                        console.print(f"[cyan]Saving final article for process {process_id}[/cyan]")
                        
                        # 既存記事をチェック
                        existing_article = supabase.table("articles").select("id").eq("generation_process_id", process_id).execute()
                        
                        if existing_article.data and len(existing_article.data) > 0:
                            # 既存記事を更新
                            article_id = existing_article.data[0]["id"]
                            console.print(f"[yellow]Updating existing article {article_id}[/yellow]")
                            article_result = supabase.table("articles").update(article_data).eq("id", article_id).execute()
                            
                            if article_result.data:
                                update_data["article_id"] = article_id
                                console.print(f"[green]Successfully updated article {article_id} for process {process_id}[/green]")
                            else:
                                console.print(f"[red]Failed to update article {article_id}: {article_result}[/red]")
                        else:
                            # 新規記事を作成
                            console.print(f"[yellow]Creating new article for process {process_id}[/yellow]")
                            article_result = supabase.table("articles").insert(article_data).execute()
                            
                            if article_result.data:
                                article_id = article_result.data[0]["id"]
                                update_data["article_id"] = article_id
                                console.print(f"[green]Successfully created article {article_id} for process {process_id}[/green]")
                            else:
                                console.print(f"[red]Failed to create article: {article_result}[/red]")
                            
                    except Exception as article_save_error:
                        console.print(f"[red]Error saving article for process {process_id}: {article_save_error}[/red]")
                        # 最後の試み: 強制的に挿入
                        try:
                            console.print(f"[yellow]Attempting force insert for process {process_id}[/yellow]")
                            article_result = supabase.table("articles").insert(article_data).execute()
                            if article_result.data:
                                article_id = article_result.data[0]["id"]
                                update_data["article_id"] = article_id
                                console.print(f"[green]Force insert successful: {article_id}[/green]")
                        except Exception as fallback_error:
                            console.print(f"[red]Fallback article save also failed: {fallback_error}[/red]")
                
                supabase.table("generated_articles_state").update(update_data).eq("id", process_id).execute()
                return process_id
            else:
                # Get default flow ID for new states
                flow_result = supabase.table("article_generation_flows").select("id").eq("name", "Default SEO Article Generation").eq("is_template", True).execute()
                
                if not flow_result.data:
                    raise Exception("Default flow template not found")
                
                default_flow_id = flow_result.data[0]["id"]
                
                # Create new state
                state_data = {
                    "flow_id": default_flow_id,
                    "user_id": user_id,
                    "organization_id": organization_id,
                    "status": map_step_to_status(context.current_step),
                    "article_context": context_dict,
                    "generated_content": {}
                }
                
                result = supabase.table("generated_articles_state").insert(state_data).execute()
                if result.data:
                    return result.data[0]["id"]
                else:
                    raise Exception("Failed to create generation state")
            
        except Exception as e:
            logger.error(f"Error saving context to database: {e}")
            raise

    async def get_generation_process_state(self, process_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Get generation process state from database"""
        try:
            from app.domains.seo_article.services.flow_service import get_supabase_client
            supabase = get_supabase_client()
            
            # Get the process state with user access control
            result = supabase.table("generated_articles_state").select("*").eq("id", process_id).eq("user_id", user_id).execute()
            
            if not result.data:
                logger.warning(f"Process {process_id} not found for user {user_id}")
                return None
            
            state = result.data[0]
            context_dict = state.get("article_context", {})
            
            # デバッグ: image_mode の値をログ出力 (get_generation_process_state)
            console.print(f"[magenta]DEBUG (get_generation_process_state): image_mode from DB = {context_dict.get('image_mode')} (type: {type(context_dict.get('image_mode'))})[/magenta]")
            
            # Return a formatted response that matches frontend expectations
            return {
                "id": state["id"],
                "flow_id": state.get("flow_id"),
                "user_id": state["user_id"],
                "organization_id": state.get("organization_id"),
                "current_step_id": state.get("current_step_id"),
                "current_step_name": context_dict.get("current_step", "start"),
                "status": state.get("status", "in_progress"),
                "article_context": context_dict,
                "generated_content": state.get("generated_content", {}),
                "article_id": state.get("article_id"),
                "error_message": state.get("error_message"),
                "is_waiting_for_input": context_dict.get("current_step") in ["persona_generated", "theme_proposed", "research_plan_generated", "outline_generated"],
                "input_type": self._get_input_type_for_step(context_dict.get("current_step")),
                # 画像モード関連情報を含める
                "image_mode": context_dict.get("image_mode", False),
                "image_settings": context_dict.get("image_settings", {}),
                "image_placeholders": context_dict.get("image_placeholders", []),
                "created_at": state.get("created_at"),
                "updated_at": state.get("updated_at")
            }
            
        except Exception as e:
            logger.error(f"Error getting generation process state: {e}")
            raise

    def _get_input_type_for_step(self, step: str) -> Optional[str]:
        """Get expected input type for a given step"""
        step_input_map = {
            "persona_generated": "select_persona",
            "theme_proposed": "select_theme", 
            "research_plan_generated": "approve_plan",
            "outline_generated": "approve_outline"
        }
        return step_input_map.get(step)

    async def _load_context_from_db(self, process_id: str, user_id: str) -> Optional[ArticleContext]:
        """Load context from database for process persistence"""
        try:
            from app.domains.seo_article.services.flow_service import get_supabase_client
            from app.domains.seo_article.schemas import AgeGroup, PersonaType
            supabase = get_supabase_client()
            
            # Get the process state with user access control
            result = supabase.table("generated_articles_state").select("*").eq("id", process_id).eq("user_id", user_id).execute()
            
            if not result.data:
                logger.warning(f"Process {process_id} not found for user {user_id}")
                return None
            
            state = result.data[0]
            context_dict = state.get("article_context", {})
            
            # デバッグ: image_mode の値をログ出力
            console.print(f"[cyan]DEBUG: Loading image_mode from DB = {context_dict.get('image_mode')} (type: {type(context_dict.get('image_mode'))})[/cyan]")
            console.print(f"[cyan]DEBUG: Full context_dict keys = {list(context_dict.keys())}[/cyan]")
            
            if not context_dict:
                logger.warning(f"No context data found for process {process_id}")
                return None
            
            # Helper function to safely convert string to enum
            def safe_convert_enum(value, enum_class):
                if value is None:
                    return None
                try:
                    if isinstance(value, str):
                        # Try to find enum by value
                        for enum_item in enum_class:
                            if enum_item.value == value:
                                return enum_item
                        # If not found, try direct conversion
                        return enum_class(value)
                    return value  # Already an enum or valid type
                except (ValueError, TypeError) as e:
                    logger.warning(f"Failed to convert {value} to {enum_class.__name__}: {e}")
                    return None
            
            # Convert enum fields back from strings
            target_age_group = safe_convert_enum(context_dict.get("target_age_group"), AgeGroup)
            persona_type = safe_convert_enum(context_dict.get("persona_type"), PersonaType)
            
            # Reconstruct ArticleContext from stored data
            context = ArticleContext(
                initial_keywords=context_dict.get("initial_keywords", []),
                target_age_group=target_age_group,
                persona_type=persona_type,
                custom_persona=context_dict.get("custom_persona"),
                target_length=context_dict.get("target_length"),
                num_theme_proposals=context_dict.get("num_theme_proposals", 3),
                num_research_queries=context_dict.get("num_research_queries", 3),
                num_persona_examples=context_dict.get("num_persona_examples", 3),
                company_name=context_dict.get("company_name"),
                company_description=context_dict.get("company_description"),
                company_style_guide=context_dict.get("company_style_guide"),
                # 画像モード関連の復元
                image_mode=context_dict.get("image_mode", False),
                image_settings=context_dict.get("image_settings", {}),
                # スタイルテンプレート関連の復元
                style_template_id=context_dict.get("style_template_id"),
                style_template_settings=context_dict.get("style_template_settings", {}),
                websocket=None,  # Will be set when WebSocket connects
                user_response_event=None,  # Will be set when WebSocket connects
                user_id=user_id  # Set user_id from method parameter
            )
            
            # Restore other context state
            context.current_step = context_dict.get("current_step", "start")
            context.generated_detailed_personas = context_dict.get("generated_detailed_personas", [])
            context.selected_detailed_persona = context_dict.get("selected_detailed_persona")
            
            # Restore complex objects with error handling
            try:
                if context_dict.get("selected_theme"):
                    from app.domains.seo_article.schemas import ThemeIdea
                    context.selected_theme = ThemeIdea(**context_dict["selected_theme"])
                
                if context_dict.get("generated_themes"):
                    from app.domains.seo_article.schemas import ThemeIdea
                    context.generated_themes = [ThemeIdea(**theme_data) for theme_data in context_dict["generated_themes"]]
                    
                if context_dict.get("research_plan"):
                    from app.domains.seo_article.schemas import ResearchPlan
                    context.research_plan = ResearchPlan(**context_dict["research_plan"])
                    
                if context_dict.get("research_report"):
                    from app.domains.seo_article.schemas import ResearchReport
                    context.research_report = ResearchReport(**context_dict["research_report"])
                    
                if context_dict.get("generated_outline"):
                    from app.domains.seo_article.schemas import Outline
                    context.generated_outline = Outline(**context_dict["generated_outline"])
                    
                if context_dict.get("serp_analysis_report"):
                    from app.domains.seo_article.schemas import SerpKeywordAnalysisReport
                    context.serp_analysis_report = SerpKeywordAnalysisReport(**context_dict["serp_analysis_report"])
                    
            except Exception as e:
                logger.warning(f"Error restoring complex objects for process {process_id}: {e}")
            
            # Restore other state
            context.research_query_results = context_dict.get("research_query_results", [])
            context.current_research_query_index = context_dict.get("current_research_query_index", 0)
            context.generated_sections_html = context_dict.get("generated_sections_html", [])
            context.current_section_index = context_dict.get("current_section_index", 0)
            context.full_draft_html = context_dict.get("full_draft_html")
            context.final_article_html = context_dict.get("final_article_html")
            context.section_writer_history = context_dict.get("section_writer_history", [])
            context.expected_user_input = context_dict.get("expected_user_input")
            
            logger.info(f"Successfully loaded context for process {process_id} from step {context.current_step}")
            return context
            
        except Exception as e:
            logger.error(f"Error loading context from database for process {process_id}: {e}")
            return None

    async def get_user_articles(
        self, 
        user_id: str, 
        status_filter: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get articles for a specific user.
        
        Args:
            user_id: User ID to filter articles
            status_filter: Optional status filter ('completed', 'in_progress', etc.)
            limit: Maximum number of articles to return
            offset: Number of articles to skip for pagination
            
        Returns:
            List of article dictionaries with basic information
        """
        try:
            from app.domains.seo_article.services.flow_service import get_supabase_client
            supabase = get_supabase_client()
            
            # Query for articles created by the user
            query = supabase.table("articles").select(
                "id, title, content, keywords, target_audience, status, created_at, updated_at"
            ).eq("user_id", user_id)
            
            # Apply status filter if provided
            if status_filter:
                query = query.eq("status", status_filter)
            
            # Apply pagination
            query = query.order("created_at", desc=True).range(offset, offset + limit - 1)
            
            result = query.execute()
            
            articles = []
            for article in result.data:
                # Extract short description from content (first 150 characters)
                content = article.get("content", "")
                # Strip HTML tags for short description
                import re
                plain_text = re.sub(r'<[^>]+>', '', content)
                short_description = plain_text[:150] + "..." if len(plain_text) > 150 else plain_text
                
                articles.append({
                    "id": article["id"],
                    "title": article["title"],
                    "shortdescription": short_description,
                    "postdate": article["created_at"].split("T")[0] if article["created_at"] else None,
                    "status": article["status"],
                    "keywords": article.get("keywords", []),
                    "target_audience": article.get("target_audience"),
                    "updated_at": article["updated_at"]
                })
            
            return articles
            
        except Exception as e:
            logger.error(f"Error retrieving articles for user {user_id}: {e}")
            raise
    
    async def get_article(self, article_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed article information by ID.
        
        Args:
            article_id: Article ID
            user_id: User ID for access control
            
        Returns:
            Article dictionary with detailed information or None if not found
        """
        try:
            from app.domains.seo_article.services.flow_service import get_supabase_client
            supabase = get_supabase_client()
            
            # Query for article with user access control
            result = supabase.table("articles").select("*").eq("id", article_id).eq("user_id", user_id).execute()
            
            # If no direct match, check if this might be a generation_process_id
            if not result.data:
                # Try to find by generation_process_id (in case user is using wrong ID)
                process_result = supabase.table("articles").select("*").eq("generation_process_id", article_id).eq("user_id", user_id).order("updated_at", desc=True).execute()
                if process_result.data:
                    result = process_result
            
            if not result.data:
                return None
            
            # If multiple articles exist for the same generation_process_id (shouldn't happen with constraint),
            # select the one with the most content
            articles = result.data
            if len(articles) > 1:
                logger.warning(f"Multiple articles found for ID {article_id}, selecting the most complete one")
                articles.sort(key=lambda x: (len(x.get("content", "")), x.get("updated_at", "")), reverse=True)
            
            article = articles[0]
            
            # Extract short description from content
            content = article.get("content", "")
            import re
            plain_text = re.sub(r'<[^>]+>', '', content)
            short_description = plain_text[:300] + "..." if len(plain_text) > 300 else plain_text
            
            return {
                "id": article["id"],
                "title": article["title"],
                "content": article["content"],
                "shortdescription": short_description,
                "postdate": article["created_at"].split("T")[0] if article["created_at"] else None,
                "status": article["status"],
                "keywords": article.get("keywords", []),
                "target_audience": article.get("target_audience"),
                "created_at": article["created_at"],
                "updated_at": article["updated_at"],
                "generation_process_id": article.get("generation_process_id")
            }
            
        except Exception as e:
            logger.error(f"Error retrieving article {article_id}: {e}")
            raise

    async def get_all_user_processes(
        self, 
        user_id: str, 
        status_filter: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get all processes (completed articles + in-progress/failed generation processes) for a user.
        
        Args:
            user_id: User ID to filter processes
            status_filter: Optional status filter ('completed', 'in_progress', 'error', etc.)
            limit: Maximum number of items to return
            offset: Number of items to skip for pagination
            
        Returns:
            List of unified process dictionaries (articles + generation processes)
        """
        try:
            from app.domains.seo_article.services.flow_service import get_supabase_client
            import re
            supabase = get_supabase_client()
            
            all_processes = []
            
            # 1. Get completed articles
            articles_query = supabase.table("articles").select(
                "id, title, content, keywords, target_audience, status, created_at, updated_at, generation_process_id"
            ).eq("user_id", user_id)
            
            if status_filter and status_filter == "completed":
                articles_query = articles_query.eq("status", "completed")
            
            articles_result = articles_query.order("created_at", desc=True).execute()
            
            for article in articles_result.data:
                # Extract short description from content
                content = article.get("content", "")
                plain_text = re.sub(r'<[^>]+>', '', content)
                short_description = plain_text[:150] + "..." if len(plain_text) > 150 else plain_text
                
                all_processes.append({
                    "id": article["id"],
                    "process_id": article.get("generation_process_id"),
                    "title": article["title"],
                    "shortdescription": short_description,
                    "postdate": article["created_at"].split("T")[0] if article["created_at"] else None,
                    "status": "completed",  # Articles are always completed
                    "process_type": "article",
                    "keywords": article.get("keywords", []),
                    "target_audience": article.get("target_audience"),
                    "updated_at": article["updated_at"],
                    "can_resume": False,
                    "is_recoverable": False
                })
            
            # Collect generation_process_ids from articles to avoid duplication
            existing_process_ids = set()
            for article in articles_result.data:
                if article.get("generation_process_id"):
                    existing_process_ids.add(article["generation_process_id"])

            # 2. Get generation processes (including incomplete ones)
            processes_query = supabase.table("generated_articles_state").select(
                "id, status, article_context, current_step_name, progress_percentage, is_waiting_for_input, created_at, updated_at, error_message"
            ).eq("user_id", user_id)
            
            # Only get non-completed processes (since completed ones have articles)
            # Also exclude processes that already have corresponding articles
            processes_query = processes_query.neq("status", "completed")
            
            if status_filter and status_filter != "completed":
                processes_query = processes_query.eq("status", status_filter)
            
            processes_result = processes_query.order("updated_at", desc=True).execute()
            
            for process in processes_result.data:
                # Skip processes that already have corresponding articles
                if process["id"] in existing_process_ids:
                    continue
                    
                # Skip completed processes (they should have articles)
                if process["status"] == "completed":
                    continue
                context = process.get("article_context", {})
                keywords = context.get("initial_keywords", [])
                
                # Generate title from keywords or step
                if keywords:
                    title = f"SEO記事: {', '.join(keywords[:3])}"
                else:
                    title = f"記事生成プロセス (ID: {process['id'][:8]}...)"
                
                # Generate description based on current step
                current_step = process.get("current_step_name", "start")
                step_descriptions = {
                    "start": "生成開始",
                    "keyword_analyzing": "キーワード分析中",
                    "persona_generating": "ペルソナ生成中",
                    "theme_generating": "テーマ生成中",
                    "theme_proposed": "テーマ選択待ち",
                    "research_planning": "リサーチ計画策定中",
                    "research_plan_generated": "リサーチ計画承認待ち",
                    "researching": "リサーチ実行中",
                    "outline_generating": "アウトライン生成中",
                    "outline_generated": "アウトライン承認待ち",
                    "writing_sections": "記事執筆中",
                    "editing": "編集中",
                    "error": "エラーが発生しました"
                }
                description = step_descriptions.get(current_step, f"ステップ: {current_step}")
                
                # Determine if process is recoverable
                is_recoverable = process["status"] in ["user_input_required", "paused", "error"]
                can_resume = is_recoverable and process.get("is_waiting_for_input", False)
                
                all_processes.append({
                    "id": process["id"],
                    "process_id": process["id"],
                    "title": title,
                    "shortdescription": description,
                    "postdate": process["created_at"].split("T")[0] if process["created_at"] else None,
                    "status": process["status"],
                    "process_type": "generation",
                    "keywords": keywords,
                    "target_audience": context.get("custom_persona") or context.get("persona_type"),
                    "updated_at": process["updated_at"],
                    "current_step": current_step,
                    "progress_percentage": process.get("progress_percentage", 0),
                    "can_resume": can_resume,
                    "is_recoverable": is_recoverable,
                    "error_message": process.get("error_message")
                })
            
            # 3. Sort all processes by updated_at (most recent first)
            all_processes.sort(key=lambda x: x["updated_at"] or "", reverse=True)
            
            # 4. Apply pagination
            paginated_processes = all_processes[offset:offset + limit]
            
            return paginated_processes
            
        except Exception as e:
            logger.error(f"Error retrieving all processes for user {user_id}: {e}")
            raise

    async def get_recoverable_processes(self, user_id: str, limit: int = 10) -> List[dict]:
        """
        Get processes that can be recovered/resumed for a user.
        
        Args:
            user_id: User ID to filter processes
            limit: Maximum number of recoverable processes to return
            
        Returns:
            List of recoverable process dictionaries with recovery metadata
        """
        try:
            from app.domains.seo_article.services.flow_service import get_supabase_client
            from datetime import datetime, timezone
            supabase = get_supabase_client()
            
            # Define recoverable statuses
            recoverable_statuses = ['user_input_required', 'paused', 'error', 'resuming', 'auto_progressing']
            
            # Query for recoverable processes
            query = supabase.table("generated_articles_state").select(
                "id, status, article_context, current_step_name, progress_percentage, "
                "is_waiting_for_input, created_at, updated_at, error_message, last_activity_at"
            ).eq("user_id", user_id).in_("status", recoverable_statuses)
            
            result = query.order("updated_at", desc=True).limit(limit).execute()
            
            recoverable_processes = []
            current_time = datetime.now(timezone.utc)
            
            for process in result.data:
                context = process.get("article_context", {})
                keywords = context.get("initial_keywords", [])
                current_step = process.get("current_step_name", "start")
                status = process["status"]
                updated_at = process.get("updated_at")
                
                # Calculate time since last activity
                time_since_activity = None
                if updated_at:
                    try:
                        last_activity = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
                        time_since_activity = int((current_time - last_activity).total_seconds())
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Error parsing updated_at for process {process['id']}: {e}")
                        time_since_activity = None
                
                # Determine recovery metadata
                recovery_metadata = self._get_recovery_metadata(status, current_step, process)
                
                # Generate title from keywords or context
                if keywords:
                    title = f"SEO記事: {', '.join(keywords[:3])}"
                elif context.get("title"):
                    title = context["title"]
                else:
                    title = f"記事生成プロセス (ID: {process['id'][:8]}...)"
                
                # Get step description
                step_descriptions = {
                    "start": "生成開始",
                    "keyword_analyzing": "キーワード分析中",
                    "persona_generating": "ペルソナ生成中",
                    "theme_generating": "テーマ生成中",
                    "theme_proposed": "テーマ選択待ち",
                    "research_planning": "リサーチ計画策定中",
                    "research_plan_generated": "リサーチ計画承認待ち",
                    "researching": "リサーチ実行中",
                    "outline_generating": "アウトライン生成中",
                    "outline_generated": "アウトライン承認待ち",
                    "writing_sections": "記事執筆中",
                    "editing": "編集中",
                    "error": "エラーが発生しました"
                }
                description = step_descriptions.get(current_step, f"ステップ: {current_step}")
                
                process_data = {
                    "id": process["id"],
                    "process_id": process["id"],
                    "title": title,
                    "description": description,
                    "status": status,
                    "current_step": current_step,
                    "progress_percentage": process.get("progress_percentage", 0),
                    "keywords": keywords,
                    "target_audience": context.get("custom_persona") or context.get("persona_type"),
                    "created_at": process["created_at"],
                    "updated_at": updated_at,
                    "time_since_last_activity": time_since_activity,
                    "error_message": process.get("error_message"),
                    
                    # Recovery metadata
                    "resume_step": recovery_metadata["resume_step"],
                    "auto_resume_possible": recovery_metadata["auto_resume_possible"],
                    "recovery_notes": recovery_metadata["recovery_notes"],
                    "requires_user_input": recovery_metadata["requires_user_input"]
                }
                
                recoverable_processes.append(process_data)
            
            return recoverable_processes
            
        except Exception as e:
            logger.error(f"Error retrieving recoverable processes for user {user_id}: {e}")
            raise
    
    def _get_recovery_metadata(self, status: str, current_step: str, process: dict) -> dict:
        """
        Generate recovery metadata for a process based on its current state.
        
        Args:
            status: Current process status
            current_step: Current step name
            process: Full process data
            
        Returns:
            Dictionary containing recovery metadata
        """
        metadata = {
            "resume_step": current_step,
            "auto_resume_possible": False,
            "recovery_notes": "",
            "requires_user_input": False
        }
        
        try:
            if status == "paused":
                # Paused processes can usually auto-resume from current step
                metadata["auto_resume_possible"] = True
                metadata["recovery_notes"] = "一時停止中です。自動復旧可能です。"
                
            elif status == "user_input_required":
                # User input required - cannot auto-resume
                metadata["auto_resume_possible"] = False
                metadata["requires_user_input"] = True
                
                # Determine what type of input is needed based on current step
                if current_step == "theme_proposed":
                    metadata["recovery_notes"] = "テーマの選択が必要です。"
                elif current_step == "research_plan_generated":
                    metadata["recovery_notes"] = "リサーチ計画の承認が必要です。"
                elif current_step == "outline_generated":
                    metadata["recovery_notes"] = "アウトラインの承認が必要です。"
                else:
                    metadata["recovery_notes"] = "ユーザーの入力が必要です。"
                    
            elif status == "in_progress":
                # In-progress processes might be resumable depending on step
                if current_step in ["researching", "writing_sections", "editing"]:
                    metadata["auto_resume_possible"] = True
                    metadata["recovery_notes"] = "処理が中断されました。自動復旧可能です。"
                else:
                    metadata["auto_resume_possible"] = False
                    metadata["recovery_notes"] = "処理が中断されました。手動での確認が必要です。"
                    
            elif status == "error":
                # Error processes need manual intervention
                metadata["auto_resume_possible"] = False
                error_message = process.get("error_message", "")
                
                # Try to provide more specific recovery guidance based on error
                if "connection" in error_message.lower():
                    metadata["recovery_notes"] = "接続エラーが発生しました。再試行可能です。"
                    metadata["auto_resume_possible"] = True
                elif "timeout" in error_message.lower():
                    metadata["recovery_notes"] = "タイムアウトエラーが発生しました。再試行可能です。"
                    metadata["auto_resume_possible"] = True
                elif "authentication" in error_message.lower():
                    metadata["recovery_notes"] = "認証エラーが発生しました。設定を確認してください。"
                elif "quota" in error_message.lower() or "limit" in error_message.lower():
                    metadata["recovery_notes"] = "API制限に達しました。時間をおいて再試行してください。"
                else:
                    metadata["recovery_notes"] = f"エラーが発生しました: {error_message[:100]}..."
            
            return metadata
            
        except Exception as e:
            logger.warning(f"Error generating recovery metadata: {e}")
            metadata["recovery_notes"] = "復旧情報の取得中にエラーが発生しました。"
            return metadata

    async def update_article(
        self, 
        article_id: str, 
        user_id: str, 
        update_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        記事を更新します。
        
        Args:
            article_id: 記事ID
            user_id: ユーザーID（アクセス制御用）
            update_data: 更新するデータの辞書
            
        Returns:
            更新された記事の情報
        """
        try:
            from app.domains.seo_article.services.flow_service import get_supabase_client
            from datetime import datetime, timezone
            supabase = get_supabase_client()
            
            # まず記事が存在し、ユーザーがアクセス権限を持つことを確認
            existing_result = supabase.table("articles").select("*").eq("id", article_id).eq("user_id", user_id).execute()
            
            if not existing_result.data:
                raise ValueError("Article not found or access denied")
            
            # 更新データを準備
            update_fields = {}
            allowed_fields = ["title", "content", "shortdescription", "target_audience", "keywords"]
            
            for field, value in update_data.items():
                if field in allowed_fields and value is not None:
                    update_fields[field] = value
            
            # 更新時刻を追加
            update_fields["updated_at"] = datetime.now(timezone.utc).isoformat()
            
            # 更新が必要なフィールドがない場合
            if not update_fields:
                return await self.get_article(article_id, user_id)
            
            # **重要**: コンテンツの更新で空のimgタグを上書きしないようにチェック
            if "content" in update_fields:
                new_content = update_fields["content"]
                # 空のimgタグを含むコンテンツのチェック
                if "<img />" in new_content or "<img/>" in new_content:
                    existing_article = existing_result.data[0]
                    existing_content = existing_article.get("content", "")
                    
                    # 既存のコンテンツの方が充実している場合は更新しない
                    if len(existing_content) > len(new_content) and "data-image-id" in existing_content:
                        logger.warning(f"Preventing content update with empty img tags for article {article_id}. Existing content is more complete.")
                        del update_fields["content"]
                        
                        # コンテント以外のフィールドだけ更新
                        if len(update_fields) == 1:  # updated_atだけ残っている場合
                            return await self.get_article(article_id, user_id)
            
            # データベースを更新
            logger.info(f"Updating article {article_id} with fields: {list(update_fields.keys())}")
            result = supabase.table("articles").update(update_fields).eq("id", article_id).eq("user_id", user_id).execute()
            
            if not result.data:
                raise Exception(f"Failed to update article {article_id} - no rows affected")
            
            # コンテンツが更新された場合、画像プレースホルダーを抽出・保存
            if "content" in update_fields:
                try:
                    await self._extract_and_save_placeholders(supabase, article_id, update_fields["content"])
                    logger.info(f"Successfully extracted and saved placeholders for article {article_id}")
                except Exception as e:
                    logger.warning(f"Failed to extract image placeholders for article {article_id}: {e}")
            
            # 更新された記事情報を返す
            return await self.get_article(article_id, user_id)
            
        except Exception as e:
            logger.error(f"Error updating article {article_id}: {e}")
            raise

    async def _extract_and_save_placeholders(self, supabase, article_id: str, content: str) -> None:
        """
        記事内容から画像プレースホルダーを抽出してデータベースに保存する
        
        Args:
            supabase: Supabaseクライアント
            article_id: 記事ID
            content: 記事内容（HTML）
        """
        import re
        
        try:
            # 画像プレースホルダーのパターン: <!-- IMAGE_PLACEHOLDER: id|description_jp|prompt_en -->
            pattern = r'<!-- IMAGE_PLACEHOLDER: ([^|]+)\|([^|]+)\|([^>]+) -->'
            matches = re.findall(pattern, content)
            
            if not matches:
                logger.info(f"No image placeholders found in article {article_id}")
                return
            
            logger.info(f"Found {len(matches)} image placeholders in article {article_id}")
            
            # 各プレースホルダーをデータベースに保存
            for index, (placeholder_id, description_jp, prompt_en) in enumerate(matches):
                placeholder_data = {
                    "article_id": article_id,
                    "placeholder_id": placeholder_id.strip(),
                    "description_jp": description_jp.strip(),
                    "prompt_en": prompt_en.strip(),
                    "position_index": index + 1,
                    "status": "pending"
                }
                
                try:
                    # ON CONFLICT DO UPDATEでupsert
                    result = supabase.table("image_placeholders").upsert(
                        placeholder_data,
                        on_conflict="article_id,placeholder_id"
                    ).execute()
                    
                    if result.data:
                        logger.info(f"Saved placeholder {placeholder_id} for article {article_id}")
                    else:
                        logger.warning(f"Failed to save placeholder {placeholder_id}: {result}")
                        
                except Exception as placeholder_error:
                    logger.error(f"Error saving placeholder {placeholder_id} for article {article_id}: {placeholder_error}")
                    # 個別のプレースホルダーエラーは継続可能
                    continue
            
        except Exception as e:
            logger.error(f"Error extracting placeholders for article {article_id}: {e}")
            raise


    async def _update_process_status(self, process_id: str, status: str, current_step: str = None, metadata: dict = None) -> None:
        """Update process status in database"""
        try:
            from app.domains.seo_article.services.flow_service import get_supabase_client
            from datetime import datetime, timezone
            supabase = get_supabase_client()
            
            update_data = {
                "status": status,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
            
            if current_step:
                update_data["current_step_name"] = current_step
            
            if metadata:
                update_data["process_metadata"] = metadata
            
            result = supabase.table("generated_articles_state").update(update_data).eq("id", process_id).execute()
            
            if result.data:
                logger.info(f"Successfully updated process {process_id} status to {status}")
                
                # Add status update to history
                await self._add_step_to_history(
                    process_id=process_id,
                    step_name="status_update",
                    status=status,
                    data={"old_status": result.data[0].get("status"), "new_status": status}
                )
            else:
                logger.warning(f"No data returned when updating status for process {process_id}")
                
        except Exception as e:
            logger.error(f"Error updating process status for {process_id}: {e}")
            raise

    async def _add_step_to_history(self, process_id: str, step_name: str, status: str, data: dict = None) -> None:
        """Add step to history using database function for process tracking"""
        try:
            from app.domains.seo_article.services.flow_service import get_supabase_client
            supabase = get_supabase_client()
            
            # Safe serialization function for history data
            def safe_serialize_history_data(value):
                """Safely serialize data for JSON storage"""
                if value is None:
                    return None
                elif isinstance(value, (str, int, float, bool)):
                    return value
                elif isinstance(value, list):
                    return [safe_serialize_history_data(item) for item in value]
                elif isinstance(value, dict):
                    return {k: safe_serialize_history_data(v) for k, v in value.items()}
                elif hasattr(value, "model_dump"):
                    return value.model_dump()
                elif hasattr(value, "__dict__"):
                    return {k: safe_serialize_history_data(v) for k, v in value.__dict__.items()}
                else:
                    return str(value)
            
            # Safely serialize the data parameter
            safe_data = safe_serialize_history_data(data or {})
            
            # Use the database function instead of direct table insert
            supabase.rpc('add_step_to_history', {
                'process_id': process_id,
                'step_name': step_name,
                'step_status': status,
                'step_data': safe_data
            }).execute()
            
            logger.debug(f"Added step {step_name} to history for process {process_id}")
                
        except Exception as e:
            logger.warning(f"Could not add step to history for process {process_id}: {e}")
            # Don't raise here as this is a non-critical operation
            pass

    async def _save_image_placeholders_to_db(self, context: ArticleContext, image_placeholders: list, section_index: int):
        """
        画像プレースホルダー情報をデータベースに保存
        """
        try:
            from app.core.config import get_supabase_client
            supabase = get_supabase_client()
            from datetime import datetime, timezone
            
            # 記事IDを取得（完成した記事から、または生成プロセスIDから推測）
            article_id = getattr(context, 'final_article_id', None)
            generation_process_id = getattr(context, 'process_id', None)
            
            for i, placeholder in enumerate(image_placeholders):
                try:
                    placeholder_data = {
                        "article_id": article_id,
                        "generation_process_id": generation_process_id,
                        "placeholder_id": placeholder.placeholder_id,
                        "description_jp": placeholder.description_jp,
                        "prompt_en": placeholder.prompt_en,
                        "position_index": (section_index * 100) + i,  # セクション内での相対位置
                        "status": "pending",
                        "metadata": {
                            "section_index": section_index,
                            "section_position": i,
                            "generated_at": datetime.now(timezone.utc).isoformat()
                        }
                    }
                    
                    # プレースホルダーをデータベースに保存（UPSERT）
                    result = supabase.table("image_placeholders").upsert(
                        placeholder_data,
                        on_conflict="generation_process_id,placeholder_id"
                    ).execute()
                    
                    if result.data:
                        logger.info(f"Image placeholder saved to database - placeholder_id: {placeholder.placeholder_id}")
                    else:
                        logger.warning(f"Image placeholder save returned no data - placeholder_id: {placeholder.placeholder_id}")
                        
                except Exception as placeholder_error:
                    logger.error(f"Failed to save individual placeholder - placeholder_id: {placeholder.placeholder_id}, error: {placeholder_error}")
                    continue
                    
        except Exception as e:
            logger.error(f"Failed to save image placeholders to database - section_index: {section_index}, error: {e}")
            # プレースホルダー保存エラーは非致命的なので、エラーを投げずに続行

    async def _save_final_article_with_placeholders(self, context: ArticleContext, process_id: str, user_id: str) -> str:
        """
        最終記事をデータベースに保存し、プレースホルダー情報も更新
        """
        try:
            from app.core.config import get_supabase_client
            supabase = get_supabase_client()
            import uuid
            from datetime import datetime, timezone
            
            # 記事データを準備
            article_data = {
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "title": context.selected_theme.title if context.selected_theme else "タイトル未設定",
                "content": context.full_draft_html,
                "status": "draft",
                "target_audience": context.selected_detailed_persona if hasattr(context, 'selected_detailed_persona') else None,
                "keywords": context.initial_keywords,
                "seo_analysis": context.serp_analysis_report.dict() if hasattr(context, 'serp_analysis_report') and context.serp_analysis_report else None,
                "generation_process_id": process_id,
                "metadata": {
                    "image_mode": getattr(context, 'image_mode', False),
                    "image_settings": getattr(context, 'image_settings', {}),
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "total_sections": len(context.generated_sections_html) if hasattr(context, 'generated_sections_html') else 0,
                    "total_placeholders": len(context.image_placeholders) if hasattr(context, 'image_placeholders') else 0
                }
            }
            
            # 記事をデータベースに保存
            result = supabase.table("articles").insert(article_data).execute()
            
            if not result.data:
                raise Exception("記事の保存に失敗しました")
            
            article_id = result.data[0]["id"]
            context.final_article_id = article_id
            
            # プレースホルダー情報のarticle_idを更新
            if hasattr(context, 'image_placeholders') and context.image_placeholders:
                await self._update_placeholders_article_id(context, article_id, process_id)
            
            logger.info(f"Final article saved successfully - article_id: {article_id}, process_id: {process_id}")
            return article_id
            
        except Exception as e:
            logger.error(f"Failed to save final article - process_id: {process_id}, error: {e}")
            raise

    async def finalize_workflow_logger(self, process_id: str, status: str = "completed"):
        """
        バックグラウンド処理完了時にワークフローロガーを最終化
        """
        if LOGGING_ENABLED and process_id in self.workflow_loggers:
            try:
                workflow_logger = self.workflow_loggers[process_id]
                
                # 最終ワークフローステップをログに記録
                workflow_logger.log_workflow_step(f"process_{status}", {
                    "status": status,
                    "background_processing_complete": True,
                    "finalization": True
                })
                
                # ログセッションを完了
                workflow_logger.finalize_session(status)
                console.print(f"[cyan]Background processing complete - finalized log session for process {process_id} with status: {status}[/cyan]")
                
                # Notionに自動同期（完了したセッションのみ）
                if NOTION_SYNC_ENABLED and self.notion_sync_service and status == "completed":
                    try:
                        console.print(f"[yellow]🔄 Notionに自動同期開始: {process_id}[/yellow]")
                        sync_success = self.notion_sync_service.sync_session_to_notion(workflow_logger.session_id)
                        if sync_success:
                            console.print(f"[green]✅ Notion自動同期完了: {process_id}[/green]")
                        else:
                            console.print(f"[red]❌ Notion自動同期失敗: {process_id}[/red]")
                    except Exception as sync_err:
                        logger.warning(f"Notion auto-sync failed: {sync_err}")
                        console.print(f"[red]❌ Notion自動同期エラー: {sync_err}[/red]")
                
                # ワークフローロガーを削除
                del self.workflow_loggers[process_id]
                console.print(f"[cyan]Workflow logger cleaned up for completed process {process_id}[/cyan]")
                
            except Exception as e:
                logger.error(f"Failed to finalize workflow logger for process {process_id}: {e}")
                # エラーでもロガーは削除してメモリリークを防ぐ
                if process_id in self.workflow_loggers:
                    del self.workflow_loggers[process_id]

    async def _update_placeholders_article_id(self, context: ArticleContext, article_id: str, process_id: str):
        """
        プレースホルダーのarticle_idを更新
        """
        try:
            from app.core.config import get_supabase_client
            supabase = get_supabase_client()
            
            # generation_process_idで検索してarticle_idを更新
            result = supabase.table("image_placeholders").update({
                "article_id": article_id
            }).eq("generation_process_id", process_id).execute()
            
            if result.data:
                logger.info(f"Updated {len(result.data)} placeholders with article_id - article_id: {article_id}")
            else:
                logger.warning(f"No placeholders found to update - process_id: {process_id}")
                
        except Exception as e:
            logger.error(f"Failed to update placeholders article_id - article_id: {article_id}, process_id: {process_id}, error: {e}")
