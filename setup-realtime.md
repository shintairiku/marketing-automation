# Supabase Realtime記事生成 セットアップガイド

## 🚀 セットアップ手順

### 1. 環境変数の確認

#### バックエンド (.env)
以下の環境変数が設定済みです：
```bash
# Cloud Tasks設定 (新規追加)
CLOUD_TASKS_LOCATION=asia-northeast1
CLOUD_TASKS_QUEUE=article-generation-queue
BACKEND_URL=http://localhost:8000

# 既存の設定
GOOGLE_CLOUD_PROJECT=marketing-automation-461305
GOOGLE_SERVICE_ACCOUNT_JSON_FILE=marketing-automation-461305-d3821e14ba9f.json
SUPABASE_URL=https://pytxohnkkyshobprrjqh.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

#### フロントエンド (.env.local)
以下の環境変数が設定済みです：
```bash
# Realtime有効化フラグ (新規追加)
NEXT_PUBLIC_REALTIME_ENABLED=true
BACKEND_URL=http://localhost:8000

# 既存の設定
NEXT_PUBLIC_SUPABASE_URL=https://pytxohnkkyshobprrjqh.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### 2. Cloud Tasksキューの作成

```bash
# Google Cloud CLIでログイン
gcloud auth login

# プロジェクトを設定
gcloud config set project marketing-automation-461305

# Cloud Tasksキューを作成
gcloud tasks queues create article-generation-queue \
  --location=asia-northeast1

# キューの作成を確認
gcloud tasks queues list --location=asia-northeast1
```

### 3. 依存関係のインストール

#### バックエンド
```bash
cd backend
pip install google-cloud-tasks>=2.16.0
# または
uv add google-cloud-tasks>=2.16.0
```

#### フロントエンド
```bash
cd frontend
npm install  # 既存の依存関係で十分
```

### 4. データベースの確認

Supabase Realtimeが`generated_articles_state`テーブルで有効化されていることを確認：

```sql
-- Supabaseダッシュボードで実行
SELECT schemaname, tablename 
FROM pg_tables 
WHERE tablename = 'generated_articles_state';

-- Realtime Publicationの確認
SELECT * FROM pg_publication_tables 
WHERE pubname = 'supabase_realtime' 
AND tablename = 'generated_articles_state';
```

## 🎯 使用方法

### 1. アプリケーションの起動

#### バックエンド
```bash
cd backend
uvicorn main:app --reload --port 8000
```

#### フロントエンド
```bash
cd frontend
npm run dev
```

### 2. Realtime記事生成の開始

1. **従来の方法（自動切り替え）**
   - `/seo/generate/new-article` にアクセス
   - `NEXT_PUBLIC_REALTIME_ENABLED=true` の場合、自動的にRealtimeベースに切り替わる

2. **直接Realtime版を使用**
   - `/seo/generate/realtime-article` にアクセス
   - Realtime専用の開始ページから生成を開始

### 3. 進捗の監視

- 生成開始後、`/tools/seo/generate/realtime-article/[process_id]` に自動リダイレクト
- Supabase Realtimeでリアルタイム進捗更新
- 複数タブで同時監視可能

## 🔄 フロー比較

### 従来（WebSocket）
```
フロントエンド ←→ WebSocket ←→ バックエンド
    ↓
中断リスク・接続制限あり
```

### 新システム（Supabase Realtime）
```
フロントエンド → REST API → バックエンド
    ↓                          ↓
Supabase Realtime ←── Cloud Tasks
    ↑
リアルタイム進捗同期
```

## 🐛 トラブルシューティング

### 1. Cloud Tasksエラー
```bash
# キューの状態確認
gcloud tasks queues describe article-generation-queue \
  --location=asia-northeast1

# タスクの一覧確認
gcloud tasks list --queue=article-generation-queue \
  --location=asia-northeast1
```

### 2. Supabase Realtimeエラー
- ブラウザのDeveloper Toolsでコンソールエラーを確認
- Supabaseダッシュボードでテーブル権限を確認
- RLS（Row Level Security）ポリシーを確認

### 3. 環境変数エラー
```bash
# バックエンド環境変数の確認
cd backend && python -c "import os; print('CLOUD_TASKS_LOCATION:', os.getenv('CLOUD_TASKS_LOCATION'))"

# フロントエンド環境変数の確認
echo $NEXT_PUBLIC_REALTIME_ENABLED
```

## 📊 監視・ログ

### Cloud Tasksの監視
- Google Cloud Console → Cloud Tasks
- キューの処理状況とエラーログを確認

### Supabaseの監視
- Supabaseダッシュボード → Logs
- Realtimeイベントとデータベース変更を確認

### アプリケーションログ
```bash
# バックエンドログ
tail -f backend/logs/app.log

# ブラウザコンソール
F12 → Console タブ
```

## ✅ 動作確認チェックリスト

- [ ] Cloud Tasksキューが作成されている
- [ ] バックエンドが起動している（ポート8000）
- [ ] フロントエンドが起動している（ポート3000）
- [ ] `/seo/generate/realtime-article` にアクセスできる
- [ ] 記事生成を開始できる
- [ ] 進捗がリアルタイムで更新される
- [ ] ユーザー入力（ペルソナ選択等）が動作する
- [ ] 最終的に記事が完成する

## 🔄 従来版への切り替え

Realtime版でエラーが発生した場合の緊急時切り替え方法：

```bash
# フロントエンド .env.local を編集
NEXT_PUBLIC_REALTIME_ENABLED=false
```

この設定により、既存のWebSocket版に自動的に切り替わります。