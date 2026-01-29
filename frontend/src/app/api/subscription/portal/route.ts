/**
 * Stripe Customer Portal Session 作成 API
 *
 * POST /api/subscription/portal
 *
 * サブスクリプション管理のためのCustomer Portal Sessionを作成し、
 * StripeのポータルページURLを返す
 */

import { NextResponse } from 'next/server';

import { getStripe } from '@/lib/subscription';
import { supabaseAdminClient } from '@/libs/supabase/supabase-admin';
import { auth } from '@clerk/nextjs/server';

export async function POST(request: Request) {
  try {
    // 1. 認証チェック
    const authData = await auth();
    const userId = authData.userId;

    if (!userId) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      );
    }

    // 2. ユーザーのStripe顧客IDを取得
    const supabase = supabaseAdminClient;
    const { data: subscription, error } = await supabase
      .from('user_subscriptions')
      .select('stripe_customer_id')
      .eq('user_id', userId)
      .single();

    if (error || !subscription?.stripe_customer_id) {
      return NextResponse.json(
        { error: 'No subscription found' },
        { status: 404 }
      );
    }

    // 3. リクエストボディからURLを取得
    const body = await request.json().catch(() => ({}));
    const returnUrl = body.returnUrl || `${process.env.NEXT_PUBLIC_APP_URL}/dashboard`;

    // 4. Stripe Customer Portal Session作成
    const stripe = getStripe();

    const session = await stripe.billingPortal.sessions.create({
      customer: subscription.stripe_customer_id,
      return_url: returnUrl,
      locale: 'ja',
    });

    // 5. Portal URLを返す
    return NextResponse.json({
      url: session.url,
    });
  } catch (error) {
    console.error('Error creating portal session:', error);
    return NextResponse.json(
      { error: 'Failed to create portal session' },
      { status: 500 }
    );
  }
}
