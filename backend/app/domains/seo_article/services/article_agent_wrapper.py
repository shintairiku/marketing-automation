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
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional
from uuid import uuid4

from app.core.config import settings
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
        self.line_start: int = 0
        self.line_end: int = 0
        self.change_type: str = "replace"
        self.old_lines: List[str] = []
        self.new_lines: List[str] = []
        self.context_before: str = ""
        self.context_after: str = ""


class ArticleAgentSession:
    """記事編集エージェントセッション"""

    def __init__(
        self,
        session_id: str,
        article_id: str,
        user_id: str,
        temp_dir: Path,
        session_store_path: Path,
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
        self.session_store_path = session_store_path
        self.conversation_history: List[Dict[str, Any]] = []
        self.pending_changes: List[PendingChange] = []
        self.original_content: str = ""
        self.session_trace: Optional[Any] = None  # OpenAI Agents SDK trace object
        self.article_title: str = ""
        self.article_metadata: Dict[str, Any] = {}
        self._lock = asyncio.Lock()
        self._change_counter = 0

    async def initialize(
        self,
        article_content: str,
        article_title: str = "",
        metadata: Optional[Dict[str, Any]] = None,
        *,
        original_content: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """セッションを初期化"""
        # オリジナルコンテンツを保存
        if not self.temp_dir.exists():
            self.temp_dir.mkdir(parents=True, exist_ok=True)

        if not self.session_store_path.parent.exists():
            self.session_store_path.parent.mkdir(parents=True, exist_ok=True)

        base_original_content = original_content if original_content is not None else article_content
        self.original_content = base_original_content
        self.article_title = article_title or "Untitled"
        self.article_metadata = metadata or {}

        # 記事ファイルを作成
        self.article_file.write_text(article_content, encoding="utf-8")
        self.original_file.write_text(base_original_content, encoding="utf-8")

        # コンテキストを作成
        self.context = agent_module.AppContext(
            root=self.temp_dir,
            target_path=self.article_file,
            article_path=self.article_file,
            session_id=self.session_id,
        )

        # セッションストアを作成
        self.session_store = agent_module.SQLiteSession(self.session_id, db_path=str(self.session_store_path))

        if conversation_history is not None:
            self.conversation_history = conversation_history
        elif not self.conversation_history:
            self.conversation_history = []

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
        """apply_patchによる変更を検出し、既存の変更に追加する。"""
        current_content = self.get_current_content()

        if current_content == self.original_content:
            return []

        original_lines = self.original_content.splitlines()
        current_lines = current_content.splitlines()

        import difflib

        existing_keys = {
            (change.line_start, change.line_end, '\n'.join(change.new_lines))
            for change in self.pending_changes
        }

        differ = difflib.SequenceMatcher(None, original_lines, current_lines)

        new_changes: List[Dict[str, Any]] = []
        updated_pending: List[PendingChange] = list(self.pending_changes)

        for tag, i1, i2, j1, j2 in differ.get_opcodes():
            if tag not in ['replace', 'delete', 'insert']:
                continue

            old_lines = original_lines[i1:i2]
            new_lines = current_lines[j1:j2]
            key = (i1, i2, '\n'.join(new_lines))

            if key in existing_keys:
                continue

            old_text = '\n'.join(old_lines)
            new_text = '\n'.join(new_lines)

            context_before_start = max(0, i1 - 3)
            context_before = '\n'.join(original_lines[context_before_start:i1])

            context_after_end = min(len(original_lines), i2 + 3)
            context_after = '\n'.join(original_lines[i2:context_after_end])

            change_id = f"change_{self._change_counter}"
            self._change_counter += 1

            pending_change = PendingChange(
                change_id=change_id,
                old_text=old_text,
                new_text=new_text,
                description=f"{tag.capitalize()} at lines {i1 + 1}-{i2}"
            )
            pending_change.line_start = i1
            pending_change.line_end = i2
            pending_change.change_type = tag
            pending_change.old_lines = old_lines
            pending_change.new_lines = new_lines
            pending_change.context_before = context_before
            pending_change.context_after = context_after

            updated_pending.append(pending_change)
            existing_keys.add(key)

            new_changes.append({
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

        if not new_changes:
            # 既存の pending_changes を維持したまま早期リターン
            self.article_file.write_text(self.original_content, encoding="utf-8")
            return []

        # 変更位置でソート
        updated_pending.sort(key=lambda c: (c.line_start, c.line_end, c.change_id))
        self.pending_changes = updated_pending

        # ファイルをオリジナルに戻す（承認されるまで適用しない）
        self.article_file.write_text(self.original_content, encoding="utf-8")

        return new_changes

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

        lines: List[Dict[str, Any]] = []
        sorted_changes = sorted(self.pending_changes, key=lambda c: (c.line_start, c.line_end, c.change_id))

        cursor = 0
        for change in sorted_changes:
            start = change.line_start
            end = change.line_end

            # 追加される行を挿入する前に、未変更部分を追加
            while cursor < start and cursor < len(original_lines):
                lines.append({
                    "type": "unchanged",
                    "content": original_lines[cursor],
                    "line_number": cursor + 1
                })
                cursor += 1

            old_lines = change.old_lines if change.old_lines else []
            new_lines = change.new_lines if change.new_lines else []

            lines.append({
                "type": "change",
                "change_id": change.change_id,
                "old_lines": old_lines,
                "new_lines": new_lines,
                "line_number": (start + 1) if start < len(original_lines) else len(original_lines) + 1,
                "approved": change.approved,
                "change_type": change.change_type,
                "context_before": change.context_before,
                "context_after": change.context_after,
            })

            cursor = max(cursor, end)

        # 末尾の未変更部分
        while cursor < len(original_lines):
            lines.append({
                "type": "unchanged",
                "content": original_lines[cursor],
                "line_number": cursor + 1
            })
            cursor += 1

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
            "approved": change.approved,
            "line_start": change.line_start,
            "line_end": change.line_end,
            "change_type": change.change_type,
            "context_before": change.context_before,
            "context_after": change.context_after
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
        self._change_counter = 0

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
        self._change_counter = 0

    async def cleanup(self, *, remove_session_store: bool = False) -> None:
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
            if remove_session_store and self.session_store_path.exists():
                try:
                    self.session_store_path.unlink()
                except Exception as e:
                    logger.warning(f"Failed to remove session store: {e}")
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
        self.session_store_base = Path(settings.agent_session_storage_dir)
        self.session_store_base.mkdir(exist_ok=True, parents=True)
        self.version_service = get_version_service()
        self.initial_assistant_message = (
            "こんにちは！記事の編集をお手伝いします。どのような編集をご希望ですか？"
        )

    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _session_temp_dir(self, session_id: str) -> Path:
        path = self.temp_base / session_id
        path.mkdir(exist_ok=True, parents=True)
        return path

    def _default_session_store_key(self, session_id: str) -> str:
        return f"{session_id}.sqlite3"

    def _session_store_path_from_key(self, key: str) -> Path:
        return self.session_store_base / key

    def _fetch_article_record(self, article_id: str, user_id: str) -> Dict[str, Any]:
        result = (
            self.supabase.table("articles")
            .select("*")
            .eq("id", article_id)
            .eq("user_id", user_id)
            .execute()
        )
        if not result.data:
            raise Exception(f"Article {article_id} not found or access denied")
        return result.data[0]

    def _pause_other_sessions(
        self,
        article_id: str,
        user_id: str,
        *,
        except_session_id: Optional[str] = None,
    ) -> None:
        builder = (
            self.supabase.table("article_agent_sessions")
            .update({"status": "paused", "updated_at": self._now_iso()})
            .eq("article_id", article_id)
            .eq("user_id", user_id)
            .neq("status", "closed")
        )
        if except_session_id:
            builder = builder.neq("id", except_session_id)
        try:
            builder.execute()
        except Exception as exc:
            logger.warning("Failed to pause sessions for article %s: %s", article_id, exc)

    def _preview_text(self, text: str, limit: int = 120) -> str:
        sanitized = text.strip().replace("\n", " ")
        if len(sanitized) <= limit:
            return sanitized
        return sanitized[: limit - 1] + "…"

    def _get_last_message_preview(self, session_id: str) -> Optional[str]:
        try:
            result = (
                self.supabase.table("article_agent_messages")
                .select("content")
                .eq("session_id", session_id)
                .order("sequence", desc=True)
                .limit(1)
                .execute()
            )
            if result.data:
                content = result.data[0].get("content", "")
                if content:
                    return self._preview_text(content)
        except Exception as exc:
            logger.warning("Failed to load last message preview for %s: %s", session_id, exc)
        return None

    def _fetch_session_record(self, session_id: str) -> Optional[Dict[str, Any]]:
        result = (
            self.supabase.table("article_agent_sessions")
            .select("*")
            .eq("id", session_id)
            .execute()
        )
        if result.data:
            return result.data[0]
        return None

    def _fetch_active_session_record(self, article_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        result = (
            self.supabase.table("article_agent_sessions")
            .select("*")
            .eq("article_id", article_id)
            .eq("user_id", user_id)
            .eq("status", "active")
            .limit(1)
            .execute()
        )
        if result.data:
            return result.data[0]
        return None

    def _load_session_messages(self, session_id: str) -> List[Dict[str, Any]]:
        result = (
            self.supabase.table("article_agent_messages")
            .select("role, content, created_at, sequence")
            .eq("session_id", session_id)
            .order("sequence", desc=False)
            .execute()
        )
        rows = result.data or []
        return [
            {
                "role": row.get("role", "assistant"),
                "content": row.get("content") or "",
                "created_at": row.get("created_at"),
            }
            for row in rows
        ]

    def _append_message(
        self,
        session_id: str,
        role: str,
        content: str,
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        payload = {
            "session_id": session_id,
            "user_id": user_id,
            "role": role,
            "content": content,
            "metadata": metadata or {},
        }
        try:
            self.supabase.table("article_agent_messages").insert(payload).execute()
            if content and role in ("assistant", "user"):
                preview = self._preview_text(content)
                self._update_session_record(
                    session_id,
                    {"conversation_summary": preview},
                )
        except Exception as exc:
            logger.error("Failed to append agent message for session %s: %s", session_id, exc)

    def _update_session_record(self, session_id: str, updates: Dict[str, Any]) -> None:
        payload = {**updates}
        payload.setdefault("updated_at", self._now_iso())
        try:
            self.supabase.table("article_agent_sessions").update(payload).eq("id", session_id).execute()
        except Exception as exc:
            logger.error("Failed to update agent session %s: %s", session_id, exc)

    async def _hydrate_session(self, record: Dict[str, Any]) -> ArticleAgentSession:
        session_id = record["id"]
        temp_dir = self._session_temp_dir(session_id)
        store_path = self._session_store_path_from_key(record["session_store_key"])

        article_content = record.get("working_content")
        original_content = record.get("original_content")
        article_title = record.get("article_title") or ""
        metadata = record.get("metadata") or {}

        article_record: Optional[Dict[str, Any]] = None
        if article_content is None or original_content is None or not article_title:
            article_record = self._fetch_article_record(record["article_id"], record["user_id"])
            article_content = article_content or article_record.get("content", "")
            original_content = original_content or article_record.get("content", "")
            article_title = article_title or article_record.get("title", "")
            if not metadata:
                metadata = article_record

        if article_content is None:
            article_record = article_record or self._fetch_article_record(record["article_id"], record["user_id"])
            article_content = article_record.get("content", "")

        history_full = self._load_session_messages(session_id)
        history_for_session = [{"role": msg["role"], "content": msg["content"]} for msg in history_full]

        session = ArticleAgentSession(
            session_id=session_id,
            article_id=record["article_id"],
            user_id=record["user_id"],
            temp_dir=temp_dir,
            session_store_path=store_path,
        )
        await session.initialize(
            article_content,
            article_title=article_title,
            metadata=metadata,
            original_content=original_content,
            conversation_history=history_for_session,
        )
        self.sessions[session_id] = session
        return session

    async def _ensure_session_loaded(
        self,
        session_id: str,
        *,
        expected_user_id: Optional[str] = None,
        expected_article_id: Optional[str] = None,
    ) -> ArticleAgentSession:
        if session_id in self.sessions:
            session = self.sessions[session_id]
            if expected_user_id and session.user_id != expected_user_id:
                raise Exception("Access denied to session")
            if expected_article_id and session.article_id != expected_article_id:
                raise Exception("Session does not belong to specified article")
            return session

        record = self._fetch_session_record(session_id)
        if not record:
            raise Exception(f"Session {session_id} not found")

        if expected_user_id and record["user_id"] != expected_user_id:
            raise Exception("Access denied to session")
        if expected_article_id and record["article_id"] != expected_article_id:
            raise Exception("Session does not belong to specified article")

        return await self._hydrate_session(record)

    def _build_session_detail(self, record: Dict[str, Any]) -> Dict[str, Any]:
        messages = self._load_session_messages(record["id"])
        return {
            "session_id": record["id"],
            "article_id": record["article_id"],
            "status": record["status"],
             "summary": record.get("conversation_summary") or self._get_last_message_preview(record["id"]),
            "messages": messages,
            "last_activity_at": record.get("last_activity_at"),
        }

    def list_sessions(self, article_id: str, user_id: str) -> List[Dict[str, Any]]:
        result = (
            self.supabase.table("article_agent_sessions")
            .select(
                "id",
                "status",
                "created_at",
                "updated_at",
                "last_activity_at",
                "conversation_summary",
            )
            .eq("article_id", article_id)
            .eq("user_id", user_id)
            .order("last_activity_at", desc=True)
            .execute()
        )
        sessions: List[Dict[str, Any]] = []
        for record in result.data or []:
            summary = record.get("conversation_summary") or self._get_last_message_preview(record["id"])
            sessions.append(
                {
                    "session_id": record["id"],
                    "status": record.get("status", "paused"),
                    "created_at": record.get("created_at"),
                    "last_activity_at": record.get("last_activity_at"),
                    "summary": summary or "",
                }
            )
        return sessions

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
        self._update_session_record(
            session.session_id,
            {
                "original_content": content,
                "working_content": content,
                "last_activity_at": self._now_iso(),
            },
        )

    async def create_session(self, article_id: str, user_id: str, *, resume_existing: bool = True) -> str:
        """セッションを作成 or 既存を再利用"""
        try:
            if resume_existing:
                existing = self._fetch_active_session_record(article_id, user_id)
                if existing:
                    await self._ensure_session_loaded(
                        existing["id"],
                        expected_user_id=user_id,
                        expected_article_id=article_id,
                    )
                    logger.info("Resuming agent session %s for article %s", existing["id"], article_id)
                    return existing["id"]

            article = self._fetch_article_record(article_id, user_id)
            article_content = article.get("content", "")
            article_title = article.get("title", "")

            # pause other sessions before creating a new active one
            self._pause_other_sessions(article_id, user_id)

            session_id = str(uuid4())
            session_store_key = self._default_session_store_key(session_id)
            temp_dir = self._session_temp_dir(session_id)
            store_path = self._session_store_path_from_key(session_store_key)

            initial_history = [{"role": "assistant", "content": self.initial_assistant_message}]

            session = ArticleAgentSession(
                session_id=session_id,
                article_id=article_id,
                user_id=user_id,
                temp_dir=temp_dir,
                session_store_path=store_path,
            )

            await session.initialize(
                article_content,
                article_title=article_title,
                metadata=article,
                original_content=article_content,
                conversation_history=initial_history,
            )

            self.sessions[session_id] = session

            session_record = {
                "id": session_id,
                "article_id": article_id,
                "user_id": user_id,
                "organization_id": article.get("organization_id"),
                "status": "active",
                "session_store_key": session_store_key,
                "original_content": article_content,
                "working_content": article_content,
                "article_title": article_title,
                "metadata": article,
                "last_activity_at": self._now_iso(),
                "conversation_summary": self._preview_text(self.initial_assistant_message),
            }
            self.supabase.table("article_agent_sessions").insert(session_record).execute()
            self._append_message(session_id, "assistant", self.initial_assistant_message, user_id)

            logger.info("Created agent session %s for article %s", session_id, article_id)
            return session_id

        except Exception as e:
            logger.error(f"Error creating session: {e}", exc_info=True)
            raise

    async def activate_session(self, article_id: str, user_id: str, session_id: str) -> Dict[str, Any]:
        record = self._fetch_session_record(session_id)
        if not record:
            raise Exception(f"Session {session_id} not found")
        if record["user_id"] != user_id or record["article_id"] != article_id:
            raise Exception("Access denied to session")
        if record.get("status") == "closed":
            raise Exception("Cannot activate a closed session")

        self._pause_other_sessions(article_id, user_id, except_session_id=session_id)
        self._update_session_record(
            session_id,
            {"status": "active", "last_activity_at": self._now_iso()},
        )

        await self._ensure_session_loaded(
            session_id,
            expected_user_id=user_id,
            expected_article_id=article_id,
        )
        updated_record = self._fetch_session_record(session_id)
        return self._build_session_detail(updated_record)

    async def chat(self, session_id: str, user_message: str) -> AsyncGenerator[str, None]:
        """エージェントとチャット"""
        session = await self._ensure_session_loaded(session_id)
        self._append_message(session_id, "user", user_message, session.user_id)
        response_accumulator = ""
        async for chunk in session.chat(user_message):
            response_accumulator += chunk
            yield chunk
        self._append_message(session_id, "assistant", response_accumulator, session.user_id)
        self._update_session_record(
            session_id,
            {
                "working_content": session.get_current_content(),
                "last_activity_at": self._now_iso(),
            },
        )

    async def get_current_content(self, session_id: str) -> str:
        """現在のコンテンツを取得"""
        session = await self._ensure_session_loaded(session_id)
        async with session._lock:
            return session.get_current_content()

    async def get_diff(self, session_id: str) -> Dict[str, Any]:
        """差分を取得"""
        session = await self._ensure_session_loaded(session_id)
        async with session._lock:
            result = self.supabase.table("articles").select("content").eq("id", session.article_id).execute()

            if not result.data or len(result.data) == 0:
                raise Exception("Article not found")

            original_content = result.data[0].get("content", "")
            return session.get_diff(original_content)

    async def save_changes(self, session_id: str) -> None:
        """変更を保存"""
        session = await self._ensure_session_loaded(session_id)
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
        session = await self._ensure_session_loaded(session_id)
        async with session._lock:
            result = self.supabase.table("articles").select("content").eq("id", session.article_id).execute()

            if not result.data or len(result.data) == 0:
                raise Exception("Article not found")

            original_content = result.data[0].get("content", "")
            session.article_file.write_text(original_content, encoding="utf-8")
            session.original_file.write_text(original_content, encoding="utf-8")
            session.original_content = original_content
            session.pending_changes = []
            session._change_counter = 0
            self._update_session_record(
                session_id,
                {
                    "working_content": original_content,
                    "last_activity_at": self._now_iso(),
                },
            )

            logger.info("Discarded changes for article %s", session.article_id)

    async def close_session(self, session_id: str) -> None:
        """セッションを閉じる"""
        record = self._fetch_session_record(session_id)
        if not record:
            return

        session = self.sessions.get(session_id)
        if session:
            async with session._lock:
                await session.cleanup(remove_session_store=True)
                self.sessions.pop(session_id, None)
                try:
                    session.temp_dir.rmdir()
                except Exception as e:
                    logger.warning("Failed to remove temp dir: %s", e)
        else:
            temp_dir = self.temp_base / session_id
            if temp_dir.exists():
                for file in temp_dir.glob("*"):
                    try:
                        file.unlink()
                    except Exception:
                        pass
                try:
                    temp_dir.rmdir()
                except Exception:
                    pass
            store_path = self._session_store_path_from_key(record["session_store_key"])
            if store_path.exists():
                try:
                    store_path.unlink()
                except Exception as e:
                    logger.warning("Failed to remove session store file: %s", e)

        self._update_session_record(
            session_id,
            {"status": "closed", "closed_at": self._now_iso(), "last_activity_at": self._now_iso()},
        )
        logger.info("Closed session %s", session_id)

    async def get_conversation_history(self, session_id: str) -> List[Dict[str, Any]]:
        """会話履歴を取得"""
        session = await self._ensure_session_loaded(session_id)
        history = self._load_session_messages(session_id)
        session.conversation_history = [{"role": msg["role"], "content": msg["content"]} for msg in history]
        return session.conversation_history

    async def extract_pending_changes(self, session_id: str) -> List[Dict[str, Any]]:
        """apply_patchによる変更を抽出"""
        session = await self._ensure_session_loaded(session_id)
        async with session._lock:
            return session.extract_pending_changes()

    async def get_pending_changes(self, session_id: str) -> List[Dict[str, Any]]:
        """承認待ちの変更を取得"""
        session = await self._ensure_session_loaded(session_id)
        async with session._lock:
            return session.get_pending_changes()

    async def get_unified_diff_view(self, session_id: str) -> Dict[str, Any]:
        """統合差分ビューを取得（VSCode風）"""
        session = await self._ensure_session_loaded(session_id)
        async with session._lock:
            return session.get_unified_diff_view()

    async def approve_change(self, session_id: str, change_id: str) -> bool:
        """変更を承認"""
        session = await self._ensure_session_loaded(session_id)
        async with session._lock:
            return session.approve_change(change_id)

    async def reject_change(self, session_id: str, change_id: str) -> bool:
        """変更を拒否"""
        session = await self._ensure_session_loaded(session_id)
        async with session._lock:
            return session.reject_change(change_id)

    async def apply_approved_changes(self, session_id: str) -> Dict[str, Any]:
        """承認された変更を適用し、保存・バージョン管理も実行する。"""
        session = await self._ensure_session_loaded(session_id)
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
            else:
                self._update_session_record(
                    session_id,
                    {
                        "working_content": session.get_current_content(),
                        "last_activity_at": self._now_iso(),
                    },
                )

            return apply_result

    async def clear_pending_changes(self, session_id: str) -> None:
        """承認待ち変更をクリア"""
        session = await self._ensure_session_loaded(session_id)
        async with session._lock:
            session.clear_pending_changes()
            self._update_session_record(
                session_id,
                {
                    "working_content": session.original_content,
                    "last_activity_at": self._now_iso(),
                },
            )

    async def get_active_session_detail(self, article_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """アクティブなセッションの詳細を取得（存在しない場合はNone）"""
        record = self._fetch_active_session_record(article_id, user_id)
        if not record:
            return None
        await self._ensure_session_loaded(
            record["id"],
            expected_user_id=user_id,
            expected_article_id=article_id,
        )
        return self._build_session_detail(record)


# Singleton instance
_article_agent_service: Optional[ArticleAgentService] = None


def get_article_agent_service() -> ArticleAgentService:
    """Get or create the article agent service singleton"""
    global _article_agent_service
    if _article_agent_service is None:
        _article_agent_service = ArticleAgentService()
    return _article_agent_service
