# -*- coding: utf-8 -*-
import asyncio
import json
import time
import traceback
import logging  # ログ追加
from datetime import datetime, timezone
from typing import AsyncGenerator, List, Dict, Any, Optional, Union
from fastapi import WebSocket, WebSocketDisconnect, status # <<< status をインポート
from starlette.websockets import WebSocketState # WebSocketStateをインポート
from openai import AsyncOpenAI, BadRequestError, InternalServerError, AuthenticationError
from openai.types.responses import ResponseTextDeltaEvent, ResponseCompletedEvent
from agents import Runner, RunConfig, Agent, RunContextWrapper, trace
from agents.exceptions import AgentsException, MaxTurnsExceeded, ModelBehaviorError, UserError
from agents.tracing import custom_span
from rich.console import Console # ログ出力用
from pydantic import ValidationError, BaseModel # <<< BaseModel をインポート

# 内部モジュールのインポート
from core.config import settings
from schemas.request import GenerateArticleRequest
from schemas.response import (
    WebSocketMessage, ServerEventMessage, ClientResponseMessage, UserActionPayload,
    StatusUpdatePayload, ThemeProposalPayload, ResearchPlanPayload, ResearchProgressPayload,
    ResearchCompletePayload, OutlinePayload, SectionChunkPayload, EditingStartPayload,
    FinalResultPayload, ErrorPayload, UserInputRequestPayload, UserInputType,
    SelectThemePayload, ApprovePayload, GeneratedPersonasPayload, SelectPersonaPayload, GeneratedPersonaData, EditAndProceedPayload, RegeneratePayload, ThemeProposalData,
    ResearchPlanData, ResearchPlanQueryData,
    OutlineData, OutlineSectionData, # OutlineData, OutlineSectionData を追加
    SerpKeywordAnalysisPayload, SerpAnalysisArticleData # SerpAPIキーワード分析用のペイロード追加
)
from services.context import ArticleContext
from services.models import (
    AgentOutput, ThemeProposal, ResearchPlan, ResearchQueryResult, ResearchReport, Outline, OutlineSection,
    RevisedArticle, ClarificationNeeded, StatusUpdate, ArticleSection, KeyPoint, GeneratedPersonasResponse, GeneratedPersonaItem, ResearchQuery,
    ThemeIdea, # ThemeIdea を追加
    SerpKeywordAnalysisReport # SerpAPIキーワード分析レポート用のモデル追加
)
from services.agents import (
    theme_agent, research_planner_agent, researcher_agent, research_synthesizer_agent,
    outline_agent, section_writer_agent, editor_agent, persona_generator_agent, # persona_generator_agent を追加
    serp_keyword_analysis_agent # SerpAPIキーワード分析エージェント追加
)
from services.serpapi_service import SerpAPIService # SerpAPIサービス追加

console = Console() # ログ出力用

# ログ設定
logger = logging.getLogger(__name__)

# OpenAIクライアントの初期化 (ファイルスコープに戻す)
async_client = AsyncOpenAI(api_key=settings.openai_api_key)

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

