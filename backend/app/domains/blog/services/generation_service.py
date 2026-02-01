# -*- coding: utf-8 -*-
"""
Blog AI Domain - Generation Service

ブログ記事生成サービス（OpenAI Agents SDK Runner.run_streamed() を使用）

会話履歴を保持し、ユーザー質問→回答後に同一コンテキストで生成を継続する。
"""

import json
import re
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from agents import Runner, RunConfig
from agents.stream_events import (
    AgentUpdatedStreamEvent,
    RawResponsesStreamEvent,
    RunItemStreamEvent,
)
from agents.items import (
    ToolCallItem,
    ToolCallOutputItem,
    ReasoningItem,
    MessageOutputItem,
)

from app.common.database import supabase
from app.domains.usage.service import usage_service
import logging

from app.core.config import settings
from app.domains.blog.agents.definitions import build_blog_writer_agent
from app.domains.blog.services.wordpress_mcp_service import (
    clear_mcp_client_cache,
    set_mcp_context,
)
try:
    from app.infrastructure.logging.service import LoggingService
    LOGGING_SERVICE_AVAILABLE = True
except Exception:
    LoggingService = None  # type: ignore
    LOGGING_SERVICE_AVAILABLE = False

try:
    from app.infrastructure.analysis.cost_calculation_service import CostCalculationService
except Exception:
    CostCalculationService = None  # type: ignore

logger = logging.getLogger(__name__)


# フロントエンドのステップキー（steps配列と一致させる）
# { key: "初期化中", label: "初期化" },
# { key: "参考記事分析中", label: "参考記事分析" },
# { key: "情報収集中", label: "情報収集" },
# { key: "記事生成中", label: "記事生成" },
# { key: "下書き作成中", label: "下書き作成" },

# ツール名 → (ステップフェーズ, フレンドリーメッセージ)
TOOL_STEP_MAPPING: Dict[str, tuple[str, str]] = {
    # 記事取得系 → 参考記事分析フェーズ
    "wp_get_posts_by_category": ("参考記事分析中", "カテゴリの記事一覧を取得しています"),
    "wp_get_post_block_structure": ("参考記事分析中", "記事のブロック構造を分析しています"),
    "wp_get_post_raw_content": ("参考記事分析中", "記事のコンテンツを読み込んでいます"),
    "wp_get_recent_posts": ("参考記事分析中", "最近の記事一覧を取得しています"),
    "wp_get_post_by_url": ("参考記事分析中", "URLから記事を取得しています"),
    "wp_analyze_category_format_patterns": ("参考記事分析中", "カテゴリの記事パターンを分析しています"),
    # ブロック・テーマ系 → 情報収集フェーズ
    "wp_extract_used_blocks": ("情報収集中", "使用されているブロックを分析しています"),
    "wp_get_theme_styles": ("情報収集中", "テーマスタイルを取得しています"),
    "wp_get_block_patterns": ("情報収集中", "ブロックパターン一覧を取得しています"),
    "wp_get_reusable_blocks": ("情報収集中", "再利用ブロック一覧を取得しています"),
    # 記事作成系 → 下書き作成フェーズ
    "wp_create_draft_post": ("下書き作成中", "下書き記事を作成しています"),
    "wp_update_post_content": ("下書き作成中", "記事コンテンツを更新しています"),
    "wp_update_post_meta": ("下書き作成中", "記事メタ情報を更新しています"),
    # バリデーション系 → 記事生成フェーズ
    "wp_validate_block_content": ("記事生成中", "ブロック構文をチェックしています"),
    "wp_check_regulation_compliance": ("記事生成中", "レギュレーション準拠をチェックしています"),
    "wp_check_seo_requirements": ("記事生成中", "SEO要件をチェックしています"),
    # メディア系 → 記事生成フェーズ
    "wp_get_media_library": ("記事生成中", "メディアライブラリを取得しています"),
    "wp_upload_media": ("記事生成中", "メディアをアップロードしています"),
    "wp_set_featured_image": ("下書き作成中", "アイキャッチ画像を設定しています"),
    # タクソノミー・サイト情報系 → 初期化/情報収集フェーズ
    "wp_get_categories": ("情報収集中", "カテゴリ一覧を取得しています"),
    "wp_get_tags": ("情報収集中", "タグ一覧を取得しています"),
    "wp_create_term": ("記事生成中", "カテゴリ/タグを作成しています"),
    "wp_get_site_info": ("初期化中", "サイト情報を取得しています"),
    "wp_get_post_types": ("初期化中", "投稿タイプ一覧を取得しています"),
    "wp_get_article_regulations": ("情報収集中", "レギュレーション設定を取得しています"),
    # ユーザー質問
    "ask_user_questions": ("情報収集中", "ユーザーに追加情報を確認しています"),
    # Web検索
    "web_search": ("リサーチ中", "Webで情報を検索しています"),
}

# 組み込みツールの type → ツール名マッピング
# OpenAI の組み込みツール（WebSearchTool等）は raw_item に "name" 属性がなく "type" で識別する
_BUILTIN_TOOL_TYPE_MAP: Dict[str, str] = {
    "web_search_call": "web_search",
    "file_search_call": "file_search",
    "code_interpreter_call": "code_interpreter",
    "image_generation_call": "image_generation",
    "computer_call": "computer_use",
    "mcp_call": "mcp_call",
}


def _resolve_tool_name(raw_item: Any) -> str:
    """ToolCallItem の raw_item からツール名を解決する。

    function_tool の場合は raw_item.name、組み込みツール（WebSearchTool等）の場合は
    raw_item.type から逆引きする。
    """
    name = getattr(raw_item, "name", None)
    if name:
        return name
    item_type = getattr(raw_item, "type", None)
    if item_type and item_type in _BUILTIN_TOOL_TYPE_MAP:
        return _BUILTIN_TOOL_TYPE_MAP[item_type]
    return "unknown_tool"


