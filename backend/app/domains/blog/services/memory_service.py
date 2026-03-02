# -*- coding: utf-8 -*-
"""
Blog Memory Service

Blog専用の長期記憶（Memory）機能を提供する。
- append item
- upsert meta
- semantic search
- embedding batch update
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

from openai import AsyncOpenAI

from app.common.database import supabase
from app.core.config import settings

logger = logging.getLogger(__name__)


ALLOWED_APPEND_ROLES = {
    "user_input",
    "qa",
    "assistant_output",
    "source",
    "system_note",
    "final_summary",
}

ALLOWED_SEARCH_ROLES = {
    "user_input",
    "qa",
    "assistant_output",
    "source",
    "system_note",
    "final_summary",
    "tool_result",
}


@dataclass
class BlogMemoryError(Exception):
    code: str
    message: str
    http_status: int = 400

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"


class BlogMemoryService:
    """Blog Memoryのアプリケーションサービス。"""

    def __init__(self) -> None:
        self._embed_model = settings.memory_embed_model
        self._embed_dim = settings.memory_embed_dim
        self._embed_max_retries = settings.memory_embed_max_retries
        self._embed_retry_base_sec = settings.memory_embed_retry_base_sec
        self._openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
        # 類似度閾値はサーバー側で固定管理する（現時点は無効）
        self._search_score_threshold: Optional[float] = None

    async def append_item(
        self,
        process_id: str,
        role: str,
        content: str,
    ) -> str:
        """blog_memory_append_item RPCを呼び出して追記する。"""
        if role not in ALLOWED_APPEND_ROLES:
            if role == "tool_result":
                raise BlogMemoryError(
                    code="ROLE_TOOL_RESULT_FORBIDDEN",
                    message="tool_result は外部APIから追加できません",
                    http_status=400,
                )
            raise BlogMemoryError(
                code="INVALID_ARGUMENT",
                message=f"role が不正です: {role}",
                http_status=400,
            )

        if not content or not content.strip():
            raise BlogMemoryError(
                code="INVALID_ARGUMENT",
                message="content は必須です",
                http_status=400,
            )

        try:
            result = supabase.rpc(
                "blog_memory_append_item",
                {
                    "p_process_id": process_id,
                    "p_role": role,
                    "p_content": content,
                },
            ).execute()
            memory_item_id = self._extract_scalar_from_rpc_result(
                result.data, "blog_memory_append_item"
            )
            return str(memory_item_id)
        except BlogMemoryError:
            raise
        except Exception as e:
            raise self._map_db_exception(e) from e

    async def append_tool_result(
        self,
        process_id: str,
        content: str,
    ) -> str:
        """検索系ツール結果を tool_result として追記する。"""
        if not content or not content.strip():
            raise BlogMemoryError(
                code="INVALID_ARGUMENT",
                message="content は必須です",
                http_status=400,
            )

        try:
            result = supabase.rpc(
                "blog_memory_append_tool_result",
                {
                    "p_process_id": process_id,
                    "p_content": content,
                },
            ).execute()
            memory_item_id = self._extract_scalar_from_rpc_result(
                result.data, "blog_memory_append_tool_result"
            )
            return str(memory_item_id)
        except BlogMemoryError:
            raise
        except Exception as e:
            raise self._map_db_exception(e) from e

    async def upsert_meta(
        self,
        process_id: str,
        title: str,
        short_summary: str,
        draft_post_id: Optional[int],
    ) -> None:
        """blog_memory_upsert_meta RPCを呼び出して1プロセス1メタを更新する。"""
        if not title or not title.strip():
            raise BlogMemoryError(
                code="INVALID_ARGUMENT",
                message="title は必須です",
                http_status=400,
            )
        if not short_summary or not short_summary.strip():
            raise BlogMemoryError(
                code="INVALID_ARGUMENT",
                message="short_summary は必須です",
                http_status=400,
            )

        embedding_input = self.build_embedding_input(title, short_summary)

        try:
            supabase.rpc(
                "blog_memory_upsert_meta",
                {
                    "p_process_id": process_id,
                    "p_title": title,
                    "p_short_summary": short_summary,
                    "p_embedding_input": embedding_input,
                    "p_draft_post_id": draft_post_id,
                },
            ).execute()
            embedding = await self.embed_text(embedding_input)
            vector_literal = self._to_pgvector_literal(embedding)
            supabase.table("blog_memory_meta").update(
                {
                    "embedding": vector_literal,
                    "embedding_updated_at": datetime.now(timezone.utc).isoformat(),
                }
            ).eq("process_id", process_id).execute()
        except BlogMemoryError:
            raise
        except Exception as e:
            raise self._map_db_exception(e) from e

    async def search(
        self,
        process_id: str,
        query: str,
        k: int = 10,
        include_roles: Optional[List[str]] = None,
        time_window_days: Optional[int] = 365,
        per_process_item_limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """クエリを埋め込み化してメタ検索＋items取得を実施する。"""
        if not query or not query.strip():
            raise BlogMemoryError(
                code="INVALID_ARGUMENT",
                message="query は必須です",
                http_status=400,
            )
        if k < 1 or k > 50:
            raise BlogMemoryError(
                code="INVALID_ARGUMENT",
                message="k は 1..50 の範囲で指定してください",
                http_status=400,
            )
        if per_process_item_limit < 1 or per_process_item_limit > 100:
            raise BlogMemoryError(
                code="INVALID_ARGUMENT",
                message="per_process_item_limit は 1..100 の範囲で指定してください",
                http_status=400,
            )
        if time_window_days is not None and (time_window_days < 1 or time_window_days > 3650):
            raise BlogMemoryError(
                code="INVALID_ARGUMENT",
                message="time_window_days は 1..3650 の範囲で指定してください",
                http_status=400,
            )

        normalized_roles = self._normalize_roles(include_roles)
        query_embedding = await self.embed_text(query)
        vector_literal = self._to_pgvector_literal(query_embedding)

        try:
            search_result = supabase.rpc(
                "blog_memory_search_meta",
                {
                    "p_process_id": process_id,
                    "p_query": vector_literal,
                    "p_k": k,
                },
            ).execute()
        except Exception as e:
            raise self._map_db_exception(e) from e

        score_threshold = self._search_score_threshold
        hits: List[Dict[str, Any]] = []
        for row in (search_result.data or []):
            if score_threshold is not None:
                raw_score = row.get("score")
                try:
                    normalized_score = float(raw_score)
                except (TypeError, ValueError):
                    continue
                if normalized_score > score_threshold:
                    continue

            hit_process_id = row.get("hit_process_id")
            if not hit_process_id:
                continue

            try:
                items_result = supabase.rpc(
                    "blog_memory_get_items",
                    {
                        "p_process_id": hit_process_id,
                        "p_roles": normalized_roles,
                        "p_time_window_days": time_window_days,
                        "p_limit": per_process_item_limit,
                    },
                ).execute()
            except Exception as e:
                raise self._map_db_exception(e) from e

            hits.append(
                {
                    "process_id": hit_process_id,
                    "score": row.get("score"),
                    "meta": {
                        "draft_post_id": row.get("draft_post_id"),
                        "title": row.get("title"),
                        "short_summary": row.get("short_summary"),
                    },
                    "items": items_result.data or [],
                }
            )

        return hits

    async def run_embedding_batch(self, limit: Optional[int] = None) -> int:
        """embedding 未投入/更新遅延のメタへ埋め込みを投入する。"""
        batch_size = limit or settings.memory_embed_batch_size
        if batch_size < 1:
            return 0

        result = supabase.table("blog_memory_meta").select(
            "process_id, embedding_input, embedding, updated_at, embedding_updated_at"
        ).order("updated_at").execute()

        all_rows = result.data or []
        pending_rows = [row for row in all_rows if self._needs_embedding_update(row)][:batch_size]
        if not pending_rows:
            return 0

        texts = [str(row.get("embedding_input") or "") for row in pending_rows]
        embeddings = await self.embed_texts(texts)

        updated = 0
        for row, emb in zip(pending_rows, embeddings):
            process_id = row.get("process_id")
            if not process_id:
                continue
            vector_literal = self._to_pgvector_literal(emb)
            supabase.table("blog_memory_meta").update(
                {
                    "embedding": vector_literal,
                    "embedding_updated_at": datetime.now(timezone.utc).isoformat(),
                }
            ).eq("process_id", process_id).execute()
            updated += 1

        return updated

    def build_embedding_input(self, title: str, short_summary: str) -> str:
        return f"{title.strip()}\n\n{short_summary.strip()}"

    async def embed_text(self, text: str) -> List[float]:
        vectors = await self.embed_texts([text])
        return vectors[0]

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        if not settings.openai_api_key:
            raise BlogMemoryError(
                code="INTERNAL_ERROR",
                message="OPENAI_API_KEY が設定されていません",
                http_status=500,
            )

        sanitized = [self._sanitize_utf16_surrogate(t) for t in texts]
        for attempt in range(self._embed_max_retries):
            try:
                response = await self._openai_client.embeddings.create(
                    model=self._embed_model,
                    input=sanitized,
                )
                vectors = [list(item.embedding) for item in response.data]
                for vec in vectors:
                    if len(vec) != self._embed_dim:
                        raise BlogMemoryError(
                            code="INTERNAL_ERROR",
                            message=(
                                f"embedding 次元が不正です: expected {self._embed_dim}, got {len(vec)}"
                            ),
                            http_status=500,
                        )
                return vectors
            except BlogMemoryError:
                raise
            except Exception as e:
                is_last = attempt == self._embed_max_retries - 1
                if is_last:
                    raise BlogMemoryError(
                        code="INTERNAL_ERROR",
                        message=f"embedding 生成に失敗しました: {e}",
                        http_status=500,
                    ) from e
                sleep_sec = self._embed_retry_base_sec * (2 ** attempt)
                logger.warning(
                    "Embedding generation failed (attempt=%s/%s): %s",
                    attempt + 1,
                    self._embed_max_retries,
                    e,
                )
                await asyncio.sleep(sleep_sec)

        raise BlogMemoryError(
            code="INTERNAL_ERROR",
            message="embedding 生成に失敗しました",
            http_status=500,
        )

    @staticmethod
    def _sanitize_utf16_surrogate(value: str) -> str:
        # httpx/json encode時に失敗する lone surrogate を除去する
        return "".join(ch for ch in value if not (0xD800 <= ord(ch) <= 0xDFFF))

    @staticmethod
    def _parse_iso_datetime(value: Any) -> Optional[datetime]:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        if not isinstance(value, str):
            return None
        text = value.strip()
        if not text:
            return None
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            return datetime.fromisoformat(text)
        except ValueError:
            return None

    def _needs_embedding_update(self, row: Dict[str, Any]) -> bool:
        if row.get("embedding") is None:
            return True

        updated_at = self._parse_iso_datetime(row.get("updated_at"))
        embedding_updated_at = self._parse_iso_datetime(row.get("embedding_updated_at"))

        if embedding_updated_at is None:
            return True
        if updated_at is None:
            return False

        return embedding_updated_at < updated_at

    @staticmethod
    def _to_pgvector_literal(vector: Iterable[float]) -> str:
        return "[" + ",".join(f"{v:.8f}" for v in vector) + "]"

    @staticmethod
    def _extract_scalar_from_rpc_result(data: Any, fn_name: str) -> Any:
        if data is None:
            raise BlogMemoryError(
                code="INTERNAL_ERROR",
                message=f"{fn_name} の戻り値が空です",
                http_status=500,
            )

        # 例1: [{"blog_memory_append_item": "<uuid>"}]
        if isinstance(data, list) and data:
            first = data[0]
            if isinstance(first, dict):
                if fn_name in first:
                    return first[fn_name]
                if len(first) == 1:
                    return list(first.values())[0]
            return first

        # 例2: "<uuid>"
        if isinstance(data, (str, int, float)):
            return data

        if isinstance(data, dict):
            if fn_name in data:
                return data[fn_name]
            if len(data) == 1:
                return list(data.values())[0]

        raise BlogMemoryError(
            code="INTERNAL_ERROR",
            message=f"{fn_name} の戻り値形式が不明です",
            http_status=500,
        )

    @staticmethod
    def _normalize_roles(include_roles: Optional[List[str]]) -> Optional[List[str]]:
        if include_roles is None:
            return None

        normalized: List[str] = []
        for role in include_roles:
            if role not in ALLOWED_SEARCH_ROLES:
                raise BlogMemoryError(
                    code="INVALID_ARGUMENT",
                    message=f"include_roles に不正な role が含まれています: {role}",
                    http_status=400,
                )
            normalized.append(role)
        return normalized

    @staticmethod
    def _map_db_exception(exc: Exception) -> BlogMemoryError:
        message = str(exc)
        upper = message.upper()

        if "INVALID INPUT SYNTAX FOR TYPE UUID" in upper:
            return BlogMemoryError(
                code="INVALID_ARGUMENT",
                message="process_id の形式が不正です",
                http_status=400,
            )
        if "BLOG_PROCESS_NOT_FOUND" in upper:
            return BlogMemoryError(
                code="BLOG_PROCESS_NOT_FOUND",
                message="指定された process_id が存在しません",
                http_status=404,
            )
        if "ROLE_TOOL_RESULT_FORBIDDEN" in upper:
            return BlogMemoryError(
                code="ROLE_TOOL_RESULT_FORBIDDEN",
                message="tool_result は外部APIから追加できません",
                http_status=400,
            )

        return BlogMemoryError(
            code="INTERNAL_ERROR",
            message=f"DB処理に失敗しました: {message}",
            http_status=500,
        )


_blog_memory_service: Optional[BlogMemoryService] = None


def get_blog_memory_service() -> BlogMemoryService:
    global _blog_memory_service
    if _blog_memory_service is None:
        _blog_memory_service = BlogMemoryService()
    return _blog_memory_service
