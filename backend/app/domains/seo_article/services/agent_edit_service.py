# -*- coding: utf-8 -*-
"""
AI Agent Article Edit Service

OpenAI Agents SDKを使用した記事編集サービス
Codex風のapply_patchツールを実装し、インタラクティブな記事編集を実現します。
"""

import asyncio
import dataclasses
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple
from uuid import uuid4

from agents import Agent, ModelSettings, Runner, RunConfig
from agents import function_tool
from agents.run_context import RunContextWrapper
from pydantic import BaseModel

from app.domains.seo_article.services.codex_patch import (
    ApplyPatch,
    HunkApplyError,
    PatchError,
    apply_hunk,
    parse_apply_patch,
)
from app.domains.seo_article.services.flow_service import get_supabase_client

logger = logging.getLogger(__name__)


# ============================================================================
# Data Structures
# ============================================================================

@dataclass
class EditContext:
    """編集コンテキスト"""
    article_id: str
    user_id: str
    session_id: str
    current_content: List[str] = field(default_factory=list)
    original_content: List[str] = field(default_factory=list)


class AgentMessage(BaseModel):
    """エージェントメッセージ"""
    role: str  # "user" | "assistant" | "system" | "tool"
    content: str
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None
    name: Optional[str] = None




# ============================================================================
# Agent Tools
# ============================================================================

@function_tool
def read_article(context: RunContextWrapper[EditContext],
                offset: int = 1,
                limit_lines: int = 400,
                with_line_numbers: bool = True) -> str:
    """
    記事の内容を読み取ります。

    Args:
        offset: 開始行（1-based）
        limit_lines: 取得行数
        with_line_numbers: 行番号を付与するか

    Returns:
        記事の内容（指定範囲）
    """
    ctx = context.context
    lines = ctx.current_content

    if not lines:
        return f"# Article ID: {ctx.article_id} (empty or not loaded)\n"

    start = max(1, int(offset))
    end = min(len(lines), start - 1 + max(1, int(limit_lines)))
    view = lines[start - 1:end]

    if with_line_numbers:
        view = [f"{i + start:>6}: {ln}" for i, ln in enumerate(view)]

    header = f"# Article ID: {ctx.article_id}\n# Showing lines {start}..{end} of {len(lines)}\n"
    return header + "\n".join(view)


@function_tool
def apply_patch_tool(context: RunContextWrapper[EditContext], patch: str) -> str:
    """
    Codex互換のapply_patchを適用します。

    Args:
        patch: パッチ文字列（*** Begin Patch ~ *** End Patch）

    Returns:
        適用結果のJSON
    """
    ctx = context.context
    ap = parse_apply_patch(patch)

    result = {"added": [], "updated": [], "deleted": []}

    for sec in ap.sections:
        if sec.action == "Add":
            ctx.current_content = sec.add_content
            result["added"].append(sec.src_path)

        elif sec.action == "Update":
            acc = ctx.current_content[:]
            for h in sec.hunks:
                try:
                    acc, a, d = apply_hunk(acc, h, file_path=sec.src_path)
                except HunkApplyError as err:
                    context = "\n".join(err.context_lines[:6])
                    message = f"apply_patch verification failed: Failed to find expected lines in {err.file_path or sec.src_path}"
                    if context:
                        message += ":\n" + context
                    raise PatchError(message) from err
            ctx.current_content = acc
            result["updated"].append(sec.src_path)

        elif sec.action == "Delete":
            ctx.current_content = []
            result["deleted"].append(sec.src_path)

    return "APPLIED " + json.dumps(result, ensure_ascii=False)


# ============================================================================
# Agent Service
# ============================================================================

CODEX_STYLE_INSTRUCTIONS = """
あなたはHTML記事を編集するコーディングエージェントです。
必ず以下に従ってください。

# 目的
- ユーザーの依頼に基づき、記事の必要箇所のみを編集します。
- 編集は必ず apply_patch_tool を使い、差分パッチで行います。

# 使えるツール
- read_article(offset, limit_lines, with_line_numbers): 記事の一部を読みます。
- apply_patch_tool(patch): Codex互換のapply_patchを適用します。

# パッチ仕様（厳守）
- 全体を `*** Begin Patch` と `*** End Patch` で囲む。
- ファイルごとに1セクション：
  - 追加:    `*** Add File: <path>` の後に内容。
  - 更新:    `*** Update File: <path>`。
             1個以上のハンクを `@@ -<旧行番号>,<旧行数> +<新行番号>,<新行数> @@` 形式で開始し、変更行を続ける
               * 例：`@@ -12,5 +12,7 @@`
               * 先頭` `（空白）= 文脈、`-`=削除、`+`=追加
               * `@@` のみのヘッダーは無効（必ず行番号と行数を指定する）
  - 削除:    `*** Delete File: <path>`
- 曖昧さ回避のため、十分な文脈行を付与すること。

# ワークフロー
1) まず read_article で必要範囲を確認し、編集位置と方針を決める。
2) apply_patch_tool で差分を適用する。
3) 必要なら短く変更点と確認方法を説明する。

# 出力
- 冗長な説明は避け、要点のみ伝える。
- 新規テキストをそのまま出力せず、必ず apply_patch_tool を生成する。
"""


