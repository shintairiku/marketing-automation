#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CLI wrapper that proxies to the production article agent toolkit.

This file exists to provide a stable entrypoint for local testing while the
actual implementation lives in `app.domains.seo_article.services.article_agent_service`.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Ensure backend/ is importable so the shared service module can be reused.
BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.append(str(BACKEND_DIR))

from app.domains.seo_article.services.article_agent_service import (  # noqa: E402
    AppContext,
    FactCheckReport,
    build_fact_check_agent,
    build_model_settings,
    build_parser,
    build_text_edit_agent,
    create_web_search_tool,
    ensure_session_trace,
    format_edit_handoff_prompt,
    main,
    make_run_config,
    read_article,
    read_file,
    run_fact_check_cli,
    run_patch_cli,
)

__all__ = [
    "AppContext",
    "FactCheckReport",
    "build_fact_check_agent",
    "build_model_settings",
    "build_parser",
    "build_text_edit_agent",
    "create_web_search_tool",
    "ensure_session_trace",
    "format_edit_handoff_prompt",
    "main",
    "make_run_config",
    "read_article",
    "read_file",
    "run_fact_check_cli",
    "run_patch_cli",
]


if __name__ == "__main__":
    asyncio.run(main())
