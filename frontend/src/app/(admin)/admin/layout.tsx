'use client';

import { PropsWithChildren, useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { Activity, Home, Layers, Menu, MessageSquare, Users, X } from 'lucide-react';

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
  const [sidebarOpen, setSidebarOpen] = useState(false);

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

  // Close sidebar on route change
  useEffect(() => {
    setSidebarOpen(false);
  }, [pathname]);

  const navItems = [
    {
      href: '/admin',
      label: 'Dashboard',
      icon: Home,
    },
    {
      href: '/admin/users',
      label: 'Users',
      icon: Users,
    },
    {
      href: '/admin/blog-usage',
      label: 'Usage',
      icon: Activity,
    },
    {
      href: '/admin/inquiries',
      label: 'Inquiries',
      icon: MessageSquare,
    },
    {
      href: '/admin/plans',
      label: 'Plans',
      icon: Layers,
    },
  ];

  const navContent = (
    <nav className="p-4 space-y-1">
      {navItems.map((item) => {
        const Icon = item.icon;
        const isActive = pathname === item.href;
        return (
          <Link
            key={item.href}
            href={item.href}
            className={cn(
              'flex items-center gap-3 px-4 py-2.5 rounded-lg transition-colors text-sm',
              isActive
                ? 'bg-primary text-primary-foreground'
                : 'text-muted-foreground hover:bg-muted hover:text-foreground'
            )}
          >
            <Icon className="h-4 w-4 shrink-0" />
            <span>{item.label}</span>
          </Link>
        );
      })}
    </nav>
  );

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="sticky top-0 z-30 border-b bg-white">
        <div className="flex items-center justify-between px-4 py-3">
          <div className="flex items-center gap-3">
            {/* Mobile hamburger */}
            <button
              className="md:hidden p-1.5 -ml-1.5 rounded-md hover:bg-muted transition-colors"
              onClick={() => setSidebarOpen(!sidebarOpen)}
              aria-label="Toggle navigation"
            >
              {sidebarOpen ? (
                <X className="h-5 w-5" />
              ) : (
                <Menu className="h-5 w-5" />
              )}
            </button>
            <h1 className="text-lg font-bold">Admin</h1>
          </div>
          <Link href="/blog/new" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
            Back
          </Link>
        </div>
      </header>

      <div className="flex relative">
        {/* Mobile overlay */}
        {sidebarOpen && (
          <div
            className="fixed inset-0 z-20 bg-black/30 md:hidden"
            onClick={() => setSidebarOpen(false)}
          />
        )}

        {/* Sidebar - desktop: always visible, mobile: slide-in overlay */}
        <aside
          className={cn(
            'fixed md:sticky top-[49px] z-20 h-[calc(100vh-49px)] w-64 border-r bg-white transition-transform duration-200 ease-in-out overflow-y-auto',
            sidebarOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'
          )}
        >
          {navContent}
        </aside>

        {/* Main Content */}
        <main className="flex-1 min-w-0 p-4 md:p-6">
          {children}
        </main>
      </div>
    </div>
  );
}
