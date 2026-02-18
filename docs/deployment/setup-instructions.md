# 本番環境セットアップ指示書

> **対象**: BlogAI / Marketing Automation Platform
> **作成日**: 2026-02-18
> **前提**: `feat/dev-prod` ブランチの Phase A (コード修正) + Phase C (CI/CD YAML) は完了済み

---

## 完了済み作業（参考）

以下はすべてコードベースで完了しています。再作業は不要です。

| 項目 | 状態 |
|------|------|
| レガシーコード19ファイル削除 | 完了 |
| ベースラインマイグレーション作成 (`supabase/migrations/00000000000000_baseline.sql`) | 完了 |
| 新Production Supabase 作成 + スキーマ適用 + 全データ移行 | 完了 |
| TypeScript型再生成 (`frontend/src/libs/supabase/types.ts`) | 完了 |
| `(supabase as any)` キャスト大部分除去 | 完了 |
| `config.py` ローカル絶対パス削除 | 完了 |
| GCSバケット名を環境変数化 (`next.config.js`) | 完了 |
| `.env.example` 更新 (本番URL削除、プレースホルダー化) | 完了 |
| `Dockerfile` からシークレットARG削除 | 完了 |
| CI/CD ワークフロー5ファイル作成 | 完了 |

---

## これからやること: 全体の流れ

```
Step 1: GCP セットアップ (Artifact Registry, WIF, Cloud Run, Secret Manager)
   ↓
Step 2: Clerk Production インスタンス作成 + カスタムドメイン
   ↓
Step 3: Supabase-Clerk 連携 (prod + dev)
   ↓
Step 4: Stripe ライブモード設定
   ↓
Step 5: Vercel 環境変数設定
   ↓
Step 6: GitHub Environments + ブランチ保護
   ↓
Step 7: feat/dev-prod → develop へマージ
   ↓
Step 8: develop → main へPR作成 (本番初回デプロイ)
   ↓
Step 9: 本番切替 (Supabase切替 + 検証)
   ↓
Step 10: Dev Supabase リセット
```

---

## Step 1: GCP セットアップ

### 1-1. Artifact Registry 作成

Cloud Run にデプロイする Docker イメージの保管先を作成します。

**場所**: ターミナル (gcloud CLI)

```bash
gcloud artifacts repositories create marketing-automation \
  --repository-format=docker \
  --location=asia-northeast1 \
  --project=marketing-automation-461305 \
  --description="BlogAI backend Docker images"
```

確認:
```bash
gcloud artifacts repositories list --location=asia-northeast1
```

### 1-2. Workload Identity Federation (WIF)

GitHub Actions から GCP に**キーレス認証**するための仕組みです。SA の JSON キーファイルが不要になります。

**場所**: ターミナル (gcloud CLI)

```bash
# === 変数設定 ===
export PROJECT_ID="marketing-automation-461305"
export GITHUB_REPO="YOUR_GITHUB_ORG/marketing-automation"  # ← あなたのGitHub org/repo に変更

# === 1. Workload Identity Pool 作成 ===
gcloud iam workload-identity-pools create "github-actions" \
  --project="${PROJECT_ID}" \
  --location="global" \
  --display-name="GitHub Actions Pool"

# === 2. OIDC Provider 作成 ===
gcloud iam workload-identity-pools providers create-oidc "github-provider" \
  --project="${PROJECT_ID}" \
  --location="global" \
  --workload-identity-pool="github-actions" \
  --display-name="GitHub Actions Provider" \
  --issuer-uri="https://token.actions.githubusercontent.com" \
  --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository,attribute.repository_owner=assertion.repository_owner" \
  --attribute-condition="assertion.repository == '${GITHUB_REPO}'"

# === 3. Service Account 作成 ===
gcloud iam service-accounts create "github-actions-deploy" \
  --project="${PROJECT_ID}" \
  --display-name="GitHub Actions Deploy"

# === 4. SA に必要なロールを付与 ===
SA_EMAIL="github-actions-deploy@${PROJECT_ID}.iam.gserviceaccount.com"

# Cloud Run デプロイ
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${SA_EMAIL}" --role="roles/run.admin"
# SA として実行するために必要
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${SA_EMAIL}" --role="roles/iam.serviceAccountUser"
# Artifact Registry への push
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${SA_EMAIL}" --role="roles/artifactregistry.writer"

# === 5. WIF Pool と SA をバインド ===
POOL_NAME=$(gcloud iam workload-identity-pools describe "github-actions" \
  --project="${PROJECT_ID}" --location="global" --format="value(name)")

gcloud iam service-accounts add-iam-policy-binding "${SA_EMAIL}" \
  --project="${PROJECT_ID}" \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/${POOL_NAME}/attribute.repository/${GITHUB_REPO}"

# === 6. Provider のフルパスを取得 (GitHub Secrets に登録する) ===
gcloud iam workload-identity-pools providers describe "github-provider" \
  --project="${PROJECT_ID}" \
  --location="global" \
  --workload-identity-pool="github-actions" \
  --format="value(name)"
```

