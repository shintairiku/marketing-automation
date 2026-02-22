# BlogAI — AI ブログ記事生成 SaaS

AI を活用した SEO 記事・ブログ記事の自動生成プラットフォーム。WordPress 連携、SEO 分析、画像生成、組織管理、サブスクリプション課金を提供。

---

## Quick Start（開発環境）

### 前提ツール

| ツール | バージョン | インストール |
|--------|-----------|-------------|
| Python | 3.12+ | `pyenv install 3.12` |
| uv | latest | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Bun | v1+ | `curl -fsSL https://bun.sh/install \| bash` |
| Docker | latest | WSL2: Docker Desktop / Linux: `apt install docker.io` |
| Supabase CLI | latest | `npx supabase` (npx 経由で自動取得) |
| Stripe CLI | latest | `brew install stripe/stripe-cli/stripe` (任意) |

### 1. リポジトリをクローン & 環境変数を設定

```bash
git clone <repo-url> && cd next-supabase-starter

# 環境変数テンプレートをコピーして値を埋める
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.local
cp supabase/.env.example supabase/.env
```

### 2. 依存をインストール

```bash
cd backend && uv sync && cd ..
cd frontend && bun install && cd ..
```

### 3. 開発サーバーを起動

```bash
make dev
```

これだけ。以下が自動で起動します：

| サービス | URL | 備考 |
|---------|-----|------|
| Frontend (Next.js) | http://localhost:3000 | Turbopack 有効 |
| Backend (FastAPI) | http://localhost:8080 | --reload 有効 |
| Supabase Studio | http://localhost:15423 | 起動済みなら自動スキップ |

**Ctrl+C** で全サービス停止。

### その他の `make` コマンド

```bash
make dev              # Supabase + Backend + Frontend を起動
make dev STRIPE=1     # 上記 + Stripe webhook listener
make frontend         # Frontend のみ
make backend          # Backend のみ
make supabase         # Supabase のみ (起動済みならスキップ)
make stripe           # Stripe CLI のみ
make stop             # Supabase コンテナ停止
make lint             # Frontend ESLint + Backend ruff
make build            # Frontend 本番ビルド
make check            # lint + build (プッシュ前チェック)
```

### DB マイグレーション

```bash
# ローカル Supabase にマイグレーション適用
npx supabase db reset          # 全マイグレーション再適用 + seed

# リモート (Dev/Prod) に適用 — CI/CD が自動実行
# develop push → Dev Supabase
# main push    → Prod Supabase

# 新しいマイグレーション作成
npx supabase migration new <name>

# TypeScript 型再生成 (テーブル/カラム変更後)
cd frontend && bun run generate-types
```

---

## プロジェクト構成

```
├── backend/                  # FastAPI + Python 3.12 (uv)
│   ├── main.py               # エントリポイント
│   ├── app/
│   │   ├── api/router.py     # ルーター集約
│   │   ├── core/             # 設定, 例外処理
│   │   ├── common/           # 認証, DB, スキーマ
│   │   ├── domains/          # DDD ドメイン
│   │   │   ├── blog/         # Blog AI (WordPress連携)
│   │   │   ├── seo_article/  # SEO 記事生成
│   │   │   ├── usage/        # 利用上限管理
│   │   │   ├── contact/      # お問い合わせ
│   │   │   ├── admin/        # 管理者機能
│   │   │   └── ...
│   │   └── infrastructure/   # 外部API (GCS, SerpAPI, Clerk)
│   └── pyproject.toml
│
├── frontend/                 # Next.js 15 + React 19 + TypeScript (Bun)
│   ├── src/
│   │   ├── app/              # App Router (pages, API routes)
│   │   ├── components/       # UI (shadcn/ui + Radix)
│   │   ├── features/         # ドメイン別 UI
│   │   ├── hooks/            # カスタムフック
│   │   └── lib/              # API クライアント, サブスクリプション
│   └── package.json
│
├── supabase/                 # Supabase ローカル設定
│   ├── config.toml           # ポート: 15421-15423
│   ├── migrations/           # SQL マイグレーション
│   └── seed.sql              # 初期データ (plan_tiers 等)
│
├── Makefile                  # 開発コマンド (make dev, make check, ...)
├── docker-compose.yml        # Docker 開発環境 (任意)
└── docs/                     # 設計ドキュメント
```

---

## Tech Stack

| レイヤー | 技術 |
|---------|------|
| Frontend | Next.js 15, React 19, TypeScript, Tailwind CSS 3, shadcn/ui, Framer Motion |
| Backend | FastAPI, Python 3.12, OpenAI Agents SDK, Google Vertex AI (Imagen-4) |
| DB | Supabase (PostgreSQL 17 + Realtime + RLS) |
| Auth | Clerk (JWT RS256, Third-Party Auth for Supabase) |
| Payment | Stripe (Checkout, Billing, Customer Portal) |
| Infra | Vercel (Frontend), Cloud Run (Backend), GCS (画像) |
| CI/CD | GitHub Actions (lint, Docker build, DB migrations) |
| Package | Bun (frontend), uv (backend) |

---

## 環境変数

### Backend (`backend/.env`)

```env
# 必須
OPENAI_API_KEY=
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=
CLERK_SECRET_KEY=
CLERK_PUBLISHABLE_KEY=
ALLOWED_ORIGINS=http://localhost:3000

# AI モデル (デフォルト値あり)
BLOG_GENERATION_MODEL=gpt-5.2
RESEARCH_MODEL=gpt-5-mini

# その他 (詳細は backend/.env.example)
STRIPE_SECRET_KEY=
GEMINI_API_KEY=
GOOGLE_CLOUD_PROJECT=
CREDENTIAL_ENCRYPTION_KEY=
```

### Frontend (`frontend/.env.local`)

```env
# 必須
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=
CLERK_SECRET_KEY=
NEXT_PUBLIC_API_BASE_URL=http://localhost:8080

# Stripe (課金テスト時)
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=
```

### Supabase (`supabase/.env`)

```env
CLERK_DOMAIN=your-clerk-domain.clerk.accounts.dev
```

---

## Git ブランチ戦略

```
main     ← 本番 (Vercel Production, Cloud Run Production, Prod Supabase)
develop  ← 開発 (Vercel Preview, Cloud Run Develop, Dev Supabase)
feat/*   ← 機能ブランチ → develop に PR
fix/*    ← バグ修正 → develop に PR
```

- PR は **develop → main** でマージ
- CI: `ci-backend.yml` (ruff + Docker), `db-migrations.yml` (Supabase push)
- Vercel: Git Integration で自動ビルド・デプロイ

---

## プッシュ前チェック（必須）

```bash
make check
```

以下が実行されます：
1. Backend lint (`ruff check`)
2. Frontend lint (`next lint`)
3. Frontend build (`next build`)

**lint または build が失敗する状態でプッシュしてはいけません。**

---

## Docker Compose（任意）

ネイティブ起動 (`make dev`) の代替として Docker でも開発可能：

```bash
docker compose up -d frontend_dev backend
docker compose logs -f backend
```

| サービス | ポート |
|---------|--------|
| frontend_dev | 3000 |
| backend | 8008 → 8000 |
| stripe-cli | (webhook 転送) |

---

## パッケージ管理ルール

```bash
# Frontend (JavaScript/TypeScript)
bun add <package>          # npm install は禁止
bun install                # lock file 同期

# Backend (Python)
uv add <package>           # pip install は禁止
uv sync                    # lock file 同期
```
