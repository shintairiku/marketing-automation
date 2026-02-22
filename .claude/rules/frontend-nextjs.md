---
paths: frontend/src/**/*.ts,frontend/src/**/*.tsx,frontend/src/**/*.css
---

# Frontend Next.js ルール

## Feature-Based Architecture
- `features/` にドメイン単位のUI (landing, pricing, blog, article-generation, tools)
- `components/` に共通UI (shadcn/ui, display, layout)
- `hooks/` にビジネスロジック (Supabase Realtime, 記事生成, 自動保存)
- `lib/` にインフラ (ApiClient, サブスクリプション)

## Realtime State Management
- Supabase Realtime で記事生成の進捗をリアルタイム同期
- ポーリングは無効化（DBが信頼の源泉）
- `useArticleGenerationRealtime` フック (1,460+行) がフロントエンド側の全状態管理を担当

## API Proxy パターン (USE_PROXY)
- 本番 (Vercel): `/api/proxy/[...path]` → route handler → IAMトークン付与 → Cloud Run
- 開発: `localhost:8080` 直接
```typescript
const USE_PROXY = process.env.NODE_ENV === 'production';
const baseURL = USE_PROXY ? '/api/proxy' : API_BASE_URL;
```
- **ブラウザから直接 Cloud Run にfetchするコードは禁止** (Cloud Run 非公開のため 403 エラー)

## Cloud Run IAM認証 (フロント側)
- `lib/google-auth.ts`: Google ID Token生成
- `lib/backend-fetch.ts`: `Authorization` (Clerk JWT) + `X-Serverless-Authorization` (Google ID Token)
- `CLOUD_RUN_AUDIENCE_URL` 未設定時 (開発環境) は IAM ヘッダーなし

## SubscriptionGuard
- `(tools)` レイアウト内のみ。`(settings)` は未課金でもアクセス可
- フリープランユーザーは `status: 'active'` + `plan_tier_id: 'free'`（SubscriptionGuard変更不要）

## ロゴ使用ルール
- **ライト背景** (サイドバー等): `logo.png` (横長) or `icon.png` (正方形)
- **ダーク背景** (ヘッダー、認証画面等): `logo-white.png`
- **ファビコン/PWA**: `favicon.png`, `icon-*.png`, `icon-maskable-*.png`

## PWA
- `app/manifest.ts` → `/manifest.webmanifest` として自動配信
- `public/sw.js` カスタムサービスワーカー (ナビゲーション: network-first, 静的アセット: stale-while-revalidate)
- API/認証リクエストは SW をバイパス

## フォント
- `@fontsource-variable/noto-sans-jp` (セルフホスト、ビルド時外部ネットワーク不要)
- `globals.css` で `@import` 、`tailwind.config.ts` で `Noto Sans JP Variable` を指定
