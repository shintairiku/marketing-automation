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
from app.domains.seo_article.services.version_service import get_version_service
from app.domains.seo_article.services import article_agent_service as agent_module

logger = logging.getLogger(__name__)


SEO_CODEX_INSTRUCTIONS = """
あなたはSEO記事のHTML編集を専門とする編集エージェントです。
必ず以下に従ってください。もし編集指示がない場合は、ツールを呼び出さず、通常会話を続けてください。

# 目的
- ユーザーの編集指示に基づき、SEO記事（HTMLファイル）の必要箇所のみを編集します。
- 編集は必ず apply_patch を使い、差分パッチで行います（ファイル全体の上書きは禁止）。
- HTML構造とタグの整合性を保ちながら内容を改善します。

# 使えるツール
- read_file(offset, limit_lines, with_line_numbers): 記事の必要箇所を参照するための閲覧ツールです。編集が必要になった際に活用してください。
- apply_patch(patch): Codex互換の差分パッチを適用します（*** Begin Patch〜*** End Patch）。
- web_search(query, recency_days=None): 追加情報のリサーチや事実確認が必要な場合にのみ使用してください。

# パッチ仕様（厳守）
- 全体を `*** Begin Patch` と `*** End Patch` で囲む。
- すべての変更は `*** Update File: <path>` を用いる。必要に応じて `*** Move to: <newpath>` を追加。
- 各ハンクは `@@` で開始し、前後の文脈行（先頭スペース）を十分に含める。
- `+` 行で追加、`-` 行で削除、` ` 行で文脈を表す。

# 編集ガイドライン
- 「わかりやすく」: 専門語を補足し、具体例や箇条書きで整理する。
- 「いい感じに」: 冗長な表現を削り、リズム良く読みやすく整える。
- HTMLタグ（<h1>, <h2>, <p>, <ul>, <li> など）の整合性を保ち、閉じ忘れを避ける。
- 既存の構造や順序を尊重しつつ、必要な範囲でのみ編集する。
- 会話のみのリクエストや挨拶にはツールを使わず、通常の対話で応答する。
- ファクトチェックや根拠が必要な場合は web_search ツールで調査し、結果を簡潔に説明する。

# 出力
- apply_patch で編集内容を提示し、ファイル全体の生テキストを直接出力しない。
- 必要に応じて適用後の確認手順を一言添える。
"""


