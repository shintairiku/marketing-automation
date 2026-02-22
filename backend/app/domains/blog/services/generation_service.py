# -*- coding: utf-8 -*-
"""
Blog AI Domain - Generation Service

ブログ記事生成サービス（OpenAI Agents SDK Runner.run_streamed() を使用）

会話履歴を保持し、ユーザー質問→回答後に同一コンテキストで生成を継続する。
"""

import asyncio
import hashlib
import json
import time
from collections import deque
from datetime import datetime
from typing import Any, Dict, List, Optional
import httpx

from agents import ModelSettings, Runner, RunConfig
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

from openai import APIConnectionError, APITimeoutError, AsyncOpenAI

from app.common.database import supabase
from app.domains.usage.service import usage_service
import logging

from app.core.config import settings
from app.domains.blog.agents.definitions import build_blog_writer_agent
from app.domains.blog.schemas import BlogCompletionOutput
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
    from app.infrastructure.analysis.cost_calculation_service import (
        CostCalculationService,
    )
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
    "wp_get_posts_by_category": (
        "参考記事分析中",
        "カテゴリの記事一覧を取得しています",
    ),
    "wp_get_post_block_structure": (
        "参考記事分析中",
        "記事のブロック構造を分析しています",
    ),
    "wp_get_post_raw_content": ("参考記事分析中", "記事のコンテンツを読み込んでいます"),
    "wp_get_recent_posts": ("参考記事分析中", "最近の記事一覧を取得しています"),
    "wp_get_post_by_url": ("参考記事分析中", "URLから記事を取得しています"),
    "wp_analyze_category_format_patterns": (
        "参考記事分析中",
        "カテゴリの記事パターンを分析しています",
    ),
    # ブロック・テーマ系 → 情報収集フェーズ
    "wp_extract_used_blocks": ("情報収集中", "使用されているブロックを分析しています"),
    "wp_get_theme_styles": ("情報収集中", "テーマスタイルを取得しています"),
    "wp_get_block_patterns": ("情報収集中", "ブロックパターン一覧を取得しています"),
    "wp_get_reusable_blocks": ("情報収集中", "再利用ブロック一覧を取得しています"),
    # 記事作成系 → 下書き作成フェーズ
    "wp_create_draft_post": ("下書き作成中", "下書き記事を作成しています"),
    "wp_update_post_content": ("下書き作成中", "記事コンテンツを更新しています"),
    "wp_update_post_meta": ("下書き作成中", "記事メタ情報を更新しています"),
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
    "wp_get_article_regulations": (
        "情報収集中",
        "レギュレーション設定を取得しています",
    ),
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

_TRACE_TEXT_LIMIT = 12000
_TRACE_IO_LIMIT = 20000


