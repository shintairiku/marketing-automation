# -*- coding: utf-8 -*-
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Optional

import pytest
from fastapi import BackgroundTasks

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.domains.blog import endpoints as blog_endpoints
from app.domains.blog.schemas import BlogCompletionOutput
from app.domains.blog.services.generation_service import BlogGenerationService
from app.domains.blog.services.memory_service import BlogMemoryService
from app.domains.usage.service import UsageLimitService
import app.domains.blog.services.memory_service as memory_service_module


class _FakeResult:
    def __init__(self, data: Any):
        self.data = data


class _EndpointTable:
    def __init__(self, db: "_EndpointSupabase", name: str):
        self.db = db
        self.name = name
        self.filters: Dict[str, Any] = {}
        self._insert_payload: Optional[Dict[str, Any]] = None

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, key: str, value: Any):
        self.filters[key] = value
        return self

    def maybe_single(self):
        return self

    def single(self):
        return self

    def insert(self, payload: Dict[str, Any]):
        self._insert_payload = payload
        return self

    def execute(self):
        return self.db.execute(self.name, self.filters, self._insert_payload)


class _EndpointSupabase:
    def __init__(self, site_row: Optional[Dict[str, Any]] = None, process_row: Optional[Dict[str, Any]] = None):
        self.site_row = site_row
        self.process_row = process_row
        self.inserted_process: Optional[Dict[str, Any]] = None

    def table(self, name: str):
        return _EndpointTable(self, name)

    def execute(self, name: str, filters: Dict[str, Any], insert_payload: Optional[Dict[str, Any]]):
        if name == "wordpress_sites":
            if self.site_row and filters.get("id") == self.site_row["id"] and filters.get("user_id") == self.site_row["user_id"]:
                return _FakeResult([self.site_row])
            return _FakeResult([])

        if name == "blog_generation_state":
            if insert_payload is not None:
                self.inserted_process = insert_payload
                return _FakeResult([insert_payload])
            if self.process_row and filters.get("id") == self.process_row["id"]:
                return _FakeResult(self.process_row)
            return _FakeResult(None)

        return _FakeResult([])


class _MemoryTable:
    def __init__(self, db: "_MemorySupabase", name: str):
        self.db = db
        self.name = name
        self.filters: Dict[str, Any] = {}
        self.in_filters: Dict[str, List[Any]] = {}
        self._upsert_payload: Optional[Dict[str, Any]] = None
        self._update_payload: Optional[Dict[str, Any]] = None
        self._select_columns: Optional[str] = None

    def select(self, columns: str, *_args, **_kwargs):
        self._select_columns = columns
        return self

    def eq(self, key: str, value: Any):
        self.filters[key] = value
        return self

    def in_(self, key: str, values: List[Any]):
        self.in_filters[key] = values
        return self

    def maybe_single(self):
        return self

    def order(self, *_args, **_kwargs):
        return self

    def upsert(self, payload: Dict[str, Any], **_kwargs):
        self._upsert_payload = payload
        return self

    def update(self, payload: Dict[str, Any]):
        self._update_payload = payload
        return self

    def execute(self):
        return self.db.execute_table(self)


class _MemoryRpc:
    def __init__(self, db: "_MemorySupabase", fn: str, params: Dict[str, Any]):
        self.db = db
        self.fn = fn
        self.params = params

    def execute(self):
        self.db.rpc_calls.append((self.fn, self.params))
        return _FakeResult(self.db.rpc_responses.get(self.fn, []))


class _MemorySupabase:
    def __init__(self):
        self.process_rows: Dict[str, Dict[str, Any]] = {}
        self.meta_rows: Dict[str, Dict[str, Any]] = {}
        self.detail_rows: Dict[str, Dict[str, Any]] = {}
        self.rpc_responses: Dict[str, Any] = {}
        self.rpc_calls: List[Any] = []

    def table(self, name: str):
        return _MemoryTable(self, name)

    def rpc(self, fn: str, params: Dict[str, Any]):
        return _MemoryRpc(self, fn, params)

    def execute_table(self, table: _MemoryTable):
        if table.name == "blog_generation_state":
            process_id = table.filters.get("id")
            return _FakeResult(self.process_rows.get(str(process_id)))

        if table.name == "blog_memory_meta":
            if table._upsert_payload is not None:
                payload = dict(table._upsert_payload)
                process_id = str(payload["process_id"])
                existing = self.meta_rows.get(process_id, {})
                merged = {**existing, **payload}
                self.meta_rows[process_id] = merged
                return _FakeResult([merged])
            if table._update_payload is not None:
                process_id = str(table.filters.get("process_id"))
                existing = self.meta_rows.get(process_id, {})
                existing.update(table._update_payload)
                self.meta_rows[process_id] = existing
                return _FakeResult([existing])
            if table._select_columns:
                rows = list(self.meta_rows.values())
                return _FakeResult(rows)

        if table.name == "blog_memory_detail":
            if table._upsert_payload is not None:
                payload = dict(table._upsert_payload)
                process_id = str(payload["process_id"])
                existing = self.detail_rows.get(process_id, {})
                merged = {**existing, **payload}
                self.detail_rows[process_id] = merged
                return _FakeResult([merged])
            if table.in_filters.get("process_id") is not None:
                rows = []
                for process_id in table.in_filters["process_id"]:
                    row = self.detail_rows.get(str(process_id))
                    if row:
                        rows.append({
                            "process_id": str(process_id),
                            "memory_json": row.get("memory_json"),
                        })
                return _FakeResult(rows)
            process_id = table.filters.get("process_id")
            row = self.detail_rows.get(str(process_id))
            if not row:
                return _FakeResult(None)
            return _FakeResult({"memory_json": row.get("memory_json")})

        return _FakeResult([])


