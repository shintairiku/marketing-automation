# Clerk / Supabase / Stripe 連携によるサブスクリプション実装ガイド

## 概要

1. **利用者とプラン体系**
   - Clerk をID基盤として採用し、個人課金とチーム課金（seat制）を統一的に管理。
   - プランごとに利用できる機能や上限値を Supabase のマスターテーブルで定義し、未確定の制限も実装しやすい拡張性を確保。（まだ詳細にはどんなプランの制限や特典を用意するか決まってません）
2. **組織機能**
   - Clerk Organizations を有効化し、Stripe の team プランと連携。購入 seat 数を超えた招待を防ぐ仕組みを Supabase/Clerk 双方で構築。
3. **課金フロー**
   - Vercel 上の Next.js Route Handler で Stripe Checkout / Customer Portal を発行。
   - Google Cloud Run 上のバックエンドで Stripe Webhook を処理し、Supabase に確実に書き込む。`stripe_events` テーブルで冪等性を担保。
4. **データベース設計**
   - 旧 Supabase Auth 依存の `uuid` 型を廃止し、Clerk ID（`user_xxx`）に統一。
   - `customers`, `subscriptions`, `organization_subscriptions`, `app_users`, `plan_features`, `usage_limits` などをテキスト ID 前提で再設計。
   - Shintairiku 社の `@shintairiku.jp` ドメインは常時アクティブ扱いとするため、例外テーブルや RLS の特別ポリシーを用意。
5. **アプリ実装のポイント**
   - SSR/CSR 双方で課金状態を判断できる Billing サービス層を作成。
   - Clerk Metadata を活用し、プラン情報や seat 数をフロントで即時参照。
   - Stripe Customer/Subscription metadata から Supabase へ同期し、異常終了時にもリトライできるよう Cloud Run 側で例外処理と監査ログを整備。

以下、上記を実現するための設計・実装手順を詳細に記載する。

## 要件ハイライト

- **ID & Profile**: Clerk を単一の ID プロバイダとし、`app_users` テーブルと metadata 同期でプロフィールを一元管理する。Supabase Auth 由来の `public.users` 依存は撤廃。
- **プラン設計**: 個人／チームの両プランを Stripe Product/Price で管理し、Seat 数や機能フラグは DB のマスターテーブルで定義。未確定の制限にも対応できる拡張性を確保。
- **Seat 課金と招待**: Stripe Checkout の quantity を seat 数として扱い、Clerk Organizations のメンバー数と比較して超過招待を防止。
- **例外ドメイン対応**: `@shintairiku.jp` ドメインは常時アクティブ扱いとし、課金状態や機能制限で優遇する例外パスを Supabase / アプリ双方に実装。
- **堅牢な同期パイプライン**: Vercel からは Checkout/Portal を生成、Google Cloud Run で Webhook を処理し冪等性テーブルへ記録。失敗時は再実行できるよう監査ログとリトライ方針を整備。
- **設定 UI の整備**: `frontend/src/app/(tools)/settings/billing` と `/members` を中心に、課金情報や seat 管理・招待フローを即時反映する UI を実装する。

---

## アーキテクチャ全体像

```
Clerk (Auth & Organizations) ─┐                         ┌──> Supabase (Postgres + RLS)
                               │                         │
User <─> Next.js App Router (Edge/API) ──> Cloud Run API │
                               │                         │
                               └──> Stripe (Checkout/Portal/Webhooks)
```

