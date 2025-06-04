'use server';

import { redirect } from 'next/navigation';

import { stripeAdmin } from '@/libs/stripe/stripe-admin';
import { supabaseAdminClient } from '@/libs/supabase/supabase-admin';
import { getURL } from '@/utils/get-url';
import { auth } from '@clerk/nextjs/server';

interface CreateTeamCheckoutParams {
  organizationId: string;
  seatQuantity: number;
  teamPriceId: string;
  organizationName: string;
}

export async function createTeamCheckoutAction({
  organizationId,
  seatQuantity,
  teamPriceId,
  organizationName,
}: CreateTeamCheckoutParams) {
  const { userId } = await auth();
  
  if (!userId) {
    throw new Error('認証が必要です');
  }

  if (seatQuantity < 2) {
    throw new Error('Teamプランは最低2シートが必要です');
  }

  try {
    // 組織の存在確認と権限チェック
    const { data: orgMembership, error: membershipError } = await supabaseAdminClient
      .from('organization_memberships')
      .select('role, organization_id, organizations(*)')
      .eq('organization_id', organizationId)
      .eq('user_id', userId)
      .eq('status', 'active')
      .single();

    if (membershipError || !orgMembership) {
      throw new Error('組織が見つからないか、アクセス権限がありません');
    }

    if (orgMembership.role !== 'owner') {
      throw new Error('組織のオーナーのみがサブスクリプションを管理できます');
    }

    // 既存のサブスクリプションがないことを確認
    const { data: existingSubscription } = await supabaseAdminClient
      .from('unified_subscriptions')
      .select('*')
      .eq('organization_id', organizationId)
      .eq('subscription_type', 'team')
      .in('status', ['active', 'trialing', 'past_due'])
      .single();

    if (existingSubscription) {
      throw new Error('この組織には既にアクティブなサブスクリプションがあります');
    }

    // Stripe顧客を作成または取得
    let customerId = orgMembership.organizations.stripe_customer_id;
    
    if (!customerId) {
      // 新しい顧客を作成
      const customer = await stripeAdmin.customers.create({
        email: orgMembership.organizations.billing_email || `${userId}@example.com`,
        name: organizationName,
        metadata: {
          organization_id: organizationId,
          owner_user_id: userId,
          subscription_type: 'team',
        },
      });
      customerId = customer.id;

      // 組織にcustomer IDを保存
      await supabaseAdminClient
        .from('organizations')
        .update({ stripe_customer_id: customerId })
        .eq('id', organizationId);
    }

    // Stripe Checkout Sessionを作成
    const checkoutSession = await stripeAdmin.checkout.sessions.create({
      customer: customerId,
      mode: 'subscription',
      payment_method_types: ['card'],
      line_items: [
        {
          price: teamPriceId,
          quantity: seatQuantity,
        },
      ],
      subscription_data: {
        metadata: {
          organization_id: organizationId,
          owner_user_id: userId,
          subscription_type: 'team',
          initial_seat_count: seatQuantity.toString(),
        },
      },
      metadata: {
        organization_id: organizationId,
        owner_user_id: userId,
        subscription_type: 'team',
      },
      success_url: `${getURL()}/dashboard?session_id={CHECKOUT_SESSION_ID}&organization_id=${organizationId}`,
      cancel_url: `${getURL()}/pricing?organization_id=${organizationId}`,
      allow_promotion_codes: true,
      billing_address_collection: 'required',
      locale: 'ja',
      custom_text: {
        submit: {
          message: `${organizationName} のTeamプラン（${seatQuantity}シート）をご購入いただきありがとうございます。`,
        },
      },
    });

    if (!checkoutSession.url) {
      throw new Error('チェックアウトセッションの作成に失敗しました');
    }

    // チェックアウトURLにリダイレクト
    redirect(checkoutSession.url);
  } catch (error) {
    console.error('Team checkout creation error:', error);
    
    if (error instanceof Error && error.message.includes('redirect')) {
      // redirect() の場合は再スロー
      throw error;
    }
    
    throw new Error(
      error instanceof Error 
        ? error.message 
        : 'チェックアウトセッションの作成中にエラーが発生しました'
    );
  }
}

/**
 * シート数変更用のチェックアウトセッション作成
 */
export async function createSeatChangeCheckoutAction({
  organizationId,
  currentSeatQuantity,
  newSeatQuantity,
  teamPriceId,
}: {
  organizationId: string;
  currentSeatQuantity: number;
  newSeatQuantity: number;
  teamPriceId: string;
}) {
  const { userId } = await auth();
  
  if (!userId) {
    throw new Error('認証が必要です');
  }

  if (newSeatQuantity < 2) {
    throw new Error('Teamプランは最低2シートが必要です');
  }

  if (newSeatQuantity <= currentSeatQuantity) {
    throw new Error('新しいシート数は現在より多くする必要があります');
  }

  try {
    // 権限チェック
    const { data: orgMembership, error: membershipError } = await supabaseAdminClient
      .from('organization_memberships')
      .select('role, organizations(*)')
      .eq('organization_id', organizationId)
      .eq('user_id', userId)
      .eq('status', 'active')
      .single();

    if (membershipError || !orgMembership || orgMembership.role !== 'owner') {
      throw new Error('組織のオーナーのみがシート数を変更できます');
    }

    // 既存のサブスクリプションを取得
    const { data: existingSubscription } = await supabaseAdminClient
      .from('unified_subscriptions')
      .select('stripe_subscription_id, stripe_customer_id')
      .eq('organization_id', organizationId)
      .eq('subscription_type', 'team')
      .in('status', ['active', 'trialing'])
      .single();

    if (!existingSubscription?.stripe_subscription_id) {
      throw new Error('アクティブなサブスクリプションが見つかりません');
    }

    // 既存のサブスクリプションのシート数を更新
    const subscription = await stripeAdmin.subscriptions.retrieve(
      existingSubscription.stripe_subscription_id
    );

    const subscriptionItem = subscription.items.data[0];
    
    await stripeAdmin.subscriptionItems.update(subscriptionItem.id, {
      quantity: newSeatQuantity,
      proration_behavior: 'always_invoice', // 即座に課金
    });

    console.log(`Updated seat quantity from ${currentSeatQuantity} to ${newSeatQuantity} for organization ${organizationId}`);

    return { success: true, newSeatQuantity };
  } catch (error) {
    console.error('Seat change error:', error);
    throw new Error(
      error instanceof Error 
        ? error.message 
        : 'シート数変更中にエラーが発生しました'
    );
  }
}