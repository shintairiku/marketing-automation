/**
 * アップグレード料金プレビュー API
 *
 * POST /api/subscription/preview-upgrade
 *
 * Stripe invoices.createPreview() を使用して、
 * 個人→チームプランへのアップグレード時の日割り差額を事前に計算する
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
    const quantity: number = Math.max(2, Math.min(50, body.quantity || 2));

    const supabase = supabaseAdminClient;
    const stripe = getStripe();

    // 既存の個人サブスクリプションを確認
    const { data: existingUserSub } = await supabase
      .from('user_subscriptions')
      .select('stripe_customer_id, stripe_subscription_id, status')
      .eq('user_id', userId)
      .single();

    if (!existingUserSub?.stripe_subscription_id || existingUserSub.status !== 'active') {
      return NextResponse.json(
        { error: 'Active individual subscription required' },
        { status: 400 }
      );
    }

    // Stripe からサブスク情報を取得
    const currentSub = await stripe.subscriptions.retrieve(existingUserSub.stripe_subscription_id);
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
      customer: existingUserSub.stripe_customer_id!,
      subscription: existingUserSub.stripe_subscription_id,
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
      // 即座に請求される金額（円）
      amountDue: preview.amount_due,
      // 通貨
      currency: preview.currency,
      // 明細
      lines,
      // 現在のプラン情報
      currentQuantity: existingItem.quantity || 1,
      newQuantity: quantity,
      currentPeriodEnd: periodEndDate,
      // proration_date を返す（実際のアップグレード時に使用可能）
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
