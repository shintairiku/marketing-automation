'use client';

import { PropsWithChildren, useEffect } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { Activity, Home, Layers, MessageSquare, Users } from 'lucide-react';

import { cn } from '@/utils/cn';
import { useUser } from '@clerk/nextjs';

const ADMIN_EMAIL_DOMAIN = '@shintairiku.jp';

function isAdminEmail(email: string | undefined | null): boolean {
  if (!email) return false;
  return email.toLowerCase().endsWith(ADMIN_EMAIL_DOMAIN.toLowerCase());
}

export default function AdminLayout({ children }: PropsWithChildren) {
  const pathname = usePathname();
  const router = useRouter();
  const { isLoaded, user } = useUser();

  useEffect(() => {
    if (!isLoaded) return;

    if (!user) {
      router.push('/sign-in');
      return;
    }

    // Check if user has admin email domain
    const userEmail = user.primaryEmailAddress?.emailAddress || 
                     user.emailAddresses?.[0]?.emailAddress;
    
    if (!isAdminEmail(userEmail)) {
      console.log('[ADMIN_LAYOUT] Access denied - email does not match admin domain:', userEmail);
      router.push('/');
      return;
    }

    console.log('[ADMIN_LAYOUT] Access granted - email matches admin domain:', userEmail);
  }, [isLoaded, user, router]);

  const navItems = [
    {
      href: '/admin',
      label: 'ダッシュボード',
      icon: Home,
    },
    {
      href: '/admin/users',
      label: 'ユーザー一覧',
      icon: Users,
    },
    {
      href: '/admin/blog-usage',
      label: '記事別Usage',
      icon: Activity,
    },
    {
      href: '/admin/inquiries',
      label: 'お問い合わせ',
      icon: MessageSquare,
    },
    {
      href: '/admin/plans',
      label: 'プラン設定',
      icon: Layers,
    },
  ];

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b bg-white">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <h1 className="text-xl font-bold">管理者ページ</h1>
            <Link href="/dashboard" className="text-sm text-muted-foreground hover:text-foreground">
              通常ページに戻る
            </Link>
          </div>
        </div>
      </header>

      <div className="flex">
        {/* Sidebar */}
        <aside className="w-64 border-r bg-white min-h-[calc(100vh-73px)]">
          <nav className="p-4 space-y-2">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    'flex items-center gap-3 px-4 py-2 rounded-lg transition-colors',
                    isActive
                      ? 'bg-primary text-primary-foreground'
                      : 'text-muted-foreground hover:bg-muted hover:text-foreground'
                  )}
                >
                  <Icon className="w-5 h-5" />
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </nav>
        </aside>

        {/* Main Content */}
        <main className="flex-1 p-6">
          {children}
        </main>
      </div>
    </div>
  );
}