1. **Clerk**: 個人の認証に加えて、Clerk Organizations を有効化しチーム管理（招待・座席管理）を行う。Clerk Webhook で Supabase の `app_users`・`organization_members` を同期する。
2. **Stripe**: プラン（個人/チーム）と価格（seat 数・プランごとの機能上限）を管理。Checkout/Customer Portal を Next.js の Route Handler（Edge でなく Node runtime）から発行し、Webhook は Cloud Run 側で処理。
3. **Supabase**: 料金プランに応じた利用制限を判定するための `subscriptions`, `organization_subscriptions`, `usage_limits` 等を保持。RLS で個人・組織双方のアクセス制御を厳格化。
4. **Cloud Run Backend**: Stripe Webhook 処理や重いバッチ、記事生成のようなロングタスクを担当。Supabaseサービスロールキーを用い、Stripe イベントの反映を確実に行う。
5. **Vercel Frontend**: Next.js の App Router を使用し、Clerk のセッションを元に SSR/CSR 双方で課金状態を判定。Route Handler で Stripe Checkout の URL を生成。

---

## 前提条件と環境設定

1. **依存パッケージ**
   - `@clerk/nextjs`, `@supabase/supabase-js`, `@supabase/ssr`
   - `stripe`, `@stripe/stripe-js`
   - `zod`, `date-fns`, `axios`（HTTP クライアント）など既存 stack

2. **環境変数**（`.env.local`）
   ```bash
   # Clerk
   NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_...
   CLERK_SECRET_KEY=sk_test_...
   CLERK_WEBHOOK_SECRET=whsec_...

   # Supabase
   NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co
   NEXT_PUBLIC_SUPABASE_ANON_KEY=...
   SUPABASE_SERVICE_ROLE=...

   # Stripe
   STRIPE_SECRET_KEY=sk_test_...
   STRIPE_PUBLISHABLE_KEY=pk_test_...
   NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_...
   STRIPE_WEBHOOK_SECRET=whsec_...
   ```

3. **Stripe ダッシュボード設定**
   - Product / Price を作成（`recurring` で月額・年額プランなど）。
   - Customer Portal を有効化し、`Billing` → `Customer portal` で設定。

---

## Supabase データモデル

### 0. 既存スキーマの現状確認

`shared/supabase/migrations` を精査した結果、課金まわりの主要テーブルは下記のとおり:

- `public.users` … Supabase Auth トリガーで作られるプロファイル。主キーは `id uuid`。
- `public.customers` … 主キー `id uuid references auth.users`、`stripe_customer_id text`。Clerk 導入を想定した `user_id text` カラムはまだ存在しない。
- `public.products` / `public.prices` … Stripe カタログ同期用。公開閲覧のみ許可。
- `public.subscriptions` … `user_id uuid references auth.users` に結び付いた個人サブスク。RLS で `auth.uid()` と一致する行のみ参照可。
- `public.organization_subscriptions` … チーム/組織課金用。`organization_id uuid references organizations`。

`20250605152628_fix_user_id_for_clerk.sql` では複数テーブルの `user_id` を text 化済みだが、`customers` と `subscriptions` は未移行のため、Clerk ユーザー ID (`user_...`) を直接格納するにはスキーマ修正が必要になる。

### 1. Clerk 互換化のためのスキーマ調整

`customers` / `subscriptions` は旧 Supabase Auth 依存の `uuid` ベース構造が残っているので、**Clerk ID（`user_xxx`）を主キーに扱う設計へリライトするマイグレーション**を新規に作成する。既存データがまだ無いとのことなので以下のステップで問題ない。

1. `customers` から `id uuid references auth.users` を廃止し、`clerk_user_id text primary key` + `stripe_customer_id text` のシンプルなマッピングに変更。
2. `subscriptions` の `user_id uuid` も `clerk_user_id text not null references customers(clerk_user_id)` に変更し、`created_at/current_period_end` などの日時カラムは Stripe 起点で upsert する。
3. `organization_subscriptions` も `organizations` の`owner_user_id` が `text` で扱えるよう、`organizations` テーブルを text 化し Cl erk ID を保持する `organization_owner_id text` にリネーム。必要に応じて `organizations.stripe_customer_id` を team 課金の Customer ID として利用。
4. RLS は `auth.uid()` → Clerk ID という前提で `current_setting('request.jwt.claims', true)::json->>'sub'` を使う方式に統一する。

