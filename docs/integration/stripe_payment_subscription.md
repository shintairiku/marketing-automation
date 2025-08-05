# Stripe連携による決済・サブスクリプション機能の仕様

## 概要

このドキュメントでは、Stripeを用いた決済およびサブスクリプション管理機能の詳細な実装について解説します。商品・価格・顧客データのSupabaseとの同期、Webhookによるイベント処理、チェックアウトセッションの作成と決済フローの全体像を説明します。

## Stripe設定とクライアント初期化

### 1. Stripe管理クライアント

**ファイル**: `/frontend/src/libs/stripe/stripe-admin.ts`

```typescript
import Stripe from 'stripe';
import { getEnvVar } from '@/utils/get-env-var';

export const stripeAdmin = new Stripe(
  getEnvVar(process.env.STRIPE_SECRET_KEY, 'STRIPE_SECRET_KEY'), 
  {
    // https://github.com/stripe/stripe-node#configuration
    apiVersion: '2025-03-31.basil',
    // Register this as an official Stripe plugin.
    // https://stripe.com/docs/building-plugins#setappinfo
    appInfo: {
      name: 'UPDATE_THIS_WITH_YOUR_STRIPE_APP_NAME',
      version: '0.1.0',
    },
  }
);
```

**特徴**:
- サーバーサイド専用の管理者権限クライアント
- 最新APIバージョンの利用
- プラグイン情報の登録（Stripe側での識別用）

### 2. 環境変数設定

```bash
# Stripe設定
STRIPE_SECRET_KEY=sk_test_...または sk_live_...
STRIPE_PUBLISHABLE_KEY=pk_test_...または pk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Next.js環境変数
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_...または pk_live_...
```

### 3. パッケージ依存関係

**package.json抜粋**:
```json
{
  "dependencies": {
    "@stripe/stripe-js": "^2.4.0",
    "stripe": "^18.0.0"
  }
}
```

## データベーススキーマ

### 1. Stripe関連テーブル

#### 商品テーブル (products)

```sql
CREATE TABLE products (
  id TEXT PRIMARY KEY, -- Stripe Product ID
  active BOOLEAN,
  name TEXT,
  description TEXT,
  image TEXT,
  metadata JSONB
);
```

#### 価格テーブル (prices)

```sql
CREATE TYPE pricing_type AS ENUM ('one_time', 'recurring');
CREATE TYPE pricing_plan_interval AS ENUM ('day', 'week', 'month', 'year');

CREATE TABLE prices (
  id TEXT PRIMARY KEY, -- Stripe Price ID
  product_id TEXT REFERENCES products(id),
  active BOOLEAN,
  description TEXT,
  unit_amount BIGINT, -- 金額（最小通貨単位、例：100 = $1.00）
  currency TEXT,
  type pricing_type,
  interval pricing_plan_interval,
  interval_count INTEGER,
  trial_period_days INTEGER,
  metadata JSONB
);
```

#### 顧客テーブル (customers)

```sql
CREATE TABLE customers (
  id TEXT PRIMARY KEY, -- Clerk User ID
  stripe_customer_id TEXT UNIQUE -- Stripe Customer ID
);
```

#### サブスクリプションテーブル (subscriptions)

```sql
CREATE TABLE subscriptions (
  id TEXT PRIMARY KEY, -- Stripe Subscription ID
  user_id TEXT NOT NULL, -- Clerk User ID
  status TEXT NOT NULL,
  metadata JSONB,
  price_id TEXT REFERENCES prices(id),
  quantity INTEGER,
  cancel_at_period_end BOOLEAN,
  created TIMESTAMPTZ DEFAULT NOW(),
  current_period_start TIMESTAMPTZ,
  current_period_end TIMESTAMPTZ,
  ended_at TIMESTAMPTZ,
  canceled_at TIMESTAMPTZ,
  trial_start TIMESTAMPTZ,
  trial_end TIMESTAMPTZ
);
```

### 2. 型定義

**ファイル**: `/frontend/src/libs/supabase/types.ts`

