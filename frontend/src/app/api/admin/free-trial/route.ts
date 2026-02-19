/**
 * 管理者: 無料トライアル管理 API
 *
 * POST /api/admin/free-trial — トライアル付与 or 延長
 * DELETE /api/admin/free-trial — トライアル取り消し
 *
 * Stripe subscription の trial_end を使い、クレジットカード不要で
 * 指定ユーザーに無料アクセスを付与する。
 */

import { NextResponse } from 'next/server';
import Stripe from 'stripe';

import { getStripe, SUBSCRIPTION_PRICE_ID } from '@/lib/subscription';
import { supabaseAdminClient } from '@/libs/supabase/supabase-admin';
import { auth, clerkClient } from '@clerk/nextjs/server';

// 管理者メールドメイン
const ADMIN_DOMAIN = '@shintairiku.jp';

async function verifyAdmin(): Promise<{ adminUserId: string } | NextResponse> {
  const authData = await auth();
  const userId = authData.userId;
  if (!userId) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  const client = await clerkClient();
  const user = await client.users.getUser(userId);
  const email = user.emailAddresses?.[0]?.emailAddress;

  if (!email?.toLowerCase().endsWith(ADMIN_DOMAIN)) {
    return NextResponse.json({ error: 'Forbidden: admin only' }, { status: 403 });
  }

  return { adminUserId: userId };
}

// ============================================
// POST: トライアル付与 or 延長
// ============================================
export async function POST(request: Request) {
  const adminResult = await verifyAdmin();
  if (adminResult instanceof NextResponse) return adminResult;
  const { adminUserId } = adminResult;

  const body = await request.json();
  const { user_id, days, plan_tier_id } = body as {
    user_id: string;
    days: number;
    plan_tier_id?: string;
  };

  if (!user_id || !days || days < 1 || days > 730) {
    return NextResponse.json(
      { error: 'user_id と days (1-730) が必要です' },
      { status: 400 }
    );
  }

  const stripe = getStripe();
  const supabase = supabaseAdminClient;

  try {
    // 1. ユーザーのメールを取得
    const client = await clerkClient();
    const targetUser = await client.users.getUser(user_id);
    const userEmail = targetUser.emailAddresses?.[0]?.emailAddress;

    if (!userEmail) {
      return NextResponse.json(
        { error: 'ユーザーのメールアドレスが見つかりません' },
        { status: 400 }
      );
    }

    // 2. 既存の user_subscriptions を取得
    const { data: existingSub } = await supabase
      .from('user_subscriptions')
      .select('*')
      .eq('user_id', user_id)
      .maybeSingle();

    // 既にアクティブな有料サブスクがある場合はエラー
    if (existingSub?.status === 'active' && existingSub.stripe_subscription_id) {
      return NextResponse.json(
        { error: 'このユーザーは既にアクティブな有料サブスクリプションを持っています' },
        { status: 409 }
      );
    }

    // 3. 既存のトライアルサブスクがある場合は延長
    if (existingSub?.status === 'trialing' && existingSub.stripe_subscription_id) {
      const newTrialEnd = Math.floor(Date.now() / 1000) + days * 86400;

      const updatedSub = await stripe.subscriptions.update(
        existingSub.stripe_subscription_id,
        { trial_end: newTrialEnd }
      );

      const trialEndDate = new Date(newTrialEnd * 1000).toISOString();
      const periodEndDate = updatedSub.items?.data?.[0]?.current_period_end
        ? new Date(updatedSub.items.data[0].current_period_end * 1000).toISOString()
        : trialEndDate;

      await supabase.from('user_subscriptions').update({
        trial_end: trialEndDate,
        current_period_end: periodEndDate,
        trial_granted_by: adminUserId,
        trial_granted_at: new Date().toISOString(),
      } as Record<string, unknown>).eq('user_id', user_id);

      return NextResponse.json({
        success: true,
        message: `トライアルを延長しました（${days}日後まで）`,
        trial_end: trialEndDate,
        subscription_id: existingSub.stripe_subscription_id,
        action: 'extended',
      });
    }

    // 4. Stripe Customer を取得または作成
    let customerId = existingSub?.stripe_customer_id;

    if (!customerId) {
      // 既存の Stripe Customer を email で検索
      const existingCustomers = await stripe.customers.list({
        email: userEmail,
        limit: 1,
      });

      if (existingCustomers.data.length > 0) {
        customerId = existingCustomers.data[0].id;
      } else {
        // 新規作成（payment method 不要）
        const customer = await stripe.customers.create({
          email: userEmail,
          name: targetUser.firstName
            ? `${targetUser.firstName} ${targetUser.lastName || ''}`.trim()
            : undefined,
          metadata: {
            user_id,
            clerk_user_id: user_id,
          },
        });
        customerId = customer.id;
      }
    }

    // 5. Price ID を確認
    const priceId = SUBSCRIPTION_PRICE_ID;
    if (!priceId) {
      return NextResponse.json(
        { error: 'STRIPE_PRICE_ID が設定されていません' },
        { status: 500 }
      );
    }

    // 6. Stripe Subscription を作成（trial_end 指定、payment method 不要）
    const trialEnd = Math.floor(Date.now() / 1000) + days * 86400;

    const subscription = await stripe.subscriptions.create({
      customer: customerId,
      items: [{ price: priceId }],
      trial_end: trialEnd,
      trial_settings: {
        end_behavior: {
          missing_payment_method: 'cancel',
        },
      },
      payment_settings: {
        save_default_payment_method: 'on_subscription',
      },
      metadata: {
        user_id,
        granted_by: adminUserId,
        type: 'free_trial',
      },
    });

    // 7. DB を即座に更新（Webhook 到着を待たない）
    const trialEndDate = new Date(trialEnd * 1000).toISOString();
    const resolvedTierId = plan_tier_id || 'default';

    await supabase.from('user_subscriptions').upsert(
      {
        user_id,
        stripe_customer_id: customerId,
        stripe_subscription_id: subscription.id,
        status: 'trialing',
        current_period_end: trialEndDate,
        cancel_at_period_end: false,
        email: userEmail,
        trial_end: trialEndDate,
        trial_granted_by: adminUserId,
        trial_granted_at: new Date().toISOString(),
        plan_tier_id: resolvedTierId,
      } as Record<string, unknown>,
      { onConflict: 'user_id' }
    );

    // 8. usage_tracking レコードを作成
    const { data: tier } = await supabase
      .from('plan_tiers')
      .select('monthly_article_limit, addon_unit_amount')
      .eq('id', resolvedTierId)
      .maybeSingle();

    const monthlyLimit = tier?.monthly_article_limit || 30;
    const now = new Date().toISOString();

    await supabase.from('usage_tracking').upsert(
      {
        user_id,
        billing_period_start: now,
        billing_period_end: trialEndDate,
        articles_generated: 0,
        articles_limit: monthlyLimit,
        addon_articles_limit: 0,
        plan_tier_id: resolvedTierId,
      },
      { onConflict: 'user_id,billing_period_start' }
    );

    return NextResponse.json({
      success: true,
      message: `${days}日間の無料トライアルを付与しました`,
      trial_end: trialEndDate,
      subscription_id: subscription.id,
      customer_id: customerId,
      action: 'created',
    });
  } catch (error) {
    console.error('Error granting free trial:', error);
    const message = error instanceof Stripe.errors.StripeError
      ? error.message
      : 'トライアルの付与に失敗しました';
    return NextResponse.json({ error: message }, { status: 500 });
  }
}

