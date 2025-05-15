'use server';

import { redirect } from 'next/navigation';

import { getOrCreateCustomer } from '@/features/account/controllers/get-or-create-customer';
import { Price } from '@/features/pricing/types';
import { stripeAdmin } from '@/libs/stripe/stripe-admin';
import { getURL } from '@/utils/get-url';
import { auth } from '@clerk/nextjs/server';

export async function createCheckoutAction({ price }: { price: Price }) {
  // 1. Get the user from Clerk
  const authData = await auth();
  const userId = authData.userId;
  const userEmail = authData.sessionClaims?.email as string | undefined;

  if (!userId) {
    return redirect(`${getURL()}/sign-in`);
  }

  if (!userEmail) {
    console.error('User email not found in Clerk session claims. Ensure email is available in session claims.');
    throw Error('Could not get email. Please ensure your email is set in your user profile and available in session claims.');
  }

  // 2. Retrieve or create the customer in Stripe
  const customer = await getOrCreateCustomer({
    userId: userId,
    email: userEmail,
  });

  // 3. Create a checkout session in Stripe
  const checkoutSession = await stripeAdmin.checkout.sessions.create({
    payment_method_types: ['card'],
    billing_address_collection: 'required',
    customer,
    customer_update: {
      address: 'auto',
    },
    line_items: [
      {
        price: price.id,
        quantity: 1,
      },
    ],
    mode: price.type === 'recurring' ? 'subscription' : 'payment',
    allow_promotion_codes: true,
    success_url: `${getURL()}/account`,
    cancel_url: `${getURL()}/`,
  });

  if (!checkoutSession || !checkoutSession.url) {
    throw Error('checkoutSession is not defined');
  }

  // 4. Redirect to checkout url
  redirect(checkoutSession.url);
}
