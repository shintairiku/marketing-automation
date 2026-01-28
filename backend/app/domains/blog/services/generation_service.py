# -*- coding: utf-8 -*-
"""
Blog AI Domain - Generation Service

ブログ記事生成サービス（OpenAI Responses API + バックグラウンドモード）
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from openai import OpenAI

from app.common.database import supabase
import logging

from app.core.config import settings

from ..context import BlogContext
from .wordpress_mcp_service import WordPressMcpService

logger = logging.getLogger(__name__)

# デフォルトモデル
DEFAULT_MODEL = "gpt-5.2"

# ポーリング間隔
POLL_INTERVAL = 2  # 秒


class BlogGenerationService:
    """
    ブログ記事生成サービス

    OpenAI Responses APIのバックグラウンドモードを使用して、
    長時間実行タスクを非同期で処理する。
    """

    def __init__(self):
        self.client = OpenAI()
        self.model = getattr(settings, "blog_generation_model", DEFAULT_MODEL)

    async def start_generation(
        self,
        user_id: str,
        user_prompt: str,
        reference_url: Optional[str],
        wordpress_site_id: str,
    ) -> str:
        """
        ブログ生成プロセスを開始

        Args:
            user_id: ユーザーID
            user_prompt: ユーザーの記事作成リクエスト
            reference_url: 参考記事URL
            wordpress_site_id: WordPressサイトID

        Returns:
            プロセスID
        """
        process_id = str(uuid.uuid4())
        realtime_channel = f"blog_generation_{process_id}"

        # 初期コンテキスト作成
        context = BlogContext(
            user_prompt=user_prompt,
            reference_url=reference_url,
            wordpress_site_id=wordpress_site_id,
            process_id=process_id,
            user_id=user_id,
            current_step="start",
        )

        # DBにプロセス状態を作成
        await self._create_process_state(
            process_id=process_id,
            user_id=user_id,
            wordpress_site_id=wordpress_site_id,
            context=context,
            realtime_channel=realtime_channel,
            user_prompt=user_prompt,
            reference_url=reference_url,
        )

        # バックグラウンドで生成タスクを開始
        asyncio.create_task(
            self._run_generation(process_id, context)
        )

        return process_id

    async def _create_process_state(
        self,
        process_id: str,
        user_id: str,
        wordpress_site_id: str,
        context: BlogContext,
        realtime_channel: str,
        user_prompt: str,
        reference_url: Optional[str],
    ) -> None:
        """プロセス状態をDBに作成"""
        supabase.table("blog_generation_state").insert({
            "id": process_id,
            "user_id": user_id,
            "wordpress_site_id": wordpress_site_id,
            "status": "pending",
            "current_step_name": "start",
            "progress_percentage": 0,
            "blog_context": context.to_dict(),
            "realtime_channel": realtime_channel,
            "user_prompt": user_prompt,
            "reference_url": reference_url,
        }).execute()

    async def _update_process_state(
        self,
        process_id: str,
        status: Optional[str] = None,
        current_step_name: Optional[str] = None,
        progress_percentage: Optional[int] = None,
        is_waiting_for_input: Optional[bool] = None,
        input_type: Optional[str] = None,
        context: Optional[BlogContext] = None,
        response_id: Optional[str] = None,
        draft_post_id: Optional[int] = None,
        draft_preview_url: Optional[str] = None,
        draft_edit_url: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """プロセス状態を更新"""
        update_data: Dict[str, Any] = {}

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
        if context is not None:
            update_data["blog_context"] = context.to_dict()
        if response_id is not None:
            update_data["response_id"] = response_id
        if draft_post_id is not None:
            update_data["draft_post_id"] = draft_post_id
        if draft_preview_url is not None:
            update_data["draft_preview_url"] = draft_preview_url
        if draft_edit_url is not None:
            update_data["draft_edit_url"] = draft_edit_url
        if error_message is not None:
            update_data["error_message"] = error_message

        if update_data:
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

    async def _run_generation(
        self,
        process_id: str,
        context: BlogContext,
    ) -> None:
        """
        生成タスクを実行

        OpenAI Responses APIのバックグラウンドモードを使用
        """
        try:
            # 状態を更新
            await self._update_process_state(
                process_id,
                status="in_progress",
                current_step_name="analyzing_reference",
                progress_percentage=10,
            )

            await self._publish_event(
                process_id,
                context.user_id,
                "generation_started",
                {"step": "analyzing_reference"},
            )

            # WordPress MCP接続情報を取得
            mcp_service = await self._get_mcp_service(context.wordpress_site_id)
            if not mcp_service:
                raise Exception("WordPress接続情報が見つかりません")

            context.mcp_endpoint = mcp_service.mcp_endpoint
            context.mcp_access_token = mcp_service.access_token

            # 参考記事を分析（参考URLがある場合）
            reference_analysis = ""
            if context.reference_url:
                await self._publish_event(
                    process_id,
                    context.user_id,
                    "step_started",
                    {"step": "analyzing_reference", "url": context.reference_url},
                )

                try:
                    article = await mcp_service.get_post_by_url(context.reference_url)
                    reference_analysis = self._format_reference_analysis(article)
                except Exception as e:
                    logger.warning(f"参考記事の取得に失敗: {e}")

            # 最近の記事からスタイルを分析
            recent_posts = await mcp_service.get_recent_posts(limit=5)
            style_analysis = self._analyze_posts_style(recent_posts)

            # プロンプトを構築
            system_prompt = self._build_system_prompt(style_analysis)
            user_input = self._build_user_input(
                context.user_prompt,
                reference_analysis,
                context.uploaded_images,
            )

            # OpenAI Responses APIでバックグラウンド実行
            await self._update_process_state(
                process_id,
                current_step_name="generating_content",
                progress_percentage=30,
            )

            await self._publish_event(
                process_id,
                context.user_id,
                "step_started",
                {"step": "generating_content"},
            )

            # バックグラウンドモードでレスポンス生成
            response = self.client.responses.create(
                model=self.model,
                input=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_input},
                ],
                background=True,
                store=True,  # バックグラウンドモードでは必須
            )

            # レスポンスIDを保存
            await self._update_process_state(
                process_id,
                response_id=response.id,
            )

            # ポーリングで完了を待つ
            while response.status in {"queued", "in_progress"}:
                await asyncio.sleep(POLL_INTERVAL)
                response = self.client.responses.retrieve(response.id)

                await self._publish_event(
                    process_id,
                    context.user_id,
                    "generation_progress",
                    {"status": response.status},
                )

            if response.status == "failed":
                raise Exception(f"生成に失敗しました: {response.error}")

            # 生成結果を取得
            generated_content = response.output_text

            # AIからの質問を解析
            questions = self._parse_ai_questions(generated_content)

            if questions:
                # ユーザー入力が必要
                context.ai_questions = questions
                context.current_step = "waiting_for_user_input"

                await self._update_process_state(
                    process_id,
                    status="user_input_required",
                    current_step_name="waiting_for_user_input",
                    is_waiting_for_input=True,
                    input_type="additional_info",
                    context=context,
                    progress_percentage=50,
                )

                await self._publish_event(
                    process_id,
                    context.user_id,
                    "user_input_required",
                    {
                        "input_type": "additional_info",
                        "questions": [
                            {
                                "question_id": q.question_id,
                                "question": q.question,
                                "input_type": q.input_type,
                            }
                            for q in questions
                        ],
                    },
                )
                return  # ユーザー入力を待つ

            # 質問がなければ直接記事作成へ
            await self._create_draft(process_id, context, generated_content, mcp_service)

        except Exception as e:
            logger.error(f"生成エラー: {e}")
            await self._update_process_state(
                process_id,
                status="error",
                error_message=str(e),
            )
            await self._publish_event(
                process_id,
                context.user_id,
                "generation_error",
                {"error": str(e)},
            )

    async def _get_mcp_service(
        self,
        site_id: str,
    ) -> Optional[WordPressMcpService]:
        """WordPressMcpServiceを取得"""
        result = supabase.table("wordpress_sites").select(
            "mcp_endpoint, encrypted_credentials"
        ).eq("id", site_id).single().execute()

        if not result.data:
            return None

        return await WordPressMcpService.from_site_credentials(
            mcp_endpoint=result.data["mcp_endpoint"],
            encrypted_credentials=result.data["encrypted_credentials"],
        )

    def _format_reference_analysis(self, article: Dict[str, Any]) -> str:
        """参考記事の分析結果をフォーマット"""
        return f"""