// ============================================
// DELETE: トライアル取り消し
// ============================================
export async function DELETE(request: Request) {
  const adminResult = await verifyAdmin();
  if (adminResult instanceof NextResponse) return adminResult;

  const { searchParams } = new URL(request.url);
  const userId = searchParams.get('user_id');

  if (!userId) {
    return NextResponse.json(
      { error: 'user_id が必要です' },
      { status: 400 }
    );
  }

  const stripe = getStripe();
  const supabase = supabaseAdminClient;

  try {
    const { data: sub } = await supabase
      .from('user_subscriptions')
      .select('*')
      .eq('user_id', userId)
      .maybeSingle();

    if (!sub || sub.status !== 'trialing' || !sub.stripe_subscription_id) {
      return NextResponse.json(
        { error: 'アクティブなトライアルが見つかりません' },
        { status: 404 }
      );
    }

    // Stripe サブスクリプションを即時キャンセル
    await stripe.subscriptions.cancel(sub.stripe_subscription_id);

    // DB を更新
    await supabase.from('user_subscriptions').update({
      status: 'expired',
      trial_end: null,
      stripe_subscription_id: null,
    } as Record<string, unknown>).eq('user_id', userId);

    return NextResponse.json({
      success: true,
      message: 'トライアルを取り消しました',
    });
  } catch (error) {
    console.error('Error revoking free trial:', error);
    const message = error instanceof Stripe.errors.StripeError
      ? error.message
      : 'トライアルの取り消しに失敗しました';
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
