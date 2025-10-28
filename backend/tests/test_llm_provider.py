# -*- coding: utf-8 -*-
import contextlib
from typing import Iterator

import pytest

from app.core import llm_provider
from app.core.config import settings


@contextlib.contextmanager
def override_settings(**overrides) -> Iterator[None]:
    """Temporarily patch attributes on the global settings object."""
    original_values = {}
    for key, value in overrides.items():
        original_values[key] = getattr(settings, key)
        setattr(settings, key, value)
    try:
        yield
    finally:
        for key, value in original_values.items():
            setattr(settings, key, value)


def test_get_writing_model_openai_backend():
    with override_settings(
        default_llm_backend="openai",
        writing_llm_backend="openai",
        writing_model="gpt-4.1-mini",
    ):
        assert llm_provider.get_writing_model() == "gpt-4.1-mini"


def test_get_writing_model_litellm_sdk_prefix_added():
    with override_settings(
        default_llm_backend="openai",
        writing_llm_backend="litellm_sdk",
        writing_litellm_provider="anthropic",
        writing_model="claude-sonnet-4-5-20250929",
    ):
        assert (
            llm_provider.get_writing_model()
            == "litellm/anthropic/claude-sonnet-4-5-20250929"
        )


def test_get_writing_model_litellm_sdk_existing_prefix():
    with override_settings(
        writing_llm_backend="litellm_sdk",
        writing_litellm_provider="anthropic",
        writing_model="litellm/anthropic/claude-sonnet-4-5-20250929",
    ):
        assert (
            llm_provider.get_writing_model()
            == "litellm/anthropic/claude-sonnet-4-5-20250929"
        )


def test_get_writing_model_litellm_sdk_provider_missing():
    with override_settings(
        writing_llm_backend="litellm_sdk",
        writing_litellm_provider="",
        writing_model="claude-sonnet-4-5-20250929",
    ):
        with pytest.raises(ValueError):
            llm_provider.get_writing_model()


def test_get_editing_model_inherits_defaults():
    with override_settings(
        default_llm_backend="litellm_sdk",
        default_litellm_provider="anthropic",
        editing_llm_backend="",
        editing_litellm_provider="",
        editing_model="claude-sonnet-4-5-20250929",
    ):
        assert (
            llm_provider.get_editing_model()
            == "litellm/anthropic/claude-sonnet-4-5-20250929"
        )


def test_get_editing_model_specific_provider_overrides_default():
    with override_settings(
        default_llm_backend="litellm_sdk",
        default_litellm_provider="anthropic",
        editing_llm_backend="litellm_sdk",
        editing_litellm_provider="gemini",
        editing_model="gemini-2.5-pro",
    ):
        assert (
            llm_provider.get_editing_model()
            == "litellm/gemini/gemini-2.5-pro"
        )