class _MaybeSingleNoneTable:
    def select(self, *_args, **_kwargs):
        return self

    def eq(self, *_args, **_kwargs):
        return self

    def lte(self, *_args, **_kwargs):
        return self

    def gte(self, *_args, **_kwargs):
        return self

    def maybe_single(self):
        return self

    def execute(self):
        return None


class _MaybeSingleNoneSupabase:
    def table(self, _name: str):
        return _MaybeSingleNoneTable()


@pytest.mark.asyncio
async def test_start_blog_generation_sets_organization_id_from_site(monkeypatch):
    fake_db = _EndpointSupabase(
        site_row={
            "id": "site-1",
            "user_id": "user-1",
            "organization_id": "org-123",
            "site_url": "https://example.com",
            "site_name": "Example",
        }
    )
    captured: Dict[str, Any] = {}

    class _DummyGenerationService:
        async def run_generation(self, **_kwargs):
            return None

    def _fake_check_can_generate(user_id: str, organization_id: Optional[str] = None):
        captured["user_id"] = user_id
        captured["organization_id"] = organization_id
        return SimpleNamespace(allowed=True, current=0, limit=10)

    monkeypatch.setattr(blog_endpoints, "get_supabase_client", lambda: fake_db)
    monkeypatch.setattr(blog_endpoints, "BlogGenerationService", _DummyGenerationService)
    monkeypatch.setattr(blog_endpoints.usage_service, "check_can_generate", _fake_check_can_generate)

    _ = await blog_endpoints.start_blog_generation(
        background_tasks=BackgroundTasks(),
        user_prompt="テスト記事を作りたい",
        wordpress_site_id="site-1",
        reference_url=None,
        files=[],
        user_id="user-1",
    )

    assert fake_db.inserted_process is not None
    assert fake_db.inserted_process["organization_id"] == "org-123"
    assert captured["organization_id"] == "org-123"


@pytest.mark.asyncio
async def test_memory_service_upsert_meta_generates_embedding_and_normalizes_categories(monkeypatch):
    fake = _MemorySupabase()
    fake.process_rows["11111111-1111-1111-1111-111111111111"] = {
        "id": "11111111-1111-1111-1111-111111111111",
        "user_id": "user-1",
        "organization_id": "org-1",
    }
    monkeypatch.setattr(memory_service_module, "supabase", fake)

    service = BlogMemoryService()

    async def _fake_embed_text(text: str):
        assert "タイトル" in text
        assert "要約" in text
        return [0.1] * 1536

    monkeypatch.setattr(service, "embed_text", _fake_embed_text)

    await service.upsert_meta(
        process_id="11111111-1111-1111-1111-111111111111",
        title="タイトル",
        summary="要約",
        draft_post_id=123,
        post_type="event",
        category_ids=[3, 1, 3, 2],
    )

    row = fake.meta_rows["11111111-1111-1111-1111-111111111111"]
    assert row["summary"] == "要約"
    assert row["post_type"] == "event"
    assert row["category_ids"] == [1, 2, 3]
    assert row["embedding_input"] == "タイトル\n\n要約"
    assert isinstance(row.get("embedding"), str)
    assert row.get("embedding_updated_at")


