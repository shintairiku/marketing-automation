'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { IoSpeedometer } from 'react-icons/io5';

import { Button } from '@/components/ui/button';
import { cn } from '@/utils/cn';
import { SignedIn, SignedOut, SignInButton, SignUpButton, UserButton } from '@clerk/nextjs';

export function LandingHeader() {
  const [isVisible, setIsVisible] = useState(true);
  const [lastScrollY, setLastScrollY] = useState(0);

  useEffect(() => {
    const handleScroll = () => {
      const currentScrollY = window.scrollY;

      if (currentScrollY < 100) {
        setIsVisible(true);
      } else if (currentScrollY > lastScrollY) {
        setIsVisible(false);
      } else {
        setIsVisible(true);
      }

      setLastScrollY(currentScrollY);
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, [lastScrollY]);

  return (
    <header
      className={cn(
        'fixed left-0 top-0 z-50 w-full border-b border-white/10 bg-primary-dark/95 backdrop-blur transition-transform duration-300',
        isVisible ? 'translate-y-0' : '-translate-y-full',
      )}
    >
      <div className='mx-auto flex h-16 w-full max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8'>
        <Link href='/' className='flex items-center gap-3 text-white'>
          <span className='text-lg font-bold sm:text-xl'>ブログAI</span>
        </Link>

        <div className='flex items-center gap-3'>
          <SignedIn>
            <Button
              asChild
              size='sm'
              className='hidden items-center gap-2 border-white/30 bg-primary-green px-4 text-white hover:bg-primary-green/90 sm:flex'
            >
              <Link href='/dashboard'>
                <IoSpeedometer size={16} />
                <span>ダッシュボード</span>
              </Link>
            </Button>
            <UserButton afterSignOutUrl='/' />
          </SignedIn>

          <SignedOut>
            <SignInButton mode='modal'>
              <Button
                size='sm'
                variant='outline'
                className='border border-dashed border-white/60 bg-transparent px-6 font-semibold text-white transition-colors hover:bg-white hover:text-primary-dark'
              >
                ログイン
              </Button>
            </SignInButton>
            <SignUpButton mode='modal'>
              <Button
                size='sm'
                className='bg-primary-green px-6 font-semibold text-white hover:bg-primary-green/90'
              >
                無料で始める
              </Button>
            </SignUpButton>
          </SignedOut>
        </div>
      </div>
    </header>
  );
}