```typescript
export type Database = {
  public: {
    Tables: {
      products: {
        Row: {
          id: string
          active: boolean | null
          name: string | null
          description: string | null
          image: string | null
          metadata: Json | null
        }
        Insert: {
          id: string
          active?: boolean | null
          name?: string | null
          description?: string | null
          image?: string | null
          metadata?: Json | null
        }
        Update: {
          id?: string
          active?: boolean | null
          name?: string | null
          description?: string | null
          image?: string | null
          metadata?: Json | null
        }
      }
      prices: {
        Row: {
          id: string
          product_id: string | null
          active: boolean | null
          description: string | null
          unit_amount: number | null
          currency: string | null
          type: Database["public"]["Enums"]["pricing_type"] | null
          interval: Database["public"]["Enums"]["pricing_plan_interval"] | null
          interval_count: number | null
          trial_period_days: number | null
          metadata: Json | null
        }
        Insert: {
          id: string
          product_id?: string | null
          active?: boolean | null
          description?: string | null
          unit_amount?: number | null
          currency?: string | null
          type?: Database["public"]["Enums"]["pricing_type"] | null
          interval?: Database["public"]["Enums"]["pricing_plan_interval"] | null
          interval_count?: number | null
          trial_period_days?: number | null
          metadata?: Json | null
        }
        Update: {
          id?: string
          product_id?: string | null
          active?: boolean | null
          description?: string | null
          unit_amount?: number | null
          currency?: string | null
          type?: Database["public"]["Enums"]["pricing_type"] | null
          interval?: Database["public"]["Enums"]["pricing_plan_interval"] | null
          interval_count?: number | null
          trial_period_days?: number | null
          metadata?: Json | null
        }
      }
      customers: {
        Row: {
          id: string
          stripe_customer_id: string | null
        }
        Insert: {
          id: string
          stripe_customer_id?: string | null
        }
        Update: {
          id?: string
          stripe_customer_id?: string | null
        }
      }
    }
    Enums: {
      pricing_plan_interval: "day" | "week" | "month" | "year"
      pricing_type: "one_time" | "recurring"
    }
  }
}
```

## Webhook実装

### 1. Webhookハンドラー

**ファイル**: `/frontend/src/app/api/webhooks/route.ts`

```typescript
import Stripe from 'stripe';

// Stripeの型定義を拡張
interface StripeSubscriptionWithPeriod extends Stripe.Subscription {
  current_period_start: number;
  current_period_end: number;
}

import { upsertUserSubscription } from '@/features/account/controllers/upsert-user-subscription';
import { upsertPrice } from '@/features/pricing/controllers/upsert-price';
import { upsertProduct } from '@/features/pricing/controllers/upsert-product';
import { stripeAdmin } from '@/libs/stripe/stripe-admin';
import { getEnvVar } from '@/utils/get-env-var';

const relevantEvents = new Set([
  'product.created',
  'product.updated',
  'price.created',
  'price.updated',
  'checkout.session.completed',
  'customer.subscription.created',
  'customer.subscription.updated',
  'customer.subscription.deleted',
]);

export async function POST(req: Request) {
  const body = await req.text();
  const sig = req.headers.get('stripe-signature') as string;
  const webhookSecret = getEnvVar(process.env.STRIPE_WEBHOOK_SECRET, 'STRIPE_WEBHOOK_SECRET');
  let event: Stripe.Event;

  try {
    if (!sig || !webhookSecret) return;
    event = stripeAdmin.webhooks.constructEvent(body, sig, webhookSecret);
  } catch (error) {
    return Response.json(`Webhook Error: ${(error as any).message}`, { status: 400 });
  }

  if (relevantEvents.has(event.type)) {
    try {
      switch (event.type) {
        case 'product.created':
        case 'product.updated':
          await upsertProduct(event.data.object as Stripe.Product);
          break;
        case 'price.created':
        case 'price.updated':
          await upsertPrice(event.data.object as Stripe.Price);
          break;
        case 'customer.subscription.created':
        case 'customer.subscription.updated':
        case 'customer.subscription.deleted':
          const subscription = event.data.object as unknown as StripeSubscriptionWithPeriod;
          console.log(`Processing subscription ${subscription.id} for customer ${subscription.customer}`);
          
          const subscriptionResult = await upsertUserSubscription({
            subscriptionId: subscription.id,
            customerId: subscription.customer as string,
            isCreateAction: false,
          });
          
          if (!subscriptionResult?.success) {
            console.error('Failed to upsert subscription:', subscriptionResult?.error);
            throw new Error(`Failed to upsert subscription: ${JSON.stringify(subscriptionResult?.error)}`);
          }
          break;
        case 'checkout.session.completed':
          const checkoutSession = event.data.object as Stripe.Checkout.Session;

          if (checkoutSession.mode === 'subscription') {
            const subscriptionId = checkoutSession.subscription;
            console.log(`Processing checkout session ${checkoutSession.id} with subscription ${subscriptionId}`);
            
            const checkoutResult = await upsertUserSubscription({
              subscriptionId: subscriptionId as string,
              customerId: checkoutSession.customer as string,
              isCreateAction: true,
            });
            
            if (!checkoutResult?.success) {
              console.error('Failed to upsert subscription from checkout:', checkoutResult?.error);
              throw new Error(`Failed to upsert subscription from checkout: ${JSON.stringify(checkoutResult?.error)}`);
            }
          }
          break;
        default:
          throw new Error('Unhandled relevant event!');
      }
    } catch (error) {
      console.error(error);
      return Response.json('Webhook handler failed. View your nextjs function logs.', {
        status: 400,
      });
    }
  }
  return Response.json({ received: true });
}
```

