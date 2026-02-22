'use client';

import { PropsWithChildren, useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import {
  Activity,
  ArrowLeft,
  Home,
  Layers,
  Menu,
  MessageSquare,
  PanelLeftClose,
  PanelLeftOpen,
  Users,
} from 'lucide-react';

import { Button } from '@/components/ui/button';
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { cn } from '@/utils/cn';
import { useUser } from '@clerk/nextjs';

const ADMIN_EMAIL_DOMAIN = '@shintairiku.jp';

function isAdminEmail(email: string | undefined | null): boolean {
  if (!email) return false;
  return email.toLowerCase().endsWith(ADMIN_EMAIL_DOMAIN.toLowerCase());
}

const navItems = [
  { href: '/admin', label: 'ダッシュボード', icon: Home },
  { href: '/admin/users', label: 'ユーザー管理', icon: Users },
  { href: '/admin/blog-usage', label: '記事別Usage', icon: Activity },
  { href: '/admin/inquiries', label: 'お問い合わせ', icon: MessageSquare },
  { href: '/admin/plans', label: 'プラン設定', icon: Layers },
];

export default function AdminLayout({ children }: PropsWithChildren) {
  const pathname = usePathname();
  const router = useRouter();
  const { isLoaded, user } = useUser();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem('admin-sidebar-collapsed');
    if (stored === 'true') setCollapsed(true);
  }, []);

  useEffect(() => {
    if (!isLoaded) return;
    if (!user) {
      router.push('/sign-in');
      return;
    }
    const userEmail =
      user.primaryEmailAddress?.emailAddress ||
      user.emailAddresses?.[0]?.emailAddress;
    if (!isAdminEmail(userEmail)) {
      router.push('/');
    }
  }, [isLoaded, user, router]);

  useEffect(() => {
    setMobileOpen(false);
  }, [pathname]);

  const toggleCollapsed = () => {
    setCollapsed((prev) => {
      const next = !prev;
      localStorage.setItem('admin-sidebar-collapsed', String(next));
      return next;
    });
  };

  const isActive = (href: string) => {
    if (href === '/admin') return pathname === '/admin';
    return pathname.startsWith(href);
  };

  const renderNavLink = (
    item: (typeof navItems)[0],
    showLabel: boolean,
    withTooltip: boolean
  ) => {
    const Icon = item.icon;
    const active = isActive(item.href);
    const link = (
      <Link
        href={item.href}
        className={cn(
          'flex items-center gap-3 rounded-lg transition-colors text-sm',
          showLabel ? 'px-3 py-2.5' : 'justify-center p-2.5',
          active
            ? 'bg-primary text-primary-foreground'
            : 'text-muted-foreground hover:bg-muted hover:text-foreground'
        )}
      >
        <Icon className="h-4 w-4 shrink-0" />
        {showLabel && <span>{item.label}</span>}
      </Link>
    );

    if (withTooltip && !showLabel) {
      return (
        <Tooltip key={item.href}>
          <TooltipTrigger asChild>{link}</TooltipTrigger>
          <TooltipContent side="right" sideOffset={8}>
            {item.label}
          </TooltipContent>
        </Tooltip>
      );
    }

    return <div key={item.href}>{link}</div>;
  };

  return (
    <TooltipProvider delayDuration={100}>
      <div className="min-h-screen bg-background flex">
        {/* ── Desktop Sidebar (full height) ── */}
        <aside
          className={cn(
            'hidden md:flex flex-col fixed inset-y-0 left-0 z-30 border-r bg-white transition-[width] duration-200 ease-in-out overflow-hidden',
            collapsed ? 'w-[60px]' : 'w-56'
          )}
        >
          {/* Sidebar header — toggle + title */}
          <div
            className={cn(
              'flex items-center h-12 border-b shrink-0',
              collapsed ? 'justify-center px-2' : 'justify-between px-3'
            )}
          >
            {!collapsed && (
              <span className="text-sm font-bold tracking-tight truncate">
                管理画面
              </span>
            )}
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 shrink-0 text-muted-foreground hover:text-foreground"
                  onClick={toggleCollapsed}
                >
                  {collapsed ? (
                    <PanelLeftOpen className="h-4 w-4" />
                  ) : (
                    <PanelLeftClose className="h-4 w-4" />
                  )}
                </Button>
              </TooltipTrigger>
              <TooltipContent side="right" sideOffset={8}>
                {collapsed ? 'サイドバーを開く' : 'サイドバーを閉じる'}
              </TooltipContent>
            </Tooltip>
          </div>

          {/* Nav links */}
          <nav className="flex-1 p-2 space-y-0.5 overflow-y-auto">
            {navItems.map((item) => renderNavLink(item, !collapsed, true))}
          </nav>

          {/* Bottom — back to app */}
          <div className="border-t p-2">
            {collapsed ? (
              <Tooltip>
                <TooltipTrigger asChild>
                  <Link
                    href="/blog/new"
                    className="flex justify-center p-2.5 rounded-lg text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
                  >
                    <ArrowLeft className="h-4 w-4" />
                  </Link>
                </TooltipTrigger>
                <TooltipContent side="right" sideOffset={8}>
                  アプリに戻る
                </TooltipContent>
              </Tooltip>
            ) : (
              <Link
                href="/blog/new"
                className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
              >
                <ArrowLeft className="h-4 w-4 shrink-0" />
                <span>アプリに戻る</span>
              </Link>
            )}
          </div>
        </aside>

        {/* ── Mobile top bar ── */}
        <div className="fixed top-0 inset-x-0 z-30 md:hidden border-b bg-white">
          <div className="flex items-center gap-2 px-3 h-11">
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              onClick={() => setMobileOpen(true)}
            >
              <Menu className="h-4 w-4" />
              <span className="sr-only">メニューを開く</span>
            </Button>
            <span className="text-sm font-bold">管理画面</span>
          </div>
        </div>

        {/* ── Mobile Sidebar (Sheet) ── */}
        <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
          <SheetContent side="left" className="w-64 p-0">
            <SheetHeader className="px-4 pt-4 pb-2 border-b">
              <SheetTitle className="text-sm font-bold">管理メニュー</SheetTitle>
            </SheetHeader>
            <nav className="p-2 space-y-0.5">
              {navItems.map((item) => renderNavLink(item, true, false))}
            </nav>
            <div className="border-t p-2 mt-auto">
              <Link
                href="/blog/new"
                className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
              >
                <ArrowLeft className="h-4 w-4 shrink-0" />
                <span>アプリに戻る</span>
              </Link>
            </div>
          </SheetContent>
        </Sheet>

        {/* ── Main Content ── */}
        <main
          className={cn(
            'flex-1 min-w-0 transition-[margin-left] duration-200 ease-in-out',
            'pt-11 md:pt-0',
            'p-4 md:p-6',
            collapsed ? 'md:ml-[60px]' : 'md:ml-56'
          )}
        >
          {children}
        </main>
      </div>
    </TooltipProvider>
  );
}
