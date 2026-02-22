# Backend (FastAPI + Python 3.12)

> このファイルは backend/ ディレクトリのファイルを操作する際に自動ロードされる。

## Project Structure
```
backend/
├── main.py                       # エントリポイント (FastAPI app, CORS, ルーティング)
├── pyproject.toml                # Python依存関係 (uv管理)
├── Dockerfile                    # Python 3.12-slim + uv
├── .env / .env.example           # 環境変数
└── app/
    ├── api/router.py             # ルーター集約
    ├── core/
    │   ├── config.py             # Settings (Pydantic BaseSettings)
    │   ├── exceptions.py         # グローバル例外ハンドラ
    │   └── logger.py             # ログ設定
    ├── common/
    │   ├── auth.py               # Clerk JWT検証 (verify_clerk_token)
    │   ├── admin_auth.py         # 管理者認証 (@shintairiku.jp)
    │   ├── database.py           # Supabaseクライアント初期化
    │   └── schemas.py            # WebSocketメッセージ定義
    ├── domains/
    │   ├── seo_article/          # SEO記事生成ドメイン（最大規模）
    │   ├── blog/                 # Blog AI / WordPress連携
    │   ├── organization/         # 組織管理
    │   ├── company/              # 会社情報管理
    │   ├── style_template/       # 文体スタイルガイド
    │   ├── image_generation/     # 画像生成
    │   ├── admin/                # 管理者ダッシュボード
    │   ├── usage/                # 利用上限管理
    │   └── contact/              # お問い合わせ
    └── infrastructure/
        ├── external_apis/        # GCS, SerpAPI, Notion
        ├── gcp_auth.py           # GCP認証 (サービスアカウント)
        ├── clerk_client.py       # Clerk API クライアント
        ├── logging/              # ログシステム
        └── analysis/             # コンテンツ分析, コスト計算
```

## 認証フロー
1. Clerk がフロントエンドのユーザー認証を管理 (Social Login, Email/Password, MFA)
2. Next.js middleware がルート保護と特権チェックを実行
3. バックエンドは Clerk JWT (RS256) を JWKS エンドポイント経由で検証
4. 管理者エンドポイントは `@shintairiku.jp` ドメインのメールを要求

## デプロイ
- Cloud Run (本番: `marketing-automation`, 開発: `marketing-automation-develop`)
- `uv run uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}`
- IAM認証: Vercel SAのみ invoker 権限 → `X-Serverless-Authorization` でバックエンドの auth.py 変更不要
