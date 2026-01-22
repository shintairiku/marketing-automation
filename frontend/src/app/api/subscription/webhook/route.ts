/**
 * Stripe Webhook ハンドラー
 *
 * POST /api/subscription/webhook
 *
 * Stripeからのイベントを受信し、サブスクリプション状態を更新する
 *
 * 処理するイベント:
 * - checkout.session.completed: チェックアウト完了
 * - customer.subscription.created: サブスクリプション作成
 * - customer.subscription.updated: サブスクリプション更新
 * - customer.subscription.deleted: サブスクリプション削除
 * - invoice.payment_succeeded: 支払い成功
 * - invoice.payment_failed: 支払い失敗
 */

import { NextResponse } from 'next/server';
import Stripe from 'stripe';

import { getStripe } from '@/lib/subscription';
import { supabaseAdminClient } from '@/libs/supabase/supabase-admin';

// Webhook署名検証用のシークレット
const webhookSecret = process.env.STRIPE_WEBHOOK_SECRET;

// 処理対象のイベント
const relevantEvents = new Set([
  'checkout.session.completed',
  'customer.subscription.created',
  'customer.subscription.updated',
  'customer.subscription.deleted',
  'invoice.payment_succeeded',
  'invoice.payment_failed',
]);

export async function POST(request: Request) {
  const body = await request.text();
  const signature = request.headers.get('stripe-signature');

  if (!signature || !webhookSecret) {
    console.error('Missing signature or webhook secret');
    return NextResponse.json(
      { error: 'Missing signature' },
      { status: 400 }
    );
  }

  let event: Stripe.Event;

  try {
    const stripe = getStripe();
    event = stripe.webhooks.constructEvent(body, signature, webhookSecret);
  } catch (error) {
    console.error('Webhook signature verification failed:', error);
    return NextResponse.json(
      { error: 'Invalid signature' },
      { status: 400 }
    );
  }

  // 処理対象外のイベントはスキップ
  if (!relevantEvents.has(event.type)) {
    return NextResponse.json({ received: true });
  }

  const supabase = supabaseAdminClient;

  try {
    // イベントの重複チェック
    const { data: existingEvent } = await supabase
      .from('subscription_events')
      .select('id')
      .eq('stripe_event_id', event.id)
      .single();

    if (existingEvent) {
      console.log(`Event ${event.id} already processed, skipping`);
      return NextResponse.json({ received: true });
    }

    // イベント処理
    switch (event.type) {
      case 'checkout.session.completed': {
        const session = event.data.object as Stripe.Checkout.Session;
        await handleCheckoutCompleted(supabase, session);
        break;
      }

      case 'customer.subscription.created':
      case 'customer.subscription.updated': {
        const subscription = event.data.object as Stripe.Subscription;
        await handleSubscriptionChange(supabase, subscription);
        break;
      }

      case 'customer.subscription.deleted': {
        const subscription = event.data.object as Stripe.Subscription;
        await handleSubscriptionDeleted(supabase, subscription);
        break;
      }

      case 'invoice.payment_succeeded': {
        const invoice = event.data.object as Stripe.Invoice;
        await handlePaymentSucceeded(supabase, invoice);
        break;
      }

      case 'invoice.payment_failed': {
        const invoice = event.data.object as Stripe.Invoice;
        await handlePaymentFailed(supabase, invoice);
        break;
      }
    }

    // イベントログを記録
    await supabase.from('subscription_events').insert({
      user_id: getUserIdFromEvent(event),
      event_type: event.type,
      stripe_event_id: event.id,
      event_data: JSON.parse(JSON.stringify(event.data.object)),
    });

    return NextResponse.json({ received: true });
  } catch (error) {
    console.error(`Error processing event ${event.type}:`, error);
    return NextResponse.json(
      { error: 'Webhook processing failed' },
      { status: 500 }
    );
  }
}

// イベントからユーザーIDを取得
function getUserIdFromEvent(event: Stripe.Event): string {
  const data = event.data.object as unknown as Record<string, unknown>;

  // metadataからuser_idを取得
  if (data.metadata && typeof data.metadata === 'object') {
    const metadata = data.metadata as Record<string, string>;
    if (metadata.user_id) return metadata.user_id;
  }

  // subscription_dataからuser_idを取得
  if (data.subscription_data && typeof data.subscription_data === 'object') {
    const subscriptionData = data.subscription_data as Record<string, unknown>;
    if (subscriptionData.metadata && typeof subscriptionData.metadata === 'object') {
      const metadata = subscriptionData.metadata as Record<string, string>;
      if (metadata.user_id) return metadata.user_id;
    }
  }

  return 'unknown';
}

