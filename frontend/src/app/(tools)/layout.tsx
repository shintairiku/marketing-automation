import { PropsWithChildren } from 'react';

import { AppLayoutClient } from '@/components/layout/AppLayoutClient';

export default function ToolsLayout({ children }: PropsWithChildren) {
  return <AppLayoutClient>{children}</AppLayoutClient>;
}
