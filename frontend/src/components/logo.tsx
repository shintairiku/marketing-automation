import Image from 'next/image';

import { cn } from '@/utils/cn';

export function Logo({ className, variant = 'dark' }: { className?: string; variant?: 'dark' | 'white' }) {
  const src = variant === 'white' ? '/logo-white.png' : '/logo.png';
  return (
    <div className={cn('flex items-center', className)}>
      <Image src={src} alt="ブログAI" width={113} height={32} />
    </div>
  );
}