### 2. Webhookセキュリティ

#### 署名検証

```typescript
// Stripe署名検証のプロセス
try {
  if (!sig || !webhookSecret) {
    throw new Error('Missing signature or webhook secret');
  }
  
  // Stripeが提供する署名検証機能を使用
  event = stripeAdmin.webhooks.constructEvent(body, sig, webhookSecret);
} catch (error) {
  console.error('Webhook signature verification failed:', error);
  return Response.json(`Webhook Error: ${error.message}`, { status: 400 });
}
```

#### べき等性の確保

```typescript
// イベントの重複処理を防ぐため、Stripe Event IDでの処理済みチェック
const processedEvents = new Set<string>();

export async function POST(req: Request) {
  // ... 署名検証

  // 重複処理防止
  if (processedEvents.has(event.id)) {
    console.log(`Event ${event.id} already processed, skipping`);
    return Response.json({ received: true });
  }

  // ... イベント処理

  // 処理完了をマーク
  processedEvents.add(event.id);
  
  return Response.json({ received: true });
}
```

## データ同期コントローラー

### 1. 商品データの同期

**ファイル**: `/frontend/src/features/pricing/controllers/upsert-product.ts`

```typescript
import { createSupabaseServerClient } from '@/libs/supabase/supabase-server-client';
import Stripe from 'stripe';

export async function upsertProduct(product: Stripe.Product) {
  const supabase = await createSupabaseServerClient();
  
  try {
    const { error } = await supabase
      .from('products')
      .upsert({
        id: product.id,
        active: product.active,
        name: product.name,
        description: product.description,
        image: product.images?.[0] || null,
        metadata: product.metadata || {},
      }, {
        onConflict: 'id'
      });

    if (error) {
      console.error('Error upserting product:', error);
      throw error;
    }

    console.log(`Product ${product.id} upserted successfully`);
  } catch (error) {
    console.error('Failed to upsert product:', error);
    throw error;
  }
}
```

### 2. 価格データの同期

**ファイル**: `/frontend/src/features/pricing/controllers/upsert-price.ts`

```typescript
import { createSupabaseServerClient } from '@/libs/supabase/supabase-server-client';
import Stripe from 'stripe';

export async function upsertPrice(price: Stripe.Price) {
  const supabase = await createSupabaseServerClient();
  
  try {
    const { error } = await supabase
      .from('prices')
      .upsert({
        id: price.id,
        product_id: typeof price.product === 'string' ? price.product : price.product.id,
        active: price.active,
        description: price.nickname || null,
        unit_amount: price.unit_amount,
        currency: price.currency,
        type: price.type as 'one_time' | 'recurring',
        interval: price.recurring?.interval as 'day' | 'week' | 'month' | 'year' || null,
        interval_count: price.recurring?.interval_count || null,
        trial_period_days: price.recurring?.trial_period_days || null,
        metadata: price.metadata || {},
      }, {
        onConflict: 'id'
      });

    if (error) {
      console.error('Error upserting price:', error);
      throw error;
    }

    console.log(`Price ${price.id} upserted successfully`);
  } catch (error) {
    console.error('Failed to upsert price:', error);
    throw error;
  }
}
```

### 3. サブスクリプションデータの同期

**ファイル**: `/frontend/src/features/account/controllers/upsert-user-subscription.ts`

