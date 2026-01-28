# -*- coding: utf-8 -*-
"""
WordPress MCP Client
動的認証対応版 - DBに保存されたサイト情報を使用して接続

参考: shintairiku-ai-agent/backend/app/infrastructure/chatkit/wordpress_mcp_client.py

優先順位:
1. site_id が指定されている場合 → そのサイトのクレデンシャルを使用
2. site_id がない場合 → アクティブサイトのクレデンシャルを使用
"""
import json
import logging
from typing import Any, Dict, Optional

import httpx

from app.common.database import supabase
from .crypto_service import get_crypto_service

logger = logging.getLogger(__name__)

# MCP プロトコルバージョン
MCP_PROTOCOL_VERSION = "2024-11-05"

# タイムアウト設定
MCP_TIMEOUT = 60.0  # 通常リクエスト
MCP_LONG_TIMEOUT = 300.0  # 長時間リクエスト（メディアアップロードなど）


class MCPError(Exception):
    """MCP通信エラー"""

    def __init__(self, message: str, code: Optional[int] = None):
        self.message = message
        self.code = code
        super().__init__(message)


class WordPressMcpClient:
    """WordPress MCPクライアント（動的認証対応）"""

    def __init__(self, site_id: Optional[str] = None, user_id: Optional[str] = None):
        """
        Args:
            site_id: 接続するWordPressサイトのID（省略時はアクティブサイトを使用）
            user_id: ユーザーID（サイト検索時に使用）
        """
        self._site_id = site_id
        self._user_id = user_id
        self._url: Optional[str] = None
        self._auth: Optional[str] = None
        self._session_id: Optional[str] = None
        self._request_id = 0
        self._credentials_loaded = False

    async def _load_credentials(self) -> tuple[str, str]:
        """
        クレデンシャルを読み込む

        Returns:
            (mcp_endpoint, authorization_header) のタプル
        """
        crypto = get_crypto_service()

        # site_id が指定されている場合はそのサイトを使用
        if self._site_id:
            result = supabase.table("wordpress_sites").select(
                "site_url, mcp_endpoint, encrypted_credentials"
            ).eq("id", self._site_id).single().execute()

            if result.data:
                credentials = crypto.decrypt_credentials(result.data["encrypted_credentials"])
                logger.info(f"Using WordPress site: {result.data['site_url']} (ID: {self._site_id[:8]}...)")
                return result.data["mcp_endpoint"], f"Bearer {credentials['access_token']}"
            else:
                logger.warning(f"Site not found: {self._site_id}, falling back to active site")

        # site_id がない場合はアクティブサイトを検索
        query = supabase.table("wordpress_sites").select(
            "id, site_url, mcp_endpoint, encrypted_credentials"
        ).eq("is_active", True)

        if self._user_id:
            query = query.eq("user_id", self._user_id)

        result = query.limit(1).execute()

        if result.data and len(result.data) > 0:
            active_site = result.data[0]
            credentials = crypto.decrypt_credentials(active_site["encrypted_credentials"])
            logger.info(f"Using active WordPress site: {active_site['site_url']}")
            return active_site["mcp_endpoint"], f"Bearer {credentials['access_token']}"

        raise MCPError("No WordPress site available. Please configure a WordPress site first.")

    async def initialize(self) -> None:
        """MCPセッションを初期化"""
        # クレデンシャルを読み込み
        if not self._credentials_loaded:
            self._url, self._auth = await self._load_credentials()
            self._credentials_loaded = True

        self._request_id += 1

        async with httpx.AsyncClient(timeout=MCP_TIMEOUT) as client:
            response = await client.post(
                self._url,
                headers={
                    "Authorization": self._auth,
                    "Content-Type": "application/json",
                },
                json={
                    "jsonrpc": "2.0",
                    "method": "initialize",
                    "params": {
                        "protocolVersion": MCP_PROTOCOL_VERSION,
                        "capabilities": {},
                        "clientInfo": {
                            "name": "marketing-automation-blog-ai",
                            "version": "1.0.0",
                        },
                    },
                    "id": self._request_id,
                },
            )

            # セッションIDを取得（大文字小文字両対応）
            session_id = (
                response.headers.get("mcp-session-id")
                or response.headers.get("Mcp-Session-Id")
            )
            if not session_id:
                raise MCPError("Failed to get MCP session ID")

            self._session_id = session_id
            logger.info(f"WordPress MCP initialized with session: {session_id[:8]}...")

    async def call_tool(
        self,
        tool_name: str,
        args: Dict[str, Any] | None = None,
        timeout: float = MCP_TIMEOUT,
    ) -> str:
        """
        MCPツールを呼び出す

        Args:
            tool_name: ツール名
            args: ツール引数
            timeout: タイムアウト（秒）

        Returns:
            ツール実行結果（JSON文字列）
        """
        if not self._session_id:
            await self.initialize()

        self._request_id += 1
        args = args or {}

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                self._url,
                headers={
                    "Authorization": self._auth,
                    "Content-Type": "application/json",
                    "Mcp-Session-Id": self._session_id,
                },
                json={
                    "jsonrpc": "2.0",
                    "method": "tools/call",
                    "params": {
                        "name": tool_name,
                        "arguments": args,
                    },
                    "id": self._request_id,
                },
            )

            data = response.json()

            if "error" in data:
                error = data["error"]
                # セッションエラーの場合は再接続を試みる
                if error.get("code") == -32600 or "session" in str(error.get("message", "")).lower():
                    logger.warning("MCP session error, attempting to reconnect")
                    self._session_id = None
                    await self.initialize()
                    return await self.call_tool(tool_name, args, timeout)

                raise MCPError(error.get("message", "Unknown MCP error"), error.get("code"))

            result = data.get("result", {})

            # structuredContentがあればそれを返す、なければtextを返す
            if result.get("structuredContent"):
                return json.dumps(result["structuredContent"], ensure_ascii=False, indent=2)

            content = result.get("content", [])
            if content and len(content) > 0 and content[0].get("text"):
                return content[0]["text"]

            return json.dumps(result, ensure_ascii=False)

    async def test_connection(self) -> Dict[str, Any]:
        """
        接続テスト

        Returns:
            {
                "success": bool,
                "message": str,
                "server_info": dict | None,
            }
        """
        try:
            await self.initialize()
            site_info_str = await self.call_tool("wp-mcp-get-site-info", {})
            site_info = json.loads(site_info_str) if isinstance(site_info_str, str) else site_info_str

            return {
                "success": True,
                "message": "接続成功",
                "server_info": {
                    "site_name": site_info.get("name"),
                    "site_url": site_info.get("url"),
                },
            }
        except MCPError as e:
            return {
                "success": False,
                "message": f"MCP接続エラー: {e.message}",
                "server_info": None,
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"接続エラー: {str(e)}",
                "server_info": None,
            }


