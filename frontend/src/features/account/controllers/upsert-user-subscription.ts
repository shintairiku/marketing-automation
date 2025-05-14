import Stripe from 'stripe';

// Stripeの型定義を拡張
interface StripeSubscriptionWithPeriod extends Stripe.Subscription {
  current_period_start: number;
  current_period_end: number;
}

import { stripeAdmin } from '@/libs/stripe/stripe-admin';
import { supabaseAdminClient } from '@/libs/supabase/supabase-admin';
import type { Database } from '@/libs/supabase/types';
import { toDateTime } from '@/utils/to-date-time';
import { AddressParam } from '@stripe/stripe-js';

export async function upsertUserSubscription({
  subscriptionId,
  customerId,
  isCreateAction,
}: {
  subscriptionId: string;
  customerId: string;
  isCreateAction?: boolean;
}) {
  try {
    // Get customer's userId from mapping table.
    const { data: customerData, error: noCustomerError } = await supabaseAdminClient
      .from('customers')
      .select('id')
      .eq('stripe_customer_id', customerId)
      .single();
    if (noCustomerError) throw noCustomerError;

    const { id: userId } = customerData!;

    // デバッグ用にログを追加
    console.log('Retrieving subscription with ID:', subscriptionId);
    
    const subscription = await stripeAdmin.subscriptions.retrieve(subscriptionId, {
      expand: ['default_payment_method'],
    }) as unknown as StripeSubscriptionWithPeriod;
  
  // デバッグ用にタイムスタンプ情報をログ出力
  console.log('Subscription timestamps:', {
    subscription_id: subscription.id,
    raw_data: JSON.stringify(subscription),
    current_period_start: subscription.current_period_start,
    current_period_end: subscription.current_period_end,
    created: subscription.created,
    type_current_period_start: typeof subscription.current_period_start,
    type_current_period_end: typeof subscription.current_period_end,
    type_created: typeof subscription.created
  });

  // 安全に日付文字列を取得する関数
  const safeISOString = (timestamp: number | null | undefined): string | null => {
    if (timestamp === null || timestamp === undefined) {
      console.log(`Timestamp is null or undefined: ${timestamp}`);
      return null;
    }
    
    try {
      console.log(`Converting timestamp: ${timestamp} of type ${typeof timestamp}`);
      const date = new Date(timestamp * 1000);
      console.log(`Created date: ${date.toString()}`);
      return date.toISOString();
    } catch (error) {
      console.error(`Error converting timestamp to ISO string: ${timestamp}`, error);
      return new Date().toISOString(); // フォールバック
    }
  };

  // Upsert the latest status of the subscription object.
  const subscriptionData: Database['public']['Tables']['subscriptions']['Insert'] = {
    id: subscription.id,
    user_id: userId,
    metadata: subscription.metadata,
    status: subscription.status,
    price_id: subscription.items.data[0].price.id,
    cancel_at_period_end: subscription.cancel_at_period_end,
    cancel_at: subscription.cancel_at ? safeISOString(subscription.cancel_at) : null,
    canceled_at: subscription.canceled_at ? safeISOString(subscription.canceled_at) : null,
    current_period_start: safeISOString(subscription.current_period_start) || new Date().toISOString(),
    current_period_end: safeISOString(subscription.current_period_end) || new Date().toISOString(),
    created: safeISOString(subscription.created) || new Date().toISOString(),
    ended_at: subscription.ended_at ? safeISOString(subscription.ended_at) : null,
    trial_start: subscription.trial_start ? safeISOString(subscription.trial_start) : null,
    trial_end: subscription.trial_end ? safeISOString(subscription.trial_end) : null,
  };

    const { error } = await supabaseAdminClient.from('subscriptions').upsert([subscriptionData]);
    if (error) {
      throw error;
    }
    console.info(`Inserted/updated subscription [${subscription.id}] for user [${userId}]`);

    // For a new subscription copy the billing details to the customer object.
    // NOTE: This is a costly operation and should happen at the very end.
    if (isCreateAction && subscription.default_payment_method && userId) {
      await copyBillingDetailsToCustomer(userId, subscription.default_payment_method as Stripe.PaymentMethod);
    }
    
    return { success: true };
  } catch (error) {
    console.error('Error in upsertUserSubscription:', error);
    return { success: false, error };
  }
}

const copyBillingDetailsToCustomer = async (userId: string, paymentMethod: Stripe.PaymentMethod) => {
  const customer = paymentMethod.customer;
  if (typeof customer !== 'string') {
    throw new Error('Customer id not found');
  }

  const { name, phone, address } = paymentMethod.billing_details;
  if (!name || !phone || !address) return;

  await stripeAdmin.customers.update(customer, { name, phone, address: address as AddressParam });

  const { error } = await supabaseAdminClient
    .from('users')
    .update({
      billing_address: { ...address },
      payment_method: { ...paymentMethod[paymentMethod.type] },
    })
    .eq('id', userId);

  if (error) {
    throw error;
  }
};