class AgentEditService:
    """AI Agent Edit Service"""

    def __init__(self):
        self.supabase = get_supabase_client()
        self.sessions: Dict[str, EditContext] = {}

    def _create_agent(self, model: str = "gpt-4o") -> Agent[EditContext]:
        """エージェントを作成"""
        settings = ModelSettings(
            tool_choice="auto",
            temperature=0.3,
        )

        return Agent[EditContext](
            name="Article Edit Agent",
            instructions=CODEX_STYLE_INSTRUCTIONS,
            model=model,
            model_settings=settings,
            tools=[read_article, apply_patch_tool],
        )

    async def load_article_content(self, article_id: str, user_id: str) -> List[str]:
        """記事をDBから読み込む"""
        try:
            result = self.supabase.table("articles").select("*").eq("id", article_id).eq("user_id", user_id).execute()

            if not result.data or len(result.data) == 0:
                raise Exception(f"Article {article_id} not found")

            article = result.data[0]
            content_html = article.get("content", "")

            # HTMLを行に分割
            lines = content_html.splitlines()
            return lines

        except Exception as e:
            logger.error(f"Error loading article: {str(e)}")
            raise

    async def save_article_content(self, article_id: str, user_id: str, content_lines: List[str]) -> None:
        """記事をDBに保存"""
        try:
            content_html = "\n".join(content_lines)

            result = self.supabase.table("articles").update({
                "content": content_html
            }).eq("id", article_id).eq("user_id", user_id).execute()

            if not result.data:
                raise Exception("Failed to save article")

            logger.info(f"Saved article {article_id}")

        except Exception as e:
            logger.error(f"Error saving article: {str(e)}")
            raise

    async def create_session(self, article_id: str, user_id: str) -> str:
        """編集セッションを作成"""
        session_id = str(uuid4())

        # 記事を読み込む
        content_lines = await self.load_article_content(article_id, user_id)

        # セッションを作成
        ctx = EditContext(
            article_id=article_id,
            user_id=user_id,
            session_id=session_id,
            current_content=content_lines[:],
            original_content=content_lines[:],
        )

        self.sessions[session_id] = ctx
        logger.info(f"Created edit session {session_id} for article {article_id}")

        return session_id

    async def chat(self, session_id: str, user_message: str, model: str = "gpt-4o"):
        """エージェントとチャット（ストリーミング）"""
        if session_id not in self.sessions:
            raise Exception(f"Session {session_id} not found")

        ctx = self.sessions[session_id]
        agent = self._create_agent(model)

        try:
            # Run agent
            result = await Runner.run(
                agent,
                input=user_message,
                context=ctx,
                run_config=RunConfig(
                    workflow_name="article-edit",
                    tracing_disabled=True,
                ),
            )

            # Stream response
            if result.final_output:
                output_text = result.final_output if isinstance(result.final_output, str) else str(result.final_output)
                yield output_text

        except Exception as e:
            logger.error(f"Error in chat: {str(e)}")
            yield f"エラーが発生しました: {str(e)}"

    async def get_current_content(self, session_id: str) -> str:
        """現在のコンテンツを取得"""
        if session_id not in self.sessions:
            raise Exception(f"Session {session_id} not found")

        ctx = self.sessions[session_id]
        return "\n".join(ctx.current_content)

    async def get_diff(self, session_id: str) -> Dict[str, Any]:
        """変更差分を取得"""
        if session_id not in self.sessions:
            raise Exception(f"Session {session_id} not found")

        ctx = self.sessions[session_id]

        return {
            "original": "\n".join(ctx.original_content),
            "current": "\n".join(ctx.current_content),
            "has_changes": ctx.current_content != ctx.original_content,
        }

    async def save_changes(self, session_id: str) -> None:
        """変更を保存"""
        if session_id not in self.sessions:
            raise Exception(f"Session {session_id} not found")

        ctx = self.sessions[session_id]
        await self.save_article_content(ctx.article_id, ctx.user_id, ctx.current_content)

        # 元のコンテンツを更新
        ctx.original_content = ctx.current_content[:]

    async def discard_changes(self, session_id: str) -> None:
        """変更を破棄"""
        if session_id not in self.sessions:
            raise Exception(f"Session {session_id} not found")

        ctx = self.sessions[session_id]
        ctx.current_content = ctx.original_content[:]

    async def close_session(self, session_id: str) -> None:
        """セッションを閉じる"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"Closed session {session_id}")


# Singleton instance
_agent_edit_service: Optional[AgentEditService] = None


def get_agent_edit_service() -> AgentEditService:
    """Get or create the agent edit service singleton"""
    global _agent_edit_service
    if _agent_edit_service is None:
        _agent_edit_service = AgentEditService()
    return _agent_edit_service
