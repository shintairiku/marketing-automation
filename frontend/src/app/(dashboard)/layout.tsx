import { PropsWithChildren } from 'react';

import { AppLayoutClient } from '@/components/layout/AppLayoutClient';

export default function DashboardLayout({ children }: PropsWithChildren) {
  return <AppLayoutClient>{children}</AppLayoutClient>;
}