> 重要: マイグレーションは `IF EXISTS` を活用し、まだ `organizations` が存在しないケースでも中断しないように記述する。Clerk 運用後に冪等性を保てるよう、`alter table ... drop constraint if exists` の順番にも注意する。

#### 新しい `customers` / `subscriptions` テーブル例

```sql
create table customers (
  clerk_user_id text primary key,
  stripe_customer_id text not null unique,
  created_at timestamptz default now()
);

create table subscriptions (
  id text primary key,
  clerk_user_id text not null references customers(clerk_user_id),
  status subscription_status not null,
  price_id text not null references prices(id),
  quantity integer not null default 1,
  current_period_start timestamptz,
  current_period_end timestamptz,
  cancel_at_period_end boolean default false,
  canceled_at timestamptz,
  metadata jsonb,
  updated_at timestamptz default now()
);

alter table customers enable row level security;
create policy "自分の customer レコードのみ参照可"
  on customers for select using (current_setting('request.jwt.claims', true)::json->>'sub' = clerk_user_id);

alter table subscriptions enable row level security;
create policy "自分の subscription のみ参照可"
  on subscriptions for select using (current_setting('request.jwt.claims', true)::json->>'sub' = clerk_user_id);
```

## Clerk / Supabase の ID 連携とプロフィール保持

### 1. Clerk Webhook
ファイル: `frontend/src/app/api/webhooks/clerk/route.ts`

```ts
import { headers } from 'next/headers';
import { Webhook } from 'svix';
import { createServerSupabaseClient } from '@/libs/supabase/server-client'; // service role 版
import { z } from 'zod';

const clerkSecret = process.env.CLERK_WEBHOOK_SECRET!;

export async function POST(req: Request) {
  const payload = await req.text();
  const { 'svix-signature': signature } = Object.fromEntries(headers());
  const event = new Webhook(clerkSecret).verify(payload, signature ?? '');

  if (event.type === 'user.created') {
    const schema = z.object({
      id: z.string(),
      email_addresses: z.array(z.object({ email_address: z.string().email() })),
      first_name: z.string().nullable(),
      last_name: z.string().nullable(),
    });
    const data = schema.parse(event.data);

    const supabase = createServerSupabaseClient({ admin: true });
    await supabase.from('app_users').upsert({
      clerk_user_id: data.id,
      email: data.email_addresses[0]?.email_address ?? null,
      first_name: data.first_name,
      last_name: data.last_name,
      profile_completed: false,
    });
  }

  return new Response('ok');
}
```

### 2. Clerk → Stripe Customer 対応

Clerk の `user.created` or `user.updated` Webhook で Stripe customer も作成し、Supabase の `customers` に保存。  
Stripe customer 作成は `backend` などサーバー側で実行（Next.js Route Handler でも可）。

```ts
import { stripeAdmin } from '@/libs/stripe/stripe-admin';

const { data: existingCustomer } = await supabase
  .from('customers')
  .select('stripe_customer_id')
  .eq('clerk_user_id', data.id)
  .maybeSingle();

if (!existingCustomer) {
  const customer = await stripeAdmin.customers.create({
    email: data.email_addresses[0]?.email_address,
    name: [data.first_name, data.last_name].filter(Boolean).join(' ') || undefined,
    metadata: { user_id: data.id },
  });

  await supabase.from('customers').insert({
    clerk_user_id: data.id,
    stripe_customer_id: customer.id,
  });
}
```

---

## サブスクリプション開始（Checkout）

### 1. Route Handler で Checkout Session を作成

- ファイル: `frontend/src/app/api/billing/create-checkout-session/route.ts`
- 要求: 認証済みユーザー限定 (`auth()` + Clerk の `requireAuth` 中間層)
- Next.js では Edge runtime ではなく Node runtime（`export const runtime = 'nodejs'`）を指定し、Stripe SDK を利用できるようにする。
- team プランの場合は `seatCount` を payload に含め、`line_items` の `quantity` に反映する。

