/**
 * Stripe Webhook ハンドラー
 *
 * POST /api/subscription/webhook
 *
 * Stripeからのイベントを受信し、サブスクリプション状態を更新する
 * 個人サブスク（user_subscriptions）と組織サブスク（organization_subscriptions）の両方に対応
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

const ADDON_PRICE_ID = process.env.STRIPE_PRICE_ADDON_ARTICLES || '';

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

// ============================================
// ヘルパー: metadata から organization_id を取得
// ============================================
function getOrgIdFromMetadata(metadata: Record<string, string> | null | undefined): string | undefined {
  return metadata?.organization_id || undefined;
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

// ============================================
// plan_tier_id 解決: Stripe Price ID → plan_tiers.stripe_price_id で逆引き
// ============================================
async function resolvePlanTierId(
  supabase: typeof supabaseAdminClient,
  subscription: Stripe.Subscription,
): Promise<string> {
  try {
    // base item (= アドオンでないアイテム) の price.id を取得
    const baseItem = subscription.items?.data?.find(
      (item) => item.price?.id !== ADDON_PRICE_ID
    );
    const priceId = baseItem?.price?.id;

    if (priceId) {
      // plan_tiers.stripe_price_id で逆引き
      // Note: plan_tiers は型生成前のため any キャストを使用
      const { data: tier } = await (supabase as any)
        .from('plan_tiers')
        .select('id')
        .eq('stripe_price_id', priceId)
        .maybeSingle();
      if (tier?.id) return tier.id;
    }
  } catch (error) {
    console.error('Error resolving plan tier ID:', error);
  }

  return 'default'; // フォールバック
}

// ============================================
// ステータスマッピング
// ============================================
function mapStripeStatus(stripeStatus: Stripe.Subscription.Status): 'active' | 'past_due' | 'canceled' | 'expired' | 'none' {
  switch (stripeStatus) {
    case 'active':
    case 'trialing':
      return 'active';
    case 'past_due':
      return 'past_due';
    case 'canceled':
      return 'canceled';
    case 'unpaid':
    case 'incomplete_expired':
      return 'expired';
    default:
      return 'none';
  }
}

// ============================================
// チェックアウト完了
// ============================================
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
  const organizationId = getOrgIdFromMetadata(session.metadata as Record<string, string>);

  if (organizationId) {
    // ============ 組織サブスク ============
    // organizations テーブルに stripe_customer_id を保存
    await supabase
      .from('organizations')
      .update({ stripe_customer_id: customerId })
      .eq('id', organizationId);

    // organization_subscriptions に upsert
    await supabase.from('organization_subscriptions').upsert(
      {
        id: subscriptionId,
        organization_id: organizationId,
        status: 'active',
        metadata: session.metadata ? JSON.parse(JSON.stringify(session.metadata)) : null,
      },
      { onConflict: 'id' }
    );

    // 組織に billing_user_id を設定（課金ユーザーの追跡）
    await supabase
      .from('organizations')
      .update({ billing_user_id: userId, stripe_customer_id: customerId })
      .eq('id', organizationId);

    console.log(`Org checkout completed: org=${organizationId}, sub=${subscriptionId}`);
  } else {
    // ============ 個人サブスク（従来通り） ============
    await supabase.from('user_subscriptions').upsert(
      {
        user_id: userId,
        stripe_customer_id: customerId,
        stripe_subscription_id: subscriptionId,
        status: 'active',
        email: session.customer_email || null,
      },
      { onConflict: 'user_id' }
    );

    console.log(`Checkout completed for user ${userId}`);
  }

  // 無料トライアル grant のステータスを active に更新
  const freeTrialGrantId = session.metadata?.free_trial_grant_id;
  if (freeTrialGrantId) {
    try {
      await (supabase as any)
        .from('free_trial_grants')
        .update({ status: 'active', used_at: new Date().toISOString() })
        .eq('id', freeTrialGrantId);
      console.log(`Free trial grant ${freeTrialGrantId} activated for user ${userId}`);
    } catch (err) {
      console.warn('Failed to update free trial grant status:', err);
    }
  }
}

// ============================================
// サブスクリプション変更（作成/更新）
// ============================================
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
  const userStatus = mapStripeStatus(subscription.status);
  const organizationId = getOrgIdFromMetadata(subscription.metadata as Record<string, string>);

  // Stripe v18: current_period_end is on subscription items
  const currentPeriodEnd = subscription.items?.data?.[0]?.current_period_end;
  const currentPeriodStart = subscription.items?.data?.[0]?.current_period_start;
  const periodEndDate = currentPeriodEnd
    ? new Date(currentPeriodEnd * 1000).toISOString()
    : null;
  const periodStartDate = currentPeriodStart
    ? new Date(currentPeriodStart * 1000).toISOString()
    : null;

  // plan_tier_id を Stripe Price ID から解決
  const planTierId = await resolvePlanTierId(supabase, subscription);

  if (organizationId) {
    // ============ 組織サブスク ============
    // organization_subscriptions は subscription_status enum を使用（Stripe ネイティブ値）
    const orgStatus = subscription.status as 'active' | 'trialing' | 'canceled' | 'incomplete' | 'incomplete_expired' | 'past_due' | 'unpaid' | 'paused';
    const quantity = subscription.items?.data?.[0]?.quantity || 1;

    await supabase.from('organization_subscriptions').upsert(
      {
        id: subscription.id,
        organization_id: organizationId,
        status: orgStatus,
        quantity,
        price_id: subscription.items?.data?.[0]?.price?.id || null,
        cancel_at_period_end: subscription.cancel_at_period_end,
        current_period_start: periodStartDate,
        current_period_end: periodEndDate,
        metadata: subscription.metadata ? JSON.parse(JSON.stringify(subscription.metadata)) : null,
        canceled_at: subscription.canceled_at
          ? new Date(subscription.canceled_at * 1000).toISOString()
          : null,
        ended_at: subscription.ended_at
          ? new Date(subscription.ended_at * 1000).toISOString()
          : null,
      },
      { onConflict: 'id' }
    );

    // 同一サブスクが個人→組織に遷移した場合、user_subscriptions も更新
    // (upgrade-to-team で quantity を変更した場合、同じ subscription ID のまま organization_id が付与される)
    // Note: upgraded_to_org_id はマイグレーション適用後に有効。型生成前は型アサーションで対応。
    await supabase
      .from('user_subscriptions')
      .update({
        status: userStatus,
        current_period_end: periodEndDate,
        cancel_at_period_end: subscription.cancel_at_period_end,
        upgraded_to_org_id: organizationId,
        plan_tier_id: planTierId,
      } as Record<string, unknown>)
      .eq('user_id', userId);

    // アドオン数量を検出・更新
    const addonItem = subscription.items?.data?.find(
      (item) => item.price?.id === ADDON_PRICE_ID
    );
    const addonQuantity = addonItem?.quantity || 0;
    await supabase
      .from('organization_subscriptions')
      .update({ addon_quantity: addonQuantity } as Record<string, unknown>)
      .eq('id', subscription.id);

    // 使用量上限を再計算（レコードがなければ新規作成）
    await ensureUsageTracking(supabase, userId, organizationId, quantity, addonQuantity, planTierId, periodStartDate, periodEndDate);

    console.log(`Org subscription ${subscription.id} updated: org=${organizationId}, status=${orgStatus}, qty=${quantity}, addon=${addonQuantity}, tier=${planTierId}`);
  } else {
    // ============ 個人サブスク（従来通り） ============
    // Note: plan_tier_id は型生成前のため any キャストを使用
    await (supabase as any).from('user_subscriptions').upsert(
      {
        user_id: userId,
        stripe_customer_id: customerId,
        stripe_subscription_id: subscription.id,
        status: userStatus,
        current_period_end: periodEndDate,
        cancel_at_period_end: subscription.cancel_at_period_end,
        plan_tier_id: planTierId,
      },
      { onConflict: 'user_id' }
    );

    // アドオン数量を検出し、user_subscriptions にも保存
    const addonItem = subscription.items?.data?.find(
      (item) => item.price?.id === ADDON_PRICE_ID
    );
    const addonQuantity = addonItem?.quantity || 0;
    await supabase
      .from('user_subscriptions')
      .update({ addon_quantity: addonQuantity } as Record<string, unknown>)
      .eq('user_id', userId);

    // 使用量上限を再計算（レコードがなければ新規作成）
    await ensureUsageTracking(supabase, userId, undefined, 1, addonQuantity, planTierId, periodStartDate, periodEndDate);

    console.log(`Subscription ${subscription.id} updated for user ${userId}: ${userStatus}, addon=${addonQuantity}, tier=${planTierId}`);
  }
}

// ============================================
// サブスクリプション削除
// ============================================
async function handleSubscriptionDeleted(
  supabase: typeof supabaseAdminClient,
  subscription: Stripe.Subscription
) {
  const userId = subscription.metadata?.user_id;
  if (!userId) {
    console.error('No user_id in subscription metadata');
    return;
  }

  const organizationId = getOrgIdFromMetadata(subscription.metadata as Record<string, string>);

  if (organizationId) {
    // ============ 組織サブスク ============
    // subscription_status enum には 'expired' がないので 'canceled' を使用
    await supabase
      .from('organization_subscriptions')
      .update({
        status: 'canceled' as const,
        ended_at: new Date().toISOString(),
      })
      .eq('id', subscription.id);

    console.log(`Org subscription deleted: org=${organizationId}`);
  } else {
    // ============ 個人サブスク（従来通り） ============
    await supabase
      .from('user_subscriptions')
      .update({
        status: 'expired',
        stripe_subscription_id: null,
      })
      .eq('user_id', userId);

    console.log(`Subscription deleted for user ${userId}`);
  }
}

// ============================================
// 支払い成功
// ============================================
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

  const stripe = getStripe();
  const subscription = await stripe.subscriptions.retrieve(subscriptionId);
  const userId = subscription.metadata?.user_id;
  if (!userId) return;

  const organizationId = getOrgIdFromMetadata(subscription.metadata as Record<string, string>);

  // Stripe v18: current_period_end is on subscription items
  const currentPeriodEnd = subscription.items?.data?.[0]?.current_period_end;
  const periodEndDate = currentPeriodEnd
    ? new Date(currentPeriodEnd * 1000).toISOString()
    : null;

  if (organizationId) {
    // ============ 組織サブスク ============
    await supabase
      .from('organization_subscriptions')
      .update({
        status: 'active',
        current_period_end: periodEndDate,
      })
      .eq('id', subscriptionId);

    console.log(`Org payment succeeded: org=${organizationId}`);
  } else {
    // ============ 個人サブスク（従来通り） ============
    await supabase
      .from('user_subscriptions')
      .update({
        status: 'active',
        current_period_end: periodEndDate,
      })
      .eq('user_id', userId);

    console.log(`Payment succeeded for user ${userId}`);
  }

  // ============ 使用量リセット（請求サイクル更新時） ============
  const billingReason = (invoice as unknown as Record<string, unknown>).billing_reason as string | undefined;
  if (billingReason === 'subscription_cycle') {
    const currentPeriodStart = subscription.items?.data?.[0]?.current_period_start;
    const periodStartDate = currentPeriodStart
      ? new Date(currentPeriodStart * 1000).toISOString()
      : null;

    if (periodStartDate && periodEndDate) {
      await createUsageTrackingForNewPeriod(
        supabase,
        userId,
        organizationId || null,
        periodStartDate,
        periodEndDate,
        subscription,
      );
    }
  }
}

// ============================================
// 支払い失敗
// ============================================
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

  const stripe = getStripe();
  const subscription = await stripe.subscriptions.retrieve(subscriptionId);
  const userId = subscription.metadata?.user_id;
  if (!userId) return;

  const organizationId = getOrgIdFromMetadata(subscription.metadata as Record<string, string>);

  if (organizationId) {
    // ============ 組織サブスク ============
    await supabase
      .from('organization_subscriptions')
      .update({ status: 'past_due' })
      .eq('id', subscriptionId);

    console.log(`Org payment failed: org=${organizationId}`);
  } else {
    // ============ 個人サブスク（従来通り） ============
    await supabase
      .from('user_subscriptions')
      .update({ status: 'past_due' })
      .eq('user_id', userId);

    console.log(`Payment failed for user ${userId}`);
  }
}

// ============================================
// 使用量リセット: 新しい請求期間のトラッキングレコード作成
// ============================================
async function createUsageTrackingForNewPeriod(
  supabase: typeof supabaseAdminClient,
  userId: string,
  organizationId: string | null,
  periodStart: string,
  periodEnd: string,
  subscription: Stripe.Subscription,
) {
  try {
    // Stripe Price ID から plan_tier_id を解決
    const planTierId = await resolvePlanTierId(supabase, subscription);

    // plan_tiers から月間上限を取得
    // Note: plan_tiers は型生成前のため any キャストを使用
    const { data: tier } = await (supabase as any)
      .from('plan_tiers')
      .select('monthly_article_limit, addon_unit_amount')
      .eq('id', planTierId)
      .single();

    const monthlyLimit = tier?.monthly_article_limit || 30;
    const addonUnitAmount = tier?.addon_unit_amount || 20;

    // quantity と addon を算出
    const baseItem = subscription.items?.data?.find(
      (item) => item.price?.id !== ADDON_PRICE_ID
    );
    const addonItem = subscription.items?.data?.find(
      (item) => item.price?.id === ADDON_PRICE_ID
    );
    const quantity = baseItem?.quantity || 1;
    const addonQuantity = addonItem?.quantity || 0;

    const articlesLimit = monthlyLimit * quantity;
    const addonArticlesLimit = addonUnitAmount * addonQuantity;

    // Note: usage_tracking は型生成前のため any キャストを使用
    if (organizationId) {
      await (supabase as any).from('usage_tracking').upsert(
        {
          organization_id: organizationId,
          billing_period_start: periodStart,
          billing_period_end: periodEnd,
          articles_generated: 0,
          articles_limit: articlesLimit,
          addon_articles_limit: addonArticlesLimit,
          plan_tier_id: planTierId,
        },
        { onConflict: 'organization_id,billing_period_start' }
      );
    } else {
      await (supabase as any).from('usage_tracking').upsert(
        {
          user_id: userId,
          billing_period_start: periodStart,
          billing_period_end: periodEnd,
          articles_generated: 0,
          articles_limit: articlesLimit,
          addon_articles_limit: addonArticlesLimit,
          plan_tier_id: planTierId,
        },
        { onConflict: 'user_id,billing_period_start' }
      );
    }

    console.log(`Usage tracking created for new period: user=${userId}, org=${organizationId}, tier=${planTierId}, limit=${articlesLimit}+${addonArticlesLimit}`);
  } catch (error) {
    console.error('Error creating usage tracking for new period:', error);
  }
}

// ============================================
// 使用量トラッキング確保（存在しなければ作成、存在すれば上限を更新）
// ============================================
async function ensureUsageTracking(
  supabase: typeof supabaseAdminClient,
  userId: string,
  organizationId: string | undefined,
  quantity: number,
  addonQuantity: number,
  planTierId: string = 'default',
  periodStartDate: string | null = null,
  periodEndDate: string | null = null,
) {
  try {
    // Note: plan_tiers, usage_tracking は型生成前のため any キャストを使用
    const { data: tier } = await (supabase as any)
      .from('plan_tiers')
      .select('monthly_article_limit, addon_unit_amount')
      .eq('id', planTierId)
      .single();

    const monthlyLimit = tier?.monthly_article_limit || 30;
    const addonUnitAmount = tier?.addon_unit_amount || 20;

    const newLimit = monthlyLimit * quantity;
    const newAddonLimit = addonUnitAmount * addonQuantity;

    const now = new Date().toISOString();

    // まず既存レコードの更新を試みる
    if (organizationId) {
      const { data: existing } = await (supabase as any)
        .from('usage_tracking')
        .select('id')
        .eq('organization_id', organizationId)
        .lte('billing_period_start', now)
        .gte('billing_period_end', now)
        .maybeSingle();

      if (existing) {
        // 既存レコードがあれば上限のみ更新
        await (supabase as any)
          .from('usage_tracking')
          .update({
            articles_limit: newLimit,
            addon_articles_limit: newAddonLimit,
            plan_tier_id: planTierId,
          })
          .eq('id', existing.id);
      } else if (periodStartDate && periodEndDate) {
        // レコードがなければ新規作成
        await (supabase as any).from('usage_tracking').upsert(
          {
            organization_id: organizationId,
            billing_period_start: periodStartDate,
            billing_period_end: periodEndDate,
            articles_generated: 0,
            articles_limit: newLimit,
            addon_articles_limit: newAddonLimit,
            plan_tier_id: planTierId,
          },
          { onConflict: 'organization_id,billing_period_start' }
        );
        console.log(`Usage tracking created for org=${organizationId}, tier=${planTierId}, limit=${newLimit}+${newAddonLimit}`);
      }
    } else {
      const { data: existing } = await (supabase as any)
        .from('usage_tracking')
        .select('id')
        .eq('user_id', userId)
        .lte('billing_period_start', now)
        .gte('billing_period_end', now)
        .maybeSingle();

      if (existing) {
        // 既存レコードがあれば上限のみ更新
        await (supabase as any)
          .from('usage_tracking')
          .update({
            articles_limit: newLimit,
            addon_articles_limit: newAddonLimit,
            plan_tier_id: planTierId,
          })
          .eq('id', existing.id);
      } else if (periodStartDate && periodEndDate) {
        // レコードがなければ新規作成
        await (supabase as any).from('usage_tracking').upsert(
          {
            user_id: userId,
            billing_period_start: periodStartDate,
            billing_period_end: periodEndDate,
            articles_generated: 0,
            articles_limit: newLimit,
            addon_articles_limit: newAddonLimit,
            plan_tier_id: planTierId,
          },
          { onConflict: 'user_id,billing_period_start' }
        );
        console.log(`Usage tracking created for user=${userId}, tier=${planTierId}, limit=${newLimit}+${newAddonLimit}`);
      }
    }

    console.log(`Usage tracking ensured: user=${userId}, org=${organizationId}, limit=${newLimit}+${newAddonLimit}`);
  } catch (error) {
    console.error('Error ensuring usage tracking:', error);
  }
}
