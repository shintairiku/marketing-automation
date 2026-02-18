# デプロイメントガイド

## 概要

2環境構成 (Development + Production) で運用する。

```
feature branch → PR → develop → PR → main
                  ↓                    ↓
            Dev環境に自動デプロイ   Prod環境に自動デプロイ
```

| レイヤー | Development | Production |
|---------|------------|------------|
| Git ブランチ | `develop` | `main` |
| Backend | Cloud Run `marketing-automation-dev` | Cloud Run `marketing-automation-prod` |
| Frontend | Vercel Preview (自動) | Vercel Production (自動) |
| Database | Supabase dev プロジェクト | Supabase prod プロジェクト |
| Auth | Clerk Development インスタンス | Clerk Production インスタンス |
| Payment | Stripe Test Mode | Stripe Live Mode |
| Storage | GCS `*-images-dev` バケット | GCS `*-images-prod` バケット |

---

## 1. 初期セットアップ

### 1.1 Git ブランチ

```bash
# main ブランチを作成 (master から)
git branch -m master main
git push -u origin main

# develop ブランチを作成
git checkout -b develop
git push -u origin develop

# GitHub の Default Branch を main に変更
# GitHub > Settings > General > Default Branch > main
```

### 1.2 Supabase (2プロジェクト)

1. [Supabase Dashboard](https://supabase.com/dashboard) で2つのプロジェクトを作成:
   - `marketing-automation-dev`
   - `marketing-automation-prod`

2. 各プロジェクトの Settings > API から取得:
   - `SUPABASE_URL`
   - `SUPABASE_ANON_KEY`
   - `SUPABASE_SERVICE_ROLE_KEY`

3. マイグレーション適用:
```bash
# Dev
npx supabase link --project-ref <dev-ref>
npx supabase db push

# Prod
npx supabase link --project-ref <prod-ref>
npx supabase db push
```

### 1.3 Clerk (2インスタンス)

Clerk は Dashboard で Development / Production インスタンスが自動分離される。

1. [Clerk Dashboard](https://dashboard.clerk.com/) でアプリケーション作成
2. Development Instance のキーを dev 環境変数に設定
3. Production Instance のキーを prod 環境変数に設定

| キー | Dev (テスト) | Prod (本番) |
|------|-------------|-------------|
| `CLERK_PUBLISHABLE_KEY` | `pk_test_xxx` | `pk_live_xxx` |
| `CLERK_SECRET_KEY` | `sk_test_xxx` | `sk_live_xxx` |

### 1.4 Stripe (Test / Live Mode)

1. [Stripe Dashboard](https://dashboard.stripe.com/) で Test Mode と Live Mode を切り替え
2. それぞれのモードで Price を作成 (基本プラン + アドオン)
3. Webhook エンドポイントを登録:
   - Dev: `https://dev.yourapp.com/api/webhooks` (Stripe Test Mode)
   - Prod: `https://app.yourapp.com/api/webhooks` (Stripe Live Mode)

| キー | Dev (Test Mode) | Prod (Live Mode) |
|------|----------------|------------------|
| `STRIPE_PUBLISHABLE_KEY` | `pk_test_xxx` | `pk_live_xxx` |
| `STRIPE_SECRET_KEY` | `sk_test_xxx` | `sk_live_xxx` |
| `STRIPE_WEBHOOK_SECRET` | `whsec_xxx` | `whsec_xxx` |
| `STRIPE_PRICE_ID` | `price_test_xxx` | `price_live_xxx` |
| `STRIPE_PRICE_ADDON_ARTICLES` | `price_test_xxx` | `price_live_xxx` |

### 1.5 Google Cloud Platform

```bash
# Artifact Registry リポジトリ作成 (Docker イメージ保存先)
gcloud artifacts repositories create marketing-automation \
  --repository-format=docker \
  --location=asia-northeast1 \
  --description="Marketing Automation Docker images"

# Cloud Run サービス作成 (dev)
gcloud run deploy marketing-automation-dev \
  --image=asia-northeast1-docker.pkg.dev/<PROJECT_ID>/marketing-automation/backend:latest \
  --region=asia-northeast1 \
  --platform=managed \
  --allow-unauthenticated  # dev は認証なしでもOK

# Cloud Run サービス作成 (prod)
gcloud run deploy marketing-automation-prod \
  --image=asia-northeast1-docker.pkg.dev/<PROJECT_ID>/marketing-automation/backend:latest \
  --region=asia-northeast1 \
  --platform=managed \
  --no-allow-unauthenticated  # prod は IAM 認証必須

# GCS バケット作成
gsutil mb -l asia-northeast1 gs://marketing-automation-images-dev
gsutil mb -l asia-northeast1 gs://marketing-automation-images-prod
```

#### Cloud Run 環境変数の設定

Cloud Run の環境変数は GCP Console または gcloud で設定する。
**シークレット (APIキー等) は GCP Secret Manager を使用する。**

```bash
# Secret Manager にシークレットを登録
echo -n "sk-proj-xxx" | gcloud secrets create openai-api-key --data-file=-
echo -n "sk_live_xxx" | gcloud secrets create clerk-secret-key-prod --data-file=-
# ... 他のシークレットも同様

# Cloud Run にシークレットをマウント
gcloud run services update marketing-automation-prod \
  --region=asia-northeast1 \
  --set-secrets=OPENAI_API_KEY=openai-api-key:latest,CLERK_SECRET_KEY=clerk-secret-key-prod:latest \
  --set-env-vars=ENVIRONMENT=production,ALLOWED_ORIGINS=https://app.yourdomain.com
```

### 1.6 Vercel

1. [Vercel Dashboard](https://vercel.com/) でプロジェクトをインポート
2. Git Integration で GitHub リポジトリを接続
3. Root Directory を `frontend` に設定
4. Framework Preset: Next.js
5. Build Command: `bun run build`
6. Install Command: `bun install`

#### Vercel 環境変数設定

Vercel Dashboard > Settings > Environment Variables で、環境ごとに変数を設定:

| Scope | 対象 |
|-------|------|
| Production | `main` ブランチのデプロイ |
| Preview | `develop` ブランチ + PR のデプロイ |
| Development | `vercel dev` コマンド |

**Production のみ**:
- `CLOUD_RUN_AUDIENCE_URL` = `https://marketing-automation-prod-xxx.run.app`
- `GOOGLE_SA_KEY_BASE64` = (Base64エンコードされたSAキーJSON)

**Preview のみ**:
- `NEXT_PUBLIC_API_BASE_URL` = dev Cloud Run の URL
- `CLOUD_RUN_AUDIENCE_URL` = dev Cloud Run の URL (IAM有効にした場合)

---

## 2. GitHub 設定

### 2.1 Environments

GitHub > Settings > Environments で2つの Environment を作成:

#### `development` Environment
- Protection rules: なし (develop ブランチへの push で即デプロイ)
- Secrets:
  - `WIF_PROVIDER`: Workload Identity Federation プロバイダー
  - `WIF_SERVICE_ACCOUNT`: GCP サービスアカウント
  - `SUPABASE_ACCESS_TOKEN`: Supabase CLI アクセストークン
  - `SUPABASE_PROJECT_REF`: dev プロジェクトの ref
- Variables:
  - `GCP_PROJECT_ID`: GCP プロジェクト ID
  - `CLOUD_RUN_SERVICE_DEV`: `marketing-automation-dev`

#### `production` Environment
- Protection rules: **Required reviewers** を設定 (本番デプロイ前に承認必須)
- Secrets: (同上、prod 用の値)
- Variables:
  - `GCP_PROJECT_ID`: GCP プロジェクト ID
  - `CLOUD_RUN_SERVICE_PROD`: `marketing-automation-prod`

### 2.2 Workload Identity Federation (WIF) セットアップ

GitHub Actions から GCP にサービスアカウントキーなしで認証する方法。

```bash
# 1. サービスアカウント作成
gcloud iam service-accounts create github-actions \
  --display-name="GitHub Actions CI/CD"

# 2. 必要なロールを付与
SA_EMAIL="github-actions@<PROJECT_ID>.iam.gserviceaccount.com"

gcloud projects add-iam-policy-binding <PROJECT_ID> \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/run.developer"

gcloud projects add-iam-policy-binding <PROJECT_ID> \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/artifactregistry.writer"

gcloud projects add-iam-policy-binding <PROJECT_ID> \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/iam.serviceAccountUser"

# 3. Workload Identity Pool 作成
gcloud iam workload-identity-pools create "github-pool" \
  --location="global" \
  --display-name="GitHub Actions Pool"

# 4. OIDC プロバイダー作成
gcloud iam workload-identity-pools providers create-oidc "github-provider" \
  --location="global" \
  --workload-identity-pool="github-pool" \
  --display-name="GitHub Provider" \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository" \
  --issuer-uri="https://token.actions.githubusercontent.com"

# 5. サービスアカウントへのバインディング
REPO="your-org/marketing-automation"  # GitHubリポジトリ

gcloud iam service-accounts add-iam-policy-binding $SA_EMAIL \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/<PROJECT_NUMBER>/locations/global/workloadIdentityPools/github-pool/attribute.repository/$REPO"

# 6. GitHub Secrets に設定する値
echo "WIF_PROVIDER: projects/<PROJECT_NUMBER>/locations/global/workloadIdentityPools/github-pool/providers/github-provider"
echo "WIF_SERVICE_ACCOUNT: $SA_EMAIL"
```

### 2.3 Branch Protection Rules

GitHub > Settings > Branches で以下を設定:

#### `main` ブランチ
- Require a pull request before merging
- Require approvals: 1
- Require status checks to pass: `ci` (backend-lint, backend-build, frontend-lint-build)
- Restrict pushes (direct push 禁止)

#### `develop` ブランチ
- Require status checks to pass: `ci`

---

## 3. デプロイフロー

### 日常の開発

```bash
# 1. feature ブランチを作成
git checkout develop
git pull origin develop
git checkout -b feature/my-feature

# 2. 開発 & コミット
# ...

# 3. develop に PR を作成
git push -u origin feature/my-feature
# GitHub で develop 宛の PR を作成

# 4. CI が通ったらマージ → dev 環境に自動デプロイ

# 5. dev 環境で動作確認

# 6. develop → main に PR を作成 → レビュー → マージ → 本番デプロイ
```

### データベースマイグレーション

```bash
# 1. マイグレーションファイル作成
cd frontend
bun run migration:new my_migration_name

# 2. SQL を編集
# shared/supabase/migrations/xxxx_my_migration_name.sql

# 3. develop にマージ → dev Supabase に自動適用
# 4. main にマージ → prod Supabase に自動適用
```

### 手動デプロイ (緊急時)

GitHub Actions の workflow_dispatch で手動実行可能:
- Actions > Deploy Backend > Run workflow > environment 選択

### ロールバック

```bash
# Cloud Run は自動でリビジョン管理されている
# 前のリビジョンにトラフィックを戻す
gcloud run services update-traffic marketing-automation-prod \
  --region=asia-northeast1 \
  --to-revisions=<previous-revision>=100
```

---

## 4. 環境変数の管理場所まとめ

| 場所 | 用途 |
|------|------|
| `backend/.env` | ローカル開発 (gitignore済み) |
| `frontend/.env.local` | ローカル開発 (gitignore済み) |
| GCP Secret Manager | Cloud Run (dev/prod) のシークレット |
| Cloud Run 環境変数 | Cloud Run の非シークレット設定 |
| Vercel Environment Variables | Vercel (Production/Preview/Development) |
| GitHub Environments Secrets | CI/CD ワークフロー |
| GitHub Environments Variables | CI/CD ワークフロー (非シークレット) |

**原則**: シークレットは各サービスの Secret Management に保存。`.env` ファイルにはコミットしない。
