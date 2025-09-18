# -*- coding: utf-8 -*-
import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# 新しいインポートパス
from app.api.router import api_router
from app.core.config import settings
from app.core.exceptions import exception_handlers

# FastAPIアプリケーションの初期化
app = FastAPI(
    title="Marketing Automation API",
    description="Comprehensive API for marketing automation including SEO article generation, organization management, and workflow automation.",
    version="2.0.0",
    exception_handlers=exception_handlers
)

# CORS設定

# 環境変数から許可するオリジンを取得
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# ★ APIルーターをまとめてインクルード（プレフィックスなしで互換性維持）
app.include_router(api_router)

# 画像の静的ファイル配信は /images/serve/{filename} エンドポイントで処理
# StaticFilesによる /images マウントは画像APIと衝突するため削除
# 画像ディレクトリは確保しておく（backendルート基準で解決）
backend_root = Path(__file__).parent
configured_path = Path(settings.image_storage_path)
images_directory = configured_path if configured_path.is_absolute() else backend_root / configured_path
images_directory.mkdir(parents=True, exist_ok=True)
print(f"画像ディレクトリ: {images_directory.resolve()}")

@app.get("/", tags=["Root"], summary="APIルートエンドポイント")
async def read_root():
    """APIのルートエンドポイント。APIが動作しているか確認できます。"""
    return {"message": "Welcome to the SEO Article Generation API (WebSocket)!"}

@app.get("/health", tags=["Health"], summary="ヘルスチェック")
async def health_check():
    """APIのヘルスチェックエンドポイント。"""
    return {"status": "healthy", "message": "API is running", "version": "2.0.0"}

# CORSプリフライトリクエストはCORSMiddlewareが自動的に処理するため、
# 個別のOPTIONSハンドラーは不要です

# テストクライアント用のエンドポイントは開発用のため、削除または `#if DEBUG:` などで囲むことを推奨
# ...

# 重複削除済み（上記で定義済み）

# Uvicornで実行する場合 (開発用)
if __name__ == "__main__":
    print("To run the server, use the command:")
    print("uvicorn main:app --reload --host 0.0.0.0 --port 8000")

