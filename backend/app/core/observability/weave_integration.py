# -*- coding: utf-8 -*-
"""
Centralized helpers for wiring Weave into the OpenAI Agents SDK runtime.
"""

from __future__ import annotations

import logging
import os
import threading
from typing import Any, Dict, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

_WEAVE_LOCK = threading.Lock()
_WEAVE_INITIALIZED = False


def _ensure_wandb_api_key() -> None:
    """Populate WANDB_API_KEY if provided via WEAVE_API_KEY env."""
    if settings.weave_api_key and not os.getenv("WANDB_API_KEY"):
        os.environ["WANDB_API_KEY"] = settings.weave_api_key


def _resolve_entity_and_project(
    override_project: Optional[str] = None,
) -> tuple[Optional[str], str]:
    """Return the (entity, project) tuple, allowing `entity/project` syntax."""
    project = override_project or settings.weave_project_name or "seo-article-generation"
    entity = settings.weave_entity or None

    if not entity and "/" in project:
        maybe_entity, maybe_project = project.split("/", 1)
        if maybe_entity and maybe_project:
            entity = maybe_entity.strip() or None
            project = maybe_project.strip() or project

    return entity, project


def build_weave_metadata_stub(
    trace_id: str,
    *,
    display_name: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Build a consistent Weave metadata dictionary that can be serialized inside ArticleContext.
    """
    base_url = (settings.weave_base_url or "https://wandb.ai").rstrip("/")
    entity, project = _resolve_entity_and_project()
    project_path = f"{entity}/{project}" if entity else project
    project_url = f"{base_url}/{project_path}/traces"
    trace_url = f"{project_url}?traceId={trace_id}"

    metadata: Dict[str, Any] = {
        "provider": "weave",
        "trace_id": trace_id,
        "project": project,
        "entity": entity,
        "project_url": project_url,
        "trace_url": trace_url,
        "tags": settings.weave_default_tags,
    }
    if display_name:
        metadata["display_name"] = display_name
    if extra:
        metadata.update(extra)
    return metadata


def init_weave_tracing(project_name: Optional[str] = None) -> bool:
    """
    Initialize Weave tracing integration with the OpenAI Agents SDK.
    Returns True when initialization succeeds (or was already completed).
    """
    global _WEAVE_INITIALIZED

    if not settings.weave_enabled:
        logger.debug("Weave tracing disabled via configuration.")
        return False

    if _WEAVE_INITIALIZED:
        return True

    with _WEAVE_LOCK:
        if _WEAVE_INITIALIZED:
            return True

        try:
            import weave  # type: ignore
            from weave.integrations.openai_agents.openai_agents import WeaveTracingProcessor  # type: ignore
            from agents import add_trace_processor, set_trace_processors  # type: ignore
        except ImportError as exc:
            logger.warning("Weave integration skipped (missing dependency): %s", exc)
            return False

        try:
            _ensure_wandb_api_key()

            entity, base_project = _resolve_entity_and_project(project_name)
            project_slug = f"{entity}/{base_project}" if entity else base_project

            weave.init(
                project_name=project_slug,
            )
            logger.info("Weave initialized with project=%s", project_slug)

            processor = WeaveTracingProcessor()
            if settings.weave_replace_default_tracer:
                set_trace_processors([processor])
                logger.info("Weave tracing processor registered as the sole trace processor.")
            else:
                add_trace_processor(processor)
                logger.info("Weave tracing processor added alongside existing processors.")

            _WEAVE_INITIALIZED = True
            return True
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.exception("Failed to initialize Weave tracing: %s", exc)
            return False
