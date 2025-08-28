# -*- coding: utf-8 -*-
import asyncio
import json
import time
import traceback
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Union
from openai import BadRequestError, AuthenticationError
from agents import Runner, RunConfig, Agent, trace
from agents.exceptions import MaxTurnsExceeded, ModelBehaviorError, UserError
from agents.tracing import custom_span
from rich.console import Console
from pydantic import ValidationError

# 内部モジュールのインポート
from app.core.config import settings
from app.domains.seo_article.schemas import (
    # Server event payloads
    StatusUpdatePayload, ThemeProposalPayload, ResearchPlanPayload, ResearchProgressPayload,
    ResearchCompletePayload, OutlinePayload, SectionChunkPayload, EditingStartPayload, ImagePlaceholderData,
    FinalResultPayload, GeneratedPersonasPayload, SerpKeywordAnalysisPayload, SerpAnalysisArticleData,
    # Client response payloads
    SelectThemePayload, ApprovePayload, SelectPersonaPayload, GeneratedPersonaData, 
    EditAndProceedPayload, EditThemePayload, EditPlanPayload, EditOutlinePayload,
    # Data models
    ThemeProposalData
)
from app.common.schemas import (
    UserInputType
)
from app.domains.seo_article.context import ArticleContext
from app.domains.seo_article.schemas import (
    ThemeProposal, ResearchPlan, ResearchQueryResult, ResearchReport, Outline, OutlineSection,
    RevisedArticle, ClarificationNeeded, StatusUpdate, ArticleSection, GeneratedPersonasResponse, ThemeProposal as ThemeIdea,
    SerpKeywordAnalysisReport, OutlineSectionData,
    ArticleSectionWithImages
)
from app.domains.seo_article.agents.definitions import (
    theme_agent, research_planner_agent, researcher_agent, research_synthesizer_agent,
    outline_agent, section_writer_agent, editor_agent, persona_generator_agent,
    serp_keyword_analysis_agent,
    section_writer_with_images_agent
)

console = Console()
logger = logging.getLogger(__name__)

# ログ関連のインポート（オプション）
try:
    from app.infrastructure.logging.service import LoggingService
    from app.infrastructure.logging.agents_logging_integration import MultiAgentWorkflowLogger
    from app.infrastructure.external_apis.notion_service import NotionService as NotionSyncService
    from app.infrastructure.analysis.cost_calculation_service import CostCalculationService
    LOGGING_ENABLED = True
    NOTION_SYNC_ENABLED = True
except ImportError as e:
    logger.warning(f"Logging system not available: {e}")
    # Use None and handle the checks properly
    LoggingService = None  # type: ignore
    MultiAgentWorkflowLogger = None  # type: ignore
    NotionSyncService = None  # type: ignore
    CostCalculationService = None  # type: ignore
    LOGGING_ENABLED = False
    NOTION_SYNC_ENABLED = False

# ステップ分類定数 - 完全なステップカバレッジ
AUTONOMOUS_STEPS = {
    'keyword_analyzing', 'keyword_analyzed', 'persona_generating', 'theme_generating',
    'research_planning', 'researching', 'research_synthesizing', 'research_report_generated',
    'outline_generating', 'writing_sections', 'editing'
}

USER_INPUT_STEPS = {
    'persona_generated', 'theme_proposed', 
    'research_plan_generated', 'outline_generated'
}

TRANSITION_STEPS = {
    'persona_selected', 'theme_selected', 'research_plan_approved'
}

TERMINAL_STEPS = {
    'completed', 'error'
}

INITIAL_STEPS = {
    'start'
}

DISCONNECTION_RESILIENT_STEPS = {
    'research_planning', 'researching', 'research_synthesizing', 'research_report_generated',
    'outline_generating', 'writing_sections', 'editing'
}

# 全ステップの統合リスト（デバッグ・検証用）
ALL_VALID_STEPS = (
    AUTONOMOUS_STEPS | USER_INPUT_STEPS | TRANSITION_STEPS | 
    TERMINAL_STEPS | INITIAL_STEPS
)

def safe_trace_context(workflow_name: str, trace_id: str, group_id: str):
    """トレーシングエラーを安全にハンドリングするコンテキストマネージャー"""
    try:
        return trace(workflow_name=workflow_name, trace_id=trace_id, group_id=group_id)
    except Exception as e:
        logger.warning(f"トレーシング初期化に失敗しました: {e}")
        from contextlib import nullcontext
        return nullcontext()

def safe_custom_span(name: str, data: dict[str, Any] | None = None):
    """カスタムスパンを安全にハンドリングするコンテキストマネージャー"""
    try:
        return custom_span(name=name, data=data)
    except Exception as e:
        logger.warning(f"カスタムスパン作成に失敗しました: {e}")
        from contextlib import nullcontext
        return nullcontext()

