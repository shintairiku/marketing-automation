'use client';

import { PropsWithChildren } from 'react';

import { AppLayoutClient } from '@/components/layout/AppLayoutClient';
import {
  SubscriptionBanner,
  SubscriptionGuard,
  SubscriptionProvider,
} from '@/components/subscription/subscription-guard';

export default function ToolsLayout({ children }: PropsWithChildren) {
  return (
    <SubscriptionProvider>
      <AppLayoutClient>
        <SubscriptionBanner />
        <SubscriptionGuard>
          {children}
        </SubscriptionGuard>
      </AppLayoutClient>
    </SubscriptionProvider>
  );
}
