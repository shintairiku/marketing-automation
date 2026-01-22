/**
 * Stripe Checkout Session 作成 API
 *
 * POST /api/subscription/checkout
 *
 * サブスクリプション購入のためのCheckout Sessionを作成し、
 * StripeのCheckoutページURLを返す
 */

import { NextResponse } from 'next/server';
import type Stripe from 'stripe';

import { getStripe, isPrivilegedEmail,SUBSCRIPTION_PRICE_ID } from '@/lib/subscription';
import { supabaseAdminClient } from '@/libs/supabase/supabase-admin';
import { auth, clerkClient } from '@clerk/nextjs/server';

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

    // 2. ユーザー情報を取得（Clerk APIから）
    const client = await clerkClient();
    const user = await client.users.getUser(userId);
    const userEmail = user.emailAddresses?.[0]?.emailAddress;

    if (!userEmail) {
      return NextResponse.json(
        { error: 'Email not found in user profile' },
        { status: 400 }
      );
    }

    // 3. 特権ユーザーはチェックアウト不要
    if (isPrivilegedEmail(userEmail)) {
      return NextResponse.json(
        { error: 'Privileged users do not need a subscription' },
        { status: 400 }
      );
    }

    // 4. 価格IDの確認
    if (!SUBSCRIPTION_PRICE_ID) {
      console.error('STRIPE_PRICE_ID is not configured');
      return NextResponse.json(
        { error: 'Subscription not configured' },
        { status: 500 }
      );
    }

    // 5. リクエストボディからURLを取得
    const body = await request.json().catch(() => ({}));
    const successUrl = body.successUrl || `${process.env.NEXT_PUBLIC_APP_URL}/dashboard?subscription=success`;
    const cancelUrl = body.cancelUrl || `${process.env.NEXT_PUBLIC_APP_URL}/pricing?subscription=canceled`;

    // 6. 既存のStripe顧客を確認
    const supabase = supabaseAdminClient;
    const { data: existingSubscription } = await supabase
      .from('user_subscriptions')
      .select('stripe_customer_id')
      .eq('user_id', userId)
      .single();

    // 7. Stripe Checkout Session作成
    const stripe = getStripe();

    const sessionParams: Stripe.Checkout.SessionCreateParams = {
      mode: 'subscription',
      payment_method_types: ['card'],
      line_items: [
        {
          price: SUBSCRIPTION_PRICE_ID,
          quantity: 1,
        },
      ],
      success_url: successUrl,
      cancel_url: cancelUrl,
      metadata: {
        user_id: userId,
      },
      subscription_data: {
        metadata: {
          user_id: userId,
        },
      },
      // 日本円の場合は税金計算を有効化
      automatic_tax: {
        enabled: true,
      },
      // 請求先住所を収集
      billing_address_collection: 'required',
      // 顧客メールを設定
      customer_email: existingSubscription?.stripe_customer_id ? undefined : userEmail,
      // 既存顧客がいる場合はそれを使用
      customer: existingSubscription?.stripe_customer_id || undefined,
      // プロモーションコードを許可
      allow_promotion_codes: true,
      // ロケール設定（日本語）
      locale: 'ja',
    };

    const session = await stripe.checkout.sessions.create(sessionParams);

    // 8. Checkout URLを返す
    return NextResponse.json({
      url: session.url,
      sessionId: session.id,
    });
  } catch (error) {
    console.error('Error creating checkout session:', error);
    return NextResponse.json(
      { error: 'Failed to create checkout session' },
      { status: 500 }
    );
  }
}
