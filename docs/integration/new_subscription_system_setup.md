# 新サブスクリプションシステム セットアップガイド

## 概要

このドキュメントでは、新しいサブスクリプションシステムのセットアップ手順を説明します。
シンプルな1プラン構成（月額サブスクリプション）で、@shintairiku.jp ユーザーは特権アクセス（無料）が付与されます。

## アーキテクチャ

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Frontend      │     │    Stripe        │     │   Supabase      │
│   (Next.js)     │◄───►│   (決済処理)     │────►│   (データ)      │
│                 │     │                  │     │                 │
│ - Pricing Page  │     │ - Checkout       │     │ - user_         │
│ - Dashboard     │     │ - Portal         │     │   subscriptions │
│ - API Routes    │     │ - Webhooks       │     │ - subscription_ │
│                 │     │                  │     │   events        │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

## 必要な環境変数

### Frontend (.env.local)

```env
# Stripe
STRIPE_SECRET_KEY=sk_test_xxxx            # Stripe シークレットキー
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_xxxx  # Stripe パブリッシュキー
STRIPE_WEBHOOK_SECRET=whsec_xxxx          # Stripe Webhook シークレット
STRIPE_PRICE_ID=price_xxxx                # 商品の価格ID

# Supabase
NEXT_PUBLIC_SUPABASE_URL=https://xxxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=xxxx
SUPABASE_SERVICE_ROLE_KEY=xxxx

# Clerk
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_xxxx
CLERK_SECRET_KEY=sk_test_xxxx

# App URL
NEXT_PUBLIC_APP_URL=https://your-app.com  # 本番URL（開発時は http://localhost:3000）
```

## セットアップ手順

### 1. Stripeの設定

#### 1.1 商品の作成

