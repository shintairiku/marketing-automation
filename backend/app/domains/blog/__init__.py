# -*- coding: utf-8 -*-
"""
Blog AI Domain

WordPress MCPと連携してブログ記事を生成するドメイン。
OpenAI Agents SDK + Responses APIを使用。
"""

from .endpoints import router as blog_router

__all__ = ["blog_router"]