@pytest.mark.asyncio
async def test_memory_service_upsert_detail_patch_merges_existing_memory_json(monkeypatch):
    fake = _MemorySupabase()
    process_id = "11111111-1111-1111-1111-111111111111"
    fake.process_rows[process_id] = {
        "id": process_id,
        "user_id": "user-1",
        "organization_id": None,
    }
    fake.detail_rows[process_id] = {
        "process_id": process_id,
        "memory_json": {
            "user_input": "初回入力",
            "qa": [{"question": "Q1", "answer": "A1"}],
            "summary": None,
            "note": None,
            "tool_results": [],
            "execution_trace": {},
            "references": [],
        },
    }
    monkeypatch.setattr(memory_service_module, "supabase", fake)

    service = BlogMemoryService()
    await service.upsert_detail_patch(
        process_id=process_id,
        patch={
            "qa": [{"question": "Q2", "answer": "A2"}],
            "note": "重要メモ",
            "references": [{"type": "wp_post", "post_id": 123, "url": "https://example.com/post/123", "title": "参考記事"}],
        },
    )

    memory_json = fake.detail_rows[process_id]["memory_json"]
    assert memory_json["user_input"] == "初回入力"
    assert memory_json["note"] == "重要メモ"
    assert len(memory_json["qa"]) == 2
    assert memory_json["qa"][1]["question"] == "Q2"
    assert memory_json["references"][0]["post_id"] == 123


@pytest.mark.asyncio
async def test_memory_service_get_detail_memory_returns_empty_when_maybe_single_is_none(monkeypatch):
    monkeypatch.setattr(memory_service_module, "supabase", _MaybeSingleNoneSupabase())

    service = BlogMemoryService()
    detail = await service.get_detail_memory("11111111-1111-1111-1111-111111111111")

    assert detail == {
        "user_input": None,
        "qa": [],
        "summary": None,
        "note": None,
        "tool_results": [],
        "execution_trace": {},
        "references": [],
    }


@pytest.mark.asyncio
async def test_memory_service_search_returns_overview_only_by_default(monkeypatch):
    fake = _MemorySupabase()
    fake.rpc_responses["blog_memory_search_meta"] = [
        {
            "hit_process_id": "11111111-1111-1111-1111-111111111111",
            "score": 0.12,
            "draft_post_id": 123,
            "title": "類似記事",
            "summary": "最終要約",
            "post_type": "event",
            "category_ids": [1, 2],
        }
    ]
    fake.detail_rows["11111111-1111-1111-1111-111111111111"] = {
        "process_id": "11111111-1111-1111-1111-111111111111",
        "memory_json": {
            "user_input": "営業向けAIセミナー記事を作る",
            "qa": [],
            "summary": "最終要約",
            "note": "高専1-2年生向け。画像生成は使わない。",
            "tool_results": [],
            "execution_trace": {},
            "references": [],
        },
    }
    monkeypatch.setattr(memory_service_module, "supabase", fake)

    service = BlogMemoryService()

    async def _fake_embed_text(_query: str):
        return [0.1] * 1536

    monkeypatch.setattr(service, "embed_text", _fake_embed_text)

    hits = await service.search(
        process_id="22222222-2222-2222-2222-222222222222",
        query="営業 AI セミナー",
        k=5,
    )

    assert len(hits) == 1
    assert hits[0]["overview"] == {
        "title": "類似記事",
        "summary": "最終要約",
        "note": "高専1-2年生向け。画像生成は使わない。",
    }
    assert "request" not in hits[0]
    assert fake.rpc_calls[0][0] == "blog_memory_search_meta"
    assert fake.rpc_calls[0][1]["p_category_ids"] == []


@pytest.mark.asyncio
async def test_memory_service_search_returns_requested_detail_sections(monkeypatch):
    fake = _MemorySupabase()
    fake.rpc_responses["blog_memory_search_meta"] = [
        {
            "hit_process_id": "11111111-1111-1111-1111-111111111111",
            "score": 0.12,
            "draft_post_id": 123,
            "title": "類似記事",
            "summary": "最終要約",
            "post_type": "event",
            "category_ids": [2, 3],
        }
    ]
    fake.detail_rows["11111111-1111-1111-1111-111111111111"] = {
        "process_id": "11111111-1111-1111-1111-111111111111",
        "memory_json": {
            "user_input": "営業向けAIセミナー記事を作る",
            "qa": [{"question": "ターゲットは?", "answer": "営業マネージャー", "payload": {"input_type": "textarea"}}],
            "summary": "最終要約",
            "note": "高専1-2年生向け。",
            "tool_results": [
                {
                    "tool_name": "wp_get_recent_posts",
                    "input": {"category_id": 3},
                    "output_preview": "{\"posts\":[{\"id\":10}]}",
                    "references": [{"type": "wp_post", "post_id": 10, "url": "https://example.com/posts/10", "title": "参考記事10"}],
                    "captured_at": "2026-03-12T12:00:00+09:00",
                }
            ],
            "execution_trace": {"tools": ["wp_get_recent_posts", "wp_create_draft_post"], "flow": ["recent_posts", "draft_created"]},
            "references": [{"type": "wp_post", "post_id": 10, "url": "https://example.com/posts/10", "title": "参考記事10"}],
        },
    }
    monkeypatch.setattr(memory_service_module, "supabase", fake)

    service = BlogMemoryService()

    async def _fake_embed_text(_query: str):
        return [0.1] * 1536

    monkeypatch.setattr(service, "embed_text", _fake_embed_text)

    hits = await service.search(
        process_id="22222222-2222-2222-2222-222222222222",
        query="営業 AI セミナー",
        need=["request", "qa", "tools", "trace", "references"],
        post_type="event",
        category_ids=[3, 2, 3],
    )

    hit = hits[0]
    assert hit["request"] == "営業向けAIセミナー記事を作る"
    assert hit["qa"] == [{"question": "ターゲットは?", "answer": "営業マネージャー", "payload": {"input_type": "textarea"}}]
    assert hit["tools"][0]["tool_name"] == "wp_get_recent_posts"
    assert hit["trace"]["flow"] == ["recent_posts", "draft_created"]
    assert hit["references"][0]["post_id"] == 10
    assert fake.rpc_calls[0][1]["p_post_type"] == "event"
    assert fake.rpc_calls[0][1]["p_category_ids"] == [2, 3]


