import Stripe from 'stripe';

// Stripeの型定義を拡張
interface StripeSubscriptionWithPeriod extends Stripe.Subscription {
  current_period_start: number;
  current_period_end: number;
}

import { 
  handleSeatQuantityChange, 
  isOrganizationSubscription,
  upsertOrganizationSubscription} from '@/features/account/controllers/upsert-organization-subscription';
import { upsertUserSubscription } from '@/features/account/controllers/upsert-user-subscription';
import { upsertPrice } from '@/features/pricing/controllers/upsert-price';
import { upsertProduct } from '@/features/pricing/controllers/upsert-product';
import { stripeAdmin } from '@/libs/stripe/stripe-admin';
import { getEnvVar } from '@/utils/get-env-var';

const relevantEvents = new Set([
  'product.created',
  'product.updated',
  'price.created',
  'price.updated',
  'checkout.session.completed',
  'customer.subscription.created',
  'customer.subscription.updated',
  'customer.subscription.deleted',
]);

export async function POST(req: Request) {
  const body = await req.text();
  const sig = req.headers.get('stripe-signature') as string;
  const webhookSecret = getEnvVar(process.env.STRIPE_WEBHOOK_SECRET, 'STRIPE_WEBHOOK_SECRET');
  let event: Stripe.Event;

  try {
    if (!sig || !webhookSecret) return;
    event = stripeAdmin.webhooks.constructEvent(body, sig, webhookSecret);
  } catch (error) {
    return Response.json(`Webhook Error: ${(error as any).message}`, { status: 400 });
  }

  if (relevantEvents.has(event.type)) {
    try {
      switch (event.type) {
        case 'product.created':
        case 'product.updated':
          await upsertProduct(event.data.object as Stripe.Product);
          break;
        case 'price.created':
        case 'price.updated':
          await upsertPrice(event.data.object as Stripe.Price);
          break;
        case 'customer.subscription.created':
        case 'customer.subscription.updated':
        case 'customer.subscription.deleted':
          const subscription = event.data.object as unknown as StripeSubscriptionWithPeriod;
          console.log(`Processing subscription ${subscription.id} for customer ${subscription.customer}`);
          
          // 組織サブスクリプションか個人サブスクリプションかを判定
          if (isOrganizationSubscription(subscription)) {
            console.log(`Processing organization subscription: ${subscription.id}`);
            
            // シート数変更の検出（更新イベントの場合）
            if (event.type === 'customer.subscription.updated' && event.data.previous_attributes) {
              const previousQuantity = event.data.previous_attributes.items?.data?.[0]?.quantity;
              const currentQuantity = subscription.items.data[0]?.quantity;
              
              if (previousQuantity && currentQuantity && previousQuantity !== currentQuantity) {
                await handleSeatQuantityChange({
                  subscriptionId: subscription.id,
                  oldQuantity: previousQuantity,
                  newQuantity: currentQuantity,
                  organizationId: subscription.metadata?.organization_id as string,
                });
              }
            }
            
            const orgSubscriptionResult = await upsertOrganizationSubscription({
              subscriptionId: subscription.id,
              customerId: subscription.customer as string,
              isCreateAction: event.type === 'customer.subscription.created',
            });
            
            if (!orgSubscriptionResult?.success) {
              console.error('Failed to upsert organization subscription:', orgSubscriptionResult?.error);
              throw new Error(`Failed to upsert organization subscription: ${JSON.stringify(orgSubscriptionResult?.error)}`);
            }
          } else {
            console.log(`Processing individual subscription: ${subscription.id}`);
            
            const subscriptionResult = await upsertUserSubscription({
              subscriptionId: subscription.id,
              customerId: subscription.customer as string,
              isCreateAction: event.type === 'customer.subscription.created',
            });
            
            if (!subscriptionResult?.success) {
              console.error('Failed to upsert individual subscription:', subscriptionResult?.error);
              throw new Error(`Failed to upsert individual subscription: ${JSON.stringify(subscriptionResult?.error)}`);
            }
          }
          break;
        case 'checkout.session.completed':
          const checkoutSession = event.data.object as Stripe.Checkout.Session;

          if (checkoutSession.mode === 'subscription') {
            const subscriptionId = checkoutSession.subscription;
            console.log(`Processing checkout session ${checkoutSession.id} with subscription ${subscriptionId}`);
            
            // サブスクリプション情報を取得して組織かどうか判定
            const checkoutSubscription = await stripeAdmin.subscriptions.retrieve(subscriptionId as string);
            
            if (isOrganizationSubscription(checkoutSubscription)) {
              console.log(`Processing organization checkout: ${checkoutSession.id}`);
              
              const orgCheckoutResult = await upsertOrganizationSubscription({
                subscriptionId: subscriptionId as string,
                customerId: checkoutSession.customer as string,
                isCreateAction: true,
              });
              
              if (!orgCheckoutResult?.success) {
                console.error('Failed to upsert organization subscription from checkout:', orgCheckoutResult?.error);
                throw new Error(`Failed to upsert organization subscription from checkout: ${JSON.stringify(orgCheckoutResult?.error)}`);
              }
            } else {
              console.log(`Processing individual checkout: ${checkoutSession.id}`);
              
              const checkoutResult = await upsertUserSubscription({
                subscriptionId: subscriptionId as string,
                customerId: checkoutSession.customer as string,
                isCreateAction: true,
              });
              
              if (!checkoutResult?.success) {
                console.error('Failed to upsert individual subscription from checkout:', checkoutResult?.error);
                throw new Error(`Failed to upsert individual subscription from checkout: ${JSON.stringify(checkoutResult?.error)}`);
              }
            }
          }
          break;
        default:
          throw new Error('Unhandled relevant event!');
      }
    } catch (error) {
      console.error(error);
      return Response.json('Webhook handler failed. View your nextjs function logs.', {
        status: 400,
      });
    }
  }
  return Response.json({ received: true });
}
