import type { Metadata } from 'next';
import { Toaster as SonnerToaster } from 'sonner';

import { Toaster } from '@/components/ui/toaster';
import { jaJP } from "@clerk/localizations";
import { ClerkProvider } from '@clerk/nextjs';
import { Analytics } from '@vercel/analytics/react';

import '@/styles/globals.css';

export const dynamic = 'force-dynamic';

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
        <body className="font-sans antialiased">
          {children}
          <Toaster />
          <SonnerToaster position="top-right" />
          <Analytics />
        </body>
      </html>
    </ClerkProvider>
  );
}