class BlogGenerationService:
    """
    ブログ記事生成サービス

    OpenAI Agents SDK の Runner.run_streamed() を使用して、
    エージェントベースでブログ記事を生成し、リアルタイムで進捗を通知する。

    会話履歴は result.to_input_list() で取得し、DBに保存する。
    ユーザー質問→回答後は、保存した会話履歴に回答を追加して
    同一コンテキストで生成を継続する。
    """

    def __init__(self):
        self._agent = build_blog_writer_agent()

    # ===========================================================
    # 公開メソッド
    # ===========================================================

    async def run_generation(
        self,
        process_id: str,
        user_id: str,
        user_prompt: str,
        reference_url: Optional[str],
        wordpress_site: Dict[str, Any],
    ) -> None:
        """
        ブログ生成を実行（初回起動）

        Args:
            process_id: プロセスID（既にDBに作成済み）
            user_id: ユーザーID
            user_prompt: ユーザーの記事作成リクエスト
            reference_url: 参考記事URL
            wordpress_site: WordPressサイト情報
        """
        try:
            # 状態を更新
            await self._update_state(
                process_id,
                status="in_progress",
                current_step_name="初期化中 - 記事生成を準備しています",
                progress_percentage=5,
            )
            await self._publish_event(
                process_id, user_id,
                "generation_started",
                {"step": "initializing", "message": "記事生成を開始しました"},
            )

            # MCPクライアントキャッシュをクリアし、コンテキストを設定
            clear_mcp_client_cache(wordpress_site["id"])
            set_mcp_context(
                site_id=wordpress_site["id"],
                user_id=user_id,
                process_id=process_id,
            )

            # アップロード済み画像を取得
            db_images = supabase.table("blog_generation_state").select(
                "uploaded_images"
            ).eq("id", process_id).single().execute()
            uploaded_images = (
                db_images.data.get("uploaded_images", [])
                if db_images.data else []
            )

            # 入力メッセージを構築（画像対応）
            input_message = self._build_input_message(
                user_prompt, reference_url, wordpress_site, uploaded_images,
            )

            # RunConfig設定（group_id で同一プロセスのトレースを紐付け）
            run_config = RunConfig(
                group_id=process_id,
                workflow_name="Blog Generation",
                trace_metadata={
                    "process_id": process_id,
                    "user_id": user_id,
                    "site_id": wordpress_site["id"],
                }
            )

            # ログセッションを確保（ブログAI用）
            log_session_id = self._get_or_create_log_session(
                process_id=process_id,
                user_id=user_id,
                organization_id=self._get_user_org_for_usage(user_id),
                wordpress_site_id=wordpress_site.get("id"),
                initial_input={
                    "user_prompt": user_prompt,
                    "reference_url": reference_url,
                },
            )

            # エージェント実行（共通メソッド）
            await self._run_agent_streamed(
                process_id=process_id,
                user_id=user_id,
                agent_input=input_message,
                run_config=run_config,
                previous_response_id=None,
                base_progress=5,
                log_session_id=log_session_id,
            )

        except Exception as e:
            logger.error(f"生成エラー: {e}", exc_info=True)
            await self._update_state(
                process_id,
                status="error",
                error_message=str(e),
            )
            await self._publish_event(
                process_id, user_id,
                "generation_error",
                {"error": str(e), "message": f"エラーが発生しました: {str(e)}"},
            )

    async def continue_generation(
        self,
        process_id: str,
        user_id: str,
        user_answers: Dict[str, Any],
        wordpress_site: Dict[str, Any],
    ) -> None:
        """
        ユーザー入力後に生成を継続（会話履歴を復元して同一コンテキストで再開）

        Args:
            process_id: プロセスID
            user_id: ユーザーID
            user_answers: ユーザーの回答（question_id → 回答テキスト）
            wordpress_site: WordPressサイト情報
        """
        try:
            # 現在の状態を取得
            db_result = supabase.table("blog_generation_state").select(
                "blog_context"
            ).eq("id", process_id).single().execute()

            if not db_result.data:
                raise Exception("プロセスが見つかりません")

            blog_context = db_result.data.get("blog_context", {})
            conversation_history = blog_context.get("conversation_history")
            previous_response_id = blog_context.get("last_response_id")

            if not conversation_history:
                raise Exception(
                    "会話履歴が見つかりません。最初から生成をやり直してください。"
                )

            # 状態を更新
            await self._update_state(
                process_id,
                status="in_progress",
                current_step_name="記事生成中 - 回答を反映しています",
                progress_percentage=45,
                is_waiting_for_input=False,
            )
            await self._publish_event(
                process_id, user_id,
                "generation_resumed",
                {"message": "追加情報を受け取りました。生成を再開します..."},
            )

            # MCPクライアントキャッシュをクリアし、コンテキストを設定
            clear_mcp_client_cache(wordpress_site["id"])
            set_mcp_context(
                site_id=wordpress_site["id"],
                user_id=user_id,
                process_id=process_id,
            )

            # ユーザーの回答メッセージを構築（画像対応）
            answer_content = self._build_user_answer_message(
                user_answers,
                blog_context.get("ai_questions", []),
                process_id=process_id,
            )

            # RunConfig設定（group_id で初回トレースと紐付け）
            run_config = RunConfig(
                group_id=process_id,
                workflow_name="Blog Generation (continued)",
                trace_metadata={
                    "process_id": process_id,
                    "user_id": user_id,
                    "site_id": wordpress_site["id"],
                    "is_continuation": "true",
                }
            )

            # ログセッションを確保（ブログAI用）
            log_session_id = self._get_or_create_log_session(
                process_id=process_id,
                user_id=user_id,
                organization_id=self._get_user_org_for_usage(user_id),
                wordpress_site_id=wordpress_site.get("id"),
                initial_input={
                    "user_prompt": blog_context.get("user_prompt"),
                    "reference_url": blog_context.get("reference_url"),
                    "is_continuation": True,
                },
            )

            # previous_response_id が使える場合:
            #   サーバー側が前回までの会話を保持しているため、
            #   新しいユーザーメッセージだけ送れば十分（トークン節約）
            # 使えない場合:
            #   to_input_list() の会話履歴全体 + 新メッセージを送信
            is_multimodal = isinstance(answer_content, list)

            if previous_response_id:
                logger.info(
                    f"previous_response_id使用: {previous_response_id} "
                    f"（サーバー側会話復元、新メッセージのみ送信, "
                    f"multimodal={is_multimodal}）"
                )
                # マルチモーダルの場合はそのまま list を渡す
                # テキストの場合は string を渡す
                agent_input: Any = answer_content
            else:
                logger.info(
                    "previous_response_id なし: "
                    f"会話履歴 {len(conversation_history)} アイテム + 新メッセージを送信"
                )
                continued_input = list(conversation_history)
                if is_multimodal:
                    # マルチモーダル: [{role: user, content: [...]}] を展開して追加
                    continued_input.extend(answer_content)
                else:
                    continued_input.append({
                        "role": "user",
                        "content": answer_content,
                    })
                agent_input = continued_input

            # エージェント実行（同一エージェント・会話コンテキスト維持）
            await self._run_agent_streamed(
                process_id=process_id,
                user_id=user_id,
                agent_input=agent_input,
                run_config=run_config,
                previous_response_id=previous_response_id,
                base_progress=45,
                log_session_id=log_session_id,
            )

        except Exception as e:
            logger.error(f"継続生成エラー: {e}", exc_info=True)
            await self._update_state(
                process_id,
                status="error",
                error_message=str(e),
            )
            await self._publish_event(
                process_id, user_id,
                "generation_error",
                {"error": str(e), "message": f"エラーが発生しました: {str(e)}"},
            )

    async def get_process_state(self, process_id: str) -> Optional[Dict[str, Any]]:
        """プロセス状態を取得"""
        result = supabase.table("blog_generation_state").select(
            "*"
        ).eq("id", process_id).single().execute()
        return result.data

    async def cancel_generation(self, process_id: str) -> bool:
        """生成をキャンセル"""
        result = supabase.table("blog_generation_state").select(
            "user_id"
        ).eq("id", process_id).single().execute()

        if not result.data:
            return False

        user_id = result.data.get("user_id")
        await self._update_state(process_id, status="cancelled")
        await self._publish_event(
            process_id, user_id,
            "generation_cancelled",
            {"message": "記事生成がキャンセルされました"},
        )
        return True

    # ===========================================================
    # コアエージェント実行（初回・継続共通）
    # ===========================================================

    async def _run_agent_streamed(
        self,
        process_id: str,
        user_id: str,
        agent_input: Any,  # str | list[TResponseInputItem]
        run_config: RunConfig,
        previous_response_id: Optional[str],
        base_progress: int = 5,
        log_session_id: Optional[str] = None,
    ) -> None:
        """
        エージェントをストリーミング実行し、結果を処理する（初回・継続共通）

        Args:
            process_id: プロセスID
            user_id: ユーザーID
            agent_input: エージェントへの入力（文字列 or 会話履歴リスト）
            run_config: RunConfig
            previous_response_id: 前回のレスポンスID（継続時）
            base_progress: 進捗バーの開始位置
        """
        logger.info(
            f"Agent実行開始（ストリーミング）: process_id={process_id}, "
            f"input_type={'list' if isinstance(agent_input, list) else 'str'}, "
            f"previous_response_id={previous_response_id}"
        )

        execution_start = time.time()
        logging_service = LoggingService() if LOGGING_SERVICE_AVAILABLE else None
        execution_id: Optional[str] = None
        tool_call_log_ids: Dict[str, str] = {}
        tool_call_start_times: Dict[str, float] = {}

        if log_session_id and logging_service:
            try:
                step_number = self._get_next_execution_step(log_session_id)
                execution_id = logging_service.create_execution_log(
                    session_id=log_session_id,
                    agent_name=self._agent.name,
                    agent_type="blog_generation",
                    step_number=step_number,
                    input_data={
                        "process_id": process_id,
                        "previous_response_id": previous_response_id,
                        "input_type": "list" if isinstance(agent_input, list) else "str",
                    },
                    llm_model=settings.blog_generation_model,
                    execution_metadata={
                        "workflow_type": "blog_generation",
                        "process_id": process_id,
                        "user_id": user_id,
                    },
                )
            except Exception as log_err:
                logger.warning(f"Failed to create execution log: {log_err}")
                execution_id = None

        try:
            result = Runner.run_streamed(
                self._agent,
                agent_input,
                run_config=run_config,
                max_turns=settings.blog_generation_max_turns,
                previous_response_id=previous_response_id,
            )

            tool_call_count = 0
            total_estimated_tools = 10
            # ask_user_questions のツール呼び出し引数をキャプチャ
            pending_user_questions: Optional[Dict[str, Any]] = None

            async for event in result.stream_events():
                # ツール呼び出しログ
                if execution_id and logging_service and isinstance(event, RunItemStreamEvent):
                    if isinstance(event.item, ToolCallItem):
                        tool_name = _resolve_tool_name(event.item.raw_item)
                        call_id = (
                            getattr(event.item.raw_item, "call_id", None)
                            or getattr(event.item.raw_item, "id", None)
                            or f"{tool_name}:{tool_call_count + 1}"
                        )
                        tool_call_start_times[call_id] = time.time()
                        raw_args = getattr(event.item.raw_item, "arguments", None)
                        parsed_args: Dict[str, Any] | str | None
                        if isinstance(raw_args, str):
                            try:
                                parsed_args = json.loads(raw_args)
                            except json.JSONDecodeError:
                                parsed_args = raw_args
                        else:
                            parsed_args = raw_args
                        try:
                            tool_call_log_id = logging_service.create_tool_call_log(
                                execution_id=execution_id,
                                tool_name=tool_name,
                                tool_function=tool_name,
                                call_sequence=tool_call_count + 1,
                                input_parameters=parsed_args if isinstance(parsed_args, dict) else {"raw": parsed_args},
                                status="started",
                                tool_metadata={
                                    "call_id": call_id,
                                },
                            )
                            tool_call_log_ids[call_id] = tool_call_log_id
                        except Exception as log_err:
                            logger.debug(f"Failed to log tool call start: {log_err}")
                    elif isinstance(event.item, ToolCallOutputItem):
                        call_id = getattr(event.item.raw_item, "call_id", None)
                        if call_id and call_id in tool_call_log_ids:
                            duration_ms = None
                            if call_id in tool_call_start_times:
                                duration_ms = int((time.time() - tool_call_start_times[call_id]) * 1000)
                            try:
                                logging_service.update_tool_call_log(
                                    call_id=tool_call_log_ids[call_id],
                                    status="completed",
                                    output_data={"output": str(event.item.output)[:1000]},
                                    execution_time_ms=duration_ms,
                                )
                            except Exception as log_err:
                                logger.debug(f"Failed to update tool call log: {log_err}")

                await self._handle_stream_event(
                    event, process_id, user_id,
                    tool_call_count, total_estimated_tools,
                    base_progress,
                )
                if isinstance(event, RunItemStreamEvent):
                    if isinstance(event.item, ToolCallItem):
                        tool_call_count += 1
                        # ask_user_questions の引数を検出
                        tool_name = _resolve_tool_name(event.item.raw_item)
                        if tool_name == "ask_user_questions":
                            pending_user_questions = self._extract_user_questions(
                                event.item.raw_item
                            )

            # 最終結果を取得
            final_result = result.final_output
            logger.info(f"Agent実行完了: process_id={process_id}")
            logger.debug(
                f"Agent出力: {final_result[:500] if final_result else 'None'}..."
            )

            # ========================================
            # 会話履歴を取得（to_input_list）
            # ========================================
            try:
                conversation_history = result.to_input_list()
                last_response_id = result.last_response_id
                logger.info(
                    f"会話履歴保存: {len(conversation_history)}アイテム, "
                    f"last_response_id={last_response_id}"
                )
            except Exception as hist_err:
                logger.warning(f"会話履歴取得エラー: {hist_err}")
                conversation_history = None
                last_response_id = None

            # ========================================
            # LLM使用量ログ
            # ========================================
            self._finalize_execution_logging(
                result=result,
                execution_id=execution_id,
                logging_service=logging_service,
                started_at=execution_start,
            )

            # ========================================
            # ユーザー質問検出 → 入力待ち遷移
            # ========================================
            if pending_user_questions:
                logger.info(
                    f"ユーザー入力待ち: process_id={process_id}, "
                    f"questions={len(pending_user_questions['questions'])}"
                )
                blog_ctx: Dict[str, Any] = {
                    "ai_questions": pending_user_questions["questions"],
                    "question_context": pending_user_questions.get("context"),
                }
                if final_result:
                    blog_ctx["agent_message"] = final_result
                # 会話履歴を保存（次回継続時に使用）
                if conversation_history is not None:
                    blog_ctx["conversation_history"] = conversation_history
                if last_response_id:
                    blog_ctx["last_response_id"] = last_response_id

                await self._update_state(
                    process_id,
                    status="user_input_required",
                    current_step_name="ユーザー入力待ち",
                    progress_percentage=40,
                    is_waiting_for_input=True,
                    input_type="questions",
                    blog_context=blog_ctx,
                )
                await self._publish_event(
                    process_id, user_id,
                    "user_input_required",
                    {
                        "questions": pending_user_questions["questions"],
                        "context": pending_user_questions.get("context"),
                        "message": pending_user_questions.get("context")
                            or "記事作成に必要な情報を入力してください",
                    },
                )
                return

            # ========================================
            # 通常完了: 結果を処理
            # ========================================
            await self._update_state(
                process_id,
                current_step_name="下書き作成中 - 結果を処理しています",
                progress_percentage=90,
            )
            await self._publish_event(
                process_id, user_id,
                "processing_result",
                {"message": "結果を処理しています..."},
            )
            await self._process_result(process_id, user_id, final_result or "")
        except Exception as e:
            if execution_id and logging_service:
                try:
                    logging_service.update_execution_log(
                        execution_id=execution_id,
                        status="failed",
                        duration_ms=int((time.time() - execution_start) * 1000),
                        error_message=str(e),
                    )
                except Exception as log_err:
                    logger.debug(f"Failed to mark execution failed: {log_err}")
            raise

    # ===========================================================
    # ストリームイベント処理
    # ===========================================================

    async def _handle_stream_event(
        self,
        event: Any,
        process_id: str,
        user_id: str,
        tool_call_count: int,
        total_estimated_tools: int,
        base_progress: int = 5,
    ) -> None:
        """ストリームイベントを処理して進捗を通知"""
        try:
            if isinstance(event, RunItemStreamEvent):
                item = event.item

                # ツール呼び出し開始
                if isinstance(item, ToolCallItem):
                    tool_name = _resolve_tool_name(item.raw_item)
                    step_info = TOOL_STEP_MAPPING.get(
                        tool_name, ("記事生成中", f"{tool_name}を実行しています")
                    )
                    step_phase, friendly_message = step_info

                    # 進捗を計算（base_progress〜85%の範囲で分配）
                    progress_range = 85 - base_progress
                    progress = min(
                        base_progress + int(
                            (tool_call_count / max(total_estimated_tools, 1))
                            * progress_range
                        ),
                        85
                    )

                    step_display = f"{step_phase} - {friendly_message}"

                    await self._update_state(
                        process_id,
                        current_step_name=step_display,
                        progress_percentage=progress,
                    )
                    await self._publish_event(
                        process_id, user_id,
                        "tool_call_started",
                        {
                            "tool_name": tool_name,
                            "step_phase": step_phase,
                            "message": friendly_message,
                            "progress": progress,
                        },
                    )
                    logger.debug(f"ツール呼び出し開始: {tool_name} ({step_phase})")

                # ツール呼び出し完了
                elif isinstance(item, ToolCallOutputItem):
                    call_id = getattr(item.raw_item, "call_id", None)
                    await self._publish_event(
                        process_id, user_id,
                        "tool_call_completed",
                        {
                            "tool_call_id": call_id,
                            "message": "処理が完了しました",
                        },
                    )

                # AI思考中（Reasoning）
                elif isinstance(item, ReasoningItem):
                    await self._publish_event(
                        process_id, user_id,
                        "reasoning",
                        {"message": "AIが考えています..."},
                    )

                # メッセージ出力
                elif isinstance(item, MessageOutputItem):
                    content = ""
                    if hasattr(item, 'content') and item.content:
                        for part in item.content:
                            if hasattr(part, 'text'):
                                content += part.text
                    if content:
                        await self._publish_event(
                            process_id, user_id,
                            "message_output",
                            {"content": content[:500]},
                        )

            elif isinstance(event, AgentUpdatedStreamEvent):
                agent_name = event.agent.name if hasattr(event, 'agent') else "Unknown"
                await self._publish_event(
                    process_id, user_id,
                    "agent_updated",
                    {"agent_name": agent_name},
                )

        except Exception as e:
            logger.warning(f"ストリームイベント処理エラー: {e}")

    # ===========================================================
    # ヘルパーメソッド
    # ===========================================================

    @staticmethod
    def _extract_user_questions(raw_item: Any) -> Optional[Dict[str, Any]]:
        """ToolCallItem の raw_item から ask_user_questions の引数を抽出（input_types対応）"""
        try:
            args_str = getattr(raw_item, "arguments", "{}")
            args_data = json.loads(args_str) if isinstance(args_str, str) else args_str
            questions_raw = args_data.get("questions", [])
            input_types_raw = args_data.get("input_types", [])
            context_raw = args_data.get("context")

            # input_types が不足している場合は "textarea" で補完
            if not input_types_raw:
                input_types_raw = ["textarea"] * len(questions_raw)
            elif len(input_types_raw) < len(questions_raw):
                input_types_raw = input_types_raw + ["textarea"] * (
                    len(questions_raw) - len(input_types_raw)
                )

            structured = []
            for i, q in enumerate(questions_raw):
                structured.append({
                    "question_id": f"q{i+1}",
                    "question": q,
                    "input_type": input_types_raw[i],
                })

            logger.info(
                f"ask_user_questions検出: {len(structured)}件の質問, "
                f"input_types={[s['input_type'] for s in structured]}"
            )
            return {
                "questions": structured,
                "context": context_raw,
            }
        except Exception as e:
            logger.warning(f"ask_user_questions引数パースエラー: {e}")
            return None

    @staticmethod
    def _build_input_message(
        user_prompt: str,
        reference_url: Optional[str],
        wordpress_site: Dict[str, Any],
        uploaded_images: Optional[List[Dict[str, Any]]] = None,
    ) -> Any:
        """初回入力メッセージを構築（画像対応）

        Args:
            user_prompt: ユーザーのリクエスト
            reference_url: 参考記事URL
            wordpress_site: WordPressサイト情報
            uploaded_images: アップロード済み画像情報

        Returns:
            str: テキストのみの場合
            list: マルチモーダル入力（画像あり）の場合
        """
        from app.domains.blog.services.image_utils import read_as_base64

        parts = [
            f"## リクエスト\n\n{user_prompt}",
        ]

        if reference_url:
            parts.append(f"\n## 参考記事URL\n\n{reference_url}")

        parts.append(
            f"\n## WordPressサイト情報\n\n"
            f"- サイトURL: {wordpress_site.get('site_url', '不明')}\n"
            f"- サイト名: {wordpress_site.get('site_name', '不明')}"
        )

        valid_images = []
        if uploaded_images:
            import os
            for img in uploaded_images:
                local_path = img.get("local_path")
                if local_path and os.path.exists(local_path):
                    valid_images.append(img)

        if valid_images:
            parts.append(
                f"\n## ユーザーアップロード画像\n\n"
                f"ユーザーが {len(valid_images)} 枚の画像をアップロードしています。\n"
                f"以下の画像が添付されています。記事内で活用したい場合は、"
                f"`upload_user_image_to_wordpress(image_index=N, alt=\"説明\")` "
                f"ツールで WordPress にアップロードしてから記事に挿入してください。\n"
            )
            for i, img in enumerate(valid_images):
                original = img.get("original_filename", img.get("filename", f"image_{i}"))
                parts.append(f"- 画像{i}: {original}")

        parts.append(
            "\n## 指示\n\n"
            "上記のリクエストに基づいて、WordPressブログ記事を作成してください。\n"
            "必ず `wp_create_draft_post` ツールを使って下書きを保存してください。"
        )

        text_content = "\n".join(parts)

        # 画像がない場合は従来通り string を返す
        if not valid_images:
            return text_content

        # 画像がある場合はマルチモーダル入力を構築
        content_parts: List[Dict[str, Any]] = [
            {"type": "input_text", "text": text_content}
        ]

        for img in valid_images:
            try:
                b64 = read_as_base64(img["local_path"])
                content_parts.append({
                    "type": "input_image",
                    "image_url": f"data:image/webp;base64,{b64}",
                })
            except Exception as e:
                logger.warning(f"画像読み込みエラー: {img.get('local_path')} - {e}")

        return [{"role": "user", "content": content_parts}]

    @staticmethod
    def _build_user_answer_message(
        user_answers: Dict[str, Any],
        ai_questions: List[Dict[str, Any]],
        process_id: Optional[str] = None,
    ) -> Any:
        """ユーザー回答メッセージを構築（画像回答対応）

        Args:
            user_answers: ユーザーの回答（question_id → 回答テキスト or "uploaded:filename"）
            ai_questions: AIからの質問リスト
            process_id: プロセスID（画像パス解決用）

        Returns:
            str: テキストのみの場合
            list: マルチモーダル入力（画像回答あり）の場合
        """
        from app.domains.blog.services.image_utils import read_as_base64

        # 質問IDと質問情報のマッピングを構築
        question_map = {
            q["question_id"]: q
            for q in ai_questions
        }

        text_parts = ["以下がユーザーからの回答です。この情報を活用して記事を作成してください。\n"]
        image_parts: List[Dict[str, Any]] = []

        has_any_answer = False
        for qid, answer in user_answers.items():
            if not answer or not str(answer).strip():
                continue

            has_any_answer = True
            question_obj = question_map.get(qid, {})
            question_text = question_obj.get("question", qid)
            input_type = question_obj.get("input_type", "textarea")

            # 画像アップロードの回答
            if input_type == "image_upload" and str(answer).startswith("uploaded:"):
                filenames = str(answer).replace("uploaded:", "").split(",")
                text_parts.append(f"**Q: {question_text}**")
                text_parts.append(f"A: (画像 {len(filenames)} 枚アップロード済み)\n")

                if process_id:
                    import os
                    from app.core.config import settings
                    upload_dir = os.path.join(
                        getattr(settings, "temp_upload_dir", None) or "/tmp/blog_uploads",
                        process_id,
                    )
                    for fname in filenames:
                        fname = fname.strip()
                        local_path = os.path.join(upload_dir, fname)
                        if os.path.exists(local_path):
                            try:
                                b64 = read_as_base64(local_path)
                                image_parts.append({
                                    "type": "input_image",
                                    "image_url": f"data:image/webp;base64,{b64}",
                                })
                            except Exception as e:
                                logger.warning(f"画像読み込みエラー: {local_path} - {e}")
            else:
                text_parts.append(f"**Q: {question_text}**")
                text_parts.append(f"A: {answer}\n")

        if not has_any_answer:
            text_parts.append(
                "（ユーザーは質問をスキップしました。"
                "リクエスト内容と参考記事の分析結果のみで記事を作成してください。）"
            )

        text_parts.append(
            "\n上記の情報をもとに、記事を作成して `wp_create_draft_post` で下書き保存してください。"
        )

        text_content = "\n".join(text_parts)

        # 画像がない場合は従来通り string を返す
        if not image_parts:
            return text_content

        # 画像がある場合はマルチモーダル入力を構築
        content_parts = [{"type": "input_text", "text": text_content}] + image_parts
        return [{"role": "user", "content": content_parts}]

    # ===========================================================
    # Logging helpers
    # ===========================================================

    def _get_or_create_log_session(
        self,
        process_id: str,
        user_id: str,
        organization_id: Optional[str],
        wordpress_site_id: Optional[str],
        initial_input: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """ブログAI用のログセッションを取得/作成"""
        if not LOGGING_SERVICE_AVAILABLE:
            return None

        try:
            existing = supabase.table("agent_log_sessions").select("id").eq(
                "article_uuid", process_id
            ).limit(1).execute()
            if existing.data:
                return existing.data[0]["id"]
        except Exception as e:
            logger.debug(f"Failed to lookup log session: {e}")

        try:
            logging_service = LoggingService()
            return logging_service.create_log_session(
                article_uuid=process_id,
                user_id=user_id,
                organization_id=organization_id,
                initial_input=initial_input or {},
                session_metadata={
                    "workflow_type": "blog_generation",
                    "process_id": process_id,
                    "wordpress_site_id": wordpress_site_id,
                },
            )
        except Exception as e:
            logger.warning(f"Failed to create log session: {e}")
            return None

    @staticmethod
    def _get_next_execution_step(session_id: str) -> int:
        """次の実行ステップ番号を取得"""
        try:
            result = supabase.table("agent_execution_logs").select(
                "id", count="exact"
            ).eq("session_id", session_id).execute()
            if result.count is not None:
                return int(result.count) + 1
            return len(result.data or []) + 1
        except Exception:
            return 1

    @staticmethod
    def _get_raw_responses(result: Any) -> Optional[List[Any]]:
        candidate_attrs = [
            "_raw_responses", "raw_responses", "_responses", "responses",
            "_RunResult__raw_responses", "__raw_responses", "new_items", "_new_items"
        ]
        for attr_name in candidate_attrs:
            if hasattr(result, attr_name):
                attr_value = getattr(result, attr_name)
                if attr_value and hasattr(attr_value, "__len__") and len(attr_value) > 0:
                    return list(attr_value)
        return None

    @staticmethod
    def _safe_get(obj: Any, key: str, default: Any = None) -> Any:
        if obj is None:
            return default
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    def _normalize_usage_entry(self, entry: Any) -> Dict[str, Any]:
        input_tokens = self._safe_get(entry, "input_tokens", None)
        if input_tokens is None:
            input_tokens = self._safe_get(entry, "prompt_tokens", 0)
        output_tokens = self._safe_get(entry, "output_tokens", None)
        if output_tokens is None:
            output_tokens = self._safe_get(entry, "completion_tokens", 0)

        input_details = self._safe_get(entry, "input_tokens_details")
        output_details = self._safe_get(entry, "output_tokens_details")

        cached_tokens = 0
        if input_details:
            cached_tokens = self._safe_get(input_details, "cached_tokens", 0)

        reasoning_tokens = 0
        if output_details:
            reasoning_tokens = self._safe_get(output_details, "reasoning_tokens", 0)

        return {
            "model": self._safe_get(entry, "model", None) or self._safe_get(entry, "model_name", None),
            "input_tokens": int(input_tokens or 0),
            "output_tokens": int(output_tokens or 0),
            "total_tokens": int(self._safe_get(entry, "total_tokens", 0) or 0),
            "cached_tokens": int(cached_tokens or 0),
            "reasoning_tokens": int(reasoning_tokens or 0),
            "response_id": self._safe_get(entry, "response_id", None) or self._safe_get(entry, "id", None),
        }

    def _extract_usage_entries(self, result: Any) -> List[Dict[str, Any]]:
        entries: List[Any] = []
        ctx = getattr(result, "context_wrapper", None)
        usage = getattr(ctx, "usage", None) if ctx else None
        if usage:
            for attr in ("request_usage_entries", "usage_entries", "request_usage"):
                value = getattr(usage, attr, None)
                if value:
                    try:
                        entries = list(value)
                    except TypeError:
                        entries = [value]
                    break

        if not entries:
            # Fallback: older SDKs or custom wrappers might expose entries directly
            for candidate in [ctx, result]:
                if not candidate:
                    continue
                for attr in ("request_usage_entries", "usage_entries", "request_usage"):
                    value = getattr(candidate, attr, None)
                    if value:
                        try:
                            entries = list(value)
                        except TypeError:
                            entries = [value]
                        break
                if entries:
                    break

        normalized = [self._normalize_usage_entry(entry) for entry in entries if entry is not None]
        # If entries lack model/response_id, try to enrich from raw responses
        raw_responses = self._get_raw_responses(result)
        if raw_responses:
            for i, entry in enumerate(normalized):
                if i < len(raw_responses):
                    raw = raw_responses[i]
                    if not entry.get("model"):
                        entry["model"] = self._safe_get(raw, "model", None)
                    if not entry.get("response_id"):
                        entry["response_id"] = self._safe_get(raw, "id", None)

        # Fallback: build entries directly from raw responses
        if not normalized and raw_responses:
            for raw in raw_responses:
                usage = self._safe_get(raw, "usage")
                if not usage:
                    continue
                entry = self._normalize_usage_entry(usage)
                if not entry.get("model"):
                    entry["model"] = self._safe_get(raw, "model", None)
                if not entry.get("response_id"):
                    entry["response_id"] = self._safe_get(raw, "id", None)
                normalized.append(entry)

        return normalized

    def _extract_usage_from_context_wrapper(self, result: Any) -> Optional[Dict[str, Any]]:
        ctx = getattr(result, "context_wrapper", None)
        usage = getattr(ctx, "usage", None) if ctx else None
        if not usage:
            return None

        input_tokens = self._safe_get(usage, "input_tokens", 0)
        output_tokens = self._safe_get(usage, "output_tokens", 0)
        total_tokens = self._safe_get(usage, "total_tokens", 0)
        input_details = self._safe_get(usage, "input_tokens_details")
        output_details = self._safe_get(usage, "output_tokens_details")

        cached_tokens = 0
        if input_details:
            cached_tokens = self._safe_get(input_details, "cached_tokens", 0)

        reasoning_tokens = 0
        if output_details:
            reasoning_tokens = self._safe_get(output_details, "reasoning_tokens", 0)

        # Usage doesn't always carry model; pull from last response if present
        model_name = self._safe_get(usage, "model", None)
        response_id = self._safe_get(usage, "response_id", None)
        raw_responses = self._get_raw_responses(result)
        if raw_responses:
            last = raw_responses[-1]
            if not model_name:
                model_name = self._safe_get(last, "model", None)
            if not response_id:
                response_id = self._safe_get(last, "id", None)

        return {
            "model": model_name,
            "input_tokens": int(input_tokens or 0),
            "output_tokens": int(output_tokens or 0),
            "total_tokens": int(total_tokens or 0),
            "cached_tokens": int(cached_tokens or 0),
            "reasoning_tokens": int(reasoning_tokens or 0),
            "response_id": response_id,
        }

    def _extract_usage_from_raw_responses(self, result: Any) -> Optional[Dict[str, Any]]:
        raw_responses = self._get_raw_responses(result)
        if not raw_responses:
            return None

        totals = {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "cached_tokens": 0,
            "reasoning_tokens": 0,
        }
        last_model = None
        last_response_id = None

        for response in raw_responses:
            usage = self._safe_get(response, "usage")
            if not usage:
                continue
            input_tokens = self._safe_get(usage, "input_tokens", 0)
            output_tokens = self._safe_get(usage, "output_tokens", 0)
            total_tokens = self._safe_get(usage, "total_tokens", 0)
            input_details = self._safe_get(usage, "input_tokens_details")
            output_details = self._safe_get(usage, "output_tokens_details")

            cached_tokens = self._safe_get(input_details, "cached_tokens", 0) if input_details else 0
            reasoning_tokens = self._safe_get(output_details, "reasoning_tokens", 0) if output_details else 0

            totals["input_tokens"] += int(input_tokens or 0)
            totals["output_tokens"] += int(output_tokens or 0)
            totals["total_tokens"] += int(total_tokens or 0)
            totals["cached_tokens"] += int(cached_tokens or 0)
            totals["reasoning_tokens"] += int(reasoning_tokens or 0)

            last_model = self._safe_get(response, "model", last_model)
            last_response_id = self._safe_get(response, "id", last_response_id)

        return {
            "model": last_model,
            "input_tokens": totals["input_tokens"],
            "output_tokens": totals["output_tokens"],
            "total_tokens": totals["total_tokens"],
            "cached_tokens": totals["cached_tokens"],
            "reasoning_tokens": totals["reasoning_tokens"],
            "response_id": last_response_id,
        }

    @staticmethod
    def _aggregate_usage(entries: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not entries:
            return None
        totals = {
            "input_tokens": 0,
            "output_tokens": 0,
            "cached_tokens": 0,
            "reasoning_tokens": 0,
            "total_tokens": 0,
            "model": entries[-1].get("model"),
        }
        for entry in entries:
            totals["input_tokens"] += int(entry.get("input_tokens", 0))
            totals["output_tokens"] += int(entry.get("output_tokens", 0))
            totals["cached_tokens"] += int(entry.get("cached_tokens", 0))
            totals["reasoning_tokens"] += int(entry.get("reasoning_tokens", 0))
            totals["total_tokens"] += int(entry.get("total_tokens", 0) or 0)
        return totals

    def _estimate_cost(self, usage: Dict[str, Any]) -> Optional[float]:
        if CostCalculationService is None:
            return None
        try:
            cost_info = CostCalculationService.calculate_cost(
                model_name=usage.get("model") or settings.blog_generation_model,
                prompt_tokens=int(usage.get("input_tokens", 0)),
                completion_tokens=int(usage.get("output_tokens", 0)),
                cached_tokens=int(usage.get("cached_tokens", 0)),
                reasoning_tokens=int(usage.get("reasoning_tokens", 0)),
                total_tokens=int(usage.get("total_tokens", 0)),
            )
            return cost_info["cost_breakdown"]["total_cost_usd"]
        except Exception:
            return None

    def _finalize_execution_logging(
        self,
        result: Any,
        execution_id: Optional[str],
        logging_service: Optional[Any],
        started_at: float,
    ) -> None:
        if not execution_id or not logging_service:
            return

        usage_entries = self._extract_usage_entries(result)
        usage_source = "context_wrapper"
        usage_summary = self._extract_usage_from_context_wrapper(result)
        if usage_summary is None:
            usage_source = "request_usage_entries"
            usage_summary = self._aggregate_usage(usage_entries)
        if usage_summary is None:
            usage_source = "raw_responses"
            usage_summary = self._extract_usage_from_raw_responses(result)

        duration_ms = int((time.time() - started_at) * 1000)

        try:
            logging_service.update_execution_log(
                execution_id=execution_id,
                status="completed",
                input_tokens=int((usage_summary or {}).get("input_tokens", 0)),
                output_tokens=int((usage_summary or {}).get("output_tokens", 0)),
                cache_tokens=int((usage_summary or {}).get("cached_tokens", 0)),
                reasoning_tokens=int((usage_summary or {}).get("reasoning_tokens", 0)),
                duration_ms=duration_ms,
            )
        except Exception as e:
            logger.debug(f"Failed to update execution log: {e}")

        # Optional consistency check between aggregate and context usage
        if usage_entries and usage_summary:
            agg = self._aggregate_usage(usage_entries)
            if agg and (
                agg.get("input_tokens") != usage_summary.get("input_tokens")
                or agg.get("output_tokens") != usage_summary.get("output_tokens")
            ):
                logger.info(
                    "Usage mismatch: context_wrapper vs request_usage_entries "
                    f"(context={usage_summary.get('input_tokens')}/{usage_summary.get('output_tokens')}, "
                    f"entries={agg.get('input_tokens')}/{agg.get('output_tokens')})"
                )

        # LLM呼び出しログ
        try:
            if usage_entries:
                for i, entry in enumerate(usage_entries):
                    cost = self._estimate_cost(entry)
                    logging_service.create_llm_call_log(
                        execution_id=execution_id,
                        call_sequence=i + 1,
                        api_type="responses_api",
                        model_name=entry.get("model") or settings.blog_generation_model,
                        provider="openai",
                        prompt_tokens=int(entry.get("input_tokens", 0)),
                        completion_tokens=int(entry.get("output_tokens", 0)),
                        total_tokens=int(entry.get("total_tokens", 0) or 0),
                        cached_tokens=int(entry.get("cached_tokens", 0)),
                        reasoning_tokens=int(entry.get("reasoning_tokens", 0)),
                        estimated_cost_usd=cost,
                        api_response_id=entry.get("response_id"),
                        response_data={
                            "usage_source": "request_usage_entries",
                            "response_id": entry.get("response_id"),
                        },
                    )
            elif usage_summary:
                cost = self._estimate_cost(usage_summary)
                logging_service.create_llm_call_log(
                    execution_id=execution_id,
                    call_sequence=1,
                    api_type="responses_api",
                    model_name=usage_summary.get("model") or settings.blog_generation_model,
                    provider="openai",
                    prompt_tokens=int(usage_summary.get("input_tokens", 0)),
                    completion_tokens=int(usage_summary.get("output_tokens", 0)),
                    total_tokens=int(usage_summary.get("total_tokens", 0)),
                    cached_tokens=int(usage_summary.get("cached_tokens", 0)),
                    reasoning_tokens=int(usage_summary.get("reasoning_tokens", 0)),
                    estimated_cost_usd=cost,
                    api_response_id=usage_summary.get("response_id"),
                    response_data={
                        "usage_source": usage_source,
                        "response_id": usage_summary.get("response_id"),
                    },
                )
        except Exception as e:
            logger.debug(f"Failed to create llm call logs: {e}")

    async def _process_result(
        self,
        process_id: str,
        user_id: str,
        output_text: str,
    ) -> None:
        """
        Agent実行結果を処理

        wp_create_draft_post の結果からプレビューURLなどを抽出
        """
        draft_info = self._extract_draft_info(output_text)

        blog_ctx: Dict[str, Any] = {}
        if output_text:
            blog_ctx["agent_message"] = output_text

        if draft_info:
            await self._update_state(
                process_id,
                status="completed",
                current_step_name="完了",
                progress_percentage=100,
                draft_post_id=draft_info.get("post_id"),
                draft_preview_url=draft_info.get("preview_url"),
                draft_edit_url=draft_info.get("edit_url"),
                blog_context=blog_ctx if blog_ctx else None,
            )
            await self._publish_event(
                process_id, user_id,
                "generation_completed",
                {
                    "draft_post_id": draft_info.get("post_id"),
                    "preview_url": draft_info.get("preview_url"),
                    "edit_url": draft_info.get("edit_url"),
                    "message": "記事の下書きが作成されました！",
                },
            )
        else:
            logger.warning(f"下書き情報が見つかりません: {output_text[:500]}")
            await self._update_state(
                process_id,
                status="completed",
                current_step_name="完了（下書きURL未取得）",
                progress_percentage=100,
                blog_context=blog_ctx if blog_ctx else None,
            )
            await self._publish_event(
                process_id, user_id,
                "generation_completed",
                {
                    "message": "記事生成は完了しましたが、下書きURLの取得に失敗しました。"
                        "WordPressの下書き一覧を確認してください。",
                    "output": output_text[:1000],
                },
            )

        # 生成成功時に使用量をカウント
        try:
            org_id = self._get_user_org_for_usage(user_id)
            usage_service.record_success(
                user_id=user_id,
                process_id=process_id,
                organization_id=org_id,
            )
            logger.info(f"Usage recorded for process {process_id}")
        except Exception as e:
            logger.error(f"Failed to record usage for process {process_id}: {e}")

    @staticmethod
    def _get_user_org_for_usage(user_id: str) -> Optional[str]:
        """ユーザーの使用量追跡対象の組織IDを取得"""
        try:
            # 1. upgraded_to_org_id を確認
            sub = supabase.table("user_subscriptions").select(
                "upgraded_to_org_id"
            ).eq("user_id", user_id).maybe_single().execute()
            if sub.data and sub.data.get("upgraded_to_org_id"):
                return sub.data["upgraded_to_org_id"]

            # 2. organization_members でアクティブな組織サブスクを探す
            memberships = supabase.table("organization_members").select(
                "organization_id"
            ).eq("user_id", user_id).execute()
            if memberships.data:
                org_ids = [m["organization_id"] for m in memberships.data]
                org_subs = supabase.table("organization_subscriptions").select(
                    "organization_id"
                ).in_("organization_id", org_ids).eq("status", "active").limit(1).execute()
                if org_subs.data:
                    return org_subs.data[0]["organization_id"]

            return None
        except Exception:
            return None

    @staticmethod
    def _extract_draft_info(output_text: str) -> Optional[Dict[str, Any]]:
        """Agent出力から下書き情報を抽出"""
        json_patterns = [
            r'\{[^{}]*"post_id"[^{}]*\}',
            r'\{[^{}]*"preview_url"[^{}]*\}',
            r'\{[^{}]*"id"[^{}]*"link"[^{}]*\}',
        ]

        for pattern in json_patterns:
            matches = re.findall(pattern, output_text, re.DOTALL)
            for match in matches:
                try:
                    data = json.loads(match)
                    if "post_id" in data or "id" in data:
                        return {
                            "post_id": data.get("post_id") or data.get("id"),
                            "preview_url": data.get("preview_url") or data.get("link"),
                            "edit_url": data.get("edit_url") or data.get("edit_link"),
                        }
                except json.JSONDecodeError:
                    continue

        preview_url_match = re.search(
            r'https?://[^\s]+[?&]preview[^\s]*',
            output_text
        )
        if preview_url_match:
            return {
                "post_id": None,
                "preview_url": preview_url_match.group(0),
                "edit_url": None,
            }

        post_id_match = re.search(r'"?post_id"?\s*[:=]\s*(\d+)', output_text)
        if post_id_match:
            return {
                "post_id": int(post_id_match.group(1)),
                "preview_url": None,
                "edit_url": None,
            }

        return None

    # ===========================================================
    # DB操作
    # ===========================================================

    async def _update_state(
        self,
        process_id: str,
        status: Optional[str] = None,
        current_step_name: Optional[str] = None,
        progress_percentage: Optional[int] = None,
        is_waiting_for_input: Optional[bool] = None,
        input_type: Optional[str] = None,
        draft_post_id: Optional[int] = None,
        draft_preview_url: Optional[str] = None,
        draft_edit_url: Optional[str] = None,
        error_message: Optional[str] = None,
        blog_context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """プロセス状態を更新"""
        update_data: Dict[str, Any] = {
            "updated_at": datetime.utcnow().isoformat(),
        }

        if status is not None:
            update_data["status"] = status
        if current_step_name is not None:
            update_data["current_step_name"] = current_step_name
        if progress_percentage is not None:
            update_data["progress_percentage"] = progress_percentage
        if is_waiting_for_input is not None:
            update_data["is_waiting_for_input"] = is_waiting_for_input
        if input_type is not None:
            update_data["input_type"] = input_type
        if draft_post_id is not None:
            update_data["draft_post_id"] = draft_post_id
        if draft_preview_url is not None:
            update_data["draft_preview_url"] = draft_preview_url
        if draft_edit_url is not None:
            update_data["draft_edit_url"] = draft_edit_url
        if error_message is not None:
            update_data["error_message"] = error_message
        if blog_context is not None:
            update_data["blog_context"] = blog_context

        supabase.table("blog_generation_state").update(
            update_data
        ).eq("id", process_id).execute()

    async def _publish_event(
        self,
        process_id: str,
        user_id: str,
        event_type: str,
        event_data: Dict[str, Any],
    ) -> None:
        """Realtimeイベントを発行"""
        try:
            result = supabase.table("blog_process_events").select(
                "event_sequence"
            ).eq("process_id", process_id).order(
                "event_sequence", desc=True
            ).limit(1).execute()

            next_sequence = 1
            if result.data:
                next_sequence = result.data[0]["event_sequence"] + 1

            supabase.table("blog_process_events").insert({
                "process_id": process_id,
                "user_id": user_id,
                "event_type": event_type,
                "event_data": event_data,
                "event_sequence": next_sequence,
            }).execute()
        except Exception as e:
            logger.warning(f"イベント発行失敗: {e}")


# シングルトンインスタンス
_generation_service: Optional[BlogGenerationService] = None


def get_generation_service() -> BlogGenerationService:
    """BlogGenerationServiceのシングルトンインスタンスを取得"""
    global _generation_service
    if _generation_service is None:
        _generation_service = BlogGenerationService()
    return _generation_service