```typescript
import { createSupabaseServerClient } from '@/libs/supabase/supabase-server-client';
import { stripeAdmin } from '@/libs/stripe/stripe-admin';

interface UpsertUserSubscriptionParams {
  subscriptionId: string;
  customerId: string;
  isCreateAction: boolean;
}

export async function upsertUserSubscription({
  subscriptionId,
  customerId,
  isCreateAction
}: UpsertUserSubscriptionParams) {
  const supabase = await createSupabaseServerClient();
  
  try {
    console.log(`Upserting subscription ${subscriptionId} for customer ${customerId}`);
    
    // 1. Stripeからサブスクリプション詳細を取得
    const subscription = await stripeAdmin.subscriptions.retrieve(subscriptionId, {
      expand: ['items.data.price']
    });
    
    console.log(`Retrieved subscription:`, {
      id: subscription.id,
      status: subscription.status,
      customerId: subscription.customer,
      priceId: subscription.items.data[0]?.price?.id
    });

    // 2. Stripe顧客IDからClerk User IDを取得
    const { data: customer, error: customerError } = await supabase
      .from('customers')
      .select('id')
      .eq('stripe_customer_id', customerId)
      .single();

    if (customerError || !customer) {
      console.error('Customer not found:', { customerId, error: customerError });
      
      // 顧客が見つからない場合、Stripeから顧客情報を取得してClerk User IDを特定
      const stripeCustomer = await stripeAdmin.customers.retrieve(customerId);
      
      if (stripeCustomer.deleted) {
        throw new Error(`Customer ${customerId} has been deleted`);
      }
      
      const clerkUserId = stripeCustomer.metadata?.clerk_user_id;
      if (!clerkUserId) {
        throw new Error(`No Clerk User ID found for customer ${customerId}`);
      }
      
      // 顧客レコードを作成
      const { error: insertError } = await supabase
        .from('customers')
        .insert({
          id: clerkUserId,
          stripe_customer_id: customerId
        });
      
      if (insertError) {
        console.error('Failed to create customer record:', insertError);
        throw insertError;
      }
      
      console.log(`Created customer record for ${clerkUserId}`);
    }

    const userId = customer?.id || stripeCustomer.metadata?.clerk_user_id;
    
    // 3. サブスクリプションデータをupsert
    const { error: subscriptionError } = await supabase
      .from('subscriptions')
      .upsert({
        id: subscription.id,
        user_id: userId,
        status: subscription.status,
        metadata: subscription.metadata || {},
        price_id: subscription.items.data[0]?.price?.id || null,
        quantity: subscription.items.data[0]?.quantity || 1,
        cancel_at_period_end: subscription.cancel_at_period_end,
        created: new Date(subscription.created * 1000).toISOString(),
        current_period_start: new Date(subscription.current_period_start * 1000).toISOString(),
        current_period_end: new Date(subscription.current_period_end * 1000).toISOString(),
        ended_at: subscription.ended_at ? new Date(subscription.ended_at * 1000).toISOString() : null,
        canceled_at: subscription.canceled_at ? new Date(subscription.canceled_at * 1000).toISOString() : null,
        trial_start: subscription.trial_start ? new Date(subscription.trial_start * 1000).toISOString() : null,
        trial_end: subscription.trial_end ? new Date(subscription.trial_end * 1000).toISOString() : null,
      }, {
        onConflict: 'id'
      });

    if (subscriptionError) {
      console.error('Error upserting subscription:', subscriptionError);
      throw subscriptionError;
    }

    console.log(`Subscription ${subscription.id} upserted successfully`);
    
    return { success: true };
  } catch (error) {
    console.error('Failed to upsert user subscription:', error);
    return { 
      success: false, 
      error: error instanceof Error ? error.message : 'Unknown error' 
    };
  }
}
```

### 4. 顧客データの管理

**ファイル**: `/frontend/src/features/account/controllers/get-or-create-customer.ts`