// チェックアウト完了時の処理
async function handleCheckoutCompleted(
  supabase: typeof supabaseAdminClient,
  session: Stripe.Checkout.Session
) {
  const userId = session.metadata?.user_id;
  if (!userId) {
    console.error('No user_id in checkout session metadata');
    return;
  }

  const customerId = session.customer as string;
  const subscriptionId = session.subscription as string;

  // 顧客IDとサブスクリプションIDを保存
  await supabase.from('user_subscriptions').upsert(
    {
      user_id: userId,
      stripe_customer_id: customerId,
      stripe_subscription_id: subscriptionId,
      status: 'active',
      email: session.customer_email || null,
    },
    {
      onConflict: 'user_id',
    }
  );

  console.log(`Checkout completed for user ${userId}`);
}

// サブスクリプション変更時の処理
async function handleSubscriptionChange(
  supabase: typeof supabaseAdminClient,
  subscription: Stripe.Subscription
) {
  const userId = subscription.metadata?.user_id;
  if (!userId) {
    console.error('No user_id in subscription metadata');
    return;
  }

  const customerId = subscription.customer as string;

  // ステータスをマッピング
  let status: 'active' | 'past_due' | 'canceled' | 'expired' | 'none';
  switch (subscription.status) {
    case 'active':
    case 'trialing':
      status = 'active';
      break;
    case 'past_due':
      status = 'past_due';
      break;
    case 'canceled':
      status = 'canceled';
      break;
    case 'unpaid':
    case 'incomplete_expired':
      status = 'expired';
      break;
    default:
      status = 'none';
  }

  // Stripe v18: current_period_end is on subscription items
  const currentPeriodEnd = subscription.items?.data?.[0]?.current_period_end;
  const periodEndDate = currentPeriodEnd
    ? new Date(currentPeriodEnd * 1000).toISOString()
    : null;

  await supabase.from('user_subscriptions').upsert(
    {
      user_id: userId,
      stripe_customer_id: customerId,
      stripe_subscription_id: subscription.id,
      status,
      current_period_end: periodEndDate,
      cancel_at_period_end: subscription.cancel_at_period_end,
    },
    {
      onConflict: 'user_id',
    }
  );

  console.log(`Subscription ${subscription.id} updated for user ${userId}: ${status}`);
}

// サブスクリプション削除時の処理
async function handleSubscriptionDeleted(
  supabase: typeof supabaseAdminClient,
  subscription: Stripe.Subscription
) {
  const userId = subscription.metadata?.user_id;
  if (!userId) {
    console.error('No user_id in subscription metadata');
    return;
  }

  await supabase
    .from('user_subscriptions')
    .update({
      status: 'expired',
      stripe_subscription_id: null,
    })
    .eq('user_id', userId);

  console.log(`Subscription deleted for user ${userId}`);
}

// 支払い成功時の処理
async function handlePaymentSucceeded(
  supabase: typeof supabaseAdminClient,
  invoice: Stripe.Invoice
) {
  // Stripe v18: subscription is at invoice.parent?.subscription_details?.subscription
  const subscriptionRef = invoice.parent?.subscription_details?.subscription;
  const subscriptionId = typeof subscriptionRef === 'string'
    ? subscriptionRef
    : subscriptionRef?.id;
  if (!subscriptionId) return;

  // サブスクリプションの詳細を取得してuser_idを確認
  const stripe = getStripe();
  const subscription = await stripe.subscriptions.retrieve(subscriptionId);
  const userId = subscription.metadata?.user_id;

  if (!userId) return;

  // Stripe v18: current_period_end is on subscription items
  const currentPeriodEnd = subscription.items?.data?.[0]?.current_period_end;
  const periodEndDate = currentPeriodEnd
    ? new Date(currentPeriodEnd * 1000).toISOString()
    : null;

  await supabase
    .from('user_subscriptions')
    .update({
      status: 'active',
      current_period_end: periodEndDate,
    })
    .eq('user_id', userId);

  console.log(`Payment succeeded for user ${userId}`);
}

// 支払い失敗時の処理
async function handlePaymentFailed(
  supabase: typeof supabaseAdminClient,
  invoice: Stripe.Invoice
) {
  // Stripe v18: subscription is at invoice.parent?.subscription_details?.subscription
  const subscriptionRef = invoice.parent?.subscription_details?.subscription;
  const subscriptionId = typeof subscriptionRef === 'string'
    ? subscriptionRef
    : subscriptionRef?.id;
  if (!subscriptionId) return;

  // サブスクリプションの詳細を取得してuser_idを確認
  const stripe = getStripe();
  const subscription = await stripe.subscriptions.retrieve(subscriptionId);
  const userId = subscription.metadata?.user_id;

  if (!userId) return;

  await supabase
    .from('user_subscriptions')
    .update({
      status: 'past_due',
    })
    .eq('user_id', userId);

  console.log(`Payment failed for user ${userId}`);
}
