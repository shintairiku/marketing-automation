# -*- coding: utf-8 -*-
"""
Blog company memory schemas.
"""

from __future__ import annotations

from typing import Any, Mapping

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

CURRENT_COMPANY_MEMORY_SCHEMA_VERSION = 1


def _normalize_text(value: Any, *, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip()


def _normalize_string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        items = [value]
    elif isinstance(value, list):
        items = value
    else:
        return []

    normalized: list[str] = []
    seen: set[str] = set()
    for item in items:
        text = _normalize_text(item)
        if not text or text in seen:
            continue
        seen.add(text)
        normalized.append(text)
    return normalized


class CompanyMemoryContent(BaseModel):
    """company_memory.content_json の canonical schema"""

    model_config = ConfigDict(extra="ignore")

    schema_version: int = CURRENT_COMPANY_MEMORY_SCHEMA_VERSION
    company_name: str = ""
    site_name: str = ""
    site_url: str = ""
    language: str = "ja"
    business_summary: str = ""
    company_positioning: str = ""
    site_positioning: str = ""
    core_services: list[str] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    target_customers: list[str] = Field(default_factory=list)
    brand_voice: list[str] = Field(default_factory=list)
    avoid_expressions: list[str] = Field(default_factory=list)
    preferred_messages: list[str] = Field(default_factory=list)
    style_rules: list[str] = Field(default_factory=list)
    primary_post_types: list[str] = Field(default_factory=list)
    primary_categories: list[str] = Field(default_factory=list)
    site_operational_notes: list[str] = Field(default_factory=list)

    @field_validator(
        "company_name",
        "site_name",
        "site_url",
        "language",
        "business_summary",
        "company_positioning",
        "site_positioning",
        mode="before",
    )
    @classmethod
    def _normalize_str_fields(cls, value: Any, info: ValidationInfo) -> str:
        default = "ja" if info.field_name == "language" else ""
        normalized = _normalize_text(value, default=default)
        if info.field_name == "language" and not normalized:
            return "ja"
        return normalized

    @field_validator(
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
        mode="before",
    )
    @classmethod
    def _normalize_list_fields(cls, value: Any) -> list[str]:
        return _normalize_string_list(value)

    @field_validator("schema_version", mode="before")
    @classmethod
    def _normalize_schema_version(cls, value: Any) -> int:
        try:
            version = int(value)
        except (TypeError, ValueError):
            version = CURRENT_COMPANY_MEMORY_SCHEMA_VERSION
        return max(version, 1)


COMPANY_MEMORY_MUTABLE_FIELDS = frozenset(
    field_name
    for field_name in CompanyMemoryContent.model_fields
    if field_name != "schema_version"
)


def normalize_company_memory(raw_json: Mapping[str, Any] | None) -> CompanyMemoryContent:
    """DBの raw JSON を最新 schema へ寄せる。

    将来 shape を変更した際は、この関数で旧キー吸収や型変換を行う。
    既存 row は read 時にここを通し、次回保存時に最新 shape へ自然更新する。
    """
    payload = dict(raw_json or {})
    payload["schema_version"] = CURRENT_COMPANY_MEMORY_SCHEMA_VERSION
    return CompanyMemoryContent.model_validate(payload)


def canonicalize_company_memory(raw_json: Mapping[str, Any] | None) -> dict[str, Any]:
    """保存用の canonical JSON に正規化する。"""
    normalized = normalize_company_memory(raw_json)
    return normalized.model_dump()


def normalize_company_memory_update_fields(
    raw_fields: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """部分更新用 fields を正規化する。

    許可キーだけを受け付け、未指定キーは保存時に current JSON を保持する。
    将来フィールド追加時は CompanyMemoryContent の定義更新だけで許可対象へ追従できる。
    """
    if raw_fields is None:
        return {}
    if not isinstance(raw_fields, Mapping):
        raise ValueError("fields はオブジェクトである必要があります")

    normalized_fields: dict[str, Any] = {}
    unknown_keys: list[str] = []
    for key, value in raw_fields.items():
        if key not in COMPANY_MEMORY_MUTABLE_FIELDS:
            unknown_keys.append(str(key))
            continue
        normalized_fields[str(key)] = value

    if unknown_keys:
        joined = ", ".join(sorted(unknown_keys))
        raise ValueError(f"未知の fields キーが含まれています: {joined}")

    return normalized_fields