**出力をメモ**:
- `GCP_WORKLOAD_IDENTITY_PROVIDER` = Step 6 の出力 (`projects/数字/locations/global/workloadIdentityPools/github-actions/providers/github-provider`)
- `GCP_SERVICE_ACCOUNT` = `github-actions-deploy@marketing-automation-461305.iam.gserviceaccount.com`

### 1-3. Cloud Run サービス作成

**場所**: ターミナル (gcloud CLI)

まずは空のサービスを作成します（CI/CDが初回デプロイで上書きします）。

```bash
# 最小限のイメージでサービスだけ作る (初回デプロイ時にCI/CDが上書き)
# Production
gcloud run deploy marketing-automation-backend \
  --image=gcr.io/cloudrun/hello \
  --region=asia-northeast1 \
  --project=marketing-automation-461305 \
  --no-allow-unauthenticated \
  --min-instances=1 --max-instances=10 \
  --cpu=1 --memory=512Mi --timeout=300

# Development
gcloud run deploy marketing-automation-backend-dev \
  --image=gcr.io/cloudrun/hello \
  --region=asia-northeast1 \
  --project=marketing-automation-461305 \
  --no-allow-unauthenticated \
  --min-instances=0 --max-instances=3 \
  --cpu=1 --memory=512Mi --timeout=300
```

Cloud Run URL をメモ（後で Vercel に設定）:
```bash
gcloud run services describe marketing-automation-backend \
  --region=asia-northeast1 --format="value(status.url)"
gcloud run services describe marketing-automation-backend-dev \
  --region=asia-northeast1 --format="value(status.url)"
```

### 1-4. Vercel → Cloud Run の IAM認証用 Service Account

Vercel から Cloud Run を呼ぶための SA です（既に `frontend/src/lib/google-auth.ts` で実装済み）。

```bash
# Vercel Invoker SA (既に存在する場合はスキップ)
gcloud iam service-accounts create vercel-invoker \
  --project=marketing-automation-461305 \
  --display-name="Vercel Cloud Run Invoker"

INVOKER_EMAIL="vercel-invoker@marketing-automation-461305.iam.gserviceaccount.com"

# Production Cloud Run への呼び出し権限
gcloud run services add-iam-policy-binding marketing-automation-backend \
  --region=asia-northeast1 \
  --member="serviceAccount:${INVOKER_EMAIL}" \
  --role="roles/run.invoker"

# Development Cloud Run への呼び出し権限
gcloud run services add-iam-policy-binding marketing-automation-backend-dev \
  --region=asia-northeast1 \
  --member="serviceAccount:${INVOKER_EMAIL}" \
  --role="roles/run.invoker"

# JSON キー生成 (Vercel 環境変数に Base64 で設定する)
gcloud iam service-accounts keys create vercel-sa-key.json \
  --iam-account="${INVOKER_EMAIL}"

# Base64 エンコード
cat vercel-sa-key.json | base64 -w 0
# ↑ この出力が GOOGLE_SA_KEY_BASE64 の値
```

**出力をメモ**:
- `GOOGLE_SA_KEY_BASE64` = 上記 Base64 文字列
- `CLOUD_RUN_AUDIENCE_URL` (prod) = Step 1-3 でメモした Production の `*.run.app` URL
- `CLOUD_RUN_AUDIENCE_URL` (dev) = Step 1-3 でメモした Development の `*.run.app` URL