class GenerationFlowManager:
    """記事生成フローの管理とエージェントの実行を担当するクラス"""
    
    def __init__(self, service):
        self.service = service  # ArticleGenerationServiceへの参照
        
    async def run_generation_loop(self, context: ArticleContext, run_config: RunConfig, process_id: Optional[str] = None, user_id: Optional[str] = None):
        """記事生成のメインループ（WebSocketインタラクティブ版）"""

        # ワークフローロガーを確実に確保
        await self.ensure_workflow_logger(context, process_id, user_id)

        try:
            while context.current_step not in ["completed", "error"]:
                console.print(f"[green]生成ループ開始: {context.current_step} (process_id: {process_id})[/green]")
                
                # 非同期yield pointを追加してWebSocketループに制御を戻す
                await asyncio.sleep(0.1)
                
                # データベースに現在の状態を保存
                if process_id and user_id:
                    await self.service.persistence_service.save_context_to_db(context, process_id=process_id, user_id=user_id)
                
                await self.service.utils.send_server_event(context, StatusUpdatePayload(
                    step=context.current_step, 
                    message=f"Starting step: {context.current_step}",
                    image_mode=getattr(context, 'image_mode', False)
                ))
                console.rule(f"[bold yellow]API Step: {context.current_step}[/bold yellow]")

                # ステップ実行
                await self.execute_step(context, run_config, process_id, user_id)

        except asyncio.CancelledError:
            console.print("[yellow]Generation loop cancelled.[/yellow]")
            await self.service.utils.send_error(context, "Generation process cancelled.", context.current_step)
        except Exception as e:
            await self.handle_generation_error(context, e, process_id)
        finally:
            await self.finalize_generation_loop(context, process_id)

    async def execute_step(self, context: ArticleContext, run_config: RunConfig, process_id: Optional[str] = None, user_id: Optional[str] = None):
        """個別のステップを実行"""
        if context.current_step == "start":
            await self.handle_start_step(context)
        elif context.current_step == "keyword_analyzing":
            await self.handle_keyword_analyzing_step(context, run_config, process_id, user_id)
        elif context.current_step == "persona_generating":
            await self.handle_persona_generating_step(context, run_config, process_id, user_id)
        elif context.current_step == "persona_selected":
            await self.handle_persona_selected_step(context, process_id, user_id)
        elif context.current_step == "theme_generating":
            await self.handle_theme_generating_step(context, run_config, process_id, user_id)
        elif context.current_step == "theme_selected":
            await self.handle_theme_selected_step(context, process_id)
        elif context.current_step == "research_planning":
            await self.handle_research_planning_step(context, run_config, process_id, user_id)
        elif context.current_step == "research_plan_approved":
            await self.handle_research_plan_approved_step(context, process_id, user_id)
        elif context.current_step == "researching":
            await self.handle_researching_step(context, run_config, process_id, user_id)
        elif context.current_step == "research_synthesizing":
            await self.handle_research_synthesizing_step(context, run_config, process_id, user_id)
        elif context.current_step == "outline_generating":
            await self.handle_outline_generating_step(context, run_config, process_id, user_id)
        elif context.current_step == "outline_generated":
            await self.handle_outline_generated_step(context, process_id, user_id)
        elif context.current_step == "outline_approved":
            await self.handle_outline_approved_step(context, process_id, user_id)
        elif context.current_step == "writing_sections":
            await self.handle_writing_sections_step(context, run_config, process_id, user_id)
        elif context.current_step == "editing":
            await self.handle_editing_step(context, run_config, process_id, user_id)
        else:
            await self.handle_user_input_step_or_unknown(context, process_id, user_id)

    async def handle_start_step(self, context: ArticleContext):
        """開始ステップの処理"""
        context.current_step = "keyword_analyzing"
        await self.log_workflow_step(context, "keyword_analyzing", {
            "has_serp_api": context.has_serp_api_key,
            "initial_keywords": context.initial_keywords
        })
        if context.websocket:
            await self.service.utils.send_server_event(context, StatusUpdatePayload(
                step=context.current_step, 
                message="Starting keyword analysis with SerpAPI...", 
                image_mode=getattr(context, 'image_mode', False)
            ))

    async def handle_keyword_analyzing_step(self, context: ArticleContext, run_config: RunConfig, process_id: Optional[str] = None, user_id: Optional[str] = None):
        """キーワード分析ステップの処理"""
        # 重複実行防止チェック
        if context.executing_step == "keyword_analyzing":
            console.print("[yellow]キーワード分析は既に実行中です。スキップします。[/yellow]")
            await asyncio.sleep(1)
            return
        
        context.executing_step = "keyword_analyzing"
        
        current_agent = serp_keyword_analysis_agent
        agent_input = f"キーワード: {', '.join(context.initial_keywords)}"
        console.print(f"🤖 {current_agent.name} にSerpAPIキーワード分析を依頼します...")
        agent_output = await self.run_agent(current_agent, agent_input, context, run_config)

        if isinstance(agent_output, SerpKeywordAnalysisReport):
            # 必要なフィールドの設定
            self.ensure_serp_analysis_fields(agent_output, context)
            
            context.serp_analysis_report = agent_output
            context.current_step = "keyword_analyzed"
            context.executing_step = None
            console.print("[green]SerpAPIキーワード分析が完了しました。[/green]")
            
            await self.save_and_send_keyword_analysis(context, agent_output, process_id, user_id)
            
            # 次のステップに進む
            context.current_step = "persona_generating"
            if context.websocket:
                await self.service.utils.send_server_event(context, StatusUpdatePayload(
                    step=context.current_step, 
                    message="Keyword analysis completed, proceeding to persona generation.", 
                    image_mode=getattr(context, 'image_mode', False)
                ))
        else:
            context.executing_step = None
            await self.service.utils.send_error(context, f"SerpAPIキーワード分析中に予期しないエージェント出力タイプ ({type(agent_output)}) を受け取りました。")
            context.current_step = "error"

    async def handle_persona_generating_step(self, context: ArticleContext, run_config: RunConfig, process_id: Optional[str] = None, user_id: Optional[str] = None):
        """ペルソナ生成ステップの処理"""
        current_agent = persona_generator_agent
        agent_input = f"キーワード: {context.initial_keywords}, 年代: {context.target_age_group}, 属性: {context.persona_type}, 独自ペルソナ: {context.custom_persona}, 生成数: {context.num_persona_examples}"
        console.print(f"🤖 {current_agent.name} に具体的なペルソナ生成を依頼します...")
        agent_output = await self.run_agent(current_agent, agent_input, context, run_config)

        if isinstance(agent_output, GeneratedPersonasResponse):
            context.generated_detailed_personas = [p.description for p in agent_output.personas]
            context.current_step = "persona_generated"
            console.print(f"[cyan]{len(context.generated_detailed_personas)}件の具体的なペルソナを生成しました。クライアントの選択を待ちます...[/cyan]")
            
            # Save context after persona generation
            if process_id and user_id:
                try:
                    await self.service.persistence_service.save_context_to_db(context, process_id=process_id, user_id=user_id)
                    logger.info("Context saved successfully after persona generation")
                except Exception as save_err:
                    logger.error(f"Failed to save context after persona generation: {save_err}")
            
            await self.handle_persona_user_interaction(context, process_id, user_id)
        else:
            console.print("[red]ペルソナ生成中に予期しないエージェント出力タイプを受け取りました。[/red]")
            context.current_step = "error"

    async def handle_persona_user_interaction(self, context: ArticleContext, process_id: Optional[str] = None, user_id: Optional[str] = None):
        """ペルソナ選択のユーザーインタラクション処理"""
        personas_data_for_client = [GeneratedPersonaData(id=i, description=desc) for i, desc in enumerate(context.generated_detailed_personas)]
        
        # CRITICAL FIX: Set step to completed state and mark waiting for input using RPC
        if process_id and user_id:
            try:
                from app.domains.seo_article.services.flow_service import get_supabase_client
                
                # 1) Ensure current_step_name is set to completion state
                context.current_step = "persona_generated"
                await self.service.persistence_service.update_process_state(
                    process_id=process_id,
                    current_step_name="persona_generated"
                )
                
                # 2) Save context with generated personas to DB
                await self.service.persistence_service.save_context_to_db(
                    context, process_id=process_id, user_id=user_id
                )
                
                # 3) Mark process waiting for input using RPC (triggers events and Realtime)
                supabase = get_supabase_client()
                await supabase.rpc(
                    'mark_process_waiting_for_input',
                    {'p_process_id': process_id, 'p_input_type': 'select_persona', 'p_timeout_minutes': 60}
                ).execute()
                
                logger.info("Process state marked waiting for persona selection with RPC")
            except Exception as save_err:
                logger.error(f"Failed to mark process waiting for persona selection: {save_err}")
        
        user_response_message = await self.service.utils.request_user_input(
            context,
            UserInputType.SELECT_PERSONA,
            GeneratedPersonasPayload(personas=personas_data_for_client).model_dump()
        )
        
        if user_response_message:
            response_type = user_response_message.response_type
            payload_dict = user_response_message.payload
            payload = self.service.utils.convert_payload_to_model(payload_dict, response_type)

            if response_type == UserInputType.SELECT_PERSONA and payload and isinstance(payload, SelectPersonaPayload):
                await self.handle_persona_selection(context, payload, process_id, user_id)
            elif response_type == UserInputType.REGENERATE:
                await self.handle_persona_regeneration(context)
            elif response_type == UserInputType.EDIT_AND_PROCEED and payload and isinstance(payload, EditAndProceedPayload):
                await self.handle_persona_edit(context, payload, process_id, user_id)
            else:
                await self.handle_invalid_persona_response(context, response_type, payload)

    async def handle_persona_selection(self, context: ArticleContext, payload: SelectPersonaPayload, process_id: Optional[str] = None, user_id: Optional[str] = None):
        """ペルソナ選択の処理"""
        selected_id = payload.selected_id
        if 0 <= selected_id < len(context.generated_detailed_personas):
            context.selected_detailed_persona = context.generated_detailed_personas[selected_id]
            context.current_step = "persona_selected"
            console.print(f"[green]クライアントがペルソナID {selected_id} を選択しました。[/green]")
            await self.service.utils.send_server_event(context, StatusUpdatePayload(
                step=context.current_step, 
                message=f"Detailed persona selected: {context.selected_detailed_persona[:50]}...", 
                image_mode=getattr(context, 'image_mode', False)
            ))
            
            if process_id and user_id:
                try:
                    await self.service.persistence_service.save_context_to_db(context, process_id=process_id, user_id=user_id)
                    logger.info("Context saved successfully after persona selection")
                except Exception as save_err:
                    logger.error(f"Failed to save context after persona selection: {save_err}")
        else:
            raise ValueError(f"無効なペルソナIDが選択されました: {selected_id}")

    async def handle_persona_regeneration(self, context: ArticleContext):
        """ペルソナ再生成の処理"""
        console.print("[yellow]クライアントがペルソナの再生成を要求しました。[/yellow]")
        context.current_step = "persona_generating"
        context.generated_detailed_personas = []

    async def handle_persona_edit(self, context: ArticleContext, payload: EditAndProceedPayload, process_id: Optional[str] = None, user_id: Optional[str] = None):
        """ペルソナ編集の処理"""
        edited_persona_description = payload.edited_content.get("description")
        if edited_persona_description and isinstance(edited_persona_description, str):
            context.selected_detailed_persona = edited_persona_description
            context.current_step = "persona_selected"
            console.print(f"[green]クライアントがペルソナを編集し、選択しました: {context.selected_detailed_persona[:50]}...[/green]")
            await self.service.utils.send_server_event(context, StatusUpdatePayload(
                step=context.current_step, 
                message="Detailed persona edited and selected.", 
                image_mode=getattr(context, 'image_mode', False)
            ))
            
            if process_id and user_id:
                try:
                    await self.service.persistence_service.save_context_to_db(context, process_id=process_id, user_id=user_id)
                    logger.info("Context saved successfully after persona editing and selection")
                except Exception as save_err:
                    logger.error(f"Failed to save context after persona editing: {save_err}")
        else:
            await self.service.utils.send_error(context, "Invalid edited persona content.")
            context.current_step = "persona_generated"

    async def handle_invalid_persona_response(self, context: ArticleContext, response_type: UserInputType, payload):
        """無効なペルソナ応答の処理"""
        payload_type = type(payload).__name__ if payload else "None"
        await self.service.utils.send_error(context, f"予期しない応答 ({response_type}, {payload_type}) がペルソナ選択で受信されました。")
        context.current_step = "persona_generated"

    async def handle_persona_selected_step(self, context: ArticleContext, process_id: Optional[str] = None, user_id: Optional[str] = None):
        """ペルソナ選択完了ステップの処理"""
        context.current_step = "theme_generating"
        
        # データベースに現在の状態を保存
        if process_id and user_id:
            try:
                await self.service.persistence_service.save_context_to_db(context, process_id=process_id, user_id=user_id)
                logger.info("Context saved successfully after persona selection step")
            except Exception as save_err:
                logger.error(f"Failed to save context after persona selection step: {save_err}")
        
        await self.service.utils.send_server_event(context, StatusUpdatePayload(
            step=context.current_step, 
            message="Persona selected, proceeding to theme generation.", 
            image_mode=getattr(context, 'image_mode', False)
        ))

    async def handle_theme_generating_step(self, context: ArticleContext, run_config: RunConfig, process_id: Optional[str] = None, user_id: Optional[str] = None):
        """テーマ生成ステップの処理"""
        current_agent = theme_agent
        if not context.selected_detailed_persona:
            await self.service.utils.send_error(context, "詳細ペルソナが選択されていません。テーマ生成をスキップします。", "theme_generating")
            context.current_step = "error"
            return
        
        # データベースに現在の状態を保存（テーマ生成開始時）
        if process_id and user_id:
            try:
                await self.service.persistence_service.save_context_to_db(context, process_id=process_id, user_id=user_id)
                logger.info("Context saved successfully at theme generation start")
            except Exception as save_err:
                logger.error(f"Failed to save context at theme generation start: {save_err}")
        
        # SerpAPI分析結果を含めたプロンプト作成
        agent_input = self.create_theme_agent_input(context)
        
        console.print(f"🤖 {current_agent.name} にテーマ提案を依頼します...")
        agent_output = await self.run_agent(current_agent, agent_input, context, run_config)

        if isinstance(agent_output, ThemeProposal):
            await self.handle_theme_proposal_result(context, agent_output, process_id, user_id)
        elif isinstance(agent_output, ClarificationNeeded):
            await self.service.utils.send_error(context, f"テーマ生成で明確化が必要です: {agent_output.message}")
            context.current_step = "error"
        else:
            await self.service.utils.send_error(context, f"テーマ生成中に予期しないエージェント出力タイプ ({type(agent_output)}) を受け取りました。")
            context.current_step = "error"

    def create_theme_agent_input(self, context: ArticleContext) -> str:
        """テーマエージェント用の入力を作成"""
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
            return agent_input_base + seo_context
        return agent_input_base

    async def handle_theme_proposal_result(self, context: ArticleContext, agent_output: ThemeProposal, process_id: Optional[str] = None, user_id: Optional[str] = None):
        """テーマ提案結果の処理"""
        context.generated_themes = agent_output.themes
        if context.generated_themes:
            context.current_step = "theme_proposed"
            console.print(f"[cyan]{len(context.generated_themes)}件のテーマ案を生成しました。クライアントの選択を待ちます...[/cyan]")
            
            if process_id and user_id:
                try:
                    await self.service.persistence_service.save_context_to_db(context, process_id=process_id, user_id=user_id)
                    logger.info("Context saved successfully after theme generation")
                except Exception as save_err:
                    logger.error(f"Failed to save context after theme generation: {save_err}")
            
            await self.handle_theme_user_interaction(context, process_id, user_id)
        else:
            await self.service.utils.send_error(context, "テーマ案がエージェントによって生成されませんでした。再試行します。")
            context.current_step = "theme_generating"

    async def handle_theme_user_interaction(self, context: ArticleContext, process_id: Optional[str] = None, user_id: Optional[str] = None):
        """テーマ選択のユーザーインタラクション処理"""
        themes_data_for_client = [
            ThemeProposalData(title=idea.title, description=idea.description, keywords=idea.keywords)
            for idea in context.generated_themes
        ]
        
        # CRITICAL FIX: Set step to completed state and mark waiting for input using RPC
        if process_id and user_id:
            try:
                from app.domains.seo_article.services.flow_service import get_supabase_client
                
                # 1) Ensure current_step_name is set to completion state
                context.current_step = "theme_proposed"
                await self.service.persistence_service.update_process_state(
                    process_id=process_id,
                    current_step_name="theme_proposed"
                )
                
                # 2) Save context with generated themes to DB
                await self.service.persistence_service.save_context_to_db(
                    context, process_id=process_id, user_id=user_id
                )
                
                # 3) Mark process waiting for input using RPC (triggers events and Realtime)
                supabase = get_supabase_client()
                await supabase.rpc(
                    'mark_process_waiting_for_input',
                    {'p_process_id': process_id, 'p_input_type': 'select_theme', 'p_timeout_minutes': 60}
                ).execute()
                
                logger.info("Process state marked waiting for theme selection with RPC")
            except Exception as save_err:
                logger.error(f"Failed to mark process waiting for theme selection: {save_err}")
        
        user_response_message = await self.service.utils.request_user_input(
            context,
            UserInputType.SELECT_THEME,
            ThemeProposalPayload(themes=themes_data_for_client).model_dump()
        )
        
        if user_response_message:
            response_type = user_response_message.response_type
            payload_dict = user_response_message.payload
            payload = self.service.utils.convert_payload_to_model(payload_dict, response_type)

            if response_type == UserInputType.SELECT_THEME and payload and isinstance(payload, SelectThemePayload):
                await self.handle_theme_selection(context, payload, process_id, user_id)
            elif response_type == UserInputType.REGENERATE:
                await self.handle_theme_regeneration(context)
            elif response_type == UserInputType.EDIT_AND_PROCEED and payload and isinstance(payload, EditAndProceedPayload):
                await self.handle_theme_edit(context, payload, process_id, user_id)
            else:
                await self.handle_invalid_theme_response(context, response_type, payload)

    async def handle_theme_selection(self, context: ArticleContext, payload: SelectThemePayload, process_id: Optional[str] = None, user_id: Optional[str] = None):
        """テーマ選択の処理"""
        selected_index = payload.selected_index
        if 0 <= selected_index < len(context.generated_themes):
            context.selected_theme = context.generated_themes[selected_index]
            context.current_step = "theme_selected"
            console.print(f"[green]クライアントがテーマ「{context.selected_theme.title}」を選択しました。[/green]")
            await self.service.utils.send_server_event(context, StatusUpdatePayload(
                step=context.current_step, 
                message=f"Theme selected: {context.selected_theme.title}", 
                image_mode=getattr(context, 'image_mode', False)
            ))
            
            if process_id and user_id:
                try:
                    await self.service.persistence_service.save_context_to_db(context, process_id=process_id, user_id=user_id)
                    logger.info("Context saved successfully after theme selection")
                except Exception as save_err:
                    logger.error(f"Failed to save context after theme selection: {save_err}")
            
            console.print(f"[blue]テーマ選択処理完了。次のステップ: {context.current_step}[/blue]")
        else:
            await self.service.utils.send_error(context, f"無効なテーマインデックスが選択されました: {selected_index}")
            context.current_step = "theme_proposed"

    async def handle_theme_regeneration(self, context: ArticleContext):
        """テーマ再生成の処理"""
        console.print("[yellow]クライアントがテーマの再生成を要求しました。[/yellow]")
        context.current_step = "theme_generating"
        context.generated_themes = []

    async def handle_theme_edit(self, context: ArticleContext, payload: EditAndProceedPayload, process_id: Optional[str] = None, user_id: Optional[str] = None):
        """テーマ編集の処理"""
        try:
            edited_theme_data = payload.edited_content
            if (isinstance(edited_theme_data.get("title"), str) and 
                isinstance(edited_theme_data.get("description"), str) and 
                isinstance(edited_theme_data.get("keywords"), list)):
                
                context.selected_theme = ThemeIdea(**edited_theme_data)
                context.current_step = "theme_selected"
                console.print(f"[green]クライアントがテーマを編集し、選択しました: {context.selected_theme.title}[/green]")
                await self.service.utils.send_server_event(context, StatusUpdatePayload(
                    step=context.current_step, 
                    message="Theme edited and selected.", 
                    image_mode=getattr(context, 'image_mode', False)
                ))
                
                if process_id and user_id:
                    try:
                        await self.service.persistence_service.save_context_to_db(context, process_id=process_id, user_id=user_id)
                        logger.info("Context saved successfully after theme editing and selection")
                    except Exception as save_err:
                        logger.error(f"Failed to save context after theme editing: {save_err}")
            else:
                await self.service.utils.send_error(context, "Invalid edited theme content structure.")
                context.current_step = "theme_proposed"
        except (ValidationError, TypeError, AttributeError) as e:
            await self.service.utils.send_error(context, f"Error processing edited theme: {e}")
            context.current_step = "theme_proposed"

    async def handle_invalid_theme_response(self, context: ArticleContext, response_type: UserInputType, payload):
        """無効なテーマ応答の処理"""
        payload_type = type(payload).__name__ if payload else "None"
        await self.service.utils.send_error(context, f"予期しない応答 ({response_type}, {payload_type}) がテーマ選択で受信されました。")
        context.current_step = "theme_proposed"

    async def handle_theme_selected_step(self, context: ArticleContext, process_id: Optional[str] = None):
        """テーマ選択完了ステップの処理"""
        console.print(f"[blue]theme_selectedステップを処理中... (process_id: {process_id})[/blue]")
        context.current_step = "research_planning"
        console.print("[blue]theme_selectedからresearch_planningに遷移します...[/blue]")
        await self.service.utils.send_server_event(context, StatusUpdatePayload(
            step=context.current_step, 
            message="Moving to research planning.", 
            image_mode=getattr(context, 'image_mode', False)
        ))
        console.print(f"[blue]research_planningステップに移行完了。継続中... (process_id: {process_id})[/blue]")

    async def handle_research_planning_step(self, context: ArticleContext, run_config: RunConfig, process_id: Optional[str] = None, user_id: Optional[str] = None):
        """リサーチ計画ステップの処理"""
        console.print(f"[blue]research_planningステップを開始します。selected_theme: {context.selected_theme.title if context.selected_theme else 'None'}[/blue]")
        if not context.selected_theme:
            console.print("[red]テーマが選択されていません。リサーチ計画作成をスキップします。[/red]")
            context.current_step = "error"
            return

        current_agent = research_planner_agent
        agent_input = f"選択されたテーマ「{context.selected_theme.title}」についてのリサーチ計画を作成してください。"
        console.print(f"🤖 {current_agent.name} にリサーチ計画作成を依頼します...")
        agent_output = await self.run_agent(current_agent, agent_input, context, run_config)

        if isinstance(agent_output, ResearchPlan):
            context.research_plan = agent_output
            context.current_step = "research_plan_generated"
            console.print("[cyan]リサーチ計画を生成しました。[/cyan]")
            
            if process_id and user_id:
                try:
                    await self.service.persistence_service.save_context_to_db(context, process_id=process_id, user_id=user_id)
                    logger.info("Context saved successfully after research plan generation")
                except Exception as save_err:
                    logger.error(f"Failed to save context after research plan generation: {save_err}")
        elif isinstance(agent_output, ClarificationNeeded):
            await self.service.utils.send_error(context, f"リサーチ計画作成で明確化が必要です: {agent_output.message}")
            context.current_step = "error"
        else:
            await self.service.utils.send_error(context, f"リサーチ計画作成中に予期しないエージェント出力タイプ ({type(agent_output)}) を受け取りました。")
            context.current_step = "error"

    async def handle_user_input_step_or_unknown(self, context: ArticleContext, process_id: Optional[str] = None, user_id: Optional[str] = None):
        """ユーザー入力ステップまたは未知のステップの処理"""
        if context.current_step in USER_INPUT_STEPS:
            console.print(f"[yellow]ステップ {context.current_step} はユーザー入力が必要です。ユーザー応答を処理します。[/yellow]")
            await self.handle_user_input_step(context, process_id, user_id)
        else:
            raise ValueError(f"未定義のステップ: {context.current_step}")

    async def execute_single_step(self, context: "ArticleContext", run_config: RunConfig, process_id: Optional[str] = None, user_id: Optional[str] = None):
        """単一ステップの実行（WebSocket不要版）"""
        
        # ワークフローロガーの確保
        await self.ensure_workflow_logger(context, process_id, user_id)
        
        # データベースに現在の状態を保存
        if process_id and user_id:
            await self.service.persistence_service.save_context_to_db(context, process_id=process_id, user_id=user_id)
        
        # WebSocketがある場合のみイベント送信
        if context.websocket:
            await self.service.utils.send_server_event(context, StatusUpdatePayload(
                step=context.current_step, 
                message=f"Starting step: {context.current_step}", 
                image_mode=getattr(context, 'image_mode', False)
            ))
        
        console.rule(f"[bold yellow]Background Step: {context.current_step}[/bold yellow]")

        # バックグラウンド専用のステップ実行
        await self.execute_background_step(context, run_config, process_id, user_id)

    async def execute_background_step(self, context: "ArticleContext", run_config: RunConfig, process_id: Optional[str] = None, user_id: Optional[str] = None):
        """バックグラウンド専用のステップ実行"""
        if context.current_step == "start":
            context.current_step = "keyword_analyzing"
            await self.log_workflow_step(context, "keyword_analyzing", {
                "has_serp_api": context.has_serp_api_key,
                "initial_keywords": context.initial_keywords
            })
            
        elif context.current_step == "research_planning":
            await self.execute_research_planning_background(context, run_config)
            
        elif context.current_step == "researching":
            await self.execute_researching_background(context, run_config)
            
        elif context.current_step == "research_synthesizing":
            await self.execute_research_synthesizing_background(context, run_config)
            
        elif context.current_step == "outline_generating":
            await self.execute_outline_generating_background(context, run_config)
            
        elif context.current_step == "writing_sections":
            await self.execute_writing_sections_background(context, run_config)
            
        elif context.current_step == "editing":
            await self.execute_editing_background(context, run_config, process_id)
            
        else:
            if context.current_step in USER_INPUT_STEPS:
                console.print(f"[yellow]ステップ {context.current_step} はユーザー入力が必要です。バックグラウンド処理を一時停止。[/yellow]")
                return
            else:
                console.print(f"[red]未定義または処理不可能なステップ: {context.current_step}[/red]")
                context.current_step = "error"

    async def execute_research_planning_background(self, context: "ArticleContext", run_config: RunConfig):
        """リサーチ計画のバックグラウンド実行"""
        if not context.selected_theme:
            console.print("[red]テーマが選択されていません。リサーチ計画作成をスキップします。[/red]")
            context.current_step = "error"
            return

        current_agent = research_planner_agent
        agent_input = f"選択されたテーマ「{context.selected_theme.title}」についてのリサーチ計画を作成してください。"
        console.print(f"🤖 {current_agent.name} にリサーチ計画作成を依頼します...")
        agent_output = await self.run_agent(current_agent, agent_input, context, run_config)

        if isinstance(agent_output, ResearchPlan):
            context.research_plan = agent_output
            context.current_step = "research_plan_generated"
            console.print("[cyan]リサーチ計画を生成しました。[/cyan]")
        else:
            console.print("[red]リサーチ計画生成中に予期しないエージェント出力タイプを受け取りました。[/red]")
            context.current_step = "error"

    async def execute_researching_background(self, context: "ArticleContext", run_config: RunConfig):
        """リサーチのバックグラウンド実行（並列処理）"""
        if not context.research_plan:
            console.print("[red]承認されたリサーチ計画がありません。リサーチをスキップします。[/red]")
            context.current_step = "error"
            return

        context.research_query_results = []
        total_queries = len(context.research_plan.queries)
        
        console.print(f"[cyan]🚀 {total_queries}件のリサーチクエリを並列実行開始...[/cyan]")
        
        # Create tasks for parallel execution
        async def execute_single_query(query, query_index: int):
            """Execute a single research query"""
            try:
                console.print(f"🔍 リサーチクエリ {query_index+1}/{total_queries}: {query.query}")
                
                current_agent = researcher_agent
                agent_input = query.query
                agent_output = await self.run_agent(current_agent, agent_input, context, run_config)

                if isinstance(agent_output, ResearchQueryResult):
                    console.print(f"[green]✅ クエリ {query_index+1} のリサーチが完了しました。[/green]")
                    return query_index, agent_output, True
                else:
                    console.print(f"[red]❌ リサーチクエリ {query_index+1} で予期しないエージェント出力タイプを受け取りました。[/red]")
                    return query_index, None, False
                    
            except Exception as e:
                console.print(f"[red]❌ リサーチクエリ {query_index+1} でエラーが発生: {e}[/red]")
                logger.error(f"Error in research query {query_index + 1}: {e}")
                return query_index, None, False
        
        # Execute all queries in parallel with concurrency limit
        # Limit concurrent requests to prevent API rate limiting
        semaphore = asyncio.Semaphore(5)  # Max 5 concurrent research queries
        
        async def execute_with_semaphore(query, query_index: int):
            """Execute query with concurrency control"""
            async with semaphore:
                return await execute_single_query(query, query_index)
        
        tasks = [
            execute_with_semaphore(query, i) 
            for i, query in enumerate(context.research_plan.queries)
        ]
        
        # Wait for all queries to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results in original order
        successful_queries = 0
        failed_queries = []
        
        # Sort results by query_index to maintain order
        sorted_results = []
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Research query failed with exception: {result}")
                failed_queries.append(str(result))
            elif isinstance(result, tuple):
                query_index, agent_output, success = result
                sorted_results.append((query_index, agent_output, success))
                if success:
                    successful_queries += 1
                else:
                    failed_queries.append(f"Query {query_index + 1}")
        
        # Sort by query_index and add successful results to context
        sorted_results.sort(key=lambda x: x[0])
        for query_index, agent_output, success in sorted_results:
            if success and agent_output:
                context.research_query_results.append(agent_output)
        
        # Update progress
        context.research_progress = {
            'current_query': total_queries,
            'total_queries': total_queries,
            'completed_queries': successful_queries,
            'failed_queries': len(failed_queries)
        }
        
        # Send final progress update via WebSocket if available
        if context.websocket:
            await self.service.utils.send_server_event(context, ResearchProgressPayload(
                current_query=total_queries,
                total_queries=total_queries,
                query_text="並列リサーチ完了",
                completed=True
            ))
        
        console.print(f"[cyan]🎉 並列リサーチ完了: {successful_queries}/{total_queries} 成功[/cyan]")
        
        if successful_queries == 0:
            console.print("[red]❌ 全てのリサーチクエリが失敗しました。[/red]")
            context.current_step = "error"
            return
        
        context.current_step = "research_synthesizing"

    async def ensure_serp_analysis_fields(self, agent_output: SerpKeywordAnalysisReport, context: ArticleContext):
        """SerpAPI分析結果に必要なフィールドを確保"""
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

    async def save_and_send_keyword_analysis(self, context: ArticleContext, agent_output: SerpKeywordAnalysisReport, process_id: Optional[str] = None, user_id: Optional[str] = None):
        """キーワード分析結果の保存と送信"""
        # Save context after keyword analysis completion
        if process_id and user_id:
            try:
                await self.service.persistence_service.save_context_to_db(context, process_id=process_id, user_id=user_id)
                logger.info("Context saved successfully after keyword analysis completion")
            except Exception as save_err:
                logger.error(f"Failed to save context after keyword analysis: {save_err}")
        
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
        await self.service.utils.send_server_event(context, analysis_data)
        
        # 推奨目標文字数をコンテキストに設定（ユーザー指定がない場合）
        if not context.target_length:
            context.target_length = agent_output.recommended_target_length
            console.print(f"[cyan]推奨目標文字数を設定しました: {context.target_length}文字[/cyan]")

    async def run_agent(self, agent: Agent[ArticleContext], input_data: Union[str, List[Dict[str, Any]]], context: ArticleContext, run_config: RunConfig) -> Any:
        """エージェントを実行し、結果を返す（リトライ付き）"""
        last_exception = None
        start_time = time.time()
        execution_log_id = None
        
        # プロセスIDを取得してログを開始
        process_id = context.process_id
        console.print(f"[dim]Agent execution - process_id: {process_id}, workflow_loggers keys: {list(self.service.workflow_loggers.keys())}[/dim]")
        
        # ワークフローロガーの取得・作成を確実に行う
        workflow_logger = self.service.workflow_loggers.get(process_id) if process_id else None
        if not workflow_logger and process_id and LOGGING_ENABLED and MultiAgentWorkflowLogger:
            console.print(f"[yellow]⚠️ No workflow logger found for process {process_id}, creating one now[/yellow]")
            try:
                await self.ensure_workflow_logger(context, process_id, getattr(context, 'user_id', 'unknown'))
                workflow_logger = self.service.workflow_loggers.get(process_id)
                console.print(f"[green]✅ Successfully created workflow logger for process {process_id}[/green]")
            except Exception as e:
                console.print(f"[red]❌ Failed to create workflow logger for process {process_id}: {e}[/red]")

        # エージェント実行のメインロジック
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

                    # 成功時の処理とログ記録
                    if result and result.final_output:
                        output = result.final_output
                        execution_time = time.time() - start_time
                        
                        logger.info(f"エージェント {agent.name} 実行成功: {execution_time:.2f}秒, 試行回数: {attempt + 1}")
                        
                        # ログ記録処理
                        await self.log_agent_execution(workflow_logger, agent, result, execution_time, attempt)
                        
                        # 出力の検証と変換
                        return await self.validate_and_convert_agent_output(agent, output)
                    else:
                        console.print(f"[yellow]エージェント {agent.name} から有効な出力が得られませんでした。[/yellow]")
                        raise ModelBehaviorError(f"No valid final output from agent {agent.name}")

                except Exception as e:
                    last_exception = e
                    await self.handle_agent_execution_error(agent, e, attempt, start_time, workflow_logger)
                    
                    if self.should_break_retry(e) or attempt >= settings.max_retries - 1:
                        break
                    
                    delay = settings.initial_retry_delay * (2 ** attempt)
                    await asyncio.sleep(delay)

            # リトライ上限到達時の処理
            if last_exception:
                total_time = time.time() - start_time
                logger.error(f"エージェント {agent.name} の実行に失敗しました（リトライ上限到達）: 総実行時間 {total_time:.2f}秒, 最終エラー: {type(last_exception).__name__}")
                console.print(f"[bold red]エージェント {agent.name} の実行に失敗しました（リトライ上限到達）。[/bold red]")
                raise last_exception
            
            total_time = time.time() - start_time
            logger.error(f"エージェント {agent.name} execution finished unexpectedly: 総実行時間 {total_time:.2f}秒")
            raise RuntimeError(f"Agent {agent.name} execution finished unexpectedly.")

    def should_break_retry(self, e: Exception) -> bool:
        """リトライを中断すべきエラーかどうかを判定"""
        return isinstance(e, (BadRequestError, MaxTurnsExceeded, ModelBehaviorError, UserError, AuthenticationError))

    async def validate_and_convert_agent_output(self, agent: Agent, output: Any) -> Any:
        """エージェント出力の検証と変換"""
        if isinstance(output, (ThemeProposal, Outline, RevisedArticle, ClarificationNeeded, StatusUpdate, 
                             ResearchPlan, ResearchQueryResult, ResearchReport, GeneratedPersonasResponse, 
                             SerpKeywordAnalysisReport, ArticleSectionWithImages)):
            return output
        elif isinstance(output, str):
            # SectionWriterAgent and EditorAgent return HTML directly, not JSON
            if agent.name in ["SectionWriterAgent", "EditorAgent"]:
                return output
            
            try:
                parsed_output = json.loads(output)
                status_val = parsed_output.get("status")
                output_model_map = {
                    "theme_proposal": ThemeProposal, "outline": Outline, "revised_article": RevisedArticle,
                    "clarification_needed": ClarificationNeeded, "status_update": StatusUpdate,
                    "research_plan": ResearchPlan, "research_query_result": ResearchQueryResult, 
                    "research_report": ResearchReport, "generated_personas_response": GeneratedPersonasResponse, 
                    "serp_keyword_analysis_report": SerpKeywordAnalysisReport,
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

    async def log_agent_execution(self, workflow_logger, agent: Agent, result, execution_time: float, attempt: int):
        """エージェント実行のログ記録"""
        if LOGGING_ENABLED and workflow_logger and self.service.logging_service:
            try:
                # トークン使用量と会話履歴を抽出（ログ目的のみ、実際には使用されない）
                # token_usage = self.service.utils.extract_token_usage_from_result(result)
                # conversation_history = self.service.utils.extract_conversation_history_from_result(result, "")
                
                # ログ更新処理（簡略化）
                console.print(f"[cyan]📋 Agent execution logged for {agent.name}[/cyan]")
            except Exception as log_err:
                logger.warning(f"Failed to log agent execution: {log_err}")

    async def handle_agent_execution_error(self, agent: Agent, e: Exception, attempt: int, start_time: float, workflow_logger):
        """エージェント実行エラーの処理"""
        attempt_time = time.time() - start_time
        error_type = type(e).__name__
        
        logger.warning(f"エージェント {agent.name} 実行エラー (試行 {attempt + 1}/{settings.max_retries}): {error_type} - {e}, 経過時間: {attempt_time:.2f}秒")
        console.print(f"[yellow]エージェント {agent.name} 実行中にエラー (試行 {attempt + 1}/{settings.max_retries}): {error_type} - {e}[/yellow]")

    async def handle_generation_error(self, context: ArticleContext, e: Exception, process_id: Optional[str] = None):
        """生成プロセスのエラー処理"""
        context.current_step = "error"
        error_message = f"記事生成プロセス中にエラーが発生しました: {type(e).__name__} - {str(e)}"
        context.error_message = error_message
        console.print(f"[bold red]Error in generation loop:[/bold red] {error_message}")
        traceback.print_exc()
        
        # ワークフローロガーを最終化（エラー状態）
        if process_id:
            await self.finalize_workflow_logger(process_id, "failed")
        
        # WebSocketでエラーイベントを送信
        await self.service.utils.send_error(context, error_message, context.current_step)

    async def finalize_generation_loop(self, context: ArticleContext, process_id: Optional[str] = None):
        """生成ループの最終化処理"""
        if LOGGING_ENABLED and process_id in self.service.workflow_loggers:
            try:
                workflow_logger = self.service.workflow_loggers[process_id]
                
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
                        "background_processing": "true",
                        "websocket_disconnected": context.websocket is None
                    })
                else:
                    # 完了または切断耐性でないステップの場合は、ログセッションを完了しロガーを削除
                    workflow_logger.finalize_session(session_status)
                    console.print(f"[cyan]Finalized log session for process {process_id} with status: {session_status}[/cyan]")
                    
                    # Notionに自動同期（完了したセッションのみ）
                    if NOTION_SYNC_ENABLED and self.service.notion_sync_service and session_status == "completed":
                        try:
                            console.print(f"[yellow]🔄 Notionに自動同期開始: {process_id}[/yellow]")
                            if hasattr(self.service.notion_sync_service, 'sync_session_to_notion'):
                                sync_success = self.service.notion_sync_service.sync_session_to_notion(workflow_logger.session_id)
                                if sync_success:
                                    console.print(f"[green]✅ Notion自動同期完了: {process_id}[/green]")
                                else:
                                    console.print(f"[red]❌ Notion自動同期失敗: {process_id}[/red]")
                            else:
                                console.print("[yellow]⚠️ Notion同期メソッドが利用できません。スキップします。[/yellow]")
                        except Exception as sync_err:
                            logger.warning(f"Notion auto-sync failed: {sync_err}")
                            console.print(f"[red]❌ Notion自動同期エラー: {sync_err}[/red]")
                    
                    # クリーンアップ
                    del self.service.workflow_loggers[process_id]
                    console.print(f"[cyan]Workflow logger cleaned up for process {process_id}[/cyan]")
                
            except Exception as log_err:
                logger.error(f"Failed to finalize logging session: {log_err}")
        
        # ループ終了時のメッセージ送信
        await self.send_final_status_message(context)

    async def send_final_status_message(self, context: ArticleContext):
        """最終ステータスメッセージの送信"""
        if context.current_step == "completed":
            await self.service.utils.send_server_event(context, StatusUpdatePayload(
                step="finished", 
                message="Article generation completed successfully.", 
                image_mode=getattr(context, 'image_mode', False)
            ))
        elif context.current_step == "error":
            await self.service.utils.send_server_event(context, StatusUpdatePayload(
                step="finished", 
                message=f"Article generation finished with error: {context.error_message}", 
                image_mode=getattr(context, 'image_mode', False)
            ))
        elif context.current_step in USER_INPUT_STEPS:
            console.print(f"[yellow]Generation loop stopped at user input step: {context.current_step}[/yellow]")
        else:
            await self.service.utils.send_server_event(context, StatusUpdatePayload(
                step="finished", 
                message="Article generation finished unexpectedly.", 
                image_mode=getattr(context, 'image_mode', False)
            ))

    async def ensure_workflow_logger(self, context: ArticleContext, process_id: Optional[str] = None, user_id: Optional[str] = None):
        """ワークフローロガーを確実に確保する"""
        if not process_id or not LOGGING_ENABLED:
            console.print(f"[yellow]Workflow logger not needed: process_id={process_id}, LOGGING_ENABLED={LOGGING_ENABLED}[/yellow]")
            return
        
        # 既存のワークフローロガーをチェック
        workflow_logger = self.service.workflow_loggers.get(process_id)
        if workflow_logger:
            console.print(f"[green]✅ Workflow logger already exists for process {process_id} (session: {workflow_logger.session_id})[/green]")
            return
        
        # ワークフローロガーを作成
        console.print(f"[yellow]🔄 Creating workflow logger for process {process_id}[/yellow]")
        try:
            # コンテキストから設定を構築
            initial_config = self.build_initial_config(context)
            
            workflow_logger = MultiAgentWorkflowLogger(
                article_uuid=process_id,
                user_id=user_id or getattr(context, 'user_id', 'unknown'),
                organization_id=getattr(context, 'organization_id', None),
                initial_config=initial_config
            )
            
            # 既存のログセッションを検索または新規作成
            await self.restore_or_create_log_session(workflow_logger, process_id)
            
            # ワークフローロガーを保存
            self.service.workflow_loggers[process_id] = workflow_logger
            console.print(f"[green]✅ Workflow logger stored for process {process_id}[/green]")
            
        except Exception as e:
            logger.error(f"Failed to ensure workflow logger for process {process_id}: {e}")
            console.print(f"[red]❌ Failed to create workflow logger: {e}[/red]")

    def build_initial_config(self, context: ArticleContext) -> Dict[str, Any]:
        """ワークフローロガー用の初期設定を構築"""
        return {
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

    async def restore_or_create_log_session(self, workflow_logger, process_id: str):
        """既存のログセッションを復元または新規作成"""
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

    async def restore_logging_session(self, context: ArticleContext, process_id: str, user_id: str):
        """ログセッションを復元または作成（復帰時用）"""
        console.print(f"[debug]Process restoration - LOGGING_ENABLED: {LOGGING_ENABLED}, MultiAgentWorkflowLogger: {MultiAgentWorkflowLogger is not None}[/debug]")
        console.print(f"[debug]Current workflow_loggers keys: {list(self.service.workflow_loggers.keys())}[/debug]")
        console.print(f"[debug]process_id {process_id} in workflow_loggers: {process_id in self.service.workflow_loggers}[/debug]")
        
        if LOGGING_ENABLED and MultiAgentWorkflowLogger:
            try:
                console.print(f"[debug]Checking workflow logger for process {process_id}. Current loggers: {list(self.service.workflow_loggers.keys())}[/debug]")
                if process_id not in self.service.workflow_loggers:
                    console.print(f"[green]Creating new workflow logger for restored process {process_id} with user_id {user_id}[/green]")
                    console.print(f"[debug]LoggingService available: {self.service.logging_service is not None}[/debug]")
                    
                    # 既存のログセッションを復元しようと試行
                    initial_config = self.build_initial_config(context)
                    initial_config["restored"] = True
                    
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
                        
                    self.service.workflow_loggers[process_id] = workflow_logger
                    console.print(f"[green]Workflow logger for process {process_id} stored successfully[/green]")
            except Exception as e:
                logger.error(f"Failed to restore logging session: {e}")

    async def initialize_logging_session(self, context: ArticleContext, process_id: str, user_id: str, request):
        """新規プロセス用のログセッション初期化"""
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
                        "article_style_info": getattr(context, 'style_template_settings', {}),
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
                    
                self.service.workflow_loggers[process_id] = workflow_logger
                console.print(f"[green]Workflow logger stored in self.workflow_loggers[{process_id}][/green]")
            except Exception as e:
                logger.error(f"Failed to initialize logging session: {e}")

    async def log_workflow_step(self, context: ArticleContext, step_name: str, step_data: Dict[str, Any] = None):
        """ワークフローステップをログに記録"""
        if not LOGGING_ENABLED:
            return
        
        try:
            process_id = context.process_id
            workflow_logger = self.service.workflow_loggers.get(process_id) if process_id else None
            
            if workflow_logger and self.service.logging_service:
                # ステップタイプを決定
                step_type = "autonomous"
                if step_name in USER_INPUT_STEPS:
                    step_type = "user_input"
                elif step_name in ["error", "completed"]:
                    step_type = "terminal"
                
                step_id = self.service.logging_service.create_workflow_step_log(
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

    async def finalize_workflow_logger(self, process_id: str, status: str = "completed"):
        """バックグラウンド処理完了時にワークフローロガーを最終化"""
        if LOGGING_ENABLED and process_id in self.service.workflow_loggers:
            try:
                workflow_logger = self.service.workflow_loggers[process_id]
                
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
                if NOTION_SYNC_ENABLED and self.service.notion_sync_service and status == "completed":
                    try:
                        console.print(f"[yellow]🔄 Notionに自動同期開始: {process_id}[/yellow]")
                        if hasattr(self.service.notion_sync_service, 'sync_session_to_notion'):
                            sync_success = self.service.notion_sync_service.sync_session_to_notion(workflow_logger.session_id)
                            if sync_success:
                                console.print(f"[green]✅ Notion自動同期完了: {process_id}[/green]")
                            else:
                                console.print(f"[red]❌ Notion自動同期失敗: {process_id}[/red]")
                        else:
                            console.print("[yellow]⚠️ Notion同期メソッドが利用できません。スキップします。[/yellow]")
                    except Exception as sync_err:
                        logger.warning(f"Notion auto-sync failed: {sync_err}")
                        console.print(f"[red]❌ Notion自動同期エラー: {sync_err}[/red]")
                
                # ワークフローロガーを削除
                del self.service.workflow_loggers[process_id]
                console.print(f"[cyan]Workflow logger cleaned up for completed process {process_id}[/cyan]")
                
            except Exception as e:
                logger.error(f"Failed to finalize workflow logger for process {process_id}: {e}")
                # エラーでもロガーは削除してメモリリークを防ぐ
                if process_id in self.service.workflow_loggers:
                    del self.service.workflow_loggers[process_id]

    # 追加のステップ処理メソッド（簡略化された実装）
    async def handle_research_plan_generated_step(self, context: ArticleContext, process_id: Optional[str] = None, user_id: Optional[str] = None):
        """リサーチ計画生成完了ステップの処理"""
        # ユーザー入力処理の実装（簡略化）
        console.print("[cyan]リサーチ計画承認待ち[/cyan]")

    async def handle_research_plan_approved_step(self, context: ArticleContext, process_id: Optional[str] = None, user_id: Optional[str] = None):
        """リサーチ計画承認ステップの処理"""
        context.current_step = "researching"
        console.print("リサーチ実行ステップに進みます...")
        
        # データベースに現在の状態を保存
        if process_id and user_id:
            try:
                await self.service.persistence_service.save_context_to_db(context, process_id=process_id, user_id=user_id)
                logger.info("Context saved successfully after research plan approval step")
            except Exception as save_err:
                logger.error(f"Failed to save context after research plan approval step: {save_err}")
        
        await self.service.utils.send_server_event(context, StatusUpdatePayload(
            step=context.current_step, 
            message="Moving to research execution.", 
            image_mode=getattr(context, 'image_mode', False)
        ))

    async def handle_researching_step(self, context: ArticleContext, run_config: RunConfig, process_id: Optional[str] = None, user_id: Optional[str] = None):
        """リサーチ実行ステップの処理"""
        if not context.research_plan or not hasattr(context.research_plan, 'queries'):
            await self.service.utils.send_error(context, "リサーチ計画がありません。リサーチをスキップします。")
            context.current_step = "error"
            return

        # 重複実行防止チェック
        if context.executing_step == "researching":
            console.print("[yellow]リサーチは既に実行中です。スキップします。[/yellow]")
            await asyncio.sleep(1)
            return
        
        context.executing_step = "researching"
        
        try:
            # Initialize research query results if not exists
            if not hasattr(context, 'research_query_results'):
                context.research_query_results = []
            
            total_queries = len(context.research_plan.queries)
            console.print(f"[cyan]🚀 {total_queries}件のリサーチクエリを並列実行します...[/cyan]")
            
            # Create tasks for parallel execution with WebSocket progress updates
            async def execute_query_with_websocket_progress(query, query_index: int):
                """Execute a single research query with WebSocket progress reporting"""
                try:
                    console.print(f"🔍 クエリ {query_index+1}/{total_queries}: {query.query if hasattr(query, 'query') else str(query)}")
                    
                    # Send research progress update
                    if context.websocket:
                        await self.service.utils.send_server_event(context, ResearchProgressPayload(
                            current_query=query_index + 1,
                            total_queries=total_queries,
                            query=query.query if hasattr(query, 'query') else str(query),
                            progress_percentage=int((query_index / total_queries) * 100)
                        ))
                    
                    # Execute research query
                    current_agent = researcher_agent
                    agent_input = f"以下のクエリについて詳細にリサーチしてください: {query.query if hasattr(query, 'query') else str(query)}"
                    agent_output = await self.run_agent(current_agent, agent_input, context, run_config)

                    if isinstance(agent_output, ResearchQueryResult):
                        console.print(f"[green]✅ クエリ {query_index+1} が完了しました。[/green]")
                        return query_index, agent_output, True
                    else:
                        console.print(f"[yellow]⚠️ クエリ {query_index+1} で予期しないエージェント出力タイプを受け取りました: {type(agent_output)}[/yellow]")
                        return query_index, None, False
                        
                except Exception as e:
                    console.print(f"[red]❌ クエリ {query_index+1} でエラーが発生: {e}[/red]")
                    logger.error(f"Error in research query {query_index + 1}: {e}")
                    return query_index, None, False
            
            # Execute all queries in parallel
            tasks = [
                execute_query_with_websocket_progress(query, i) 
                for i, query in enumerate(context.research_plan.queries)
            ]
            
            # Wait for all queries to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results in original order
            successful_queries = 0
            failed_queries = []
            
            # Sort results by query_index to maintain order
            sorted_results = []
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Research query failed with exception: {result}")
                    failed_queries.append(str(result))
                elif isinstance(result, tuple):
                    query_index, agent_output, success = result
                    sorted_results.append((query_index, agent_output, success))
                    if success:
                        successful_queries += 1
                    else:
                        failed_queries.append(f"Query {query_index + 1}")
            
            # Sort by query_index and add successful results to context
            sorted_results.sort(key=lambda x: x[0])
            for query_index, agent_output, success in sorted_results:
                if success and agent_output:
                    context.research_query_results.append(agent_output)
            
            console.print(f"[cyan]🎉 並列リサーチ完了: {successful_queries}/{total_queries} 成功[/cyan]")
            
            # Check if we have any successful results
            if successful_queries == 0:
                console.print("[red]❌ 全てのリサーチクエリが失敗しました。[/red]")
                context.current_step = "error"
                context.executing_step = None
                await self.service.utils.send_error(context, "All research queries failed")
                return
            
            # Move to synthesis step
            context.current_step = "research_synthesizing"
            context.executing_step = None
            console.print(f"[green]{len(context.research_query_results)}件のリサーチが完了しました。統合ステップに進みます。[/green]")
            
            # Save context after research completion
            if process_id and user_id:
                try:
                    await self.service.persistence_service.save_context_to_db(context, process_id=process_id, user_id=user_id)
                    logger.info("Context saved successfully after research completion")
                except Exception as save_err:
                    logger.error(f"Failed to save context after research completion: {save_err}")
            
            await self.service.utils.send_server_event(context, StatusUpdatePayload(
                step=context.current_step, 
                message=f"Research completed ({successful_queries}/{total_queries} successful), proceeding to synthesis.", 
                image_mode=getattr(context, 'image_mode', False)
            ))
            
        except Exception as e:
            context.executing_step = None
            await self.service.utils.send_error(context, f"リサーチ実行中にエラーが発生しました: {str(e)}")
            context.current_step = "error"

    async def execute_research_synthesizing_background(self, context: "ArticleContext", run_config: RunConfig):
        """リサーチ統合のバックグラウンド実行"""
        if not context.research_query_results:
            console.print("[red]リサーチ結果がありません。合成をスキップします。[/red]")
            context.current_step = "error"
            return

        current_agent = research_synthesizer_agent
        agent_input = f"テーマ: {context.selected_theme.title}\nリサーチ結果: {json.dumps([r.model_dump() for r in context.research_query_results], indent=2)}"
        console.print(f"🤖 {current_agent.name} にリサーチ結果の統合を依頼します...")
        agent_output = await self.run_agent(current_agent, agent_input, context, run_config)

        if isinstance(agent_output, ResearchReport):
            context.research_report = agent_output
            console.print("[cyan]リサーチ報告書が完成しました。[/cyan]")
            
            # Publish research synthesis completion event for Supabase Realtime
            try:
                from .flow_service import get_supabase_client
                supabase = get_supabase_client()
                
                result = supabase.rpc('create_process_event', {
                    'p_process_id': getattr(context, 'process_id', 'unknown'),
                    'p_event_type': 'research_synthesis_completed',
                    'p_event_data': {
                        'step': 'research_synthesizing',
                        'message': 'Research synthesis completed successfully',
                        'report_summary': getattr(agent_output, 'summary', ''),
                        'key_findings_count': len(getattr(agent_output, 'key_findings', [])),
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    },
                    'p_event_category': 'step_completion',
                    'p_event_source': 'flow_manager'
                }).execute()
                
                if result.data:
                    logger.info(f"Published research_synthesis_completed event for process {getattr(context, 'process_id', 'unknown')}")
                    
            except Exception as e:
                logger.error(f"Error publishing research_synthesis_completed event: {e}")
            
            context.current_step = "outline_generating"
            
            if context.websocket:
                from app.domains.seo_article.schemas import ResearchReportData, KeyPointData
                
                # Convert research report to the expected format
                key_points = []
                if hasattr(agent_output, 'key_findings') and agent_output.key_findings:
                    for finding in agent_output.key_findings:
                        key_points.append(KeyPointData(
                            point=finding if isinstance(finding, str) else str(finding),
                            supporting_sources=[]  # Will be empty for now
                        ))
                
                report_data = ResearchReportData(
                    topic=context.selected_theme.title if context.selected_theme else "Research Topic",
                    overall_summary=getattr(agent_output, 'summary', ''),
                    key_points=key_points,
                    interesting_angles=[],  # Will be empty for now  
                    all_sources=[]  # Will be empty for now
                )
                
                await self.service.utils.send_server_event(context, ResearchCompletePayload(
                    report=report_data
                ))
        else:
            console.print("[red]リサーチ合成中に予期しないエージェント出力タイプを受け取りました。[/red]")
            context.current_step = "error"

    async def execute_outline_generating_background(self, context: "ArticleContext", run_config: RunConfig):
        """アウトライン生成のバックグラウンド実行"""
        if not context.research_report:
            console.print("[red]リサーチ報告書がありません。アウトライン生成をスキップします。[/red]")
            context.current_step = "error"
            return

        # Publish outline generation start event for Supabase Realtime
        try:
            from .flow_service import get_supabase_client
            supabase = get_supabase_client()
            
            result = supabase.rpc('create_process_event', {
                'p_process_id': getattr(context, 'process_id', 'unknown'),
                'p_event_type': 'outline_generation_started',
                'p_event_data': {
                    'step': 'outline_generating',
                    'message': 'Outline generation started',
                    'theme_title': getattr(context.selected_theme, 'title', 'Unknown'),
                    'target_length': context.target_length,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                },
                'p_event_category': 'step_start',
                'p_event_source': 'flow_manager'
            }).execute()
            
            if result.data:
                logger.info(f"Published outline_generation_started event for process {getattr(context, 'process_id', 'unknown')}")
                
        except Exception as e:
            logger.error(f"Error publishing outline_generation_started event: {e}")

        current_agent = outline_agent
        agent_input = f"テーマ: {context.selected_theme.title}\nペルソナ: {context.selected_detailed_persona}\nリサーチ報告書: {context.research_report.model_dump_json(indent=2)}\n目標文字数: {context.target_length}"
        console.print(f"🤖 {current_agent.name} にアウトライン生成を依頼します...")
        agent_output = await self.run_agent(current_agent, agent_input, context, run_config)

        if isinstance(agent_output, Outline):
            context.generated_outline = agent_output
            context.current_step = "outline_generated"
            console.print(f"[cyan]アウトライン（{len(agent_output.sections)}セクション）を生成しました。[/cyan]")
            
            # CRITICAL FIX: Save context to database IMMEDIATELY after outline generation
            # This ensures the generated outline is persisted and survives page reloads
            process_id = getattr(context, 'process_id', None)
            user_id = getattr(context, 'user_id', None)
            
            if process_id and user_id and hasattr(self.service, 'persistence_service'):
                try:
                    await self.service.persistence_service.save_context_to_db(
                        context, process_id=process_id, user_id=user_id
                    )
                    logger.info(f"✅ Context with generated outline saved to DB for process {process_id}")
                except Exception as save_err:
                    logger.error(f"❌ Failed to save context after outline generation: {save_err}")
            else:
                logger.warning(f"⚠️ Cannot save context - missing process_id: {process_id}, user_id: {user_id}, or persistence_service")
            
            # Publish outline generation completion event for Supabase Realtime
            try:
                from .flow_service import get_supabase_client
                supabase = get_supabase_client()
                
                result = supabase.rpc('create_process_event', {
                    'p_process_id': getattr(context, 'process_id', 'unknown'),
                    'p_event_type': 'outline_generation_completed',
                    'p_event_data': {
                        'step': 'outline_generated',
                        'message': 'Outline generation completed successfully',
                        'outline_title': agent_output.title,
                        'sections_count': len(agent_output.sections),
                        'suggested_tone': getattr(agent_output, 'suggested_tone', ''),
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    },
                    'p_event_category': 'step_completion',
                    'p_event_source': 'flow_manager'
                }).execute()
                
                if result.data:
                    logger.info(f"Published outline_generation_completed event for process {getattr(context, 'process_id', 'unknown')}")
                    
            except Exception as e:
                logger.error(f"Error publishing outline_generation_completed event: {e}")
        else:
            console.print("[red]アウトライン生成中に予期しないエージェント出力タイプを受け取りました。[/red]")
            context.current_step = "error"

    async def execute_writing_sections_background(self, context: "ArticleContext", run_config: RunConfig):
        """セクション執筆のバックグラウンド実行"""
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
            
            # Publish section start event for background processing
            try:
                from .flow_service import get_supabase_client
                supabase = get_supabase_client()
                
                result = supabase.rpc('create_process_event', {
                    'p_process_id': getattr(context, 'process_id', 'unknown'),
                    'p_event_type': 'section_writing_started',
                    'p_event_data': {
                        'step': 'writing_sections',
                        'section_index': i,
                        'section_heading': section.heading,
                        'total_sections': total_sections,
                        'image_mode': is_image_mode,
                        'message': f'Started writing section {i + 1}: {section.heading}',
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    },
                    'p_event_category': 'section_progress',
                    'p_event_source': 'flow_manager_background'
                }).execute()
                
                if result.data:
                    logger.info(f"Published section_writing_started event for section {i + 1} (background)")
                    
            except Exception as e:
                logger.error(f"Error publishing section_writing_started event: {e}")
            
            # コンテキストの現在のセクションインデックスを設定
            context.current_section_index = i
            
            # 画像モードに応じてエージェントを選択
            if is_image_mode:
                current_agent = section_writer_with_images_agent
                console.print(f"[cyan]画像プレースホルダー対応エージェント ({current_agent.name}) を使用します。[/cyan]")
            else:
                current_agent = section_writer_agent
                console.print(f"[cyan]通常エージェント ({current_agent.name}) を使用します。[/cyan]")
            
            # エージェント実行に必要な情報をコンテキストに設定（会話履歴を活用）
            user_request = (
                f"前のセクション（もしあれば）に続けて、アウトラインのセクション {i + 1}"
                f"「{section.heading}」の内容をHTMLで執筆してください。提供された詳細リサーチ情報を参照し、"
                f""
            )
            current_input_messages: List[Dict[str, Any]] = list(context.section_writer_history)
            current_input_messages.append({
                "role": "user",
                "content": [{"type": "input_text", "text": user_request}]
            })
            agent_input = current_input_messages
            agent_output = await self.run_agent(current_agent, agent_input, context, run_config)

            # 出力処理
            section_content_length = 0
            if is_image_mode and isinstance(agent_output, ArticleSectionWithImages):
                # ArticleSectionWithImagesをArticleSectionに変換
                article_section = ArticleSection(
                    title=agent_output.title,
                    content=agent_output.content,
                    order=agent_output.order
                )
                context.generated_sections.append(article_section)
                section_content_length = len(agent_output.content)
                
                # 画像プレースホルダー情報をコンテキストに保存
                if not hasattr(context, 'image_placeholders'):
                    context.image_placeholders = []
                context.image_placeholders.extend(agent_output.image_placeholders)
                
                console.print(f"[green]セクション {i+1} が完了しました（画像プレースホルダー {len(agent_output.image_placeholders)} 個含む）。[/green]")
                
            elif not is_image_mode and isinstance(agent_output, ArticleSection):
                context.generated_sections.append(agent_output)
                section_content_length = len(agent_output.content)
                console.print(f"[green]セクション {i+1} が完了しました。[/green]")
                
            elif isinstance(agent_output, str):
                # 従来のHTML文字列形式の場合（旧形式対応）
                article_section = ArticleSection(
                    title=section.heading,
                    content=agent_output,
                    order=i
                )
                context.generated_sections.append(article_section)
                section_content_length = len(agent_output)
                console.print(f"[green]セクション {i+1} が完了しました（HTML文字列形式）。[/green]")
                
            else:
                console.print(f"[red]セクション {i+1} で予期しないエージェント出力タイプを受け取りました: {type(agent_output)}[/red]")
                context.current_step = "error"
                return
            
            # 会話履歴の追記（user → assistant）
            try:
                # 直前に積んだユーザー指示を履歴に反映
                context.add_to_section_writer_history("user", user_request)
                # アシスタント出力をテキスト化
                assistant_content = (
                    agent_output.content if hasattr(agent_output, 'content') else (
                        agent_output if isinstance(agent_output, str) else ''
                    )
                )
                if assistant_content:
                    context.add_to_section_writer_history("assistant", assistant_content)
            except Exception as _:
                # 履歴追記の失敗は致命的ではないため握りつぶす
                pass

            # セクションインデックスを完了に合わせて更新（統一）
            context.current_section_index = i + 1

            # Publish section completion event for background processing
            try:
                from .flow_service import get_supabase_client
                supabase = get_supabase_client()
                
                result = supabase.rpc('create_process_event', {
                    'p_process_id': getattr(context, 'process_id', 'unknown'),
                    'p_event_type': 'section_completed',
                    'p_event_data': {
                        'step': 'writing_sections',
                        'section_index': i,
                        'section_heading': section.heading,
                        'section_content': (
                            agent_output.content if hasattr(agent_output, 'content') else (
                                agent_output if isinstance(agent_output, str) else ''
                            )
                        ),
                        'section_content_length': section_content_length,
                        'completed_sections': i + 1,
                        'total_sections': total_sections,
                        'image_mode': is_image_mode,
                        'placeholders_count': len(getattr(agent_output, 'image_placeholders', [])) if hasattr(agent_output, 'image_placeholders') else 0,
                        'image_placeholders': [
                            {
                                'placeholder_id': p.placeholder_id,
                                'description_jp': p.description_jp,
                                'prompt_en': p.prompt_en,
                                'alt_text': p.alt_text,
                            }
                            for p in getattr(agent_output, 'image_placeholders', [])
                        ] if is_image_mode else [],
                        'message': f'Completed section {i + 1}: {section.heading}',
                        'progress_percentage': int(((i + 1) / total_sections) * 100),
                        'batch_completion': True,
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    },
                    'p_event_category': 'section_completion',
                    'p_event_source': 'flow_manager_background'
                }).execute()
                
                if result.data:
                    logger.info(f"Published section_completed event for section {i + 1} (background)")
                    
            except Exception as e:
                logger.error(f"Error publishing section_completed event: {e}")

        # 全セクション完了
        context.current_step = "editing"
        console.print("[cyan]全セクションの執筆が完了しました。[/cyan]")
        
        # Publish all sections completion event
        try:
            from .flow_service import get_supabase_client
            supabase = get_supabase_client()
            
            result = supabase.rpc('create_process_event', {
                'p_process_id': getattr(context, 'process_id', 'unknown'),
                'p_event_type': 'all_sections_completed',
                'p_event_data': {
                    'step': 'writing_sections',
                    'total_sections': total_sections,
                    'image_mode': is_image_mode,
                    'total_content_length': sum(len(getattr(s, 'content', '')) for s in context.generated_sections),
                    'total_placeholders': len(getattr(context, 'image_placeholders', [])),
                    'message': f'All {total_sections} sections completed successfully',
                    'next_step': 'editing',
                    'timestamp': datetime.now(timezone.utc).isoformat()
                },
                'p_event_category': 'step_completion',
                'p_event_source': 'flow_manager_background'
            }).execute()
            
            if result.data:
                logger.info(f"Published all_sections_completed event for {total_sections} sections")
                
        except Exception as e:
            logger.error(f"Error publishing all_sections_completed event: {e}")

    async def execute_editing_background(self, context: "ArticleContext", run_config: RunConfig, process_id: Optional[str] = None, user_id: Optional[str] = None):
        """編集のバックグラウンド実行"""
        if not context.generated_sections_html:
            console.print("[red]生成されたセクションがありません。編集をスキップします。[/red]")
            context.current_step = "error"
            return

        current_agent = editor_agent
        combined_content = "\n\n".join([section for section in context.generated_sections_html if section and section.strip()])
        agent_input = f"タイトル: {context.generated_outline.title}\nコンテンツ: {combined_content}\nペルソナ: {context.selected_detailed_persona}\n目標文字数: {context.target_length}"
        console.print(f"🤖 {current_agent.name} に最終編集を依頼します...")
        
        if context.websocket:
            await self.service.utils.send_server_event(context, EditingStartPayload(message="記事の最終編集を開始しています..."))
        
        agent_output = await self.run_agent(current_agent, agent_input, context, run_config)

        if isinstance(agent_output, RevisedArticle):
            context.final_article = agent_output
            context.final_article_html = agent_output.content
            context.current_step = "completed"
            await self.log_workflow_step(context, "completed", {
                "final_article_length": len(agent_output.content),
                "sections_count": len(context.generated_sections) if hasattr(context, 'generated_sections') else 0,
                "total_tokens_used": getattr(context, 'total_tokens_used', 0)
            })
            console.print("[green]記事の編集が完了しました！[/green]")
            
            # Save context to database if available
            if process_id and user_id:
                try:
                    await self.service.persistence_service.save_context_to_db(context, process_id=process_id, user_id=user_id)
                    logger.info("Context saved successfully after article editing")
                except Exception as save_err:
                    logger.error(f"Failed to save context after article editing: {save_err}")
            
            # ワークフローロガーを最終化（記事編集完了）
            if process_id:
                await self.finalize_workflow_logger(process_id, "completed")
            elif hasattr(context, 'process_id') and context.process_id:
                await self.finalize_workflow_logger(context.process_id, "completed")
        elif isinstance(agent_output, str):
            # EditorAgent returns HTML directly as string
            context.final_article_html = agent_output
            context.current_step = "completed"
            await self.log_workflow_step(context, "completed", {
                "final_article_length": len(agent_output),
                "sections_count": len(context.generated_sections_html) if hasattr(context, 'generated_sections_html') else 0,
                "total_tokens_used": getattr(context, 'total_tokens_used', 0)
            })
            console.print("[green]記事の編集が完了しました！[/green]")
            
            # Save context to database if available
            if process_id and user_id:
                try:
                    await self.service.persistence_service.save_context_to_db(context, process_id=process_id, user_id=user_id)
                    logger.info("Context saved successfully after article editing")
                except Exception as save_err:
                    logger.error(f"Failed to save context after article editing: {save_err}")
            
            # ワークフローロガーを最終化（記事編集完了）
            if process_id:
                await self.finalize_workflow_logger(process_id, "completed")
            elif hasattr(context, 'process_id') and context.process_id:
                await self.finalize_workflow_logger(context.process_id, "completed")
        else:
            console.print(f"[red]編集中に予期しないエージェント出力タイプを受け取りました: {type(agent_output)}[/red]")
            context.current_step = "error"

# ============================================================================
    # 省略されていたステップ処理メソッドの完全実装
    # ============================================================================

    async def handle_research_synthesizing_step(self, context: ArticleContext, run_config: RunConfig, process_id: Optional[str] = None, user_id: Optional[str] = None):
        """リサーチ統合ステップの処理"""
        current_agent = research_synthesizer_agent
        agent_input = "収集された詳細なリサーチ結果を分析し、記事執筆のための詳細な要約レポートを作成してください。"
        console.print(f"🤖 {current_agent.name} に詳細リサーチ結果の要約を依頼します...")
        agent_output = await self.run_agent(current_agent, agent_input, context, run_config)

        if isinstance(agent_output, ResearchReport):
            context.research_report = agent_output
            context.current_step = "research_report_generated"
            console.print("[green]リサーチレポートを生成しました。[/green]")
            
            # WebSocketでレポートを送信（承認は求めず、情報提供のみ）
            from app.domains.seo_article.schemas import ResearchReportData, KeyPointData
            
            # Convert research report to the expected format
            key_points = []
            if hasattr(agent_output, 'key_findings') and agent_output.key_findings:
                for finding in agent_output.key_findings:
                    key_points.append(KeyPointData(
                        point=finding if isinstance(finding, str) else str(finding),
                        supporting_sources=[]  # Will be empty for now
                    ))
            
            report_data = ResearchReportData(
                topic=context.selected_theme.title if context.selected_theme else "Research Topic",
                overall_summary=getattr(agent_output, 'summary', ''),
                key_points=key_points,
                interesting_angles=[],  # Will be empty for now  
                all_sources=[]  # Will be empty for now
            )
            
            await self.service.utils.send_server_event(context, ResearchCompletePayload(
                report=report_data
            ))
            
            # Save context after research report generation
            if process_id and user_id:
                try:
                    await self.service.persistence_service.save_context_to_db(context, process_id=process_id, user_id=user_id)
                    logger.info("Context saved successfully after research report generation")
                except Exception as save_err:
                    logger.error(f"Failed to save context after research report generation: {save_err}")
            
            # すぐにアウトライン生成へ
            context.current_step = "outline_generating"
            await self.service.utils.send_server_event(context, StatusUpdatePayload(
                step=context.current_step, 
                message="Research report generated, generating outline.", 
                image_mode=getattr(context, 'image_mode', False)
            ))
        else:
            await self.service.utils.send_error(context, f"リサーチ合成中に予期しないエージェント出力タイプ ({type(agent_output)}) を受け取りました。")
            context.current_step = "error"

    async def handle_outline_generating_step(self, context: ArticleContext, run_config: RunConfig, process_id: Optional[str] = None, user_id: Optional[str] = None):
        """アウトライン生成ステップの処理"""
        current_agent = outline_agent
        if not context.research_report:
            await self.service.utils.send_error(context, "リサーチレポートがありません。アウトライン作成をスキップします。", "outline_generating")
            context.current_step = "error"
            return
        
        instruction_text = f"詳細リサーチレポートに基づいてアウトラインを作成してください。テーマ: {context.selected_theme.title if context.selected_theme else '未選択'}, 目標文字数 {context.target_length or '指定なし'}"
        research_report_json_str = json.dumps(context.research_report.model_dump(), indent=2)

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
        agent_output = await self.run_agent(current_agent, agent_input_list_for_outline, context, run_config)

        if isinstance(agent_output, Outline):
            context.generated_outline = agent_output
            context.current_step = "outline_generated"
            console.print("[cyan]アウトラインを生成しました。クライアントの承認/編集/再生成を待ちます...[/cyan]")
            
            # Save context after outline generation
            if process_id and user_id:
                try:
                    await self.service.persistence_service.save_context_to_db(context, process_id=process_id, user_id=user_id)
                    logger.info("Context saved successfully after outline generation")
                except Exception as save_err:
                    logger.error(f"Failed to save context after outline generation: {save_err}")
            
            await self.handle_outline_generated_step(context, process_id, user_id)
        elif isinstance(agent_output, ClarificationNeeded):
            await self.service.utils.send_error(context, f"アウトライン生成で確認が必要になりました: {agent_output.message}")
            context.current_step = "error"
        else:
            await self.service.utils.send_error(context, f"アウトライン生成中に予期しないエージェント出力タイプ ({type(agent_output)}) を受け取りました。")
            context.current_step = "error"

    async def handle_outline_generated_step(self, context: ArticleContext, process_id: Optional[str] = None, user_id: Optional[str] = None):
        """アウトライン生成完了ステップの処理"""
        if context.generated_outline:
            outline_data_for_client = context.generated_outline
            
            # CRITICAL FIX: Set step to completed state and mark waiting for input using RPC
            # This ensures DB state is persistent and survives page reloads
            if process_id and user_id:
                try:
                    from app.domains.seo_article.services.flow_service import get_supabase_client
                    
                    # 1) Ensure current_step_name is set to completion state
                    context.current_step = "outline_generated"
                    await self.service.persistence_service.update_process_state(
                        process_id=process_id,
                        current_step_name="outline_generated"
                    )
                    
                    # 2) Save context with generated outline to DB
                    await self.service.persistence_service.save_context_to_db(
                        context, process_id=process_id, user_id=user_id
                    )
                    
                    # 3) Mark process waiting for input using RPC (triggers events and Realtime)
                    supabase = get_supabase_client()
                    await supabase.rpc(
                        'mark_process_waiting_for_input',
                        {'p_process_id': process_id, 'p_input_type': 'approve_outline', 'p_timeout_minutes': 60}
                    ).execute()
                    
                    logger.info("Process state marked waiting for outline approval with RPC")
                except Exception as save_err:
                    logger.error(f"Failed to mark process waiting for outline approval: {save_err}")
            
            user_response_message = await self.service.utils.request_user_input(
                context,
                UserInputType.APPROVE_OUTLINE,
                OutlinePayload(outline=outline_data_for_client).model_dump()
            )
            
            if user_response_message:
                response_type = user_response_message.response_type
                payload_dict = user_response_message.payload
                payload = self.service.utils.convert_payload_to_model(payload_dict, response_type)

                if response_type == UserInputType.APPROVE_OUTLINE and payload and isinstance(payload, ApprovePayload):
                    if payload.approved:
                        context.current_step = "outline_approved"
                        console.print("[green]クライアントがアウトラインを承認しました。[/green]")
                        await self.service.utils.send_server_event(context, StatusUpdatePayload(
                            step=context.current_step, 
                            message="Outline approved, proceeding to writing.", 
                            image_mode=getattr(context, 'image_mode', False)
                        ))
                        
                        # Save context after outline approval
                        if process_id and user_id:
                            try:
                                await self.service.persistence_service.save_context_to_db(context, process_id=process_id, user_id=user_id)
                                logger.info("Context saved successfully after outline approval")
                            except Exception as save_err:
                                logger.error(f"Failed to save context after outline approval: {save_err}")
                    else:
                        console.print("[yellow]クライアントがアウトラインを否認しました。再生成を試みます。[/yellow]")
                        context.current_step = "outline_generating"
                        context.generated_outline = None

                elif response_type == UserInputType.REGENERATE:
                    console.print("[yellow]クライアントがアウトラインの再生成を要求しました。[/yellow]")
                    context.current_step = "outline_generating"
                    context.generated_outline = None

                elif response_type == UserInputType.EDIT_OUTLINE and payload and isinstance(payload, EditOutlinePayload):
                    try:
                        edited_outline_data = payload.edited_outline
                        console.print("[green]アウトラインが編集されました（EditOutlinePayload）。[/green]")
                        # 編集されたアウトラインを適用
                        if (isinstance(edited_outline_data.get("title"), str) and 
                            isinstance(edited_outline_data.get("sections"), list)):
                            edited_sections = []
                            for section_data in edited_outline_data["sections"]:
                                if isinstance(section_data.get("heading"), str):
                                    edited_sections.append(OutlineSectionData(
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
                            await self.service.utils.send_server_event(context, StatusUpdatePayload(
                                step=context.current_step, 
                                message="Edited outline applied and approved.", 
                                image_mode=getattr(context, 'image_mode', False)
                            ))
                            
                            # Save context after outline editing
                            if process_id and user_id:
                                try:
                                    await self.service.persistence_service.save_context_to_db(context, process_id=process_id, user_id=user_id)
                                    logger.info("Context saved successfully after outline editing")
                                except Exception as save_err:
                                    logger.error(f"Failed to save context after outline editing: {save_err}")
                        else:
                            await self.service.utils.send_error(context, "編集されたアウトラインの形式が無効です。")
                            context.current_step = "error"
                    except (ValidationError, TypeError, AttributeError) as e:
                        await self.service.utils.send_error(context, f"アウトライン編集エラー: {e}")
                        context.current_step = "error"

                elif response_type == UserInputType.EDIT_AND_PROCEED and payload and isinstance(payload, EditAndProceedPayload):
                    try:
                        edited_outline_data = payload.edited_content
                        console.print("[green]アウトラインが編集されました（EditAndProceedPayload）。[/green]")
                        # 編集されたアウトラインを適用
                        if (isinstance(edited_outline_data.get("title"), str) and 
                            isinstance(edited_outline_data.get("sections"), list)):
                            edited_sections = []
                            for section_data in edited_outline_data["sections"]:
                                if isinstance(section_data.get("heading"), str):
                                    edited_sections.append(OutlineSectionData(
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
                            await self.service.utils.send_server_event(context, StatusUpdatePayload(
                                step=context.current_step, 
                                message="Edited outline applied and approved.", 
                                image_mode=getattr(context, 'image_mode', False)
                            ))
                            
                            # Save context after outline editing
                            if process_id and user_id:
                                try:
                                    await self.service.persistence_service.save_context_to_db(context, process_id=process_id, user_id=user_id)
                                    logger.info("Context saved successfully after outline editing")
                                except Exception as save_err:
                                    logger.error(f"Failed to save context after outline editing: {save_err}")
                        else:
                            await self.service.utils.send_error(context, "編集されたアウトラインの形式が無効です。")
                            context.current_step = "error"
                    except (ValidationError, TypeError, AttributeError) as e:
                        await self.service.utils.send_error(context, f"アウトライン編集エラー: {e}")
                        context.current_step = "error"

                elif response_type == UserInputType.EDIT_GENERIC:
                    try:
                        # EDIT_GENERIC - generic edit handler for outline step
                        console.print(f"[yellow]EDIT_GENERIC received for outline step. Payload: {payload}[/yellow]")
                        if hasattr(payload, 'edited_content'):
                            edited_outline_data = payload.edited_content
                            if (isinstance(edited_outline_data.get("title"), str) and 
                                isinstance(edited_outline_data.get("sections"), list)):
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
                                await self.service.utils.send_server_event(context, StatusUpdatePayload(
                                    step=context.current_step, 
                                    message="Edited outline applied and approved.", 
                                    image_mode=getattr(context, 'image_mode', False)
                                ))
                                
                                # Save context after outline editing
                                if process_id and user_id:
                                    try:
                                        await self.service.persistence_service.save_context_to_db(context, process_id=process_id, user_id=user_id)
                                        logger.info("Context saved successfully after outline editing")
                                    except Exception as save_err:
                                        logger.error(f"Failed to save context after outline editing: {save_err}")
                            else:
                                await self.service.utils.send_error(context, "EDIT_GENERIC: 編集されたアウトラインの形式が無効です。")
                                context.current_step = "error"
                        else:
                            await self.service.utils.send_error(context, "EDIT_GENERIC: 編集されたアウトラインの形式が無効です。")
                            context.current_step = "error"
                    except Exception as e:
                        await self.service.utils.send_error(context, f"EDIT_GENERIC アウトライン編集エラー: {e}")
                        context.current_step = "error"
                else:
                    await self.service.utils.send_error(context, f"予期しない応答タイプ: {response_type}")
                    context.current_step = "error"
            else:
                console.print("[red]アウトラインの承認/編集でクライアントからの応答がありませんでした。[/red]")
                context.current_step = "error"
        else:
            console.print("[yellow]アウトラインが見つからないため生成ステップに戻します。[/yellow]")
            context.current_step = "outline_generating"

    async def handle_outline_approved_step(self, context: ArticleContext, process_id: Optional[str] = None, user_id: Optional[str] = None):
        """アウトライン承認ステップの処理"""
        console.print("記事執筆ステップに進みます...")
        
        # セクションライティングの初期化（重要：current_section_indexを0にリセット）
        context.current_section_index = 0
        context.generated_sections_html = []
        context.section_writer_history = []
        
        console.print(f"[yellow]セクションライティング初期化: {len(context.generated_outline.sections)}セクションを実行予定[/yellow]")
        
        context.current_step = "writing_sections"
        
        # データベースに現在の状態を保存
        if process_id and user_id:
            try:
                await self.service.persistence_service.save_context_to_db(context, process_id=process_id, user_id=user_id)
                logger.info("Context saved successfully after outline approval step")
            except Exception as save_err:
                logger.error(f"Failed to save context after outline approval step: {save_err}")
        
        await self.service.utils.send_server_event(context, StatusUpdatePayload(
            step=context.current_step, 
            message="Outline approved, starting section writing.", 
            image_mode=getattr(context, 'image_mode', False)
        ))

    async def handle_writing_sections_step(self, context: ArticleContext, run_config: RunConfig, process_id: Optional[str] = None, user_id: Optional[str] = None):
        """セクション執筆ステップの処理"""
        if not context.generated_outline:
            await self.service.utils.send_error(context, "承認済みアウトラインがありません。セクション執筆をスキップします。")
            context.current_step = "error"
            return

        # セクション完了判定を厳密化
        total_sections = len(context.generated_outline.sections)
        
        # セクション完全性をチェック
        if self.service.utils.validate_section_completeness(context, context.generated_outline.sections, total_sections):
            context.current_step = "editing"
            console.print(f"[green]全{total_sections}セクションの執筆が完了しました（{len(context.full_draft_html)}文字）。編集ステップに移ります。[/green]")
            await self.service.utils.send_server_event(context, EditingStartPayload())
            return

        # 画像モードかどうかでエージェントを選択
        is_image_mode = getattr(context, 'image_mode', False)
        
        if is_image_mode:
            current_agent = section_writer_with_images_agent
            console.print(f"[cyan]画像モードが有効: {current_agent.name} を使用[/cyan]")
        else:
            current_agent = section_writer_agent

        target_index = context.current_section_index
        target_heading = context.generated_outline.sections[target_index].heading

        # セクション執筆処理をカスタムスパンでラップ
        with safe_custom_span("section_writing", data={
            "section_index": str(target_index),
            "section_heading": target_heading,
            "total_sections": str(len(context.generated_outline.sections))
        }):
            user_request = f"前のセクション（もしあれば）に続けて、アウトラインのセクション {target_index + 1}「{target_heading}」の内容をHTMLで執筆してください。"
            current_input_messages: List[Dict[str, Any]] = list(context.section_writer_history)
            current_input_messages.append({"role": "user", "content": [{"type": "input_text", "text": user_request}]})
            agent_input = current_input_messages

            # 画像モードの場合は通常のエージェント実行、そうでなければストリーミング実行
            if is_image_mode:
                # 画像モード: 通常のエージェント実行（structured output対応）
                console.print(f"🤖 {current_agent.name} にセクション {target_index + 1} の執筆を依頼します (画像モード)...")
                await self.service.utils.send_server_event(context, StatusUpdatePayload(
                    step=context.current_step, 
                    message=f"Writing section {target_index + 1}: {target_heading} (with images)", 
                    image_mode=True
                ))
                
                agent_output = await self.run_agent(current_agent, agent_input, context, run_config)
                
                if isinstance(agent_output, ArticleSectionWithImages):
                    # 画像プレースホルダーが含まれている場合はログ出力するが、必須ではない
                    if agent_output.image_placeholders and len(agent_output.image_placeholders) > 0:
                        console.print(f"[cyan]セクション {target_index + 1} に画像プレースホルダーが含まれています: {len(agent_output.image_placeholders)}個[/cyan]")
                    else:
                        console.print(f"[yellow]セクション {target_index + 1} には画像プレースホルダーが含まれていません（記事全体で1つ以上あれば問題ありません）[/yellow]")
                    
                    generated_section = ArticleSection(
                        title=target_heading, 
                        content=agent_output.content, 
                        order=target_index
                    )
                    console.print(f"[green]セクション {target_index + 1}「{generated_section.title}」を画像プレースホルダー付きで生成しました。（{len(agent_output.content)}文字、画像{len(agent_output.image_placeholders)}個）[/green]")
                    
                    # 画像プレースホルダー情報をコンテキストに保存
                    if not hasattr(context, 'image_placeholders'):
                        context.image_placeholders = []
                    context.image_placeholders.extend(agent_output.image_placeholders)
                    
                    # プレースホルダー情報をデータベースに保存
                    await self.service.persistence_service.save_image_placeholders_to_db(context, agent_output.image_placeholders, target_index)
                    
                    # セクション内容をcontextに保存
                    if len(context.generated_sections_html) <= target_index:
                        context.generated_sections_html.extend([""] * (target_index + 1 - len(context.generated_sections_html)))
                    
                    context.generated_sections_html[target_index] = generated_section.content
                    context.last_agent_output = generated_section
                    
                    # 会話履歴更新
                    last_user_request_item = agent_input[-1] if isinstance(agent_input, list) else None
                    if last_user_request_item and last_user_request_item.get('role') == 'user':
                        user_request_text = last_user_request_item['content'][0]['text']
                        context.add_to_section_writer_history("user", user_request_text)
                    context.add_to_section_writer_history("assistant", generated_section.content)
                    
                    # セクション完了後にインデックスを更新
                    context.current_section_index = target_index + 1
                    
                    # Save context after each section completion（必須）
                    if process_id and user_id:
                        try:
                            await self.service.persistence_service.save_context_to_db(context, process_id=process_id, user_id=user_id)
                            logger.info(f"Context saved successfully after section {context.current_section_index}/{len(context.generated_outline.sections)} completion")
                        except Exception as save_err:
                            logger.error(f"Failed to save context after section completion: {save_err}")
                    
                    console.print(f"[blue]セクション {target_index + 1} 完了。次のセクション: {context.current_section_index + 1}[/blue]")
                    
                    # WebSocketでセクション完了を通知（画像モード）
                    if context.websocket:
                        try:
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
                                section_complete_content=generated_section.content,
                                image_placeholders=image_placeholders_data,
                                is_image_mode=True
                            )
                            console.print(f"[cyan]📤 Sending SectionChunkPayload for image mode: section_index={target_index}, heading='{target_heading}', is_image_mode=True, content_length={len(generated_section.content)}, placeholders={len(image_placeholders_data)}[/cyan]")
                            await self.service.utils.send_server_event(context, payload)
                            console.print(f"[green]✅ SectionChunkPayload sent successfully for section {target_index}[/green]")
                        except Exception as e:
                            console.print(f"[red]❌ Failed to send SectionChunkPayload for section {target_index}: {e}[/red]")
                    else:
                        console.print(f"[yellow]⚠️ No WebSocket connection available for section {target_index} notification[/yellow]")
                else:
                    await self.service.utils.send_error(context, f"画像モードで予期しないAgent出力タイプ: {type(agent_output)}")
                    context.current_step = "error"
            else:
                # 通常モード: バッチ実行 (Converted from streaming to batch processing)
                console.print(f"🤖 {current_agent.name} にセクション {target_index + 1} の執筆を依頼します (Batch)...")
                await self.service.utils.send_server_event(context, StatusUpdatePayload(
                    step=context.current_step, 
                    message=f"Writing section {target_index + 1}: {target_heading}", 
                    image_mode=False
                ))

                # Publish section start event for Supabase Realtime
                try:
                    from .flow_service import get_supabase_client
                    supabase = get_supabase_client()
                    
                    result = supabase.rpc('create_process_event', {
                        'p_process_id': getattr(context, 'process_id', 'unknown'),
                        'p_event_type': 'section_writing_started',
                        'p_event_data': {
                            'step': 'writing_sections',
                            'section_index': target_index,
                            'section_heading': target_heading,
                            'total_sections': len(context.generated_outline.sections),
                            'message': f'Started writing section {target_index + 1}: {target_heading}',
                            'timestamp': datetime.now(timezone.utc).isoformat()
                        },
                        'p_event_category': 'section_progress',
                        'p_event_source': 'flow_manager'
                    }).execute()
                    
                    if result.data:
                        logger.info(f"Published section_writing_started event for section {target_index + 1}")
                        
                except Exception as e:
                    logger.error(f"Error publishing section_writing_started event: {e}")

                # バッチ実行 - Use regular Runner.run instead of streaming
                agent_output = await self.run_agent(current_agent, agent_input, context, run_config)

                # セクション内容の処理 - Convert agent output to section
                if isinstance(agent_output, str):
                    # HTML string format (legacy support)
                    from app.domains.seo_article.schemas import ArticleSection
                    generated_section = ArticleSection(
                        title=target_heading,
                        content=agent_output,
                        order=target_index
                    )
                elif hasattr(agent_output, 'content') and hasattr(agent_output, 'title'):
                    # ArticleSection format
                    generated_section = agent_output
                else:
                    # Handle unexpected output format
                    console.print(f"[red]予期しないエージェント出力タイプ: {type(agent_output)}[/red]")
                    generated_section = ArticleSection(
                        title=target_heading,
                        content=str(agent_output),
                        order=target_index
                    )

                # セクション内容をcontextに保存
                if len(context.generated_sections_html) <= target_index:
                    context.generated_sections_html.extend([""] * (target_index + 1 - len(context.generated_sections_html)))
                
                context.generated_sections_html[target_index] = generated_section.content
                context.last_agent_output = generated_section
                
                # 会話履歴更新
                last_user_request_item = agent_input[-1] if isinstance(agent_input, list) else None
                if last_user_request_item and last_user_request_item.get('role') == 'user':
                    user_request_text = last_user_request_item['content'][0]['text']
                    context.add_to_section_writer_history("user", user_request_text)
                context.add_to_section_writer_history("assistant", generated_section.content)
                
                # セクション完了後にインデックスを更新
                context.current_section_index = target_index + 1
                
                # Publish section completion event for Supabase Realtime (batch format)
                try:
                    from .flow_service import get_supabase_client
                    supabase = get_supabase_client()
                    
                    result = supabase.rpc('create_process_event', {
                        'p_process_id': getattr(context, 'process_id', 'unknown'),
                        'p_event_type': 'section_completed',
                        'p_event_data': {
                            'step': 'writing_sections',
                            'section_index': target_index,
                            'section_heading': target_heading,
                            'section_content': generated_section.content,
                            'section_content_length': len(generated_section.content),
                            'completed_sections': context.current_section_index,
                            'total_sections': len(context.generated_outline.sections),
                            'image_placeholders': [
                                {
                                    'placeholder_id': p.placeholder_id,
                                    'description_jp': p.description_jp,
                                    'prompt_en': p.prompt_en,
                                    'alt_text': p.alt_text,
                                }
                                for p in getattr(context, 'image_placeholders', [])
                            ] if getattr(context, 'image_mode', False) else [],
                            'message': f'Completed section {target_index + 1}: {target_heading}',
                            'progress_percentage': int((context.current_section_index / len(context.generated_outline.sections)) * 100),
                            'batch_completion': True,  # Flag to indicate this is batch completion
                            'timestamp': datetime.now(timezone.utc).isoformat()
                        },
                        'p_event_category': 'section_completion',
                        'p_event_source': 'flow_manager'
                    }).execute()
                    
                    if result.data:
                        logger.info(f"Published section_completed event for section {target_index + 1} (batch processing)")
                        
                except Exception as e:
                    logger.error(f"Error publishing section_completed event: {e}")
                
                # Save context after each section completion（必須）
                if process_id and user_id:
                    try:
                        await self.service.persistence_service.save_context_to_db(context, process_id=process_id, user_id=user_id)
                        logger.info(f"Context saved successfully after section {context.current_section_index}/{len(context.generated_outline.sections)} completion")
                    except Exception as save_err:
                        logger.error(f"Failed to save context after section completion: {save_err}")
                        # セーブに失敗しても処理は継続
                
                console.print(f"[blue]セクション {target_index + 1} 完了。次のセクション: {context.current_section_index + 1}[/blue]")
                
                # Send batch section completion event to WebSocket if available (for backward compatibility)
                if context.websocket:
                    try:
                        await self.service.utils.send_server_event(context, SectionChunkPayload(
                            section_index=target_index,
                            heading=target_heading,
                            html_content_chunk=generated_section.content,
                            is_complete=True,
                            batch_mode=True  # Flag to indicate batch completion
                        ))
                    except Exception as ws_err:
                        console.print(f"[dim]WebSocket section completion event error (continuing): {ws_err}[/dim]")

    async def handle_editing_step(self, context: ArticleContext, run_config: RunConfig, process_id: Optional[str] = None, user_id: Optional[str] = None):
        """編集ステップの処理"""
        if not context.generated_sections_html or not any(s.strip() for s in context.generated_sections_html):
            await self.service.utils.send_error(context, "生成されたセクションがありません。編集をスキップします。")
            context.current_step = "error"
            return

        current_agent = editor_agent
        combined_content = "\n\n".join([section for section in context.generated_sections_html if section and section.strip()])
        agent_input = f"タイトル: {context.generated_outline.title}\nコンテンツ: {combined_content}\nペルソナ: {context.selected_detailed_persona}\n目標文字数: {context.target_length}"
        console.print(f"🤖 {current_agent.name} に最終編集を依頼します...")
        
        await self.service.utils.send_server_event(context, EditingStartPayload(message="記事の最終編集を開始しています..."))
        
        agent_output = await self.run_agent(current_agent, agent_input, context, run_config)

        if isinstance(agent_output, RevisedArticle):
            context.final_article = agent_output
            context.current_step = "completed"
            await self.log_workflow_step(context, "completed", {
                "final_article_length": len(agent_output.content),
                "sections_count": len(context.generated_sections_html) if hasattr(context, 'generated_sections_html') else 0,
                "total_tokens_used": getattr(context, 'total_tokens_used', 0)
            })
            console.print("[green]記事の編集が完了しました！[/green]")
            
            # ワークフローロガーを最終化（記事編集完了）
            if hasattr(context, 'process_id') and context.process_id:
                await self.finalize_workflow_logger(context.process_id, "completed")
            
            # Save context after final article completion
            if process_id and user_id:
                try:
                    await self.service.persistence_service.save_context_to_db(context, process_id=process_id, user_id=user_id)
                    logger.info("Context saved successfully after final article completion")
                except Exception as save_err:
                    logger.error(f"Failed to save context after final article completion: {save_err}")

            # --- 1. DBへ保存して article_id を取得 ---
            article_id: Optional[str] = None
            if process_id and user_id:
                try:
                    # 先に保存処理を実行（articles への INSERT を含む）
                    await self.service.persistence_service.save_context_to_db(context, process_id=process_id, user_id=user_id)

                    # 保存後に generated_articles_state から article_id を取得
                    from app.domains.seo_article.services.flow_service import get_supabase_client
                    supabase = get_supabase_client()
                    state_res = supabase.table("generated_articles_state").select("article_id").eq("id", process_id).execute()
                    if state_res.data and state_res.data[0].get("article_id"):
                        article_id = state_res.data[0]["article_id"]
                except Exception as fetch_err:
                    console.print(f"[yellow]Warning: article_id の取得に失敗しました: {fetch_err}[/yellow]")

            # --- 2. WebSocketで最終結果を送信（article_id 付き） ---
            await self.service.utils.send_server_event(context, FinalResultPayload(
                title=agent_output.title,
                final_html_content=agent_output.content,
                article_id=article_id
            ))
        else:
            await self.service.utils.send_error(context, f"編集中に予期しないAgent出力タイプ ({type(agent_output)}) を受け取りました。")
            context.current_step = "error"

    async def handle_user_input_step(self, context: ArticleContext, process_id: Optional[str] = None, user_id: Optional[str] = None):
        """ユーザー入力ステップの汎用処理"""
        from app.common.schemas import UserInputType
        from app.domains.seo_article.schemas import (
            GeneratedPersonasPayload, GeneratedPersonaData,
            ThemeProposalPayload, ThemeProposalData,
            SelectPersonaPayload, SelectThemePayload, ApprovePayload,
            EditAndProceedPayload
        )
        from pydantic import ValidationError
        
        console.print(f"[blue]ユーザー入力ステップを処理中: {context.current_step}[/blue]")
        
        if context.current_step == "persona_generated":
            if context.generated_detailed_personas:
                personas_data_for_client = [GeneratedPersonaData(id=i, description=desc) for i, desc in enumerate(context.generated_detailed_personas)]
                
                user_response_message = await self.service.utils.request_user_input(
                    context,
                    UserInputType.SELECT_PERSONA,
                    GeneratedPersonasPayload(personas=personas_data_for_client).model_dump()
                )
                
                if user_response_message:
                    response_type = user_response_message.response_type
                    payload_dict = user_response_message.payload
                    payload = self.service.utils.convert_payload_to_model(payload_dict, response_type)

                    if response_type == UserInputType.SELECT_PERSONA and payload and isinstance(payload, SelectPersonaPayload):
                        selected_id = payload.selected_id
                        if 0 <= selected_id < len(context.generated_detailed_personas):
                            context.selected_detailed_persona = context.generated_detailed_personas[selected_id]
                            context.current_step = "persona_selected"
                            console.print(f"[green]ペルソナが選択されました: {context.selected_detailed_persona[:100]}...[/green]")
                            await self.service.utils.send_server_event(context, StatusUpdatePayload(
                                step=context.current_step, 
                                message="Persona selected, proceeding to theme generation.", 
                                image_mode=getattr(context, 'image_mode', False)
                            ))
                            
                            # Save context after persona selection
                            if process_id and user_id:
                                try:
                                    await self.service.persistence_service.save_context_to_db(context, process_id=process_id, user_id=user_id)
                                    logger.info("Context saved successfully after persona selection")
                                except Exception as save_err:
                                    logger.error(f"Failed to save context after persona selection: {save_err}")
                        else:
                            await self.service.utils.send_error(context, f"無効なペルソナインデックス: {selected_id}")
                            context.current_step = "error"
                    elif response_type == UserInputType.REGENERATE:
                        console.print("[yellow]ペルソナの再生成が要求されました。[/yellow]")
                        context.current_step = "persona_generating"
                        context.generated_detailed_personas = []
                    elif response_type == UserInputType.EDIT_AND_PROCEED and payload and isinstance(payload, EditAndProceedPayload):
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
                                await self.service.utils.send_server_event(context, StatusUpdatePayload(
                                    step=context.current_step, 
                                    message="Persona edited and selected.", 
                                    image_mode=getattr(context, 'image_mode', False)
                                ))
                                
                                # Save context after persona editing
                                if process_id and user_id:
                                    try:
                                        await self.service.persistence_service.save_context_to_db(context, process_id=process_id, user_id=user_id)
                                        logger.info("Context saved successfully after persona editing")
                                    except Exception as save_err:
                                        logger.error(f"Failed to save context after persona editing: {save_err}")
                            else:
                                await self.service.utils.send_error(context, f"編集されたペルソナの形式が無効です。受信データ: {edited_persona_data}")
                                context.current_step = "error"
                        except (ValidationError, TypeError, AttributeError) as e:
                            await self.service.utils.send_error(context, f"ペルソナ編集エラー: {e}")
                            context.current_step = "error"
                    else:
                        await self.service.utils.send_error(context, f"予期しない応答タイプ: {response_type}")
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
                
                user_response_message = await self.service.utils.request_user_input(
                    context,
                    UserInputType.SELECT_THEME,
                    ThemeProposalPayload(themes=themes_data).model_dump()
                )
                
                if user_response_message:
                    response_type = user_response_message.response_type
                    payload_dict = user_response_message.payload
                    payload = self.service.utils.convert_payload_to_model(payload_dict, response_type)

                    if response_type == UserInputType.SELECT_THEME and payload and isinstance(payload, SelectThemePayload):
                        selected_index = payload.selected_index
                        if 0 <= selected_index < len(context.generated_themes):
                            context.selected_theme = context.generated_themes[selected_index]
                            context.current_step = "theme_selected"
                            console.print(f"[green]テーマ「{context.selected_theme.title}」が選択されました。[/green]")
                            await self.service.utils.send_server_event(context, StatusUpdatePayload(
                                step=context.current_step, 
                                message=f"Theme selected: {context.selected_theme.title}", 
                                image_mode=getattr(context, 'image_mode', False)
                            ))
                            
                            # Save context after theme selection
                            if process_id and user_id:
                                try:
                                    await self.service.persistence_service.save_context_to_db(context, process_id=process_id, user_id=user_id)
                                    logger.info("Context saved successfully after theme selection")
                                except Exception as save_err:
                                    logger.error(f"Failed to save context after theme selection: {save_err}")
                        else:
                            await self.service.utils.send_error(context, f"無効なテーマインデックス: {selected_index}")
                            context.current_step = "error"
                    elif response_type == UserInputType.REGENERATE:
                        console.print("[yellow]テーマの再生成が要求されました。[/yellow]")
                        context.current_step = "theme_generating"
                        context.generated_themes = []
                    elif response_type == UserInputType.EDIT_AND_PROCEED and payload and isinstance(payload, EditAndProceedPayload):
                        try:
                            edited_theme_data = payload.edited_content
                            if (isinstance(edited_theme_data.get("title"), str) and 
                                isinstance(edited_theme_data.get("description"), str) and 
                                isinstance(edited_theme_data.get("keywords"), list)):
                                from app.domains.seo_article.schemas import ThemeProposalData as ThemeIdea
                                context.selected_theme = ThemeIdea(**edited_theme_data)
                                context.current_step = "theme_selected"
                                console.print(f"[green]テーマが編集され選択されました: {context.selected_theme.title}[/green]")
                                await self.service.utils.send_server_event(context, StatusUpdatePayload(
                                    step=context.current_step, 
                                    message="Theme edited and selected.", 
                                    image_mode=getattr(context, 'image_mode', False)
                                ))
                                
                                # Save context after theme editing
                                if process_id and user_id:
                                    try:
                                        await self.service.persistence_service.save_context_to_db(context, process_id=process_id, user_id=user_id)
                                        logger.info("Context saved successfully after theme editing")
                                    except Exception as save_err:
                                        logger.error(f"Failed to save context after theme editing: {save_err}")
                            else:
                                await self.service.utils.send_error(context, "編集されたテーマの形式が無効です。")
                                context.current_step = "error"
                        except (ValidationError, TypeError, AttributeError) as e:
                            await self.service.utils.send_error(context, f"テーマ編集エラー: {e}")
                            context.current_step = "error"
                    elif response_type == UserInputType.EDIT_THEME and payload and isinstance(payload, EditThemePayload):
                        try:
                            edited_theme_data = payload.edited_theme
                            if (isinstance(edited_theme_data.get("title"), str) and 
                                isinstance(edited_theme_data.get("description"), str) and 
                                isinstance(edited_theme_data.get("keywords"), list)):
                                from app.domains.seo_article.schemas import ThemeProposalData as ThemeIdea
                                context.selected_theme = ThemeIdea(**edited_theme_data)
                                context.current_step = "theme_selected"
                                console.print(f"[green]テーマが編集され選択されました: {context.selected_theme.title}[/green]")
                                await self.service.utils.send_server_event(context, StatusUpdatePayload(
                                    step=context.current_step, 
                                    message="Theme edited and selected.", 
                                    image_mode=getattr(context, 'image_mode', False)
                                ))
                                
                                # Save context after theme editing
                                if process_id and user_id:
                                    try:
                                        await self.service.persistence_service.save_context_to_db(context, process_id=process_id, user_id=user_id)
                                        logger.info("Context saved successfully after theme editing")
                                    except Exception as save_err:
                                        logger.error(f"Failed to save context after theme editing: {save_err}")
                            else:
                                await self.service.utils.send_error(context, "編集されたテーマの形式が無効です。")
                                context.current_step = "error"
                        except (ValidationError, TypeError, AttributeError) as e:
                            await self.service.utils.send_error(context, f"テーマ編集エラー: {e}")
                            context.current_step = "error"
                    elif response_type == UserInputType.EDIT_GENERIC:
                        try:
                            # EDIT_GENERIC - generic edit handler for theme step
                            console.print(f"[yellow]EDIT_GENERIC received for theme step. Payload: {payload}[/yellow]")
                            if hasattr(payload, 'edited_content'):
                                edited_theme_data = payload.edited_content
                                if (isinstance(edited_theme_data.get("title"), str) and 
                                    isinstance(edited_theme_data.get("description"), str) and 
                                    isinstance(edited_theme_data.get("keywords"), list)):
                                    from app.domains.seo_article.schemas import ThemeProposalData as ThemeIdea
                                    context.selected_theme = ThemeIdea(**edited_theme_data)
                                    context.current_step = "theme_selected"
                                    console.print(f"[green]テーマが編集され選択されました（EDIT_GENERIC）: {context.selected_theme.title}[/green]")
                                    await self.service.utils.send_server_event(context, StatusUpdatePayload(
                                        step=context.current_step, 
                                        message="Theme edited and selected.", 
                                        image_mode=getattr(context, 'image_mode', False)
                                    ))
                                    
                                    # Save context after theme editing
                                    if process_id and user_id:
                                        try:
                                            await self.service.persistence_service.save_context_to_db(context, process_id=process_id, user_id=user_id)
                                            logger.info("Context saved successfully after theme editing")
                                        except Exception as save_err:
                                            logger.error(f"Failed to save context after theme editing: {save_err}")
                                else:
                                    await self.service.utils.send_error(context, "EDIT_GENERIC: 編集されたテーマの形式が無効です。")
                                    context.current_step = "error"
                            else:
                                await self.service.utils.send_error(context, "EDIT_GENERIC: 編集されたテーマの形式が無効です。")
                                context.current_step = "error"
                        except Exception as e:
                            await self.service.utils.send_error(context, f"EDIT_GENERIC テーマ編集エラー: {e}")
                            context.current_step = "error"
                    else:
                        await self.service.utils.send_error(context, f"予期しない応答タイプ: {response_type}")
                        context.current_step = "error"
                else:
                    console.print("[red]テーマ選択でユーザー応答がありませんでした。[/red]")
                    context.current_step = "error"
            else:
                console.print("[yellow]テーマが見つからないため生成ステップに戻します。[/yellow]")
                context.current_step = "theme_generating"
        
        elif context.current_step == "research_plan_generated":
            if context.research_plan:
                from app.domains.seo_article.schemas import ResearchPlanData, ResearchPlanQueryData
                plan_data = ResearchPlanData(
                    topic=context.research_plan.topic,
                    queries=[ResearchPlanQueryData(query=q.query, focus=q.focus) for q in context.research_plan.queries]
                )
                
                # CRITICAL FIX: Set step to completed state and mark waiting for input using RPC
                if process_id and user_id:
                    try:
                        from app.domains.seo_article.services.flow_service import get_supabase_client
                        
                        # 1) Ensure current_step_name is set to completion state
                        context.current_step = "research_plan_generated"
                        await self.service.persistence_service.update_process_state(
                            process_id=process_id,
                            current_step_name="research_plan_generated"
                        )
                        
                        # 2) Save context with research plan to DB
                        await self.service.persistence_service.save_context_to_db(
                            context, process_id=process_id, user_id=user_id
                        )
                        
                        # 3) Mark process waiting for input using RPC (triggers events and Realtime)
                        supabase = get_supabase_client()
                        await supabase.rpc(
                            'mark_process_waiting_for_input',
                            {'p_process_id': process_id, 'p_input_type': 'approve_plan', 'p_timeout_minutes': 60}
                        ).execute()
                        
                        logger.info("Process state marked waiting for research plan approval with RPC")
                    except Exception as save_err:
                        logger.error(f"Failed to mark process waiting for research plan approval: {save_err}")
                
                user_response_message = await self.service.utils.request_user_input(
                    context,
                    UserInputType.APPROVE_PLAN,
                    ResearchPlanPayload(plan=plan_data).model_dump()
                )
                
                if user_response_message:
                    response_type = user_response_message.response_type
                    payload_dict = user_response_message.payload
                    payload = self.service.utils.convert_payload_to_model(payload_dict, response_type)

                    if response_type == UserInputType.APPROVE_PLAN and payload and isinstance(payload, ApprovePayload):
                        if payload.approved:
                            context.current_step = "research_plan_approved"
                            console.print("[green]リサーチプランが承認されました。[/green]")
                            await self.service.utils.send_server_event(context, StatusUpdatePayload(
                                step=context.current_step, 
                                message="Research plan approved.", 
                                image_mode=getattr(context, 'image_mode', False)
                            ))
                            
                            # Save context after research plan approval
                            if process_id and user_id:
                                try:
                                    await self.service.persistence_service.save_context_to_db(context, process_id=process_id, user_id=user_id)
                                    logger.info("Context saved successfully after research plan approval")
                                except Exception as save_err:
                                    logger.error(f"Failed to save context after research plan approval: {save_err}")
                        else:
                            console.print("[yellow]リサーチプランが否認されました。再生成を試みます。[/yellow]")
                            context.current_step = "research_planning"
                            context.research_plan = None
                    elif response_type == UserInputType.REGENERATE:
                        console.print("[yellow]リサーチプランの再生成が要求されました。[/yellow]")
                        context.current_step = "research_planning"
                        context.research_plan = None
                    elif response_type == UserInputType.EDIT_PLAN and payload and isinstance(payload, EditPlanPayload):
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
                                await self.service.utils.send_server_event(context, StatusUpdatePayload(
                                    step=context.current_step, 
                                    message="Research plan edited and approved.", 
                                    image_mode=getattr(context, 'image_mode', False)
                                ))
                                
                                # Save context after plan editing
                                if process_id and user_id:
                                    try:
                                        await self.service.persistence_service.save_context_to_db(context, process_id=process_id, user_id=user_id)
                                        logger.info("Context saved successfully after research plan editing")
                                    except Exception as save_err:
                                        logger.error(f"Failed to save context after research plan editing: {save_err}")
                            else:
                                await self.service.utils.send_error(context, "編集されたリサーチプランの形式が無効です。")
                                context.current_step = "error"
                        except (ValidationError, TypeError, AttributeError) as e:
                            await self.service.utils.send_error(context, f"リサーチプラン編集エラー: {e}")
                            context.current_step = "error"
                    elif response_type == UserInputType.EDIT_AND_PROCEED and payload and isinstance(payload, EditAndProceedPayload):
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
                                await self.service.utils.send_server_event(context, StatusUpdatePayload(
                                    step=context.current_step, 
                                    message="Research plan edited and approved.", 
                                    image_mode=getattr(context, 'image_mode', False)
                                ))
                                
                                # Save context after plan editing
                                if process_id and user_id:
                                    try:
                                        await self.service.persistence_service.save_context_to_db(context, process_id=process_id, user_id=user_id)
                                        logger.info("Context saved successfully after research plan editing")
                                    except Exception as save_err:
                                        logger.error(f"Failed to save context after research plan editing: {save_err}")
                            else:
                                await self.service.utils.send_error(context, "編集されたリサーチプランの形式が無効です。")
                                context.current_step = "error"
                        except (ValidationError, TypeError, AttributeError) as e:
                            await self.service.utils.send_error(context, f"リサーチプラン編集エラー: {e}")
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
                                    await self.service.utils.send_server_event(context, StatusUpdatePayload(
                                        step=context.current_step, 
                                        message="Research plan edited and approved.", 
                                        image_mode=getattr(context, 'image_mode', False)
                                    ))
                                else:
                                    await self.service.utils.send_error(context, "EDIT_GENERIC: 編集されたリサーチプランの形式が無効です。")
                                    context.current_step = "error"
                            else:
                                await self.service.utils.send_error(context, "EDIT_GENERIC: 編集されたリサーチプランの形式が無効です。")
                                context.current_step = "error"
                        except Exception as e:
                            await self.service.utils.send_error(context, f"EDIT_GENERIC リサーチプラン編集エラー: {e}")
                            context.current_step = "error"
                    else:
                        await self.service.utils.send_error(context, f"予期しない応答タイプ: {response_type}")
                        context.current_step = "error"
                else:
                    console.print("[red]リサーチプラン承認でユーザー応答がありませんでした。[/red]")
                    context.current_step = "error"
            else:
                console.print("[yellow]リサーチプランが見つからないため生成ステップに戻します。[/yellow]")
                context.current_step = "research_planning"
        
        else:
            console.print(f"[red]未実装のユーザー入力ステップ: {context.current_step}[/red]")
            context.current_step = "error"

    # ============================================================================
    # Background Task Execution Methods (Wrapper methods for background task manager)
    # ============================================================================

    async def execute_keyword_analysis_step(self, context: ArticleContext):
        """Execute keyword analysis step for background tasks"""
        try:
            process_id = getattr(context, 'process_id', 'unknown')
            run_config = RunConfig(
                workflow_name="SEO記事生成ワークフロー（バックグラウンド）",
                trace_id=f"trace_bg_keyword_{process_id}",
                group_id=process_id,
                trace_metadata={
                    "process_id": process_id,
                    "background_processing": "true",
                    "current_step": "keyword_analyzing"
                }
            )
            await self.handle_keyword_analyzing_step(context, run_config)
        except Exception as e:
            logger.error(f"Error in keyword analysis step: {e}")
            context.current_step = "error"
            context.error_message = str(e)
            raise

    async def execute_persona_generation_step(self, context: ArticleContext):
        """Execute persona generation step for background tasks"""
        try:
            process_id = getattr(context, 'process_id', 'unknown')
            run_config = RunConfig(
                workflow_name="SEO記事生成ワークフロー（バックグラウンド）",
                trace_id=f"trace_bg_persona_{process_id}",
                group_id=process_id,
                trace_metadata={
                    "process_id": process_id,
                    "background_processing": "true",
                    "current_step": "persona_generating"
                }
            )
            
            # Execute persona generation without WebSocket interaction
            current_agent = persona_generator_agent
            agent_input = f"キーワード: {context.initial_keywords}, 年代: {context.target_age_group}, 属性: {context.persona_type}, 独自ペルソナ: {context.custom_persona}, 生成数: {context.num_persona_examples}"
            logger.info("PersonaGeneratorAgent に具体的なペルソナ生成を依頼します...")
            
            agent_output = await self.run_agent(current_agent, agent_input, context, run_config)

            if isinstance(agent_output, GeneratedPersonasResponse):
                context.generated_detailed_personas = [p.description for p in agent_output.personas]
                context.current_step = "persona_generated"
                logger.info(f"{len(context.generated_detailed_personas)}件の具体的なペルソナを生成しました。ユーザー選択待ちです。")
            else:
                logger.error("ペルソナ生成中に予期しないエージェント出力タイプを受け取りました。")
                context.current_step = "error"
                context.error_message = "ペルソナ生成に失敗しました"
                raise Exception("ペルソナ生成に失敗しました")
                
        except Exception as e:
            logger.error(f"Error in persona generation step: {e}")
            context.current_step = "error"
            context.error_message = str(e)
            raise

    async def execute_theme_generation_step(self, context: ArticleContext):
        """Execute theme generation step for background tasks"""
        try:
            process_id = getattr(context, 'process_id', 'unknown')
            run_config = RunConfig(
                workflow_name="SEO記事生成ワークフロー（バックグラウンド）",
                trace_id=f"trace_bg_theme_{process_id}",
                group_id=process_id,
                trace_metadata={
                    "process_id": process_id,
                    "background_processing": "true",
                    "current_step": "theme_generating"
                }
            )
            
            # Execute theme generation without WebSocket interaction
            current_agent = theme_agent
            agent_input = self.create_theme_agent_input(context)
            logger.info("ThemeAgent にテーマ提案を依頼します...")
            
            agent_output = await self.run_agent(current_agent, agent_input, context, run_config)

            if isinstance(agent_output, ThemeProposal):
                context.generated_themes = agent_output.themes
                context.current_step = "theme_proposed"
                logger.info(f"{len(context.generated_themes)}件のテーマ案を生成しました。ユーザー選択待ちです。")
            else:
                logger.error("テーマ生成中に予期しないエージェント出力タイプを受け取りました。")
                context.current_step = "error"
                context.error_message = "テーマ生成に失敗しました"
                raise Exception("テーマ生成に失敗しました")
                
        except Exception as e:
            logger.error(f"Error in theme generation step: {e}")
            context.current_step = "error"
            context.error_message = str(e)
            raise

    async def execute_research_planning_step(self, context: ArticleContext):
        """Execute research planning step for background tasks"""
        try:
            process_id = getattr(context, 'process_id', 'unknown')
            run_config = RunConfig(
                workflow_name="SEO記事生成ワークフロー（バックグラウンド）",
                trace_id=f"trace_bg_research_plan_{process_id}",
                group_id=process_id,
                trace_metadata={
                    "process_id": process_id,
                    "background_processing": "true",
                    "current_step": "research_planning"
                }
            )
            await self.execute_research_planning_background(context, run_config)
        except Exception as e:
            logger.error(f"Error in research planning step: {e}")
            context.current_step = "error"
            context.error_message = str(e)
            raise

    async def execute_single_research_query(self, context: ArticleContext, query, query_index: int):
        """Execute a single research query for background tasks"""
        try:
            process_id = getattr(context, 'process_id', 'unknown')
            run_config = RunConfig(
                workflow_name="SEO記事生成ワークフロー（バックグラウンド）",
                trace_id=f"trace_bg_research_query_{process_id}_{query_index}",
                group_id=process_id,
                trace_metadata={
                    "process_id": process_id,
                    "background_processing": "true",
                    "current_step": "researching",
                    "query_index": query_index
                }
            )
            
            # Initialize research query results if not exists
            if not hasattr(context, 'research_query_results'):
                context.research_query_results = []
                
            # Execute research for this query
            current_agent = researcher_agent
            agent_input = f"以下のクエリについて詳細にリサーチしてください: {query.query if hasattr(query, 'query') else str(query)}"
            
            agent_output = await self.run_agent(current_agent, agent_input, context, run_config)
            
            if isinstance(agent_output, ResearchQueryResult):
                context.research_query_results.append(agent_output)
                logger.info(f"Research query {query_index + 1} completed successfully")
            else:
                logger.warning(f"Unexpected agent output type for research query {query_index + 1}: {type(agent_output)}")
                
        except Exception as e:
            logger.error(f"Error in research query {query_index}: {e}")
            raise

    async def execute_research_synthesis_step(self, context: ArticleContext):
        """Execute research synthesis step for background tasks"""
        try:
            process_id = getattr(context, 'process_id', 'unknown')
            run_config = RunConfig(
                workflow_name="SEO記事生成ワークフロー（バックグラウンド）",
                trace_id=f"trace_bg_research_synthesis_{process_id}",
                group_id=process_id,
                trace_metadata={
                    "process_id": process_id,
                    "background_processing": "true",
                    "current_step": "research_synthesizing"
                }
            )
            await self.execute_research_synthesizing_background(context, run_config)
        except Exception as e:
            logger.error(f"Error in research synthesis step: {e}")
            context.current_step = "error"
            context.error_message = str(e)
            raise

    async def execute_outline_generation_step(self, context: ArticleContext):
        """Execute outline generation step for background tasks"""
        try:
            process_id = getattr(context, 'process_id', 'unknown')
            run_config = RunConfig(
                workflow_name="SEO記事生成ワークフロー（バックグラウンド）",
                trace_id=f"trace_bg_outline_{process_id}",
                group_id=process_id,
                trace_metadata={
                    "process_id": process_id,
                    "background_processing": "true",
                    "current_step": "outline_generating"
                }
            )
            await self.execute_outline_generating_background(context, run_config)
        except Exception as e:
            logger.error(f"Error in outline generation step: {e}")
            context.current_step = "error"
            context.error_message = str(e)
            raise

    async def write_single_section(self, context: ArticleContext, section, section_index: int) -> str:
        """Write a single section for background tasks"""
        try:
            process_id = getattr(context, 'process_id', 'unknown')
            run_config = RunConfig(
                workflow_name="SEO記事生成ワークフロー（バックグラウンド）",
                trace_id=f"trace_bg_section_{process_id}_{section_index}",
                group_id=process_id,
                trace_metadata={
                    "process_id": process_id,
                    "background_processing": "true",
                    "current_step": "writing_sections",
                    "section_index": str(section_index)
                }
            )
            
            # Choose appropriate agent based on image mode
            if getattr(context, 'image_mode', False):
                current_agent = section_writer_with_images_agent
            else:
                current_agent = section_writer_agent
            
            # Prepare section input using conversation history
            section_title = section.heading if hasattr(section, 'heading') else f"Section {section_index + 1}"
            user_request = (
                f"前のセクション（もしあれば）に続けて、アウトラインのセクション {section_index + 1}"
                f"「{section_title}」の内容をHTMLで執筆してください。提供された詳細リサーチ情報を参照し、"
                f""
            )
            current_input_messages: List[Dict[str, Any]] = list(context.section_writer_history)
            current_input_messages.append({
                "role": "user",
                "content": [{"type": "input_text", "text": user_request}]
            })
            agent_input = current_input_messages

            agent_output = await self.run_agent(current_agent, agent_input, context, run_config)
            
            # Append to conversation history for continuity
            try:
                context.add_to_section_writer_history("user", user_request)
                if hasattr(agent_output, 'content') and agent_output.content:
                    context.add_to_section_writer_history("assistant", agent_output.content)
                elif isinstance(agent_output, str) and agent_output:
                    context.add_to_section_writer_history("assistant", agent_output)
            except Exception:
                pass

            if hasattr(agent_output, 'content'):
                return agent_output.content
            elif isinstance(agent_output, str):
                return agent_output
            else:
                logger.warning(f"Unexpected section output type: {type(agent_output)}")
                return f"<h2>{section_title}</h2>\n<p>セクション生成に失敗しました。</p>"
                
        except Exception as e:
            logger.error(f"Error writing section {section_index}: {e}")
            return f"<h2>{section.heading if hasattr(section, 'heading') else f'Section {section_index + 1}'}</h2>\n<p>セクション生成中にエラーが発生しました: {str(e)}</p>"

    async def execute_editing_step(self, context: ArticleContext):
        """Execute editing step for background tasks"""
        try:
            process_id = getattr(context, 'process_id', 'unknown')
            run_config = RunConfig(
                workflow_name="SEO記事生成ワークフロー（バックグラウンド）",
                trace_id=f"trace_bg_editing_{process_id}",
                group_id=process_id,
                trace_metadata={
                    "process_id": process_id,
                    "background_processing": "true",
                    "current_step": "editing"
                }
            )
            await self.execute_editing_background(context, run_config)
        except Exception as e:
            logger.error(f"Error in editing step: {e}")
            context.current_step = "error"
            context.error_message = str(e)
            raise
