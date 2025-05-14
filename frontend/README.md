# supabase-nextjs-starter フロントエンド

このプロジェクトは、Next.js, Supabase, Stripe を使用したスターターキットのフロントエンド部分です。

## 概要

ユーザー認証、商品表示、Stripe を介した決済機能などを提供することを目的としています。モダンなウェブ技術スタックを用いて構築されており、迅速な開発スタートを支援します。

## 主な使用技術

- **フレームワーク**: [Next.js](https://nextjs.org/) (App Router, Turbopack)
- **UIライブラリ**:
    - [React](https://react.dev/)
    - [Shadcn/UI](https://ui.shadcn.com/) (Radix UI, Lucide React)
    - [Geist UI](https://geist-ui.dev/)
- **状態管理・データフェッチ**: React Server Components, SWR, または Supabase client
- **データベース・認証**: [Supabase](https://supabase.io/)
- **決済**: [Stripe](https://stripe.com/)
- **スタイリング**: [Tailwind CSS](https://tailwindcss.com/)
- **型チェック**: [TypeScript](https://www.typescriptlang.org/)
- **バリデーション**: [Zod](https://zod.dev/)
- **メール**: [React Email](https://react.email/)
- **リンター・フォーマッター**: ESLint, Prettier
- **パッケージマネージャー**: npm (または Bun も利用可能)
- **コンテナ化**: Docker

## ディレクトリ構造 (主要部分)

```
frontend
├── src
│   ├── app/          # Next.js App Router (ページ、レイアウト、APIルートなど)
│   ├── components/   # 再利用可能なUIコンポーネント (Shadcn/UI, カスタム)
│   ├── features/     # 特定機能関連のモジュール
│   ├── hooks/        # カスタムReact Hooks
│   ├── libs/         # ライブラリ連携 (Supabaseクライアント, Stripeヘルパーなど)
│   │   └── supabase/
│   │       └── types.ts # Supabase から生成された型定義
│   ├── styles/       # グローバルスタイル、Tailwind CSS設定
│   ├── types/        # カスタム型定義
│   ├── utils/        # 汎用ユーティリティ関数
│   └── middleware.ts # Next.js ミドルウェア
├── .env.local.example # 環境変数設定のサンプル (各自 .env.local を作成)
├── next.config.js     # Next.js 設定ファイル
├── tailwind.config.ts # Tailwind CSS 設定ファイル
├── tsconfig.json      # TypeScript 設定ファイル
├── package.json       # プロジェクト定義、スクリプト、依存関係
└── Dockerfile         # Docker イメージ構築用ファイル
```

## セットアップと実行方法

### 1. 前提条件

- Node.js (v18 以降推奨)
- npm (Node.js に付属) または Bun
- Stripe CLI (Webhook のテストに必要)
- Supabase CLI (マイグレーション、型生成に必要)

### 2. プロジェクトのクローンと依存関係のインストール

```bash
git clone <リポジトリURL>
cd frontend
npm install
# または bun install
```

### 3. 環境変数の設定

プロジェクトルート (frontend ディレクトリ直下) に `.env.local` ファイルを作成し、必要な環境変数を設定します。
Supabase のプロジェクト URL と anon キー、Stripe の公開可能キーとシークレットキーなどが必要です。
`supabase:link` コマンドや Supabase, Stripe のダッシュボードから取得してください。

`.env.local.example` があれば、それをコピーして編集してください。なければ、以下のような内容になります。

```env
# Supabase
NEXT_PUBLIC_SUPABASE_URL=your_supabase_url
NEXT_PUBLIC_SUPABASE_ANON_KEY=your_supabase_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key # サーバーサイドで使用

# Stripe
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=your_stripe_publishable_key
STRIPE_SECRET_KEY=your_stripe_secret_key
STRIPE_WEBHOOK_SECRET=your_stripe_webhook_secret # stripe listen コマンドから取得

# その他 (必要に応じて)
# NEXT_PUBLIC_SITE_URL=http://localhost:3000
```

**注意**: `SUPABASE_SERVICE_ROLE_KEY` や `STRIPE_SECRET_KEY` などのシークレットキーは、Next.js のサーバーサイド環境でのみ使用し、クライアントには公開しないでください。

### 4. Supabase プロジェクトとの連携と型生成

Supabase プロジェクトを作成または既存のものを使用し、以下のコマンドで連携と型生成を行います。
`wptklzekgtduiluwzhap` の部分は実際の Supabase プロジェクトIDに置き換えてください。

```bash
npx env-cmd -f ./.env.local supabase link --project-ref wptklzekgtduiluwzhap
npm run generate-types
```

### 5. Supabase マイグレーションの実行

データベーススキーマをセットアップします。

```bash
# 新しいマイグレーションファイルを作成する場合 (初回や変更時)
# npx supabase migration new <migration_name>

# マイグレーションを実行
npx supabase migration up --linked
# 実行後、再度型を生成するとより安全です
npm run generate-types
```

### 6. 開発サーバーの起動

```bash
npm run dev
# または bun dev
```

ブラウザで `http://localhost:3000` を開きます。

### 7. Stripe Webhook のリッスン (決済テスト時)

Stripe のイベントをローカルで受け取るために、別のターミナルで以下のコマンドを実行します。

```bash
stripe listen --forward-to=localhost:3000/api/webhooks
```

表示された Webhook signing secret (`whsec_...`) を `.env.local` の `STRIPE_WEBHOOK_SECRET` に設定してください。

## ビルドと本番起動

```bash
# ビルド
npm run build
# または bun build

# 本番サーバー起動
npm run start
# または bun start
```

## 利用可能なスクリプト

- `npm run dev`: 開発モードで Next.js (Turbopack) を起動
- `npm run build`: 本番用にアプリケーションをビルド
- `npm run start`: ビルドされたアプリケーションを起動
- `npm run lint`: ESLint を使用してコードをリント
- `npm run stripe:listen`: Stripe CLI を起動し、ローカルの Webhook エンドポイントにイベントを転送
- `npm run generate-types`: Supabase から TypeScript の型定義を生成
- `npm run supabase:link`: ローカルプロジェクトを Supabase プロジェクトにリンク
- `npm run migration:new`: 新しい Supabase マイグレーションファイルを作成
- `npm run migration:up`: Supabase マイグレーションを実行し、型を再生成
- `npm run migration:squash`: Supabase マイグレーションをスカッシュ（統合）
