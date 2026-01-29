'use client';

import Image from 'next/image';

import { useSidebar } from '@/contexts/SidebarContext';
import { cn } from '@/utils/cn';
import { SignedIn, SignedOut, SignInButton, UserButton } from '@clerk/nextjs';

export default function Header() {
  const { isSidebarOpen } = useSidebar();

  return (
    <header
      className={cn(
        'flex justify-between items-center h-[45px] bg-primary fixed top-0 right-0 z-30 px-3 transition-all duration-300 ease-in-out',
        isSidebarOpen ? 'left-[240px]' : 'left-[64px]'
      )}
    >
      <div className="flex items-center">
        <div className="flex items-center gap-5">
          <Image src="/logo.png" alt="logo" width={32} height={32} />
          <p className="text-white text-lg font-bold">BlogAI</p>
        </div>
      </div>
      <div className="flex items-center gap-4">
        <SignedIn>
          <UserButton afterSignOutUrl="/" />
        </SignedIn>
        <SignedOut>
          <SignInButton />
        </SignedOut>
      </div>
    </header>
  );
}
