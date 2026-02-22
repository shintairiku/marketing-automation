# CLAUDE.md - 永続メモリ & 階層化コンテキスト

> ## **【最重要】記憶の更新は絶対に忘れるな**
> **作業の開始時・途中・完了時に必ずこのファイルまたは該当する分割ファイルを確認・更新せよ。**
> コード変更、設計変更、新しい知見、バグ修正、アーキテクチャ変更 — どんな小さな変更でも、発生したらその場で即座に記録すること。
> **ユーザーに「記憶を更新して」と言われる前に、自分から更新するのが当たり前。言われてからでは遅い。**
>
> ## 記録先ガイド
> - **変更履歴**: @.claude/changelog.md に追記（直近10項目を保持、古いものは @.claude/changelog-archive.md）
> - **自己改善**: @.claude/self-improvement.md に追記
> - **ドメイン固有知見**: 該当する `.claude/rules/*.md` に追記
> - **このファイル**: プロジェクト全体に関わるルール変更のみ

---

## Package Management (STRICT)

- **Backend (Python)**: `uv add <package>` for dependencies. **Never use `pip install`.**
- **Frontend (JS/TS)**: `bun add <package>` for dependencies. **Never use `npm install` or `yarn add`.**
- Backend lock: `uv sync` to sync after changes
- Frontend lock: `bun install` to sync after changes

---

## Cloud Sandbox Claude Code 必須手順

### 作業開始時（必須）
```bash
cd frontend && bun install && cd ..
cd backend && uv sync && cd ..
```

### プッシュ前（必須）
```bash
cd backend && uv run python -m ruff check app      # Backend Lint
cd frontend && bun run lint                          # Frontend Lint
cd frontend && bun run build                         # Frontend Build
```
**lint, ruff check, build が失敗する状態でプッシュしてはならない。**

### ビルド用プレースホルダー .env.local
サンドボックスでは `.env.example` をコピーしてプレースホルダー値を入れる。

---

## プロジェクト概要

**BlogAI** — AIを活用したブログ記事の自動生成SaaSプラットフォーム。
WordPress連携によるブログ投稿、画像生成、組織管理、サブスクリプション課金を提供。

### 主要機能
1. **Blog AI (WordPress連携)**: WordPressサイトと接続し、AIがブログ記事を生成・投稿
2. **SEO記事生成**: キーワード→SERP分析→ペルソナ→アウトライン→本文のフルフロー（特権のみ）
3. **AI画像生成**: Google Vertex AI Imagen-4による記事用画像
4. **組織管理**: マルチテナント対応。招待制でチームメンバー管理
5. **サブスクリプション**: Stripe連携 + フリープラン（月10記事、クレカ不要）
6. **管理者ダッシュボード**: @shintairiku.jp ドメインユーザー専用

---

## Tech Stack

### Backend
- FastAPI + Uvicorn (Python 3.12) / uv
- OpenAI Agents SDK, Google Generative AI (Gemini), Vertex AI (Imagen-4)
- Supabase (PostgreSQL + Realtime), Clerk JWT (RS256)

### Frontend
- Next.js 15 + React 19 + TypeScript / Bun
- Tailwind CSS 3.4 + shadcn/ui + Framer Motion
- @clerk/nextjs v6, @supabase/supabase-js, Stripe v20
- Font: Noto Sans JP (fontsource セルフホスト)

### Infrastructure
- Supabase (PostgreSQL + RLS + Realtime)
- Google Cloud Storage, Cloud Run
- GitHub Actions, Vercel

---

## Project Structure (概要)

```
marketing-automation/
├── backend/                    # FastAPI (DDD/オニオンアーキテクチャ)
│   ├── app/api/                # ルーター集約
│   ├── app/core/               # 設定、例外、ログ
│   ├── app/common/             # 認証、DB、スキーマ
│   ├── app/domains/            # seo_article, blog, organization, company,
│   │                           # style_template, image_generation, admin, usage, contact
│   └── app/infrastructure/     # GCS, SerpAPI, Clerk, GCP認証, ログ
├── frontend/                   # Next.js 15 (Feature-Based Architecture)
│   ├── src/app/(tools)/        # Blog AI (SubscriptionGuard有)
│   ├── src/app/(settings)/     # 設定 (SubscriptionGuard無)
│   ├── src/app/(admin)/        # 管理画面 (特権のみ)
│   ├── src/app/api/            # API Routes (proxy, subscription, webhooks)
│   ├── src/components/         # shadcn/ui, display, layout, subscription, pwa
│   ├── src/hooks/              # Realtime, 記事生成, 自動保存
│   └── src/lib/                # ApiClient, google-auth, backend-fetch
├── shared/supabase/            # マイグレーション + config
├── .claude/rules/              # path-scoped ルール (自動ロード)
├── .claude/docs/               # リファレンス (@import で参照)
└── .claude/changelog.md        # 変更履歴
```