```typescript
import { createSupabaseServerClient } from '@/libs/supabase/supabase-server-client';
import { stripeAdmin } from '@/libs/stripe/stripe-admin';

export async function getOrCreateCustomer(
  userId: string,
  email: string,
  name?: string
): Promise<string> {
  const supabase = await createSupabaseServerClient();
  
  try {
    // 1. 既存の顧客レコードを確認
    const { data: existingCustomer, error: fetchError } = await supabase
      .from('customers')
      .select('stripe_customer_id')
      .eq('id', userId)
      .single();

    if (existingCustomer?.stripe_customer_id) {
      // 既存のStripe顧客IDを返す
      return existingCustomer.stripe_customer_id;
    }

    // 2. 新しいStripe顧客を作成
    const stripeCustomer = await stripeAdmin.customers.create({
      email,
      name,
      metadata: {
        clerk_user_id: userId,
      },
    });

    // 3. 顧客レコードをデータベースに保存
    const { error: insertError } = await supabase
      .from('customers')
      .insert({
        id: userId,
        stripe_customer_id: stripeCustomer.id,
      });

    if (insertError) {
      console.error('Failed to save customer record:', insertError);
      throw insertError;
    }

    console.log(`Created new customer ${stripeCustomer.id} for user ${userId}`);
    return stripeCustomer.id;
  } catch (error) {
    console.error('Failed to get or create customer:', error);
    throw error;
  }
}
```

## 決済フロー実装

### 1. チェックアウトセッション作成

**ファイル**: `/frontend/src/features/pricing/actions/create-checkout-action.ts`

```typescript
import { stripeAdmin } from '@/libs/stripe/stripe-admin';
import { getOrCreateCustomer } from '@/features/account/controllers/get-or-create-customer';
import { getEnvVar } from '@/utils/get-env-var';

interface CreateCheckoutActionParams {
  priceId: string;
  userId: string;
  userEmail: string;
  userName?: string;
  successUrl?: string;
  cancelUrl?: string;
}

export async function createCheckoutAction({
  priceId,
  userId,
  userEmail,
  userName,
  successUrl,
  cancelUrl
}: CreateCheckoutActionParams) {
  try {
    console.log('Creating checkout session:', {
      priceId,
      userId,
      userEmail,
      userName
    });

    // 1. Stripe顧客を取得または作成
    const customerId = await getOrCreateCustomer(userId, userEmail, userName);

    // 2. チェックアウトセッションを作成
    const session = await stripeAdmin.checkout.sessions.create({
      customer: customerId,
      payment_method_types: ['card'],
      line_items: [
        {
          price: priceId,
          quantity: 1,
        },
      ],
      mode: 'subscription',
      success_url: successUrl || `${getEnvVar(process.env.NEXT_PUBLIC_SITE_URL, 'NEXT_PUBLIC_SITE_URL')}/dashboard?session_id={CHECKOUT_SESSION_ID}`,
      cancel_url: cancelUrl || `${getEnvVar(process.env.NEXT_PUBLIC_SITE_URL, 'NEXT_PUBLIC_SITE_URL')}/pricing`,
      subscription_data: {
        metadata: {
          clerk_user_id: userId,
        },
      },
      metadata: {
        clerk_user_id: userId,
      },
      billing_address_collection: 'required',
      customer_update: {
        address: 'auto',
        name: 'auto',
      },
      automatic_tax: {
        enabled: true,
      },
      tax_id_collection: {
        enabled: true,
      },
    });

    console.log(`Created checkout session ${session.id} for customer ${customerId}`);

    return {
      success: true,
      sessionId: session.id,
      url: session.url,
    };
  } catch (error) {
    console.error('Failed to create checkout session:', error);
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error',
    };
  }
}
```

### 2. 料金プランコンポーネント

**ファイル**: `/frontend/src/features/pricing/components/price-card.tsx`

