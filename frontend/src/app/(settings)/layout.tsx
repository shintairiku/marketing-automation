'use client';

import { PropsWithChildren } from 'react';

import { AppLayoutClient } from '@/components/layout/AppLayoutClient';
import {
  SubscriptionBanner,
  SubscriptionProvider,
} from '@/components/subscription/subscription-guard';

export default function SettingsLayout({ children }: PropsWithChildren) {
  return (
    <SubscriptionProvider>
      <AppLayoutClient>
        <SubscriptionBanner />
        {children}
      </AppLayoutClient>
    </SubscriptionProvider>
  );
}
