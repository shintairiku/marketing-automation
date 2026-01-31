/**
 * サブスクリプション変更 料金プレビュー API
 *
 * POST /api/subscription/preview-upgrade
 *
 * Stripe invoices.createPreview() を使用して、
 * サブスクリプション変更時の日割り差額を事前に計算する
 *
 * 対応パターン:
 * 1. 個人→チームプランへのアップグレード（user_subscriptions 経由）
 * 2. チームプランのシート数変更（organization_subscriptions 経由）
 */

import { NextResponse } from 'next/server';

import { getStripe, isPrivilegedEmail, SUBSCRIPTION_PRICE_ID } from '@/lib/subscription';
import { supabaseAdminClient } from '@/libs/supabase/supabase-admin';
import { auth, clerkClient } from '@clerk/nextjs/server';

export async function POST(request: Request) {
  try {
    const authData = await auth();
    const userId = authData.userId;

    if (!userId) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    const client = await clerkClient();
    const user = await client.users.getUser(userId);
    const userEmail = user.emailAddresses?.[0]?.emailAddress;

    if (!userEmail) {
      return NextResponse.json({ error: 'Email not found' }, { status: 400 });
    }

    if (isPrivilegedEmail(userEmail)) {
      return NextResponse.json(
        { error: 'Privileged users do not need a subscription' },
        { status: 400 }
      );
    }

    const body = await request.json().catch(() => ({}));
    const quantity: number = Math.max(1, Math.min(50, body.quantity || 2));

    const supabase = supabaseAdminClient;
    const stripe = getStripe();

    // まずチームプランのサブスクを確認（シート変更のケース）
    const { data: memberships } = await supabase
      .from('organization_members')
      .select('organization_id')
      .eq('user_id', userId);

    let stripeCustomerId: string | null = null;
    let stripeSubscriptionId: string | null = null;

    if (memberships && memberships.length > 0) {
      const orgIds = memberships.map((m) => m.organization_id);
      const { data: orgSub } = await supabase
        .from('organization_subscriptions')
        .select('id, organization_id, quantity')
        .in('organization_id', orgIds)
        .eq('status', 'active')
        .limit(1)
        .single();

      if (orgSub) {
        // チームプランのシート変更プレビュー
        const { data: org } = await supabase
          .from('organizations')
          .select('stripe_customer_id')
          .eq('id', orgSub.organization_id)
          .single();

        stripeCustomerId = org?.stripe_customer_id || null;
        stripeSubscriptionId = orgSub.id;
      }
    }

    // チームプランがなければ個人サブスクをチェック（アップグレードのケース）
    if (!stripeSubscriptionId) {
      const { data: existingUserSub } = await supabase
        .from('user_subscriptions')
        .select('stripe_customer_id, stripe_subscription_id, status')
        .eq('user_id', userId)
        .single();

      if (!existingUserSub?.stripe_subscription_id || existingUserSub.status !== 'active') {
        return NextResponse.json(
          { error: 'No active subscription found' },
          { status: 400 }
        );
      }

      stripeCustomerId = existingUserSub.stripe_customer_id;
      stripeSubscriptionId = existingUserSub.stripe_subscription_id;
    }

    if (!stripeCustomerId || !stripeSubscriptionId) {
      return NextResponse.json(
        { error: 'Subscription not found' },
        { status: 400 }
      );
    }

    // Stripe からサブスク情報を取得
    const currentSub = await stripe.subscriptions.retrieve(stripeSubscriptionId);
    const existingItem = currentSub.items.data[0];

    if (!existingItem) {
      return NextResponse.json(
        { error: 'Subscription item not found' },
        { status: 500 }
      );
    }

    // invoices.createPreview で日割り差額をプレビュー
    const proration_date = Math.floor(Date.now() / 1000);

    const preview = await stripe.invoices.createPreview({
      customer: stripeCustomerId,
      subscription: stripeSubscriptionId,
      subscription_details: {
        items: [
          {
            id: existingItem.id,
            price: SUBSCRIPTION_PRICE_ID!,
            quantity,
          },
        ],
        proration_date,
        proration_behavior: 'always_invoice',
      },
    });

    // プレビュー結果からプロレーション項目を抽出
    const lines = preview.lines.data.map((line) => ({
      description: line.description,
      amount: line.amount,
      proration: line.parent?.subscription_item_details?.proration ?? false,
    }));

    // 現在の期間終了日
    const currentPeriodEnd = existingItem.current_period_end;
    const periodEndDate = currentPeriodEnd
      ? new Date(currentPeriodEnd * 1000).toISOString()
      : null;

    return NextResponse.json({
      amountDue: preview.amount_due,
      currency: preview.currency,
      lines,
      currentQuantity: existingItem.quantity || 1,
      newQuantity: quantity,
      currentPeriodEnd: periodEndDate,
      prorationDate: proration_date,
    });
  } catch (error) {
    console.error('Error previewing upgrade:', error);
    return NextResponse.json(
      { error: 'Failed to preview upgrade' },
      { status: 500 }
    );
  }
}
