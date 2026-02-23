# Frontend (Next.js 15 + React 19 + TypeScript)

> このファイルは frontend/ ディレクトリのファイルを操作する際に自動ロードされる。

## Project Structure
```
frontend/
├── package.json                  # Bun依存関係
├── next.config.js                # API proxy, 画像ドメイン設定
├── tailwind.config.ts            # カスタムカラー・フォント
├── Dockerfile                    # Next.js standalone
└── src/
    ├── middleware.ts             # Clerk認証 + ルート保護 + 特権チェック
    ├── app/
    │   ├── layout.tsx            # ルートレイアウト (ClerkProvider, Noto Sans JP)
    │   ├── manifest.ts           # PWA マニフェスト
    │   ├── auth/page.tsx         # 認証選択画面
    │   ├── (tools)/              # メインツール群 (SubscriptionGuard有)
    │   │   └── blog/             # Blog AI
    │   ├── (settings)/           # 設定群 (SubscriptionGuardなし)
    │   │   └── settings/         # /settings/* ページ
    │   ├── (admin)/              # 管理者画面 (特権のみ)
    │   ├── sign-in/ sign-up/     # Clerk認証
    │   └── api/                  # Next.js API Routes
    │       ├── proxy/[...path]/  # バックエンドAPIプロキシ
    │       ├── subscription/     # Stripe checkout/portal/status/webhook
    │       └── webhooks/clerk    # Clerk webhook
    ├── components/
    │   ├── ui/                   # shadcn/ui
    │   ├── display/              # header, sidebar, pageTabs
    │   ├── layout/               # AppLayoutClient
    │   ├── subscription/         # SubscriptionGuard, Banner
    │   ├── blog/                 # wordpress-onboarding
    │   └── pwa/                  # service-worker-register
    ├── features/                 # ドメイン単位のUI
    ├── hooks/                    # Supabase Realtime, 記事生成等
    ├── lib/
    │   ├── api.ts               # ApiClientクラス
    │   ├── google-auth.ts       # Cloud Run IAM認証
    │   ├── backend-fetch.ts     # バックエンドfetchヘルパー
    │   └── subscription/        # サブスクリプションロジック
    ├── utils/                   # cn, image-compress等
    └── styles/globals.css       # グローバルCSS
```

## デプロイ
- Vercel (Production: main, Preview: develop)
- Next.js standalone 出力
- 環境変数: Production/Preview スコープ別に設定
- Cloud Run IAM: `CLOUD_RUN_AUDIENCE_URL` + `GOOGLE_SA_KEY_BASE64`

## ビルド
```bash
cd frontend && bun run lint && bun run build
```

## 注意点
- `AppLayoutClient` が `mt-[45px]` + `p-3` を適用 → 子ページで `min-h-screen` を使うとビューポート超過。全高が必要な場合は `calc(100dvh - 57px)` を使う
- `next/font/google` は使わない (ネットワーク依存)。`@fontsource-variable/noto-sans-jp` でセルフホスト