@pytest.mark.asyncio
async def test_process_result_saves_summary_note_and_execution_trace(monkeypatch):
    monkeypatch.setattr(
        "app.domains.blog.services.generation_service.build_blog_writer_agent",
        lambda: SimpleNamespace(name="dummy-agent"),
    )
    service = BlogGenerationService()

    async def _noop_async(*_args, **_kwargs):
        return None

    summary_calls = []
    note_calls = []
    upsert_calls = []
    trace_calls = []
    captured: Dict[str, Any] = {}

    async def _fake_record_memory_summary_safe(*, process_id: str, summary: str):
        summary_calls.append({"process_id": process_id, "summary": summary})

    async def _fake_record_memory_note_safe(*, process_id: str, note: str):
        note_calls.append({"process_id": process_id, "note": note})

    async def _fake_upsert_memory_meta_safe(**kwargs):
        upsert_calls.append(kwargs)

    async def _fake_set_memory_execution_trace_safe(*, process_id: str, tool_sequence: List[str]):
        trace_calls.append({"process_id": process_id, "tool_sequence": tool_sequence})

    def _fake_record_success(user_id: str, process_id: str, organization_id: Optional[str] = None):
        captured["user_id"] = user_id
        captured["process_id"] = process_id
        captured["organization_id"] = organization_id
        return True

    monkeypatch.setattr(service, "_update_state", _noop_async)
    monkeypatch.setattr(service, "_publish_event", _noop_async)
    monkeypatch.setattr(service, "_record_memory_summary_safe", _fake_record_memory_summary_safe)
    monkeypatch.setattr(service, "_record_memory_note_safe", _fake_record_memory_note_safe)
    monkeypatch.setattr(service, "_upsert_memory_meta_safe", _fake_upsert_memory_meta_safe)
    monkeypatch.setattr(service, "_set_memory_execution_trace_safe", _fake_set_memory_execution_trace_safe)
    monkeypatch.setattr(service, "_get_process_organization_id", lambda _pid: "org-fixed")
    monkeypatch.setattr("app.domains.blog.services.generation_service.usage_service.record_success", _fake_record_success)

    await service._process_result(
        process_id="process-1",
        user_id="user-1",
        output=BlogCompletionOutput(
            post_id=123,
            preview_url="https://preview.example.com",
            edit_url="https://edit.example.com",
            summary="高専生向けAIセミナー告知記事を作成しました",
            note="高専1-2年生向け。画像生成なし。CTAは最後に1回。",
        ),
        draft_post_args={"post_type": "event", "category_ids": [4, 2, 4]},
        tool_sequence=["wp_get_site_info", "memory_search", "wp_create_draft_post"],
    )

    assert summary_calls[0] == {
        "process_id": "process-1",
        "summary": "高専生向けAIセミナー告知記事を作成しました",
    }
    assert note_calls[0] == {
        "process_id": "process-1",
        "note": "高専1-2年生向け。画像生成なし。CTAは最後に1回。",
    }
    assert upsert_calls[0]["summary"] == "高専生向けAIセミナー告知記事を作成しました"
    assert upsert_calls[0]["post_type"] == "event"
    assert upsert_calls[0]["category_ids"] == [2, 4]
    assert trace_calls[0] == {
        "process_id": "process-1",
        "tool_sequence": ["wp_get_site_info", "memory_search", "wp_create_draft_post"],
    }
    assert captured["organization_id"] == "org-fixed"


def test_usage_limit_service_handles_maybe_single_none():
    service = UsageLimitService()
    service.db = _MaybeSingleNoneSupabase()

    assert service._is_privileged("user-1") is False
    assert service._get_current_tracking("user-1") is None
    assert service._create_tracking_from_subscription("user-1") is None
    assert service._get_plan_tier("free") is None
