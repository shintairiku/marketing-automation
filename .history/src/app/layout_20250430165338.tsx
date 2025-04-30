import { PropsWithChildren } from 'react';
import type { Metadata } from 'next';
import { Montserrat, Montserrat_Alternates } from 'next/font/google';

import { Toaster } from '@/components/ui/toaster';
import { cn } from '@/utils/cn';
import { Analytics } from '@vercel/analytics/react';

import '@/styles/globals.css';

export const dynamic = 'force-dynamic';

// 山下変更領域------------------------
import { GeistSans, GeistMono } from 'geist-ui';






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

export default function RootLayout({ children }: PropsWithChildren) {
  // return (
  //   <html lang='ja'>
  //     <body className={cn('font-sans antialiased', montserrat.variable, montserratAlternates.variable)}>
  //       {children}
  //       <Toaster />
  //       <Analytics />
  //     </body>
  //   </html>
  // );
  return (
    <html lang="en">
      <body className={`${geistSans.variable} ${geistMono.variable} antialiased`}>
        <div className="flex flex-col h-screen">
          <Header />
          <div className="flex flex-1">
            <Sidebar isExpanded={isExpanded} setIsExpanded={setIsExpanded} />
            <main className="flex-1 py-5 px-10">{children}</main>
          </div>
        </div>
      </body>
    </html>
  );
}