class ArticleGenerationService:
    """記事生成のコアロジックを提供し、WebSocket通信を処理するサービスクラス"""

    async def handle_websocket_connection(self, websocket: WebSocket, process_id: Optional[str] = None, user_id: Optional[str] = None):
        """WebSocket接続を処理し、記事生成プロセスを実行"""
        await websocket.accept()
        context: Optional[ArticleContext] = None
        run_config: Optional[RunConfig] = None
        generation_task: Optional[asyncio.Task] = None
        is_initialized = False  # 初期化完了フラグ

        try:
            # 1. 既存プロセスの再開か新規作成かを判定
            if process_id:
                # 既存プロセスの再開
                context = await self._load_context_from_db(process_id)
                if not context:
                    raise ValueError(f"Process {process_id} not found")
                
                # WebSocketオブジェクトを再設定
                context.websocket = websocket
                context.user_response_event = asyncio.Event()
                
                console.print(f"[green]Resuming process {process_id} from step {context.current_step}[/green]")
                
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
                        "session_start_time": time.time(),
                        "workflow_version": "1.0.0",
                        "resumed": True
                    },
                    tracing_disabled=not settings.enable_tracing,
                    trace_include_sensitive_data=settings.trace_include_sensitive_data
                )
                is_initialized = True  # 既存プロセスは既に初期化済み
            else:
                # 新規プロセスの開始
                # 最初のメッセージ(生成リクエスト)を受信
                initial_data = await websocket.receive_json()
                request = GenerateArticleRequest(**initial_data) # バリデーション

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
                websocket=websocket, # WebSocketオブジェクトをコンテキストに追加
                    user_response_event=asyncio.Event() # ユーザー応答待ちイベント
                )
                
                # 単一のトレースIDとグループIDを生成して、フロー全体をまとめる
                import uuid
                import time
                session_id = str(uuid.uuid4())
                trace_id = f"trace_{session_id.replace('-', '')[:32]}"
                
                # データベースに初期状態を保存してprocess_idを取得
                if user_id:
                    process_id = await self._save_context_to_db(context, user_id=user_id)
                    console.print(f"[cyan]Created new process {process_id}[/cyan]")
                
                run_config = RunConfig(
                workflow_name="SEO記事生成ワークフロー",
                trace_id=trace_id,
                group_id=session_id,
                trace_metadata={
                    "keywords": request.initial_keywords,
                    "target_length": request.target_length,
                    "persona_type": request.persona_type.value if request.persona_type else None,
                    "company_name": request.company_name,
                    "session_start_time": time.time(),
                    "workflow_version": "1.0.0",
                    "user_agent": "unknown"  # ユーザーエージェント情報があれば追加
                },
                tracing_disabled=not settings.enable_tracing,
                trace_include_sensitive_data=settings.trace_include_sensitive_data
                )
                is_initialized = True  # 初期化完了

            # 3. 単一のトレースコンテキスト内でバックグラウンド生成ループを開始
            with safe_trace_context("SEO記事生成ワークフロー", trace_id, session_id):
                generation_task = asyncio.create_task(
                    self._run_generation_loop(context, run_config, process_id, user_id)
                )

                # 4. クライアントからの応答を待ち受けるループ
                while not generation_task.done():
                    try:
                        # タイムアウトを設定してクライアントからの応答を待つ (例: 5分)
                        response_data = await asyncio.wait_for(websocket.receive_json(), timeout=300.0) # TODO: タイムアウト値を設定ファイルなど外部から設定可能にする
                        
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
                                if message.response_type in [UserInputType.SELECT_PERSONA, UserInputType.SELECT_THEME, UserInputType.APPROVE_PLAN, UserInputType.APPROVE_OUTLINE, UserInputType.REGENERATE, UserInputType.EDIT_AND_PROCEED]:
                                    console.print(f"[blue]応答タイプ確認OK: {message.response_type} は有効な応答タイプです[/blue]")
                                    # 期待される応答タイプ、または再生成・編集要求の場合
                                    if context.expected_user_input == message.response_type or \
                                       message.response_type == UserInputType.REGENERATE or \
                                       message.response_type == UserInputType.EDIT_AND_PROCEED:
                                        
                                        console.print(f"[green]応答タイプマッチ！ {message.response_type} を処理します[/green]")
                                        context.user_response = message # 応答全体をコンテキストに保存 (payloadだけでなくtypeも含む)
                                        context.user_response_event.set() # 待機中のループに応答があったことを通知
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
                            console.print(f"[red]Received message before initialization complete[/red]")
                            await self._send_error(context, "System not ready for client responses")

                    except asyncio.TimeoutError:
                        await self._send_error(context, "Client response timeout.")
                        if generation_task: generation_task.cancel()
                        break
                    except WebSocketDisconnect:
                        console.print("[yellow]WebSocket disconnected by client.[/yellow]")
                        if generation_task: generation_task.cancel()
                        break
                    except (json.JSONDecodeError) as e:
                        await self._send_error(context, f"Invalid JSON format: {e}")
                        # 不正なメッセージを受け取った場合、処理を続ける
                    except Exception as e: # その他の予期せぬエラー
                         await self._send_error(context, f"Error processing client message: {e}")
                         if generation_task: generation_task.cancel()
                         break

                # 生成タスクの結果を確認 (例外が発生していないか)
                if generation_task and generation_task.done() and not generation_task.cancelled():
                     try:
                         generation_task.result()
                     except Exception as e:
                         # _run_generation_loop内でハンドルされなかった例外
                         console.print(f"[bold red]Unhandled exception in generation task:[/bold red] {e}")
                         # WebSocketがまだ接続されていればエラーを送信
                         if websocket.client_state == WebSocketState.CONNECTED:
                             await self._send_error(context, f"Internal server error during generation: {e}")

        except WebSocketDisconnect:
            console.print("[yellow]WebSocket disconnected.[/yellow]")
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
            # クリーンアップ
            if generation_task and not generation_task.done():
                generation_task.cancel()
                try:
                    await generation_task # キャンセル完了を待つ
                except asyncio.CancelledError:
                    console.print("Generation task cancelled.")
            if websocket.client_state == WebSocketState.CONNECTED:
                 await websocket.close()
            console.print("WebSocket connection closed.")


    async def _send_server_event(self, context: ArticleContext, payload: BaseModel): # <<< BaseModel をインポートしたのでOK
        """WebSocket経由でサーバーイベントを送信するヘルパー関数"""
        if context.websocket:
            try:
                message = ServerEventMessage(payload=payload)
                await context.websocket.send_json(message.model_dump())
            except WebSocketDisconnect:
                console.print("[yellow]WebSocket disconnected while trying to send message.[/yellow]")
                raise # 再送出するか、ここで処理するか検討
            except Exception as e:
                console.print(f"[bold red]Error sending WebSocket message: {e}[/bold red]")
        else:
            console.print(f"[Warning] WebSocket not available. Event discarded: {payload.model_dump_json(indent=2)}")

    async def _send_error(self, context: ArticleContext, error_message: str, step: Optional[str] = None):
        """WebSocket経由でエラーイベントを送信するヘルパー関数"""
        current_step = step or (context.current_step if context else "unknown")
        payload = ErrorPayload(step=current_step, error_message=error_message)
        await self._send_server_event(context, payload)


    async def _request_user_input(self, context: ArticleContext, request_type: UserInputType, data: Optional[Dict[str, Any]] = None):
        """クライアントに特定のタイプの入力を要求し、応答を待つ"""
        context.expected_user_input = request_type
        context.user_response = None # 前回の応答をクリア
        context.user_response_event.clear() # イベントをリセット

        payload = UserInputRequestPayload(request_type=request_type, data=data)
        await self._send_server_event(context, payload)

        # クライアントからの応答を待つ (タイムアウトは handle_websocket_connection で処理)
        await context.user_response_event.wait()

        response = context.user_response
        context.user_response = None # 応答をクリア
        context.expected_user_input = None # 期待する入力をクリア
        return response


    async def _run_generation_loop(self, context: ArticleContext, run_config: RunConfig, process_id: Optional[str] = None, user_id: Optional[str] = None):
        """記事生成のメインループ（WebSocketインタラクティブ版）"""
        current_agent: Optional[Agent[ArticleContext]] = None
        agent_input: Union[str, List[Dict[str, Any]]]

        try:
            while context.current_step not in ["completed", "error"]:
                # データベースに現在の状態を保存
                if process_id and user_id:
                    await self._save_context_to_db(context, process_id=process_id, user_id=user_id)
                
                await self._send_server_event(context, StatusUpdatePayload(step=context.current_step, message=f"Starting step: {context.current_step}"))
                console.rule(f"[bold yellow]API Step: {context.current_step}[/bold yellow]")

                # --- ステップに応じた処理 ---
                if context.current_step == "start":
                    context.current_step = "keyword_analyzing"  # SerpAPIキーワード分析から開始
                    await self._send_server_event(context, StatusUpdatePayload(step=context.current_step, message="Starting keyword analysis with SerpAPI..."))
                    # エージェント実行なし、次のループで処理

                elif context.current_step == "keyword_analyzing":
                    # SerpAPIキーワード分析エージェントを実行
                    current_agent = serp_keyword_analysis_agent
                    agent_input = f"キーワード: {', '.join(context.initial_keywords)}"
                    console.print(f"🤖 {current_agent.name} にSerpAPIキーワード分析を依頼します...")
                    agent_output = await self._run_agent(current_agent, agent_input, context, run_config)

                    if isinstance(agent_output, SerpKeywordAnalysisReport):
                        context.serp_analysis_report = agent_output
                        context.current_step = "keyword_analyzed"
                        console.print("[green]SerpAPIキーワード分析が完了しました。[/green]")
                        
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
                        await self._send_server_event(context, StatusUpdatePayload(step=context.current_step, message="Keyword analysis completed, proceeding to persona generation."))
                    else:
                        await self._send_error(context, f"SerpAPIキーワード分析中に予期しないエージェント出力タイプ ({type(agent_output)}) を受け取りました。")
                        context.current_step = "error"
                        continue

                elif context.current_step == "keyword_analyzed":
                    context.current_step = "persona_generating"  # ペルソナ生成ステップに移行
                    await self._send_server_event(context, StatusUpdatePayload(step=context.current_step, message="Proceeding to persona generation."))
                
                elif context.current_step == "persona_generating":
                    current_agent = persona_generator_agent
                    agent_input = f"キーワード: {context.initial_keywords}, 年代: {context.target_age_group}, 属性: {context.persona_type}, 独自ペルソナ: {context.custom_persona}, 生成数: {context.num_persona_examples}"
                    console.print(f"🤖 {current_agent.name} に具体的なペルソナ生成を依頼します...")
                    agent_output = await self._run_agent(current_agent, agent_input, context, run_config)

                    if isinstance(agent_output, GeneratedPersonasResponse):
                        context.generated_detailed_personas = [p.description for p in agent_output.personas]
                        context.current_step = "persona_generated"
                        console.print(f"[cyan]{len(context.generated_detailed_personas)}件の具体的なペルソナを生成しました。クライアントの選択を待ちます...[/cyan]")
                        
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
                                    await self._send_server_event(context, StatusUpdatePayload(step=context.current_step, message=f"Detailed persona selected: {context.selected_detailed_persona[:50]}..."))
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
                                    await self._send_server_event(context, StatusUpdatePayload(step=context.current_step, message=f"Detailed persona edited and selected."))
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
                    await self._send_server_event(context, StatusUpdatePayload(step=context.current_step, message="Persona selected, proceeding to theme generation."))

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
                                        await self._send_server_event(context, StatusUpdatePayload(step=context.current_step, message=f"Theme selected: {context.selected_theme.title}"))
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
                                            await self._send_server_event(context, StatusUpdatePayload(step=context.current_step, message=f"Theme edited and selected."))
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
                    context.current_step = "research_planning"
                    console.print("リサーチ計画ステップに進みます...")
                    await self._send_server_event(context, StatusUpdatePayload(step=context.current_step, message="Moving to research planning."))
                    # エージェント実行なし

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
                        
                        plan_data_for_client = ResearchPlanData(
                            topic=context.research_plan.topic, # agent_output から context.research_plan に変更
                            queries=[ResearchPlanQueryData(query=q.query, focus=q.focus) for q in context.research_plan.queries] # agent_output から context.research_plan に変更
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
                                    # context.research_plan は既に設定済みなので、ここでは何もしない
                                    context.current_step = "research_plan_approved"
                                    console.print("[green]クライアントがリサーチ計画を承認しました。[/green]")
                                    await self._send_server_event(context, StatusUpdatePayload(step=context.current_step, message="Research plan approved."))
                                else:
                                    console.print("[yellow]クライアントがリサーチ計画を否認しました。再生成を試みます。[/yellow]")
                                    context.current_step = "research_planning"
                                    context.research_plan = None # 承認されなかったのでクリア
                                    continue
                            elif response_type == UserInputType.REGENERATE:
                                console.print("[yellow]クライアントがリサーチ計画の再生成を要求しました。[/yellow]")
                                context.current_step = "research_planning"
                                context.research_plan = None # 再生成するのでクリア
                                continue
                            elif response_type == UserInputType.EDIT_AND_PROCEED and isinstance(payload, EditAndProceedPayload):
                                try:
                                    edited_plan_data = payload.edited_content
                                    if isinstance(edited_plan_data.get("topic"), str) and isinstance(edited_plan_data.get("queries"), list):
                                        context.research_plan = ResearchPlan(
                                            topic=edited_plan_data['topic'],
                                            queries=[ResearchQuery(**q_data) for q_data in edited_plan_data['queries']],
                                            status="research_plan"  # "approved_by_user_edit" から "research_plan" に修正
                                        )
                                        context.current_step = "research_plan_approved"
                                        console.print(f"[green]クライアントがリサーチ計画を編集し、承認しました。[/green]")
                                        await self._send_server_event(context, StatusUpdatePayload(step=context.current_step, message="Research plan edited and approved."))
                                    else:
                                        await self._send_error(context, "Invalid edited research plan content structure.")
                                        context.current_step = "research_plan_generated" # ユーザーの再操作を待つ
                                        # context.research_plan はエージェント生成のものが残っているか、Noneのまま
                                        continue
                                except (ValidationError, TypeError, AttributeError, KeyError) as e:
                                    await self._send_error(context, f"Error processing edited research plan: {e}")
                                    context.current_step = "research_plan_generated" # ユーザーの再操作を待つ
                                    continue
                            else:
                                await self._send_error(context, f"予期しない応答 ({response_type}) がリサーチ計画承認で受信されました。")
                                context.current_step = "research_plan_generated" # ユーザーの再操作を待つ
                                continue
                        else:
                            console.print("[red]リサーチ計画の承認/編集でクライアントからの応答がありませんでした。[/red]")
                            context.current_step = "research_plan_generated" # ユーザーの再操作を待つ
                            # タイムアウトの場合、上位の handle_websocket_connection で処理される
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
                    await self._send_server_event(context, StatusUpdatePayload(step=context.current_step, message="Moving to research execution."))
                    # エージェント実行なし

                elif context.current_step == "researching":
                    if not context.research_plan: raise ValueError("リサーチ計画がありません。")
                    if context.current_research_query_index >= len(context.research_plan.queries):
                        context.current_step = "research_synthesizing"
                        console.print("[green]全クエリのリサーチが完了しました。要約ステップに移ります。[/green]")
                        await self._send_server_event(context, StatusUpdatePayload(step=context.current_step, message="All research queries completed, synthesizing results."))
                        continue

                    current_agent = researcher_agent
                    current_query_obj = context.research_plan.queries[context.current_research_query_index]
                    
                    # リサーチクエリ実行をカスタムスパンでラップ
                    with safe_custom_span(f"research_query", data={
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

                        agent_output = await self._run_agent(current_agent, agent_input, context, run_config)

                        if isinstance(agent_output, ResearchQueryResult):
                            if agent_output.query == current_query_obj.query:
                                context.add_query_result(agent_output)
                                console.print(f"[green]クエリ「{agent_output.query}」の詳細リサーチ結果を処理しました。[/green]")
                                context.current_research_query_index += 1
                            else:
                                raise ValueError(f"予期しないクエリ「{agent_output.query}」の結果を受け取りました。")
                        else:
                             raise TypeError(f"予期しないAgent出力タイプ: {type(agent_output)}")

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
                        # すぐにアウトライン生成へ
                        context.current_step = "outline_generating" # ★ ステップ名修正
                        await self._send_server_event(context, StatusUpdatePayload(step=context.current_step, message="Research report generated, generating outline."))
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
                                    await self._send_server_event(context, StatusUpdatePayload(step=context.current_step, message="Outline approved, proceeding to writing."))
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
                                        console.print(f"[green]クライアントがアウトラインを編集し、承認しました。[/green]")
                                        await self._send_server_event(context, StatusUpdatePayload(step=context.current_step, message="Outline edited and approved."))
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
                    context.current_step = "writing_sections" 

                elif context.current_step == "writing_sections":
                    if not context.generated_outline: raise ValueError("承認済みアウトラインがありません。") # context.outline_approved から context.generated_outline に変更
                    if context.current_section_index >= len(context.generated_outline.sections): # context.outline_approved から context.generated_outline に変更
                        context.full_draft_html = context.get_full_draft()
                        context.current_step = "editing"
                        console.print("[green]全セクションの執筆が完了しました。編集ステップに移ります。[/green]")
                        await self._send_server_event(context, EditingStartPayload())
                        continue

                    current_agent = section_writer_agent
                    target_index = context.current_section_index
                    target_heading = context.generated_outline.sections[target_index].heading # context.outline_approved から context.generated_outline に変更

                    # セクション執筆処理をカスタムスパンでラップ
                    with safe_custom_span(f"section_writing", data={
                        "section_index": target_index,
                        "section_heading": target_heading,
                        "total_sections": len(context.generated_outline.sections)
                    }):
                        user_request = f"前のセクション（もしあれば）に続けて、アウトラインのセクション {target_index + 1}「{target_heading}」の内容をHTMLで執筆してください。提供された詳細リサーチ情報を参照し、必要に応じて出典へのリンクを含めてください。"
                        current_input_messages: List[Dict[str, Any]] = list(context.section_writer_history)
                        current_input_messages.append({"role": "user", "content": [{"type": "input_text", "text": user_request}]})
                        agent_input = current_input_messages

                        console.print(f"🤖 {current_agent.name} にセクション {target_index + 1} の執筆を依頼します (Streaming)...")
                        await self._send_server_event(context, StatusUpdatePayload(step=context.current_step, message=f"Writing section {target_index + 1}: {target_heading}"))

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
                                        # WebSocketでHTMLチャンクを送信
                                        await self._send_server_event(context, SectionChunkPayload(
                                            section_index=target_index,
                                            heading=target_heading,
                                            html_content_chunk=delta,
                                            is_complete=False
                                        ))
                                    elif event.type == "run_item_stream_event" and event.item.type == "tool_call_item":
                                        console.print(f"\n[dim]ツール呼び出し: {event.item.name}[/dim]")
                                    elif event.type == "raw_response_event" and isinstance(event.data, ResponseCompletedEvent):
                                         console.print(f"\n[dim]レスポンス完了イベント受信[/dim]")

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

                        if accumulated_html:
                            generated_section = ArticleSection(
                                section_index=target_index, heading=target_heading, html_content=accumulated_html.strip()
                            )
                            console.print(f"[green]セクション {target_index + 1}「{generated_section.heading}」のHTMLをストリームから構築しました。[/green]")
                            # 完了イベントを送信
                            await self._send_server_event(context, SectionChunkPayload(
                                section_index=target_index, heading=target_heading, html_content_chunk="", is_complete=True
                            ))
                            context.generated_sections_html.append(generated_section.html_content)
                            context.last_agent_output = generated_section
                            # 会話履歴更新
                            last_user_request_item = agent_input[-1] if isinstance(agent_input, list) else None
                            if last_user_request_item and last_user_request_item.get('role') == 'user':
                                user_request_text = last_user_request_item['content'][0]['text']
                                context.add_to_section_writer_history("user", user_request_text)
                            context.add_to_section_writer_history("assistant", generated_section.html_content)
                            context.current_section_index += 1
                        else:
                            raise ValueError(f"セクション {target_index + 1} のHTMLコンテンツが空です。")

                elif context.current_step == "editing":
                    current_agent = editor_agent
                    if not context.full_draft_html: raise ValueError("編集対象のドラフトがありません。")
                    agent_input = "記事ドラフト全体をレビューし、詳細リサーチ情報に基づいて推敲・編集してください。特にリンクの適切性を確認してください。"
                    console.print(f"🤖 {current_agent.name} に最終編集を依頼します...")
                    await self._send_server_event(context, StatusUpdatePayload(step=context.current_step, message="Starting final editing..."))
                    agent_output = await self._run_agent(current_agent, agent_input, context, run_config)

                    if isinstance(agent_output, RevisedArticle):
                        context.final_article_html = agent_output.final_html_content
                        context.current_step = "completed"
                        console.print("[green]記事の編集が完了しました！[/green]")

                        # --- 1. DBへ保存して article_id を取得 ---
                        article_id: Optional[str] = None
                        if process_id and user_id:
                            try:
                                # 先に保存処理を実行（articles への INSERT を含む）
                                await self._save_context_to_db(context, process_id=process_id, user_id=user_id)

                                # 保存後に generated_articles_state から article_id を取得
                                from services.article_flow_service import get_supabase_client
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
            # WebSocketでエラーイベントを送信
            await self._send_error(context, error_message, context.current_step) # stepを指定
        finally:
            # ループ終了時に特別なメッセージを送る (任意)
            if context.current_step == "completed":
                 await self._send_server_event(context, StatusUpdatePayload(step="finished", message="Article generation completed successfully."))
            elif context.current_step == "error":
                 await self._send_server_event(context, StatusUpdatePayload(step="finished", message=f"Article generation finished with error: {context.error_message}"))
            else:
                 # キャンセルされた場合など
                 await self._send_server_event(context, StatusUpdatePayload(step="finished", message="Article generation finished unexpectedly."))


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
        
        # エージェント実行をカスタムスパンでラップ
        with safe_custom_span(f"agent_execution", data={
            "agent_name": agent.name,
            "current_step": context.current_step,
            "max_retries": settings.max_retries,
            "input_type": type(input_data).__name__,
            "input_length": len(str(input_data)) if input_data else 0,
            "execution_start_time": start_time
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

                    if result and result.final_output:
                         output = result.final_output
                         execution_time = time.time() - start_time
                         
                         # 成功時のメトリクス記録
                         logger.info(f"エージェント {agent.name} 実行成功: {execution_time:.2f}秒, 試行回数: {attempt + 1}")
                         
                         if isinstance(output, (ThemeProposal, Outline, RevisedArticle, ClarificationNeeded, StatusUpdate, ResearchPlan, ResearchQueryResult, ResearchReport, GeneratedPersonasResponse, SerpKeywordAnalysisReport)):
                             return output
                         elif isinstance(output, str):
                             try:
                                 parsed_output = json.loads(output)
                                 status_val = parsed_output.get("status") # 変数名を変更
                                 output_model_map = {
                                     "theme_proposal": ThemeProposal, "outline": Outline, "revised_article": RevisedArticle,
                                     "clarification_needed": ClarificationNeeded, "status_update": StatusUpdate,
                                     "research_plan": ResearchPlan, "research_query_result": ResearchQueryResult, "research_report": ResearchReport,
                                     "generated_personas_response": GeneratedPersonasResponse, "serp_keyword_analysis_report": SerpKeywordAnalysisReport
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

    async def _save_context_to_db(self, context: ArticleContext, process_id: Optional[str] = None, user_id: Optional[str] = None, organization_id: Optional[str] = None) -> str:
        """Save ArticleContext to database and return process_id"""
        try:
            from services.article_flow_service import get_supabase_client
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
                if step in ["start", "keyword_analysis", "persona_generation", "theme_generation", 
                           "research_planning", "research_execution", "outline_generation", 
                           "content_writing", "editing"]:
                    return "in_progress"
                elif step == "completed":
                    return "completed"
                elif step == "error":
                    return "error"
                elif step in ["persona_selection_required", "theme_selection_required", 
                             "research_plan_generated", "outline_generated"]:
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
                    # Create article record
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
                    
                    article_result = supabase.table("articles").insert(article_data).execute()
                    if article_result.data:
                        update_data["article_id"] = article_result.data[0]["id"]
                
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

    async def _load_context_from_db(self, process_id: str) -> Optional[ArticleContext]:
        """Load ArticleContext from database"""
        try:
            from services.article_flow_service import get_supabase_client
            supabase = get_supabase_client()
            
            result = supabase.table("generated_articles_state").select("*").eq("id", process_id).execute()
            
            if not result.data:
                return None
            
            state = result.data[0]
            context_dict = state["article_context"]
            
            # Reconstruct ArticleContext from stored data
            context = ArticleContext(
                initial_keywords=context_dict.get("initial_keywords", []),
                target_age_group=context_dict.get("target_age_group"),
                persona_type=context_dict.get("persona_type"),
                custom_persona=context_dict.get("custom_persona"),
                target_length=context_dict.get("target_length"),
                num_theme_proposals=context_dict.get("num_theme_proposals", 3),
                num_research_queries=context_dict.get("num_research_queries", 3),
                num_persona_examples=context_dict.get("num_persona_examples", 3),
                company_name=context_dict.get("company_name"),
                company_description=context_dict.get("company_description"),
                company_style_guide=context_dict.get("company_style_guide"),
                websocket=None,  # Will be set when WebSocket connects
                user_response_event=None  # Will be set when WebSocket connects
            )
            
            # Restore other context state
            context.current_step = context_dict.get("current_step", "start")
            context.generated_detailed_personas = context_dict.get("generated_detailed_personas", [])
            context.selected_detailed_persona = context_dict.get("selected_detailed_persona")
            
            # Restore complex objects
            if context_dict.get("selected_theme"):
                from services.models import ThemeIdea
                context.selected_theme = ThemeIdea(**context_dict["selected_theme"])
            
            if context_dict.get("generated_themes"):
                from services.models import ThemeIdea
                context.generated_themes = [ThemeIdea(**theme_data) for theme_data in context_dict["generated_themes"]]
                
            if context_dict.get("research_plan"):
                from services.models import ResearchPlan
                context.research_plan = ResearchPlan(**context_dict["research_plan"])
                
            if context_dict.get("research_report"):
                from services.models import ResearchReport
                context.research_report = ResearchReport(**context_dict["research_report"])
                
            if context_dict.get("generated_outline"):
                from services.models import Outline
                context.generated_outline = Outline(**context_dict["generated_outline"])
            
            # Restore other state
            context.research_query_results = context_dict.get("research_query_results", [])
            context.current_research_query_index = context_dict.get("current_research_query_index", 0)
            context.generated_sections_html = context_dict.get("generated_sections_html", [])
            context.current_section_index = context_dict.get("current_section_index", 0)
            context.full_draft_html = context_dict.get("full_draft_html")
            context.final_article_html = context_dict.get("final_article_html")
            context.section_writer_history = context_dict.get("section_writer_history", [])
            
            # Restore SerpAPI analysis report if available
            if context_dict.get("serp_analysis_report"):
                from services.models import SerpKeywordAnalysisReport
                context.serp_analysis_report = SerpKeywordAnalysisReport(**context_dict["serp_analysis_report"])
            
            # Restore other simple fields
            context.expected_user_input = context_dict.get("expected_user_input")
            
            return context
            
        except Exception as e:
            logger.error(f"Error loading context from database: {e}")
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
            from services.article_flow_service import get_supabase_client
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
            from services.article_flow_service import get_supabase_client
            supabase = get_supabase_client()
            
            # Query for article with user access control
            result = supabase.table("articles").select("*").eq("id", article_id).eq("user_id", user_id).execute()
            
            if not result.data:
                return None
            
            article = result.data[0]
            
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
            from services.article_flow_service import get_supabase_client
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
            
            # データベースを更新
            result = supabase.table("articles").update(update_fields).eq("id", article_id).eq("user_id", user_id).execute()
            
            if not result.data:
                raise Exception("Failed to update article")
            
            # 更新された記事情報を返す
            return await self.get_article(article_id, user_id)
            
        except Exception as e:
            logger.error(f"Error updating article {article_id}: {e}")
            raise
