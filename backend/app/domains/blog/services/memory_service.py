# -*- coding: utf-8 -*-
"""
Blog Memory Service

Blog専用の長期記憶（Memory）機能を提供する。
- meta upsert
- detail(memory_json) merge
- semantic search
- embedding batch update
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

from openai import AsyncOpenAI

from app.common.database import supabase
from app.core.config import settings

logger = logging.getLogger(__name__)

ALLOWED_NEEDS = {
    "overview",
    "request",
    "qa",
    "tools",
    "trace",
    "references",
}


def _result_data(result: Any) -> Any:
    """Supabase maybe_single() が None を返すケースを吸収する。"""
    return getattr(result, "data", None) if result is not None else None

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
        self._search_score_threshold: Optional[float] = None

    async def record_user_input(self, process_id: str, user_input: str) -> None:
        if not user_input or not user_input.strip():
            return
        await self.upsert_detail_patch(
            process_id=process_id,
            patch={"user_input": user_input.strip()},
        )

    async def append_qa(
        self,
        process_id: str,
        questions: Optional[List[Dict[str, Any]]],
        answers: Dict[str, Any],
    ) -> None:
        qa_entries = self._build_qa_entries(questions or [], answers)
        if not qa_entries:
            return
        await self.upsert_detail_patch(
            process_id=process_id,
            patch={"qa": qa_entries},
        )

    async def record_summary(self, process_id: str, summary: str) -> None:
        if not summary or not summary.strip():
            return
        await self.upsert_detail_patch(
            process_id=process_id,
            patch={"summary": summary.strip()},
        )

    async def record_note(self, process_id: str, note: str) -> None:
        if not note or not note.strip():
            return
        await self.upsert_detail_patch(
            process_id=process_id,
            patch={"note": note.strip()},
        )

    async def append_tool_result(
        self,
        process_id: str,
        tool_name: str,
        input_data: Optional[Dict[str, Any]],
        output: Any,
    ) -> None:
        if not tool_name:
            return
        references = self._normalize_references(
            self._extract_references(input_data) + self._extract_references(output)
        )
        tool_entry = {
            "tool_name": tool_name,
            "input": input_data or {},
            "output_preview": self._build_output_preview(output),
            "references": references,
            "captured_at": datetime.now(timezone.utc).isoformat(),
        }
        await self.upsert_detail_patch(
            process_id=process_id,
            patch={
                "tool_results": [tool_entry],
                "references": references,
            },
        )

    async def set_execution_trace(
        self,
        process_id: str,
        tool_sequence: List[str],
    ) -> None:
        if not tool_sequence:
            return
        unique_tools = list(dict.fromkeys(tool_sequence))
        flow = [tool_name for tool_name in tool_sequence if tool_name]
        await self.upsert_detail_patch(
            process_id=process_id,
            patch={
                "execution_trace": {
                    "tools": unique_tools,
                    "flow": flow,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            },
        )

    async def upsert_meta(
        self,
        process_id: str,
        title: str,
        summary: str,
        draft_post_id: Optional[int],
        post_type: Optional[str] = None,
        category_ids: Optional[List[int]] = None,
    ) -> None:
        """blog_memory_meta を upsert する。"""
        if not title or not title.strip():
            raise BlogMemoryError(
                code="INVALID_ARGUMENT",
                message="title は必須です",
                http_status=400,
            )
        if not summary or not summary.strip():
            raise BlogMemoryError(
                code="INVALID_ARGUMENT",
                message="summary は必須です",
                http_status=400,
            )

        scope = await self._get_process_scope(process_id)
        normalized_categories = self.normalize_category_ids(category_ids)
        embedding_input = self.build_embedding_input(title, summary)

        try:
            supabase.table("blog_memory_meta").upsert(
                {
                    "process_id": process_id,
                    "user_id": scope["user_id"],
                    "organization_id": scope["organization_id"],
                    "scope_type": scope["scope_type"],
                    "draft_post_id": draft_post_id,
                    "title": title.strip(),
                    "summary": summary.strip(),
                    "post_type": (post_type or None),
                    "category_ids": normalized_categories,
                    "embedding_input": embedding_input,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                },
                on_conflict="process_id",
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

    async def upsert_detail_patch(
        self,
        process_id: str,
        patch: Dict[str, Any],
    ) -> None:
        scope = await self._get_process_scope(process_id)
        current_memory = await self.get_detail_memory(process_id)
        merged = self._merge_memory_json(current_memory, patch)

        try:
            supabase.table("blog_memory_detail").upsert(
                {
                    "process_id": process_id,
                    "user_id": scope["user_id"],
                    "organization_id": scope["organization_id"],
                    "scope_type": scope["scope_type"],
                    "memory_json": merged,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                },
                on_conflict="process_id",
            ).execute()
        except Exception as e:
            raise self._map_db_exception(e) from e

    async def get_detail_memory(self, process_id: str) -> Dict[str, Any]:
        try:
            result = supabase.table("blog_memory_detail").select(
                "memory_json"
            ).eq("process_id", process_id).maybe_single().execute()
        except Exception as e:
            raise self._map_db_exception(e) from e

        data = _result_data(result) or {}
        memory_json = data.get("memory_json") if isinstance(data, dict) else {}
        return self._normalize_memory_json(memory_json)

    async def search(
        self,
        process_id: str,
        query: str,
        k: int = 10,
        need: Optional[List[str]] = None,
        time_window_days: Optional[int] = 365,
        post_type: Optional[str] = None,
        category_ids: Optional[List[int]] = None,
    ) -> List[Dict[str, Any]]:
        """クエリを埋め込み化してメタ検索＋必要な detail 取得を実施する。"""
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
        if time_window_days is not None and (time_window_days < 1 or time_window_days > 3650):
            raise BlogMemoryError(
                code="INVALID_ARGUMENT",
                message="time_window_days は 1..3650 の範囲で指定してください",
                http_status=400,
            )

        normalized_need = self._normalize_need(need)
        normalized_categories = self.normalize_category_ids(category_ids)
        query_embedding = await self.embed_text(query)
        vector_literal = self._to_pgvector_literal(query_embedding)

        try:
            search_result = supabase.rpc(
                "blog_memory_search_meta",
                {
                    "p_process_id": process_id,
                    "p_query": vector_literal,
                    "p_k": k,
                    "p_post_type": (post_type or None),
                    "p_category_ids": normalized_categories,
                    "p_time_window_days": time_window_days,
                },
            ).execute()
        except Exception as e:
            raise self._map_db_exception(e) from e

        rows = search_result.data or []
        hit_ids = [str(row.get("hit_process_id")) for row in rows if row.get("hit_process_id")]
        details_by_process_id = await self._fetch_details_by_process_ids(hit_ids)

        hits: List[Dict[str, Any]] = []
        score_threshold = self._search_score_threshold
        for row in rows:
            raw_score = row.get("score")
            if score_threshold is not None:
                try:
                    normalized_score = float(raw_score)
                except (TypeError, ValueError):
                    continue
                if normalized_score > score_threshold:
                    continue

            hit_process_id = row.get("hit_process_id")
            if not hit_process_id:
                continue

            detail = details_by_process_id.get(str(hit_process_id), self._normalize_memory_json(None))
            hits.append(self._build_hit(row=row, detail=detail, need=normalized_need))

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

    def build_embedding_input(self, title: str, summary: str) -> str:
        return f"{title.strip()}\n\n{summary.strip()}"

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

    async def _get_process_scope(self, process_id: str) -> Dict[str, Any]:
        try:
            result = supabase.table("blog_generation_state").select(
                "user_id, organization_id"
            ).eq("id", process_id).maybe_single().execute()
        except Exception as e:
            raise self._map_db_exception(e) from e

        row = _result_data(result) or {}
        user_id = row.get("user_id")
        if not user_id:
            raise BlogMemoryError(
                code="BLOG_PROCESS_NOT_FOUND",
                message="指定された process_id が存在しません",
                http_status=404,
            )
        organization_id = row.get("organization_id")
        return {
            "user_id": user_id,
            "organization_id": organization_id,
            "scope_type": "org" if organization_id else "user",
        }

    async def _fetch_details_by_process_ids(self, process_ids: List[str]) -> Dict[str, Dict[str, Any]]:
        if not process_ids:
            return {}
        try:
            result = supabase.table("blog_memory_detail").select(
                "process_id, memory_json"
            ).in_("process_id", process_ids).execute()
        except Exception as e:
            raise self._map_db_exception(e) from e

        details: Dict[str, Dict[str, Any]] = {}
        for row in result.data or []:
            process_id = row.get("process_id")
            if not process_id:
                continue
            details[str(process_id)] = self._normalize_memory_json(row.get("memory_json"))
        return details

    def _build_hit(
        self,
        row: Dict[str, Any],
        detail: Dict[str, Any],
        need: List[str],
    ) -> Dict[str, Any]:
        hit: Dict[str, Any] = {
            "process_id": row.get("hit_process_id"),
            "score": row.get("score"),
        }

        if "overview" in need:
            hit["overview"] = {
                "title": row.get("title"),
                "summary": row.get("summary"),
                "note": detail.get("note"),
            }
        if "request" in need:
            hit["request"] = detail.get("user_input")
        if "qa" in need:
            hit["qa"] = self._normalize_qa_entries(detail.get("qa"))
        if "tools" in need:
            hit["tools"] = self._normalize_tool_results(detail.get("tool_results"))
        if "trace" in need:
            hit["trace"] = self._normalize_execution_trace(detail.get("execution_trace"))
        if "references" in need:
            hit["references"] = self._normalize_references(detail.get("references"))
        return hit

    @staticmethod
    def _normalize_qa_entries(raw: Any) -> List[Dict[str, Any]]:
        if not isinstance(raw, list):
            return []

        normalized: List[Dict[str, Any]] = []
        for entry in raw:
            if not isinstance(entry, dict):
                continue

            question = entry.get("question")
            answer = entry.get("answer")
            payload = entry.get("payload") if isinstance(entry.get("payload"), dict) else {}
            if question is None and answer is None:
                continue

            normalized.append(
                {
                    "question": str(question).strip() if question is not None else None,
                    "answer": str(answer).strip() if answer is not None else None,
                    "payload": payload,
                }
            )
        return normalized

    @staticmethod
    def _normalize_tool_results(raw: Any) -> List[Dict[str, Any]]:
        if not isinstance(raw, list):
            return []
        normalized: List[Dict[str, Any]] = []
        for entry in raw:
            if not isinstance(entry, dict):
                continue
            tool_name = str(entry.get("tool_name") or "").strip()
            if not tool_name:
                continue
            input_data = entry.get("input") if isinstance(entry.get("input"), dict) else {}
            output_preview = entry.get("output_preview")
            if output_preview is not None:
                output_preview = str(output_preview).strip() or None
            captured_at = entry.get("captured_at")
            if captured_at is not None:
                captured_at = str(captured_at).strip() or None
            normalized.append(
                {
                    "tool_name": tool_name,
                    "input": input_data,
                    "output_preview": output_preview,
                    "references": BlogMemoryService._normalize_references(entry.get("references")),
                    "captured_at": captured_at,
                }
            )
        return normalized

    @staticmethod
    def _normalize_execution_trace(raw: Any) -> Optional[Dict[str, Any]]:
        if not isinstance(raw, dict):
            return None
        tools = [str(value).strip() for value in raw.get("tools") or [] if str(value).strip()]
        flow = [str(value).strip() for value in raw.get("flow") or [] if str(value).strip()]
        updated_at = raw.get("updated_at")
        normalized: Dict[str, Any] = {
            "tools": tools,
            "flow": flow,
        }
        if isinstance(updated_at, str) and updated_at.strip():
            normalized["updated_at"] = updated_at.strip()
        return normalized

    @staticmethod
    def _normalize_references(raw: Any) -> List[Dict[str, Any]]:
        if not isinstance(raw, list):
            return []
        normalized: List[Dict[str, Any]] = []
        seen: set[tuple[Any, ...]] = set()
        for entry in raw:
            if not isinstance(entry, dict):
                continue
            normalized_entry = {
                "type": str(entry.get("type")).strip() if entry.get("type") is not None else None,
                "id": str(entry.get("id")).strip() if entry.get("id") is not None else None,
                "post_id": BlogMemoryService._coerce_int(entry.get("post_id")),
                "url": str(entry.get("url")).strip() if entry.get("url") is not None else None,
                "title": str(entry.get("title")).strip() if entry.get("title") is not None else None,
            }
            if not any(normalized_entry.values()):
                continue
            dedupe_key = (
                normalized_entry["type"],
                normalized_entry["id"],
                normalized_entry["post_id"],
                normalized_entry["url"],
                normalized_entry["title"],
            )
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            normalized.append(normalized_entry)
        return normalized

    @staticmethod
    def _normalize_need(need: Optional[List[str]]) -> List[str]:
        if not need:
            return ["overview"]

        normalized: List[str] = []
        for value in need:
            if value not in ALLOWED_NEEDS:
                raise BlogMemoryError(
                    code="INVALID_ARGUMENT",
                    message=f"need に不正な値が含まれています: {value}",
                    http_status=400,
                )
            if value not in normalized:
                normalized.append(value)
        return normalized or ["overview"]

    @staticmethod
    def normalize_category_ids(category_ids: Optional[List[int]]) -> List[int]:
        if not category_ids:
            return []
        return sorted({int(category_id) for category_id in category_ids})

    @staticmethod
    def _normalize_memory_json(memory_json: Any) -> Dict[str, Any]:
        normalized = BlogMemoryService._empty_memory_json()
        if not isinstance(memory_json, dict):
            return normalized

        user_input = memory_json.get("user_input")
        normalized["user_input"] = str(user_input).strip() if isinstance(user_input, str) and user_input.strip() else None

        summary = memory_json.get("summary")
        normalized["summary"] = str(summary).strip() if isinstance(summary, str) and summary.strip() else None

        note = memory_json.get("note")
        normalized["note"] = (
            str(note).strip()
            if isinstance(note, str) and note.strip()
            else None
        )

        for key in ("qa", "tool_results", "references"):
            value = memory_json.get(key)
            if key == "tool_results":
                normalized[key] = BlogMemoryService._normalize_tool_results(value)
            elif key == "references":
                normalized[key] = BlogMemoryService._normalize_references(value)
            else:
                normalized[key] = value if isinstance(value, list) else []

        execution_trace = memory_json.get("execution_trace")
        normalized["execution_trace"] = BlogMemoryService._normalize_execution_trace(execution_trace) or {}
        return normalized

    @staticmethod
    def _empty_memory_json() -> Dict[str, Any]:
        return {
            "user_input": None,
            "qa": [],
            "summary": None,
            "note": None,
            "tool_results": [],
            "execution_trace": {},
            "references": [],
        }

    def _merge_memory_json(self, current: Dict[str, Any], patch: Dict[str, Any]) -> Dict[str, Any]:
        merged = self._normalize_memory_json(current)

        for scalar_key in ("user_input", "summary", "note"):
            value = patch.get(scalar_key)
            if isinstance(value, str) and value.strip():
                merged[scalar_key] = value.strip()

        for list_key in ("qa", "tool_results", "references"):
            value = patch.get(list_key)
            if isinstance(value, list) and value:
                current_list = merged.get(list_key)
                if not isinstance(current_list, list):
                    current_list = []
                if list_key == "references":
                    current_list.extend(value)
                    merged[list_key] = self._normalize_references(current_list)
                else:
                    current_list.extend(value)
                    merged[list_key] = current_list

        execution_trace = patch.get("execution_trace")
        if isinstance(execution_trace, dict) and execution_trace:
            normalized_trace = self._normalize_execution_trace(execution_trace)
            if normalized_trace:
                merged["execution_trace"] = normalized_trace

        return merged

    @classmethod
    def _build_output_preview(cls, output: Any, limit: int = 2000) -> Optional[str]:
        jsonable = cls._to_jsonable(output)
        if jsonable is None:
            return None
        if isinstance(jsonable, str):
            text = jsonable
        else:
            try:
                text = json.dumps(jsonable, ensure_ascii=False, separators=(",", ":"))
            except TypeError:
                text = str(jsonable)
        text = text.strip()
        if not text:
            return None
        if len(text) <= limit:
            return text
        return text[:limit] + "...(truncated)"

    @classmethod
    def _extract_references(cls, value: Any) -> List[Dict[str, Any]]:
        references: List[Dict[str, Any]] = []
        cls._collect_references(value, references)
        return cls._normalize_references(references)

    @classmethod
    def _collect_references(cls, value: Any, collector: List[Dict[str, Any]]) -> None:
        if isinstance(value, dict):
            reference = cls._build_reference_entry(value)
            if reference:
                collector.append(reference)
            for nested in value.values():
                cls._collect_references(nested, collector)
            return
        if isinstance(value, list):
            for nested in value:
                cls._collect_references(nested, collector)

    @staticmethod
    def _build_reference_entry(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        raw_id = data.get("id")
        raw_post_id = data.get("post_id")
        post_id = BlogMemoryService._coerce_int(raw_post_id)
        if post_id is None and BlogMemoryService._coerce_int(raw_id) is not None:
            post_id = BlogMemoryService._coerce_int(raw_id)
        entry = {
            "type": "wp_post" if post_id is not None else None,
            "id": str(data.get("id")).strip() if data.get("id") is not None else None,
            "post_id": post_id,
            "url": BlogMemoryService._coerce_url(
                data.get("url")
                or data.get("link")
                or data.get("preview_url")
                or data.get("edit_url")
            ),
            "title": BlogMemoryService._coerce_title(
                data.get("title")
                or data.get("name")
                or data.get("post_title")
            ),
        }
        if not any(entry.values()):
            return None
        if entry["post_id"] is None and entry["url"] is None:
            return None
        return entry

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
    def _coerce_int(value: Any) -> Optional[int]:
        if value is None or value == "":
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _coerce_url(value: Any) -> Optional[str]:
        if not isinstance(value, str):
            return None
        text = value.strip()
        if not text:
            return None
        if text.startswith(("http://", "https://")):
            return text
        return None

    @staticmethod
    def _coerce_title(value: Any) -> Optional[str]:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @staticmethod
    def _build_qa_entries(
        questions: List[Dict[str, Any]],
        answers: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        entries: List[Dict[str, Any]] = []
        indexed_questions = {
            str(question.get("question_id") or ""): question
            for question in questions
            if isinstance(question, dict)
        }

        for question_id, raw_answer in answers.items():
            answer_text = str(raw_answer or "").strip()
            if not answer_text:
                continue
            question = indexed_questions.get(str(question_id), {})
            question_text = str(question.get("question") or question.get("label") or "").strip()
            entry: Dict[str, Any] = {
                "question_id": str(question_id),
                "answer": answer_text,
            }
            if question_text:
                entry["question"] = question_text
            input_type = question.get("input_type")
            if input_type:
                entry["payload"] = {"input_type": input_type}
            entries.append(entry)
        return entries

    @staticmethod
    def _sanitize_utf16_surrogate(value: str) -> str:
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
