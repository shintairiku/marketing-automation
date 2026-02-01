import { redirect } from 'next/navigation';

import { auth } from '@clerk/nextjs/server';

export default async function PricingRedirect() {
  const { userId } = await auth();
  if (userId) {
    redirect('/settings/billing');
  }
  redirect('/auth');
}
