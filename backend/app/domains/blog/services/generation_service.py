# -*- coding: utf-8 -*-
"""
Blog AI Domain - Generation Service

ブログ記事生成サービス（OpenAI Agents SDK Runner.run() を使用）
"""

import asyncio
import json
import re
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from agents import Runner, RunConfig

from app.common.database import supabase
import logging

from app.core.config import settings
from app.domains.blog.agents.definitions import build_blog_writer_agent
from app.domains.blog.services.wordpress_mcp_service import (
    clear_mcp_client_cache,
)

logger = logging.getLogger(__name__)


class BlogGenerationService:
    """
    ブログ記事生成サービス

    OpenAI Agents SDK の Runner.run() を使用して、
    エージェントベースでブログ記事を生成する。
    """

    def __init__(self):
        self._agent = build_blog_writer_agent()

    async def run_generation(
        self,
        process_id: str,
        user_id: str,
        user_prompt: str,
        reference_url: Optional[str],
        wordpress_site: Dict[str, Any],
    ) -> None:
        """
        ブログ生成を実行

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
                current_step_name="分析中",
                progress_percentage=10,
            )

            await self._publish_event(
                process_id,
                user_id,
                "generation_started",
                {"step": "analyzing"},
            )

            # MCPクライアントキャッシュをクリア（新しいサイトIDで再接続）
            clear_mcp_client_cache(wordpress_site["id"])

            # 入力メッセージを構築
            input_message = self._build_input_message(
                user_prompt,
                reference_url,
                wordpress_site,
            )

            # 進捗更新
            await self._update_state(
                process_id,
                current_step_name="記事生成中",
                progress_percentage=30,
            )

            await self._publish_event(
                process_id,
                user_id,
                "step_started",
                {"step": "generating_content"},
            )

            # RunConfig設定
            run_config = RunConfig(
                trace_metadata={
                    "process_id": process_id,
                    "user_id": user_id,
                    "site_id": wordpress_site["id"],
                }
            )

            # Agent実行（max_turnsを設定で制御）
            logger.info(f"Agent実行開始: process_id={process_id}")
            result = await Runner.run(
                self._agent,
                input_message,
                run_config=run_config,
                max_turns=settings.blog_generation_max_turns,  # 環境変数で制御可能（デフォルト100）
            )
            logger.info(f"Agent実行完了: process_id={process_id}")

            # 結果を取得
            output_text = result.final_output
            logger.debug(f"Agent出力: {output_text[:500]}...")

            # 進捗更新
            await self._update_state(
                process_id,
                current_step_name="結果処理中",
                progress_percentage=80,
            )

            # 結果を解析してDBに保存
            await self._process_result(process_id, user_id, output_text)

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
                {"error": str(e)},
            )

    def _build_input_message(
        self,
        user_prompt: str,
        reference_url: Optional[str],
        wordpress_site: Dict[str, Any],
    ) -> str:
        """入力メッセージを構築"""
        parts = [
            f"## リクエスト\n\n{user_prompt}",
        ]

        if reference_url:
            parts.append(f"\n## 参考記事URL\n\n{reference_url}")

        parts.append(f"\n## WordPressサイト情報\n\n- サイトURL: {wordpress_site.get('site_url', '不明')}")
        parts.append(f"- サイト名: {wordpress_site.get('site_name', '不明')}")

        parts.append("\n## 指示\n\n上記のリクエストに基づいて、WordPressブログ記事を作成してください。")
        parts.append("必ず `wp_create_draft_post` ツールを使って下書きを保存してください。")

        return "\n".join(parts)

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
        # wp_create_draft_post の結果を解析
        draft_info = self._extract_draft_info(output_text)

        if draft_info:
            await self._update_state(
                process_id,
                status="completed",
                current_step_name="完了",
                progress_percentage=100,
                draft_post_id=draft_info.get("post_id"),
                draft_preview_url=draft_info.get("preview_url"),
                draft_edit_url=draft_info.get("edit_url"),
            )

            await self._publish_event(
                process_id,
                user_id,
                "generation_completed",
                {
                    "draft_post_id": draft_info.get("post_id"),
                    "preview_url": draft_info.get("preview_url"),
                    "edit_url": draft_info.get("edit_url"),
                },
            )
        else:
            # 下書き情報が見つからない場合
            logger.warning(f"下書き情報が見つかりません: {output_text[:500]}")
            await self._update_state(
                process_id,
                status="completed",
                current_step_name="完了（下書きURL未取得）",
                progress_percentage=100,
            )

            await self._publish_event(
                process_id,
                user_id,
                "generation_completed",
                {
                    "message": "記事生成は完了しましたが、下書きURLの取得に失敗しました。WordPressの下書き一覧を確認してください。",
                    "output": output_text[:1000],
                },
            )

    def _extract_draft_info(self, output_text: str) -> Optional[Dict[str, Any]]:
        """
        Agent出力から下書き情報を抽出

        wp_create_draft_post の結果JSON、または直接的なURL記述を探す
        """
        # JSONブロックを探す
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

        # URL直接記述を探す
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

        # post_id のみを探す
        post_id_match = re.search(r'"?post_id"?\s*[:=]\s*(\d+)', output_text)
        if post_id_match:
            return {
                "post_id": int(post_id_match.group(1)),
                "preview_url": None,
                "edit_url": None,
            }

        return None

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
            # イベントシーケンスを取得
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

    async def continue_generation(
        self,
        process_id: str,
        user_id: str,
        user_answers: Dict[str, Any],
        wordpress_site: Dict[str, Any],
    ) -> None:
        """
        ユーザー入力後に生成を継続

        Args:
            process_id: プロセスID
            user_id: ユーザーID
            user_answers: ユーザーの回答
            wordpress_site: WordPressサイト情報
        """
        try:
            # 現在の状態を取得
            result = supabase.table("blog_generation_state").select(
                "user_prompt, reference_url, blog_context"
            ).eq("id", process_id).single().execute()

            if not result.data:
                raise Exception("プロセスが見つかりません")

            state = result.data
            user_prompt = state.get("user_prompt", "")
            reference_url = state.get("reference_url")

            # 回答を含めた入力を構築
            answers_text = "\n".join(
                f"- {k}: {v}" for k, v in user_answers.items()
            )
            enhanced_prompt = f"{user_prompt}\n\n## 追加情報\n\n{answers_text}"

            await self._update_state(
                process_id,
                status="in_progress",
                current_step_name="生成再開中",
                progress_percentage=50,
            )

            # 生成を再実行
            await self.run_generation(
                process_id=process_id,
                user_id=user_id,
                user_prompt=enhanced_prompt,
                reference_url=reference_url,
                wordpress_site=wordpress_site,
            )

        except Exception as e:
            logger.error(f"継続生成エラー: {e}")
            await self._update_state(
                process_id,
                status="error",
                error_message=str(e),
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

        await self._update_state(
            process_id,
            status="cancelled",
        )

        await self._publish_event(
            process_id,
            user_id,
            "generation_cancelled",
            {},
        )

        return True


# シングルトンインスタンス
_generation_service: Optional[BlogGenerationService] = None


def get_generation_service() -> BlogGenerationService:
    """BlogGenerationServiceのシングルトンインスタンスを取得"""
    global _generation_service
    if _generation_service is None:
        _generation_service = BlogGenerationService()
    return _generation_service
