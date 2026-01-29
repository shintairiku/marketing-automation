'use client';

import { PropsWithChildren } from 'react';
import { usePathname } from 'next/navigation';

import Header from '@/components/display/header';
import Sidebar from '@/components/display/sidebar';
import { SidebarProvider, useSidebar } from '@/contexts/SidebarContext';
import { cn } from '@/utils/cn';
import { useUser } from '@clerk/nextjs';

function AppLayoutContent({ children }: PropsWithChildren) {
  const pathname = usePathname();
  const { isSignedIn } = useUser();
  const { isSidebarOpen } = useSidebar();

  const showSidebar = isSignedIn && !['/sign-in', '/sign-up', '/user-profile'].includes(pathname);

  return (
    <div className="min-h-screen bg-background">
      {showSidebar && (
        <div className="fixed left-0 top-0 h-screen z-40">
          <Sidebar />
        </div>
      )}
      {showSidebar && <Header />}
      <main className={cn(
        "flex-1 p-5 transition-all duration-300 ease-in-out",
        showSidebar ? cn("mt-[45px]", isSidebarOpen ? "ml-[240px]" : "ml-[64px]") : ""
      )}>
        {children}
      </main>
    </div>
  );
}

export function AppLayoutClient({ children }: PropsWithChildren) {
  return (
    <SidebarProvider>
      <AppLayoutContent>{children}</AppLayoutContent>
    </SidebarProvider>
  );
}