1. [Stripe Dashboard](https://dashboard.stripe.com/products) にアクセス
2. 「+ 商品を追加」をクリック
3. 以下の情報を入力:
   - 名前: `プロプラン` または任意の名前
   - 説明: `すべての機能にアクセス可能な月額プラン`
4. 価格を設定:
   - 価格モデル: `定期購入`
   - 金額: `2980`（または任意の金額）
   - 通貨: `JPY`
   - 請求期間: `月次`
5. 保存して、生成された `price_xxxx` をコピー

#### 1.2 Webhook の設定

1. [Stripe Dashboard > Webhooks](https://dashboard.stripe.com/webhooks) にアクセス
2. 「エンドポイントを追加」をクリック
3. エンドポイントURL: `https://your-app.com/api/subscription/webhook`
4. リッスンするイベント:
   - `checkout.session.completed`
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.payment_succeeded`
   - `invoice.payment_failed`
5. 作成後、「署名シークレット」をコピー（`whsec_xxxx`）

### 2. Supabase の設定

#### 2.1 マイグレーションの実行

```bash
# プロジェクトルートから
cd shared/supabase

# マイグレーションを実行
supabase db push
# または
supabase migration up
```

マイグレーションファイル: `migrations/20260122000000_new_subscription_system.sql`

これにより以下が作成されます:
- `user_subscriptions` テーブル
- `subscription_events` テーブル（監査ログ）
- `has_active_access()` 関数
- 必要なRLSポリシー

### 3. 環境変数の設定

#### 開発環境

```bash
# frontend/.env.local
STRIPE_SECRET_KEY=sk_test_xxxx
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_xxxx
STRIPE_WEBHOOK_SECRET=whsec_xxxx
STRIPE_PRICE_ID=price_xxxx
NEXT_PUBLIC_APP_URL=http://localhost:3000
```

#### 本番環境

本番用のStripeキーに切り替え、環境変数を更新してください。

### 4. ローカルでの Webhook テスト

Stripe CLIを使用してローカルでWebhookをテストできます:

```bash
# Stripe CLI をインストール
brew install stripe/stripe-cli/stripe

# Stripe にログイン
stripe login

# Webhook をローカルにフォワード
stripe listen --forward-to localhost:3000/api/subscription/webhook

# 別ターミナルでテストイベントをトリガー
stripe trigger checkout.session.completed
```

## 実装されたファイル

### API Routes

| ファイル | 説明 |
|---------|------|
| `/api/subscription/checkout` | Checkout Session 作成 |
| `/api/subscription/portal` | Customer Portal へのリダイレクト |
| `/api/subscription/status` | サブスクリプション状態の取得 |
| `/api/subscription/webhook` | Stripe Webhook ハンドラー |

### Components

| ファイル | 説明 |
|---------|------|
| `/components/subscription/subscription-guard.tsx` | アクセス制御コンポーネント |

### ライブラリ

| ファイル | 説明 |
|---------|------|
| `/lib/subscription/index.ts` | Stripe クライアント、型定義、ヘルパー関数 |

## アクセス制御

### SubscriptionProvider

アプリケーション全体でサブスクリプション状態を管理するContext Provider。

```tsx
import { SubscriptionProvider } from '@/components/subscription/subscription-guard';

function Layout({ children }) {
  return (
    <SubscriptionProvider>
      {children}
    </SubscriptionProvider>
  );
}
```

### SubscriptionGuard

サブスクリプションが有効でない場合、Pricingページにリダイレクト。

```tsx
import { SubscriptionGuard } from '@/components/subscription/subscription-guard';

function ProtectedPage() {
  return (
    <SubscriptionGuard>
      <YourContent />
    </SubscriptionGuard>
  );
}
```

### SubscriptionBanner

サブスクリプション状態に応じたバナー表示。

```tsx
import { SubscriptionBanner } from '@/components/subscription/subscription-guard';

function Dashboard() {
  return (
    <>
      <SubscriptionBanner />
      <DashboardContent />
    </>
  );
}
```

### useSubscription Hook

サブスクリプション情報へのアクセス。

```tsx
import { useSubscription } from '@/components/subscription/subscription-guard';

function Component() {
  const { subscription, hasAccess, isLoading, refetch } = useSubscription();

  if (isLoading) return <Loading />;
  if (!hasAccess) return <UpgradePrompt />;

  return <Content />;
}
```

## 特権ユーザー

`@shintairiku.jp` ドメインのメールアドレスを持つユーザーは、サブスクリプションなしですべての機能にアクセスできます。

この判定は以下で行われます:
- フロントエンド: `isPrivilegedEmail()` 関数
- バックエンド: `is_admin_email()` 関数
- データベース: `user_subscriptions.is_privileged` フラグ

## サブスクリプション状態

| 状態 | 説明 | アクセス |
|------|------|---------|
| `active` | 有効なサブスクリプション | 可 |
| `past_due` | 支払い遅延（3日間の猶予） | 可（猶予期間中） |
| `canceled` | キャンセル済み | 可（期間終了まで） |
| `expired` | 期限切れ | 不可 |
| `none` | サブスクリプションなし | 不可 |

## トラブルシューティング

### Webhook が動作しない

1. `STRIPE_WEBHOOK_SECRET` が正しいか確認
2. Webhookエンドポイントが公開アクセス可能か確認
3. Stripe Dashboard でイベントログを確認

### サブスクリプション状態が更新されない

1. Supabase の `user_subscriptions` テーブルを確認
2. `subscription_events` テーブルでイベントログを確認
3. Stripe Dashboard でサブスクリプション状態を確認

### チェックアウトが失敗する

1. `STRIPE_PRICE_ID` が正しいか確認
2. Stripe Dashboard で商品が有効か確認
3. ブラウザのコンソールでエラーを確認

## 参考リンク

- [Stripe Checkout ドキュメント](https://stripe.com/docs/checkout)
- [Stripe Customer Portal](https://stripe.com/docs/billing/subscriptions/customer-portal)
- [Stripe Webhooks](https://stripe.com/docs/webhooks)
- [Supabase RLS](https://supabase.com/docs/guides/auth/row-level-security)
