# 環境分離・デプロイ戦略ガイド

> **作成日**: 2026-02-18
> **最終更新**: 2026-02-18
> **対象**: BlogAI / Marketing Automation Platform
> **ブランチ戦略**: `feature/*` → `develop` → `main`
> **作業ブランチ**: `feat/dev-prod` (developから派生)

---

## 目次

1. [現在の状態 (2026-02-18時点)](#1-現在の状態)
2. [環境設計: Development vs Production](#2-環境設計)
3. [残タスク一覧 (優先順)](#3-残タスク一覧)
4. [サービス別セットアップ手順](#4-サービス別セットアップ手順)
5. [CI/CD パイプライン設計](#5-cicd-パイプライン設計)
6. [環境変数の完全マトリックス](#6-環境変数の完全マトリックス)
7. [CLI リファレンス](#7-cli-リファレンス)

---

## 1. 現在の状態

### 1.1 完了済み

| 項目 | 状態 | 詳細 |
|------|------|------|
| レガシーコード削除 | 完了 | 19ファイル削除 (旧Stripe webhook, 旧pricing, 旧account controllers等) |
| middleware.ts 更新 | 完了 | `/api/webhooks(.*)` → `/api/webhooks/clerk(.*)` に変更 |
| docker-compose.yml 更新 | 完了 | stripe-cli forward先を `/api/subscription/webhook` に変更 |
| ベースラインマイグレーション | 完了 | 33個の旧マイグレーション → `00000000000000_baseline.sql` (3,409行) に統合 |
| 旧マイグレーションアーカイブ | 完了 | `supabase/migrations/_archive/` に33ファイル移動 |
| seed.sql 作成 | 完了 | plan_tiers + article_generation_flows + 9 flow_steps |
| データ移行スクリプト | 完了 | `scripts/migrate-data.py` (Supabase REST API経由) |
| 新Production Supabase作成 | 完了 | `tkkbhglcudsxcwxdyplp` にベースライン適用済み |
| データ移行実行 | 完了 | 全31テーブル、ミスマッチ0 |

### 1.2 Supabaseプロジェクト

| 用途 | Project Ref | 名前 | 状態 |
|------|------------|------|------|
| **Production (新)** | `tkkbhglcudsxcwxdyplp` | (新規作成) | ベースライン適用済み、全データ移行済み |
| **Development (新)** | `dddprfuwksduqsimiylg` | `-dev` | 新規作成、クリーン状態 |

### 1.3 未完了 (コードベースの問題)

| 優先度 | 問題 | 箇所 |
|--------|------|------|
| **HIGH** | ローカル絶対パス | `backend/app/core/config.py:143` — `/home/als0028/...` |
| **HIGH** | GCSバケット名ハードコード | `frontend/next.config.js` — `marketing-automation-images` |
| **HIGH** | 移行用env vars残存 | `backend/.env` — `OLD_SUPABASE_*`, `NEW_SUPABASE_*` |
| **MEDIUM** | TypeScript型未再生成 | `(supabase as any)` キャストが4+箇所に残存 |
| **MEDIUM** | Clerk Third-Party Auth未設定 | 新Supabaseプロジェクトに未接続 |
| **MEDIUM** | 本番env vars未切替 | Vercel/Cloud Runが旧Supabaseを指したまま |

### 1.4 認証キーの状態

| サービス | 現在のキー | 用途 |
|---------|-----------|------|
| **Clerk** | `pk_test_*` / `sk_test_*` | Development インスタンスのみ。Production インスタンス未作成 |
| **Stripe** | `sk_test_*` / `pk_test_*` | テストモードのみ。ライブモード未設定 |
| **Supabase** | 旧プロジェクトのキー | まだ本番切替していない |

---

## 2. 環境設計

### 2.1 全体構成図

```
┌──────────────────────────────────────────────────────────────┐
│                      Git Repository                          │
│                                                              │
│   feat/* ──PR──▶ develop ──PR──▶ main                       │
│                      │                │                      │
│                      ▼                ▼                      │
│              ┌── Development ──┐  ┌── Production ──┐        │
│              │                 │  │                │        │
│              │  Vercel         │  │  Vercel        │        │
│              │  (Preview)      │  │  (Production)  │        │
│              │                 │  │                │        │
│              │  Cloud Run      │  │  Cloud Run     │        │
│              │  (dev service)  │  │  (prod service)│        │
│              │                 │  │                │        │
│              │  Supabase       │  │  Supabase      │        │
│              │  pytxohnkky..   │  │  tkkbhglcu..   │        │
│              │                 │  │                │        │
│              │  Clerk Dev      │  │  Clerk Prod    │        │
│              │  pk_test_*      │  │  pk_live_*     │        │
│              │                 │  │                │        │
│              │  Stripe Test    │  │  Stripe Live   │        │
│              │  sk_test_*      │  │  sk_live_*     │        │
│              └─────────────────┘  └────────────────┘        │
└──────────────────────────────────────────────────────────────┘
```

### 2.2 環境×サービス マトリックス

| サービス | Development | Production |
|---------|-------------|------------|
| **Frontend** | Vercel Preview (`develop` ブランチ) | Vercel Production (`main` ブランチ) |
| **Backend** | Cloud Run `backend-dev` (min=0) | Cloud Run `backend-prod` (min=1) |
| **DB** | Supabase `dddprfuwksduqsimiylg` | Supabase `tkkbhglcudsxcwxdyplp` |
| **Auth** | Clerk Development (`pk_test_*`) | Clerk Production (`pk_live_*`) |
| **決済** | Stripe テストモード (`sk_test_*`) | Stripe ライブモード (`sk_live_*`) |
| **Storage** | GCS `blogai-images-dev` | GCS `blogai-images-prod` |
| **Secrets** | `.env` ファイル | GCP Secret Manager |

### 2.3 Clerk 環境分離

| 項目 | Development | Production |
|------|-------------|------------|
| インスタンスタイプ | Development | Production |
| キー | `pk_test_*` / `sk_test_*` | `pk_live_*` / `sk_live_*` |
| ドメイン | `*.clerk.accounts.dev` | カスタムドメイン必須 |
| OAuth | Clerk共有クレデンシャル | 自前のOAuthアプリ登録 |
| ユーザーDB | 完全に別（同一メールでも別user_id） | 別 |
| Webhook secret | dev用 | prod用 |
| Supabase連携 | dev Supabaseに接続 | prod Supabaseに接続 |

**重要**: Clerk Production インスタンスを使うには:
1. カスタムドメインの設定が必須
2. Social Login (Google等) を使う場合は自前のOAuth Clientの登録が必要
3. 既存の Development ユーザーは Production に自動移行されない（別DB）

### 2.4 Stripe 環境分離

| 項目 | Development | Production |
|------|-------------|------------|
| モード | テストモード | ライブモード |
| API Key | `sk_test_*` / `pk_test_*` | `sk_live_*` / `pk_live_*` |
| Price ID | テスト用（環境変数で管理） | ライブ用（環境変数で管理） |
| Webhook | `localhost` (CLI) or dev URL | prod URL + signing secret |
| テストカード | `4242 4242 4242 4242` | 実カード |

**Price ID の管理**: テストとライブでIDが完全に異なる。環境変数 `STRIPE_PRICE_ID`, `STRIPE_PRICE_ADDON_ARTICLES` で管理。

### 2.5 Supabase-Clerk 連携 (Third-Party Auth)

各Supabaseプロジェクトに対応するClerkインスタンスを接続:

| Supabase プロジェクト | 接続する Clerk |
|---------------------|---------------|
| `dddprfuwksduqsimiylg` (dev) | Clerk Development インスタンス |
| `tkkbhglcudsxcwxdyplp` (prod) | Clerk Production インスタンス |

設定手順 (各環境で実施):
1. **Clerk Dashboard** → Integrations → Supabase → Activate → Clerk domain をコピー
2. **Supabase Dashboard** → Authentication → Sign In / Up → Add provider → Clerk → domain を貼り付け

これにより、フロントエンドの `accessToken` コールバック経由のClerk JWTをSupabaseが認識し、RLSポリシーが正しく動作する。

---

## 3. 残タスク一覧

### Phase A: コードベース修正 (ブランチ内作業、無停止)

| # | タスク | 優先度 | 詳細 |
|---|--------|--------|------|
| A1 | `config.py` 絶対パス削除 | HIGH | `backend/app/core/config.py:143` の `/home/als0028/...` を削除 |
| A2 | GCSバケット名を環境変数化 | HIGH | `frontend/next.config.js` の `marketing-automation-images` → `process.env.NEXT_PUBLIC_GCS_BUCKET_NAME` |
| A3 | `.env.example` 更新 | HIGH | 本番URLを削除、`NEXT_PUBLIC_GCS_BUCKET_NAME` 追加、移行用変数テンプレート削除 |
| A4 | `backend/.env` から移行用変数削除 | MEDIUM | `OLD_SUPABASE_*`, `NEW_SUPABASE_*` を削除 |
| A5 | TypeScript型再生成 | MEDIUM | 新Supabaseにリンク → `bun run generate-types` → `(supabase as any)` キャスト除去 |
| A6 | `@shintairiku.jp` ハードコードを環境変数化 | LOW | backend 3箇所 + frontend 5箇所 → `ADMIN_EMAIL_DOMAIN` 環境変数 |
| A7 | `frontend/Dockerfile` からシークレットARG削除 | MEDIUM | `STRIPE_SECRET_KEY`, `SUPABASE_SERVICE_ROLE_KEY` のビルドARGを削除 |

### Phase B: 外部サービス設定 (Dashboard作業、無停止)

| # | タスク | 優先度 | 詳細 |
|---|--------|--------|------|
| B1 | Supabase-Clerk連携 (prod) | HIGH | 新Supabase `tkkbhglcu..` に Clerk Third-Party Auth を設定 |
| B2 | Supabase-Clerk連携 (dev) | HIGH | 旧Supabase `pytxohnkky..` にも同様に設定 |
| B3 | Clerk Production インスタンス作成 | HIGH | カスタムドメイン設定、OAuth Client登録、Webhook endpoint登録 |
| B4 | Stripe ライブモード設定 | HIGH | Products/Prices作成、Webhook endpoint登録、signing secret取得 |
| B5 | Stripe 旧Webhook削除 | MEDIUM | Dashboard で `/api/webhooks` endpoint が残っていれば削除 |
| B6 | GCP Artifact Registry 作成 | MEDIUM | `asia-northeast1` にDockerリポジトリ作成 |
| B7 | GCP Secret Manager にシークレット登録 | MEDIUM | prod用の全APIキー・シークレットを登録 |
| B8 | GCP Workload Identity Federation | MEDIUM | GitHub Actions → GCP のキーレス認証セットアップ |
| B9 | Vercel 環境変数設定 | HIGH | Production / Preview のスコープ別に全変数設定 |
| B10 | Cloud Run prod/dev サービス作成 | HIGH | `backend-prod` (min=1) + `backend-dev` (min=0) |
| B11 | カスタムドメイン設定 | HIGH | Vercel + Cloud Run + Clerk に本番ドメインを設定 |
| B12 | Dev Supabase リセット | LOW | `pytxohnkky..` を `supabase db reset` でクリーンベースライン化 |

### Phase C: CI/CD パイプライン (ブランチ内作業、無停止)

| # | タスク | 優先度 | 詳細 |
|---|--------|--------|------|
| C1 | `ci-frontend.yml` 作成 | HIGH | PR時: lint + build チェック |
| C2 | `ci-backend.yml` 作成 | HIGH | PR時: ruff + Docker build テスト |
| C3 | `deploy-frontend.yml` 作成 | HIGH | develop→Staging, main→Production (Vercel CLI) |
| C4 | `deploy-backend.yml` 作成 | HIGH | develop→dev Cloud Run, main→prod Cloud Run |
| C5 | `db-migrations.yml` 作成 | MEDIUM | migration変更時: Supabase db push |
| C6 | GitHub Environments 作成 | MEDIUM | `development`, `production` + 保護ルール |
| C7 | ブランチ保護ルール設定 | MEDIUM | main: PR必須+レビュー+CI通過, develop: PR必須+CI通過 |

### Phase D: 本番切替 (ダウンタイム30-60分)

| # | タスク | 優先度 | 詳細 |
|---|--------|--------|------|
| D1 | メンテナンスモード有効化 | - | ユーザー事前通知、深夜JST推奨 |
| D2 | 最終データ同期 | HIGH | 切替直前に旧→新の差分データを再移行 |
| D3 | Vercel env vars を新Supabaseに切替 | HIGH | `NEXT_PUBLIC_SUPABASE_URL` 等3変数 |
| D4 | Cloud Run env vars を新Supabaseに切替 | HIGH | `SUPABASE_URL` 等3変数 |
| D5 | Vercel + Cloud Run 再デプロイ | HIGH | env vars変更を反映 |
| D6 | クリティカルフロー検証 | HIGH | ログイン、ブログ生成、WordPress、サブスク、管理画面、Realtime |
| D7 | メンテナンスモード解除 | - | 検証完了後 |

### Phase E: 本番切替後の整理 (無停止)

| # | タスク | 優先度 | 詳細 |
|---|--------|--------|------|
| E1 | CLAUDE.md 更新 | HIGH | 移行記録、新プロジェクトID、環境分離の変更を記録 |
| E2 | ドキュメント整理 | MEDIUM | この戦略ドキュメントの最終更新 |
| E3 | `_archive/` ディレクトリ削除判断 | LOW | 旧33マイグレーションのアーカイブを保持するか削除するか |

---

## 4. サービス別セットアップ手順

### 4.1 Clerk

#### Development (現在使用中のインスタンス)
- 既存のまま使用
- Supabase dev プロジェクト (`pytxohnkky..`) と Third-Party Auth 連携を設定

#### Production (新規作成)
```
1. Clerk Dashboard → 新アプリケーション作成 or 既存の Production インスタンスへ切替
2. カスタムドメイン設定 (例: auth.blogai.jp)
3. Social Login: Google OAuth Client を自前で登録
   - Google Cloud Console → APIs & Services → Credentials → OAuth 2.0 Client
   - Authorized redirect URI: Clerk Dashboardに表示されるURLを設定
4. Webhook endpoint 登録:
   - Production URL: https://app.blogai.jp/api/webhooks/clerk
   - Events: user.created, user.updated, user.deleted
   - Signing secret → 環境変数 CLERK_WEBHOOK_SECRET に設定
5. Supabase連携:
   - Clerk Dashboard → Integrations → Supabase → Activate
   - Clerk domain をコピー
   - Supabase Dashboard (prod) → Auth → Sign In/Up → Add Clerk → domain 貼付
```

### 4.2 Stripe

#### Development (テストモード)
- 現在のキー (`sk_test_*`) をそのまま使用
- Webhook: `stripe listen --forward-to localhost:3000/api/subscription/webhook`

#### Production (ライブモード)
```
1. Stripe Dashboard → ライブモードに切替
2. Products/Prices 作成:
   - 個人プラン: ¥29,800/月 → Price ID をメモ → STRIPE_PRICE_ID
   - チームプラン: ¥29,800/席/月 → Price ID をメモ (同一 or 別)
   - アドオン: 記事追加パック → Price ID をメモ → STRIPE_PRICE_ADDON_ARTICLES
3. Webhook endpoint 登録:
   - URL: https://app.blogai.jp/api/subscription/webhook
   - Events: checkout.session.completed, customer.subscription.created,
     customer.subscription.updated, customer.subscription.deleted,
     invoice.payment_succeeded
   - Signing secret → STRIPE_WEBHOOK_SECRET
4. Customer Portal 設定 (ライブモード)
```

### 4.3 Supabase

#### Development (`dddprfuwksduqsimiylg`)
```
1. supabase link --project-ref dddprfuwksduqsimiylg
2. supabase db reset  # 全データ削除 → ベースライン適用 → seed実行
3. Clerk Dev インスタンスと Third-Party Auth 連携
```

#### Production (`tkkbhglcudsxcwxdyplp`)
```
- スキーマ適用済み ✓
- データ移行済み ✓
- Clerk Prod インスタンスと Third-Party Auth 連携 (B1)
- Realtime 有効化確認
```

### 4.4 Google Cloud

#### Artifact Registry
```bash
gcloud artifacts repositories create marketing-automation \
  --repository-format=docker \
  --location=asia-northeast1 \
  --project=marketing-automation-461305
```

#### Cloud Run (2サービス)
```bash
# Production
gcloud run deploy backend-prod \
  --image=asia-northeast1-docker.pkg.dev/PROJECT/marketing-automation/backend:SHA \
  --region=asia-northeast1 \
  --no-allow-unauthenticated \
  --min-instances=1 --max-instances=10 \
  --cpu=1 --memory=512Mi --timeout=300 \
  --update-secrets=OPENAI_API_KEY=openai-api-key-prod:latest,...

# Development
gcloud run deploy backend-dev \
  --image=asia-northeast1-docker.pkg.dev/PROJECT/marketing-automation/backend:SHA \
  --region=asia-northeast1 \
  --no-allow-unauthenticated \
  --min-instances=0 --max-instances=3 \
  --cpu=1 --memory=512Mi --timeout=300 \
  --update-secrets=OPENAI_API_KEY=openai-api-key-dev:latest,...
```

#### Secret Manager
```bash
# 各シークレットを環境別に作成
for secret in openai-api-key supabase-service-role-key clerk-secret-key stripe-secret-key; do
  echo -n "VALUE" | gcloud secrets create ${secret}-prod --data-file=-
  echo -n "VALUE" | gcloud secrets create ${secret}-dev --data-file=-
done
```

#### Workload Identity Federation (GitHub Actions → GCP)
```bash
# Pool + Provider 作成 (1回のみ)
gcloud iam workload-identity-pools create github-actions-pool \
  --location=global --display-name="GitHub Actions"

gcloud iam workload-identity-pools providers create-oidc github-provider \
  --location=global \
  --workload-identity-pool=github-actions-pool \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository" \
  --attribute-condition="assertion.repository=='YOUR_ORG/marketing-automation'" \
  --issuer-uri="https://token.actions.githubusercontent.com"
```

### 4.5 Vercel

#### 環境変数スコーピング
```bash
# Production 環境 (main ブランチ)
vercel env add NEXT_PUBLIC_SUPABASE_URL production      # prod Supabase URL
vercel env add NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY production  # pk_live_*
vercel env add STRIPE_SECRET_KEY production              # sk_live_*

# Preview 環境 (develop + feature branches)
vercel env add NEXT_PUBLIC_SUPABASE_URL preview          # dev Supabase URL
vercel env add NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY preview  # pk_test_*
vercel env add STRIPE_SECRET_KEY preview                  # sk_test_*

# Development 環境 (ローカル開発用)
vercel env add NEXT_PUBLIC_SUPABASE_URL development       # dev Supabase URL
```

#### ドメイン設定
- `main` ブランチ → `app.blogai.jp` (Production)
- `develop` ブランチ → `dev.blogai.jp` (Preview, ブランチ固定ドメイン)

---

## 5. CI/CD パイプライン設計

### 5.1 ワークフロー構成

```
.github/workflows/
├── ci-frontend.yml        # PR時: lint + build
├── ci-backend.yml         # PR時: ruff + Docker build
├── deploy-frontend.yml    # develop/main push: Vercel デプロイ
├── deploy-backend.yml     # develop/main push: Cloud Run デプロイ
└── db-migrations.yml      # migration変更時: Supabase db push
```

### 5.2 トリガーマトリックス

| イベント | Frontend CI | Backend CI | Frontend Deploy | Backend Deploy | DB Migration |
|---------|------------|-----------|----------------|---------------|-------------|
| PR → develop | `frontend/**` | `backend/**` | - | - | - |
| PR → main | `frontend/**` | `backend/**` | - | - | - |
| push → develop | - | - | Dev デプロイ | Dev デプロイ | Dev push |
| push → main | - | - | **承認後** Prod | **承認後** Prod | **承認後** Prod |

### 5.3 GitHub Environments

| 環境 | 承認者 | ブランチ制限 | Secrets |
|------|--------|-------------|---------|
| `development` | なし | `develop` | dev Supabase, Clerk test, Stripe test |
| `production` | 1名以上 | `main` | prod Supabase, Clerk live, Stripe live |

---

## 6. 環境変数の完全マトリックス

### 6.1 Frontend (Vercel)

| 変数 | Development (local) | Preview (develop) | Production (main) |
|------|--------------------|--------------------|-------------------|
| `NEXT_PUBLIC_SUPABASE_URL` | pytxohnkky.. | pytxohnkky.. | tkkbhglcu.. |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | dev anon key | dev anon key | prod anon key |
| `SUPABASE_SERVICE_ROLE_KEY` | dev service key | dev service key | prod service key |
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | `pk_test_*` | `pk_test_*` | `pk_live_*` |
| `CLERK_SECRET_KEY` | `sk_test_*` | `sk_test_*` | `sk_live_*` |
| `CLERK_WEBHOOK_SECRET` | dev whsec | dev whsec | prod whsec |
| `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY` | `pk_test_*` | `pk_test_*` | `pk_live_*` |
| `STRIPE_SECRET_KEY` | `sk_test_*` | `sk_test_*` | `sk_live_*` |
| `STRIPE_WEBHOOK_SECRET` | CLI生成 | dev whsec | prod whsec |
| `STRIPE_PRICE_ID` | test Price | test Price | live Price |
| `STRIPE_PRICE_ADDON_ARTICLES` | test Price | test Price | live Price |
| `NEXT_PUBLIC_API_BASE_URL` | localhost:8080 | dev Cloud Run URL | prod Cloud Run URL |
| `NEXT_PUBLIC_APP_URL` | localhost:3000 | dev.blogai.jp | app.blogai.jp |
| `CLOUD_RUN_AUDIENCE_URL` | (未設定) | dev *.run.app | prod *.run.app |
| `GOOGLE_SA_KEY_BASE64` | (未設定) | dev SA Base64 | prod SA Base64 |
| `NEXT_PUBLIC_GCS_BUCKET_NAME` | dev bucket | dev bucket | prod bucket |

### 6.2 Backend (Cloud Run)

| 変数 | Development | Production | 管理方法 |
|------|-------------|------------|---------|
| `SUPABASE_URL` | pytxohnkky.. | tkkbhglcu.. | Secret Manager |
| `SUPABASE_ANON_KEY` | dev key | prod key | Secret Manager |
| `SUPABASE_SERVICE_ROLE_KEY` | dev key | prod key | Secret Manager |
| `OPENAI_API_KEY` | 共通 | 共通 | Secret Manager |
| `GEMINI_API_KEY` | 共通 | 共通 | Secret Manager |
| `CLERK_SECRET_KEY` | `sk_test_*` | `sk_live_*` | Secret Manager |
| `CLERK_PUBLISHABLE_KEY` | `pk_test_*` | `pk_live_*` | Secret Manager |
| `STRIPE_SECRET_KEY` | `sk_test_*` | `sk_live_*` | Secret Manager |
| `STRIPE_WEBHOOK_SECRET` | dev whsec | prod whsec | Secret Manager |
| `ALLOWED_ORIGINS` | dev URL | prod URL | env var (inline) |
| `FRONTEND_URL` | dev URL | prod URL | env var (inline) |
| `GCS_BUCKET_NAME` | dev bucket | prod bucket | env var (inline) |
| `CREDENTIAL_ENCRYPTION_KEY` | dev key | prod key | Secret Manager |

---

## 7. CLI リファレンス

### Vercel
```bash
vercel link                                    # プロジェクトリンク
vercel env add VAR production                  # Production変数追加
vercel env add VAR preview develop             # Preview (developブランチ固有)
vercel env pull .env.local                     # Development変数ダウンロード
vercel deploy                                  # Preview デプロイ
vercel deploy --prod                           # Production デプロイ
```

### Supabase
```bash
supabase link --project-ref REF --password PW  # リンク
SUPABASE_DB_PASSWORD=PW supabase db push       # マイグレーション適用
supabase db reset                              # ローカルDB or リンク先リセット
supabase gen types typescript --linked          # TypeScript型生成
```

### gcloud (Cloud Run)
```bash
gcloud auth login                              # 認証
gcloud run deploy SERVICE --image=IMAGE ...    # デプロイ
gcloud run services update-traffic SERVICE --to-latest  # トラフィック切替
gcloud secrets create NAME --data-file=-       # シークレット作成
```

### Stripe
```bash
stripe listen --forward-to localhost:3000/api/subscription/webhook  # ローカルWebhook
stripe trigger checkout.session.completed      # テストイベント
```

---

## 付録: 推奨実行順序

Phase間の依存関係を考慮した推奨順序:

```
A1-A4 (コード修正) ─────────────────────────┐
                                             ├──▶ コミット & PR
A5 (型再生成) ──────────────────────────────┘

B3 (Clerk Prod作成) ─┐
B4 (Stripe Live設定) ─┤
B6 (Artifact Registry)┼──▶ B9 (Vercel env) ──▶ D1-D7 (本番切替)
B7 (Secret Manager) ──┤
B10 (Cloud Run作成) ──┘

B1-B2 (Supabase-Clerk連携) ──▶ 独立して実施可能

C1-C7 (CI/CD) ──▶ 本番切替後でもOK（優先度は本番切替より低い）

E1-E3 (整理) ──▶ 最後
```

**最短パス**: A1-A5 → B1-B4,B9-B11 → D1-D7 → E1

---

## 付録: 情報ソース

- [Clerk: Supabase Integration](https://clerk.com/docs/guides/development/integrations/databases/supabase)
- [Supabase: Clerk Third-Party Auth](https://supabase.com/docs/guides/auth/third-party/clerk)
- [Clerk: Managing Environments](https://clerk.com/docs/guides/development/managing-environments)
- [Stripe: Sandboxes](https://docs.stripe.com/sandboxes)
- [Vercel: Set Up a Staging Environment](https://vercel.com/kb/guide/set-up-a-staging-environment-on-vercel)
- [Google Cloud: Workload Identity Federation](https://cloud.google.com/blog/products/identity-security/enabling-keyless-authentication-from-github-actions)
- [Supabase: Managing Environments](https://supabase.com/docs/guides/deployment/managing-environments)
