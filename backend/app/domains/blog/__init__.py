# -*- coding: utf-8 -*-
"""
Blog AI Domain

WordPress MCPと連携してブログ記事を生成するドメイン。
"""

__all__ = ["blog_router"]


def __getattr__(name: str):
    if name == "blog_router":
        from .endpoints import router as blog_router

        return blog_router
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
