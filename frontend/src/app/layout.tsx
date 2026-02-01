import type { Metadata } from 'next';
import { Noto_Sans_JP } from 'next/font/google';
import { Toaster as SonnerToaster } from 'sonner';

import { Toaster } from '@/components/ui/toaster';
import { cn } from '@/utils/cn';
import { jaJP } from "@clerk/localizations";
import { ClerkProvider } from '@clerk/nextjs';
import { Analytics } from '@vercel/analytics/react';

import '@/styles/globals.css';

export const dynamic = 'force-dynamic';

const notoSansJP = Noto_Sans_JP({
  variable: '--font-noto-sans-jp',
  subsets: ['latin'],
  weight: ['400', '500', '600', '700'],
});

export const metadata: Metadata = {
  title: 'BlogAI',
  description: 'AIを活用したブログ記事自動生成サービス。あなたのWordPressサイトに最適な記事を生成します。',
  icons: {
    icon: '/favicon.png',
    apple: '/apple-touch-icon.png',
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <ClerkProvider localization={jaJP}>
      <html lang='ja'>
        <body className={cn('font-sans antialiased', notoSansJP.variable)}>
          {children}
          <Toaster />
          <SonnerToaster position="top-right" />
          <Analytics />
        </body>
      </html>
    </ClerkProvider>
  );
}
