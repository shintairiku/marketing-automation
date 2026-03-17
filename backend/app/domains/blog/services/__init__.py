# -*- coding: utf-8 -*-
"""
Blog AI Domain - Services
"""

__all__ = [
    "CryptoService",
    "get_crypto_service",
    "WordPressMcpService",
    "WordPressMcpClient",
    "MCPError",
    "get_wordpress_mcp_client",
    "call_wordpress_mcp_tool",
    "clear_mcp_client_cache",
    "BlogGenerationService",
    "get_generation_service",
]


def __getattr__(name: str):
    if name in {"CryptoService", "get_crypto_service"}:
        from .crypto_service import CryptoService, get_crypto_service

        return {"CryptoService": CryptoService, "get_crypto_service": get_crypto_service}[name]
    if name in {
        "WordPressMcpService",
        "WordPressMcpClient",
        "MCPError",
        "get_wordpress_mcp_client",
        "call_wordpress_mcp_tool",
        "clear_mcp_client_cache",
    }:
        from .wordpress_mcp_service import (
            WordPressMcpClient,
            WordPressMcpService,
            MCPError,
            get_wordpress_mcp_client,
            call_wordpress_mcp_tool,
            clear_mcp_client_cache,
        )

        return {
            "WordPressMcpService": WordPressMcpService,
            "WordPressMcpClient": WordPressMcpClient,
            "MCPError": MCPError,
            "get_wordpress_mcp_client": get_wordpress_mcp_client,
            "call_wordpress_mcp_tool": call_wordpress_mcp_tool,
            "clear_mcp_client_cache": clear_mcp_client_cache,
        }[name]
    if name in {"BlogGenerationService", "get_generation_service"}:
        from .generation_service import BlogGenerationService, get_generation_service

        return {
            "BlogGenerationService": BlogGenerationService,
            "get_generation_service": get_generation_service,
        }[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