```typescript
import { useState } from 'react';
import { useUser } from '@clerk/nextjs';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { createCheckoutAction } from '@/features/pricing/actions/create-checkout-action';

interface PriceCardProps {
  price: {
    id: string;
    unit_amount: number;
    currency: string;
    interval?: string;
    interval_count?: number;
    product: {
      id: string;
      name: string;
      description: string;
      metadata: {
        features: string[];
        popular?: boolean;
        tier: string;
      };
    };
  };
}

export function PriceCard({ price }: PriceCardProps) {
  const { user } = useUser();
  const [isLoading, setIsLoading] = useState(false);

  const handleSubscribe = async () => {
    if (!user) return;

    setIsLoading(true);
    try {
      const result = await createCheckoutAction({
        priceId: price.id,
        userId: user.id,
        userEmail: user.primaryEmailAddress?.emailAddress || '',
        userName: user.fullName || user.firstName || '',
      });

      if (result.success && result.url) {
        window.location.href = result.url;
      } else {
        console.error('Failed to create checkout session:', result.error);
      }
    } catch (error) {
      console.error('Subscription error:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const formatPrice = (amount: number, currency: string) => {
    return new Intl.NumberFormat('ja-JP', {
      style: 'currency',
      currency: currency.toUpperCase(),
    }).format(amount / 100);
  };

  const formatInterval = (interval?: string, intervalCount?: number) => {
    if (!interval) return '';
    
    const count = intervalCount || 1;
    const unit = interval === 'month' ? '月' : interval === 'year' ? '年' : interval;
    
    return count === 1 ? `/${unit}` : `/${count}${unit}`;
  };

  return (
    <Card className={`relative ${price.product.metadata.popular ? 'border-primary' : ''}`}>
      {price.product.metadata.popular && (
        <Badge className="absolute -top-2 left-1/2 transform -translate-x-1/2 bg-primary">
          人気
        </Badge>
      )}
      
      <CardHeader>
        <CardTitle className="text-xl">
          {price.product.name}
        </CardTitle>
        <div className="text-3xl font-bold">
          {formatPrice(price.unit_amount, price.currency)}
          <span className="text-sm font-normal text-muted-foreground">
            {formatInterval(price.interval, price.interval_count)}
          </span>
        </div>
        <p className="text-muted-foreground">
          {price.product.description}
        </p>
      </CardHeader>
      
      <CardContent>
        <ul className="space-y-2 mb-6">
          {price.product.metadata.features.map((feature, index) => (
            <li key={index} className="flex items-center space-x-2">
              <svg className="h-4 w-4 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
              </svg>
              <span>{feature}</span>
            </li>
          ))}
        </ul>
        
        <Button 
          onClick={handleSubscribe}
          disabled={isLoading || !user}
          className="w-full"
          variant={price.product.metadata.popular ? 'default' : 'outline'}
        >
          {isLoading ? '処理中...' : '今すぐ始める'}
        </Button>
      </CardContent>
    </Card>
  );
}
```

### 3. 料金プランセクション

**ファイル**: `/frontend/src/features/pricing/components/pricing-section.tsx`

```typescript
import { useEffect, useState } from 'react';
import { getProducts } from '@/features/pricing/controllers/get-products';
import { PriceCard } from './price-card';

interface Product {
  id: string;
  name: string;
  description: string;
  metadata: any;
  prices: Array<{
    id: string;
    unit_amount: number;
    currency: string;
    interval?: string;
    interval_count?: number;
  }>;
}

export function PricingSection() {
  const [products, setProducts] = useState<Product[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchProducts = async () => {
      try {
        const data = await getProducts();
        setProducts(data);
      } catch (error) {
        console.error('Failed to fetch products:', error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchProducts();
  }, []);

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {[1, 2, 3].map((i) => (
          <div key={i} className="animate-pulse">
            <div className="bg-gray-200 rounded-lg h-96"></div>
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
      {products.map((product) =>
        product.prices.map((price) => (
          <PriceCard
            key={price.id}
            price={{
              ...price,
              product,
            }}
          />
        ))
      )}
    </div>
  );
}
```

## サブスクリプション管理

### 1. サブスクリプション状態の取得

**ファイル**: `/frontend/src/features/account/controllers/get-subscription.ts`

```typescript
import { createSupabaseServerClient } from '@/libs/supabase/supabase-server-client';

export async function getSubscription(userId: string) {
  const supabase = await createSupabaseServerClient();
  
  try {
    const { data: subscription, error } = await supabase
      .from('subscriptions')
      .select(`
        *,
        prices (
          *,
          products (*)
        )
      `)
      .eq('user_id', userId)
      .eq('status', 'active')
      .single();

    if (error && error.code !== 'PGRST116') {
      console.error('Error fetching subscription:', error);
      throw error;
    }

    return subscription;
  } catch (error) {
    console.error('Failed to get subscription:', error);
    throw error;
  }
}
```

### 2. サブスクリプション管理UI