# サイトIDごとのクライアントキャッシュ
_mcp_clients: Dict[Optional[str], WordPressMcpClient] = {}


def get_wordpress_mcp_client(
    site_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> WordPressMcpClient:
    """
    WordPress MCPクライアントを取得

    Args:
        site_id: 接続するWordPressサイトのID（省略時はアクティブサイトを使用）
        user_id: ユーザーID（サイト検索時に使用）

    Returns:
        WordPressMcpClient インスタンス
    """
    global _mcp_clients

    # site_id ごとにクライアントをキャッシュ
    cache_key = site_id
    if cache_key not in _mcp_clients:
        _mcp_clients[cache_key] = WordPressMcpClient(site_id, user_id)

    return _mcp_clients[cache_key]


def clear_mcp_client_cache(site_id: Optional[str] = None) -> None:
    """
    MCPクライアントキャッシュをクリア

    Args:
        site_id: クリアするサイトID（省略時は全キャッシュをクリア）
    """
    global _mcp_clients

    if site_id is None:
        _mcp_clients.clear()
        logger.info("Cleared all MCP client cache")
    elif site_id in _mcp_clients:
        del _mcp_clients[site_id]
        logger.info(f"Cleared MCP client cache for site: {site_id[:8]}...")


async def call_wordpress_mcp_tool(
    tool_name: str,
    args: Dict[str, Any] | None = None,
    site_id: Optional[str] = None,
    user_id: Optional[str] = None,
    timeout: float = MCP_TIMEOUT,
) -> str:
    """
    WordPress MCPツールを呼び出す便利関数

    Args:
        tool_name: ツール名
        args: ツール引数
        site_id: 接続するWordPressサイトのID（省略時はアクティブサイトを使用）
        user_id: ユーザーID
        timeout: タイムアウト（秒）

    Returns:
        ツールの実行結果（JSON文字列）
    """
    client = get_wordpress_mcp_client(site_id, user_id)
    return await client.call_tool(tool_name, args, timeout)


# 後方互換性のためのエイリアス
class WordPressMcpService(WordPressMcpClient):
    """後方互換性のためのエイリアス（非推奨）"""

    @classmethod
    async def from_site_credentials(
        cls,
        mcp_endpoint: str,
        encrypted_credentials: str,
    ) -> "WordPressMcpService":
        """
        暗号化された認証情報からサービスを作成（後方互換性）
        """
        crypto = get_crypto_service()
        credentials = crypto.decrypt_credentials(encrypted_credentials)

        instance = cls()
        instance._url = mcp_endpoint
        instance._auth = f"Bearer {credentials['access_token']}"
        instance._credentials_loaded = True

        return instance