### 1-5. Cloud Run 環境変数 / Secret Manager

Cloud Run のバックエンドに環境変数を設定します。

```bash
# Secret Manager にシークレットを登録
# (値は各サービスのダッシュボードからコピー)
gcloud secrets create openai-api-key --data-file=- <<< "YOUR_OPENAI_API_KEY"
gcloud secrets create gemini-api-key --data-file=- <<< "YOUR_GEMINI_API_KEY"
gcloud secrets create serpapi-api-key --data-file=- <<< "YOUR_SERPAPI_API_KEY"
gcloud secrets create supabase-service-role-key-prod --data-file=- <<< "PROD_KEY"
gcloud secrets create supabase-service-role-key-dev --data-file=- <<< "DEV_KEY"
gcloud secrets create clerk-secret-key-prod --data-file=- <<< "sk_live_..."
gcloud secrets create clerk-secret-key-dev --data-file=- <<< "sk_test_..."
gcloud secrets create stripe-secret-key-prod --data-file=- <<< "sk_live_..."
gcloud secrets create stripe-secret-key-dev --data-file=- <<< "sk_test_..."
gcloud secrets create stripe-webhook-secret-prod --data-file=- <<< "whsec_..."
gcloud secrets create stripe-webhook-secret-dev --data-file=- <<< "whsec_..."
gcloud secrets create credential-encryption-key --data-file=- <<< "YOUR_KEY"
gcloud secrets create google-service-account-json --data-file=path/to/sa.json

# Cloud Run SA にシークレットアクセス権限
CLOUD_RUN_SA_EMAIL="$(gcloud run services describe marketing-automation-backend \
  --region=asia-northeast1 --format='value(spec.template.spec.serviceAccountName)')"
# デフォルト SA なら: PROJECT_NUMBER-compute@developer.gserviceaccount.com

# 全シークレットへのアクセス付与 (簡易版)
gcloud projects add-iam-policy-binding marketing-automation-461305 \
  --member="serviceAccount:${CLOUD_RUN_SA_EMAIL}" \
  --role="roles/secretmanager.secretAccessor"
```

Cloud Run に環境変数をセット:
```bash
# === Production ===
gcloud run services update marketing-automation-backend \
  --region=asia-northeast1 \
  --update-env-vars="SUPABASE_URL=https://tkkbhglcudsxcwxdyplp.supabase.co,\
SUPABASE_ANON_KEY=PROD_ANON_KEY,\
CLERK_PUBLISHABLE_KEY=pk_live_...,\
ALLOWED_ORIGINS=https://app.blogai.jp,\
FRONTEND_URL=https://app.blogai.jp,\
GCS_BUCKET_NAME=YOUR_PROD_BUCKET,\
IMAGEN_MODEL_NAME=imagen-4.0-generate-preview-06-06,\
GOOGLE_CLOUD_PROJECT=marketing-automation-461305,\
GOOGLE_CLOUD_LOCATION=us-central1,\
ENVIRONMENT=production" \
  --update-secrets="\
OPENAI_API_KEY=openai-api-key:latest,\
GEMINI_API_KEY=gemini-api-key:latest,\
SERPAPI_API_KEY=serpapi-api-key:latest,\
SUPABASE_SERVICE_ROLE_KEY=supabase-service-role-key-prod:latest,\
CLERK_SECRET_KEY=clerk-secret-key-prod:latest,\
STRIPE_SECRET_KEY=stripe-secret-key-prod:latest,\
STRIPE_WEBHOOK_SECRET=stripe-webhook-secret-prod:latest,\
CREDENTIAL_ENCRYPTION_KEY=credential-encryption-key:latest,\
GOOGLE_SERVICE_ACCOUNT_JSON=google-service-account-json:latest"

# === Development ===
gcloud run services update marketing-automation-backend-dev \
  --region=asia-northeast1 \
  --update-env-vars="SUPABASE_URL=https://pytxohnkkyshobprrjqh.supabase.co,\
SUPABASE_ANON_KEY=DEV_ANON_KEY,\
CLERK_PUBLISHABLE_KEY=pk_test_...,\
ALLOWED_ORIGINS=https://dev.blogai.jp,\
FRONTEND_URL=https://dev.blogai.jp,\
GCS_BUCKET_NAME=YOUR_DEV_BUCKET,\
IMAGEN_MODEL_NAME=imagen-4.0-generate-preview-06-06,\
GOOGLE_CLOUD_PROJECT=marketing-automation-461305,\
GOOGLE_CLOUD_LOCATION=us-central1,\
ENVIRONMENT=development,\
DEBUG=true" \
  --update-secrets="\
OPENAI_API_KEY=openai-api-key:latest,\
GEMINI_API_KEY=gemini-api-key:latest,\
SERPAPI_API_KEY=serpapi-api-key:latest,\
SUPABASE_SERVICE_ROLE_KEY=supabase-service-role-key-dev:latest,\
CLERK_SECRET_KEY=clerk-secret-key-dev:latest,\
STRIPE_SECRET_KEY=stripe-secret-key-dev:latest,\
STRIPE_WEBHOOK_SECRET=stripe-webhook-secret-dev:latest,\
CREDENTIAL_ENCRYPTION_KEY=credential-encryption-key:latest,\
GOOGLE_SERVICE_ACCOUNT_JSON=google-service-account-json:latest"
```

