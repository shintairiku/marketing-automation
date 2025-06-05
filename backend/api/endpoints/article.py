# -*- coding: utf-8 -*-
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from typing import Any
import traceback
import json
from pydantic import ValidationError

from services.article_service import ArticleGenerationService
from schemas.response import WebSocketMessage, ErrorPayload # エラー送信用

router = APIRouter()
article_service = ArticleGenerationService() # サービスインスタンス化

@router.websocket("/ws/generate")
async def generate_article_websocket_endpoint(websocket: WebSocket, process_id: str = None, user_id: str = None):
    """
    WebSocket接続を確立し、インタラクティブな記事生成プロセスを開始します。

    **パラメータ:**
    - process_id: 既存プロセスの再開用ID（新規作成の場合はNone）
    - user_id: ユーザーID（認証システムから取得）

    **接続後の流れ:**

    1.  **クライアント -> サーバー:** 接続後、最初のメッセージとして記事生成のリクエストパラメータをJSON形式で送信します (`GenerateArticleRequest` スキーマ参照)。
        ```json
        {
          "initial_keywords": ["札幌", "注文住宅", "自然素材"],
          "target_persona": "30代夫婦",
          // ... 他のパラメータ
        }
        ```
    2.  **サーバー -> クライアント:** サーバーは記事生成プロセスを開始し、進捗状況、ユーザーに入力を求める要求、最終結果などを `ServerEventMessage` 形式で送信します。
        ```json
        {
          "type": "server_event",
          "payload": {
            "event_type": "status_update", // または theme_proposal, user_input_request など
            // ... 各イベントタイプに応じたペイロード
          }
        }
        ```
    3.  **クライアント -> サーバー (応答):** サーバーから `user_input_request` イベントを受信した場合、クライアントは対応する応答を `ClientResponseMessage` 形式で送信します。
        ```json
        {
          "type": "client_response",
          "response_type": "select_theme", // または approve_plan など
          "payload": {
            "selected_index": 0 // または approved: true など
          }
        }
        ```
    4.  **最終結果:** 生成が完了すると、サーバーは `final_result` イベントを送信します。
    5.  **エラー:** エラーが発生した場合、サーバーは `error` イベントを送信します。

    接続は、生成完了時、エラー発生時、またはクライアント/サーバーからの切断要求時に閉じられます。
    """
    await article_service.handle_websocket_connection(websocket, process_id, user_id)