## 参考記事分析

**タイトル**: {article.get('title', '')}

**構造**:
{article.get('content', '')[:2000]}...

**特徴**:
- 投稿タイプ: {article.get('type', 'post')}
- カテゴリ: {', '.join(article.get('categories', []))}
"""

    def _analyze_posts_style(self, posts: List[Dict[str, Any]]) -> str:
        """投稿スタイルを分析"""
        if not posts:
            return "スタイル情報なし"

        titles = [p.get("title", "") for p in posts[:5]]
        return f"""
## サイトのスタイル分析

**最近の記事タイトル例**:
{chr(10).join(f'- {t}' for t in titles)}

このサイトのトンマナに合わせて記事を作成してください。
"""

    def _build_system_prompt(self, style_analysis: str) -> str:
        """システムプロンプトを構築"""
        return f"""あなたはWordPressブログ記事作成のエキスパートです。

ユーザーのリクエストに基づいて、高品質なブログ記事を作成してください。

{style_analysis}

## 重要な指示

1. **情報収集**: 記事作成に必要な情報が不足している場合は、ユーザーに質問してください。
   質問は以下のJSON形式で出力してください:
   ```json
   {{"questions": [{{"question_id": "q1", "question": "質問内容", "input_type": "text"}}]}}
   ```

2. **記事作成**: 十分な情報がある場合は、Gutenbergブロック形式で記事を作成してください。
   記事は以下のJSON形式で出力してください:
   ```json
   {{"article": {{"title": "タイトル", "content": "<!-- wp:paragraph -->...", "excerpt": "抜粋"}}}}
   ```

