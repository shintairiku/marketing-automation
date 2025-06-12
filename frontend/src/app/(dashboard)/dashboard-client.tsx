'use client';

import { PropsWithChildren } from 'react';
import { usePathname } from 'next/navigation';

import Header from '@/components/display/header';
import Sidebar from '@/components/display/sidebar';
import { cn } from '@/utils/cn';
import { useUser } from '@clerk/nextjs';

export function DashboardClient({ children }: PropsWithChildren) {
  const pathname = usePathname();
  const { isSignedIn } = useUser();

  // showSidebarAndHeader はサイドバーの表示制御のみに
  const showSidebar = isSignedIn && !['/sign-in', '/sign-up', '/user-profile'].includes(pathname);

  return (
    <div className="min-h-screen bg-background">
      {showSidebar && <Header />}
      <div className="flex mt-[45px]">
        {showSidebar && (
          <div className="fixed left-0 top-[45px] h-[calc(100vh-45px)]">
            <Sidebar />
          </div>
        )}
        <main className={cn("flex-1", showSidebar ? "ml-[314px]" : "", "p-5")}>
          {children}
        </main>
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