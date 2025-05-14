# Next.js + Supabase + Stripe + FastAPI プロジェクトスターター

このリポジトリは、モダンな技術スタックを用いたフルスタックアプリケーションの開発を迅速に開始するためのスターターキットです。
フロントエンドは Next.js (with TypeScript, Tailwind CSS, Shadcn/UI)、Supabase (データベース、認証)、Stripe (決済) を使用し、バックエンドは Python (FastAPI) で構築されています。
Docker を用いた開発環境が整備されており、チームでの開発をスムーズに進めることを目指しています。

## 目次

- [Next.js + Supabase + Stripe + FastAPI プロジェクトスターター](#nextjs--supabase--stripe--fastapi-プロジェクトスターター)
  - [目次](#目次)
  - [プロジェクト概要](#プロジェクト概要)
  - [前提条件](#前提条件)
  - [プロジェクト構造](#プロジェクト構造)
  - [環境構築](#環境構築)
    - [リポジトリのクローン](#リポジトリのクローン)
    - [環境変数の設定](#環境変数の設定)
  - [Docker を使用した開発](#docker-を使用した開発)
    - [docker-compose.yml の概要](#docker-composeyml-の概要)
    - [開発環境の起動](#開発環境の起動)
    - [各サービスへのアクセス](#各サービスへのアクセス)
    - [ログの確認](#ログの確認)
    - [コンテナの停止・削除](#コンテナの停止削除)
  - [フロントエンド開発 (frontend/)](#フロントエンド開発-frontend)
    - [フロントエンド概要](#フロントエンド概要)
    - [フロントエンドセットアップとローカル実行](#フロントエンドセットアップとローカル実行)
    - [フロントエンド詳細](#フロントエンド詳細)
  - [バックエンド開発 (backend/)](#バックエンド開発-backend)
    - [バックエンド概要](#バックエンド概要)
    - [バックエンドセットアップとローカル実行](#バックエンドセットアップとローカル実行)
    - [バックエンド詳細](#バックエンド詳細)
  - [データベース (Supabase)](#データベース-supabase)
    - [マイグレーション](#マイグレーション)
    - [型生成 (フロントエンド用)](#型生成-フロントエンド用)
  - [Stripe 連携](#stripe-連携)
    - [Webhook のテスト](#webhook-のテスト)
  - [チーム開発のヒント](#チーム開発のヒント)
    - [ブランチ戦略](#ブランチ戦略)
    - [コードレビュー](#コードレビュー)
    - [コーディング規約](#コーディング規約)
    - [Issue トラッキング](#issue-トラッキング)
    - [ドキュメント](#ドキュメント)
  - [デプロイメント](#デプロイメント)
  - [トラブルシューティング](#トラブルシューティング)

## プロジェクト概要

- **フロントエンド**: Next.js を使用したインタラクティブなUI。Supabase によるユーザー認証とデータ管理、Stripe による決済機能。
- **バックエンド**: FastAPI を使用した Python 製 API。OpenAI API を利用した SEO 記事の自動生成機能などを提供 (詳細は `backend/README.md` を参照)。
- **データベース**: Supabase (PostgreSQL)
- **開発環境**: Docker Compose により、フロントエンド、バックエンド、Stripe CLI を統合。

## 前提条件

開発を始める前に、DockerDesktopがインストールされていることを確認して下さい。WSLの方は、Windows上にDockerDesktopをインストールしてください。

## プロジェクト構造

```
.
├── backend/              # FastAPI バックエンドアプリケーション
│   ├── api/              # API エンドポイント定義
│   ├── core/             # 設定、例外処理など
│   ├── schemas/          # Pydantic スキーマ
│   ├── services/         # ビジネスロジック
│   ├── utils/            # ユーティリティ
│   ├── Dockerfile        # バックエンド Docker イメージ
│   ├── main.py           # FastAPI アプリケーションエントリーポイント
│   ├── requirements.txt  # Python 依存関係
│   ├── pyproject.toml    # Python プロジェクト設定
│   └── README.md         # バックエンド詳細ガイド
├── frontend/             # Next.js フロントエンドアプリケーション
│   ├── src/
│   │   ├── app/
│   │   ├── components/
│   │   ├── features/
│   │   ├── hooks/
│   │   ├── libs/
│   │   ├── styles/
│   │   ├── types/
│   │   └── utils/
│   ├── Dockerfile        # フロントエンド Docker イメージ (開発用・本番用)
│   ├── package.json      # Node.js 依存関係、スクリプト
│   └── README.md         # フロントエンド詳細ガイド
├── supabase/             # Supabase マイグレーションファイルなど
│   └── migrations/
├── .env.local.example    # プロジェクト全体の環境変数テンプレート
├── .gitignore
├── docker-compose.yml    # Docker Compose 設定ファイル
├── LICENSE               # プロジェクトライセンス (適宜設定)
└── README.md             # このファイル (プロジェクト全体ガイド)
```

## 環境構築

### リポジトリのクローン

```bash
git clone <リポジトリURL>
cd <リポジトリ名>
```

### 環境変数の設定

プロジェクトルートに `.env.local` という名前のファイルを作成し、必要な環境変数を設定します。
このファイルは `.gitignore` に登録されており、Git の管理対象外となります。
テンプレートとして `.env.local.example` があれば、それをコピーして使用してください。

**主要な環境変数:**

```env
# Supabase (frontend および backend から参照される可能性あり)
NEXT_PUBLIC_SUPABASE_URL=your_supabase_project_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key # バックエンドやNext.jsサーバーサイドで使用

# Stripe (frontend および backend から参照される可能性あり)
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=your_stripe_publishable_key
STRIPE_SECRET_KEY=your_stripe_secret_key # バックエンドやNext.jsサーバーサイド、Stripe CLIで使用
STRIPE_WEBHOOK_SECRET=your_stripe_webhook_secret # フロントエンドのWebhookハンドラで使用 (stripe listen から取得)

# Backend (FastAPI)
OPENAI_API_KEY=your_openai_api_key # バックエンドのOpenAI連携用
# その他バックエンド固有の環境変数は backend/.env または backend/README.md を参照

# Frontend (Next.js)
# NEXT_PUBLIC_SITE_URL=http://localhost:3000 # 必要に応じて
```

**注意点:**
- `frontend/` ディレクトリ内にも `.env.local` を作成し、フロントエンド固有のビルド時引数 (Dockerビルド時に `NEXT_PUBLIC_`変数を渡すため) や開発時の環境変数を設定します。通常はプロジェクトルートの `.env.local` の内容を一部コピー＆ペーストすることになります。
- `backend/` ディレクトリにも `.env` ファイルを作成し、バックエンド固有の環境変数を設定します (例: `OPENAI_API_KEY`)。
- `docker-compose.yml` では、各サービスがどの `.env` ファイルを参照するかが `env_file` ディレクティブで指定されています。

## Docker を使用した開発

`docker-compose.yml` を使うことで、複数のサービス（フロントエンド、バックエンド、Stripe CLI）をまとめて管理・実行できます。

### docker-compose.yml の概要

- **`frontend_dev`**: Next.js フロントエンドの開発用サービス。ホットリロード対応。
- **`frontend_prod`**: Next.js フロントエンドの本番ビルド用サービス (デプロイの参考)。
- **`backend`**: FastAPI バックエンドAPIサービス。
- **`stripe-cli`**: Stripe Webhook イベントをローカルの `frontend_dev` サービスに転送。

各サービスの Docker イメージは、それぞれのディレクトリ ( `frontend/` および `backend/` ) にある `Dockerfile` を基にビルドされます。

### 開発環境の起動

必要な `.env` ファイルを設定した後、以下のコマンドで開発に必要なサービスを起動します。

```bash
docker-compose up -d frontend_dev backend stripe-cli
```
`-d` オプションはデタッチモードで起動し、バックグラウンドで実行します。初回の起動時はイメージのビルドに時間がかかることがあります。

特定のサービスのみを起動・再起動したい場合:
```bash
docker-compose up -d <サービス名> # 例: docker-compose up -d backend
docker-compose restart <サービス名>
```

### 各サービスへのアクセス

- **フロントエンド (Next.js)**: `http://localhost:3000`
- **バックエンド (FastAPI)**: `http://localhost:8008` (APIドキュメントは `http://localhost:8008/docs` や `http://localhost:8008/redoc` で確認可能。`backend/main.py` の設定による)
- **バックエンドテストクライアント (あれば)**: `http://localhost:8008/test-client` ( `backend/main.py` で定義されている場合)

### ログの確認

各サービスのログは以下のコマンドで確認できます。

```bash
docker-compose logs -f <サービス名> # 例: docker-compose logs -f frontend_dev
docker-compose logs -f # 全サービスのログ
```
`-f` オプションはログを追従表示します。

### コンテナの停止・削除

起動中のコンテナを停止するには:
```bash
docker-compose down
```
このコマンドはコンテナを停止し、作成されたネットワークも削除します。
ボリュームは削除されません。ボリュームも完全に削除したい場合は `docker-compose down -v` を使用します。

## フロントエンド開発 (frontend/)

### フロントエンド概要
Next.js (App Router), TypeScript, Tailwind CSS, Shadcn/UI, Supabase, Stripe を使用。

### フロントエンドセットアップとローカル実行
Docker を使わずにローカルでフロントエンドのみを開発する場合:

1.  **ディレクトリ移動**: `cd frontend`
2.  **環境変数**: `frontend/.env.local` を設定 (プロジェクトルートの `.env.local` から関連するものをコピー)。
3.  **依存関係インストール**: `npm install` (または `bun install`)
4.  **Supabase連携と型生成**:
    ```bash
    # プロジェクトルートの .env.local を参照して Supabase プロジェクトID を確認
    npx env-cmd -f .env.local supabase link --project-ref <あなたのSupabaseプロジェクトID>
    npm run generate-types
    ```
5.  **Supabaseマイグレーション**: (Supabase Studio や CLI でスキーマ変更後)
    ```bash
    # プロジェクトルートから実行
    # npx supabase migration up --linked
    ```
6.  **開発サーバー起動**: `npm run dev`
    ブラウザで `http://localhost:3000` を開きます。

### フロントエンド詳細
より詳しい情報は `frontend/README.md` を参照してください。

## バックエンド開発 (backend/)

### バックエンド概要
Python, FastAPI を使用。SEO 記事生成機能など。

### バックエンドセットアップとローカル実行
Docker を使わずにローカルでバックエンドのみを開発する場合:

1.  **ディレクトリ移動**: `cd backend`
2.  **環境変数**: `backend/.env` を設定 (例: `OPENAI_API_KEY`)。
3.  **仮想環境作成 (推奨)**:
    ```bash
    python -m venv venv
    source venv/bin/activate # Linux/macOS
    # venv\Scripts\activate # Windows
    ```
4.  **依存関係インストール**: `pip install -r requirements.txt`
5.  **開発サーバー起動**: `uvicorn main:app --reload --host 0.0.0.0 --port 8000`
    API は `http://localhost:8000` で利用可能になります。

### バックエンド詳細
より詳しい情報は `backend/README.md` を参照してください。

## データベース (Supabase)

データベーススキーマの管理は `supabase/migrations` ディレクトリ内のマイグレーションファイルによって行われます。

### マイグレーション
ローカルでの開発中や Supabase Studio でスキーマを変更した後は、以下のコマンドでマイグレーションファイルを更新・適用します。
Supabase CLI とプロジェクトがリンクされていることを確認してください (`npx supabase link --project-ref <your-project-ref>`)。

```bash
# (変更を検知して) 新しいマイグレーションファイルを作成
npx supabase db diff -f <migration_name>
# または直接マイグレーションファイルを作成・編集
# npx supabase migration new <migration_name>

# ローカルのマイグレーションをリンクされた Supabase プロジェクトに適用
npx supabase migration up --linked
```
チームで開発する場合、他のメンバーが作成したマイグレーションを取り込むには、リポジトリをプルした後 `npx supabase migration up --linked` を実行します。

### 型生成 (フロントエンド用)
データベーススキーマの変更後、フロントエンドで Supabase クライアントの型安全性を保つために型定義を再生成します。
`frontend` ディレクトリで以下のコマンドを実行します。

```bash
npm run generate-types
```
これは `supabase gen types typescript ...` コマンドを実行します。

## Stripe 連携

### Webhook のテスト
Stripe のイベント (決済成功など) をローカルでテストするために、Stripe CLI を使用します。
`docker-compose.yml` で `stripe-cli` サービスが設定されており、`frontend_dev` サービスの `/api/webhooks` エンドポイントにイベントを転送します。

1.  `docker-compose up -d stripe-cli frontend_dev` でサービスを起動。
2.  Stripe CLI が起動すると、ターミナルに Webhook signing secret (`whsec_...`) が表示されます。これをコピーします。
3.  プロジェクトルートの `.env.local` および `frontend/.env.local` の `STRIPE_WEBHOOK_SECRET` に設定します。
4.  フロントエンドの Webhook ハンドラー (`frontend/src/app/api/webhooks/route.ts` など) が正しく設定されていることを確認します。

Stripe ダッシュボードからテストイベントを送信するか、ローカルでStripeを利用する操作（テスト決済など）を行うことで、Webhookがローカル環境で受信できるか確認できます。

## チーム開発のヒント

### ブランチ戦略
- `main` (または `master`): 本番リリース用の安定ブランチ。
- `develop`: 最新の開発ブランチ。機能開発が完了し、テストされたものがマージされる。
- `feature/<issue-id>-<description>`: 個別の機能開発用ブランチ。`develop` から分岐し、完了後に `develop` へプルリクエスト。
- `fix/<issue-id>-<description>`: バグ修正用ブランチ。
- `hotfix/<issue-id>-<description>`: 緊急の本番バグ修正用ブランチ。`main` から分岐し、修正後 `main` と `develop` にマージ。

Git Flow や GitHub Flow などを参考に、チームに合ったブランチ戦略を導入しましょう。

### コードレビュー
- プルリクエスト (マージリクエスト) を通じてコードレビューを実施します。
- 最低1人以上のレビュアーによる承認を必須とするなどのルールを設けます。
- 建設的なフィードバックを心がけ、コードの品質向上と知識共有を目指します。

### コーディング規約

### Issue トラッキング

### ドキュメント
- この `README.md` や各サブディレクトリの `README.md` を最新の状態に保ちます。
- APIドキュメント (FastAPI の自動生成ドキュメントなど) も活用します。
- 複雑なロジックやアーキテクチャの決定事項は別途ドキュメント化することを検討します。

## デプロイメント

デプロイ戦略

- **バックエンド**:
  `backend/Dockerfile` を使用して Docker イメージをビルドし、コンテナホスティングサービス (例: AWS ECS, Google Cloud Run, DigitalOcean App Platform) にデプロイします。
  データベース (Supabase) や Stripe の本番用キーを環境変数として設定する必要があります。

CI/CD パイプラインを構築し、テスト、ビルド、デプロイのプロセスを自動化することを強く推奨します。

## トラブルシューティング

- **Docker関連のエラー**:
  - ポートが既に使用されている場合: `docker-compose down` で一度コンテナを停止するか、`docker-compose.yml` で使用ポートを変更。
  - ビルドエラー: Dockerfile の内容や依存関係のバージョンを確認。
- **環境変数が読み込まれない**: `.env` ファイルのパスやファイル名が正しいか、`docker-compose.yml` の `env_file` 設定が正しいか確認。
- **各サービスのログを確認**: `docker-compose logs -f <サービス名>` でエラーメッセージを確認。