```ts
export const runtime = 'nodejs';
export async function POST(req: Request) {
  const { userId, orgId } = auth();
  if (!userId) return new Response('Unauthorized', { status: 401 });

  const { priceId, seatCount = 1, successUrl, cancelUrl } = await req.json();
  const supabase = getSupabaseServerClient({ admin: true });

  const { data: customer } = await supabase
    .from('customers')
    .select('stripe_customer_id')
    .eq('clerk_user_id', userId)
    .single();

  // Team プランで組織が明示された場合は organizations.stripe_customer_id を利用
  const stripeCustomerId = orgId
    ? await resolveOrganizationCustomerId(supabase, orgId)
    : customer?.stripe_customer_id;

  const session = await stripeAdmin.checkout.sessions.create({
    mode: 'subscription',
    customer: stripeCustomerId,
    line_items: [{ price: priceId, quantity: seatCount }],
    success_url: successUrl,
    cancel_url: cancelUrl,
    subscription_data: {
      metadata: {
        user_id: userId,
        organization_id: orgId ?? '',
        seat_count: String(seatCount),
      },
    },
    allow_promotion_codes: true,
  });

  return Response.json({ url: session.url });
}
```

```ts
import { auth } from '@clerk/nextjs/server';
import { stripeAdmin } from '@/libs/stripe/stripe-admin';
import { getSupabaseServerClient } from '@/libs/supabase/server-client';

export async function POST(req: Request) {
  const { userId } = auth();
  if (!userId) return new Response('Unauthorized', { status: 401 });

  const supabase = getSupabaseServerClient({ admin: true });
  const { data: customer } = await supabase
    .from('customers')
    .select('stripe_customer_id')
    .eq('clerk_user_id', userId)
    .single();

  const { priceId, successUrl, cancelUrl } = await req.json();

  const session = await stripeAdmin.checkout.sessions.create({
    mode: 'subscription',
    customer: customer.stripe_customer_id,
    line_items: [{ price: priceId, quantity: 1 }],
    success_url: successUrl,
    cancel_url: cancelUrl,
    allow_promotion_codes: true,
  });

  return Response.json({ url: session.url });
}
```

### 2. フロントエンドの呼び出し

`frontend/src/features/pricing/components/pricing-section.tsx` などの CTA ボタンから `fetch('/api/billing/create-checkout-session', …)` → 取得した URL にリダイレクト。  
Clerk の `SignedOut` ブロックではサインアップ誘導。

---

## Customer Portal（プラン変更・解約）

Route Handler: `frontend/src/app/api/billing/create-portal-session/route.ts`

```ts
const portalSession = await stripeAdmin.billingPortal.sessions.create({
  customer: customer.stripe_customer_id,
  return_url: new URL('/dashboard/billing', req.url).toString(),
});

return Response.json({ url: portalSession.url });
```

フロントエンドでは `useMutation` などで叩き、取得した URL へ遷移。`orgId` を保持している場合は team portal を開くようにする。

---

## Stripe Webhook で Supabase を同期

Route Handler: `frontend/src/app/api/webhooks/stripe/route.ts`

