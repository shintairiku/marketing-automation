# AGENTS.md — OpenAI Codex CLI / その他AIエージェント用プロジェクト設定

> **このファイルは Codex CLI (OpenAI) やその他のAIエージェントツール向けの設定ファイルです。**
> Claude Code を使用している場合は `CLAUDE.md` を参照してください。

---

## 重要: CLAUDE.md を参照せよ

このプロジェクトの**詳細な設計情報・変更履歴・技術的知見**は全て `CLAUDE.md` に集約されている。
ただし CLAUDE.md は **1800行以上** あるため、全文を一度に読み込むとコンテキストを圧迫する。

### 読み込み戦略

1. **まずこの AGENTS.md を読む** — プロジェクト概要、必須ルール、基本構造を把握
2. **必要に応じて CLAUDE.md の特定セクションを参照** — タスクに関連するセクションのみ読む
3. **CLAUDE.md のセクション構成**:
   - プロジェクト概要 (〜50行目)
   - Tech Stack (〜100行目)
   - Project Structure (〜200行目)
   - Backend API Endpoints (〜400行目)
   - Frontend Routes (〜500行目)
   - Database Tables (〜600行目)
   - Authentication & Authorization (〜650行目)
   - Key Architecture Decisions (〜720行目)
   - AI Models Configuration (〜750行目)
   - Environment Variables (〜820行目)
   - Development Commands (〜870行目)
   - Stripe サブスクリプション設計知見 (〜1000行目)
   - セッション内の変更履歴 (1000行目〜) — 過去の全変更記録。通常は最新数件のみ参照

---

## 絶対に守るべきルール

### Package Management (厳守)
- **Frontend**: `bun add <package>` / `bun install` — **npm, yarn は禁止**
- **Backend**: `uv add <package>` / `uv sync` — **pip install は禁止**

### Git
- **main**: 本番ブランチ（直接pushしない）
- **develop**: 開発ブランチ
- **ブランチ戦略**: `feature/*` → `develop` → `main`

### コード変更時の義務
- **CLAUDE.md を更新する**: 設計変更、新ファイル作成、バグ修正、知見の獲得 — あらゆる変更を記録
- セッション内の変更履歴セクションに追記すること

---

## プロジェクト概要

**BlogAI** — AIを活用したSEO記事・ブログ記事の自動生成SaaSプラットフォーム。
WordPress連携によるブログ投稿、SEO分析、画像生成、組織管理、サブスクリプション課金を提供。

---

## Tech Stack (要約)

| レイヤー | 技術 |
|---------|------|
| Frontend | Next.js 15 + React 19 + TypeScript + Tailwind CSS 3 + shadcn/ui |
| Backend | FastAPI + Python 3.12 (uv) |
| AI/ML | OpenAI Agents SDK, Google Generative AI (Gemini), Vertex AI (Imagen-4) |
| DB | Supabase (PostgreSQL + Realtime + RLS) |
| Auth | Clerk (JWT RS256, Third-Party Auth for Supabase) |
| Payment | Stripe (サブスクリプション + アドオン) |
| Hosting | Vercel (Frontend) + Cloud Run (Backend) |
| Storage | Google Cloud Storage |

---

## ディレクトリ構成 (要約)

```
├── backend/                 # FastAPI (Python 3.12, uv)
│   ├── app/
│   │   ├── api/router.py    # ルーター集約
│   │   ├── core/            # config, exceptions, logger
│   │   ├── common/          # auth, database, schemas
│   │   ├── domains/         # DDD: seo_article, blog, organization, company, etc.
│   │   └── infrastructure/  # GCS, SerpAPI, Clerk, GCP auth, logging
│   └── pyproject.toml
├── frontend/                # Next.js 15 (Bun, Turbopack)
│   └── src/
│       ├── app/             # App Router (pages, API routes)
│       ├── components/      # shadcn/ui + custom components
│       ├── features/        # Feature-based modules
│       ├── hooks/           # Business logic hooks
│       ├── lib/             # ApiClient, subscription logic
│       └── utils/           # Utilities
├── supabase/
│   ├── config.toml          # Supabase CLI config (local dev)
│   ├── migrations/          # SQL migrations (baseline + incremental)
│   └── seed.sql             # Initial data (plan_tiers, flow templates)
└── .github/workflows/       # CI/CD (ci-backend.yml, db-migrations.yml)
```

---

## 開発コマンド

```bash
# Frontend
cd frontend && bun install && bun run dev     # 開発サーバー
cd frontend && bun run build                  # ビルド
cd frontend && bun run lint                   # Lint

# Backend
cd backend && uv sync                         # 依存同期
cd backend && uv run uvicorn main:app --reload --host 0.0.0.0 --port 8080
cd backend && uv run ruff check app           # Lint
cd backend && uv run ruff format app          # Format

# Supabase (ローカル)
npx supabase start                            # 起動
npx supabase db diff -f <name>                # スキーマ差分からマイグレーション生成
npx supabase db reset                         # 全migration + seed 再適用
npx supabase stop                             # 停止

# Supabase (型生成)
cd frontend && bun run generate-types
```

---

## 環境分離

| 環境 | Frontend | Backend | DB | Auth |
|------|---------|---------|-----|------|
| **Production** | Vercel (main) | Cloud Run `marketing-automation` | Supabase `tkkbhglcudsxcwxdyplp` | Clerk Prod |
| **Development** | Vercel Preview (develop) | Cloud Run `marketing-automation-develop` | Supabase `dddprfuwksduqsimiylg` | Clerk Dev |
| **Local** | localhost:3000 | localhost:8080 | Supabase Local (Docker) | Clerk Dev |

---

## CI/CD

| ワークフロー | トリガー | 内容 |
|---|---|---|
| `ci-backend.yml` | PR to main/develop (backend/**) | ruff lint + Docker build |
| `db-migrations.yml` | PR + push (supabase/migrations/**) | PR: dry-run / push: 実適用 |
| Vercel Git Integration | 全push | Frontend lint + build + deploy |
| Cloud Run 自動デプロイ | develop/main push | Backend Docker build + deploy |

---

## 認証フロー

```
ブラウザ → Clerk (JWT取得) → Vercel/Next.js → /api/proxy → Cloud Run (FastAPI)
                                                    ↓
                                        X-Serverless-Authorization (IAM token)
                                        Authorization (Clerk JWT)
```

- Vercel → Cloud Run: `X-Serverless-Authorization` ヘッダーでIAM認証
- Cloud Run → Supabase: service_role key
- Frontend → Supabase (Realtime): Clerk JWT + Third-Party Auth

---

## よくある注意点

1. **`(supabase as any)` キャスト**: `organization_subscriptions` テーブルは PK がデフォルト値なしの `text` 型のため、supabase-js の型推論が壊れる。`as any` は意図的
2. **Vercel Preview の環境変数**: Production と Preview で異なる値が設定されている（Supabase, Stripe, Clerk）。変数追加時はスコープに注意
3. **Cloud Run IAM**: 新しいCloud Runサービスを作ったら `vercel-invoker` SAに `run.invoker` を付与すること
4. **特権ユーザー**: `@shintairiku.jp` ドメインのユーザーは全機能アクセス可能（サブスク不要）。チェックは `middleware.ts`
5. **Supabase Realtime**: ポーリング無効化、DBが信頼の源泉。`useArticleGenerationRealtime` フックが全状態管理を担当
