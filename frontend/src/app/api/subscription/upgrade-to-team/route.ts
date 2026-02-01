/**
 * 個人プラン → チームプランへのアップグレード API
 *
 * POST /api/subscription/upgrade-to-team
 *
 * Stripe 公式推奨: 既存サブスクリプションの items を更新する (subscriptions.update)
 * - 同一 Stripe Customer を使用
 * - quantity を変更するだけで日割り計算が自動適用される
 * - proration_behavior: 'always_invoice' で差額を即座に請求
 * - payment_behavior: 'pending_if_incomplete' で支払い失敗時は変更を保留
 */

import { NextResponse } from 'next/server';

import { getStripe, isPrivilegedEmail, SUBSCRIPTION_PRICE_ID } from '@/lib/subscription';
import { supabaseAdminClient } from '@/libs/supabase/supabase-admin';
import { auth, clerkClient } from '@clerk/nextjs/server';

export async function POST(request: Request) {
  try {
    // 1. 認証チェック
    const authData = await auth();
    const userId = authData.userId;

    if (!userId) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
    }

    // 2. ユーザー情報を取得
    const client = await clerkClient();
    const user = await client.users.getUser(userId);
    const userEmail = user.emailAddresses?.[0]?.emailAddress;
    const userFullName = `${user.firstName || ''} ${user.lastName || ''}`.trim();

    if (!userEmail) {
      return NextResponse.json({ error: 'Email not found' }, { status: 400 });
    }

    if (isPrivilegedEmail(userEmail)) {
      return NextResponse.json(
        { error: 'Privileged users do not need a subscription' },
        { status: 400 }
      );
    }

    // 3. リクエストボディ
    const body = await request.json().catch(() => ({}));
    const quantity: number = Math.max(2, Math.min(50, body.quantity || 2));
    const organizationId: string | undefined = body.organizationId;
    const organizationName: string | undefined = body.organizationName;

    const supabase = supabaseAdminClient;
    const stripe = getStripe();

    // 4. 既存の個人サブスクリプションを確認
    const { data: existingUserSub } = await supabase
      .from('user_subscriptions')
      .select('stripe_customer_id, stripe_subscription_id, status')
      .eq('user_id', userId)
      .single();

    if (!existingUserSub?.stripe_subscription_id || existingUserSub.status !== 'active') {
      return NextResponse.json(
        { error: 'Active individual subscription required for upgrade' },
        { status: 400 }
      );
    }

    // 5. Stripe から現在のサブスクリプション情報を取得
    const currentSub = await stripe.subscriptions.retrieve(existingUserSub.stripe_subscription_id);
    const existingItemId = currentSub.items.data[0]?.id;

    if (!existingItemId) {
      return NextResponse.json(
        { error: 'Subscription item not found' },
        { status: 500 }
      );
    }

    // 6. 組織を作成 or 既存を確認
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
          stripe_customer_id: existingUserSub.stripe_customer_id,
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

      // オーナーのメンバー情報を更新
      await supabase
        .from('organization_members')
        .update({ email: userEmail, display_name: userFullName || null })
        .eq('organization_id', resolvedOrgId)
        .eq('user_id', userId);
    } else {
      // 既存組織に billing_user_id と stripe_customer_id を設定
      await supabase
        .from('organizations')
        .update({
          stripe_customer_id: existingUserSub.stripe_customer_id,
          billing_user_id: userId,
        })
        .eq('id', resolvedOrgId);
    }

    // 7. Stripe サブスクリプションを更新（日割り + 即時請求）
    // Note: pending_if_incomplete では metadata の同時更新が不可（Stripe制限）
    // そのため、まず items を更新し、成功後に metadata を別途更新する
    const updatedSub = await stripe.subscriptions.update(
      existingUserSub.stripe_subscription_id,
      {
        items: [{
          id: existingItemId,
          quantity,
        }],
        proration_behavior: 'always_invoice',
        payment_behavior: 'pending_if_incomplete',
      }
    );

    // 7b. metadata を別途更新（items 更新成功後）
    await stripe.subscriptions.update(
      existingUserSub.stripe_subscription_id,
      {
        metadata: {
          user_id: userId,
          organization_id: resolvedOrgId,
        },
      }
    );

    // 8. organization_subscriptions に upsert
    const currentPeriodEnd = updatedSub.items?.data?.[0]?.current_period_end;
    const currentPeriodStart = updatedSub.items?.data?.[0]?.current_period_start;

    await supabase.from('organization_subscriptions').upsert(
      {
        id: updatedSub.id,
        organization_id: resolvedOrgId,
        status: updatedSub.status as 'active' | 'trialing' | 'canceled' | 'incomplete' | 'incomplete_expired' | 'past_due' | 'unpaid' | 'paused',
        quantity,
        price_id: SUBSCRIPTION_PRICE_ID || null,
        cancel_at_period_end: updatedSub.cancel_at_period_end,
        current_period_start: currentPeriodStart
          ? new Date(currentPeriodStart * 1000).toISOString()
          : new Date().toISOString(),
        current_period_end: currentPeriodEnd
          ? new Date(currentPeriodEnd * 1000).toISOString()
          : new Date().toISOString(),
        metadata: { user_id: userId, organization_id: resolvedOrgId },
      },
      { onConflict: 'id' }
    );

    // 9. user_subscriptions にアップグレード先を記録
    // Note: upgraded_to_org_id はマイグレーション適用後に有効。型生成前は型アサーションで対応。
    await supabase
      .from('user_subscriptions')
      .update({ upgraded_to_org_id: resolvedOrgId } as Record<string, unknown>)
      .eq('user_id', userId);

    console.log(
      `Upgraded user ${userId} from individual to team: org=${resolvedOrgId}, quantity=${quantity}, sub=${updatedSub.id}`
    );

    return NextResponse.json({
      success: true,
      organizationId: resolvedOrgId,
      subscriptionId: updatedSub.id,
      quantity,
      status: updatedSub.status,
    });
  } catch (error) {
    console.error('Error upgrading to team plan:', error);

    // Stripe エラーの詳細判定
    if (error && typeof error === 'object' && 'type' in error) {
      const stripeError = error as { type: string; statusCode?: number; message?: string };

      // 支払い失敗（カード拒否など）
      if (stripeError.statusCode === 402 || stripeError.type === 'StripeCardError') {
        return NextResponse.json(
          { error: 'Payment failed. Please update your payment method and try again.' },
          { status: 402 }
        );
      }
    }

    return NextResponse.json(
      { error: 'Failed to upgrade subscription' },
      { status: 500 }
    );
  }
}
