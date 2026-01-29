'use client';

import { PropsWithChildren, useEffect } from 'react';
import { usePathname } from 'next/navigation';

import Header from '@/components/display/header';
import Sidebar from '@/components/display/sidebar';
import { Sheet, SheetContent, SheetTitle } from '@/components/ui/sheet';
import { SidebarProvider, useSidebar } from '@/contexts/SidebarContext';
import { cn } from '@/utils/cn';
import { useUser } from '@clerk/nextjs';
import { VisuallyHidden } from '@radix-ui/react-visually-hidden';

function AppLayoutContent({ children }: PropsWithChildren) {
  const pathname = usePathname();
  const { isSignedIn } = useUser();
  const { isSidebarOpen, isMobile, isMobileMenuOpen, setMobileMenuOpen } = useSidebar();

  const showSidebar = isSignedIn && !['/sign-in', '/sign-up', '/user-profile'].includes(pathname);

  // モバイルでページ遷移時にメニューを自動クローズ
  useEffect(() => {
    if (isMobile) {
      setMobileMenuOpen(false);
    }
  }, [pathname, isMobile, setMobileMenuOpen]);

  return (
    <div className="min-h-screen bg-background">
      {showSidebar && (
        <>
          {/* デスクトップ: 固定サイドバー */}
          <div className="hidden md:block fixed left-0 top-0 h-screen z-40">
            <Sidebar />
          </div>

          {/* モバイル: Sheetドロワー */}
          <Sheet open={isMobileMenuOpen} onOpenChange={setMobileMenuOpen}>
            <SheetContent side="left" className="p-0 w-[240px] [&>button]:hidden">
              <VisuallyHidden>
                <SheetTitle>ナビゲーションメニュー</SheetTitle>
              </VisuallyHidden>
              <Sidebar />
            </SheetContent>
          </Sheet>
        </>
      )}
      {showSidebar && <Header />}
      <main className={cn(
        "flex-1 p-3 md:p-5 transition-all duration-300 ease-in-out",
        showSidebar
          ? cn(
              "mt-[45px]",
              isMobile
                ? "ml-0"
                : isSidebarOpen ? "ml-[240px]" : "ml-[64px]"
            )
          : ""
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
