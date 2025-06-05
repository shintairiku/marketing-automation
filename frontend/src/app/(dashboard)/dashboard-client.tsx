'use client';

import { PropsWithChildren, useState } from 'react';
// import Link from 'next/link'; // Link はヘッダー内で使われなくなったため削除
import { usePathname } from 'next/navigation';
import {
  // IoAdd, // IoAdd はヘッダー内で使われなくなったため削除
  // IoClose, // IoClose はヘッダー・サイドバー内で使われなくなったため削除
  // IoDocumentText,
  // IoHelp,
  // IoHome,
  IoMenu, // モバイルのシートトリガー用に残す
  // IoNotifications, // IoNotifications はヘッダー内で使われなくなったため削除
  // IoPerson,
  // IoSearchOutline, // IoSearchOutline はヘッダー内で使われなくなったため削除
  // IoSettings,
  // IoSpeedometer,
  // IoStatsChart
} from 'react-icons/io5';

import Header from '@/components/display/header'; // 新しいヘッダーをインポート
// import { SignedIn, UserButton, useUser } from '@clerk/nextjs'; // Clerk関連は新しいヘッダーにないので一旦コメントアウト（必要なら復活）
import Sidebar from '@/components/display/sidebar';
import { Button } from '@/components/ui/button';
// import { Input } from '@/components/ui/input'; // Input はヘッダー内で使われなくなったため削除
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from '@/components/ui/sheet';
import { cn } from '@/utils/cn';
import { useUser } from '@clerk/nextjs'; // useUser は showSidebarAndHeader で使用するため残す

export function DashboardClient({ children }: PropsWithChildren) {
  const pathname = usePathname();
  const { isSignedIn } = useUser();
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  // const [isSearchExpanded, setIsSearchExpanded] = useState(false); // isSearchExpanded は使われなくなったため削除

  // showSidebarAndHeader はサイドバーの表示制御のみに
  const showSidebar = isSignedIn && !['/sign-in', '/sign-up', '/user-profile'].includes(pathname);

  // toggleSidebar はデスクトップホバー用（Sidebar内部で処理）と、将来的なピン留めボタン用に残す
  const toggleSidebar = () => {
    setIsSidebarCollapsed(!isSidebarCollapsed);
  };

  return (
    <div className="flex h-screen w-full flex-col overflow-hidden bg-background">
      {/* 新しい共通ヘッダーを配置 */}
      {showSidebar && <Header />}

      <div className="flex flex-1 overflow-hidden">
        {/* デスクトップ - サイドバー */}
        {showSidebar && (
          <div className={cn(
            "hidden lg:block transition-all duration-300 ease-in-out",
          )}>
            <Sidebar />
          </div>
        )}

        {/* メインコンテンツエリア */}
        <div className="flex h-full flex-1 flex-col overflow-hidden">
          {/* 旧ヘッダーは削除 */}
          
          {/* モバイル用サイドバートグルをヘッダーに含めるか検討したが、現状のHeaderコンポーネントにはないので、
              dashboard-client に残す場合は、Headerコンポーネントとデザイン調整が必要。
              一旦、モバイルのSheetTriggerはメインコンテンツエリアの直前に配置する。
              理想的にはHeaderコンポーネントがモバイルトグルも持つべき。
           */}
          {showSidebar && (
             <div className="lg:hidden p-4 border-b border-border bg-background flex items-center">
                <Sheet>
                    <SheetTrigger asChild>
                    <Button variant="ghost" size="icon">
                        <IoMenu size={24} />
                        <span className="sr-only">メニュー</span>
                    </Button>
                    </SheetTrigger>
                    <SheetContent side="left" className="p-0">
                    <SheetHeader className="sr-only">
                        <SheetTitle>ナビゲーションメニュー</SheetTitle>
                    </SheetHeader>
                    <Sidebar />
                    </SheetContent>
                </Sheet>
                {/* モバイル時のページタイトルなどもここに表示するか、Headerコンポーネント側でレスポンシブ対応するか検討 */}
             </div>
          )}

          {/* スクロール可能なコンテンツエリア */}
          <main className={cn('flex-1 overflow-auto bg-background p-6', !showSidebar && 'pt-0')}>
            <div className="mx-auto max-w-7xl">
              {children}
            </div>
          </main>
        </div>
      </div>
    </div>
  );
}

// パスに基づいてページタイトルを取得する関数 (旧ヘッダーで使っていたもの)
// 新しいヘッダーまたは別の場所で必要なら再利用
/*
function getPageTitle(pathname: string): string {
  if (pathname === '/dashboard') return 'ダッシュボード';
  if (pathname === '/dashboard/articles') return '記事一覧';
  if (pathname === '/generate') return '新規記事生成';
  if (pathname === '/edit') return '記事編集';
  if (pathname === '/analytics') return '分析';
  if (pathname === '/settings') return 'アプリ設定';
  if (pathname === '/help') return 'ヘルプ・サポート';
  if (pathname === '/account') return 'アカウント概要';
  if (pathname.startsWith('/user-profile')) return 'アカウント設定';

  if (pathname.startsWith('/dashboard/articles/')) return '記事詳細';

  return '新大陸';
}
*/