class PendingChange:
    """承認待ちの変更"""
    def __init__(self, change_id: str, old_text: str, new_text: str, description: str = ""):
        self.change_id = change_id
        self.old_text = old_text
        self.new_text = new_text
        self.description = description
        self.approved = False


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
        self.original_file = temp_dir / f"{article_id}_original.html"
        self.context: Optional[agent_module.AppContext] = None
        self.agent: Optional[agent_module.Agent] = None
        self.session_store: Optional[agent_module.SQLiteSession] = None
        self.conversation_history: List[Dict[str, Any]] = []
        self.pending_changes: List[PendingChange] = []
        self.original_content: str = ""
        self.session_trace: Optional[Any] = None  # OpenAI Agents SDK trace object
        self.article_title: str = ""
        self.article_metadata: Dict[str, Any] = {}
        self._lock = asyncio.Lock()

    async def initialize(self, article_content: str, article_title: str = "", metadata: Optional[Dict[str, Any]] = None) -> None:
        """セッションを初期化"""
        # オリジナルコンテンツを保存
        self.original_content = article_content
        self.article_title = article_title or "Untitled"
        self.article_metadata = metadata or {}

        # 記事ファイルを作成
        self.article_file.write_text(article_content, encoding="utf-8")
        self.original_file.write_text(article_content, encoding="utf-8")

        # コンテキストを作成
        self.context = agent_module.AppContext(
            root=self.temp_dir,
            target_path=self.article_file,
            article_path=self.article_file,
            session_id=self.session_id,
        )

        # セッションストアを作成
        self.session_store = agent_module.SQLiteSession(self.session_id)

        # エージェントを作成（SEO記事編集用）
        web_tool = agent_module.create_web_search_tool()
        self.agent = agent_module.build_text_edit_agent(
            model="gpt-5-mini",
            tool_choice="auto",
            instructions=SEO_CODEX_INSTRUCTIONS,
            include_web_search=True,
            web_search_tool=web_tool,
        )

        # トレースを初期化（セッション全体で1つのトレースを使用）
        try:
            trace_id = agent_module.agent_tracing.gen_trace_id()
            self.session_trace = agent_module.agent_tracing.trace(
                workflow_name="seo-article-edit",
                trace_id=trace_id,
                group_id=self.session_id,
                metadata={
                    "article_id": self.article_id,
                    "user_id": self.user_id,
                    "mode": "web-edit"
                },
                disabled=False,
            )
            self.session_trace.start(mark_as_current=True)
            logger.info(f"Initialized agent session {self.session_id} with trace_id: {trace_id}")
        except Exception as e:
            logger.warning(f"Failed to initialize trace: {e}, continuing without tracing")
            logger.info(f"Initialized agent session {self.session_id}")

    async def chat(self, user_message: str) -> AsyncGenerator[str, None]:
        """エージェントとチャット"""
        if not self.agent or not self.context or not self.session_store:
            raise Exception("Session not initialized")

        async with self._lock:
            try:
                enhanced_message = user_message
                if len(self.conversation_history) == 0:
                    file_name = self.article_file.name
                    context_lines = [f"対象ファイル: {file_name}"]
                    if self.article_title:
                        context_lines.append(f"記事タイトル: {self.article_title}")
                    if self.article_metadata:
                        metadata_json = json.dumps(self.article_metadata, ensure_ascii=False, indent=2)
                        context_lines.append("記事メタデータ:")
                        context_lines.append(metadata_json)

                    guidance = (
                        "補足: 編集や修正が必要な場合のみ read_file と apply_patch を使用してください。"
                        " 単なる挨拶や雑談には通常の会話で応答し、必要に応じて web_search ツールでリサーチできます。"
                    )

                    context_block = "\n".join(context_lines)
                    enhanced_message = (
                        f"{context_block}\n\n{guidance}\n\nユーザーからのメッセージ:\n{user_message}"
                    )

                self.conversation_history.append({
                    "role": "user",
                    "content": user_message,
                })

                trace_id = self.session_trace.trace_id if self.session_trace else None
                run_config = agent_module.make_run_config(
                    workflow_name="seo-article-edit",
                    trace_id=trace_id,
                    group_id=self.session_id,
                    trace_metadata={
                        "article_id": self.article_id,
                        "user_id": self.user_id,
                        "mode": "web-edit",
                        "message_count": str(len(self.conversation_history))
                    },
                    tracing_disabled=(self.session_trace is None),
                    model_settings=agent_module.build_model_settings(
                        tool_choice="auto",
                    ),
                )

                if trace_id:
                    logger.info(
                        "Agent execution with trace_id: %s, message #%s",
                        trace_id,
                        len(self.conversation_history),
                    )

                result = await agent_module.Runner.run(
                    self.agent,
                    input=enhanced_message,
                    context=self.context,
                    session=self.session_store,
                    run_config=run_config,
                )

                output_text = ""
                if result.final_output:
                    output_text = result.final_output if isinstance(result.final_output, str) else str(
                        result.final_output
                    )

                self.conversation_history.append({
                    "role": "assistant",
                    "content": output_text,
                })

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

    def extract_pending_changes(self) -> List[Dict[str, Any]]:
        """apply_patchによる変更を検出して承認待ちリストに追加（統合差分形式）"""
        current_content = self.get_current_content()

        if current_content == self.original_content:
            return []

        # 行ごとに差分検出
        original_lines = self.original_content.splitlines()
        current_lines = current_content.splitlines()

        # 最新の変更のみを保持するためにリストを初期化
        self.pending_changes = []

        # 変更されたセクションを検出
        import difflib
        differ = difflib.SequenceMatcher(None, original_lines, current_lines)

        changes = []
        for tag, i1, i2, j1, j2 in differ.get_opcodes():
            if tag in ['replace', 'delete', 'insert']:
                change_id = f"change_{len(self.pending_changes)}_{i1}_{i2}"
                old_text = '\n'.join(original_lines[i1:i2])
                new_text = '\n'.join(current_lines[j1:j2])

                # コンテキスト（前後3行）を追加
                context_before_start = max(0, i1 - 3)
                context_before = '\n'.join(original_lines[context_before_start:i1])

                context_after_end = min(len(original_lines), i2 + 3)
                context_after = '\n'.join(original_lines[i2:context_after_end])

                pending_change = PendingChange(
                    change_id=change_id,
                    old_text=old_text,
                    new_text=new_text,
                    description=f"{tag.capitalize()} at lines {i1+1}-{i2}"
                )
                self.pending_changes.append(pending_change)

                changes.append({
                    "change_id": change_id,
                    "old_text": old_text,
                    "new_text": new_text,
                    "description": pending_change.description,
                    "approved": False,
                    "line_start": i1,
                    "line_end": i2,
                    "context_before": context_before,
                    "context_after": context_after,
                    "change_type": tag
                })

        # ファイルをオリジナルに戻す（承認されるまで適用しない）
        self.article_file.write_text(self.original_content, encoding="utf-8")

        return changes

    def get_unified_diff_view(self) -> Dict[str, Any]:
        """VSCode風の統合差分ビューを生成（変更がない場合でも記事全体を返す）"""
        original_lines = self.original_content.splitlines()

        # 変更がない場合は記事全体を通常の行として返す
        if not self.pending_changes:
            lines = []
            for i, line in enumerate(original_lines):
                lines.append({
                    "type": "unchanged",
                    "content": line,
                    "line_number": i + 1
                })
            return {
                "lines": lines,
                "has_changes": False
            }

        # 変更箇所のマップを作成
        change_map = {}
        for change in self.pending_changes:
            # change_idから行番号を抽出
            parts = change.change_id.split('_')
            if len(parts) >= 4:
                start_line = int(parts[2])
                end_line = int(parts[3])
                change_map[(start_line, end_line)] = change

        # 統合差分を生成
        lines = []
        i = 0
        while i < len(original_lines):
            # この行が変更箇所かチェック
            change_found = None
            for (start, end), change in change_map.items():
                if start <= i < end:
                    change_found = (start, end, change)
                    break

            if change_found:
                start, end, change = change_found
                # 変更箇所を追加
                lines.append({
                    "type": "change",
                    "change_id": change.change_id,
                    "old_lines": original_lines[start:end],
                    "new_lines": change.new_text.splitlines() if change.new_text else [],
                    "line_number": start + 1,
                    "approved": change.approved
                })
                i = end
            else:
                # 通常の行を追加
                lines.append({
                    "type": "unchanged",
                    "content": original_lines[i],
                    "line_number": i + 1
                })
                i += 1

        return {
            "lines": lines,
            "has_changes": len(self.pending_changes) > 0
        }

    def get_pending_changes(self) -> List[Dict[str, Any]]:
        """承認待ちの変更を取得"""
        return [{
            "change_id": change.change_id,
            "old_text": change.old_text,
            "new_text": change.new_text,
            "description": change.description,
            "approved": change.approved
        } for change in self.pending_changes]

    def approve_change(self, change_id: str) -> bool:
        """特定の変更を承認"""
        for change in self.pending_changes:
            if change.change_id == change_id:
                change.approved = True
                return True
        return False

    def reject_change(self, change_id: str) -> bool:
        """特定の変更を拒否"""
        for change in self.pending_changes:
            if change.change_id == change_id:
                self.pending_changes.remove(change)
                return True
        return False

    def apply_approved_changes(self) -> Dict[str, Any]:
        """承認された変更のみを適用し、新しいコンテンツと適用数を返す。"""
        if not self.pending_changes:
            return {"content": self.original_content, "applied_count": 0, "applied_change_ids": []}

        approved = [c for c in self.pending_changes if c.approved]
        if not approved:
            return {"content": self.original_content, "applied_count": 0, "applied_change_ids": []}

        content = self.original_content
        applied_ids: List[str] = []
        for change in approved:
            if change.old_text in content:
                content = content.replace(change.old_text, change.new_text, 1)
                applied_ids.append(change.change_id)

        # ファイルとセッション状態を更新
        self.article_file.write_text(content, encoding="utf-8")
        self.original_file.write_text(content, encoding="utf-8")
        self.original_content = content
        self.pending_changes = []

        return {
            "content": content,
            "applied_count": len(applied_ids),
            "applied_change_ids": applied_ids,
        }

    def clear_pending_changes(self) -> None:
        """承認待ち変更をすべてクリア"""
        self.pending_changes = []
        self.article_file.write_text(self.original_content, encoding="utf-8")
        self.original_file.write_text(self.original_content, encoding="utf-8")

    async def cleanup(self) -> None:
        """セッションをクリーンアップ"""
        try:
            # トレースを終了
            if self.session_trace:
                try:
                    self.session_trace.finish(reset_current=True)
                    logger.info(f"Finished trace for session {self.session_id}")
                except Exception as e:
                    logger.warning(f"Failed to finish trace: {e}")

            # ファイルをクリーンアップ
            if self.article_file.exists():
                self.article_file.unlink()
            if self.original_file.exists():
                self.original_file.unlink()
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
        self.version_service = get_version_service()

    async def _save_article_and_version(
        self,
        session: ArticleAgentSession,
        content: str,
        *,
        change_description: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Persist article content and store a version snapshot."""
        result = self.supabase.table("articles").update({
            "content": content
        }).eq("id", session.article_id).eq("user_id", session.user_id).execute()

        if not result.data:
            raise Exception("Failed to save article")

        if metadata is None:
            metadata = {}
        metadata = {**metadata, "agent_session_id": session.session_id}

        title = session.article_metadata.get("title") or result.data[0].get("title") or session.article_title

        await self.version_service.save_version(
            article_id=session.article_id,
            user_id=session.user_id,
            title=title,
            content=content,
            change_description=change_description,
            metadata=metadata,
        )

        session.article_metadata.update({"title": title, "content": content})

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
            article_title = article.get("title", "")

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
            await session.initialize(article_content, article_title=article_title, metadata=article)

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
        async with session._lock:
            return session.get_current_content()

    async def get_diff(self, session_id: str) -> Dict[str, Any]:
        """差分を取得"""
        if session_id not in self.sessions:
            raise Exception(f"Session {session_id} not found")

        session = self.sessions[session_id]
        async with session._lock:
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
        async with session._lock:
            current_content = session.get_current_content()
            await self._save_article_and_version(
                session,
                current_content,
                change_description="Manual save from AI agent session",
            )

            session.original_content = current_content
            session.pending_changes = []
            session.article_file.write_text(current_content, encoding="utf-8")
            session.original_file.write_text(current_content, encoding="utf-8")

            logger.info("Saved changes for article %s", session.article_id)

    async def discard_changes(self, session_id: str) -> None:
        """変更を破棄"""
        if session_id not in self.sessions:
            raise Exception(f"Session {session_id} not found")

        session = self.sessions[session_id]
        async with session._lock:
            result = self.supabase.table("articles").select("content").eq("id", session.article_id).execute()

            if not result.data or len(result.data) == 0:
                raise Exception("Article not found")

            original_content = result.data[0].get("content", "")
            session.article_file.write_text(original_content, encoding="utf-8")
            session.original_file.write_text(original_content, encoding="utf-8")
            session.original_content = original_content
            session.pending_changes = []

            logger.info("Discarded changes for article %s", session.article_id)

    async def close_session(self, session_id: str) -> None:
        """セッションを閉じる"""
        if session_id in self.sessions:
            session = self.sessions[session_id]
            async with session._lock:
                await session.cleanup()
                del self.sessions[session_id]

                try:
                    session.temp_dir.rmdir()
                except Exception as e:
                    logger.warning("Failed to remove temp dir: %s", e)

                logger.info("Closed session %s", session_id)

    async def get_conversation_history(self, session_id: str) -> List[Dict[str, Any]]:
        """会話履歴を取得"""
        if session_id not in self.sessions:
            raise Exception(f"Session {session_id} not found")

        session = self.sessions[session_id]
        return session.conversation_history

    async def extract_pending_changes(self, session_id: str) -> List[Dict[str, Any]]:
        """apply_patchによる変更を抽出"""
        if session_id not in self.sessions:
            raise Exception(f"Session {session_id} not found")

        session = self.sessions[session_id]
        async with session._lock:
            return session.extract_pending_changes()

    async def get_pending_changes(self, session_id: str) -> List[Dict[str, Any]]:
        """承認待ちの変更を取得"""
        if session_id not in self.sessions:
            raise Exception(f"Session {session_id} not found")

        session = self.sessions[session_id]
        async with session._lock:
            return session.get_pending_changes()

    async def get_unified_diff_view(self, session_id: str) -> Dict[str, Any]:
        """統合差分ビューを取得（VSCode風）"""
        if session_id not in self.sessions:
            raise Exception(f"Session {session_id} not found")

        session = self.sessions[session_id]
        async with session._lock:
            return session.get_unified_diff_view()

    async def approve_change(self, session_id: str, change_id: str) -> bool:
        """変更を承認"""
        if session_id not in self.sessions:
            raise Exception(f"Session {session_id} not found")

        session = self.sessions[session_id]
        async with session._lock:
            return session.approve_change(change_id)

    async def reject_change(self, session_id: str, change_id: str) -> bool:
        """変更を拒否"""
        if session_id not in self.sessions:
            raise Exception(f"Session {session_id} not found")

        session = self.sessions[session_id]
        async with session._lock:
            return session.reject_change(change_id)

    async def apply_approved_changes(self, session_id: str) -> Dict[str, Any]:
        """承認された変更を適用し、保存・バージョン管理も実行する。"""
        if session_id not in self.sessions:
            raise Exception(f"Session {session_id} not found")

        session = self.sessions[session_id]
        async with session._lock:
            apply_result = session.apply_approved_changes()
            applied_count = apply_result.get("applied_count", 0)
            content = apply_result.get("content", session.original_content)

            if applied_count > 0:
                await self._save_article_and_version(
                    session,
                    content,
                    change_description=f"AI agent auto-applied {applied_count} change(s)",
                    metadata={"applied_change_ids": apply_result.get("applied_change_ids", [])},
                )

            return apply_result

    async def clear_pending_changes(self, session_id: str) -> None:
        """承認待ち変更をクリア"""
        if session_id not in self.sessions:
            raise Exception(f"Session {session_id} not found")

        session = self.sessions[session_id]
        async with session._lock:
            session.clear_pending_changes()


# Singleton instance
_article_agent_service: Optional[ArticleAgentService] = None


def get_article_agent_service() -> ArticleAgentService:
    """Get or create the article agent service singleton"""
    global _article_agent_service
    if _article_agent_service is None:
        _article_agent_service = ArticleAgentService()
    return _article_agent_service