```typescript
import { useEffect, useState } from 'react';
import { useUser } from '@clerk/nextjs';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { getSubscription } from '@/features/account/controllers/get-subscription';

export function SubscriptionManager() {
  const { user } = useUser();
  const [subscription, setSubscription] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchSubscription = async () => {
      if (!user?.id) return;

      try {
        const data = await getSubscription(user.id);
        setSubscription(data);
      } catch (error) {
        console.error('Failed to fetch subscription:', error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchSubscription();
  }, [user?.id]);

  const handleCancelSubscription = async () => {
    // キャンセル処理の実装
    console.log('Cancelling subscription...');
  };

  const handleUpdateSubscription = async () => {
    // プラン変更処理の実装
    console.log('Updating subscription...');
  };

  if (isLoading) {
    return <div>読み込み中...</div>;
  }

  if (!subscription) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>サブスクリプション</CardTitle>
        </CardHeader>
        <CardContent>
          <p>アクティブなサブスクリプションがありません。</p>
          <Button className="mt-4">
            プランを選択
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          現在のプラン
          <Badge variant={subscription.status === 'active' ? 'default' : 'secondary'}>
            {subscription.status}
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <div>
            <h3 className="font-semibold">{subscription.prices?.products?.name}</h3>
            <p className="text-muted-foreground">
              {subscription.prices?.products?.description}
            </p>
          </div>
          
          <div className="flex justify-between items-center">
            <span>料金:</span>
            <span className="font-semibold">
              ¥{(subscription.prices?.unit_amount / 100).toLocaleString()}
              /{subscription.prices?.interval}
            </span>
          </div>
          
          <div className="flex justify-between items-center">
            <span>次回請求日:</span>
            <span>{new Date(subscription.current_period_end).toLocaleDateString()}</span>
          </div>
          
          <div className="flex space-x-2">
            <Button variant="outline" onClick={handleUpdateSubscription}>
              プラン変更
            </Button>
            <Button variant="destructive" onClick={handleCancelSubscription}>
              キャンセル
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
```

## エラーハンドリングとログ

### 1. エラー処理の統一

```typescript
interface StripeError {
  type: string;
  code?: string;
  message: string;
  param?: string;
}

export function handleStripeError(error: StripeError) {
  console.error('Stripe error:', error);
  
  switch (error.type) {
    case 'card_error':
      return {
        success: false,
        message: 'カードエラーが発生しました。カード情報を確認してください。',
        code: error.code,
      };
    case 'invalid_request_error':
      return {
        success: false,
        message: 'リクエストに問題があります。しばらく待ってから再試行してください。',
      };
    case 'api_error':
      return {
        success: false,
        message: 'システムエラーが発生しました。サポートにお問い合わせください。',
      };
    default:
      return {
        success: false,
        message: '予期しないエラーが発生しました。',
      };
  }
}
```

### 2. ログとメトリクス

```typescript
// 決済関連のログ
export function logPaymentEvent(
  eventType: string,
  data: any,
  userId?: string
) {
  console.log(`[Payment] ${eventType}:`, {
    timestamp: new Date().toISOString(),
    userId,
    ...data,
  });
  
  // 外部ログサービスへの送信
  // Sentry、DataDog等への送信ロジック
}

// 使用例
await logPaymentEvent('checkout_session_created', {
  sessionId: session.id,
  priceId,
  customerId,
}, userId);
```

## セキュリティ考慮事項

### 1. 価格操作の防止

```typescript
// サーバーサイドでの価格検証
export async function validatePriceIntegrity(priceId: string) {
  const supabase = await createSupabaseServerClient();
  
  const { data: price, error } = await supabase
    .from('prices')
    .select('*')
    .eq('id', priceId)
    .eq('active', true)
    .single();

  if (error || !price) {
    throw new Error('Invalid or inactive price');
  }

  // Stripeから最新の価格情報を取得して比較
  const stripePrice = await stripeAdmin.prices.retrieve(priceId);
  
  if (price.unit_amount !== stripePrice.unit_amount) {
    throw new Error('Price mismatch detected');
  }

  return price;
}
```

### 2. 顧客データの保護

```typescript
// 顧客情報のマスキング
export function maskCustomerData(customer: any) {
  return {
    ...customer,
    email: customer.email ? customer.email.replace(/(.{2}).*(@.*)/, '$1***$2') : null,
    name: customer.name ? customer.name.replace(/(.{1}).*(.{1})/, '$1***$2') : null,
  };
}
```

## 結論

このStripe決済・サブスクリプションシステムにより、以下の機能を実現しています：

1. **包括的な決済処理**: チェックアウトからサブスクリプション管理まで
2. **データ整合性**: WebhookによるStripeとSupabaseの自動同期
3. **セキュリティ**: 署名検証と価格操作防止
4. **ユーザビリティ**: 直感的な料金プランとサブスクリプション管理UI
5. **監視可能性**: 詳細なログとエラーハンドリング
6. **スケーラビリティ**: 効率的なデータ構造と処理フロー

この設計により、信頼性が高く使いやすい決済システムを構築し、ビジネスの成長を支援します。