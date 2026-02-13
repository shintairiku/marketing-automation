import { POST as handleSubscriptionWebhook } from '../subscription/webhook/route';

export async function POST(req: Request) {
  console.warn('[Webhook] /api/webhooks is deprecated. Use /api/subscription/webhook instead.');
  return handleSubscriptionWebhook(req);
}
