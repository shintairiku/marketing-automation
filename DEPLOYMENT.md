# デプロイ設定ガイド

## 概要

- **フロントエンド**: Vercel (`https://marketing-automation-three.vercel.app`)
- **バックエンド**: Google Cloud Run (`https://marketing-automation-742231208085.asia-northeast1.run.app`)

## 1. バックエンド（Google Cloud Run）の設定

### 環境変数

Cloud Runサービスに以下の環境変数を設定してください：

```bash
# CORS設定（重要）
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:3001,https://marketing-automation-three.vercel.app

# OpenAI API
OPENAI_API_KEY=sk-your-actual-openai-key

# SERP API
SERP_API_KEY=your-actual-serpapi-key

# データベース
DATABASE_URL=postgresql://username:password@host:5432/dbname

# その他の設定
ENVIRONMENT=production
DEBUG=false
API_HOST=0.0.0.0
API_PORT=8000
```

### デプロイコマンド

```bash
cd backend

# Cloud Runにデプロイ
gcloud run deploy marketing-automation-backend \
  --source . \
  --region asia-northeast1 \
  --allow-unauthenticated \
  --port 8000 \
  --memory 2Gi \
  --cpu 1 \
  --set-env-vars="ALLOWED_ORIGINS=http://localhost:3000,http://localhost:3001,https://marketing-automation-three.vercel.app" \
  --set-env-vars="OPENAI_API_KEY=your-actual-key" \
  --set-env-vars="ENVIRONMENT=production"
```

## 2. フロントエンド（Vercel）の設定

### 環境変数

Vercelダッシュボードで以下の環境変数を設定：

```bash
# Clerk認証
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_your-actual-key
CLERK_SECRET_KEY=sk_test_your-actual-key
NEXT_PUBLIC_CLERK_SIGN_IN_URL=/sign-in
NEXT_PUBLIC_CLERK_SIGN_UP_URL=/sign-up
NEXT_PUBLIC_CLERK_AFTER_SIGN_IN_URL=/dashboard
NEXT_PUBLIC_CLERK_AFTER_SIGN_UP_URL=/dashboard

# API設定
NEXT_PUBLIC_API_BASE_URL=https://marketing-automation-742231208085.asia-northeast1.run.app

# アプリURL
NEXT_PUBLIC_APP_URL=https://marketing-automation-three.vercel.app
NEXT_PUBLIC_SITE_URL=https://marketing-automation-three.vercel.app
```

### デプロイコマンド

```bash
cd frontend

# Vercelにデプロイ
vercel --prod

# または、GitHubと連携して自動デプロイ
```

## 3. セキュリティ考慮事項

### CORS設定の重要性

バックエンドの `ALLOWED_ORIGINS` 環境変数には、必ずフロントエンドの正確なURLを含めてください：

- 開発環境: `http://localhost:3000`
- プレビュー環境: Vercelの各プレビューURL
- 本番環境: `https://marketing-automation-three.vercel.app`

### API キーの管理

- **本番環境**: 環境変数として設定
- **開発環境**: `.env.local` ファイルを使用（GitHubにコミットしない）

## 4. デプロイ順序

1. **バックエンドを先にデプロイ**
   ```bash
   cd backend
   gcloud run deploy marketing-automation-backend --source .
   ```

2. **デプロイされたURLを確認**
   ```bash
   gcloud run services describe marketing-automation-backend \
     --region asia-northeast1 \
     --format 'value(status.url)'
   ```

3. **フロントエンドの環境変数を更新**
   
4. **フロントエンドをデプロイ**
   ```bash
   cd frontend
   vercel --prod
   ```

## 5. トラブルシューティング

### CORSエラーが発生する場合

1. バックエンドの `ALLOWED_ORIGINS` にフロントエンドのURLが含まれているか確認
2. プロトコル（http/https）が正確に指定されているか確認
3. ポート番号の有無を確認

### API接続エラーが発生する場合

1. `NEXT_PUBLIC_API_BASE_URL` が正しく設定されているか確認
2. バックエンドサービスが正常に起動しているか確認
3. ネットワークファイアウォールの設定を確認

## 6. 監視とログ

### Cloud Runログの確認
```bash
gcloud logs read --service marketing-automation-backend \
  --region asia-northeast1 \
  --limit 50
```

### Vercelログの確認
Vercelダッシュボードの「Functions」タブでログを確認できます。

## 7. 更新手順

### バックエンドの更新
```bash
cd backend
gcloud run deploy marketing-automation-backend --source .
```

### フロントエンドの更新
GitHubにプッシュすると自動的にデプロイされます（GitHub連携済みの場合）。

手動でデプロイする場合：
```bash
cd frontend
vercel --prod
```