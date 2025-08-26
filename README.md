# Shintairiku Marketing‑Automation Monorepo

FastAPI バックエンド（Python 3.12）／Next.js **15**（Bun）フロントエンド／Supabase（Postgres + Auth + RLS）のモノレポです。**uv** で Python 依存を管理し、開発時は `uv run uvicorn main:app --reload --host 0.0.0.0 --port 8080` 等で起動できます。フロントは Bun で `bun run dev`、DB は Supabase CLI の `link`→`db push` で反映します。

---

## リポジトリ構成（主要）

```
backend/
  ├─ Dockerfile                     # uv + Uvicorn。Cloud Run の PORT に追従
  ├─ main.py                        # FastAPI 本体（CORS, ルーティング, /health）
  ├─ pyproject.toml                 # uv 用依存。fastapi/uvicorn/openai 等
  ├─ .env.example                   # バックエンド用環境変数（雛形）
  ├─ app/
  │   ├─ api/router.py              # 主要ルーター集約（/articles ほか）
  │   ├─ core/{config,exceptions}.py
  │   ├─ common/{auth,database,schemas}.py
  │   ├─ domains/
  │   │   ├─ seo_article/{endpoints,schemas,services,...}
  │   │   ├─ organization/{endpoints,schemas,service}.py
  │   │   ├─ company/{endpoints,models,schemas,service}.py
  │   │   ├─ style_template/{endpoints,schemas,service}.py
  │   │   └─ image_generation/{endpoints,schemas,service}.py
  │   └─ infrastructure/{external_apis,analysis,logging,...}
frontend/
  ├─ Dockerfile                     # Next.js standalone 出力（server.js）
  ├─ next.config.js                 # /api/proxy → BACKEND への rewrite
  ├─ package.json                   # scripts, Next.js 15 / React 19 依存
  ├─ tailwind.config.ts, postcss.config.js, tsconfig.json
  ├─ .env.example                   # Supabase/Stripe/Clerk など
  └─ src/                           # app ディレクトリ, API ルート, libs, hooks など
shared/supabase/
  ├─ config.toml                    # auth.site_url 等の設定
  ├─ migrations/                    # すべての SQL マイグレーション
  └─ seed.sql                       # 追加データ（必要に応じて）

docker-compose.yml                  # frontend_dev(3000), backend(8008→8000), stripe-cli
.env.example                         # ルートの環境変数雛形
```

---

## 前提ツール

* Python **3.12**（`pyenv` 推奨）
* **Bun** v1 系
* Node.js（本番ビルド／standalone 実行で使用）
* **Supabase CLI**（`npm i -g supabase` または `npx supabase`）
* Docker / Docker Compose（任意）

---

## 環境変数の配置

* ルート: `.env` または `.env.local`（Supabase/Stripe/Google 等の共通）
* バックエンド: `backend/.env`（API キー, ALLOWED\_ORIGINS など）
* フロント: `frontend/.env.local`（NEXT\_PUBLIC\_\* 系, Clerk/Stripe/Supabase など）

**代表例（抜粋）**

```env
# Supabase（必須）
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=
SUPABASE_DB_PASSWORD=

# Backend URL（フロント → API プロキシに利用）
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_SITE_URL=http://localhost:3000

# Stripe / Clerk（必要な場合のみ）
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=
CLERK_SECRET_KEY=

# バックエンド専用
ALLOWED_ORIGINS=http://localhost:3000
OPENAI_API_KEY=
GEMINI_API_KEY=
SERPAPI_API_KEY=
```

---

## セットアップ手順

### 1) Supabase をリンクしてマイグレーション

1. CLI ログイン

   ```bash
   supabase login
   ```
2. プロジェクトにリンク（既存プロジェクトを選択）

   ```bash
   npx supabase link
   # 既に project-ref が分かっている場合
   # npx supabase link --project-ref <your-ref>
   ```
3. マイグレーション適用（DDL を反映 & 型生成を実行する運用を推奨）

   ```bash
   npx supabase db push
   # あるいはフロントスクリプト：
   # bun run migration:up    # migration up --linked && 型生成
   # bun run generate-types  # types → frontend/src/libs/supabase/types.ts
   ```

> `shared/supabase/migrations/` に初期スキーマと拡張マイグレーションがまとまっています（`users` RLS, organizations/article\_flows, company\_info, style\_guide\_templates, Supabase Realtime 連携, 外部キー修正 など）。

### 2) バックエンド（FastAPI + Uvicorn）

```bash
cd backend
uv sync
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8080
```

* 主要エンドポイント: `/`（稼働確認メッセージ）, `/health`（ヘルス）
* ルーター: `/articles`, `/organizations`, `/companies`, `/style-templates`, `/images` を集約
* CORS: `ALLOWED_ORIGINS`（カンマ区切り）で許可オリジンを設定

### 3) フロントエンド（Next.js 15 + Bun）

```bash
cd frontend
bun install
bun run dev
```

* `next.config.js` の `rewrites()` で `'/api/proxy/:path*' → ${NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'}/:path*` に転送
* 開発既定 URL は `http://localhost:3000`
* 必要に応じて `NEXT_PUBLIC_API_BASE_URL` を API に合わせて変更

---

## Docker / Docker Compose（任意）

開発をまとめて動かす場合：

```bash
docker compose up -d frontend_dev backend
# ログ
docker compose logs -f backend
```

* Frontend: [http://localhost:3000（\`frontend\_dev\`）](http://localhost:3000（`frontend_dev`）)
* Backend:  [http://localhost:8008](http://localhost:8008) → コンテナ 8000 へフォワード
* Stripe CLI（任意）: `stripe listen --forward-to=frontend_dev:3000/api/webhooks`

**Backend コンテナ**は uv を用いて依存を同期し、Cloud Run 互換のコマンドで起動します：

```dockerfile
CMD ["sh","-c","uv run uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
```

**Frontend コンテナ**は Next.js **standalone** 出力を `node server.js` で実行します（`EXPOSE 3000`）。

---

## データベース（要点）

* 初期化: `20240115041359_init.sql` — `users` テーブル + **RLS（自身のみ参照/更新）**
* 以降: organizations / article\_flows / company\_info / style\_guide\_templates / 画像プレースホルダー / GCS 対応 / Realtime / FK 修正 / Agents ログなど随時拡張
* `shared/supabase/config.toml` の `auth.site_url` はローカルでは `http://localhost:3000` を想定

---

## 実運用ヒント

* **型の同期**: マイグレーション後は `bun run generate-types` でフロントの Supabase 型を再生成
* **CORS**: フロント URL を `ALLOWED_ORIGINS` に必ず含める
* **API プロキシ**: フロントからは `/api/proxy/*` を使うとバックエンド切替が容易
* **Cloud Run**: `PORT` は実行環境から注入されるため Dockerfile は `${PORT:-8000}` を利用