---

## Step 2: Clerk Production インスタンス作成

### 2-1. Production インスタンスへの切替

**場所**: https://dashboard.clerk.com

1. 画面上部の **Development** ドロップダウンをクリック
2. **「Create production instance」** を選択
3. Development の設定がクローンされる（ただし SSO, Integrations, Paths は再設定が必要）

### 2-2. カスタムドメイン設定

**場所**: https://dashboard.clerk.com → **Domains** ページ（左サイドバー）

1. Production ドメインを入力（例: `blogai.jp`）
2. 表示される **5つの DNS レコード** (CNAME) をあなたの DNS プロバイダーに追加
3. DNS 追加後、Clerk ダッシュボードに戻って **「Validate configuration」** をクリック
4. 検証完了後、**「Deploy certificates」** をクリック

**注意**:
- DNS 反映に最大48時間かかる場合がある
- Cloudflare の場合、Clerk 関連のサブドメインは **「DNS only」モード**（グレーの雲）にする（プロキシNG）
- CAA レコードがある場合、Let's Encrypt または Google Trust Services を許可する

### 2-3. Google OAuth 設定

**Clerk 側**: https://dashboard.clerk.com → **User Authentication** → **SSO Connections**

1. **「Add connection」** → **「For all users」**
2. プロバイダー: **Google** を選択
3. **「Enable for sign-up and sign-in」** と **「Use custom credentials」** をON
4. 表示される **Authorized Redirect URI** をコピー

**Google Cloud Console 側**: https://console.cloud.google.com → **APIs & Services** → **Credentials**

1. **「Create Credentials」** → **「OAuth client ID」**
2. Application type: **Web application**
3. **Authorized JavaScript origins**: `https://blogai.jp` を追加
4. **Authorized Redirect URIs**: Clerk からコピーした URI を貼り付け
5. **Create** → **Client ID** と **Client Secret** をコピー

**Google Cloud Console**: **APIs & Services** → **OAuth consent screen**

6. Publishing status を **「Testing」→「In production」** に変更
   - Testing のままだと100ユーザーまでしか使えない
   - Google の審査プロセスが始まる

**Clerk に戻って**:

7. Client ID と Client Secret を貼り付けて **Save**

### 2-4. Webhook エンドポイント登録

**場所**: https://dashboard.clerk.com → **Webhooks**

1. **「Add Endpoint」** をクリック
2. **Endpoint URL**: `https://app.blogai.jp/api/webhooks/clerk`
3. **Events** (最低限):
   - `user.created`
   - `user.updated`
   - `user.deleted`
4. **Create** → Signing Secret (目のアイコンで表示) をメモ → `CLERK_WEBHOOK_SECRET`

### 2-5. API キーの確認

**場所**: https://dashboard.clerk.com → **API Keys**

メモするもの:
- `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` = `pk_live_...`
- `CLERK_SECRET_KEY` = `sk_live_...`

---

## Step 3: Supabase-Clerk 連携

Production と Development の両方で同じ手順を実施します。

### 3-1. Clerk 側で Supabase 統合を有効化