def _resolve_tool_name(raw_item: Any) -> str:
    """ToolCallItem の raw_item からツール名を解決する。

    function_tool の場合は raw_item.name、組み込みツール（WebSearchTool等）の場合は
    raw_item.type から逆引きする。
    """
    name = getattr(raw_item, "name", None)
    if name:
        return name
    item_type = (
        raw_item.get("type")
        if isinstance(raw_item, dict)
        else getattr(raw_item, "type", None)
    )
    if item_type:
        return _BUILTIN_TOOL_TYPE_MAP.get(item_type, str(item_type))
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
    # キャッシュ最適化ヘルパー
    # ===========================================================

    @staticmethod
    def _input_has_images(agent_input: Any) -> bool:
        """入力に input_image が含まれているかを判定する。"""
        if not isinstance(agent_input, list):
            return False
        for item in agent_input:
            content = (
                item.get("content")
                if isinstance(item, dict)
                else getattr(item, "content", None)
            )
            if not isinstance(content, list):
                continue
            for part in content:
                if isinstance(part, dict) and part.get("type") == "input_image":
                    return True
        return False

    def _build_prompt_cache_key(
        self,
        process_id: str,
        site_id: Optional[str],
        has_images: bool,
    ) -> str:
        """Prompt cache key を安定生成する。"""
        scope = (settings.blog_prompt_cache_scope or "site").strip().lower()
        if scope == "process":
            scope_part = f"process:{process_id}"
            scope_code = "p"
        elif scope == "global":
            scope_part = "global"
            scope_code = "g"
        else:
            scope_part = f"site:{site_id or 'unknown'}"
            scope_code = "s"

        model = (settings.blog_generation_model or "unknown").replace(":", "_")
        version = (settings.blog_prompt_cache_key_version or "v1").strip() or "v1"
        modality = "image" if has_images else "text"

        # OpenAI prompt_cache_key は最大64文字。可読な短い接頭辞 + 安定ハッシュで構成する。
        canonical = (
            f"workflow=blog_generation|version={version}|model={model}|"
            f"scope={scope_part}|modality={modality}"
        )
        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:24]

        def _slug(text: str, max_len: int) -> str:
            cleaned = "".join(
                ch if (ch.isalnum() or ch in "._-") else "_"
                for ch in (text or "")
            )
            return (cleaned or "x")[:max_len]

        version_short = _slug(version, 8)
        model_short = _slug(model, 12)
        modality_code = "img" if has_images else "txt"

        key = f"bai:{version_short}:{model_short}:{scope_code}:{modality_code}:{digest}"
        return key[:64]

    def _build_run_model_settings(
        self,
        process_id: str,
        site_id: Optional[str],
        has_images: bool,
    ) -> ModelSettings:
        """RunConfigに注入するモデル設定を構築（キャッシュ/並列ツール）。"""
        extra_body: Dict[str, Any] = {}
        if settings.blog_prompt_cache_enabled:
            extra_body["prompt_cache_key"] = self._build_prompt_cache_key(
                process_id=process_id,
                site_id=site_id,
                has_images=has_images,
            )

        prompt_cache_retention: Optional[str] = (
            "24h" if settings.blog_prompt_cache_retention_24h else None
        )

        return ModelSettings(
            parallel_tool_calls=settings.blog_generation_parallel_tool_calls,
            prompt_cache_retention=prompt_cache_retention,
            extra_body=extra_body or None,
        )

    def _build_blog_run_config(
        self,
        process_id: str,
        user_id: str,
        site_id: Optional[str],
        workflow_name: str,
        is_continuation: bool,
        has_images: bool,
    ) -> RunConfig:
        model_settings = self._build_run_model_settings(
            process_id=process_id,
            site_id=site_id,
            has_images=has_images,
        )
        return RunConfig(
            group_id=process_id,
            workflow_name=workflow_name,
            trace_metadata={
                "process_id": process_id,
                "user_id": user_id,
                "site_id": site_id,
                "is_continuation": str(is_continuation).lower(),
            },
            model_settings=model_settings,
        )

    @staticmethod
    def _extract_cache_metadata_from_run_config(run_config: RunConfig) -> Dict[str, Any]:
        model_settings = getattr(run_config, "model_settings", None)
        extra_body = getattr(model_settings, "extra_body", None) if model_settings else None
        prompt_cache_key = None
        if isinstance(extra_body, dict):
            prompt_cache_key = extra_body.get("prompt_cache_key")
        return {
            "prompt_cache_key": prompt_cache_key,
            "prompt_cache_retention": getattr(
                model_settings, "prompt_cache_retention", None
            )
            if model_settings
            else None,
            "parallel_tool_calls": getattr(model_settings, "parallel_tool_calls", None)
            if model_settings
            else None,
        }

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
                process_id,
                user_id,
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
            db_images = (
                supabase.table("blog_generation_state")
                .select("uploaded_images")
                .eq("id", process_id)
                .single()
                .execute()
            )
            uploaded_images = (
                db_images.data.get("uploaded_images", []) if db_images.data else []
            )

            # 入力メッセージを構築（画像対応）
            input_message = self._build_input_message(
                user_prompt,
                reference_url,
                wordpress_site,
                uploaded_images,
            )

            has_images = self._input_has_images(input_message)
            # RunConfig設定（group_id で同一プロセスのトレースを紐付け）
            run_config = self._build_blog_run_config(
                process_id=process_id,
                user_id=user_id,
                site_id=wordpress_site.get("id"),
                workflow_name="Blog Generation",
                is_continuation=False,
                has_images=has_images,
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
            await self._run_agent_streamed_with_retry(
                process_id=process_id,
                user_id=user_id,
                agent_input=input_message,
                run_config=run_config,
                previous_response_id=None,
                base_progress=5,
                log_session_id=log_session_id,
                existing_conversation_history=None,
            )

        except Exception as e:
            logger.error(f"生成エラー: {e}", exc_info=True)
            await self._update_state(
                process_id,
                status="error",
                error_message=str(e),
            )
            await self._publish_event(
                process_id,
                user_id,
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
            db_result = (
                supabase.table("blog_generation_state")
                .select("blog_context")
                .eq("id", process_id)
                .single()
                .execute()
            )

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
                process_id,
                user_id,
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

            has_images = self._input_has_images(answer_content)
            # RunConfig設定（group_id で初回トレースと紐付け）
            run_config = self._build_blog_run_config(
                process_id=process_id,
                user_id=user_id,
                site_id=wordpress_site.get("id"),
                workflow_name="Blog Generation (continued)",
                is_continuation=True,
                has_images=has_images,
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
                    continued_input.append(
                        {
                            "role": "user",
                            "content": answer_content,
                        }
                    )
                agent_input = continued_input

            # エージェント実行（同一エージェント・会話コンテキスト維持）
            await self._run_agent_streamed_with_retry(
                process_id=process_id,
                user_id=user_id,
                agent_input=agent_input,
                run_config=run_config,
                previous_response_id=previous_response_id,
                base_progress=45,
                log_session_id=log_session_id,
                existing_conversation_history=conversation_history,
            )

        except Exception as e:
            logger.error(f"継続生成エラー: {e}", exc_info=True)
            await self._update_state(
                process_id,
                status="error",
                error_message=str(e),
            )
            await self._publish_event(
                process_id,
                user_id,
                "generation_error",
                {"error": str(e), "message": f"エラーが発生しました: {str(e)}"},
            )

    async def get_process_state(self, process_id: str) -> Optional[Dict[str, Any]]:
        """プロセス状態を取得"""
        result = (
            supabase.table("blog_generation_state")
            .select("*")
            .eq("id", process_id)
            .single()
            .execute()
        )
        return result.data

    async def cancel_generation(self, process_id: str) -> bool:
        """生成をキャンセル"""
        result = (
            supabase.table("blog_generation_state")
            .select("user_id")
            .eq("id", process_id)
            .single()
            .execute()
        )

        if not result.data:
            return False

        user_id = result.data.get("user_id")
        await self._update_state(process_id, status="cancelled")
        await self._publish_event(
            process_id,
            user_id,
            "generation_cancelled",
            {"message": "記事生成がキャンセルされました"},
        )
        return True

    # ===========================================================
    # コアエージェント実行（初回・継続共通）
    # ===========================================================

    @staticmethod
    def _is_retryable_stream_exception(exc: Exception) -> bool:
        retryable_types = (
            httpx.RemoteProtocolError,
            httpx.ReadError,
            httpx.ReadTimeout,
            httpx.ConnectError,
            APIConnectionError,
            APITimeoutError,
        )
        retry_markers = (
            "incomplete chunked read",
            "peer closed connection",
            "server disconnected",
            "connection reset",
            "temporarily unavailable",
        )

        current: Optional[BaseException] = exc
        depth = 0
        while current and depth < 6:
            if isinstance(current, retryable_types):
                return True
            message = str(current).lower()
            if any(marker in message for marker in retry_markers):
                return True
            current = getattr(current, "__cause__", None) or getattr(
                current, "__context__", None
            )
            depth += 1
        return False

    async def _run_agent_streamed_with_retry(
        self,
        process_id: str,
        user_id: str,
        agent_input: Any,
        run_config: RunConfig,
        previous_response_id: Optional[str],
        base_progress: int = 5,
        log_session_id: Optional[str] = None,
        existing_conversation_history: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        max_attempts = max(
            1, int(getattr(settings, "blog_generation_stream_retry_attempts", 3) or 3)
        )
        base_delay = float(
            getattr(settings, "blog_generation_stream_retry_delay_seconds", 1.5) or 1.5
        )

        for attempt in range(1, max_attempts + 1):
            try:
                await self._run_agent_streamed(
                    process_id=process_id,
                    user_id=user_id,
                    agent_input=agent_input,
                    run_config=run_config,
                    previous_response_id=previous_response_id,
                    base_progress=base_progress,
                    log_session_id=log_session_id,
                    existing_conversation_history=existing_conversation_history,
                )
                return
            except Exception as exc:
                is_retryable = self._is_retryable_stream_exception(exc)
                is_last_attempt = attempt >= max_attempts
                if not is_retryable or is_last_attempt:
                    raise

                wait_seconds = min(base_delay * (2 ** (attempt - 1)), 8.0)
                logger.warning(
                    "Stream connection interrupted; retrying "
                    f"(attempt {attempt + 1}/{max_attempts}, wait={wait_seconds:.1f}s): {exc}"
                )
                try:
                    await self._update_state(
                        process_id,
                        status="in_progress",
                        current_step_name="通信エラーが発生したため再試行しています",
                        progress_percentage=max(base_progress, 20),
                    )
                    await self._publish_event(
                        process_id,
                        user_id,
                        "generation_warning",
                        {
                            "message": "通信が不安定なため自動再試行しています",
                            "attempt": attempt + 1,
                            "max_attempts": max_attempts,
                        },
                    )
                except Exception as notify_err:
                    logger.debug(f"Retry notification failed: {notify_err}")
                await asyncio.sleep(wait_seconds)

    async def _run_agent_streamed(
        self,
        process_id: str,
        user_id: str,
        agent_input: Any,  # str | list[TResponseInputItem]
        run_config: RunConfig,
        previous_response_id: Optional[str],
        base_progress: int = 5,
        log_session_id: Optional[str] = None,
        existing_conversation_history: Optional[List[Dict[str, Any]]] = None,
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
            existing_conversation_history: 前回までの会話履歴（継続時のマージ用）
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
        tool_call_id_to_name: Dict[str, str] = {}
        pending_output_call_ids: deque[str] = deque()
        trace_events: List[Dict[str, Any]] = []
        trace_sequence = 1
        response_usage_entries: List[Dict[str, Any]] = []

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
                        "input_type": "list"
                        if isinstance(agent_input, list)
                        else "str",
                    },
                    llm_model=settings.blog_generation_model,
                    execution_metadata={
                        "workflow_type": "blog_generation",
                        "process_id": process_id,
                        "user_id": user_id,
                    },
                )
                trace_events.append(
                    self._make_trace_event(
                        process_id=process_id,
                        user_id=user_id,
                        session_id=log_session_id,
                        execution_id=execution_id,
                        event_sequence=trace_sequence,
                        source="system",
                        event_type="execution.started",
                        event_name="execution_started",
                        agent_name=self._agent.name,
                        input_payload={
                            "previous_response_id": previous_response_id,
                            "input_type": "list"
                            if isinstance(agent_input, list)
                            else "str",
                        },
                    )
                )
                trace_sequence += 1
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
                if (
                    execution_id
                    and log_session_id
                    and isinstance(event, RawResponsesStreamEvent)
                ):
                    raw_event_type = self._safe_get(event.data, "type")
                    if raw_event_type == "response.output_item.done":
                        item = self._safe_get(event.data, "item")
                        item_type = self._safe_get(item, "type")
                        if item_type == "function_call":
                            call_id = self._safe_get(item, "call_id") or self._safe_get(
                                item, "id"
                            )
                            tool_name = self._safe_get(item, "name")
                            if call_id:
                                if call_id not in pending_output_call_ids:
                                    pending_output_call_ids.append(call_id)
                                if tool_name:
                                    tool_call_id_to_name[call_id] = tool_name
                    elif raw_event_type == "response.web_search_call.completed":
                        call_id = self._safe_get(event.data, "item_id")
                        if call_id:
                            tool_call_id_to_name[call_id] = "web_search"
                        if (
                            call_id
                            and call_id in tool_call_log_ids
                            and logging_service
                            and execution_id
                        ):
                            duration_ms = None
                            if call_id in tool_call_start_times:
                                duration_ms = int(
                                    (time.time() - tool_call_start_times[call_id]) * 1000
                                )
                            try:
                                logging_service.update_tool_call_log(
                                    call_id=tool_call_log_ids[call_id],
                                    status="completed",
                                    output_data={
                                        "output": {
                                            "results": self._to_jsonable(
                                                self._safe_get(event.data, "results") or []
                                            ),
                                            "status": "completed",
                                        }
                                    },
                                    execution_time_ms=duration_ms,
                                )
                            except Exception as log_err:
                                logger.debug(
                                    f"Failed to update web_search tool call log: {log_err}"
                                )

                    trace_row, usage_entry = self._build_raw_trace_event(
                        raw_event=event.data,
                        process_id=process_id,
                        user_id=user_id,
                        session_id=log_session_id,
                        execution_id=execution_id,
                        event_sequence=trace_sequence,
                    )
                    if trace_row:
                        trace_events.append(trace_row)
                        trace_sequence += 1
                    if usage_entry:
                        response_usage_entries.append(usage_entry)

                # ツール呼び出しログ
                if (
                    execution_id
                    and logging_service
                    and isinstance(event, RunItemStreamEvent)
                ):
                    if isinstance(event.item, ToolCallItem):
                        tool_name = _resolve_tool_name(event.item.raw_item)
                        call_id = (
                            self._safe_get(event.item.raw_item, "call_id")
                            or self._safe_get(event.item.raw_item, "id")
                            or f"{tool_name}:{tool_call_count + 1}"
                        )
                        tool_call_id_to_name[call_id] = tool_name
                        tool_call_start_times[call_id] = time.time()
                        raw_args = self._safe_get(event.item.raw_item, "arguments")
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
                                input_parameters=parsed_args
                                if isinstance(parsed_args, dict)
                                else {"raw": parsed_args},
                                status="started",
                                tool_metadata={
                                    "call_id": call_id,
                                },
                            )
                            tool_call_log_ids[call_id] = tool_call_log_id
                        except Exception as log_err:
                            logger.debug(f"Failed to log tool call start: {log_err}")

                        if log_session_id:
                            trace_events.append(
                                self._make_trace_event(
                                    process_id=process_id,
                                    user_id=user_id,
                                    session_id=log_session_id,
                                    execution_id=execution_id,
                                    event_sequence=trace_sequence,
                                    source="run_item",
                                    event_type="tool_called",
                                    event_name=event.name,
                                    agent_name=getattr(event.item, "agent", None).name
                                    if getattr(event.item, "agent", None)
                                    else None,
                                    tool_name=tool_name,
                                    tool_call_id=call_id,
                                    input_payload=parsed_args
                                    if isinstance(parsed_args, dict)
                                    else {"raw": parsed_args},
                                    event_metadata={
                                        "call_sequence": tool_call_count + 1
                                    },
                                )
                            )
                            trace_sequence += 1
                    elif isinstance(event.item, ToolCallOutputItem):
                        call_id = self._safe_get(
                            event.item.raw_item, "call_id"
                        ) or self._safe_get(event.item.raw_item, "id")
                        matched_by_sequence = False
                        if not call_id and pending_output_call_ids:
                            call_id = pending_output_call_ids.popleft()
                            matched_by_sequence = True
                        elif call_id and call_id in pending_output_call_ids:
                            pending_output_call_ids.remove(call_id)

                        tool_name = (
                            tool_call_id_to_name.get(call_id or "")
                            if call_id
                            else None
                        )
                        if not tool_name:
                            maybe_name = _resolve_tool_name(event.item.raw_item)
                            if maybe_name != "unknown_tool":
                                tool_name = maybe_name

                        output_value = self._to_jsonable(event.item.output)
                        output_preview = self._truncate_text(
                            output_value, _TRACE_IO_LIMIT
                        )
                        if call_id and call_id in tool_call_log_ids:
                            duration_ms = None
                            if call_id in tool_call_start_times:
                                duration_ms = int(
                                    (time.time() - tool_call_start_times[call_id])
                                    * 1000
                                )
                            try:
                                logging_service.update_tool_call_log(
                                    call_id=tool_call_log_ids[call_id],
                                    status="completed",
                                    output_data={"output": output_value},
                                    execution_time_ms=duration_ms,
                                )
                            except Exception as log_err:
                                logger.debug(
                                    f"Failed to update tool call log: {log_err}"
                                )

                        if log_session_id:
                            trace_events.append(
                                self._make_trace_event(
                                    process_id=process_id,
                                    user_id=user_id,
                                    session_id=log_session_id,
                                    execution_id=execution_id,
                                    event_sequence=trace_sequence,
                                    source="run_item",
                                    event_type="tool_output",
                                    event_name=event.name,
                                    agent_name=getattr(event.item, "agent", None).name
                                    if getattr(event.item, "agent", None)
                                    else None,
                                    tool_name=tool_name,
                                    tool_call_id=call_id,
                                    output_payload={"output": output_value},
                                    event_metadata={"matched_by_sequence": matched_by_sequence}
                                    if matched_by_sequence
                                    else None,
                                    message_text=output_preview,
                                )
                            )
                            trace_sequence += 1
                    elif log_session_id and isinstance(event.item, MessageOutputItem):
                        msg = self._extract_message_output_text(event.item)
                        trace_events.append(
                            self._make_trace_event(
                                process_id=process_id,
                                user_id=user_id,
                                session_id=log_session_id,
                                execution_id=execution_id,
                                event_sequence=trace_sequence,
                                source="run_item",
                                event_type="message_output_created",
                                event_name=event.name,
                                agent_name=getattr(event.item, "agent", None).name
                                if getattr(event.item, "agent", None)
                                else None,
                                role="assistant",
                                message_text=self._truncate_text(
                                    msg, _TRACE_TEXT_LIMIT
                                ),
                            )
                        )
                        trace_sequence += 1
                    elif log_session_id and isinstance(event.item, ReasoningItem):
                        reasoning_summary = self._extract_reasoning_summary(
                            event.item.raw_item
                        )
                        trace_events.append(
                            self._make_trace_event(
                                process_id=process_id,
                                user_id=user_id,
                                session_id=log_session_id,
                                execution_id=execution_id,
                                event_sequence=trace_sequence,
                                source="run_item",
                                event_type="reasoning_item_created",
                                event_name=event.name,
                                agent_name=getattr(event.item, "agent", None).name
                                if getattr(event.item, "agent", None)
                                else None,
                                message_text=self._truncate_text(
                                    reasoning_summary, _TRACE_TEXT_LIMIT
                                )
                                if reasoning_summary
                                else None,
                            )
                        )
                        trace_sequence += 1
                elif (
                    execution_id
                    and log_session_id
                    and isinstance(event, AgentUpdatedStreamEvent)
                ):
                    trace_events.append(
                        self._make_trace_event(
                            process_id=process_id,
                            user_id=user_id,
                            session_id=log_session_id,
                            execution_id=execution_id,
                            event_sequence=trace_sequence,
                            source="agent_event",
                            event_type="agent_updated",
                            event_name="agent_updated",
                            agent_name=event.agent.name
                            if hasattr(event, "agent")
                            else None,
                        )
                    )
                    trace_sequence += 1

                await self._handle_stream_event(
                    event,
                    process_id,
                    user_id,
                    tool_call_count,
                    total_estimated_tools,
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

            # 最終結果を取得（構造化出力: BlogCompletionOutput）
            final_result: Optional[BlogCompletionOutput] = result.final_output
            logger.info(f"Agent実行完了: process_id={process_id}")
            if final_result:
                logger.debug(
                    f"Agent構造化出力: post_id={final_result.post_id}, "
                    f"preview_url={final_result.preview_url}, "
                    f"edit_url={final_result.edit_url}, "
                    f"summary={final_result.summary[:200] if final_result.summary else 'None'}"
                )
            else:
                logger.debug("Agent出力: None（構造化出力なし）")

            # ========================================
            # 会話履歴を取得（to_input_list）
            # ========================================
            try:
                conversation_history = result.to_input_list()
                if existing_conversation_history:
                    conversation_history = self._merge_conversation_histories(
                        existing_conversation_history, conversation_history
                    )
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
            cache_config = self._extract_cache_metadata_from_run_config(run_config)
            self._finalize_execution_logging(
                result=result,
                execution_id=execution_id,
                logging_service=logging_service,
                started_at=execution_start,
                usage_entries_from_stream=response_usage_entries,
                cache_config=cache_config,
            )

            self._flush_trace_events(trace_events)

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
                    blog_ctx["agent_message"] = final_result.summary
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
                    response_id=last_response_id,
                )
                await self._publish_event(
                    process_id,
                    user_id,
                    "user_input_required",
                    {
                        "questions": pending_user_questions["questions"],
                        "context": pending_user_questions.get("context"),
                        "message": pending_user_questions.get("context")
                        or "記事作成に必要な情報を入力してください",
                    },
                )
                if log_session_id and logging_service:
                    try:
                        logging_service.update_session_status(
                            session_id=log_session_id,
                            status="in_progress",
                        )
                    except Exception as log_err:
                        logger.debug(
                            f"Failed to mark log session in_progress: {log_err}"
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
                process_id,
                user_id,
                "processing_result",
                {"message": "結果を処理しています..."},
            )
            await self._process_result(
                process_id=process_id,
                user_id=user_id,
                output=final_result,
                conversation_history=conversation_history,
                last_response_id=last_response_id,
            )
            if log_session_id and logging_service:
                try:
                    logging_service.update_session_status(
                        session_id=log_session_id,
                        status="completed",
                        completed_at=datetime.now(),
                    )
                except Exception as log_err:
                    logger.debug(f"Failed to mark log session completed: {log_err}")
        except Exception as e:
            if execution_id and log_session_id:
                trace_events.append(
                    self._make_trace_event(
                        process_id=process_id,
                        user_id=user_id,
                        session_id=log_session_id,
                        execution_id=execution_id,
                        event_sequence=trace_sequence,
                        source="system",
                        event_type="execution.failed",
                        event_name="execution_failed",
                        agent_name=self._agent.name,
                        message_text=self._truncate_text(str(e), _TRACE_TEXT_LIMIT),
                        event_metadata={
                            "duration_ms": int((time.time() - execution_start) * 1000)
                        },
                    )
                )
                trace_sequence += 1
                self._flush_trace_events(trace_events)
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
            if log_session_id and logging_service:
                try:
                    logging_service.update_session_status(
                        session_id=log_session_id,
                        status="failed",
                        completed_at=datetime.now(),
                    )
                except Exception as log_err:
                    logger.debug(f"Failed to mark log session failed: {log_err}")
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
                        base_progress
                        + int(
                            (tool_call_count / max(total_estimated_tools, 1))
                            * progress_range
                        ),
                        85,
                    )

                    step_display = f"{step_phase} - {friendly_message}"

                    await self._update_state(
                        process_id,
                        current_step_name=step_display,
                        progress_percentage=progress,
                    )
                    await self._publish_event(
                        process_id,
                        user_id,
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
                    call_id = self._safe_get(item.raw_item, "call_id") or self._safe_get(
                        item.raw_item, "id"
                    )
                    tool_name = _resolve_tool_name(item.raw_item)
                    await self._publish_event(
                        process_id,
                        user_id,
                        "tool_call_completed",
                        {
                            "tool_call_id": call_id,
                            "tool_name": tool_name if tool_name != "unknown_tool" else None,
                            "message": "処理が完了しました",
                        },
                    )

                # AI思考中（Reasoning）
                elif isinstance(item, ReasoningItem):
                    # reasoning summary テキストを抽出
                    summary_text = None
                    if hasattr(item.raw_item, "summary") and item.raw_item.summary:
                        texts = [
                            s.text
                            for s in item.raw_item.summary
                            if hasattr(s, "text") and s.text
                        ]
                        if texts:
                            summary_text = " ".join(texts)

                    # 英語 summary → 日本語に翻訳
                    if summary_text:
                        summary_text = await self._translate_to_japanese(summary_text)

                    await self._publish_event(
                        process_id,
                        user_id,
                        "reasoning",
                        {
                            "message": summary_text or "AIが考えています...",
                            "has_summary": summary_text is not None,
                        },
                    )

                # メッセージ出力
                elif isinstance(item, MessageOutputItem):
                    content = ""
                    if hasattr(item, "content") and item.content:
                        for part in item.content:
                            if hasattr(part, "text"):
                                content += part.text
                    if content:
                        await self._publish_event(
                            process_id,
                            user_id,
                            "message_output",
                            {"content": content[:500]},
                        )

            elif isinstance(event, AgentUpdatedStreamEvent):
                agent_name = event.agent.name if hasattr(event, "agent") else "Unknown"
                await self._publish_event(
                    process_id,
                    user_id,
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
                structured.append(
                    {
                        "question_id": f"q{i + 1}",
                        "question": q,
                        "input_type": input_types_raw[i],
                    }
                )

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
                f'`upload_user_image_to_wordpress(image_index=N, alt="説明")` '
                f"ツールで WordPress にアップロードしてから記事に挿入してください。\n"
            )
            for i, img in enumerate(valid_images):
                original = img.get(
                    "original_filename", img.get("filename", f"image_{i}")
                )
                parts.append(f"- 画像{i}: {original}")

        parts.append(
            "\n## 指示\n\n"
            "上記のリクエストに基づいて、WordPressブログ記事を作成してください。\n"
            "`wp_get_post_types` は未取得の場合のみ実行し、取得済みなら再利用してください。\n"
            "投稿タイプエラー（`invalid_post_type`）時のみ `wp_get_post_types` を再取得してください。\n"
            "`wp_create_draft_post` で `post_type` を指定して下書きを保存してください。"
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
                content_parts.append(
                    {
                        "type": "input_image",
                        "image_url": f"data:image/webp;base64,{b64}",
                    }
                )
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
        question_map = {q["question_id"]: q for q in ai_questions}

        text_parts = [
            "以下がユーザーからの回答です。この情報を活用して記事を作成してください。\n"
        ]
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
                        getattr(settings, "temp_upload_dir", None)
                        or "/tmp/blog_uploads",
                        process_id,
                    )
                    for fname in filenames:
                        fname = fname.strip()
                        local_path = os.path.join(upload_dir, fname)
                        if os.path.exists(local_path):
                            try:
                                b64 = read_as_base64(local_path)
                                image_parts.append(
                                    {
                                        "type": "input_image",
                                        "image_url": f"data:image/webp;base64,{b64}",
                                    }
                                )
                            except Exception as e:
                                logger.warning(
                                    f"画像読み込みエラー: {local_path} - {e}"
                                )
            else:
                text_parts.append(f"**Q: {question_text}**")
                text_parts.append(f"A: {answer}\n")

        if not has_any_answer:
            text_parts.append(
                "（ユーザーは質問をスキップしました。"
                "リクエスト内容と参考記事の分析結果のみで記事を作成してください。）"
            )

        text_parts.append(
            "\n上記の情報をもとに、`wp_get_post_types` は未取得の場合のみ実行し、取得済みなら再利用してください。\n"
            "投稿タイプエラー（`invalid_post_type`）時のみ `wp_get_post_types` を再取得してください。\n"
            "`wp_create_draft_post` で `post_type` を指定して下書き保存してください。"
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

    @staticmethod
    def _truncate_text(value: Any, limit: int) -> Optional[str]:
        if value is None:
            return None
        text = str(value)
        if len(text) <= limit:
            return text
        return f"{text[:limit]}…(truncated)"

    @classmethod
    def _to_jsonable(cls, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, dict):
            return {str(k): cls._to_jsonable(v) for k, v in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [cls._to_jsonable(v) for v in value]
        if hasattr(value, "model_dump"):
            return cls._to_jsonable(value.model_dump(exclude_none=True))
        if hasattr(value, "dict"):
            return cls._to_jsonable(value.dict())
        return str(value)

    @staticmethod
    def _parse_json_maybe(value: Any) -> Any:
        if not isinstance(value, str):
            return value
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value

    @classmethod
    def _history_item_signature(cls, item: Any) -> str:
        try:
            normalized = cls._to_jsonable(item)
            return json.dumps(normalized, sort_keys=True, ensure_ascii=False)
        except Exception:
            return str(item)

    @classmethod
    def _merge_conversation_histories(
        cls, existing: List[Dict[str, Any]], latest: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """既存履歴と最新履歴を重複なくマージする。

        previous_response_id を使った継続実行では、SDK 側の to_input_list() が
        直近ターン中心になることがあるため、履歴のオーバーラップを計算して補完する。
        """
        existing_items = [cls._to_jsonable(item) for item in (existing or []) if item]
        latest_items = [cls._to_jsonable(item) for item in (latest or []) if item]

        if not existing_items:
            return latest_items  # type: ignore[return-value]
        if not latest_items:
            return existing_items  # type: ignore[return-value]

        existing_sig = [cls._history_item_signature(item) for item in existing_items]
        latest_sig = [cls._history_item_signature(item) for item in latest_items]

        if len(latest_sig) >= len(existing_sig) and latest_sig[: len(existing_sig)] == existing_sig:
            return latest_items  # type: ignore[return-value]
        if len(existing_sig) >= len(latest_sig) and existing_sig[-len(latest_sig) :] == latest_sig:
            return existing_items  # type: ignore[return-value]

        max_overlap = 0
        for overlap in range(min(len(existing_sig), len(latest_sig)), 0, -1):
            if existing_sig[-overlap:] == latest_sig[:overlap]:
                max_overlap = overlap
                break

        merged = existing_items + latest_items[max_overlap:]
        return merged  # type: ignore[return-value]

    def _extract_message_output_text(self, item: MessageOutputItem) -> str:
        content = ""
        if hasattr(item, "content") and item.content:
            for part in item.content:
                part_text = getattr(part, "text", None)
                if part_text:
                    content += part_text
        return content

    @staticmethod
    def _extract_reasoning_summary(raw_item: Any) -> Optional[str]:
        if hasattr(raw_item, "summary") and raw_item.summary:
            texts = [s.text for s in raw_item.summary if hasattr(s, "text") and s.text]
            if texts:
                return " ".join(texts)
        return None

    def _extract_output_item_text(self, item: Any) -> Optional[str]:
        content = self._safe_get(item, "content", [])
        texts: List[str] = []
        for part in content or []:
            text = self._safe_get(part, "text")
            if text:
                texts.append(text)
        if texts:
            return " ".join(texts)
        return None

    def _make_trace_event(
        self,
        process_id: str,
        user_id: str,
        session_id: str,
        execution_id: Optional[str],
        event_sequence: int,
        source: str,
        event_type: str,
        event_name: Optional[str] = None,
        agent_name: Optional[str] = None,
        role: Optional[str] = None,
        message_text: Optional[str] = None,
        tool_name: Optional[str] = None,
        tool_call_id: Optional[str] = None,
        response_id: Optional[str] = None,
        model_name: Optional[str] = None,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        cached_tokens: int = 0,
        reasoning_tokens: int = 0,
        total_tokens: int = 0,
        input_payload: Optional[Dict[str, Any]] = None,
        output_payload: Optional[Dict[str, Any]] = None,
        event_metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return {
            "process_id": process_id,
            "user_id": user_id,
            "session_id": session_id,
            "execution_id": execution_id,
            "event_sequence": event_sequence,
            "source": source,
            "event_type": event_type,
            "event_name": event_name,
            "agent_name": agent_name,
            "role": role,
            "message_text": self._truncate_text(message_text, _TRACE_TEXT_LIMIT),
            "tool_name": tool_name,
            "tool_call_id": tool_call_id,
            "response_id": response_id,
            "model_name": model_name,
            "prompt_tokens": max(0, int(prompt_tokens or 0)),
            "completion_tokens": max(0, int(completion_tokens or 0)),
            "cached_tokens": max(0, int(cached_tokens or 0)),
            "reasoning_tokens": max(0, int(reasoning_tokens or 0)),
            "total_tokens": max(0, int(total_tokens or 0)),
            "input_payload": self._to_jsonable(input_payload or {}),
            "output_payload": self._to_jsonable(output_payload or {}),
            "event_metadata": self._to_jsonable(event_metadata or {}),
        }

    def _build_raw_trace_event(
        self,
        raw_event: Any,
        process_id: str,
        user_id: str,
        session_id: str,
        execution_id: str,
        event_sequence: int,
    ) -> tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        event_type = self._safe_get(raw_event, "type", "unknown")
        if event_type == "keepalive" or str(event_type).endswith(".delta"):
            # deltaイベントは粒度が細かく行数を爆発させるため保存しない。
            return None, None
        sequence_number = self._safe_get(raw_event, "sequence_number")
        item_id = self._safe_get(raw_event, "item_id")
        output_index = self._safe_get(raw_event, "output_index")

        metadata = {
            "sequence_number": sequence_number,
            "item_id": item_id,
            "output_index": output_index,
            "content_index": self._safe_get(raw_event, "content_index"),
            "summary_index": self._safe_get(raw_event, "summary_index"),
        }
        metadata = {k: v for k, v in metadata.items() if v is not None}

        trace_kwargs: Dict[str, Any] = {
            "process_id": process_id,
            "user_id": user_id,
            "session_id": session_id,
            "execution_id": execution_id,
            "event_sequence": event_sequence,
            "source": "raw_response",
            "event_type": event_type,
            "event_name": event_type,
            "event_metadata": metadata,
        }
        usage_entry: Optional[Dict[str, Any]] = None

        if event_type == "response.output_text.done":
            trace_kwargs["role"] = "assistant"
            trace_kwargs["message_text"] = self._truncate_text(
                self._safe_get(raw_event, "text"), _TRACE_TEXT_LIMIT
            )
        elif event_type == "response.reasoning_summary_text.done":
            trace_kwargs["message_text"] = self._truncate_text(
                self._safe_get(raw_event, "text"),
                _TRACE_TEXT_LIMIT,
            )
        elif event_type == "response.function_call_arguments.done":
            trace_kwargs["tool_call_id"] = self._safe_get(raw_event, "item_id")
            trace_kwargs["tool_name"] = self._safe_get(raw_event, "name")
            trace_kwargs["input_payload"] = {
                "arguments": self._to_jsonable(
                    self._parse_json_maybe(self._safe_get(raw_event, "arguments"))
                )
            }
        elif event_type.startswith("response.web_search_call."):
            trace_kwargs["tool_name"] = "web_search"
            trace_kwargs["tool_call_id"] = self._safe_get(raw_event, "item_id")
            query = self._safe_get(raw_event, "query")
            if query:
                trace_kwargs["input_payload"] = {"query": query}
            trace_kwargs["event_metadata"] = {
                **metadata,
                "web_search_status": event_type.split(".")[-1],
            }
        elif event_type in ("response.output_item.added", "response.output_item.done"):
            item = self._safe_get(raw_event, "item")
            item_type = self._safe_get(item, "type")
            trace_kwargs["event_metadata"] = {
                **metadata,
                "item_type": item_type,
            }
            trace_kwargs["role"] = self._safe_get(item, "role")
            trace_kwargs["tool_name"] = self._safe_get(item, "name")
            trace_kwargs["tool_call_id"] = self._safe_get(
                item, "call_id"
            ) or self._safe_get(item, "id")
            if item_type in ("message", "output_text"):
                trace_kwargs["message_text"] = self._truncate_text(
                    self._extract_output_item_text(item), _TRACE_TEXT_LIMIT
                )
            arguments = self._safe_get(item, "arguments")
            if arguments:
                trace_kwargs["input_payload"] = {
                    "arguments": self._to_jsonable(self._parse_json_maybe(arguments))
                }
            output = self._safe_get(item, "output")
            if output:
                trace_kwargs["output_payload"] = {
                    "output": self._truncate_text(output, _TRACE_IO_LIMIT)
                }
        elif event_type == "response.completed":
            response = self._safe_get(raw_event, "response")
            usage = self._safe_get(response, "usage")
            input_details = self._safe_get(usage, "input_tokens_details")
            output_details = self._safe_get(usage, "output_tokens_details")

            prompt_tokens = int(self._safe_get(usage, "input_tokens", 0) or 0)
            completion_tokens = int(self._safe_get(usage, "output_tokens", 0) or 0)
            total_tokens = int(self._safe_get(usage, "total_tokens", 0) or 0)
            cached_tokens = int(self._safe_get(input_details, "cached_tokens", 0) or 0)
            reasoning_tokens = int(
                self._safe_get(output_details, "reasoning_tokens", 0) or 0
            )

            response_id = self._safe_get(response, "id")
            model_name = self._safe_get(response, "model")

            trace_kwargs.update(
                {
                    "response_id": response_id,
                    "model_name": model_name,
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "cached_tokens": cached_tokens,
                    "reasoning_tokens": reasoning_tokens,
                    "total_tokens": total_tokens,
                }
            )

            output_items = self._safe_get(response, "output", []) or []
            output_summary: List[Dict[str, Any]] = []
            for item in output_items:
                output_summary.append(
                    {
                        "type": self._safe_get(item, "type"),
                        "id": self._safe_get(item, "id"),
                        "role": self._safe_get(item, "role"),
                        "name": self._safe_get(item, "name"),
                        "call_id": self._safe_get(item, "call_id"),
                        "text": self._truncate_text(
                            self._extract_output_item_text(item), 800
                        ),
                    }
                )
            trace_kwargs["output_payload"] = {
                "output_count": len(output_items),
                "output_items": output_summary,
            }

            usage_entry = {
                "model": model_name,
                "input_tokens": prompt_tokens,
                "output_tokens": completion_tokens,
                "total_tokens": total_tokens,
                "cached_tokens": cached_tokens,
                "reasoning_tokens": reasoning_tokens,
                "response_id": response_id,
            }
        else:
            # Keep non-critical raw events compact to avoid large rows.
            trace_kwargs["event_metadata"] = {
                **metadata,
                "raw_type": event_type,
            }

        return self._make_trace_event(**trace_kwargs), usage_entry

    @staticmethod
    def _flush_trace_events(trace_events: List[Dict[str, Any]]) -> None:
        if not trace_events:
            return
        try:
            for i in range(0, len(trace_events), 200):
                chunk = trace_events[i : i + 200]
                supabase.table("blog_agent_trace_events").insert(chunk).execute()
        except Exception as e:
            logger.debug(f"Failed to flush blog trace events: {e}")
        finally:
            trace_events.clear()

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
            existing = (
                supabase.table("agent_log_sessions")
                .select("id")
                .eq("article_uuid", process_id)
                .limit(1)
                .execute()
            )
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
            result = (
                supabase.table("agent_execution_logs")
                .select("id", count="exact")
                .eq("session_id", session_id)
                .execute()
            )
            if result.count is not None:
                return int(result.count) + 1
            return len(result.data or []) + 1
        except Exception:
            return 1

    @staticmethod
    def _get_raw_responses(result: Any) -> Optional[List[Any]]:
        candidate_attrs = [
            "_raw_responses",
            "raw_responses",
            "_responses",
            "responses",
            "_RunResult__raw_responses",
            "__raw_responses",
            "new_items",
            "_new_items",
        ]
        for attr_name in candidate_attrs:
            if hasattr(result, attr_name):
                attr_value = getattr(result, attr_name)
                if (
                    attr_value
                    and hasattr(attr_value, "__len__")
                    and len(attr_value) > 0
                ):
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
            "model": self._safe_get(entry, "model", None)
            or self._safe_get(entry, "model_name", None),
            "input_tokens": int(input_tokens or 0),
            "output_tokens": int(output_tokens or 0),
            "total_tokens": int(self._safe_get(entry, "total_tokens", 0) or 0),
            "cached_tokens": int(cached_tokens or 0),
            "reasoning_tokens": int(reasoning_tokens or 0),
            "response_id": self._safe_get(entry, "response_id", None)
            or self._safe_get(entry, "id", None),
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

        normalized = [
            self._normalize_usage_entry(entry) for entry in entries if entry is not None
        ]
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

    def _extract_usage_from_context_wrapper(
        self, result: Any
    ) -> Optional[Dict[str, Any]]:
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

    def _extract_usage_from_raw_responses(
        self, result: Any
    ) -> Optional[Dict[str, Any]]:
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

            cached_tokens = (
                self._safe_get(input_details, "cached_tokens", 0)
                if input_details
                else 0
            )
            reasoning_tokens = (
                self._safe_get(output_details, "reasoning_tokens", 0)
                if output_details
                else 0
            )

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
        usage_entries_from_stream: Optional[List[Dict[str, Any]]] = None,
        cache_config: Optional[Dict[str, Any]] = None,
    ) -> None:
        if not execution_id or not logging_service:
            return

        usage_source = "stream_response_completed"
        usage_entries = usage_entries_from_stream or []
        usage_summary = self._aggregate_usage(usage_entries)

        if not usage_entries:
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
                    input_tokens = int(entry.get("input_tokens", 0))
                    cached_tokens = int(entry.get("cached_tokens", 0))
                    cache_hit_rate = (
                        round((cached_tokens / input_tokens) * 100, 2)
                        if input_tokens > 0
                        else 0.0
                    )
                    logging_service.create_llm_call_log(
                        execution_id=execution_id,
                        call_sequence=i + 1,
                        api_type="responses_api",
                        model_name=entry.get("model") or settings.blog_generation_model,
                        provider="openai",
                        prompt_tokens=input_tokens,
                        completion_tokens=int(entry.get("output_tokens", 0)),
                        total_tokens=int(entry.get("total_tokens", 0) or 0),
                        cached_tokens=cached_tokens,
                        reasoning_tokens=int(entry.get("reasoning_tokens", 0)),
                        estimated_cost_usd=cost,
                        api_response_id=entry.get("response_id"),
                        response_data={
                            "usage_source": usage_source,
                            "response_id": entry.get("response_id"),
                            "cache_hit_rate": cache_hit_rate,
                            "cache_config": cache_config or {},
                        },
                    )
            elif usage_summary:
                cost = self._estimate_cost(usage_summary)
                input_tokens = int(usage_summary.get("input_tokens", 0))
                cached_tokens = int(usage_summary.get("cached_tokens", 0))
                cache_hit_rate = (
                    round((cached_tokens / input_tokens) * 100, 2)
                    if input_tokens > 0
                    else 0.0
                )
                logging_service.create_llm_call_log(
                    execution_id=execution_id,
                    call_sequence=1,
                    api_type="responses_api",
                    model_name=usage_summary.get("model")
                    or settings.blog_generation_model,
                    provider="openai",
                    prompt_tokens=input_tokens,
                    completion_tokens=int(usage_summary.get("output_tokens", 0)),
                    total_tokens=int(usage_summary.get("total_tokens", 0)),
                    cached_tokens=cached_tokens,
                    reasoning_tokens=int(usage_summary.get("reasoning_tokens", 0)),
                    estimated_cost_usd=cost,
                    api_response_id=usage_summary.get("response_id"),
                    response_data={
                        "usage_source": usage_source,
                        "response_id": usage_summary.get("response_id"),
                        "cache_hit_rate": cache_hit_rate,
                        "cache_config": cache_config or {},
                    },
                )
        except Exception as e:
            logger.debug(f"Failed to create llm call logs: {e}")

    async def _process_result(
        self,
        process_id: str,
        user_id: str,
        output: Optional[BlogCompletionOutput],
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        last_response_id: Optional[str] = None,
    ) -> None:
        """
        Agent実行結果を処理（構造化出力から直接プレビューURL等を取得）
        """
        blog_ctx: Dict[str, Any] = {}
        if output and output.summary:
            blog_ctx["agent_message"] = output.summary
        if conversation_history is not None:
            blog_ctx["conversation_history"] = conversation_history
        if last_response_id:
            blog_ctx["last_response_id"] = last_response_id

        has_draft_info = output and (
            output.post_id or output.preview_url or output.edit_url
        )

        if has_draft_info:
            await self._update_state(
                process_id,
                status="completed",
                current_step_name="完了",
                progress_percentage=100,
                draft_post_id=output.post_id,
                draft_preview_url=output.preview_url,
                draft_edit_url=output.edit_url,
                blog_context=blog_ctx if blog_ctx else None,
                response_id=last_response_id,
            )
            await self._publish_event(
                process_id,
                user_id,
                "generation_completed",
                {
                    "draft_post_id": output.post_id,
                    "preview_url": output.preview_url,
                    "edit_url": output.edit_url,
                    "message": "記事の下書きが作成されました！",
                },
            )
        else:
            summary_preview = (
                output.summary[:500] if output and output.summary else "(出力なし)"
            )
            logger.warning(
                f"下書き情報が構造化出力に含まれていません: {summary_preview}"
            )
            await self._update_state(
                process_id,
                status="completed",
                current_step_name="完了（下書きURL未取得）",
                progress_percentage=100,
                blog_context=blog_ctx if blog_ctx else None,
                response_id=last_response_id,
            )
            await self._publish_event(
                process_id,
                user_id,
                "generation_completed",
                {
                    "message": "記事生成は完了しましたが、下書きURLの取得に失敗しました。"
                    "WordPressの下書き一覧を確認してください。",
                    "summary": output.summary if output else None,
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
            sub = (
                supabase.table("user_subscriptions")
                .select("upgraded_to_org_id")
                .eq("user_id", user_id)
                .maybe_single()
                .execute()
            )
            if sub.data and sub.data.get("upgraded_to_org_id"):
                return sub.data["upgraded_to_org_id"]

            # 2. organization_members でアクティブな組織サブスクを探す
            memberships = (
                supabase.table("organization_members")
                .select("organization_id")
                .eq("user_id", user_id)
                .execute()
            )
            if memberships.data:
                org_ids = [m["organization_id"] for m in memberships.data]
                org_subs = (
                    supabase.table("organization_subscriptions")
                    .select("organization_id")
                    .in_("organization_id", org_ids)
                    .eq("status", "active")
                    .limit(1)
                    .execute()
                )
                if org_subs.data:
                    return org_subs.data[0]["organization_id"]

            return None
        except Exception:
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
        response_id: Optional[str] = None,
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
        if response_id is not None:
            update_data["response_id"] = response_id
        if error_message is not None:
            update_data["error_message"] = error_message
        if blog_context is not None:
            update_data["blog_context"] = blog_context

        supabase.table("blog_generation_state").update(update_data).eq(
            "id", process_id
        ).execute()

    async def _translate_to_japanese(self, text: str) -> str:
        """英語の reasoning summary を gpt-5-nano で日本語に翻訳"""
        try:
            client = AsyncOpenAI(api_key=settings.openai_api_key)
            response = await client.responses.create(
                model=settings.reasoning_translate_model,
                instructions="Translate the following text to Japanese. Output ONLY the translated text, nothing else. Keep any markdown formatting intact.",
                input=text,
                reasoning={"effort": "minimal", "summary": None},
                text={"verbosity": "low"},
                store=False,
            )
            return response.output_text or text
        except Exception as e:
            logger.warning(f"Reasoning summary 翻訳失敗、原文を使用: {e}")
            return text

    async def _publish_event(
        self,
        process_id: str,
        user_id: str,
        event_type: str,
        event_data: Dict[str, Any],
    ) -> None:
        """Realtimeイベントを発行"""
        try:
            result = (
                supabase.table("blog_process_events")
                .select("event_sequence")
                .eq("process_id", process_id)
                .order("event_sequence", desc=True)
                .limit(1)
                .execute()
            )

            next_sequence = 1
            if result.data:
                next_sequence = result.data[0]["event_sequence"] + 1

            supabase.table("blog_process_events").insert(
                {
                    "process_id": process_id,
                    "user_id": user_id,
                    "event_type": event_type,
                    "event_data": event_data,
                    "event_sequence": next_sequence,
                }
            ).execute()
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
