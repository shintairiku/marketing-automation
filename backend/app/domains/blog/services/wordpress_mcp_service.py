# -*- coding: utf-8 -*-
"""
WordPress MCP Client
動的認証対応版 - DBに保存されたサイト情報を使用して接続

参考: shintairiku-ai-agent/backend/app/infrastructure/chatkit/wordpress_mcp_client.py

優先順位:
1. site_id が指定されている場合 → そのサイトのクレデンシャルを使用
2. site_id がない場合 → アクティブサイトのクレデンシャルを使用
"""
import contextvars
import hashlib
import json
import logging
import time
from typing import Any, Dict, List, Optional

import httpx

from app.common.database import supabase
from .crypto_service import get_crypto_service

# コンテキスト変数: エージェント実行中にsite_id/user_id/process_idを伝播
_current_site_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "_current_site_id", default=None
)
_current_user_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "_current_user_id", default=None
)
_current_process_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "_current_process_id", default=None
)

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

        # ユーザー個人のサイトが見つからない場合、組織のアクティブサイトをフォールバック検索
        if self._user_id:
            org_memberships = supabase.table("organization_members").select(
                "organization_id"
            ).eq("user_id", self._user_id).execute()

            if org_memberships.data:
                org_ids = [m["organization_id"] for m in org_memberships.data]
                org_site_result = supabase.table("wordpress_sites").select(
                    "id, site_url, mcp_endpoint, encrypted_credentials"
                ).in_("organization_id", org_ids).eq("is_active", True).limit(1).execute()

                if org_site_result.data and len(org_site_result.data) > 0:
                    org_site = org_site_result.data[0]
                    credentials = crypto.decrypt_credentials(org_site["encrypted_credentials"])
                    logger.info(f"Using organization WordPress site: {org_site['site_url']}")
                    return org_site["mcp_endpoint"], f"Bearer {credentials['access_token']}"

        raise MCPError("No WordPress site available. Please configure a WordPress site first.")

    async def initialize(self) -> None:
        """MCPセッションを初期化"""
        # クレデンシャルを読み込み
        if not self._credentials_loaded:
            self._url, self._auth = await self._load_credentials()
            self._credentials_loaded = True

            # デバッグ: トークンのハッシュをログに記録して照合可能にする
            if self._auth and self._auth.startswith("Bearer "):
                token = self._auth[7:]  # "Bearer " を除去
                token_hash = hashlib.sha256(token.encode()).hexdigest()
                logger.info(
                    f"MCP認証トークン読み込み完了: token_prefix={token[:8]}..., "
                    f"token_sha256={token_hash[:16]}..., "
                    f"token_len={len(token)}"
                )

        self._request_id += 1

        logger.info(f"MCP初期化リクエスト: url={self._url}")

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

            # HTTPステータスコードをチェック
            if response.status_code != 200:
                body_text = response.text[:500]
                logger.error(
                    f"MCP初期化HTTPエラー: status={response.status_code}, "
                    f"url={self._url}, body={body_text}"
                )
                raise MCPError(
                    f"MCP endpoint returned HTTP {response.status_code}: {body_text}",
                    code=response.status_code,
                )

            # JSON-RPCエラーをチェック
            try:
                data = response.json()
                if "error" in data:
                    error = data["error"]
                    error_msg = error.get("message", "Unknown MCP error")
                    logger.error(f"MCP初期化JSON-RPCエラー: {error}")
                    raise MCPError(error_msg, error.get("code"))
            except (json.JSONDecodeError, ValueError):
                pass  # JSON-RPCレスポンスでない場合はスキップ

            # セッションIDを取得（大文字小文字両対応）
            session_id = (
                response.headers.get("mcp-session-id")
                or response.headers.get("Mcp-Session-Id")
            )
            if not session_id:
                logger.error(
                    f"MCP session ID not found in headers. "
                    f"Response headers: {dict(response.headers)}, "
                    f"Response body: {response.text[:300]}"
                )
                raise MCPError("Failed to get MCP session ID: header not present in response")

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

            # HTTPステータスコードをチェック
            if response.status_code != 200:
                body_text = response.text[:500]
                logger.error(
                    f"MCPツール呼び出しHTTPエラー: tool={tool_name}, "
                    f"status={response.status_code}, body={body_text}"
                )
                raise MCPError(
                    f"MCP endpoint returned HTTP {response.status_code}: {body_text}",
                    code=response.status_code,
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
        包括的な接続テスト - 各ステップを個別にテストして詳細結果を返す

        Returns:
            {
                "success": bool,
                "message": str,
                "server_info": dict | None,
                "steps": list[dict],
            }
        """
        steps: List[Dict[str, Any]] = []
        server_info = None
        all_success = True

        # ---- Step 1: クレデンシャル読み込み ----
        t0 = time.monotonic()
        try:
            self._url, self._auth = await self._load_credentials()
            self._credentials_loaded = True
            duration = int((time.monotonic() - t0) * 1000)

            token = self._auth[7:] if self._auth.startswith("Bearer ") else self._auth
            token_hash = hashlib.sha256(token.encode()).hexdigest()

            steps.append({
                "name": "credentials",
                "label": "クレデンシャル読み込み",
                "status": "success",
                "message": "暗号化されたトークンの復号に成功",
                "detail": f"endpoint={self._url}, token_prefix={token[:8]}..., sha256={token_hash[:16]}...",
                "duration_ms": duration,
            })
        except Exception as e:
            duration = int((time.monotonic() - t0) * 1000)
            steps.append({
                "name": "credentials",
                "label": "クレデンシャル読み込み",
                "status": "error",
                "message": f"クレデンシャル読み込み失敗: {str(e)}",
                "detail": None,
                "duration_ms": duration,
            })
            return {
                "success": False,
                "message": f"クレデンシャル読み込み失敗: {str(e)}",
                "server_info": None,
                "steps": steps,
            }

        # ---- Step 2: MCP エンドポイント到達性 ----
        t0 = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                # OPTIONS/HEADではなくPOSTで疎通確認（initializeの前段）
                response = await client.post(
                    self._url,
                    headers={
                        "Content-Type": "application/json",
                    },
                    json={
                        "jsonrpc": "2.0",
                        "method": "initialize",
                        "params": {
                            "protocolVersion": MCP_PROTOCOL_VERSION,
                            "capabilities": {},
                            "clientInfo": {"name": "connection-test", "version": "1.0.0"},
                        },
                        "id": 9999,
                    },
                )
            duration = int((time.monotonic() - t0) * 1000)
            # エンドポイントに到達できた（認証エラーでもOK）
            steps.append({
                "name": "endpoint_reachable",
                "label": "MCPエンドポイント到達性",
                "status": "success",
                "message": f"エンドポイントに到達: HTTP {response.status_code}",
                "detail": f"url={self._url}",
                "duration_ms": duration,
            })
        except httpx.ConnectError as e:
            duration = int((time.monotonic() - t0) * 1000)
            steps.append({
                "name": "endpoint_reachable",
                "label": "MCPエンドポイント到達性",
                "status": "error",
                "message": f"エンドポイントに接続できません: {str(e)}",
                "detail": f"url={self._url}",
                "duration_ms": duration,
            })
            return {
                "success": False,
                "message": f"エンドポイント接続失敗: {str(e)}",
                "server_info": None,
                "steps": steps,
            }
        except httpx.TimeoutException:
            duration = int((time.monotonic() - t0) * 1000)
            steps.append({
                "name": "endpoint_reachable",
                "label": "MCPエンドポイント到達性",
                "status": "error",
                "message": "エンドポイントへの接続がタイムアウト",
                "detail": f"url={self._url}, timeout=15s",
                "duration_ms": duration,
            })
            return {
                "success": False,
                "message": "エンドポイント接続タイムアウト",
                "server_info": None,
                "steps": steps,
            }
        except Exception as e:
            duration = int((time.monotonic() - t0) * 1000)
            steps.append({
                "name": "endpoint_reachable",
                "label": "MCPエンドポイント到達性",
                "status": "error",
                "message": f"エンドポイント到達エラー: {str(e)}",
                "detail": f"url={self._url}",
                "duration_ms": duration,
            })
            return {
                "success": False,
                "message": f"エンドポイント到達エラー: {str(e)}",
                "server_info": None,
                "steps": steps,
            }

        # ---- Step 3: MCP初期化（認証 + セッション取得） ----
        t0 = time.monotonic()
        try:
            self._session_id = None  # 新鮮なセッションで実行
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
            duration = int((time.monotonic() - t0) * 1000)

            if response.status_code != 200:
                body_text = response.text[:500]
                steps.append({
                    "name": "mcp_initialize",
                    "label": "MCP初期化（認証・セッション）",
                    "status": "error",
                    "message": f"HTTP {response.status_code} エラー",
                    "detail": body_text,
                    "duration_ms": duration,
                })
                all_success = False

                # 401の場合は認証問題を特定
                if response.status_code == 401:
                    try:
                        err_data = response.json()
                        err_code = err_data.get("code", "")
                        err_msg = err_data.get("message", "")
                        steps[-1]["message"] = f"認証失敗 (HTTP 401): {err_code} - {err_msg}"
                    except Exception:
                        pass
            else:
                # JSON-RPCエラーチェック
                try:
                    data = response.json()
                    if "error" in data:
                        error = data["error"]
                        steps.append({
                            "name": "mcp_initialize",
                            "label": "MCP初期化（認証・セッション）",
                            "status": "error",
                            "message": f"JSON-RPCエラー: {error.get('message', 'Unknown')}",
                            "detail": json.dumps(error, ensure_ascii=False),
                            "duration_ms": duration,
                        })
                        all_success = False
                    else:
                        # セッションID取得
                        session_id = (
                            response.headers.get("mcp-session-id")
                            or response.headers.get("Mcp-Session-Id")
                        )
                        if session_id:
                            self._session_id = session_id
                            steps.append({
                                "name": "mcp_initialize",
                                "label": "MCP初期化（認証・セッション）",
                                "status": "success",
                                "message": "認証成功、セッション確立",
                                "detail": f"session_id={session_id[:12]}...",
                                "duration_ms": duration,
                            })
                        else:
                            steps.append({
                                "name": "mcp_initialize",
                                "label": "MCP初期化（認証・セッション）",
                                "status": "error",
                                "message": "セッションIDがレスポンスヘッダーに含まれていません",
                                "detail": f"headers={dict(response.headers)}",
                                "duration_ms": duration,
                            })
                            all_success = False
                except (json.JSONDecodeError, ValueError):
                    steps.append({
                        "name": "mcp_initialize",
                        "label": "MCP初期化（認証・セッション）",
                        "status": "error",
                        "message": "レスポンスのJSONパースに失敗",
                        "detail": response.text[:300],
                        "duration_ms": duration,
                    })
                    all_success = False
        except Exception as e:
            duration = int((time.monotonic() - t0) * 1000)
            steps.append({
                "name": "mcp_initialize",
                "label": "MCP初期化（認証・セッション）",
                "status": "error",
                "message": f"初期化エラー: {str(e)}",
                "detail": None,
                "duration_ms": duration,
            })
            all_success = False

        # ---- Step 4: ツール呼び出し（サイト情報取得） ----
        if self._session_id:
            t0 = time.monotonic()
            try:
                site_info_str = await self.call_tool("wp-mcp-get-site-info", {})
                duration = int((time.monotonic() - t0) * 1000)
                site_info = json.loads(site_info_str) if isinstance(site_info_str, str) else site_info_str

                server_info = {
                    "site_name": site_info.get("name"),
                    "site_url": site_info.get("url"),
                }
                steps.append({
                    "name": "tool_call",
                    "label": "ツール呼び出し（サイト情報取得）",
                    "status": "success",
                    "message": f"サイト情報取得成功: {site_info.get('name', 'N/A')}",
                    "detail": json.dumps(server_info, ensure_ascii=False),
                    "duration_ms": duration,
                })
            except MCPError as e:
                duration = int((time.monotonic() - t0) * 1000)
                steps.append({
                    "name": "tool_call",
                    "label": "ツール呼び出し（サイト情報取得）",
                    "status": "error",
                    "message": f"ツール呼び出し失敗: {e.message}",
                    "detail": f"code={e.code}",
                    "duration_ms": duration,
                })
                all_success = False
            except Exception as e:
                duration = int((time.monotonic() - t0) * 1000)
                steps.append({
                    "name": "tool_call",
                    "label": "ツール呼び出し（サイト情報取得）",
                    "status": "error",
                    "message": f"ツール呼び出しエラー: {str(e)}",
                    "detail": None,
                    "duration_ms": duration,
                })
                all_success = False
        else:
            steps.append({
                "name": "tool_call",
                "label": "ツール呼び出し（サイト情報取得）",
                "status": "skipped",
                "message": "セッション未確立のためスキップ",
                "detail": None,
                "duration_ms": None,
            })
            all_success = False

        # 総合結果
        if all_success:
            message = "すべてのテストに成功しました"
        else:
            failed = [s for s in steps if s["status"] == "error"]
            message = f"{len(failed)}件のテストが失敗: " + ", ".join(s["label"] for s in failed)

        return {
            "success": all_success,
            "message": message,
            "server_info": server_info,
            "steps": steps,
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


def set_mcp_context(
    site_id: Optional[str],
    user_id: Optional[str],
    process_id: Optional[str] = None,
) -> None:
    """
    エージェント実行前にMCPコンテキストを設定する。

    これにより、エージェントツールが site_id/user_id/process_id を明示的に渡さなくても
    正しいWordPressサイトに接続できる。
    """
    _current_site_id.set(site_id)
    _current_user_id.set(user_id)
    if process_id is not None:
        _current_process_id.set(process_id)
    logger.info(
        f"MCPコンテキスト設定: site_id={site_id[:8] + '...' if site_id else None}, "
        f"user_id={user_id[:8] + '...' if user_id else None}, "
        f"process_id={process_id[:8] + '...' if process_id else None}"
    )


def get_current_process_id() -> Optional[str]:
    """現在のコンテキストの process_id を取得"""
    return _current_process_id.get()


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
        site_id: 接続するWordPressサイトのID（省略時はコンテキスト変数→アクティブサイト）
        user_id: ユーザーID（省略時はコンテキスト変数）
        timeout: タイムアウト（秒）

    Returns:
        ツールの実行結果（JSON文字列）
    """
    # 明示的引数 > コンテキスト変数 > None（フォールバック）
    resolved_site_id = site_id or _current_site_id.get()
    resolved_user_id = user_id or _current_user_id.get()
    client = get_wordpress_mcp_client(resolved_site_id, resolved_user_id)
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
