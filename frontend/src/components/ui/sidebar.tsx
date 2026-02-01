'use client';

import { ReactNode } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { 
  IoAdd, 
  IoDocumentText, 
  IoHelp,
  IoHome, 
  IoPerson,
  IoSettings, 
  IoStatsChart} from 'react-icons/io5';

import { cn } from '@/utils/cn';

interface SidebarProps {
  className?: string;
}

export function Sidebar({ className }: SidebarProps) {
  const pathname = usePathname();

  const links = [
    {
      href: '/dashboard',
      label: 'ダッシュボード',
      icon: <IoHome size={20} />,
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
    <div className={cn('h-full w-64 border-r border-border bg-background p-4', className)}>
      <div className="mb-8 py-2">
        <Link href="/dashboard" className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-md bg-indigo-600">
            <span className="font-alt text-lg font-bold text-foreground">S</span>
          </div>
          <span className="font-alt text-xl font-semibold text-foreground">新大陸</span>
        </Link>
      </div>

      <nav className="space-y-1">
        {links.map((link) => (
          <Link
            key={link.href}
            href={link.href}
            className={cn(
              'flex items-center gap-3 rounded-md px-3 py-2 transition-colors',
              link.active
                ? 'bg-indigo-600/20 text-indigo-400'
                : 'text-muted-foreground hover:bg-muted hover:text-foreground'
            )}
          >
            <span className={link.active ? 'text-indigo-400' : 'text-muted-foreground'}>{link.icon}</span>
            <span>{link.label}</span>
          </Link>
        ))}
      </nav>

      <div className="mt-auto">
        <div className="mt-10 rounded-md border border-border bg-muted/50 p-4">
          <div className="mb-2 flex items-center gap-2">
            <div className="flex h-6 w-6 items-center justify-center rounded-full bg-indigo-600/30">
              <span className="text-xs font-semibold text-indigo-400">5</span>
            </div>
            <span className="text-sm font-medium text-foreground">記事作成枠数</span>
          </div>
          <div className="h-2 w-full overflow-hidden rounded-full bg-muted">
            <div className="h-full w-1/2 bg-indigo-600"></div>
          </div>
          <div className="mt-1 flex justify-between text-xs text-muted-foreground">
            <span>5/10記事</span>
            <Link href="/settings/billing" className="hover:text-indigo-400 hover:underline">
              プロプランに変更
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}