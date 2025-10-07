import { PropsWithChildren } from 'react';

import { LandingFooter } from '@/features/landing/components/footer';
import { LandingHeader } from '@/features/landing/components/header';

export default function MarketingLayout({ children }: PropsWithChildren) {
  return (
    <div className='bg-primary-beige/60 text-foreground'>
      <LandingHeader />
      <main className='pt-16'>{children}</main>
      <LandingFooter />
    </div>
  );
}
