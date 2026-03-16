'use client';

import { PropsWithChildren, useEffect } from 'react';
import { useRouter } from 'next/navigation';

import { AppLayoutClient } from '@/components/layout/AppLayoutClient';
import {
  SubscriptionBanner,
  SubscriptionGuard,
  SubscriptionProvider,
} from '@/components/subscription/subscription-guard';
import { hasPrivilegedRole } from '@/lib/subscription';
import { useUser } from '@clerk/nextjs';

export default function DashboardLayout({ children }: PropsWithChildren) {
  const { user, isLoaded } = useUser();
  const router = useRouter();

  // 非特権ユーザーは /blog/new にリダイレクト（クライアントサイドフォールバック）
  useEffect(() => {
    if (isLoaded && user) {
      if (!hasPrivilegedRole(user.publicMetadata as Record<string, unknown>)) {
        router.replace('/blog/new');
      }
    }
  }, [isLoaded, user, router]);

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
