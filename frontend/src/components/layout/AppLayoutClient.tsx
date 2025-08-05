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
  const { isSubSidebarOpen } = useSidebar();

  const showSidebar = isSignedIn && !['/sign-in', '/sign-up', '/user-profile'].includes(pathname);

  return (
    <div className="min-h-screen bg-background">
      {showSidebar && <Header />}
      <div className="flex mt-[45px]">
        {showSidebar && (
          <div className="fixed left-0 top-[45px] h-[calc(100vh-45px)] z-30">
            <Sidebar />
          </div>
        )}
        <main className={cn(
          "flex-1 p-5 transition-all duration-300 ease-in-out",
          showSidebar ? (isSubSidebarOpen ? "ml-[314px]" : "ml-[128px]") : ""
        )}>
          {children}
        </main>
      </div>
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
