# -*- coding: utf-8 -*-
"""
Blog company memory service.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Literal, Optional

from app.common.database import supabase
from app.domains.blog.company_memory_schemas import (
    CURRENT_COMPANY_MEMORY_SCHEMA_VERSION,
    canonicalize_company_memory,
)

logger = logging.getLogger(__name__)


def _result_data(result: Any) -> Any:
    if result is None:
        return None
    return getattr(result, "data", None)


def _resolve_scope(user_id: str, organization_id: Optional[str]) -> tuple[str, Optional[str]]:
    return ("org", organization_id) if organization_id else ("user", None)


def _company_memory_query(user_id: str, organization_id: Optional[str]):
    scope_type, resolved_org_id = _resolve_scope(user_id, organization_id)
    query = supabase.table("company_memory").select("*").eq("scope_type", scope_type)
    if scope_type == "org":
        return query.eq("organization_id", resolved_org_id)
    return query.eq("user_id", user_id)


def _load_default_company_name(user_id: str) -> str:
    try:
        result = (
            supabase.table("company_info")
            .select("name")
            .eq("user_id", user_id)
            .eq("is_default", True)
            .maybe_single()
            .execute()
        )
        row = _result_data(result) or {}
        return str(row.get("name") or "").strip()
    except Exception as exc:
        logger.warning("Default company_info 読み込み失敗: %s", exc)
        return ""


def _create_initial_content(
    *,
    site_name: Optional[str],
    site_url: Optional[str],
    language: Optional[str],
    company_name: Optional[str],
) -> dict[str, Any]:
    return canonicalize_company_memory(
        {
            "schema_version": CURRENT_COMPANY_MEMORY_SCHEMA_VERSION,
            "company_name": company_name or "",
            "site_name": site_name or "",
            "site_url": site_url or "",
            "language": language or "ja",
        }
    )


def get_company_memory(
    *,
    user_id: str,
    organization_id: Optional[str],
) -> Optional[dict[str, Any]]:
    try:
        result = _company_memory_query(user_id, organization_id).maybe_single().execute()
        row = _result_data(result)
        if not row:
            return None
        row["content_json"] = canonicalize_company_memory(row.get("content_json"))
        row["schema_version"] = CURRENT_COMPANY_MEMORY_SCHEMA_VERSION
        return row
    except Exception as exc:
        logger.warning("company_memory 取得失敗: %s", exc)
        return None


def get_or_create_company_memory(
    *,
    user_id: str,
    organization_id: Optional[str],
    site_name: Optional[str],
    site_url: Optional[str],
    language: Optional[str] = None,
) -> dict[str, Any]:
    existing = get_company_memory(user_id=user_id, organization_id=organization_id)
    if existing:
        return existing

    scope_type, resolved_org_id = _resolve_scope(user_id, organization_id)
    initial_content = _create_initial_content(
        site_name=site_name,
        site_url=site_url,
        language=language,
        company_name=_load_default_company_name(user_id),
    )
    payload = {
        "user_id": user_id,
        "organization_id": resolved_org_id,
        "scope_type": scope_type,
        "content_json": initial_content,
        "content_md": None,
        "schema_version": CURRENT_COMPANY_MEMORY_SCHEMA_VERSION,
        "version": 1,
    }

    try:
        result = supabase.table("company_memory").insert(payload).execute()
        row = (_result_data(result) or [{}])[0]
        row["content_json"] = canonicalize_company_memory(row.get("content_json"))
        row["schema_version"] = CURRENT_COMPANY_MEMORY_SCHEMA_VERSION
        return row
    except Exception as exc:
        logger.warning("company_memory 作成時競合または失敗: %s", exc)
        existing = get_company_memory(user_id=user_id, organization_id=organization_id)
        if existing:
            return existing
        raise


def resolve_company_memory_scope_from_process(process_id: str) -> dict[str, Any]:
    result = (
        supabase.table("blog_generation_state")
        .select("user_id, organization_id, wordpress_site_id")
        .eq("id", process_id)
        .single()
        .execute()
    )
    row = _result_data(result)
    if not row:
        raise ValueError(f"blog_generation_state not found: {process_id}")
    return {
        "user_id": row["user_id"],
        "organization_id": row.get("organization_id"),
        "wordpress_site_id": row.get("wordpress_site_id"),
    }


def _load_site_defaults(site_id: Optional[str]) -> dict[str, Any]:
    if not site_id:
        return {"site_name": "", "site_url": "", "language": "ja"}
    try:
        result = (
            supabase.table("wordpress_sites")
            .select("site_name, site_url")
            .eq("id", site_id)
            .maybe_single()
            .execute()
        )
        row = _result_data(result) or {}
        return {
            "site_name": row.get("site_name") or "",
            "site_url": row.get("site_url") or "",
            "language": "ja",
        }
    except Exception as exc:
        logger.warning("wordpress_sites から初期値取得失敗: %s", exc)
        return {"site_name": "", "site_url": "", "language": "ja"}


def get_or_create_company_memory_from_process(process_id: str) -> dict[str, Any]:
    scope = resolve_company_memory_scope_from_process(process_id)
    defaults = _load_site_defaults(scope.get("wordpress_site_id"))
    return get_or_create_company_memory(
        user_id=scope["user_id"],
        organization_id=scope.get("organization_id"),
        site_name=defaults["site_name"],
        site_url=defaults["site_url"],
        language=defaults["language"],
    )


def render_company_memory_text(content_json: dict[str, Any]) -> str:
    content = canonicalize_company_memory(content_json)
    sections: list[str] = []

    overview_lines: list[str] = []
    field_labels = [
        ("company_name", "会社名"),
        ("site_name", "サイト名"),
        ("site_url", "サイトURL"),
        ("language", "言語"),
        ("business_summary", "事業概要"),
        ("company_positioning", "会社の立ち位置"),
        ("site_positioning", "サイトの位置づけ"),
    ]
    for key, label in field_labels:
        value = content.get(key)
        if value:
            overview_lines.append(f"- {label}: {value}")
    if overview_lines:
        sections.append("### 会社概要\n" + "\n".join(overview_lines))

    list_sections = [
        ("core_services", "### 主力サービス"),
        ("strengths", "### 強み"),
        ("target_customers", "### 基本ターゲット"),
        ("brand_voice", "### ブランドトーン"),
        ("avoid_expressions", "### 避けたい表現"),
        ("preferred_messages", "### よく使いたい訴求"),
        ("style_rules", "### 表記ルール"),
    ]
    for key, title in list_sections:
        items = content.get(key) or []
        if items:
            sections.append(title + "\n" + "\n".join(f"- {item}" for item in items))

    site_ops: list[str] = []
    if content.get("primary_post_types"):
        site_ops.append("- 主な投稿タイプ:")
        site_ops.extend(f"  - {item}" for item in content["primary_post_types"])
    if content.get("primary_categories"):
        site_ops.append("- 主なカテゴリ:")
        site_ops.extend(f"  - {item}" for item in content["primary_categories"])
    if content.get("site_operational_notes"):
        site_ops.append("- 運用メモ:")
        site_ops.extend(f"  - {item}" for item in content["site_operational_notes"])
    if site_ops:
        sections.append("### サイト運用情報\n" + "\n".join(site_ops))

    return "\n\n".join(sections)


def render_company_memory_json_text(content_json: dict[str, Any]) -> str:
    content = canonicalize_company_memory(content_json)
    return json.dumps(content, ensure_ascii=False, indent=2)


def get_empty_company_memory_fields(content_json: dict[str, Any]) -> list[str]:
    content = canonicalize_company_memory(content_json)
    empty_fields: list[str] = []

    scalar_fields = [
        "company_name",
        "site_name",
        "site_url",
        "language",
        "business_summary",
        "company_positioning",
        "site_positioning",
    ]
    list_fields = [
        "core_services",
        "strengths",
        "target_customers",
        "brand_voice",
        "avoid_expressions",
        "preferred_messages",
        "style_rules",
        "primary_post_types",
        "primary_categories",
        "site_operational_notes",
    ]

    for key in scalar_fields:
        if not content.get(key):
            empty_fields.append(key)
    for key in list_fields:
        if not content.get(key):
            empty_fields.append(key)

    return empty_fields


def save_company_memory_update(
    *,
    process_id: str,
    decision: Literal["update", "no_change"],
    content_json: Optional[dict[str, Any]],
) -> dict[str, Any]:
    if decision == "update" and content_json is None:
        return {
            "status": "validation_error",
            "message": "decision=update の場合は content_json が必要です",
        }

    current_row = get_or_create_company_memory_from_process(process_id)
    current_content = canonicalize_company_memory(current_row.get("content_json"))

    if decision == "no_change":
        logger.info("company_memory_update: no_change process_id=%s", process_id)
        logger.info("company_memory current=%s", json.dumps(current_content, ensure_ascii=False))
        return {"status": "no_change"}

    try:
        next_content = canonicalize_company_memory(content_json)
    except Exception as exc:
        return {
            "status": "validation_error",
            "message": f"content_json の正規化に失敗しました: {exc}",
        }

    logger.info("company_memory current=%s", json.dumps(current_content, ensure_ascii=False))
    logger.info("company_memory proposed=%s", json.dumps(next_content, ensure_ascii=False))

    if next_content == current_content:
        logger.info("company_memory_update: effective no_change process_id=%s", process_id)
        return {"status": "no_change"}

    try:
        result = (
            supabase.table("company_memory")
            .update(
                {
                    "content_json": next_content,
                    "schema_version": CURRENT_COMPANY_MEMORY_SCHEMA_VERSION,
                    "version": int(current_row["version"]) + 1,
                }
            )
            .eq("id", current_row["id"])
            .eq("version", current_row["version"])
            .execute()
        )
        updated_rows = _result_data(result) or []
        if not updated_rows:
            logger.warning("company_memory_update: conflict process_id=%s", process_id)
            return {"status": "conflict"}
        logger.info("company_memory updated=%s", json.dumps(next_content, ensure_ascii=False))
        return {"status": "saved"}
    except Exception as exc:
        logger.warning("company_memory_update validation/save failed: %s", exc)
        return {"status": "validation_error", "message": str(exc)}
