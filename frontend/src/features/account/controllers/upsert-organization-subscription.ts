import Stripe from 'stripe';

import { stripeAdmin } from '@/libs/stripe/stripe-admin';
import { supabaseAdminClient } from '@/libs/supabase/supabase-admin';
import type { Database } from '@/libs/supabase/types';

/**
 * 組織のサブスクリプション情報をupsert
 */
export async function upsertOrganizationSubscription({
  subscriptionId,
  customerId,
  isCreateAction,
}: {
  subscriptionId: string;
  customerId: string;
  isCreateAction?: boolean;
}) {
  try {
    console.log('Processing organization subscription:', { subscriptionId, customerId, isCreateAction });

    // Stripeサブスクリプション情報を取得
    const subscription = await stripeAdmin.subscriptions.retrieve(subscriptionId, {
      expand: ['default_payment_method', 'customer'],
    });

    // メタデータから組織IDを取得
    const organizationId = subscription.metadata?.organization_id;
    if (!organizationId) {
      throw new Error('組織IDがサブスクリプションメタデータに含まれていません');
    }

    // 組織情報を取得・確認
    const { data: organizationData, error: orgError } = await supabaseAdminClient
      .from('organizations')
      .select('id, owner_user_id, stripe_customer_id')
      .eq('id', organizationId)
      .single();

    if (orgError || !organizationData) {
      throw new Error(`組織が見つかりません: ${organizationId}`);
    }

    // シート数を取得（quantity）
    const seatQuantity = subscription.items.data[0]?.quantity || 2;

    // 組織テーブルの更新
    const organizationUpdates = {
      stripe_customer_id: customerId,
      stripe_subscription_id: subscription.id,
      max_seats: seatQuantity,
      subscription_status: subscription.status,
    };

    const { error: orgUpdateError } = await supabaseAdminClient
      .from('organizations')
      .update(organizationUpdates)
      .eq('id', organizationId);

    if (orgUpdateError) {
      throw new Error(`組織情報の更新に失敗: ${orgUpdateError.message}`);
    }

    // unified_subscriptions テーブルにも記録
    const subscriptionAny = subscription as any;
    const unifiedSubscriptionData = {
      organization_id: organizationId,
      subscription_type: 'team' as const,
      plan_tier: 'pro' as const, // Team プランは Pro tier とする
      stripe_customer_id: customerId,
      stripe_subscription_id: subscription.id,
      stripe_price_id: subscription.items.data[0].price.id,
      seat_quantity: seatQuantity,
      seat_price_per_unit: subscription.items.data[0].price.unit_amount || 0,
      status: subscription.status,
      current_period_start: subscriptionAny.current_period_start 
        ? new Date(subscriptionAny.current_period_start * 1000).toISOString()
        : new Date().toISOString(),
      current_period_end: subscriptionAny.current_period_end
        ? new Date(subscriptionAny.current_period_end * 1000).toISOString()
        : new Date().toISOString(),
      cancel_at_period_end: subscriptionAny.cancel_at_period_end,
      monthly_article_limit: seatQuantity * 50, // シート当たり50記事/月
      monthly_articles_used: 0,
    };

    const { error: unifiedError } = await supabaseAdminClient
      .from('unified_subscriptions')
      .upsert([unifiedSubscriptionData], { onConflict: 'stripe_subscription_id' });

    if (unifiedError) {
      throw new Error(`統合サブスクリプション情報の更新に失敗: ${unifiedError.message}`);
    }

    console.info(`Updated organization subscription [${subscription.id}] for organization [${organizationId}]`);

    // サブスクリプション作成時は課金詳細をコピー
    if (isCreateAction && subscription.default_payment_method) {
      await copyBillingDetailsToOrganization(organizationId, subscription.default_payment_method as Stripe.PaymentMethod);
    }

    return { success: true, organizationId };
  } catch (error) {
    console.error('Error in upsertOrganizationSubscription:', error);
    return { success: false, error };
  }
}

/**
 * 課金詳細を組織設定にコピー
 */
const copyBillingDetailsToOrganization = async (
  organizationId: string, 
  paymentMethod: Stripe.PaymentMethod
) => {
  try {
    const { billing_details } = paymentMethod;
    
    if (billing_details.email) {
      // 組織の課金用メールアドレスを更新
      const { error } = await supabaseAdminClient
        .from('organizations')
        .update({ billing_email: billing_details.email })
        .eq('id', organizationId);

      if (error) {
        console.error('Failed to update organization billing email:', error);
      }
    }

    console.info(`Updated billing details for organization [${organizationId}]`);
  } catch (error) {
    console.error('Error copying billing details to organization:', error);
  }
};

/**
 * サブスクリプションのタイプを判定（個人 vs 組織）
 */
export function isOrganizationSubscription(subscription: Stripe.Subscription): boolean {
  return !!subscription.metadata?.organization_id;
}

/**
 * シート数の変更を処理
 */
export async function handleSeatQuantityChange({
  subscriptionId,
  oldQuantity,
  newQuantity,
  organizationId,
}: {
  subscriptionId: string;
  oldQuantity: number;
  newQuantity: number;
  organizationId: string;
}) {
  try {
    console.log(`Seat quantity changed: ${oldQuantity} → ${newQuantity} for org ${organizationId}`);

    // 組織のmax_seatsを更新
    const { error: orgError } = await supabaseAdminClient
      .from('organizations')
      .update({ max_seats: newQuantity })
      .eq('id', organizationId);

    if (orgError) {
      throw new Error(`組織シート数更新に失敗: ${orgError.message}`);
    }

    // 統合サブスクリプションも更新
    const { error: unifiedError } = await supabaseAdminClient
      .from('unified_subscriptions')
      .update({ 
        seat_quantity: newQuantity,
        monthly_article_limit: newQuantity * 50 // シート当たり50記事/月
      })
      .eq('stripe_subscription_id', subscriptionId);

    if (unifiedError) {
      throw new Error(`統合サブスクリプション更新に失敗: ${unifiedError.message}`);
    }

    // 使用中シート数が新しい上限を超える場合、警告ログ
    const { data: currentOrg } = await supabaseAdminClient
      .from('organizations')
      .select('used_seats')
      .eq('id', organizationId)
      .single();

    if (currentOrg && currentOrg.used_seats > newQuantity) {
      console.warn(`Organization ${organizationId} is using ${currentOrg.used_seats} seats but limit is now ${newQuantity}`);
      // TODO: 超過分の処理（メンバー非アクティブ化など）
    }

    return { success: true };
  } catch (error) {
    console.error('Error in handleSeatQuantityChange:', error);
    return { success: false, error };
  }
}