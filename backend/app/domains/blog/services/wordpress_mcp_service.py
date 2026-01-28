# -*- coding: utf-8 -*-
"""
Blog AI Domain - WordPress MCP Service

WordPress MCPサーバーとの通信を管理するサービス
"""

import asyncio
from typing import Any, Dict, List, Optional

import logging

import httpx

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


class WordPressMcpService:
    """
    WordPress MCPサーバーとの通信を管理するサービス

    MCP（Model Context Protocol）を使用してWordPressと通信し、
    記事の取得・作成・メディアアップロードなどを行う。
    """

    def __init__(
        self,
        mcp_endpoint: str,
        access_token: str,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
    ):
        """
        Args:
            mcp_endpoint: MCPサーバーのエンドポイントURL
            access_token: Bearer認証用アクセストークン
            api_key: Basic認証用APIキー（オプション）
            api_secret: Basic認証用APIシークレット（オプション）
        """
        self.mcp_endpoint = mcp_endpoint
        self.access_token = access_token
        self.api_key = api_key
        self.api_secret = api_secret
        self.session_id: Optional[str] = None
        self._request_id = 0

    @classmethod
    async def from_site_credentials(
        cls,
        mcp_endpoint: str,
        encrypted_credentials: str,
    ) -> "WordPressMcpService":
        """
        暗号化された認証情報からサービスを作成

        Args:
            mcp_endpoint: MCPエンドポイント
            encrypted_credentials: 暗号化された認証情報

        Returns:
            WordPressMcpServiceインスタンス
        """
        crypto = get_crypto_service()
        credentials = crypto.decrypt_credentials(encrypted_credentials)

        return cls(
            mcp_endpoint=mcp_endpoint,
            access_token=credentials["access_token"],
            api_key=credentials.get("api_key"),
            api_secret=credentials.get("api_secret"),
        )

    def _get_headers(self) -> Dict[str, str]:
        """リクエストヘッダーを取得"""
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        return headers

    def _next_request_id(self) -> int:
        """次のリクエストIDを取得"""
        self._request_id += 1
        return self._request_id

    async def connect(self) -> Dict[str, Any]:
        """
        MCPセッションを初期化

        Returns:
            サーバー情報
        """
        logger.info(f"MCP接続を開始: {self.mcp_endpoint}")

        async with httpx.AsyncClient(timeout=MCP_TIMEOUT) as client:
            response = await client.post(
                self.mcp_endpoint,
                headers=self._get_headers(),
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
                    "id": self._next_request_id(),
                },
            )

            # セッションIDを取得（大文字小文字両対応）
            self.session_id = (
                response.headers.get("Mcp-Session-Id")
                or response.headers.get("mcp-session-id")
            )

            result = response.json()

            if "error" in result:
                raise MCPError(
                    result["error"].get("message", "MCP初期化エラー"),
                    result["error"].get("code"),
                )

            logger.info(f"MCP接続成功: session_id={self.session_id}")
            return result.get("result", {})

    async def _request(
        self,
        method: str,
        params: Dict[str, Any],
        timeout: float = MCP_TIMEOUT,
    ) -> Dict[str, Any]:
        """
        MCPリクエストを送信

        Args:
            method: MCPメソッド名
            params: パラメータ
            timeout: タイムアウト（秒）

        Returns:
            レスポンス結果
        """
        if not self.session_id:
            await self.connect()

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                self.mcp_endpoint,
                headers=self._get_headers(),
                json={
                    "jsonrpc": "2.0",
                    "method": method,
                    "params": params,
                    "id": self._next_request_id(),
                },
            )

            result = response.json()

            if "error" in result:
                error = result["error"]
                # セッションエラーの場合は再接続を試みる
                if error.get("code") == -32600 or "session" in str(error.get("message", "")).lower():
                    logger.warning("MCPセッションエラー、再接続を試みます")
                    await self.connect()
                    return await self._request(method, params, timeout)

                raise MCPError(
                    error.get("message", "MCPリクエストエラー"),
                    error.get("code"),
                )

            return result.get("result", {})

    async def list_tools(self) -> List[Dict[str, Any]]:
        """利用可能なツール一覧を取得"""
        result = await self._request("tools/list", {})
        return result.get("tools", [])

    async def call_tool(
        self,
        name: str,
        arguments: Dict[str, Any],
        timeout: float = MCP_TIMEOUT,
    ) -> Dict[str, Any]:
        """
        MCPツールを呼び出す

        Args:
            name: ツール名
            arguments: 引数
            timeout: タイムアウト（秒）

        Returns:
            ツール実行結果
        """
        logger.info(f"MCPツール呼び出し: {name}")
        return await self._request(
            "tools/call",
            {"name": name, "arguments": arguments},
            timeout,
        )

    # =====================================================
    # WordPress固有のヘルパーメソッド
    # =====================================================

    async def get_site_info(self) -> Dict[str, Any]:
        """サイト情報を取得"""
        return await self.call_tool("wp-mcp-get-site-info", {})

    async def get_post(self, post_id: int) -> Dict[str, Any]:
        """投稿を取得"""
        return await self.call_tool("wp-mcp-get-post", {"post_id": post_id})

    async def get_post_by_url(self, url: str) -> Dict[str, Any]:
        """URLから投稿を取得"""
        return await self.call_tool("wp-mcp-get-post-by-url", {"url": url})

    async def get_recent_posts(
        self,
        limit: int = 10,
        post_type: str = "post",
    ) -> List[Dict[str, Any]]:
        """最近の投稿を取得"""
        result = await self.call_tool(
            "wp-mcp-get-recent-posts",
            {"limit": limit, "post_type": post_type},
        )
        return result.get("posts", [])

    async def create_draft_post(
        self,
        title: str,
        content: str,
        excerpt: Optional[str] = None,
        categories: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        featured_image_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        下書き投稿を作成

        Args:
            title: タイトル
            content: 本文（Gutenbergブロック形式推奨）
            excerpt: 抜粋
            categories: カテゴリ
            tags: タグ
            featured_image_id: アイキャッチ画像のメディアID

        Returns:
            作成された投稿情報
        """
        arguments = {
            "title": title,
            "content": content,
            "status": "draft",
        }

        if excerpt:
            arguments["excerpt"] = excerpt
        if categories:
            arguments["categories"] = categories
        if tags:
            arguments["tags"] = tags
        if featured_image_id:
            arguments["featured_media"] = featured_image_id

        return await self.call_tool("wp-mcp-create-draft-post", arguments)

    async def upload_media(
        self,
        file_data: bytes,
        filename: str,
        mime_type: str = "image/jpeg",
        alt_text: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        メディアをアップロード

        Args:
            file_data: ファイルデータ（バイト）
            filename: ファイル名
            mime_type: MIMEタイプ
            alt_text: 代替テキスト

        Returns:
            アップロードされたメディア情報
        """
        import base64

        arguments = {
            "file_data": base64.b64encode(file_data).decode("utf-8"),
            "filename": filename,
            "mime_type": mime_type,
        }

        if alt_text:
            arguments["alt_text"] = alt_text

        return await self.call_tool(
            "wp-mcp-upload-media",
            arguments,
            timeout=MCP_LONG_TIMEOUT,
        )

    async def get_categories(self) -> List[Dict[str, Any]]:
        """カテゴリ一覧を取得"""
        result = await self.call_tool("wp-mcp-get-categories", {})
        return result.get("categories", [])

    async def get_tags(self) -> List[Dict[str, Any]]:
        """タグ一覧を取得"""
        result = await self.call_tool("wp-mcp-get-tags", {})
        return result.get("tags", [])

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
            server_info = await self.connect()
            site_info = await self.get_site_info()

            return {
                "success": True,
                "message": "接続成功",
                "server_info": {
                    "name": server_info.get("serverInfo", {}).get("name"),
                    "version": server_info.get("serverInfo", {}).get("version"),
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
