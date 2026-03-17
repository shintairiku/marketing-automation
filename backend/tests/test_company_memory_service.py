# -*- coding: utf-8 -*-

from app.domains.blog.company_memory_schemas import (
    CURRENT_COMPANY_MEMORY_SCHEMA_VERSION,
    canonicalize_company_memory,
    normalize_company_memory_update_fields,
)
from app.domains.blog.services import company_memory_service


def test_canonicalize_company_memory_normalizes_shape() -> None:
    result = canonicalize_company_memory(
        {
            "schema_version": 999,
            "company_name": "  株式会社新大陸  ",
            "language": "",
            "strengths": [" 現場伴走 ", "", "現場伴走", "継続改善"],
            "unknown_key": "ignored",
        }
    )

    assert result["schema_version"] == CURRENT_COMPANY_MEMORY_SCHEMA_VERSION
    assert result["company_name"] == "株式会社新大陸"
    assert result["language"] == "ja"
    assert result["strengths"] == ["現場伴走", "継続改善"]
    assert "unknown_key" not in result


def test_render_company_memory_text_omits_empty_sections() -> None:
    text = company_memory_service.render_company_memory_text(
        {
            "schema_version": 1,
            "company_name": "株式会社新大陸",
            "site_name": "SNS・WEB集客の新大陸",
            "strengths": ["現場伴走", "継続改善"],
            "site_operational_notes": ["課題解決型の記事を重視する"],
        }
    )

    assert "### 会社概要" in text
    assert "### 強み" in text
    assert "### サイト運用情報" in text
    assert "### ブランドトーン" not in text


def test_get_empty_company_memory_fields_lists_blank_keys() -> None:
    empty_fields = company_memory_service.get_empty_company_memory_fields(
        {
            "schema_version": 1,
            "site_name": "SNS・WEB集客の新大陸",
            "site_url": "https://shintairiku.jp/wp",
            "language": "ja",
            "strengths": ["現場伴走"],
        }
    )

    assert "company_name" in empty_fields
    assert "business_summary" in empty_fields
    assert "strengths" not in empty_fields
    assert "site_name" not in empty_fields


def test_render_company_memory_json_text_includes_empty_shape() -> None:
    text = company_memory_service.render_company_memory_json_text(
        {
            "schema_version": 1,
            "site_name": "SNS・WEB集客の新大陸",
            "site_url": "https://shintairiku.jp/wp",
            "language": "ja",
        }
    )

    assert '"site_name": "SNS・WEB集客の新大陸"' in text
    assert '"business_summary": ""' in text
    assert '"strengths": []' in text


def test_normalize_company_memory_update_fields_rejects_unknown_keys() -> None:
    try:
        normalize_company_memory_update_fields(
            {
                "business_summary": "Web集客支援",
                "unknown_key": "ignored",
            }
        )
    except ValueError as exc:
        assert "unknown_key" in str(exc)
    else:
        raise AssertionError("未知キーで ValueError になる想定")


def test_save_company_memory_update_returns_no_change_when_effectively_same(
    monkeypatch,
) -> None:
    current = {
        "id": "memory-1",
        "version": 3,
        "content_json": {
            "schema_version": 1,
            "company_name": "株式会社新大陸",
            "strengths": ["現場伴走", "継続改善"],
        },
    }

    monkeypatch.setattr(
        company_memory_service,
        "get_or_create_company_memory_from_process",
        lambda process_id: current,
    )

    result = company_memory_service.save_company_memory_update(
        process_id="process-1",
        decision="update",
        fields={
            "company_name": " 株式会社新大陸 ",
            "strengths": ["現場伴走", "継続改善", "現場伴走"],
        },
    )

    assert result == {"status": "no_change"}


def test_save_company_memory_update_merges_partial_fields(
    monkeypatch,
) -> None:
    current = {
        "id": "memory-1",
        "version": 3,
        "content_json": {
            "schema_version": 1,
            "company_name": "株式会社新大陸",
            "business_summary": "",
            "strengths": ["現場伴走"],
        },
    }

    updated_payload: dict[str, object] = {}

    monkeypatch.setattr(
        company_memory_service,
        "get_or_create_company_memory_from_process",
        lambda process_id: current,
    )

    class _Result:
        def __init__(self) -> None:
            self.data = [{"id": "memory-1"}]

    class _UpdateQuery:
        def update(self, payload):
            updated_payload.update(payload)
            return self

        def eq(self, *_args):
            return self

        def execute(self):
            return _Result()

    class _SupabaseStub:
        def table(self, name: str):
            assert name == "company_memory"
            return _UpdateQuery()

    monkeypatch.setattr(company_memory_service, "supabase", _SupabaseStub())

    result = company_memory_service.save_company_memory_update(
        process_id="process-1",
        decision="update",
        fields={
            "business_summary": "  Web集客支援  ",
            "strengths": ["現場伴走", "継続改善", "現場伴走"],
        },
    )

    assert result == {"status": "saved"}
    assert updated_payload["content_json"]["company_name"] == "株式会社新大陸"
    assert updated_payload["content_json"]["business_summary"] == "Web集客支援"
    assert updated_payload["content_json"]["strengths"] == ["現場伴走", "継続改善"]


def test_save_company_memory_update_requires_fields() -> None:
    result = company_memory_service.save_company_memory_update(
        process_id="process-1",
        decision="update",
        fields=None,
    )

    assert result["status"] == "validation_error"