3. **トンマナ**: 参考記事やサイトのスタイルに合わせて執筆してください。

4. **画像**: ユーザーが画像を提供した場合は、適切な場所に配置してください。
"""

    def _build_user_input(
        self,
        user_prompt: str,
        reference_analysis: str,
        uploaded_images: List,
    ) -> str:
        """ユーザー入力を構築"""
        parts = [f"## リクエスト\n\n{user_prompt}"]

        if reference_analysis:
            parts.append(reference_analysis)

        if uploaded_images:
            images_info = "\n".join(
                f"- {img.filename}" for img in uploaded_images
            )
            parts.append(f"## 提供された画像\n\n{images_info}")

        return "\n\n".join(parts)

    def _parse_ai_questions(self, content: str) -> List:
        """AIの出力から質問を解析"""
        from ..context import AIQuestion
        import re

        # JSON形式の質問を探す
        pattern = r'\{"questions":\s*\[(.*?)\]\}'
        match = re.search(pattern, content, re.DOTALL)

        if not match:
            return []

        try:
            questions_json = json.loads(f'{{"questions": [{match.group(1)}]}}')
            return [
                AIQuestion(
                    question_id=q.get("question_id", f"q{i}"),
                    question=q.get("question", ""),
                    input_type=q.get("input_type", "text"),
                )
                for i, q in enumerate(questions_json.get("questions", []))
            ]
        except json.JSONDecodeError:
            return []

    async def _create_draft(
        self,
        process_id: str,
        context: BlogContext,
        generated_content: str,
        mcp_service: WordPressMcpService,
    ) -> None:
        """下書き記事を作成"""
        import re

        await self._update_process_state(
            process_id,
            current_step_name="creating_draft",
            progress_percentage=80,
        )

        await self._publish_event(
            process_id,
            context.user_id,
            "step_started",
            {"step": "creating_draft"},
        )

        # 記事データを解析
        pattern = r'\{"article":\s*(\{.*?\})\}'
        match = re.search(pattern, generated_content, re.DOTALL)

        if match:
            try:
                article_json = json.loads(match.group(1))
                title = article_json.get("title", "無題の記事")
                content = article_json.get("content", generated_content)
                excerpt = article_json.get("excerpt")
            except json.JSONDecodeError:
                title = "無題の記事"
                content = generated_content
                excerpt = None
        else:
            title = "無題の記事"
            content = generated_content
            excerpt = None

        # MCP経由で下書き作成
        result = await mcp_service.create_draft_post(
            title=title,
            content=content,
            excerpt=excerpt,
        )

        context.draft_post_id = result.get("post_id")
        context.draft_preview_url = result.get("preview_url")
        context.draft_edit_url = result.get("edit_url")
        context.current_step = "completed"

        await self._update_process_state(
            process_id,
            status="completed",
            current_step_name="completed",
            progress_percentage=100,
            context=context,
            draft_post_id=context.draft_post_id,
            draft_preview_url=context.draft_preview_url,
            draft_edit_url=context.draft_edit_url,
        )

        await self._publish_event(
            process_id,
            context.user_id,
            "generation_completed",
            {
                "draft_post_id": context.draft_post_id,
                "preview_url": context.draft_preview_url,
                "edit_url": context.draft_edit_url,
            },
        )

    async def submit_user_input(
        self,
        process_id: str,
        input_type: str,
        payload: Dict[str, Any],
    ) -> None:
        """ユーザー入力を処理"""
        # 現在の状態を取得
        result = supabase.table("blog_generation_state").select(
            "*"
        ).eq("id", process_id).single().execute()

        if not result.data:
            raise Exception("プロセスが見つかりません")

        state = result.data
        context = BlogContext.from_dict(state.get("blog_context", {}))
        context.user_id = state["user_id"]
        context.process_id = process_id

        if input_type == "additional_info":
            # ユーザーの回答を保存
            context.user_answers = payload.get("answers", {})

            # 入力待ち状態を解除
            await self._update_process_state(
                process_id,
                is_waiting_for_input=False,
                input_type=None,
                context=context,
            )

            # 生成を再開
            asyncio.create_task(
                self._continue_generation(process_id, context)
            )

    async def _continue_generation(
        self,
        process_id: str,
        context: BlogContext,
    ) -> None:
        """ユーザー入力後に生成を継続"""
        try:
            await self._update_process_state(
                process_id,
                status="in_progress",
                current_step_name="generating_content",
                progress_percentage=60,
            )

            mcp_service = await self._get_mcp_service(context.wordpress_site_id)
            if not mcp_service:
                raise Exception("WordPress接続情報が見つかりません")

            # 回答を含めて再度生成
            user_input = self._build_user_input(
                context.user_prompt,
                "",
                context.uploaded_images,
            )

            # 回答を追加
            answers_text = "\n".join(
                f"- {k}: {v}" for k, v in context.user_answers.items()
            )
            user_input += f"\n\n## 追加情報\n\n{answers_text}"

            response = self.client.responses.create(
                model=self.model,
                input=[
                    {"role": "system", "content": self._build_system_prompt("")},
                    {"role": "user", "content": user_input},
                ],
                background=True,
                store=True,
            )

            while response.status in {"queued", "in_progress"}:
                await asyncio.sleep(POLL_INTERVAL)
                response = self.client.responses.retrieve(response.id)

            if response.status == "failed":
                raise Exception(f"生成に失敗しました: {response.error}")

            generated_content = response.output_text
            await self._create_draft(process_id, context, generated_content, mcp_service)

        except Exception as e:
            logger.error(f"継続生成エラー: {e}")
            await self._update_process_state(
                process_id,
                status="error",
                error_message=str(e),
            )

    async def run_generation(
        self,
        process_id: str,
        user_id: str,
        user_prompt: str,
        reference_url: Optional[str],
        wordpress_site: Dict[str, Any],
    ) -> None:
        """
        外部から呼び出し可能な生成メソッド

        Args:
            process_id: プロセスID（既にDBに作成済み）
            user_id: ユーザーID
            user_prompt: ユーザーの記事作成リクエスト
            reference_url: 参考記事URL
            wordpress_site: WordPressサイト情報
        """
        context = BlogContext(
            user_prompt=user_prompt,
            reference_url=reference_url,
            wordpress_site_id=wordpress_site["id"],
            process_id=process_id,
            user_id=user_id,
            current_step="start",
        )

        await self._run_generation(process_id, context)

    async def continue_generation(
        self,
        process_id: str,
        user_id: str,
        user_answers: Dict[str, Any],
        wordpress_site: Dict[str, Any],
    ) -> None:
        """
        ユーザー入力後に生成を継続（外部から呼び出し可能）

        Args:
            process_id: プロセスID
            user_id: ユーザーID
            user_answers: ユーザーの回答
            wordpress_site: WordPressサイト情報
        """
        # 現在のコンテキストを取得
        result = supabase.table("blog_generation_state").select(
            "blog_context, user_prompt, reference_url"
        ).eq("id", process_id).single().execute()

        if not result.data:
            raise Exception("プロセスが見つかりません")

        state = result.data
        context = BlogContext.from_dict(state.get("blog_context", {}))
        context.user_id = user_id
        context.process_id = process_id
        context.wordpress_site_id = wordpress_site["id"]
        context.user_answers = user_answers
        context.user_prompt = state.get("user_prompt", "")
        context.reference_url = state.get("reference_url")

        await self._continue_generation(process_id, context)

    async def get_process_state(self, process_id: str) -> Optional[Dict[str, Any]]:
        """プロセス状態を取得"""
        result = supabase.table("blog_generation_state").select(
            "*"
        ).eq("id", process_id).single().execute()

        return result.data

    async def cancel_generation(self, process_id: str) -> bool:
        """生成をキャンセル"""
        result = supabase.table("blog_generation_state").select(
            "response_id, user_id"
        ).eq("id", process_id).single().execute()

        if not result.data:
            return False

        response_id = result.data.get("response_id")
        user_id = result.data.get("user_id")

        # OpenAI Responses APIのキャンセル
        if response_id:
            try:
                self.client.responses.cancel(response_id)
            except Exception as e:
                logger.warning(f"レスポンスキャンセルエラー: {e}")

        await self._update_process_state(
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
