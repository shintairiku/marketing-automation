'use client';

import { PropsWithChildren, useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { 
  IoMenu, 
  IoClose, 
  IoHome, 
  IoDocumentText, 
  IoAdd, 
  IoSettings, 
  IoHelp,
  IoStatsChart,
  IoPerson,
  IoSpeedometer,
  IoNotifications,
  IoSearchOutline
} from 'react-icons/io5';

import { AccountMenu } from '@/components/account-menu';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Sheet, SheetContent, SheetTrigger } from '@/components/ui/sheet';
import { cn } from '@/utils/cn';
import { signOut } from '@/app/(auth)/auth-actions';

export default function DashboardLayout({ children }: PropsWithChildren) {
  const pathname = usePathname();
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [isSearchExpanded, setIsSearchExpanded] = useState(false);

  // 現在のページがログインや登録ページでない場合にのみサイドバーを表示
  const showSidebar = !['/login', '/signup'].includes(pathname);

  const toggleSidebar = () => {
    setIsSidebarCollapsed(!isSidebarCollapsed);
  };

  return (
    <div className="flex h-screen w-full overflow-hidden bg-zinc-950">
      {/* デスクトップ - サイドバー */}
      {showSidebar && (
        <div className={cn(
          "hidden lg:block transition-all duration-300 ease-in-out",
          isSidebarCollapsed ? "w-20" : "w-64"
        )}>
          <ImprovedSidebar collapsed={isSidebarCollapsed} onToggle={toggleSidebar} />
        </div>
      )}

      {/* メインコンテンツエリア */}
      <div className="flex h-full flex-1 flex-col overflow-hidden">
        {/* ヘッダー */}
        {showSidebar && (
          <header className="flex h-16 shrink-0 items-center justify-between border-b border-zinc-800 bg-black px-4">
            {/* モバイル - サイドバートグル */}
            <div className="flex items-center gap-2">
              <Sheet>
                <SheetTrigger asChild>
                  <Button variant="ghost" size="icon" className="lg:hidden">
                    <IoMenu size={24} />
                    <span className="sr-only">メニュー</span>
                  </Button>
                </SheetTrigger>
                <SheetContent side="left" className="p-0">
                  <ImprovedSidebar className="h-full w-full border-0" collapsed={false} />
                </SheetContent>
              </Sheet>

              {/* ページタイトル */}
              <h1 className="lg:text-xl text-lg font-semibold text-white">
                {getPageTitle(pathname)}
              </h1>
            </div>

            {/* 右側コントロールエリア */}
            <div className="flex items-center gap-4">
              {/* 検索フォーム - デスクトップのみ */}
              <div className={cn(
                "hidden md:flex items-center bg-zinc-900 rounded-md border border-zinc-800 px-3 transition-all",
                isSearchExpanded ? "w-64" : "w-auto"
              )}>
                <Input
                  type="text"
                  placeholder="検索..."
                  className="border-0 bg-transparent"
                  onFocus={() => setIsSearchExpanded(true)}
                  onBlur={() => setIsSearchExpanded(false)}
                />
                <IoSearchOutline className="text-gray-400" />
              </div>

              {/* 生成ボタン */}
              <Button variant="sexy" size="sm" asChild>
                <Link href="/generate">
                  <IoAdd size={16} className="mr-2" /> 記事生成
                </Link>
              </Button>

              {/* 通知ボタン */}
              <Button variant="ghost" size="icon" className="relative">
                <IoNotifications size={22} />
                <span className="absolute top-0 right-0 flex h-2 w-2 rounded-full bg-indigo-500"></span>
              </Button>
              
              {/* アカウントメニュー */}
              <AccountMenu signOut={signOut} />
            </div>
          </header>
        )}

        {/* スクロール可能なコンテンツエリア */}
        <main className={cn('flex-1 overflow-auto bg-zinc-950 p-6', !showSidebar && 'pt-0')}>
          <div className="mx-auto max-w-7xl">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}

export function ImprovedSidebar({ 
  className,
  collapsed = false,
  onToggle
}: { 
  className?: string;
  collapsed?: boolean;
  onToggle?: () => void;
}) {
  const pathname = usePathname();

  const links = [
    {
      href: '/dashboard',
      label: 'ダッシュボード',
      icon: <IoSpeedometer size={20} />,
      active: pathname === '/dashboard',
    },
    {
      href: '/dashboard/articles',
      label: '記事一覧',
      icon: <IoDocumentText size={20} />,
      active: pathname === '/dashboard/articles' || pathname.startsWith('/dashboard/articles/'),
    },
    {
      href: '/generate',
      label: '新規記事生成',
      icon: <IoAdd size={20} />,
      active: pathname === '/generate',
    },
    {
      href: '/analytics',
      label: '分析',
      icon: <IoStatsChart size={20} />,
      active: pathname === '/analytics',
    },
    {
      href: '/settings',
      label: '設定',
      icon: <IoSettings size={20} />,
      active: pathname === '/settings',
    },
    {
      href: '/account',
      label: 'アカウント',
      icon: <IoPerson size={20} />,
      active: pathname === '/account',
    },
    {
      href: '/help',
      label: 'ヘルプ・サポート',
      icon: <IoHelp size={20} />,
      active: pathname === '/help',
    },
  ];

  return (
    <div className={cn('h-full border-r border-zinc-800 bg-black', className)}>
      <div className="flex h-16 items-center justify-between border-b border-zinc-800 px-4">
        <Link href="/dashboard" className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-md bg-indigo-600">
            <span className="font-alt text-lg font-bold text-white">S</span>
          </div>
          {!collapsed && <span className="font-alt text-xl font-semibold text-white">SEO記事くん</span>}
        </Link>
        
        {/* コラプスボタン - デスクトップのみ */}
        {onToggle && (
          <Button 
            variant="ghost" 
            size="icon" 
            onClick={onToggle} 
            className="hidden lg:flex"
          >
            {collapsed ? <IoMenu size={20} /> : <IoClose size={20} />}
          </Button>
        )}
      </div>

      <div className="h-[calc(100%-4rem)] flex flex-col justify-between p-4">
        <nav className="space-y-1">
          {links.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className={cn(
                'flex items-center gap-3 rounded-md px-3 py-2 transition-colors',
                link.active
                  ? 'bg-indigo-600/20 text-indigo-400'
                  : 'text-gray-400 hover:bg-zinc-900 hover:text-white'
              )}
            >
              <span className={link.active ? 'text-indigo-400' : 'text-gray-400'}>
                {link.icon}
              </span>
              {!collapsed && <span>{link.label}</span>}
            </Link>
          ))}
        </nav>

        <div className="mt-auto">
          <div className={cn(
            "rounded-lg border border-zinc-800 bg-zinc-900/50 p-4",
            collapsed && "p-2"
          )}>
            <div className="mb-2 flex items-center gap-2">
              <div className="flex h-6 w-6 items-center justify-center rounded-full bg-indigo-600/30">
                <span className="text-xs font-semibold text-indigo-400">5</span>
              </div>
              {!collapsed && <span className="text-sm font-medium text-white">記事作成枠数</span>}
            </div>
            <div className="h-2 w-full overflow-hidden rounded-full bg-zinc-800">
              <div className="h-full w-1/2 bg-indigo-600"></div>
            </div>
            {!collapsed && (
              <div className="mt-1 flex justify-between text-xs text-gray-400">
                <span>5/10記事</span>
                <Link href="/pricing" className="hover:text-indigo-400 hover:underline">
                  プロプランに変更
                </Link>
              </div>
            )}
          </div>
        </div>
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