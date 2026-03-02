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


def test_memory_service_normalize_roles_accepts_qa():
    roles = BlogMemoryService._normalize_roles(["qa", "user_input"])
    assert roles == ["qa", "user_input"]


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


@pytest.mark.asyncio
async def test_memory_service_upsert_meta_generates_embedding_immediately(monkeypatch):
    class _UpsertTable:
        def __init__(self, owner):
            self.owner = owner
            self.payload = None
            self.eq_key = None
            self.eq_value = None

        def update(self, payload):
            self.payload = payload
            self.owner.update_payload = payload
            return self

        def eq(self, key, value):
            self.eq_key = key
            self.eq_value = value
            self.owner.update_eq = (key, value)
            return self

        def execute(self):
            return _FakeResult([{"process_id": self.eq_value}])

    class _UpsertSupabase:
        def __init__(self):
            self.rpc_fn = None
            self.rpc_params = None
            self.update_payload = None
            self.update_eq = None

        def rpc(self, fn, params):
            self.rpc_fn = fn
            self.rpc_params = params
            return self

        def execute(self):
            return _FakeResult([])

        def table(self, name):
            assert name == "blog_memory_meta"
            return _UpsertTable(self)

    fake = _UpsertSupabase()
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
        short_summary="要約",
        draft_post_id=123,
    )

    assert fake.rpc_fn == "blog_memory_upsert_meta"
    assert fake.rpc_params["p_process_id"] == "11111111-1111-1111-1111-111111111111"
    assert fake.update_eq == ("process_id", "11111111-1111-1111-1111-111111111111")
    assert fake.update_payload is not None
    assert isinstance(fake.update_payload.get("embedding"), str)
    assert fake.update_payload.get("embedding_updated_at")


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


@pytest.mark.asyncio
async def test_memory_service_append_tool_result_uses_rpc(monkeypatch):
    class _RpcSupabase:
        def __init__(self):
            self.fn = None
            self.params = None

        def rpc(self, fn, params):
            self.fn = fn
            self.params = params
            return self

        def execute(self):
            return _FakeResult([{"blog_memory_append_tool_result": "tool-memory-1"}])

    fake = _RpcSupabase()
    monkeypatch.setattr(memory_service_module, "supabase", fake)
    service = BlogMemoryService()

    memory_id = await service.append_tool_result(
        process_id="11111111-1111-1111-1111-111111111111",
        content='{"query":"test"}',
    )

    assert fake.fn == "blog_memory_append_tool_result"
    assert fake.params["p_process_id"] == "11111111-1111-1111-1111-111111111111"
    assert fake.params["p_content"] == '{"query":"test"}'
    assert memory_id == "tool-memory-1"


@pytest.mark.asyncio
async def test_memory_service_search_uses_server_side_threshold_setting(monkeypatch):
    class _SearchSupabase:
        def __init__(self):
            self.calls = []
            self.fn = None
            self.params = None

        def rpc(self, fn, params):
            self.calls.append((fn, params))
            self.fn = fn
            self.params = params
            return self

        def execute(self):
            if self.fn == "blog_memory_search_meta":
                return _FakeResult(
                    [
                        {
                            "hit_process_id": "11111111-1111-1111-1111-111111111111",
                            "score": 0.12,
                            "draft_post_id": 123,
                            "title": "類似記事",
                            "short_summary": "要約",
                        },
                        {
                            "hit_process_id": "33333333-3333-3333-3333-333333333333",
                            "score": 0.67,
                            "draft_post_id": 456,
                            "title": "遠い記事",
                            "short_summary": "要約2",
                        }
                    ]
                )
            if self.fn == "blog_memory_get_items":
                return _FakeResult([])
            return _FakeResult([])

    fake = _SearchSupabase()
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

    assert hits
    assert len(hits) == 2
    first_call = fake.calls[0]
    assert first_call[0] == "blog_memory_search_meta"
    assert "p_score_threshold" not in first_call[1]


def test_should_persist_tool_result_excludes_search_tools():
    assert BlogGenerationService._should_persist_tool_result("memory_search") is False
    assert BlogGenerationService._should_persist_tool_result("web_search") is False
    assert BlogGenerationService._should_persist_tool_result("wp_get_recent_posts") is True
    assert BlogGenerationService._should_persist_tool_result("unknown_tool") is False


def test_build_memory_search_log_content_compacts_hits(monkeypatch):
    monkeypatch.setattr(
        "app.domains.blog.services.generation_service.build_blog_writer_agent",
        lambda: SimpleNamespace(name="dummy-agent"),
    )
    service = BlogGenerationService()
    output = json.dumps(
        {
            "ok": True,
            "data": {
                "hits": [
                    {"process_id": "p1", "score": 0.11, "meta": {"title": "記事1"}},
                    {"process_id": "p2", "score": 0.22, "meta": {"title": "記事2"}},
                    {"process_id": "p3", "score": 0.33, "meta": {"title": "記事3"}},
                    {"process_id": "p4", "score": 0.44, "meta": {"title": "記事4"}},
                ]
            },
        },
        ensure_ascii=False,
    )

    content = service._build_memory_search_log_content(
        tool_args={"query": "営業 AI セミナー", "k": 5},
        output=output,
    )
    payload = json.loads(content)

    assert payload["type"] == "memory_search_log"
    assert payload["query"] == "営業 AI セミナー"
    assert payload["k"] == 5
    assert payload["hit_count"] == 4
    assert len(payload["top_hits"]) == 3
    assert payload["top_hits"][0]["process_id"] == "p1"


def test_extract_answer_by_question_keywords():
    blog_context = {
        "ai_questions": [
            {"question_id": "q1", "question": "この記事のターゲット読者は誰ですか？"},
            {"question_id": "q2", "question": "トーンはどうしますか？"},
            {"question_id": "q3", "question": "含めたいキーワードはありますか？"},
        ],
        "user_answers": {
            "q1": "営業マネージャー",
            "q2": "フォーマル",
            "q3": "生成AI, セミナー, 導入事例",
        },
    }

    audience = BlogGenerationService._extract_answer_by_question_keywords(
        blog_context, ["ターゲット", "読者"]
    )
    tone = BlogGenerationService._extract_answer_by_question_keywords(
        blog_context, ["トーン", "文体"]
    )
    must_include = BlogGenerationService._extract_must_include_keywords(blog_context)

    assert audience == "営業マネージャー"
    assert tone == "フォーマル"
    assert must_include == ["生成AI", "セミナー", "導入事例"]


def test_extract_post_snapshot_payload_from_wp_raw_content():
    raw_output = json.dumps(
        {
            "ok": True,
            "data": {
                "post": {
                    "title": "営業向けAIセミナー告知",
                    "raw_content": (
                        "<h2>開催概要</h2><p>営業部門向けの実践セミナーです。</p>"
                        "<h3>申し込み方法</h3><p>フォームから登録してください。</p>"
                    ),
                }
            },
        },
        ensure_ascii=False,
    )

    payload = BlogGenerationService._extract_post_snapshot_payload(
        raw_output=raw_output,
        post_id=123,
        excerpt_max_chars=80,
    )

    assert payload["type"] == "post_snapshot"
    assert payload["post_id"] == 123
    assert payload["title"] == "営業向けAIセミナー告知"
    assert payload["headings"] == ["開催概要", "申し込み方法"]
    assert payload["content_hash"]
