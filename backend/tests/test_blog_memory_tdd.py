# -*- coding: utf-8 -*-
import json
import sys
from types import SimpleNamespace
from typing import Any, Dict, Optional
from pathlib import Path

import pytest
from fastapi import BackgroundTasks

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.domains.blog import endpoints as blog_endpoints
from app.domains.blog.agents import tools as agent_tools
from app.domains.blog.schemas import BlogCompletionOutput, BlogMemoryAppendItemRequest
from app.domains.blog.services.generation_service import BlogGenerationService
from app.domains.blog.services.memory_service import BlogMemoryError, BlogMemoryService
import app.domains.blog.services.memory_service as memory_service_module


class _FakeResult:
    def __init__(self, data: Any):
        self.data = data


class _FakeTable:
    def __init__(self, db: "_FakeSupabase", name: str):
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


class _FakeSupabase:
    def __init__(self, site_row: Optional[Dict[str, Any]] = None, process_row: Optional[Dict[str, Any]] = None):
        self.site_row = site_row
        self.process_row = process_row
        self.inserted_process: Optional[Dict[str, Any]] = None

    def table(self, name: str):
        return _FakeTable(self, name)

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


@pytest.mark.asyncio
async def test_start_blog_generation_sets_organization_id_from_site(monkeypatch):
    fake_db = _FakeSupabase(
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
async def test_append_memory_item_returns_not_found_when_process_missing(monkeypatch):
    fake_db = _FakeSupabase(process_row=None)
    monkeypatch.setattr(blog_endpoints, "get_supabase_client", lambda: fake_db)

    response = await blog_endpoints.append_memory_item(
        process_id="11111111-1111-1111-1111-111111111111",
        request=BlogMemoryAppendItemRequest(role="user_input", content="hello"),
        user_id="user-1",
    )

    assert response.status_code == 404
    payload = json.loads(response.body.decode("utf-8"))
    assert payload["ok"] is False
    assert payload["error"]["code"] == "BLOG_PROCESS_NOT_FOUND"


@pytest.mark.asyncio
async def test_append_memory_item_returns_invalid_argument_for_malformed_process_id(monkeypatch):
    fake_db = _FakeSupabase(process_row=None)
    monkeypatch.setattr(blog_endpoints, "get_supabase_client", lambda: fake_db)

    response = await blog_endpoints.append_memory_item(
        process_id="not-a-uuid",
        request=BlogMemoryAppendItemRequest(role="user_input", content="hello"),
        user_id="user-1",
    )

    assert response.status_code == 400
    payload = json.loads(response.body.decode("utf-8"))
    assert payload["ok"] is False
    assert payload["error"]["code"] == "INVALID_ARGUMENT"


@pytest.mark.asyncio
async def test_append_memory_item_success_payload(monkeypatch):
    fake_db = _FakeSupabase(
        process_row={
            "id": "11111111-1111-1111-1111-111111111111",
            "user_id": "user-1",
            "organization_id": "org-1",
            "wordpress_site_id": "site-1",
            "draft_post_id": None,
        }
    )

    class _FakeMemoryService:
        async def append_item(self, process_id: str, role: str, content: str) -> str:
            assert process_id == "11111111-1111-1111-1111-111111111111"
            assert role == "assistant_output"
            assert content == "保存テスト"
            return "memory-item-1"

    monkeypatch.setattr(blog_endpoints, "get_supabase_client", lambda: fake_db)
    monkeypatch.setattr(blog_endpoints, "get_blog_memory_service", lambda: _FakeMemoryService())

    response = await blog_endpoints.append_memory_item(
        process_id="11111111-1111-1111-1111-111111111111",
        request=BlogMemoryAppendItemRequest(role="assistant_output", content="保存テスト"),
        user_id="user-1",
    )

    assert isinstance(response, dict)
    assert response["ok"] is True
    assert response["data"]["memory_item_id"] == "memory-item-1"


@pytest.mark.asyncio
async def test_memory_service_rejects_tool_result_role():
    service = BlogMemoryService()

    with pytest.raises(BlogMemoryError) as exc:
        await service.append_item(
            process_id="process-1",
            role="tool_result",
            content="forbidden",
        )

    assert exc.value.code == "ROLE_TOOL_RESULT_FORBIDDEN"


@pytest.mark.asyncio
async def test_memory_service_maps_invalid_uuid_error_to_invalid_argument():
    err = BlogMemoryService._map_db_exception(
        Exception('invalid input syntax for type uuid: "bad-id"')
    )
    assert err.code == "INVALID_ARGUMENT"
    assert err.http_status == 400


def test_format_user_answers_for_memory_includes_questions():
    text = BlogGenerationService._format_user_answers_for_memory(
        user_answers={
            "q1": "東京で開催します",
            "q2": "uploaded:seminar-banner.webp",
        },
        ai_questions=[
            {
                "question_id": "q1",
                "question": "開催場所はどこですか？",
                "input_type": "textarea",
            },
            {
                "question_id": "q2",
                "question": "告知画像をアップロードしてください",
                "input_type": "image_upload",
            },
        ],
    )

    assert "Q(q1): 開催場所はどこですか？" in text
    assert "A: 東京で開催します" in text
    assert "Q(q2): 告知画像をアップロードしてください" in text
    assert "InputType: image_upload" in text
    assert "A: uploaded:seminar-banner.webp" in text


@pytest.mark.asyncio
async def test_process_result_uses_process_fixed_org_id(monkeypatch):
    monkeypatch.setattr(
        "app.domains.blog.services.generation_service.build_blog_writer_agent",
        lambda: SimpleNamespace(name="dummy-agent"),
    )
    service = BlogGenerationService()

    async def _noop_async(*_args, **_kwargs):
        return None

    captured: Dict[str, Any] = {}

    def _fake_record_success(user_id: str, process_id: str, organization_id: Optional[str] = None):
        captured["user_id"] = user_id
        captured["process_id"] = process_id
        captured["organization_id"] = organization_id
        return True

    monkeypatch.setattr(service, "_update_state", _noop_async)
    monkeypatch.setattr(service, "_publish_event", _noop_async)
    monkeypatch.setattr(service, "_append_memory_item_safe", _noop_async)
    monkeypatch.setattr(service, "_upsert_memory_meta_safe", _noop_async)
    monkeypatch.setattr(service, "_get_process_organization_id", lambda _pid: "org-fixed")
    monkeypatch.setattr("app.domains.blog.services.generation_service.usage_service.record_success", _fake_record_success)

    await service._process_result(
        process_id="process-1",
        user_id="user-1",
        output=BlogCompletionOutput(
            post_id=123,
            preview_url="https://preview.example.com",
            edit_url="https://edit.example.com",
            summary="要約",
        ),
    )

    assert captured["organization_id"] == "org-fixed"


@pytest.mark.asyncio
async def test_run_embedding_batch_handles_stale_rows_without_column_compare_filter(monkeypatch):
    updates: list[str] = []

    class _BatchTable:
        def __init__(self, rows):
            self._rows = rows
            self._update_payload = None
            self._eq_pid = None

        def select(self, *_args, **_kwargs):
            return self

        def order(self, *_args, **_kwargs):
            return self

        def execute(self):
            if self._update_payload is None:
                return _FakeResult(self._rows)
            updates.append(self._eq_pid)
            return _FakeResult([{"process_id": self._eq_pid}])

        def update(self, payload):
            self._update_payload = payload
            return self

        def eq(self, _key, value):
            self._eq_pid = value
            return self

    class _BatchSupabase:
        def __init__(self):
            self.rows = [
                {
                    "process_id": "p1",
                    "embedding_input": "t1",
                    "embedding": None,
                    "updated_at": "2026-02-23T12:00:00+00:00",
                    "embedding_updated_at": None,
                },
                {
                    "process_id": "p2",
                    "embedding_input": "t2",
                    "embedding": "[0.1,0.2]",
                    "updated_at": "2026-02-23T13:00:00+00:00",
                    "embedding_updated_at": "2026-02-23T12:00:00+00:00",
                },
                {
                    "process_id": "p3",
                    "embedding_input": "t3",
                    "embedding": "[0.1,0.2]",
                    "updated_at": "2026-02-23T12:00:00+00:00",
                    "embedding_updated_at": "2026-02-23T13:00:00+00:00",
                },
            ]

        def table(self, _name):
            return _BatchTable(self.rows)

    service = BlogMemoryService()
    monkeypatch.setattr(memory_service_module, "supabase", _BatchSupabase())

    async def _fake_embed_texts(texts):
        assert texts == ["t1", "t2"]
        return [[0.1] * 1536, [0.2] * 1536]

    monkeypatch.setattr(service, "embed_texts", _fake_embed_texts)

    updated = await service.run_embedding_batch(limit=10)

    assert updated == 2
    assert updates == ["p1", "p2"]


def test_resolve_process_id_for_memory_uses_current_context(monkeypatch):
    monkeypatch.setattr(agent_tools, "get_current_process_id", lambda: "proc-1")

    resolved, err = agent_tools._resolve_process_id_for_memory(None)

    assert err is None
    assert resolved == "proc-1"


def test_resolve_process_id_for_memory_rejects_mismatch(monkeypatch):
    monkeypatch.setattr(agent_tools, "get_current_process_id", lambda: "proc-1")

    resolved, err = agent_tools._resolve_process_id_for_memory("proc-2")

    assert resolved is None
    assert err is not None
    assert err["error"]["code"] == "FORBIDDEN"
