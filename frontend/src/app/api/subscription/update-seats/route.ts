/**
 * チームプラン シート数変更 API
 *
 * POST /api/subscription/update-seats
 *
 * 既存のチームプランのシート数を変更する
 * Stripe subscriptions.update() で quantity を更新（日割り自動適用）
 */

import { NextResponse } from 'next/server';

import { getStripe, isPrivilegedEmail } from '@/lib/subscription';
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

    // ユーザーが所属する組織のサブスクリプションを取得
    const { data: memberships } = await supabase
      .from('organization_members')
      .select('organization_id, role')
      .eq('user_id', userId);

    if (!memberships || memberships.length === 0) {
      return NextResponse.json(
        { error: 'No organization found' },
        { status: 400 }
      );
    }

    // owner または admin のみシート変更可能
    const adminMembership = memberships.find((m) => m.role === 'owner' || m.role === 'admin');
    if (!adminMembership) {
      return NextResponse.json(
        { error: 'Only organization owners or admins can change seats' },
        { status: 403 }
      );
    }

    const orgId = adminMembership.organization_id;

    // 組織のアクティブなサブスクリプションを取得
    const { data: orgSub } = await supabase
      .from('organization_subscriptions')
      .select('id, status, quantity')
      .eq('organization_id', orgId)
      .eq('status', 'active')
      .single();

    if (!orgSub) {
      return NextResponse.json(
        { error: 'No active team subscription found' },
        { status: 400 }
      );
    }

    if (orgSub.quantity === quantity) {
      return NextResponse.json(
        { error: 'Seat count is already the same' },
        { status: 400 }
      );
    }

    // Stripe からサブスクリプション情報を取得
    const currentSub = await stripe.subscriptions.retrieve(orgSub.id);
    const existingItem = currentSub.items.data[0];

    if (!existingItem) {
      return NextResponse.json(
        { error: 'Subscription item not found' },
        { status: 500 }
      );
    }

    // Stripe サブスクリプションを更新
    // pending_if_incomplete では metadata 同時更新不可のため items のみ
    const updatedSub = await stripe.subscriptions.update(
      orgSub.id,
      {
        items: [{
          id: existingItem.id,
          quantity,
        }],
        proration_behavior: 'always_invoice',
        payment_behavior: 'pending_if_incomplete',
      }
    );

    // DB の organization_subscriptions を更新
    const currentPeriodEnd = updatedSub.items?.data?.[0]?.current_period_end;

    await supabase
      .from('organization_subscriptions')
      .update({
        quantity,
        current_period_end: currentPeriodEnd
          ? new Date(currentPeriodEnd * 1000).toISOString()
          : undefined,
      })
      .eq('id', orgSub.id);

    const direction = quantity > (orgSub.quantity || 1) ? 'increased' : 'decreased';
    console.log(
      `Seats ${direction} for org=${orgId}: ${orgSub.quantity} → ${quantity}, sub=${orgSub.id}`
    );

    return NextResponse.json({
      success: true,
      organizationId: orgId,
      subscriptionId: orgSub.id,
      previousQuantity: orgSub.quantity,
      newQuantity: quantity,
      status: updatedSub.status,
    });
  } catch (error) {
    console.error('Error updating seats:', error);

    if (error && typeof error === 'object' && 'type' in error) {
      const stripeError = error as { type: string; statusCode?: number };

      if (stripeError.statusCode === 402 || stripeError.type === 'StripeCardError') {
        return NextResponse.json(
          { error: 'Payment failed. Please update your payment method and try again.' },
          { status: 402 }
        );
      }
    }

    return NextResponse.json(
      { error: 'Failed to update seats' },
      { status: 500 }
    );
  }
}
