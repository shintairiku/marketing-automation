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

# 生成された画像の静的ファイル配信
# パスをプロジェクトルートからの相対パスとして解決
images_directory = Path(__file__).parent / settings.image_storage_path.lstrip('/')
images_directory.mkdir(parents=True, exist_ok=True)
print(f"画像ディレクトリ: {images_directory.resolve()}")
app.mount("/images", StaticFiles(directory=str(images_directory.resolve())), name="images")

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

# テストクライアント用のエンドポイントは開発用のため、削除または `#if DEBUG:` などで囲むことを推奨
# ...

# 重複削除済み（上記で定義済み）

# Uvicornで実行する場合 (開発用)
if __name__ == "__main__":
    print("To run the server, use the command:")
    print("uvicorn main:app --reload --host 0.0.0.0 --port 8000")

