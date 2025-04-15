'use client';

import { PropsWithChildren } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { IoMenu, IoHome, IoSpeedometer } from 'react-icons/io5';

import { AccountMenu } from '@/components/account-menu';
import { Button } from '@/components/ui/button';
import { Sidebar } from '@/components/sidebar';
import { Sheet, SheetContent, SheetTrigger } from '@/components/ui/sheet';
import { cn } from '@/utils/cn';
import { signOut } from '@/app/(auth)/auth-actions';

export default function DashboardLayout({ children }: PropsWithChildren) {
  const pathname = usePathname();
  const showSidebar = !['/login', '/signup'].includes(pathname);

  return (
    <div className="flex h-screen w-full overflow-hidden bg-black">
      {/* デスクトップ - サイドバー */}
      {showSidebar && (
        <div className="hidden lg:block">
          <Sidebar />
        </div>
      )}

      {/* メインコンテンツエリア */}
      <div className="flex h-full flex-1 flex-col overflow-hidden">
        {/* ヘッダー */}
        {showSidebar && (
          <header className="flex h-16 shrink-0 items-center justify-between border-b border-zinc-800 bg-black px-4">
            {/* モバイル - サイドバートグル */}
            <Sheet>
              <SheetTrigger asChild>
                <Button variant="ghost" size="icon" className="lg:hidden">
                  <IoMenu size={24} />
                  <span className="sr-only">メニュー</span>
                </Button>
              </SheetTrigger>
              <SheetContent side="left" className="p-0">
                <Sidebar className="h-full w-full border-0" />
              </SheetContent>
            </Sheet>

            {/* ページタイトル */}
            <div className="lg:hidden">
              <h1 className="text-lg font-semibold text-white">
                {getPageTitle(pathname)}
              </h1>
            </div>

            {/* 右側コントロール */}
            <div className="flex items-center gap-4">
              <Button variant="outline" size="sm" asChild className="hidden sm:flex">
                <Link href="/dashboard">
                  <IoSpeedometer size={16} className="mr-2" /> ダッシュボード
                </Link>
              </Button>
              <Button variant="outline" size="sm" asChild className="hidden sm:flex">
                <Link href="/generate">
                  <IoHome size={16} className="mr-2" /> 記事を生成
                </Link>
              </Button>
              <AccountMenu signOut={signOut} />
            </div>
          </header>
        )}

        {/* スクロール可能なコンテンツエリア */}
        <main className={cn('flex-1 overflow-auto bg-zinc-950 p-0', !showSidebar && 'pt-0')}>
          {children}
        </main>
      </div>
    </div>
  );
}

// パスに基づいてページタイトルを取得する関数
function getPageTitle(pathname: string): string {
  if (pathname === '/dashboard') return 'ダッシュボード';
  if (pathname === '/dashboard/articles') return '記事一覧';
  if (pathname === '/generate') return '新規記事生成';
  if (pathname === '/edit') return '記事編集';
  if (pathname === '/analytics') return '分析';
  if (pathname === '/settings') return '設定';
  if (pathname === '/help') return 'ヘルプ・サポート';
  if (pathname === '/account') return 'アカウント';
  
  // articleのパスにマッチするかチェック
  if (pathname.startsWith('/dashboard/articles/')) return '記事詳細';
  
  return 'SEO記事くん';
}