**場所**: https://dashboard.clerk.com → 左サイドバー **Integrations** （または直接 `dashboard.clerk.com/setup/supabase`）

1. **「Activate Supabase integration」** をクリック
2. 表示される **Clerk domain** をコピー
   - Production: カスタムドメイン（例: `clerk.blogai.jp`）
   - Development: `xxx.clerk.accounts.dev`

### 3-2. Supabase 側で Clerk をプロバイダーに追加

**場所 (Production)**: https://supabase.com/dashboard/project/tkkbhglcudsxcwxdyplp/auth/providers

**場所 (Development)**: https://supabase.com/dashboard/project/pytxohnkkyshobprrjqh/auth/providers

1. 左サイドバー **Authentication** → **Sign In / Up** (または **Providers**)
2. **Third Party Auth** セクションで **「Add provider」**
3. **Clerk** を選択
4. Step 3-1 でコピーした **Clerk domain** を貼り付け
5. **Save**

### やること一覧

| 組み合わせ | Clerk インスタンス | Supabase プロジェクト |
|-----------|------------------|---------------------|
| Production | Production (`pk_live_*`) | `tkkbhglcudsxcwxdyplp` |
| Development | Development (`pk_test_*`) | `pytxohnkkyshobprrjqh` |

---

## Step 4: Stripe ライブモード設定

### 4-1. ライブモードに切替

**場所**: https://dashboard.stripe.com

1. 右上のトグルで **「テストモード」→「ライブモード」** に切替
   - 初回は本人確認・事業情報の入力が必要
   - 審査に数日かかる場合がある

### 4-2. Products / Prices 作成

**場所**: https://dashboard.stripe.com/products → **「+ Add product」**

| Product | Price | メモ先の環境変数 |
|---------|-------|-----------------|
| BlogAI 個人プラン | ¥29,800/月 (recurring, monthly) | `STRIPE_PRICE_ID` |
| BlogAI アドオン記事パック | ¥任意/月 (recurring, monthly) | `STRIPE_PRICE_ADDON_ARTICLES` |

各 Price を作成後、Price ID (`price_live_...`) をメモ。

**注意**: チームプランは個人プランと同じ Price ID を使い、quantity で管理する設計です。チーム用に別 Product を作る必要はありません。

### 4-3. Webhook エンドポイント登録

**場所**: https://dashboard.stripe.com/webhooks → **「+ Add endpoint」**（ライブモードであることを確認）

1. **Endpoint URL**: `https://app.blogai.jp/api/subscription/webhook`
2. **Events**:
   - `checkout.session.completed`
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.payment_succeeded`
3. **Add endpoint** → **Signing secret** をメモ → `STRIPE_WEBHOOK_SECRET`

### 4-4. Customer Portal 設定

**場所**: https://dashboard.stripe.com/settings/billing/portal （ライブモードで）

1. Customer Portal を有効化
2. 許可する操作を設定（プラン変更、キャンセル等）

### 4-5. 旧 Webhook の削除

**場所**: https://dashboard.stripe.com/webhooks （テストモードも確認）

- `/api/webhooks` に向いている古いエンドポイントがあれば削除
- `/api/subscription/webhook` のみが存在する状態にする

### メモする値一覧

| 値 | 環境変数名 |
|----|-----------|
| `pk_live_...` | `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY` |
| `sk_live_...` | `STRIPE_SECRET_KEY` |
| `whsec_...` (Webhook signing secret) | `STRIPE_WEBHOOK_SECRET` |
| `price_live_...` (個人プラン) | `STRIPE_PRICE_ID` |
| `price_live_...` (アドオン) | `STRIPE_PRICE_ADDON_ARTICLES` |

---

## Step 5: Vercel 環境変数設定

**場所**: https://vercel.com → あなたのプロジェクト → **Settings** → **Environment Variables**

以下の変数を、スコープ別に設定してください。

### Production スコープ（`main` ブランチ → 本番）

| 変数名 | 値 |
|--------|-----|
| `NEXT_PUBLIC_SUPABASE_URL` | `https://tkkbhglcudsxcwxdyplp.supabase.co` |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | (prod anon key) |
| `SUPABASE_SERVICE_ROLE_KEY` | (prod service role key) |
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | `pk_live_...` |
| `CLERK_SECRET_KEY` | `sk_live_...` |
| `CLERK_WEBHOOK_SECRET` | (prod signing secret) |
| `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY` | `pk_live_...` |
| `STRIPE_SECRET_KEY` | `sk_live_...` |
| `STRIPE_WEBHOOK_SECRET` | (prod signing secret) |
| `STRIPE_PRICE_ID` | `price_live_...` |
| `STRIPE_PRICE_ADDON_ARTICLES` | `price_live_...` |
| `NEXT_PUBLIC_API_BASE_URL` | (prod Cloud Run URL: `https://marketing-automation-backend-xxxx.a.run.app`) |
| `NEXT_PUBLIC_APP_URL` | `https://app.blogai.jp` |
| `NEXT_PUBLIC_SITE_URL` | `https://app.blogai.jp` |
| `NEXT_PUBLIC_GCS_BUCKET_NAME` | (prod bucket name) |
| `CLOUD_RUN_AUDIENCE_URL` | (prod `*.run.app` URL — **カスタムドメインは不可**) |
| `GOOGLE_SA_KEY_BASE64` | (Step 1-4 の Base64 文字列) |

