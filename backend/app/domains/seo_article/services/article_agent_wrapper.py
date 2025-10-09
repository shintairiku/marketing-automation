# -*- coding: utf-8 -*-
"""
Article Agent Wrapper Service

fact_check_multi_agent.pyの機能をWebアプリケーション向けにラップしたサービス。
DDDアーキテクチャに統合し、REST API / WebSocket経由で使用可能にします。
"""

import asyncio
import json
import logging
import tempfile
from dataclasses import replace
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional
from uuid import uuid4

from app.domains.seo_article.services.flow_service import get_supabase_client
from app.domains.seo_article.services import article_agent_service as agent_module

logger = logging.getLogger(__name__)


class ArticleAgentSession:
    """記事編集エージェントセッション"""

    def __init__(
        self,
        session_id: str,
        article_id: str,
        user_id: str,
        temp_dir: Path,
    ):
        self.session_id = session_id
        self.article_id = article_id
        self.user_id = user_id
        self.temp_dir = temp_dir
        self.article_file = temp_dir / f"{article_id}.html"
        self.context: Optional[agent_module.AppContext] = None
        self.agent: Optional[agent_module.Agent] = None
        self.session_store: Optional[agent_module.SQLiteSession] = None
        self.conversation_history: List[Dict[str, Any]] = []

    async def initialize(self, article_content: str) -> None:
        """セッションを初期化"""
        # 記事ファイルを作成
        self.article_file.write_text(article_content, encoding="utf-8")

        # コンテキストを作成
        self.context = agent_module.AppContext(
            root=self.temp_dir,
            target_path=self.article_file,
            article_path=self.article_file,
            session_id=self.session_id,
        )

        # セッションストアを作成
        self.session_store = agent_module.SQLiteSession(self.session_id)

        # エージェントを作成
        self.agent = agent_module.build_text_edit_agent(
            model="gpt-4o",
            tool_choice="auto",
            temperature=0.3,
        )

        logger.info(f"Initialized agent session {self.session_id}")

    async def chat(self, user_message: str) -> AsyncGenerator[str, None]:
        """エージェントとチャット"""
        if not self.agent or not self.context or not self.session_store:
            raise Exception("Session not initialized")

        try:
            # ユーザーメッセージを履歴に追加
            self.conversation_history.append({
                "role": "user",
                "content": user_message,
            })

            # Run config
            run_config = agent_module.make_run_config(
                workflow_name="article-edit",
                trace_id=None,
                group_id=self.session_id,
                trace_metadata={"article_id": self.article_id},
                tracing_disabled=True,
                model_settings=agent_module.build_model_settings(
                    tool_choice="auto",
                    temperature=0.3,
                ),
            )

            # エージェント実行
            result = await agent_module.Runner.run(
                self.agent,
                input=user_message,
                context=self.context,
                session=self.session_store,
                run_config=run_config,
            )

            # レスポンスを取得
            output_text = ""
            if result.final_output:
                output_text = result.final_output if isinstance(result.final_output, str) else str(
                    result.final_output)

            # アシスタントメッセージを履歴に追加
            self.conversation_history.append({
                "role": "assistant",
                "content": output_text,
            })

            # ストリーミング形式で返す
            yield output_text

        except Exception as e:
            error_msg = f"エラーが発生しました: {str(e)}"
            logger.error(f"Chat error: {e}", exc_info=True)
            yield error_msg

    def get_current_content(self) -> str:
        """現在の記事内容を取得"""
        if self.article_file.exists():
            return self.article_file.read_text(encoding="utf-8")
        return ""

    def get_diff(self, original_content: str) -> Dict[str, Any]:
        """差分を取得"""
        current = self.get_current_content()
        return {
            "original": original_content,
            "current": current,
            "has_changes": original_content != current,
        }

    async def cleanup(self) -> None:
        """セッションをクリーンアップ"""
        try:
            if self.article_file.exists():
                self.article_file.unlink()
            logger.info(f"Cleaned up session {self.session_id}")
        except Exception as e:
            logger.error(f"Cleanup error: {e}")


