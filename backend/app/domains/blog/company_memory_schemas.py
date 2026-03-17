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


def normalize_company_memory(raw_json: Mapping[str, Any] | None) -> CompanyMemoryContent:
    """DBの raw JSON を最新 schema へ寄せる。"""
    payload = dict(raw_json or {})
    payload["schema_version"] = CURRENT_COMPANY_MEMORY_SCHEMA_VERSION
    return CompanyMemoryContent.model_validate(payload)


def canonicalize_company_memory(raw_json: Mapping[str, Any] | None) -> dict[str, Any]:
    """保存用の canonical JSON に正規化する。"""
    normalized = normalize_company_memory(raw_json)
    return normalized.model_dump()