```ts
/**
 * Google Cloud Run 上の Fastify/Express ハンドラで Stripe Webhook を受ける想定。
 * Supabase Service Role を使用し、冪等性を保証する。
 */
import Stripe from 'stripe';
import { createClient } from '@supabase/supabase-js';

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!, { apiVersion: '2025-03-31.basil' });
const supabase = createClient(process.env.SUPABASE_URL!, process.env.SUPABASE_SERVICE_ROLE!);

const relevantEvents = new Set([
  'checkout.session.completed',
  'customer.subscription.created',
  'customer.subscription.updated',
  'customer.subscription.deleted',
  'invoice.payment_succeeded',
  'invoice.payment_failed',
]);

export const stripeWebhookHandler = async (req: express.Request, res: express.Response) => {
  const payload = req.rawBody; // Cloud Run + Fastify: raw body を保持
  const signature = req.headers['stripe-signature'];

  let event: Stripe.Event;
  try {
    event = stripe.webhooks.constructEvent(payload, signature as string, process.env.STRIPE_WEBHOOK_SECRET!);
  } catch (err) {
    res.status(400).send(`Webhook Error: ${(err as Error).message}`);
    return;
  }

  if (!relevantEvents.has(event.type)) {
    res.status(200).send('ignored');
    return;
  }

  // Stripe Event ID で冪等性チェック
  const alreadyProcessed = await supabase
    .from('stripe_events')
    .select('id')
    .eq('id', event.id)
    .maybeSingle();

  if (alreadyProcessed.data) {
    res.status(200).send('already processed');
    return;
  }

  try {
    switch (event.type) {
      case 'checkout.session.completed': {
        const session = event.data.object as Stripe.Checkout.Session;
        await handleCheckoutSessionCompleted(session);
        break;
      }
      case 'customer.subscription.created':
      case 'customer.subscription.updated':
      case 'customer.subscription.deleted': {
        const subscription = event.data.object as Stripe.Subscription;
        await upsertSubscriptionFromStripe(subscription);
        break;
      }
      case 'invoice.payment_failed': {
        const invoice = event.data.object as Stripe.Invoice;
        await markInvoiceFailed(invoice);
        break;
      }
    }

    await supabase.from('stripe_events').insert({ id: event.id, type: event.type, payload: event });
    res.status(200).send('ok');
  } catch (err) {
    res.status(500).send(`Webhook handling failed: ${(err as Error).message}`);
  }
};
```

- `lookupUserId` は `customers` テーブルから `stripe_customer_id` → `user_id` を解決するユーティリティを実装。
- Supabase の upsert では `onConflict: 'id'` を使用。
- 日時は Unix 秒を `new Date(unix * 1000)` に変換。

---

## アプリ内の課金状態判定と機能制限

1. Supabase から `subscriptions`（個人）と `organization_subscriptions`（チーム）を読み取り、`status in ('active','trialing')` かつ `current_period_end > now()` を満たすレコードを検索するサービス関数を `shared/billing` に用意。
2. Clerk の `auth()` で取得した `userId` / `orgId` に応じて、個人用・組織用のどちらを評価するかを決定する。Team プランの場合は `organization_subscriptions` の seat 数から、Clerk Organization の `maxAllowedMemberships` を更新し、追加招待のガードを行う。
3. Next.js では `Server Components` 内で Supabase SSR クライアント（`@supabase/ssr`）を使って課金状態を取得し、Context で配布。クライアントサイドでは `/api/billing/status` を叩き、React Query/SWR でキャッシュする。
4. プランごとの機能制限は `plan_features` や `usage_limits` を参照するサービス関数を経由し、UI 表示／API レート制限の両方で活用する。

ポリシー例:
```sql
create function public.has_active_subscription() returns boolean as $$
  select exists (
    select 1
    from subscriptions
    where clerk_user_id = current_setting('request.jwt.claims', true)::json->>'sub'
      and status in ('active', 'trialing')
      and current_period_end > now()
  );
$$ language sql stable;

create function public.organization_has_active_subscription(org_id uuid) returns boolean as $$
  select exists (
    select 1
    from organization_subscriptions
    where organization_id = org_id
      and status in ('active', 'trialing')
      and current_period_end > now()
  );
$$ language sql stable;
```
これらの関数をビューや RLS 条件に組み込むことで、課金状態と連動した機能制御が実現できる。

### フロントエンド設定画面の実装

- **メンバー管理 UI**: `frontend/src/app/(tools)/settings/members/page.tsx`（`http://localhost:3000/settings/members`）に存在するプレースホルダーを実装し、Clerk Organizations API と Supabase の `organization_members` を組み合わせて以下を提供する。
  1. seat 残量の表示（`organization_subscriptions.quantity` と Cl erk membership 数を比較）。
  2. メンバー招待（メール入力→Clerk `createOrganizationInvitation`→Supabase `organization_invites`）。
  3. ロール変更（owner/admin/member）および削除。RLS を満たすユーザーのみ操作可能にする。
