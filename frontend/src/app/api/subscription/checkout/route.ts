/**
 * Stripe Checkout Session 作成 API
 *
 * POST /api/subscription/checkout
 *
 * サブスクリプション購入のためのCheckout Sessionを作成し、
 * StripeのCheckoutページURLを返す
 *
 * 個人サブスクと組織サブスクの両方に対応:
 * - 既に個人サブスクがある場合のチーム移行は /api/subscription/upgrade-to-team を使用
 * - organizationId を指定すると新規組織サブスクとして処理（ユーザーの Stripe Customer を使用）
 * - quantity でシート数を指定可能（デフォルト: 1）
 */

import { NextResponse } from 'next/server';
import type Stripe from 'stripe';

import { getStripe, isPrivilegedEmail, SUBSCRIPTION_PRICE_ID } from '@/lib/subscription';
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
    const cancelUrl = body.cancelUrl || `${process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:3000'}/settings/billing?subscription=canceled`;
    const quantity: number = Math.max(1, Math.min(50, body.quantity || 1));
    const organizationId: string | undefined = body.organizationId;
    const organizationName: string | undefined = body.organizationName;

    const supabase = supabaseAdminClient;

    // 6. 既存の個人サブスクリプションを確認
    const { data: existingUserSub } = await supabase
      .from('user_subscriptions')
      .select('stripe_customer_id, stripe_subscription_id, status')
      .eq('user_id', userId)
      .single();

    const isTeamRequest = quantity > 1 || organizationId || organizationName;

    // 7. チームプランへのアップグレード: 既に個人サブスクがある場合
    if (isTeamRequest && existingUserSub?.stripe_subscription_id && existingUserSub.status === 'active') {
      // upgrade-to-team エンドポイントを使うように誘導
      return NextResponse.json(
        {
          error: 'Use /api/subscription/upgrade-to-team for upgrading from individual to team plan',
          redirect: '/api/subscription/upgrade-to-team',
          hasActiveSubscription: true,
        },
        { status: 409 }
      );
    }

    // 8. 新規チームプラン（個人サブスクなし）: ユーザー自身の Stripe Customer を使用
    if (isTeamRequest) {
      let resolvedOrgId = organizationId;

      if (!resolvedOrgId) {
        const orgName = organizationName || `${userFullName || userEmail}のチーム`;

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
            billing_user_id: userId,
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

        await supabase
          .from('organization_members')
          .update({ email: userEmail, display_name: userFullName || null })
          .eq('organization_id', resolvedOrgId)
          .eq('user_id', userId);
      }

      const stripe = getStripe();

      // ユーザー自身の Stripe Customer を使用（組織用に別 Customer は作成しない）
      let stripeCustomerId = existingUserSub?.stripe_customer_id;

      if (!stripeCustomerId) {
        const newCustomer = await stripe.customers.create({
          email: userEmail,
          name: userFullName || userEmail,
          metadata: {
            user_id: userId,
          },
        });
        stripeCustomerId = newCustomer.id;
      }

      // 組織に stripe_customer_id を保存（ユーザーと同一の Customer）
      await supabase
        .from('organizations')
        .update({
          stripe_customer_id: stripeCustomerId,
          billing_user_id: userId,
        })
        .eq('id', resolvedOrgId);

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
        customer: stripeCustomerId,
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

    // 9. 個人サブスク（従来通り）
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
      customer_email: existingUserSub?.stripe_customer_id ? undefined : userEmail,
      customer: existingUserSub?.stripe_customer_id || undefined,
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
