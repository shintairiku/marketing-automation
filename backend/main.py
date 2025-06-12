# -*- coding: utf-8 -*-
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse # <<< HTMLResponse をインポート
from fastapi.templating import Jinja2Templates # HTMLファイルを使う場合 (今回は直接返す)
from fastapi.middleware.cors import CORSMiddleware # CORS ミドルウェア追加
from pathlib import Path # <<< Path をインポート
from openai import AsyncOpenAI

from api.endpoints import article as article_router
from api.endpoints import organization as organization_router
from api.endpoints import article_flow as article_flow_router
from core.config import settings
from core.exceptions import exception_handlers

# FastAPIアプリケーションの初期化
app = FastAPI(
    title="Marketing Automation API",
    description="Comprehensive API for marketing automation including SEO article generation, organization management, and workflow automation.",
    version="2.0.0",
    exception_handlers=exception_handlers
)

# CORS設定
import os

# 環境変数から許可するオリジンを取得
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# APIルーターのインクルード
app.include_router(article_router.router, prefix="/articles", tags=["Articles"])
app.include_router(organization_router.router, prefix="/organizations", tags=["Organizations"])
app.include_router(article_flow_router.router, prefix="/article-flows", tags=["Article Flows"])

@app.get("/", tags=["Root"], summary="APIルートエンドポイント")
async def read_root():
    """APIのルートエンドポイント。APIが動作しているか確認できます。"""
    return {"message": "Welcome to the SEO Article Generation API (WebSocket)!"}

@app.get("/health", tags=["Health"], summary="ヘルスチェック")
async def health_check():
    """APIのヘルスチェックエンドポイント。"""
    return {"status": "healthy", "message": "API is running", "version": "2.0.0"}

# プリフライトリクエスト用のOPTIONSハンドラー
@app.options("/{path:path}", tags=["CORS"], summary="CORS プリフライトハンドラー")
async def options_handler(path: str):
    """CORS プリフライトリクエストに対応するOPTIONSハンドラー。"""
    return {"message": "OK"}

# --- テストクライアント用エンドポイント ---
# test_client.html がプロジェクトルートにあると仮定
HTML_FILE_PATH = Path(__file__).parent / "test_client.html"

@app.get("/test-client", response_class=HTMLResponse, tags=["Test Client"], summary="WebSocketテストクライアント")
async def get_test_client():
    """
    WebSocket接続をテストするための簡単なHTMLクライアントページを返します。
    """
    if not HTML_FILE_PATH.is_file():
        return HTMLResponse(content="<html><body><h1>Error: test_client.html not found</h1></body></html>", status_code=404)
    with open(HTML_FILE_PATH, "r", encoding="utf-8") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)
# --------------------------------------

# Uvicornで実行する場合 (開発用)
if __name__ == "__main__":
    import uvicorn
    print("To run the server, use the command:")
    print("uvicorn main:app --reload --host 0.0.0.0 --port 8000")