class ArticleAgentService:
    """記事編集エージェントサービス"""

    def __init__(self):
        self.supabase = get_supabase_client()
        self.sessions: Dict[str, ArticleAgentSession] = {}
        self.temp_base = Path(tempfile.gettempdir()) / "article-agent-sessions"
        self.temp_base.mkdir(exist_ok=True, parents=True)

    async def create_session(self, article_id: str, user_id: str) -> str:
        """新しいセッションを作成"""
        try:
            # 記事を取得
            result = self.supabase.table("articles").select("*").eq("id", article_id).eq("user_id",
                                                                                         user_id).execute()

            if not result.data or len(result.data) == 0:
                raise Exception(f"Article {article_id} not found or access denied")

            article = result.data[0]
            article_content = article.get("content", "")

            # セッションIDを生成
            session_id = str(uuid4())

            # 一時ディレクトリを作成
            temp_dir = self.temp_base / session_id
            temp_dir.mkdir(exist_ok=True, parents=True)

            # セッションオブジェクトを作成
            session = ArticleAgentSession(
                session_id=session_id,
                article_id=article_id,
                user_id=user_id,
                temp_dir=temp_dir,
            )

            # 初期化
            await session.initialize(article_content)

            # セッションを保存
            self.sessions[session_id] = session

            logger.info(f"Created agent session {session_id} for article {article_id}")

            return session_id

        except Exception as e:
            logger.error(f"Error creating session: {e}", exc_info=True)
            raise

    async def chat(self, session_id: str, user_message: str) -> AsyncGenerator[str, None]:
        """エージェントとチャット"""
        if session_id not in self.sessions:
            raise Exception(f"Session {session_id} not found")

        session = self.sessions[session_id]

        async for chunk in session.chat(user_message):
            yield chunk

    async def get_current_content(self, session_id: str) -> str:
        """現在のコンテンツを取得"""
        if session_id not in self.sessions:
            raise Exception(f"Session {session_id} not found")

        session = self.sessions[session_id]
        return session.get_current_content()

    async def get_diff(self, session_id: str) -> Dict[str, Any]:
        """差分を取得"""
        if session_id not in self.sessions:
            raise Exception(f"Session {session_id} not found")

        session = self.sessions[session_id]

        # 元の記事を取得
        result = self.supabase.table("articles").select("content").eq("id", session.article_id).execute()

        if not result.data or len(result.data) == 0:
            raise Exception("Article not found")

        original_content = result.data[0].get("content", "")

        return session.get_diff(original_content)

    async def save_changes(self, session_id: str) -> None:
        """変更を保存"""
        if session_id not in self.sessions:
            raise Exception(f"Session {session_id} not found")

        session = self.sessions[session_id]
        current_content = session.get_current_content()

        # DBに保存
        result = self.supabase.table("articles").update({
            "content": current_content
        }).eq("id", session.article_id).eq("user_id", session.user_id).execute()

        if not result.data:
            raise Exception("Failed to save article")

        logger.info(f"Saved changes for article {session.article_id}")

    async def discard_changes(self, session_id: str) -> None:
        """変更を破棄"""
        if session_id not in self.sessions:
            raise Exception(f"Session {session_id} not found")

        session = self.sessions[session_id]

        # 元の記事を取得
        result = self.supabase.table("articles").select("content").eq("id", session.article_id).execute()

        if not result.data or len(result.data) == 0:
            raise Exception("Article not found")

        original_content = result.data[0].get("content", "")

        # ファイルを元に戻す
        session.article_file.write_text(original_content, encoding="utf-8")

        logger.info(f"Discarded changes for article {session.article_id}")

    async def close_session(self, session_id: str) -> None:
        """セッションを閉じる"""
        if session_id in self.sessions:
            session = self.sessions[session_id]
            await session.cleanup()
            del self.sessions[session_id]

            # 一時ディレクトリを削除
            try:
                session.temp_dir.rmdir()
            except Exception as e:
                logger.warning(f"Failed to remove temp dir: {e}")

            logger.info(f"Closed session {session_id}")

    async def get_conversation_history(self, session_id: str) -> List[Dict[str, Any]]:
        """会話履歴を取得"""
        if session_id not in self.sessions:
            raise Exception(f"Session {session_id} not found")

        session = self.sessions[session_id]
        return session.conversation_history


# Singleton instance
_article_agent_service: Optional[ArticleAgentService] = None


def get_article_agent_service() -> ArticleAgentService:
    """Get or create the article agent service singleton"""
    global _article_agent_service
    if _article_agent_service is None:
        _article_agent_service = ArticleAgentService()
    return _article_agent_service
