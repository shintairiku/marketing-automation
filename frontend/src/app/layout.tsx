import type { Metadata } from 'next';
import { Montserrat, Montserrat_Alternates } from 'next/font/google';
import { Toaster as SonnerToaster } from 'sonner';

import { Toaster } from '@/components/ui/toaster';
import { cn } from '@/utils/cn';
import { jaJP } from "@clerk/localizations";
import { ClerkProvider } from '@clerk/nextjs';
import { Analytics } from '@vercel/analytics/react';

import '@/styles/globals.css';

export const dynamic = 'force-dynamic';

const montserrat = Montserrat({
  variable: '--font-montserrat',
  subsets: ['latin'],
});

const montserratAlternates = Montserrat_Alternates({
  variable: '--font-montserrat-alternates',
  weight: ['500', '600', '700'],
  subsets: ['latin'],
});

export const metadata: Metadata = {
  title: '新大陸 - AI搭載SEO記事自動生成サービス',
  description: 'AIを活用したSEO記事自動生成サービス。高品質なSEO記事を数分で作成。チャットベースの編集機能で簡単修正。',
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <ClerkProvider localization={jaJP}>
      <html lang='ja'>
        <body className={cn('font-sans antialiased', montserrat.variable, montserratAlternates.variable)}>
          {children}
          <Toaster />
          <SonnerToaster position="top-right" />
          <Analytics />
        </body>
      </html>
    </ClerkProvider>
  );
}