### Preview スコープ（`develop` ブランチ → 開発環境）

**設定方法**: 変数追加時に **Preview** を選択 → **「Select specific branches」** → `develop` と入力

| 変数名 | 値 |
|--------|-----|
| `NEXT_PUBLIC_SUPABASE_URL` | `https://pytxohnkkyshobprrjqh.supabase.co` |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | (dev anon key) |
| `SUPABASE_SERVICE_ROLE_KEY` | (dev service role key) |
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | `pk_test_...` |
| `CLERK_SECRET_KEY` | `sk_test_...` |
| `CLERK_WEBHOOK_SECRET` | (dev signing secret) |
| `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY` | `pk_test_...` |
| `STRIPE_SECRET_KEY` | `sk_test_...` |
| `STRIPE_WEBHOOK_SECRET` | (dev signing secret) |
| `STRIPE_PRICE_ID` | `price_test_...` |
| `STRIPE_PRICE_ADDON_ARTICLES` | `price_test_...` |
| `NEXT_PUBLIC_API_BASE_URL` | (dev Cloud Run URL: `https://marketing-automation-backend-dev-xxxx.a.run.app`) |
| `NEXT_PUBLIC_APP_URL` | `https://dev.blogai.jp` |
| `NEXT_PUBLIC_SITE_URL` | `https://dev.blogai.jp` |
| `NEXT_PUBLIC_GCS_BUCKET_NAME` | (dev bucket name) |
| `CLOUD_RUN_AUDIENCE_URL` | (dev `*.run.app` URL) |
| `GOOGLE_SA_KEY_BASE64` | (同じ SA キーでOK) |

### Vercel ドメイン設定

**場所**: https://vercel.com → プロジェクト → **Settings** → **Domains**

| ドメイン | ブランチ | 用途 |
|---------|---------|------|
| `app.blogai.jp` | `main` (Production) | 本番 |
| `dev.blogai.jp` | `develop` (Preview) | 開発 |

---

## Step 6: GitHub Environments + ブランチ保護

### 6-1. Environments 作成

**場所**: https://github.com/YOUR_ORG/marketing-automation/settings/environments

#### `development` 環境

1. **「New environment」** → 名前: `development` → **「Configure environment」**
2. **Deployment branches**: 「Selected branches and tags」→ ルール追加 → `develop`
3. **Required reviewers**: なし（developは自由にデプロイ）
4. **Environment secrets** を追加:

| Secret 名 | 値 |
|-----------|-----|
| `SUPABASE_PROJECT_ID` | `pytxohnkkyshobprrjqh` |
| `SUPABASE_ACCESS_TOKEN` | (Supabase CLI アクセストークン) |
| `SUPABASE_DB_PASSWORD` | (dev DB パスワード) |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | (Step 1-2 の出力) |
| `GCP_SERVICE_ACCOUNT` | `github-actions-deploy@marketing-automation-461305.iam.gserviceaccount.com` |
| `VERCEL_TOKEN` | (Vercel アクセストークン) |
| `VERCEL_ORG_ID` | (Vercel org ID) |
| `VERCEL_PROJECT_ID` | (Vercel project ID) |

