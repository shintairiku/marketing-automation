# 環境分離・デプロイ戦略ガイド

> **作成日**: 2026-02-18
> **対象**: BlogAI / Marketing Automation Platform
> **ブランチ戦略**: `feature/*` → `develop` → `main`

---

## 目次

1. [現状の棚卸し](#1-現状の棚卸し)
2. [推奨アーキテクチャ](#2-推奨アーキテクチャ)
3. [CI/CD パイプライン設計](#3-cicd-パイプライン設計)
4. [外部サービスの環境分離](#4-外部サービスの環境分離)
5. [環境変数の完全マトリックス](#5-環境変数の完全マトリックス)
6. [コスト見積もり](#6-コスト見積もり)
7. [実装ステップ](#7-実装ステップ)
8. [CLI リファレンス](#8-cli-リファレンス)
9. [GitHub Actions ワークフロー例](#9-github-actions-ワークフロー例)
10. [コードベースの要修正箇所](#10-コードベースの要修正箇所)

---

## 1. 現状の棚卸し

### 1.1 利用可能なCLIツール

| ツール | 状態 | バージョン | 備考 |
|--------|------|-----------|------|
| **gcloud** | インストール済み（認証期限切れ） | 555.0.0 | `gcloud auth login` が必要 |
| **GitHub CLI (gh)** | インストール済み・認証OK | 2.4.0 | `als141` でログイン済み |
| **Docker** | インストール済み | 28.2.2 | `docker compose` (plugin形式) を使用 |
| **Stripe CLI** | インストール済み | 1.34.0 | |
| **Bun** | インストール済み | 1.3.6 | |
| **uv** | インストール済み | 0.9.5 | |
| **Node.js** | fnm管理 | 22.14.0 | |
| **Vercel CLI** | 未インストール（`npx`で利用可能） | 50.18.2 | グローバルインストール推奨 |
| **Supabase CLI** | 未インストール（`npx`で利用可能） | 2.76.9 | グローバルインストール推奨 |

### 1.2 プロジェクトリンク状態

| サービス | 状態 | 必要なアクション |
|---------|------|----------------|
| **Vercel** | 未リンク（`frontend/.vercel/` なし） | `vercel link` |
| **Supabase** | 未リンク（`shared/supabase/.supabase/` なし） | `supabase link` |
| **GCP** | プロジェクト設定済み（`marketing-automation-461305`）、認証期限切れ | `gcloud auth login` |

### 1.3 現在のCI/CD状態

- **GitHub Actions**: `backend-docker-build.yml` のみ（ビルド+スモークテストのみ、デプロイなし）
- **フロントエンドCI**: 存在しない
- **デプロイ**: 手動
- **環境分離**: なし（dev/staging/prodの区別がない）

---

## 2. 推奨アーキテクチャ

### 2.1 全体構成図

```
┌──────────────────────────────────────────────────────────────┐
│                      Git Repository                          │
│                                                              │
│   feature/* ──PR──▶ develop ──PR──▶ main                    │
│                        │                │                    │
│                        ▼                ▼                    │
│                 ┌── Staging ──┐   ┌── Production ──┐        │
│                 │             │   │                │        │
│                 │  Vercel     │   │  Vercel        │        │
│                 │  (Preview)  │   │  (Production)  │        │
│                 │             │   │                │        │
│                 │  Cloud Run  │   │  Cloud Run     │        │
│                 │  (staging)  │   │  (production)  │        │
│                 │             │   │                │        │
│                 │  Supabase   │   │  Supabase      │        │
│                 │  (staging)  │   │  (production)  │        │
│                 │             │   │                │        │
│                 │  Clerk Dev  │   │  Clerk Prod    │        │
│                 │  Stripe Test│   │  Stripe Live   │        │
│                 └─────────────┘   └────────────────┘        │
└──────────────────────────────────────────────────────────────┘
```

### 2.2 環境×サービス マトリックス

| サービス | ローカル開発 | Staging (develop) | Production (main) |
|---------|-------------|-------------------|-------------------|
| **Frontend** | `bun run dev` (localhost:3000) | Vercel Preview (`staging.example.com`) | Vercel Production (`app.example.com`) |
| **Backend** | `uv run uvicorn` (localhost:8080) | Cloud Run `backend-staging` | Cloud Run `backend-production` |
| **DB** | Supabase ローカル or 開発プロジェクト | Supabase Staging プロジェクト | Supabase Production プロジェクト |
| **Auth** | Clerk Development (`pk_test_`) | Clerk Development (`pk_test_`) | Clerk Production (`pk_live_`) |
| **決済** | Stripe テスト + CLI | Stripe テスト/Sandbox | Stripe ライブ |
| **Storage** | ローカル or GCS dev バケット | GCS staging バケット | GCS production バケット |
| **API通信** | 直接 localhost:8080 | Vercel → IAM → Cloud Run | Vercel → IAM → Cloud Run |

### 2.3 ドメイン設計（例）

| 環境 | Frontend | Backend |
|------|----------|---------|
| ローカル | `localhost:3000` | `localhost:8080` |
| Staging | `staging.blogai.jp` (Vercel Preview, developブランチにドメイン割当) | `staging-xxx.run.app` (Cloud Run staging) |
| Production | `app.blogai.jp` (Vercel Production) | `api.blogai.jp` or `xxx.run.app` (Cloud Run production) |

---

## 3. CI/CD パイプライン設計

### 3.1 ワークフロー構成

```
.github/workflows/
├── ci-frontend.yml        # PR時: lint + build チェック
├── ci-backend.yml         # PR時: lint + pytest + Docker build テスト
├── deploy-frontend.yml    # develop/main push時: Vercel デプロイ
├── deploy-backend.yml     # develop/main push時: Cloud Run デプロイ
└── db-migrations.yml      # migration変更時: Supabase db push
```

### 3.2 トリガーマトリックス

| イベント | Frontend CI | Backend CI | Frontend Deploy | Backend Deploy | DB Migration |
|---------|------------|-----------|----------------|---------------|-------------|
| PR → develop | `frontend/**` 変更時 | `backend/**` 変更時 | - | - | - |
| PR → main | `frontend/**` 変更時 | `backend/**` 変更時 | - | - | - |
| push → develop | - | - | Staging デプロイ | Staging デプロイ | Staging push |
| push → main | - | - | **承認後** Prod デプロイ | **承認後** Prod デプロイ | **承認後** Prod push |

### 3.3 GCP認証: Workload Identity Federation

SAキーJSONファイルの管理が不要になるキーレス認証。GitHub Actions からGCPへのOIDC連携:

- 短命トークン（~1時間自動失効）
- リポジトリ・ブランチ単位でスコープ制限可能
- SAキー漏洩リスクゼロ

**セットアップコマンド**:
```bash
PROJECT_ID="marketing-automation-461305"
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
GITHUB_ORG="als141"  # or your org
GITHUB_REPO="marketing-automation"

# 1. 必要なAPIを有効化
gcloud services enable \
  iamcredentials.googleapis.com \
  artifactregistry.googleapis.com \
  run.googleapis.com \
  secretmanager.googleapis.com \
  --project=$PROJECT_ID

# 2. Workload Identity Pool 作成
gcloud iam workload-identity-pools create "github-actions-pool" \
  --project=$PROJECT_ID \
  --location="global" \
  --display-name="GitHub Actions Pool"

# 3. OIDC Provider 作成（リポジトリスコープ）
gcloud iam workload-identity-pools providers create-oidc "github-provider" \
  --project=$PROJECT_ID \
  --location="global" \
  --workload-identity-pool="github-actions-pool" \
  --display-name="GitHub Provider" \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.actor=assertion.actor,attribute.ref=assertion.ref" \
  --attribute-condition="assertion.repository=='${GITHUB_ORG}/${GITHUB_REPO}'" \
  --issuer-uri="https://token.actions.githubusercontent.com"

# 4. CI/CD用サービスアカウント作成
gcloud iam service-accounts create "github-actions-sa" \
  --project=$PROJECT_ID \
  --display-name="GitHub Actions CI/CD"

SA_EMAIL="github-actions-sa@${PROJECT_ID}.iam.gserviceaccount.com"

# 5. 必要なIAMロール付与
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/run.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/artifactregistry.writer"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/iam.serviceAccountUser"

# 6. GitHub ActionsがSAを偽装できるようバインド
gcloud iam service-accounts add-iam-policy-binding $SA_EMAIL \
  --project=$PROJECT_ID \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/github-actions-pool/attribute.repository/${GITHUB_ORG}/${GITHUB_REPO}"

# 7. Provider IDを取得（GitHub Secretsに設定）
gcloud iam workload-identity-pools providers describe "github-provider" \
  --project=$PROJECT_ID \
  --location="global" \
  --workload-identity-pool="github-actions-pool" \
  --format="value(name)"
```

※ 5分ほど伝播に時間がかかる

### 3.4 Docker イメージ管理: Artifact Registry

Container Registry は2025年3月に廃止済み。Artifact Registry を使用:

```bash
# リポジトリ作成
gcloud artifacts repositories create marketing-automation \
  --repository-format=docker \
  --location=asia-northeast1 \
  --description="Marketing Automation Docker images" \
  --project=$PROJECT_ID

# Docker認証設定
gcloud auth configure-docker asia-northeast1-docker.pkg.dev

# イメージ命名規則
# asia-northeast1-docker.pkg.dev/PROJECT_ID/marketing-automation/backend:GIT_SHA
```

- タグは **git SHA** を使用（`latest` は本番では非推奨）
- Vulnerability Scanning を有効化推奨

### 3.5 GitHub Environments 設定

| 環境 | 承認者 | 待機時間 | ブランチ制限 |
|------|--------|---------|-------------|
| `staging` | なし | なし | `develop` |
| `production` | 1-2名 | 5分 | `main` |

**GitHub Secretsの分離**:

```
# Repository Secrets（環境共通）
VERCEL_TOKEN
VERCEL_ORG_ID
VERCEL_PROJECT_ID
SUPABASE_ACCESS_TOKEN

# Environment: staging
GCP_WORKLOAD_IDENTITY_PROVIDER  (staging GCPプロジェクト用)
GCP_SERVICE_ACCOUNT
SUPABASE_PROJECT_ID             (staging Supabaseプロジェクト)
SUPABASE_DB_PASSWORD

# Environment: production
GCP_WORKLOAD_IDENTITY_PROVIDER  (production GCPプロジェクト用)
GCP_SERVICE_ACCOUNT
SUPABASE_PROJECT_ID             (production Supabaseプロジェクト)
SUPABASE_DB_PASSWORD
```

### 3.6 ブランチ保護ルール

**`main` ブランチ**:
- PR必須（直接pushを禁止）
- レビュー1名以上必須
- CI ステータスチェック必須（Frontend CI, Backend CI）
- ブランチ最新化必須
- force push禁止

**`develop` ブランチ**:
- PR必須
- CI ステータスチェック必須
- force push禁止

---

## 4. 外部サービスの環境分離

### 4.1 Clerk

| 項目 | 開発/Staging | Production |
|------|-------------|------------|
| インスタンス | Development (`pk_test_` / `sk_test_`) | Production (`pk_live_` / `sk_live_`) |
| ドメイン | `*.clerk.accounts.dev` | カスタムドメイン必須 |
| ユーザー上限 | 500人 | プラン依存 |
| OAuth | Clerk共有クレデンシャル（登録不要） | 自前のOAuthアプリ登録必須 |
| Webhook | 環境ごとに個別の signing secret | 同左 |
| JWKS | インスタンスごとに異なるエンドポイント | 同左 |

**重要な注意点**:
- Development と Production はユーザーDBが完全に別。同一メールでも異なる `user_id`
- Staging 用に **別のClerkアプリケーション** を作成し、そのProduction インスタンスを使うのが推奨
- 各環境のClerk webhook エンドポイントに対応する signing secret を個別に設定
- Vercel Preview デプロイメントには `pk_test_` キーを使用（動的URLでもOK）

**Supabase連携**: Clerk の Native Third-Party Auth Integration（2025年以降の新方式）を使用。各Supabaseプロジェクトの Auth > Third Party Auth > Clerk に、対応するClerkドメインを設定。

> 情報ソース: https://clerk.com/docs/guides/development/managing-environments

### 4.2 Stripe

| 項目 | 開発/Staging | Production |
|------|-------------|------------|
| モード | テストモード or Sandbox | ライブモード |
| API Key | `sk_test_` / `pk_test_` | `sk_live_` / `pk_live_` |
| Price ID | **テストとライブで完全に別のID** | 別のPrice ID |
| Webhook | 環境ごとに個別のendpoint + signing secret | 同左 |
| テストカード | `4242424242424242` | 実カード |
| Customer Portal | 環境ごとに個別設定 | 同左 |

**Price ID の管理戦略**:
- 方式1: 環境変数で管理（現在の方式）— `STRIPE_PRICE_ID=price_test_xxx` / `price_live_xxx`
- 方式2 (推奨): **`lookup_keys`** を使用。テスト/ライブで同じキー名（例: `personal_monthly`）を割り当て、APIで逆引き
  ```typescript
  const prices = await stripe.prices.list({
    lookup_keys: ['personal_monthly', 'team_monthly_per_seat'],
  });
  ```

**Sandbox（2025年の新機能）**: テストモードよりも完全に分離された環境。1アカウント最大5つ。ライブ設定のミラーリング可能。

**Stripe Test Clocks**: サブスクリプションのライフサイクルテスト（更新、日割り、猶予期間、キャンセル）を時間操作で実行可能。Staging環境での検証に活用推奨。

> 情報ソース:
> - https://docs.stripe.com/sandboxes
> - https://docs.stripe.com/billing/testing/test-clocks

### 4.3 Supabase

**推奨: 別プロジェクト方式**（ブランチングよりシンプル）

| 項目 | 方式A: 別プロジェクト（推奨） | 方式B: ブランチング |
|------|---------------------------|-------------------|
| コスト | Pro $25/月 + staging $10/月 = $35/月 | Pro $25/月 + branch ~$10/月 = $35/月 |
| 分離度 | 完全分離（独立プロジェクト） | 同一プロジェクト内の論理分離 |
| マイグレーション | `supabase link` → `supabase db push` を環境ごと | ブランチマージで自動適用 |
| セットアップ | シンプル | ブランチング2.0の学習コスト |
| RLS | 独立検証可能 | ブランチ内で検証 |

**別プロジェクト方式のワークフロー**:
```bash
# Staging
supabase link --project-ref STAGING_PROJECT_ID
supabase db push

# Production
supabase link --project-ref PRODUCTION_PROJECT_ID
supabase db push
```

**CI/CDでの自動適用**: GitHub Actions で `supabase/setup-cli@v1` → `supabase link` → `supabase db push`

**型生成**: マイグレーション後に `bun run generate-types` で TypeScript型を再生成。CIで型の整合性を検証可能。

**Free Tier の制約**:
- 2プロジェクトまで
- 7日間アクティビティなしで自動停止
- 500MB ストレージ制限
- → **Staging には使えない。Pro ($25/月) が必要**

> 情報ソース:
> - https://supabase.com/docs/guides/deployment/managing-environments
> - https://supabase.com/pricing

### 4.4 Google Cloud (Cloud Run / GCS / Secret Manager)

**環境分離の選択肢**:
- 方式A: **同一GCPプロジェクト、別サービス** — `backend-staging` / `backend-production`
- 方式B: **別GCPプロジェクト** — `myapp-staging` / `myapp-production`

方式Aがシンプル。IAMロールでアクセス制御。

**Secret Manager**: 機密情報は環境変数ではなくSecret Managerに格納:
```bash
# シークレット作成
echo -n "sk-xxx" | gcloud secrets create openai-api-key --data-file=-

# Cloud Runへの紐付け
gcloud run deploy backend-production \
  --update-secrets=OPENAI_API_KEY=openai-api-key:latest
```

**GCS バケット**: 環境ごとに別バケット
- `blogai-images-staging`
- `blogai-images-production`

**Cloud Run の推奨設定**:

| 設定 | Staging | Production |
|------|---------|-----------|
| CPU | 1 vCPU | 1 vCPU |
| Memory | 512Mi | 512Mi-1Gi |
| Min instances | 0 | 1 |
| Max instances | 3 | 10 |
| Concurrency | 80 | 80 |
| Timeout | 300s | 300s |
| 認証 | IAM (`--no-allow-unauthenticated`) | IAM |

---

## 5. 環境変数の完全マトリックス

### 5.1 Frontend (Vercel)

| 変数 | ローカル | Staging (Preview) | Production |
|------|---------|-------------------|------------|
| `NEXT_PUBLIC_SUPABASE_URL` | localhost:54321 | staging-xxx.supabase.co | prod-xxx.supabase.co |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | ローカルキー | stagingキー | prodキー |
| `SUPABASE_SERVICE_ROLE_KEY` | ローカルキー | stagingキー | prodキー |
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | `pk_test_` | `pk_test_` | `pk_live_` |
| `CLERK_SECRET_KEY` | `sk_test_` | `sk_test_` | `sk_live_` |
| `CLERK_WEBHOOK_SECRET` | `whsec_` (dev) | `whsec_` (staging) | `whsec_` (prod) |
| `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY` | `pk_test_` | `pk_test_` | `pk_live_` |
| `STRIPE_SECRET_KEY` | `sk_test_` | `sk_test_` | `sk_live_` |
| `STRIPE_WEBHOOK_SECRET` | CLI生成 | Dashboard生成 | Dashboard生成 |
| `STRIPE_PRICE_ID` | テスト用Price | テスト用Price | ライブ用Price |
| `STRIPE_PRICE_ADDON_ARTICLES` | テスト用Price | テスト用Price | ライブ用Price |
| `NEXT_PUBLIC_API_BASE_URL` | localhost:8080 | staging Cloud Run URL | prod Cloud Run URL |
| `NEXT_PUBLIC_APP_URL` | localhost:3000 | staging.example.com | app.example.com |
| `NEXT_PUBLIC_SITE_URL` | localhost:3000 | staging.example.com | app.example.com |
| `CLOUD_RUN_AUDIENCE_URL` | (未設定) | staging *.run.app | prod *.run.app |
| `GOOGLE_SA_KEY_BASE64` | (未設定) | staging SA Base64 | prod SA Base64 |

### 5.2 Backend (Cloud Run)

**非機密 (env vars inline)**:

| 変数 | Staging | Production |
|------|---------|------------|
| `ALLOWED_ORIGINS` | `https://staging.example.com` | `https://app.example.com` |
| `FRONTEND_URL` | `https://staging.example.com` | `https://app.example.com` |
| `GCS_BUCKET_NAME` | `blogai-images-staging` | `blogai-images-production` |
| `IMAGEN_MODEL_NAME` | `imagen-4.0-generate-preview-06-06` | 同左 |
| `GOOGLE_CLOUD_PROJECT` | project ID | 同左 |
| `GOOGLE_CLOUD_LOCATION` | `asia-northeast1` | 同左 |

**機密 (Secret Manager)**:

| 変数 | Secret名 (環境ごとに別の値) |
|------|---------------------------|
| `OPENAI_API_KEY` | `openai-api-key` |
| `GEMINI_API_KEY` | `gemini-api-key` |
| `SERPAPI_API_KEY` | `serpapi-api-key` |
| `SUPABASE_URL` | `supabase-url` |
| `SUPABASE_ANON_KEY` | `supabase-anon-key` |
| `SUPABASE_SERVICE_ROLE_KEY` | `supabase-service-role-key` |
| `CLERK_SECRET_KEY` | `clerk-secret-key` |
| `CLERK_PUBLISHABLE_KEY` | `clerk-publishable-key` |
| `STRIPE_SECRET_KEY` | `stripe-secret-key` |
| `STRIPE_WEBHOOK_SECRET` | `stripe-webhook-secret` |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | `gcp-sa-json` |
| `CREDENTIAL_ENCRYPTION_KEY` | `credential-encryption-key` |

### 5.3 Vercel での環境変数スコーピング

Vercel は変数を3つのスコープに分けて管理:

| スコープ | 適用タイミング | 用途 |
|---------|-------------|------|
| **Production** | `main` ブランチのデプロイ | 本番用の値 |
| **Preview** | `main` 以外のブランチのデプロイ | Staging/テスト用の値 |
| **Development** | `vercel dev` or `vercel env pull` | ローカル開発用 |

Preview スコープの変数は **特定ブランチにオーバーライド可能**。例えば `develop` ブランチ専用の `NEXT_PUBLIC_API_BASE_URL` を設定できる。

```bash
# ブランチ固有の変数設定
vercel env add NEXT_PUBLIC_API_BASE_URL preview develop
```

---

## 6. コスト見積もり

### 6.1 月額ランニングコスト（Staging + Production）

| サービス | Staging | Production | 合計 |
|---------|---------|------------|------|
| **Supabase** (Pro) | ~$10 (追加compute) | $25 (base) | **$35/月** |
| **Vercel** (Hobby/Pro) | $0 (Preview) | $0-20 | **$0-20/月** |
| **Cloud Run** | ~$5-15 (min=0) | ~$20-50 (min=1) | **$25-65/月** |
| **Clerk** | $0 (Dev) | $0-25 | **$0-25/月** |
| **Artifact Registry** | ~$1 | ~$1 | **~$2/月** |
| **Secret Manager** | ~$0.5 | ~$0.5 | **~$1/月** |
| **合計** | | | **~$63-148/月** |

### 6.2 初期費用

- なし（全サービスが従量課金 or 無料枠あり）

### 6.3 コスト最適化のポイント

- Staging の Cloud Run は `min-instances=0` で未使用時コストゼロ
- Vercel Hobby プラン（無料）で Preview デプロイは無制限
- Supabase の Staging プロジェクトは最小 Micro compute ($10/月)
- Staging の GCS バケットは使用量が少ないため ~$0

---

## 7. 実装ステップ

### Phase 1: 基盤整備（すぐやるべき）

1. **`gcloud auth login`** で認証を復活
2. **Vercel CLI セットアップ**: `bun add -g vercel` → `vercel link`
3. **Supabase CLI セットアップ**: `supabase link --project-ref <ref>`
4. **コードのハードコード修正**:
   - `config.py` のローカル絶対パス削除
   - `next.config.js` のGCSバケット名を環境変数化
   - `frontend/Dockerfile` からシークレットの ARG 削除
   - `.env.example` から本番URL削除

### Phase 2: Staging環境構築

5. **Supabase Staging プロジェクト作成** → マイグレーション適用
6. **Cloud Run Staging サービス作成** + Artifact Registry セットアップ
7. **Vercel 環境変数設定** (Preview = Staging 向け)
8. **Clerk Development インスタンスの Staging 用設定確認**
9. **Stripe テストモードの Webhook endpoint 登録** (staging URL)

### Phase 3: CI/CD パイプライン

10. **GitHub Environments 作成** (staging, production + 保護ルール)
11. **Workload Identity Federation セットアップ** (キーレスGCP認証)
12. **5つのGitHub Actions ワークフロー作成**:
    - `ci-frontend.yml`
    - `ci-backend.yml`
    - `deploy-frontend.yml`
    - `deploy-backend.yml`
    - `db-migrations.yml`
13. **ブランチ保護ルール設定** (main: レビュー必須 + CI通過必須)

### Phase 4: 本番移行

14. **Secret Manager にシークレット登録**
15. **Cloud Run Production サービスにシークレット紐付け**
16. **Vercel Production 環境変数設定** (`pk_live_` 等)
17. **カスタムドメイン設定** (frontend + backend)
18. **Stripe ライブモードの Webhook endpoint 登録**
19. **Clerk Production インスタンスのセットアップ**

---

## 8. CLI リファレンス

### 8.1 Vercel CLI

```bash
# インストール
bun add -g vercel

# ログイン
vercel login

# プロジェクトリンク
cd frontend && vercel link

# 環境変数管理
vercel env ls                                    # 一覧
vercel env add VAR_NAME production               # Production に追加
vercel env add VAR_NAME preview develop           # Preview (developブランチ固有)
vercel env pull .env.local                       # Development 環境変数をダウンロード

# デプロイ
vercel deploy                                    # Preview デプロイ
vercel deploy --prod                             # Production デプロイ
vercel build --prod && vercel deploy --prebuilt --prod  # ローカルビルド → デプロイ

# ドメイン
vercel domains add staging.example.com           # ドメイン追加
vercel domains ls                                # ドメイン一覧
```

### 8.2 gcloud CLI (Cloud Run)

```bash
# 認証
gcloud auth login
gcloud config set project marketing-automation-461305

# Cloud Run デプロイ
gcloud run deploy backend-staging \
  --image=asia-northeast1-docker.pkg.dev/PROJECT/repo/backend:SHA \
  --region=asia-northeast1 \
  --no-allow-unauthenticated \
  --min-instances=0 \
  --max-instances=3 \
  --cpu=1 --memory=512Mi \
  --timeout=300 \
  --set-env-vars=ALLOWED_ORIGINS=https://staging.example.com \
  --update-secrets=OPENAI_API_KEY=openai-api-key:latest

# サービス情報
gcloud run services list --region=asia-northeast1
gcloud run services describe backend-staging --region=asia-northeast1
gcloud run services describe backend-staging --region=asia-northeast1 --format="value(status.url)"

# リビジョン管理
gcloud run revisions list --service=backend-production --region=asia-northeast1

# トラフィック管理（カナリアリリース）
gcloud run deploy backend-production --image=NEW --no-traffic --tag=canary
gcloud run services update-traffic backend-production --to-tags=canary=5
gcloud run services update-traffic backend-production --to-tags=canary=25
gcloud run services update-traffic backend-production --to-latest  # 全トラフィック切替

# ロールバック
gcloud run services update-traffic backend-production \
  --to-revisions=REVISION_NAME=100

# ログ
gcloud run services logs tail backend-production --region=asia-northeast1

# Secret Manager
echo -n "value" | gcloud secrets create SECRET_NAME --data-file=-
gcloud secrets versions access latest --secret=SECRET_NAME
gcloud secrets add-iam-policy-binding SECRET_NAME \
  --member="serviceAccount:SA@PROJECT.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

# Artifact Registry
gcloud artifacts repositories create marketing-automation \
  --repository-format=docker --location=asia-northeast1
gcloud auth configure-docker asia-northeast1-docker.pkg.dev
docker build -t asia-northeast1-docker.pkg.dev/PROJECT/marketing-automation/backend:TAG ./backend
docker push asia-northeast1-docker.pkg.dev/PROJECT/marketing-automation/backend:TAG
```

### 8.3 Supabase CLI

```bash
# リンク
supabase link --project-ref PROJECT_ID

# マイグレーション
supabase db push                    # リモートに適用
supabase db push --dry-run          # ドライラン
supabase migration new NAME         # 新規マイグレーション作成
supabase migration list             # 適用状態確認

# 型生成
supabase gen types typescript --linked > src/types/database.types.ts

# ローカル開発
supabase start                      # ローカルDB起動
supabase db reset                   # リセット（全マイグレーション再適用 + seed）
supabase db diff -f NAME            # スキーマ変更を検出してマイグレーション生成

# テスト
supabase db lint                    # SQLリント
supabase test db                    # pgTAPテスト実行
```

### 8.4 Stripe CLI

```bash
# ログイン
stripe login

# Webhook転送（ローカル開発）
stripe listen --forward-to localhost:3000/api/subscription/webhook

# 特定イベントのみ転送
stripe listen \
  --events checkout.session.completed,customer.subscription.updated,invoice.payment_succeeded \
  --forward-to localhost:3000/api/subscription/webhook

# テストイベント発火
stripe trigger checkout.session.completed
stripe trigger customer.subscription.updated

# テストクロック（サブスクリプションテスト）
# → Stripe Dashboard で操作
```

---

## 9. GitHub Actions ワークフロー例

### 9.1 Frontend CI (`ci-frontend.yml`)

```yaml
name: Frontend CI
on:
  pull_request:
    branches: [main, develop]
    paths:
      - 'frontend/**'
      - '.github/workflows/ci-frontend.yml'

concurrency:
  group: frontend-ci-${{ github.ref }}
  cancel-in-progress: true

jobs:
  lint-and-build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: oven-sh/setup-bun@v2
      - run: bun install --frozen-lockfile
        working-directory: ./frontend
      - run: bun run lint
        working-directory: ./frontend
      - run: bun run build
        working-directory: ./frontend
        env:
          NEXT_PUBLIC_SUPABASE_URL: https://placeholder.supabase.co
          NEXT_PUBLIC_SUPABASE_ANON_KEY: placeholder
          NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY: pk_test_placeholder
          NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY: pk_test_placeholder
          NEXT_PUBLIC_API_BASE_URL: https://placeholder.example.com
          NEXT_PUBLIC_SITE_URL: https://placeholder.example.com
          NEXT_PUBLIC_APP_URL: https://placeholder.example.com
```

### 9.2 Backend CI (`ci-backend.yml`)

```yaml
name: Backend CI
on:
  pull_request:
    branches: [main, develop]
    paths:
      - 'backend/**'
      - '.github/workflows/ci-backend.yml'

concurrency:
  group: backend-ci-${{ github.ref }}
  cancel-in-progress: true

jobs:
  lint-and-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - uses: astral-sh/setup-uv@v4
        with:
          enable-cache: true
          cache-dependency-glob: 'backend/uv.lock'
      - run: uv sync --frozen
        working-directory: ./backend
      - run: uv run ruff check app
        working-directory: ./backend
      - run: uv run ruff format --check app
        working-directory: ./backend

  docker-build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - uses: docker/build-push-action@v6
        with:
          context: ./backend
          file: ./backend/Dockerfile
          push: false
          load: true
          tags: backend:test
          cache-from: type=gha
          cache-to: type=gha,mode=max
      - name: Test container starts
        run: |
          docker run --rm -d --name test-backend -p 8000:8000 -e PORT=8000 backend:test
          sleep 5
          curl -f http://localhost:8000/health || exit 1
          docker stop test-backend
```

### 9.3 Frontend Deploy (`deploy-frontend.yml`)

```yaml
name: Deploy Frontend
on:
  push:
    branches: [main, develop]
    paths:
      - 'frontend/**'

env:
  VERCEL_ORG_ID: ${{ secrets.VERCEL_ORG_ID }}
  VERCEL_PROJECT_ID: ${{ secrets.VERCEL_PROJECT_ID }}

jobs:
  deploy-staging:
    if: github.ref == 'refs/heads/develop'
    runs-on: ubuntu-latest
    environment: staging
    steps:
      - uses: actions/checkout@v4
      - run: npm install -g vercel@latest
      - run: vercel pull --yes --environment=preview --token=${{ secrets.VERCEL_TOKEN }}
        working-directory: ./frontend
      - run: vercel build --token=${{ secrets.VERCEL_TOKEN }}
        working-directory: ./frontend
      - run: vercel deploy --prebuilt --token=${{ secrets.VERCEL_TOKEN }}
        working-directory: ./frontend

  deploy-production:
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    environment: production
    steps:
      - uses: actions/checkout@v4
      - run: npm install -g vercel@latest
      - run: vercel pull --yes --environment=production --token=${{ secrets.VERCEL_TOKEN }}
        working-directory: ./frontend
      - run: vercel build --prod --token=${{ secrets.VERCEL_TOKEN }}
        working-directory: ./frontend
      - run: vercel deploy --prebuilt --prod --token=${{ secrets.VERCEL_TOKEN }}
        working-directory: ./frontend
```

### 9.4 Backend Deploy (`deploy-backend.yml`)

```yaml
name: Deploy Backend
on:
  push:
    branches: [main, develop]
    paths:
      - 'backend/**'

permissions:
  contents: read
  id-token: write

jobs:
  deploy-staging:
    if: github.ref == 'refs/heads/develop'
    runs-on: ubuntu-latest
    environment: staging
    env:
      REGION: asia-northeast1
      SERVICE: marketing-automation-backend-staging
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: ${{ secrets.GCP_WORKLOAD_IDENTITY_PROVIDER }}
          service_account: ${{ secrets.GCP_SERVICE_ACCOUNT }}
      - uses: google-github-actions/setup-gcloud@v2
      - run: gcloud auth configure-docker ${{ env.REGION }}-docker.pkg.dev
      - uses: docker/build-push-action@v6
        with:
          context: ./backend
          push: true
          tags: ${{ env.REGION }}-docker.pkg.dev/${{ vars.GCP_PROJECT_ID }}/marketing-automation/backend:${{ github.sha }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
      - uses: google-github-actions/deploy-cloudrun@v2
        with:
          service: ${{ env.SERVICE }}
          region: ${{ env.REGION }}
          image: ${{ env.REGION }}-docker.pkg.dev/${{ vars.GCP_PROJECT_ID }}/marketing-automation/backend:${{ github.sha }}
          flags: >-
            --min-instances=0
            --max-instances=3
            --cpu=1
            --memory=512Mi
            --timeout=300

  deploy-production:
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    environment: production
    env:
      REGION: asia-northeast1
      SERVICE: marketing-automation-backend
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: ${{ secrets.GCP_WORKLOAD_IDENTITY_PROVIDER }}
          service_account: ${{ secrets.GCP_SERVICE_ACCOUNT }}
      - uses: google-github-actions/setup-gcloud@v2
      - run: gcloud auth configure-docker ${{ env.REGION }}-docker.pkg.dev
      - uses: docker/build-push-action@v6
        with:
          context: ./backend
          push: true
          tags: |
            ${{ env.REGION }}-docker.pkg.dev/${{ vars.GCP_PROJECT_ID }}/marketing-automation/backend:${{ github.sha }}
            ${{ env.REGION }}-docker.pkg.dev/${{ vars.GCP_PROJECT_ID }}/marketing-automation/backend:latest
          cache-from: type=gha
          cache-to: type=gha,mode=max
      - id: deploy
        uses: google-github-actions/deploy-cloudrun@v2
        with:
          service: ${{ env.SERVICE }}
          region: ${{ env.REGION }}
          image: ${{ env.REGION }}-docker.pkg.dev/${{ vars.GCP_PROJECT_ID }}/marketing-automation/backend:${{ github.sha }}
          flags: >-
            --min-instances=1
            --max-instances=10
            --cpu=1
            --memory=512Mi
            --timeout=300
      - name: Health Check
        run: |
          sleep 10
          curl -sf "${{ steps.deploy.outputs.url }}/health" || exit 1
```

### 9.5 Database Migrations (`db-migrations.yml`)

```yaml
name: Database Migrations
on:
  push:
    branches: [main, develop]
    paths:
      - 'shared/supabase/migrations/**'

jobs:
  migrate-staging:
    if: github.ref == 'refs/heads/develop'
    runs-on: ubuntu-latest
    environment: staging
    steps:
      - uses: actions/checkout@v4
      - uses: supabase/setup-cli@v1
        with:
          version: latest
      - run: supabase link --project-ref ${{ secrets.SUPABASE_PROJECT_ID }}
        env:
          SUPABASE_ACCESS_TOKEN: ${{ secrets.SUPABASE_ACCESS_TOKEN }}
          SUPABASE_DB_PASSWORD: ${{ secrets.SUPABASE_DB_PASSWORD }}
      - run: supabase db push
        env:
          SUPABASE_ACCESS_TOKEN: ${{ secrets.SUPABASE_ACCESS_TOKEN }}
          SUPABASE_DB_PASSWORD: ${{ secrets.SUPABASE_DB_PASSWORD }}

  migrate-production:
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    environment: production
    steps:
      - uses: actions/checkout@v4
      - uses: supabase/setup-cli@v1
        with:
          version: latest
      - run: supabase link --project-ref ${{ secrets.SUPABASE_PROJECT_ID }}
        env:
          SUPABASE_ACCESS_TOKEN: ${{ secrets.SUPABASE_ACCESS_TOKEN }}
          SUPABASE_DB_PASSWORD: ${{ secrets.SUPABASE_DB_PASSWORD }}
      - run: supabase db push
        env:
          SUPABASE_ACCESS_TOKEN: ${{ secrets.SUPABASE_ACCESS_TOKEN }}
          SUPABASE_DB_PASSWORD: ${{ secrets.SUPABASE_DB_PASSWORD }}
```

---

## 10. コードベースの要修正箇所

### 10.1 HIGH 優先度

| # | 問題 | ファイル | 修正内容 |
|---|------|---------|---------|
| 1 | ローカル絶対パス | `backend/app/core/config.py:134` | `/home/als0028/...` パスを削除 |
| 2 | GCSバケット名ハードコード | `frontend/next.config.js:9` | `NEXT_PUBLIC_GCS_BUCKET_NAME` 環境変数を使用 |
| 3 | Dockerfileにシークレット | `frontend/Dockerfile` | `STRIPE_SECRET_KEY`, `SUPABASE_SERVICE_ROLE_KEY` のARGを削除 |
| 4 | `localhost:8008` ハードコード | `backend/app/domains/image_generation/service.py:267,282` | `settings.frontend_url` or 専用env var使用 |
| 5 | `@shintairiku.jp` 8箇所ハードコード | backend 3箇所 + frontend 5箇所 | `ADMIN_EMAIL_DOMAIN` 環境変数に統一 |

### 10.2 MEDIUM 優先度

| # | 問題 | ファイル | 修正内容 |
|---|------|---------|---------|
| 6 | 本番URLが `.env.example` に露出 | `backend/.env.example`, `frontend/.env.example` | プレースホルダーに置換 |
| 7 | `ALLOWED_ORIGINS` が settings 経由でない | `backend/main.py:24` | `settings` クラスに統合 |
| 8 | Clerk キーが settings 経由でない | `backend/app/common/auth.py:26-27` | `settings.clerk_*` を使用 |
| 9 | Clerk キーの直接 os.getenv | `backend/app/domains/organization/endpoints.py:58` | `settings.clerk_secret_key` を使用 |
| 10 | `saas_identifier: "BlogAI"` ハードコード | `backend/app/domains/blog/endpoints.py:507` | env var化 |

### 10.3 LOW 優先度

| # | 問題 | ファイル | 修正内容 |
|---|------|---------|---------|
| 11 | `USE_PROXY` 2回定義 | `frontend/src/app/(admin)/admin/users/page.tsx` | モジュールレベル定数に統一 |
| 12 | docker-compose の `--reload` 未設定 | `docker-compose.yml` | backend の CMD に `--reload` 追加 |
| 13 | `stripe-cli` が存在しない `.env.local` を参照 | `docker-compose.yml` | ドキュメント or ファイル作成 |

---

## 付録: 情報ソース

### Vercel
- [Vercel CLI Overview](https://vercel.com/docs/cli)
- [Vercel Environments](https://vercel.com/docs/deployments/environments)
- [Set Up a Staging Environment](https://vercel.com/kb/guide/set-up-a-staging-environment-on-vercel)
- [GitHub Actions with Vercel](https://vercel.com/kb/guide/how-can-i-use-github-actions-with-vercel)

### Google Cloud
- [gcloud run deploy](https://cloud.google.com/sdk/gcloud/reference/run/deploy)
- [Cloud Run Secrets](https://docs.google.com/run/docs/configuring/services/secrets)
- [Workload Identity Federation](https://cloud.google.com/blog/products/identity-security/enabling-keyless-authentication-from-github-actions)
- [Rollbacks and Traffic Migration](https://cloud.google.com/run/docs/rollouts-rollbacks-traffic-migration)
- [Cloud Run IAM (X-Serverless-Authorization)](https://cloud.google.com/blog/products/serverless/cloud-run-supports-new-authorization-mechanisms)

### Supabase
- [Managing Environments](https://supabase.com/docs/guides/deployment/managing-environments)
- [Database Migrations](https://supabase.com/docs/guides/deployment/database-migrations)
- [Branching](https://supabase.com/docs/guides/deployment/branching)
- [Pricing](https://supabase.com/pricing)

### Clerk
- [Managing Environments](https://clerk.com/docs/guides/development/managing-environments)
- [Set Up Staging](https://clerk.com/docs/deployments/set-up-staging)
- [Deploying to Vercel](https://clerk.com/docs/guides/development/deployment/vercel)

### Stripe
- [Sandboxes](https://docs.stripe.com/sandboxes)
- [Test Clocks](https://docs.stripe.com/billing/testing/test-clocks)
- [Webhooks](https://docs.stripe.com/webhooks)
- [Go-Live Checklist](https://docs.stripe.com/get-started/checklist/go-live)

### GitHub Actions
- [Deployment Environments](https://docs.github.com/en/actions/concepts/workflows-and-actions/deployment-environments)
- [Secrets](https://docs.github.com/en/actions/concepts/security/secrets)
- [google-github-actions/auth (WIF)](https://github.com/google-github-actions/auth)
- [google-github-actions/deploy-cloudrun](https://github.com/google-github-actions/deploy-cloudrun)
- [supabase/setup-cli](https://github.com/supabase/setup-cli)
