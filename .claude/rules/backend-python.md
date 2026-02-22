---
paths: backend/**/*.py
---

# Backend Python ルール

## DDD/オニオンアーキテクチャ
- `domains/` にビジネスドメイン (seo_article, blog, organization, company, style_template, image_generation, admin, usage, contact)
- `infrastructure/` に外部API統合 (GCS, SerpAPI, Notion, Clerk, GCP認証)
- `common/` に横断的関心事 (認証, DB, スキーマ)
- `core/` にアプリケーション設定・例外処理

## 認証パターン
- Clerk JWT (RS256) をJWKSエンドポイント経由で検証: `verify_clerk_token()` in `common/auth.py`
- 管理者エンドポイントは `@shintairiku.jp` ドメインを要求: `admin_auth.py`
- エンドポイントには `Depends(get_current_user_id_from_token)` を必ず追加

## エージェント実装パターン (OpenAI Agents SDK)
- `agents/definitions.py` でエージェント定義 (output_type, tools, instructions)
- `agents/tools.py` でツール関数定義 (@function_tool)
- `services/generation_service.py` で Runner.run_streamed() を使用
- ストリーミングイベント: RunItemStreamEvent + RawResponsesStreamEvent
- contextvars で process_id をエージェントツールに渡す (スレッドセーフ)

## Lint
```bash
cd backend && uv run python -m ruff check app
```

## デプロイ
- Dockerfile: `python:3.12-slim` + `uv`
- 起動: `uv run uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}`
- Cloud Run (本番: `marketing-automation`, 開発: `marketing-automation-develop`)