5. **Environment variables** を追加:

| Variable 名 | 値 |
|-------------|-----|
| `GCP_PROJECT_ID` | `marketing-automation-461305` |

#### `production` 環境

1. **「New environment」** → 名前: `production` → **「Configure environment」**
2. **Deployment branches**: 「Selected branches and tags」→ ルール追加 → `main`
3. **Required reviewers**: **ON** → あなた自身を追加（本番デプロイ前に承認が必要）
4. **Environment secrets** を追加:

| Secret 名 | 値 |
|-----------|-----|
| `SUPABASE_PROJECT_ID` | `tkkbhglcudsxcwxdyplp` |
| `SUPABASE_ACCESS_TOKEN` | (同じトークンでOK) |
| `SUPABASE_DB_PASSWORD` | (prod DB パスワード) |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | (同上) |
| `GCP_SERVICE_ACCOUNT` | (同上) |
| `VERCEL_TOKEN` | (同上) |
| `VERCEL_ORG_ID` | (同上) |
| `VERCEL_PROJECT_ID` | (同上) |

5. **Environment variables** を追加:

| Variable 名 | 値 |
|-------------|-----|
| `GCP_PROJECT_ID` | `marketing-automation-461305` |

### 6-2. ブランチ保護ルール

**場所**: https://github.com/YOUR_ORG/marketing-automation/settings/branches → **「Add rule」**

#### `main` ブランチ (本番)

| 設定 | 値 |
|------|-----|
| Branch name pattern | `main` |
| Require a pull request before merging | ON |
| Required approvals | 1 |
| Dismiss stale PR approvals | ON |
| Require status checks to pass | ON |
| → 検索して追加 | `lint-and-build` (ci-frontend), `lint` (ci-backend), `docker-build` (ci-backend) |
| Require branches to be up to date | ON |
| Do not allow bypassing the above settings | ON (自分にも適用) |

#### `develop` ブランチ (開発)

| 設定 | 値 |
|------|-----|
| Branch name pattern | `develop` |
| Require a pull request before merging | ON |
| Required approvals | 0 (自分だけなら不要) |
| Require status checks to pass | ON |
| → 検索して追加 | `lint-and-build`, `lint`, `docker-build` |
| Do not allow bypassing the above settings | OFF (自分は直push可能にしてもOK) |

---

## Step 7: feat/dev-prod → develop へマージ

ここからは Git 操作です。

```bash
# feat/dev-prod の最新をプッシュ
git push origin feat/dev-prod

# GitHub で PR 作成: feat/dev-prod → develop
# マージ
```

または:
```bash
git checkout develop
git merge feat/dev-prod
git push origin develop
```

これにより CI/CD が発火し:
- `deploy-frontend.yml` → Vercel Preview デプロイ
- `deploy-backend.yml` → Cloud Run dev デプロイ
- `db-migrations.yml` → Dev Supabase にマイグレーション push

### 確認

- Vercel Preview デプロイが成功するか
- Cloud Run dev デプロイが成功するか
- dev 環境でアプリが動作するか

---

## Step 8: develop → main へ PR（本番初回デプロイ）

```bash
# GitHub で PR 作成: develop → main
# CI チェック通過を確認
# レビュー承認
# マージ
```

これにより:
- `deploy-frontend.yml` → Vercel Production デプロイ（承認必要）
- `deploy-backend.yml` → Cloud Run prod デプロイ（承認必要）
- `db-migrations.yml` → Prod Supabase にマイグレーション push（承認必要）

---

## Step 9: 本番切替 + 検証

### 9-1. データの最終同期

最終データ移行から時間が経っている場合、新たに追加されたデータを同期する必要があります。

```bash
# scripts/migrate-data.py を再実行（既存レコードはスキップ）
python scripts/migrate-data.py
```

### 9-2. クリティカルフロー検証チェックリスト

本番URL (`app.blogai.jp`) にアクセスして以下を確認:

