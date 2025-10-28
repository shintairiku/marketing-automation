# -*- coding: utf-8 -*-
"""Helpers for selecting LLM backends and model identifiers."""

from __future__ import annotations

from typing import Optional

from app.core.config import settings


class LLMBackend:
    """Supported backend identifiers."""

    OPENAI = "openai"
    LITELLM_SDK = "litellm_sdk"
    LITELLM_PROXY = "litellm_proxy"

    @classmethod
    def normalize(cls, backend: Optional[str]) -> str:
        value = (backend or "").strip().lower()
        if value in {cls.OPENAI, cls.LITELLM_SDK, cls.LITELLM_PROXY}:
            return value
        return cls.OPENAI


def _litellm_model_identifier(model_name: str, provider: str) -> str:
    """Compose a LiteLLM model identifier (litellm/<provider>/<model>).

    The helper keeps user-provided identifiers intact when they already
    include the ``litellm/`` prefix to avoid double wrapping.
    """
    if model_name.startswith("litellm/"):
        return model_name
    provider_value = provider.strip()
    if not provider_value:
        raise ValueError("Litellm provider is required when using litellm_sdk backend.")
    return f"litellm/{provider_value}/{model_name}"


def _resolve_backend(
    explicit_backend: Optional[str],
) -> str:
    """Return the backend to use, falling back to the default setting."""
    backend = LLMBackend.normalize(explicit_backend)
    if backend != LLMBackend.OPENAI:
        return backend
    return LLMBackend.normalize(settings.default_llm_backend)


def _resolve_provider(
    explicit_provider: Optional[str],
) -> str:
    """Resolve LiteLLM provider with default fallback."""
    candidate = (explicit_provider or settings.default_litellm_provider or "").strip()
    return candidate


def _select_model(
    model_name: str,
    backend: str,
    litellm_provider: str,
) -> str:
    """Convert a logical model name into the identifier consumed by Agents SDK."""
    if not model_name:
        raise ValueError("Model name must be provided for agent configuration.")
    if backend == LLMBackend.LITELLM_SDK:
        return _litellm_model_identifier(model_name, litellm_provider)
    # OPENAI と LiteLLM proxy の場合は元のモデル名をそのまま返す
    return model_name


def get_writing_model() -> str:
    """Model identifier for writing-focused agents."""
    backend = _resolve_backend(settings.writing_llm_backend)
    provider = _resolve_provider(settings.writing_litellm_provider)
    return _select_model(settings.writing_model, backend, provider)


def get_editing_model() -> str:
    """Model identifier for editing/QA agents."""
    backend = _resolve_backend(settings.editing_llm_backend)
    provider = _resolve_provider(settings.editing_litellm_provider or settings.writing_litellm_provider)
    return _select_model(settings.editing_model, backend, provider)

