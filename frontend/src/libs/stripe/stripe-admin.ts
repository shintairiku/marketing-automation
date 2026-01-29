import Stripe from 'stripe';

import { getEnvVar } from '@/utils/get-env-var';

let stripeAdmin: Stripe | null = null;

export const getStripeAdmin = () => {
  if (!stripeAdmin) {
    stripeAdmin = new Stripe(getEnvVar(process.env.STRIPE_SECRET_KEY, 'STRIPE_SECRET_KEY'), {
      // Register this as an official Stripe plugin.
      // https://stripe.com/docs/building-plugins#setappinfo
      appInfo: {
        name: 'UPDATE_THIS_WITH_YOUR_STRIPE_APP_NAME',
        version: '0.1.0',
      },
    });
  }

  return stripeAdmin;
};