- [ ] `/auth` でサインイン/サインアップが表示される
- [ ] Google ログインが動作する
- [ ] ログイン後 `/blog/new` にリダイレクトされる
- [ ] サブスクリプション状態が正しく表示される（`/settings/billing`）
- [ ] ブログ生成が開始できる（上限表示も確認）
- [ ] WordPress 連携が動作する（`/settings/integrations/wordpress`）
- [ ] 管理者画面が表示される (`/admin` — @shintairiku.jp ユーザー)
- [ ] Stripe Checkout が動作する（テストカード `4242...` は使えない。ライブモード）
- [ ] Supabase Realtime が動作する（ブログ生成の進捗がリアルタイム更新される）

---

## Step 10: Dev Supabase リセット

本番切替が安定したら、旧 Supabase をクリーンなdev環境にリセットします。

```bash
supabase link --project-ref pytxohnkkyshobprrjqh
SUPABASE_DB_PASSWORD=YOUR_DEV_PW supabase db reset
```

これで dev DB にもベースラインマイグレーション + seed データが適用されます。

---

## Git ブランチ戦略 & リリースフロー

### ブランチ構成

```
main (本番)
 ↑ PR (レビュー + CI必須)
develop (開発)
 ↑ PR (CI必須)
feat/xxx, fix/xxx (機能ブランチ)
```

### 日常の開発フロー

```
1. develop から feature ブランチを切る
   git checkout develop
   git checkout -b feat/new-feature

2. 開発・コミット
   git add ... && git commit -m "..."

3. feature → develop へ PR
   gh pr create --base develop --title "..."

4. CI 通過 → マージ
   → 自動で Vercel Preview + Cloud Run dev にデプロイ

5. develop で動作確認OK → develop → main へ PR
   gh pr create --base main --title "Release: ..."

6. レビュー承認 + CI 通過 → マージ
   → 自動で Vercel Production + Cloud Run prod にデプロイ
   → GitHub Environment の Required Reviewers による承認ステップあり
```

### ホットフィックス

本番で緊急バグが見つかった場合:

```
1. main から hotfix ブランチを切る
   git checkout main
   git checkout -b hotfix/critical-bug

2. 修正 → main へ直接 PR
   gh pr create --base main --title "Hotfix: ..."

3. マージ後、main → develop にも反映
   git checkout develop
   git merge main
   git push origin develop
```

### DBマイグレーションの注意

- 新しいマイグレーションファイルは `supabase/migrations/` に追加
- ファイル名: `YYYYMMDDHHMMSS_description.sql`（Supabase CLI の `supabase migration new` で生成）
- `develop` にマージ → dev DB に自動適用
- `main` にマージ → prod DB に自動適用（承認後）
- **破壊的なマイグレーション（テーブル削除、カラム削除等）は本番適用前に必ず dry-run で確認**

### タグ / リリース（オプション）

本番デプロイ時にバージョンタグを打つ場合:

```bash
git tag v1.0.0
git push origin v1.0.0
```

GitHub Releases を使ってリリースノートを管理するのも可。ただし現段階では PR ベースの管理で十分です。

---

## トラブルシューティング

### Cloud Run デプロイが失敗する
- GitHub Environments の secrets が正しいか確認
- WIF の attribute-condition でリポジトリ名が正しいか確認
- `id-token: write` パーミッションが workflow に設定されているか確認

### Vercel デプロイが失敗する
- `VERCEL_TOKEN`, `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID` が正しいか確認
- 環境変数のスコープ (Production / Preview) が正しいか確認

### Supabase マイグレーションが失敗する
- `SUPABASE_ACCESS_TOKEN` が有効か確認（https://supabase.com/dashboard/account/tokens で生成）
- `SUPABASE_DB_PASSWORD` が正しいか確認
- マイグレーションファイルの SQL 構文エラーを確認

### Clerk ログインが動かない
- Clerk Production のカスタムドメイン設定が完了しているか確認
- DNS レコードが正しく伝播しているか確認 (`dig` コマンドで確認)
- `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` が `pk_live_*` になっているか確認

### Stripe Webhook が動かない
- Webhook URL が `/api/subscription/webhook` を指しているか確認
- Signing secret が `STRIPE_WEBHOOK_SECRET` に設定されているか確認
- ライブモードで Webhook を作成しているか確認（テストモードの Webhook は別管理）
