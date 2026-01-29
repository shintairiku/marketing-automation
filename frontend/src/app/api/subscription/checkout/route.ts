/**
 * Stripe Checkout Session 作成 API
 *
 * POST /api/subscription/checkout
 *
 * サブスクリプション購入のためのCheckout Sessionを作成し、
 * StripeのCheckoutページURLを返す
 *
 * 個人サブスクと組織サブスクの両方に対応:
 * - organizationId を指定すると組織サブスクとして処理
 * - quantity でシート数を指定可能（デフォルト: 1）
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
    const userFullName = `${user.firstName || ''} ${user.lastName || ''}`.trim();

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

    // 5. リクエストボディから情報を取得
    const body = await request.json().catch(() => ({}));
    const successUrl = body.successUrl || `${process.env.NEXT_PUBLIC_APP_URL}/blog/new?subscription=success`;
    const cancelUrl = body.cancelUrl || `${process.env.NEXT_PUBLIC_APP_URL}/pricing?subscription=canceled`;
    const quantity: number = Math.max(1, Math.min(50, body.quantity || 1));
    const organizationId: string | undefined = body.organizationId;
    const organizationName: string | undefined = body.organizationName;

    const supabase = supabaseAdminClient;

    // 6. 組織サブスクの場合: 組織を作成 or 既存を確認
    let resolvedOrgId = organizationId;

    if (quantity > 1 || organizationId || organizationName) {
      // 組織サブスク
      if (!resolvedOrgId) {
        // 組織を自動作成
        const orgName = organizationName || `${userFullName || userEmail}の組織`;

        // Clerk Organization を作成
        const clerkOrg = await client.organizations.createOrganization({
          name: orgName,
          createdBy: userId,
        });

        const { data: newOrg, error: orgError } = await supabase
          .from('organizations')
          .insert({
            name: orgName,
            owner_user_id: userId,
            clerk_organization_id: clerkOrg.id,
          })
          .select()
          .single();

        if (orgError) {
          console.error('Error creating organization:', orgError);
          return NextResponse.json(
            { error: 'Failed to create organization' },
            { status: 500 }
          );
        }

        resolvedOrgId = newOrg.id;

        // オーナーの email と display_name をメンバーテーブルに更新
        // (トリガーで owner が自動追加されるが email/display_name は入らない)
        await supabase
          .from('organization_members')
          .update({ email: userEmail, display_name: userFullName || null })
          .eq('organization_id', resolvedOrgId)
          .eq('user_id', userId);
      }

      const stripe = getStripe();

      // 既存組織の Stripe 顧客IDを確認
      const { data: existingOrg } = await supabase
        .from('organizations')
        .select('stripe_customer_id')
        .eq('id', resolvedOrgId)
        .single();

      // 組織用の Stripe Customer を確保
      // 既存の個人用 Customer と分離するため、組織専用の Customer を作成
      let orgStripeCustomerId = existingOrg?.stripe_customer_id;

      if (!orgStripeCustomerId) {
        const newCustomer = await stripe.customers.create({
          email: userEmail,
          name: organizationName || `Organization ${resolvedOrgId}`,
          metadata: {
            organization_id: resolvedOrgId,
            created_by: userId,
          },
        });
        orgStripeCustomerId = newCustomer.id;

        // 組織に Stripe Customer ID を保存
        await supabase
          .from('organizations')
          .update({ stripe_customer_id: orgStripeCustomerId })
          .eq('id', resolvedOrgId);

        console.log(`Created new Stripe customer ${orgStripeCustomerId} for org ${resolvedOrgId}`);
      }

      // 7. Stripe Checkout Session作成（組織）
      // 注: 個人サブスクのキャンセルはWebhook（checkout.session.completed）で行う
      // チェックアウト未完了時に個人プランが失われるのを防ぐため
      // 組織専用の Stripe Customer を使用（個人用とは別）
      const sessionParams: Stripe.Checkout.SessionCreateParams = {
        mode: 'subscription',
        payment_method_types: ['card'],
        line_items: [
          {
            price: SUBSCRIPTION_PRICE_ID,
            quantity,
          },
        ],
        success_url: successUrl,
        cancel_url: cancelUrl,
        customer: orgStripeCustomerId,
        metadata: {
          user_id: userId,
          organization_id: resolvedOrgId,
        },
        subscription_data: {
          metadata: {
            user_id: userId,
            organization_id: resolvedOrgId,
          },
        },
        automatic_tax: { enabled: true },
        customer_update: {
          address: 'auto',
        },
        billing_address_collection: 'required',
        allow_promotion_codes: true,
        locale: 'ja',
      };

      const session = await stripe.checkout.sessions.create(sessionParams);

      return NextResponse.json({
        url: session.url,
        sessionId: session.id,
        organizationId: resolvedOrgId,
      });
    }

    // 8. 個人サブスク（従来通り）
    const { data: existingSubscription } = await supabase
      .from('user_subscriptions')
      .select('stripe_customer_id')
      .eq('user_id', userId)
      .single();

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
      automatic_tax: { enabled: true },
      billing_address_collection: 'required',
      customer_email: existingSubscription?.stripe_customer_id ? undefined : userEmail,
      customer: existingSubscription?.stripe_customer_id || undefined,
      allow_promotion_codes: true,
      locale: 'ja',
    };

    const session = await stripe.checkout.sessions.create(sessionParams);

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