- **請求設定 UI**: `frontend/src/app/(tools)/settings/billing/page.tsx`（`http://localhost:3000/settings/billing`）では、上記 API を呼んで以下を表示・操作する。
  1. 現在のプランと次回請求日（Supabase `subscriptions` / `organization_subscriptions` から取得）。
  2. Stripe Customer Portal への遷移ボタン（`POST /api/billing/create-portal-session`）。
  3. 請求履歴一覧（Stripe Invoices API → Supabase キャッシュ、または直接 Stripe → UI）。
  4. Shintairiku ドメインユーザーの場合は「社内利用につき無課金」バッジを表示し、課金関連 UI を read-only にする。
- UI レイヤーでは課金状態サービスを hooks (`useBilling`, `useSeats`) として切り出し、Server Component で事前フェッチしたデータを props で渡す構成を推奨。

---

## Clerk メタデータとの同期（オプション）

Stripe customer ID や現在のプラン名を Clerk 側の `publicMetadata` に保存しておくと、フロントエンドだけで即時反映（`useUser().publicMetadata`) が可能。  
Webhook で `clerkClient.users.updateUserMetadata(userId, { publicMetadata: { stripeSubscriptionStatus: subscription.status } })` のように同期する。

---

## テスト戦略

1. **ローカル開発**  
   - `stripe listen --forward-to localhost:3000/api/webhooks/stripe`  
   - Clerk のローカルキー（`CLERK_SECRET_KEY`）を使い、`clerk dev` CLI でイベントを受ける。
2. **E2E テスト**  
   - Playwright でサインアップ → Checkout → Dashboard gating を自動確認。
3. **フォールバック動作**  
   - 失敗した決済 (`invoice.payment_failed`) の Webhook を処理し、`status` を `past_due` に落とす。
4. **アカウント削除**  
   - Clerk の `user.deleted` イベントで Stripe customer をアーカイブし、Supabase のレコードも論理削除する。

---

## 今後の拡張ポイント

- **Usageベース課金**: `usage_records` テーブルと Stripe Metered Billing を組み合わせる。Cloud Run バッチでメーターリングを送信。
- **Team/Workspace 課金**: Clerk Organizations をフル活用し、Supabase の `organizations`, `organization_members`, `organization_subscriptions` と同期。
- **Invoices/Receipts**: Stripe の Hosted Invoice Page URL を Supabase に保存し、顧客向けメールに添付。また管理者用 Slack 通知も追加。
- **Webhook 冪等性管理**: Stripe event `id` を Supabase (`stripe_events` table) に記録し、再送時にも二重処理を防ぐ。
- **@shintairiku.jp ドメイン特権**: Supabase に `company_domain_whitelist` テーブルを作成し、対象ユーザーは常にアクティブ扱いにする。Webhook で `status` が `canceled` になっても上書きしないようガード。

---

## 参考リンク

- [Clerk Webhooks](https://clerk.com/docs/reference/webhooks)  
- [Stripe Subscription Quickstart](https://stripe.com/docs/billing/subscriptions/quickstart)  
- [Supabase Row Level Security](https://supabase.com/docs/guides/auth/row-level-security)  
- 既存ドキュメント: `docs/integration/stripe_payment_subscription.md`, `docs/frontend/` 配下のガイド

---

以上の手順をもとに、Clerk で認証されたユーザーに対して Stripe の決済を実行し、Supabase を単一の信頼できるソースとして課金状態を管理することで、SaaS としてのサブスクリプション体験を実現する。実装時は、Webhook の冪等性・Supabase の RLS 設計・Clerk セッションのバリデーションを徹底し、監査ログ（Stripe Dashboard, Supabase Logs）も活用すること。 
