'use client';

import Image from 'next/image';
import { LuMenu } from 'react-icons/lu';

import { useSidebar } from '@/contexts/SidebarContext';
import { cn } from '@/utils/cn';
import { SignedIn, SignedOut, SignInButton, UserButton } from '@clerk/nextjs';

export default function Header() {
  const { isSidebarOpen, isMobile, toggleMobileMenu } = useSidebar();

  return (
    <header
      className={cn(
        'flex justify-between items-center h-[45px] bg-primary fixed top-0 right-0 z-30 px-3 transition-all duration-300 ease-in-out',
        isMobile
          ? 'left-0'
          : isSidebarOpen ? 'left-[240px]' : 'left-[64px]'
      )}
    >
      <div className="flex items-center">
        {/* ハンバーガーメニュー - モバイルのみ */}
        <button
          onClick={toggleMobileMenu}
          className="md:hidden p-1.5 rounded-md text-white/80 hover:text-white hover:bg-white/10 transition-colors mr-2"
          aria-label="メニューを開く"
        >
          <LuMenu size={20} />
        </button>
        <div className="flex items-center gap-5">
          <Image src="/logo.png" alt="logo" width={32} height={32} />
          <p className="hidden sm:block text-white text-lg font-bold">BlogAI</p>
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