---

## 認証 & サブスクリプション

### 認証フロー
- Clerk → Next.js middleware → Backend (Clerk JWT RS256 + JWKS)
- 管理者: `@shintairiku.jp` ドメイン → 全機能アクセス可能（サブスク不要）
- 非特権: `/blog/*`, `/settings/*`, `/help/*` のみ

### サブスクリプション
- **フリープラン**: 月10記事、クレカ不要、登録時自動付与 (`plan_tier_id: 'free'`)
- **有料プラン**: 現在非表示（価格未決定）
- **total_limit 公式**: `articles_limit + addon_articles_limit + admin_granted_articles`
- `SubscriptionGuard`: `(tools)` レイアウト内のみ。`(settings)` は未課金でもアクセス可
- 同一 Stripe Customer を個人・チームで共有

---

## Development Commands

```bash
# Backend
cd backend && uv run uvicorn main:app --reload --host 0.0.0.0 --port 8080
cd backend && uv run python -m ruff check app

# Frontend
cd frontend && bun run dev          # 開発サーバー (Turbopack)
cd frontend && bun run build        # 本番ビルド
cd frontend && bun run lint         # ESLint
cd frontend && bun run generate-types  # Supabase型生成

# Database
npx supabase start                  # ローカルDB起動
npx supabase db diff -f <name>      # 差分SQL生成
npx supabase db reset               # 全migration再適用
```

---

## Git Branching
- **main**: 本番ブランチ
- **develop**: 開発ブランチ
- PRは `develop` → `main`

---

## Design Rules
- **Primary Color**: custom-orange (#E5581C)
- **Component Library**: shadcn/ui (Radix UI)
- **Animation**: Framer Motion
- **Icons**: Lucide React

---

## 重要な横断的ルール

### USE_PROXY パターン (Frontend)
- 本番: `/api/proxy/[...path]` → IAMトークン付与 → Cloud Run
- 開発: `localhost:8080` 直接
- **ブラウザから直接 Cloud Run にfetchするコードは禁止**

### 記憶の更新タイミング
- コード変更を完了したら、**コミット前に**必ず該当ファイルを更新する
- 「後で更新しよう」は禁止。今すぐ更新せよ

---

## 詳細リファレンス (@import)

以下のファイルは必要時に参照:
- @.claude/docs/api-reference.md — 全API エンドポイント
- @.claude/docs/database-schema.md — DBテーブル一覧
- @.claude/docs/frontend-routes.md — フロントエンドルート
- @.claude/docs/environment-variables.md — 環境変数
- @.claude/docs/openai-sdk-knowledge.md — OpenAI SDK知見
- @.claude/changelog.md — 直近の変更履歴
- @.claude/changelog-archive.md — 古い変更履歴
- @.claude/self-improvement.md — 自己改善ログ

## path-scoped ルール (.claude/rules/)

以下は該当ファイル操作時に自動ロード:
- `.claude/rules/backend-python.md` — Backend固有 (paths: backend/**/*.py)
- `.claude/rules/frontend-nextjs.md` — Frontend固有 (paths: frontend/src/**/*.ts,tsx,css)
- `.claude/rules/database-migrations.md` — DBマイグレーション (paths: shared/supabase/**)
- `.claude/rules/stripe-billing.md` — Stripe/課金 (paths: frontend/src/app/api/subscription/**)
- `.claude/rules/blog-ai-domain.md` — Blog AI (paths: backend/app/domains/blog/**,frontend/src/app/(tools)/blog/**)
- `.claude/rules/admin-dashboard.md` — 管理画面 (paths: frontend/src/app/(admin)/**,backend/app/domains/admin/**)

## サブディレクトリ CLAUDE.md (on-demand)

以下は該当ディレクトリ作業時に自動ロード:
- `backend/CLAUDE.md` — Backend プロジェクト構造・認証・デプロイ
- `frontend/CLAUDE.md` — Frontend プロジェクト構造・デプロイ・注意点
