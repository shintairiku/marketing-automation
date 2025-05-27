# -*- coding: utf-8 -*-
import asyncio
import json
import traceback
from typing import AsyncGenerator, List, Dict, Any, Optional, Union
from fastapi import WebSocket, WebSocketDisconnect, status # <<< status をインポート
from openai import AsyncOpenAI, BadRequestError, InternalServerError, AuthenticationError
from openai.types.responses import ResponseTextDeltaEvent, ResponseCompletedEvent
from agents import Runner, RunConfig, Agent, RunContextWrapper
from agents.exceptions import AgentsException, MaxTurnsExceeded, ModelBehaviorError, UserError
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
    SelectThemePayload, ApprovePayload # ApprovePayload を追加
)
from services.context import ArticleContext
from services.models import (
    AgentOutput, ThemeProposal, ResearchPlan, ResearchQueryResult, ResearchReport, Outline, OutlineSection,
    RevisedArticle, ClarificationNeeded, StatusUpdate, ArticleSection, KeyPoint, ResearchGapAnalysis
)
from services.agents import (
    theme_agent, research_planner_agent, researcher_agent, research_synthesizer_agent,
    outline_agent, section_writer_agent, editor_agent,
    research_gap_analyzer_agent
)

console = Console() # ログ出力用

# OpenAIクライアントの初期化 (ファイルスコープに戻す)
async_client = AsyncOpenAI(api_key=settings.openai_api_key)

