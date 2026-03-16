# -*- coding: utf-8 -*-
"""
Blog Memory Embedding Job

`blog_memory_meta` の embedding 未投入/更新遅延レコードに対して
埋め込み更新を行う後段ジョブ。
"""

from __future__ import annotations

import logging
from typing import Optional

from app.domains.blog.services.memory_service import get_blog_memory_service

logger = logging.getLogger(__name__)


async def run_blog_memory_embedding_job(limit: Optional[int] = None) -> int:
    """Blog Memory embedding バッチを実行し、更新件数を返す。"""
    service = get_blog_memory_service()
    updated = await service.run_embedding_batch(limit=limit)
    logger.info("Blog memory embedding job updated %s rows", updated)
    return updated

