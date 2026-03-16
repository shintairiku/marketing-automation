'use client';

import { PropsWithChildren, useEffect } from 'react';
import { usePathname } from 'next/navigation';
import { LuMenu } from 'react-icons/lu';

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

          {/* モバイル: フローティングハンバーガーボタン */}
          <button
            onClick={() => setMobileMenuOpen(true)}
            className="md:hidden fixed top-3 left-3 z-30 p-2 rounded-lg bg-white border border-stone-200 shadow-sm text-stone-600 hover:bg-stone-50 transition-colors"
            aria-label="メニューを開く"
          >
            <LuMenu size={20} />
          </button>
        </>
      )}
      <main className={cn(
        "flex-1 p-3 md:p-5 transition-all duration-300 ease-in-out",
        showSidebar
          ? isMobile
            ? "pt-14"
            : isSidebarOpen ? "ml-[240px]" : "ml-[64px]"
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