class ArticleGenerationService:
    """記事生成のコアロジックを提供し、WebSocket通信を処理するサービスクラス"""

    async def handle_websocket_connection(self, websocket: WebSocket):
        """WebSocket接続を処理し、記事生成プロセスを実行"""
        await websocket.accept()
        context: Optional[ArticleContext] = None
        run_config: Optional[RunConfig] = None
        generation_task: Optional[asyncio.Task] = None

        try:
            # 1. 最初のメッセージ(生成リクエスト)を受信
            initial_data = await websocket.receive_json()
            request = GenerateArticleRequest(**initial_data) # バリデーション

            # 2. コンテキストと実行設定を初期化
            context = ArticleContext(
                initial_keywords=request.initial_keywords,
                target_persona=request.target_persona,
                target_length=request.target_length,
                num_theme_proposals=request.num_theme_proposals,
                num_research_queries=request.num_research_queries,
                max_research_phases=request.max_research_phases,
                company_name=request.company_name,
                company_description=request.company_description,
                company_style_guide=request.company_style_guide,
                websocket=websocket, # WebSocketオブジェクトをコンテキストに追加
                user_response_event=asyncio.Event() # ユーザー応答待ちイベント
            )
            run_config = RunConfig(workflow_name="SEOArticleGenerationAPI_WS")

            # 3. バックグラウンドで生成ループを開始
            generation_task = asyncio.create_task(
                self._run_generation_loop(context, run_config)
            )

            # 4. クライアントからの応答を待ち受けるループ
            while not generation_task.done():
                try:
                    # タイムアウトを設定してクライアントからの応答を待つ (例: 5分)
                    response_data = await asyncio.wait_for(websocket.receive_json(), timeout=300.0)
                    message = ClientResponseMessage(**response_data) # バリデーション

                    if context.current_step in ["theme_proposed", "research_plan_generated", "outline_generated"]:
                        if context.expected_user_input == message.response_type:
                            context.user_response = message.payload # 応答をコンテキストに保存
                            context.user_response_event.set() # 待機中のループに応答があったことを通知
                        else:
                            # 予期しない応答タイプ
                            await self._send_error(context, "Invalid response type received.")
                    else:
                        # ユーザー入力待ちでないときにメッセージが来た場合
                        console.print(f"[yellow]Ignoring unexpected client message during step {context.current_step}[/yellow]")

                except asyncio.TimeoutError:
                    await self._send_error(context, "Client response timeout.")
                    if generation_task: generation_task.cancel()
                    break
                except WebSocketDisconnect:
                    console.print("[yellow]WebSocket disconnected by client.[/yellow]")
                    if generation_task: generation_task.cancel()
                    break
                except (ValidationError, json.JSONDecodeError) as e:
                    await self._send_error(context, f"Invalid message format: {e}")
                    # 不正なメッセージを受け取った場合、処理を続けるか切断するか検討
                    # ここではエラーを送信してループを続ける
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


    async def _run_generation_loop(self, context: ArticleContext, run_config: RunConfig):
        """記事生成のメインループ（WebSocketインタラクティブ版）"""
        current_agent: Optional[Agent[ArticleContext]] = None
        agent_input: Union[str, List[Dict[str, Any]]]

        try:
            while context.current_step not in ["completed", "error"]:
                await self._send_server_event(context, StatusUpdatePayload(step=context.current_step, message=f"Starting step: {context.current_step}"))
                console.rule(f"[bold yellow]API Step: {context.current_step}[/bold yellow]")

                # --- ステップに応じた処理 ---
                if context.current_step == "start":
                    current_agent = theme_agent
                    agent_input = f"キーワード「{', '.join(context.initial_keywords)}」とペルソナ「{context.target_persona}」に基づいて、{context.num_theme_proposals}個のテーマ案を生成してください。"
                    console.print(f"🤖 {current_agent.name} にテーマ提案を依頼します...")
                    agent_output = await self._run_agent(current_agent, agent_input, context, run_config)

                    if isinstance(agent_output, ThemeProposal):
                        context.last_agent_output = agent_output
                        if agent_output.themes:
                            context.current_step = "theme_proposed" # ユーザー選択待ちステップへ
                            console.print(f"[cyan]テーマ案を{len(agent_output.themes)}件生成しました。クライアントの選択を待ちます...[/cyan]")
                            # WebSocketでテーマ案を送信し、選択を要求
                            theme_data = [t.model_dump() for t in agent_output.themes]
                            user_response = await self._request_user_input(
                                context,
                                UserInputType.SELECT_THEME,
                                {"themes": theme_data}
                            )
                            # クライアントからの応答を処理
                            if user_response:
                                console.print(f"[cyan]クライアントからの応答を受信 (型: {type(user_response)}): {user_response}[/cyan]")
                                try:
                                    selected_index = None
                                    # user_response が SelectThemePayload インスタンスかチェック
                                    if isinstance(user_response, SelectThemePayload): # 型チェックを追加
                                        selected_index = user_response.selected_index # 属性アクセスに変更
                                    # 辞書の場合も念のため残す
                                    elif isinstance(user_response, dict) and "selected_index" in user_response:
                                        selected_index = int(user_response["selected_index"])

                                    if selected_index is not None and 0 <= selected_index < len(agent_output.themes):
                                        context.selected_theme = agent_output.themes[selected_index]
                                        context.current_step = "theme_selected"
                                        console.print(f"[green]クライアントがテーマ「{context.selected_theme.title}」を選択しました。[/green]")
                                        await self._send_server_event(context, StatusUpdatePayload(step=context.current_step, message=f"Theme selected: {context.selected_theme.title}"))
                                    else:
                                        if selected_index is None:
                                            # エラーメッセージを修正
                                            raise ValueError(f"テーマ選択の応答ペイロードから selected_index を抽出できませんでした: {user_response}")
                                        else:
                                            raise ValueError(f"無効なテーマインデックスが選択されました: {selected_index} (有効範囲: 0～{len(agent_output.themes)-1})")
                                except (AttributeError, TypeError, ValueError) as e: # AttributeError をキャッチするよう修正
                                    console.print(f"[bold red]テーマ選択の応答処理中にエラー: {e}[/bold red]")
                                    raise ValueError(f"テーマ選択の応答処理に失敗しました: {e}")
                            else:
                                raise ValueError("テーマ選択の応答が空です。")
                        else:
                            raise ValueError("テーマ案が生成されませんでした。")
                    elif isinstance(agent_output, ClarificationNeeded):
                         raise ValueError(f"テーマ生成で確認が必要になりました: {agent_output.message}")
                    else:
                        raise TypeError(f"予期しないAgent出力タイプ: {type(agent_output)}")

                elif context.current_step == "theme_selected":
                    context.current_step = "research_planning"
                    console.print("リサーチ計画ステップに進みます...")
                    await self._send_server_event(context, StatusUpdatePayload(step=context.current_step, message="Moving to research planning."))
                    # エージェント実行なし

                elif context.current_step == "research_planning":
                    if not context.selected_theme: raise ValueError("テーマが選択されていません。")
                    
                    phase_num = len(context.research_plans) + 1
                    current_agent = research_planner_agent
                    agent_input = f"選択されたテーマ「{context.selected_theme.title}」についての第{phase_num}段階リサーチ計画を作成してください。"
                    
                    console.print(f"🤖 {current_agent.name} に第{phase_num}段階リサーチ計画作成を依頼します...")
                    agent_output = await self._run_agent(current_agent, agent_input, context, run_config)

                    if isinstance(agent_output, ResearchPlan):
                        context.research_plans.append(agent_output)
                        context.current_research_plan_index = len(context.research_plans) - 1 
                        context.current_step = "research_plan_generated" # ユーザー承認待ちステップへ
                        console.print(f"[cyan]第{phase_num}段階リサーチ計画を生成しました。クライアントの承認を待ちます...[/cyan]")
                        # WebSocketで計画を送信し、承認を要求
                        plan_data = agent_output.model_dump()
                        user_response = await self._request_user_input(
                            context,
                            UserInputType.APPROVE_PLAN,
                            {"plan": plan_data}
                        )
                        # 承認ペイロードがApprovePayloadまたはdictの場合に対応
                        approved = False
                        if isinstance(user_response, ApprovePayload):
                            approved = user_response.approved
                        elif isinstance(user_response, dict):
                            approved = bool(user_response.get("approved"))
                        if approved:
                            console.print(f"[green]クライアントが第{phase_num}段階リサーチ計画を承認しました。[/green]")
                            context.current_step = "researching" # リサーチ開始
                            context.current_research_query_index = 0
                            # このフェーズの結果リストを初期化
                            while len(context.research_results_by_phase) <= context.current_research_plan_index:
                                context.research_results_by_phase.append([])
                            await self._send_server_event(context, StatusUpdatePayload(step=context.current_step, message=f"Phase {phase_num} research plan approved, starting research."))
                        else:
                            raise ValueError(f"第{phase_num}段階リサーチ計画が承認されませんでした。")
                    elif isinstance(agent_output, ClarificationNeeded):
                         raise ValueError(f"リサーチ計画生成で確認が必要になりました: {agent_output.message}")
                    else:
                         raise TypeError(f"予期しないAgent出力タイプ: {type(agent_output)}")

                elif context.current_step == "researching":
                    if not context.research_plan: raise ValueError("リサーチ計画がありません。")
                    if context.current_research_query_index >= len(context.research_plan.queries):
                        context.current_step = "research_synthesizing"
                        console.print("[green]全クエリのリサーチが完了しました。要約ステップに移ります。[/green]")
                        await self._send_server_event(context, StatusUpdatePayload(step=context.current_step, message="All research queries completed, synthesizing results."))
                        continue

                    current_agent = researcher_agent
                    current_query_obj = context.research_plan.queries[context.current_research_query_index]
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
                        context.current_step = "outline_generation"
                        await self._send_server_event(context, StatusUpdatePayload(step=context.current_step, message="Research report generated, generating outline."))
                    else:
                        raise TypeError(f"予期しないAgent出力タイプ: {type(agent_output)}")

                elif context.current_step == "outline_generation":
                    current_agent = outline_agent
                    if not context.selected_theme: raise ValueError("テーマが選択されていません。")
                    if not context.research_report: raise ValueError("リサーチレポートがありません。")
                    agent_input = f"選択されたテーマ「{context.selected_theme.title}」、詳細リサーチレポート、目標文字数 {context.target_length or '指定なし'} に基づいてアウトラインを作成してください。"
                    console.print(f"🤖 {current_agent.name} にアウトライン作成を依頼します...")
                    agent_output = await self._run_agent(current_agent, agent_input, context, run_config)

                    if isinstance(agent_output, Outline):
                        context.generated_outline = agent_output
                        context.current_step = "outline_generated" # ユーザー承認待ちステップへ
                        console.print("[cyan]アウトラインを生成しました。クライアントの承認を待ちます...[/cyan]")
                        # WebSocketでアウトラインを送信し、承認を要求
                        def outline_section_to_dict(section: OutlineSection) -> Dict[str, Any]:
                            data = section.model_dump(exclude={'subsections'})
                            if section.subsections:
                                data['subsections'] = [outline_section_to_dict(sub) for sub in section.subsections]
                            return data
                        outline_data = {
                            "title": agent_output.title,
                            "suggested_tone": agent_output.suggested_tone,
                            "sections": [outline_section_to_dict(s) for s in agent_output.sections]
                        }
                        user_response = await self._request_user_input(
                            context,
                            UserInputType.APPROVE_OUTLINE,
                            {"outline": outline_data}
                        )
                        # 承認ペイロードがApprovePayloadまたはdictの場合に対応
                        approved = False
                        if isinstance(user_response, ApprovePayload):
                            approved = user_response.approved
                        elif isinstance(user_response, dict):
                            approved = bool(user_response.get("approved"))
                        if approved:
                            console.print("[green]クライアントがアウトラインを承認しました。[/green]")
                            context.current_step = "writing_sections" # 執筆開始
                            context.current_section_index = 0
                            context.generated_sections_html = []
                            context.clear_section_writer_history()
                            from services.agents import create_section_writer_instructions, SECTION_WRITER_AGENT_BASE_PROMPT
                            base_instruction_text = await create_section_writer_instructions(SECTION_WRITER_AGENT_BASE_PROMPT)(RunContextWrapper(context=context), section_writer_agent)
                            context.add_to_section_writer_history("system", base_instruction_text)
                            await self._send_server_event(context, StatusUpdatePayload(step=context.current_step, message="Outline approved, starting section writing."))
                        else:
                            raise ValueError("アウトラインが承認されませんでした。")
                    elif isinstance(agent_output, ClarificationNeeded):
                        raise ValueError(f"アウトライン生成で確認が必要になりました: {agent_output.message}")
                    else:
                        raise TypeError(f"予期しないAgent出力タイプ: {type(agent_output)}")

                elif context.current_step == "writing_sections":
                    if not context.generated_outline: raise ValueError("アウトラインがありません。")
                    if context.current_section_index >= len(context.generated_outline.sections):
                        context.full_draft_html = context.get_full_draft()
                        context.current_step = "editing"
                        console.print("[green]全セクションの執筆が完了しました。編集ステップに移ります。[/green]")
                        await self._send_server_event(context, EditingStartPayload())
                        continue

                    current_agent = section_writer_agent
                    target_index = context.current_section_index
                    target_heading = context.generated_outline.sections[target_index].heading

                    user_request = f"前のセクション（もしあれば）に続けて、アウトラインのセクション {target_index + 1}「{target_heading}」の内容をHTMLで執筆してください。提供された詳細リサーチ情報を参照し、必要に応じて出典へのリンクを含めてください。"
                    current_input_messages: List[Dict[str, Any]] = list(context.section_writer_history)
                    current_input_messages.append({"role": "user", "content": [{"type": "input_text", "text": user_request}]})
                    agent_input = current_input_messages

                    console.print(f"🤖 {current_agent.name} にセクション {target_index + 1} の執筆を依頼します (Streaming)...")
                    await self._send_server_event(context, StatusUpdatePayload(step=context.current_step, message=f"Writing section {target_index + 1}: {target_heading}"))

                    accumulated_html = ""
                    stream_result = None
                    last_exception = None

                    for attempt in range(settings.max_retries):
                        try:
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
                            console.print(f"\n[yellow]ストリーミング中にエラー発生 (試行 {attempt + 1}/{settings.max_retries}): {type(e).__name__} - {e}[/yellow]")
                            if isinstance(e, (BadRequestError, MaxTurnsExceeded, ModelBehaviorError, UserError, AuthenticationError)):
                                break # リトライしないエラー
                            if attempt < settings.max_retries - 1:
                                delay = settings.initial_retry_delay * (2 ** attempt)
                                await asyncio.sleep(delay)
                            else:
                                context.error_message = f"ストリーミングエラー: {str(e)}"
                                context.current_step = "error"
                                break

                    if context.current_step == "error": break
                    if last_exception: raise last_exception

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
                        # WebSocketで最終結果を送信
                        await self._send_server_event(context, FinalResultPayload(
                            title=agent_output.title,
                            final_html_content=agent_output.final_html_content
                        ))
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
        for attempt in range(settings.max_retries):
            try:
                console.print(f"[dim]エージェント {agent.name} 実行開始 (試行 {attempt + 1}/{settings.max_retries})...[/dim]")
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
                     if isinstance(output, (ThemeProposal, Outline, RevisedArticle, ClarificationNeeded, StatusUpdate, ResearchPlan, ResearchQueryResult, ResearchReport)):
                         return output
                     elif isinstance(output, str):
                         try:
                             parsed_output = json.loads(output)
                             status_val = parsed_output.get("status") # 変数名を変更
                             output_model_map = {
                                 "theme_proposal": ThemeProposal, "outline": Outline, "revised_article": RevisedArticle,
                                 "clarification_needed": ClarificationNeeded, "status_update": StatusUpdate,
                                 "research_plan": ResearchPlan, "research_query_result": ResearchQueryResult, "research_report": ResearchReport,
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
                console.print(f"[yellow]エージェント {agent.name} 実行中にエラー (試行 {attempt + 1}/{settings.max_retries}): {type(e).__name__} - {e}[/yellow]")
                if isinstance(e, (BadRequestError, MaxTurnsExceeded, ModelBehaviorError, UserError, AuthenticationError)):
                    break
                if attempt < settings.max_retries - 1:
                    delay = settings.initial_retry_delay * (2 ** attempt)
                    await asyncio.sleep(delay)
                else:
                    break

        if last_exception:
            console.print(f"[bold red]エージェント {agent.name} の実行に失敗しました（リトライ上限到達）。[/bold red]")
            raise last_exception
        raise RuntimeError(f"Agent {agent.name} execution finished unexpectedly.")

# WebSocketStateのインポートを追加 (エラーハンドリングで使用)
from starlette.websockets import WebSocketState # <<< WebSocketState をインポート
