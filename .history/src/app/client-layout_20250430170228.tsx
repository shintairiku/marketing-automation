'use client'

import { useState } from 'react';
import { GeistSans } from 'geist/font'
import { GeistMono } from 'geist/font/mono'
import Header from '@/components/display/header';
import Sidebar from '@/components/display/sidebar';

export function ClientLayout({ 
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const [isExpanded, setIsExpanded] = useState(true);

  return (
    <html lang="ja">
      <body className={`${GeistSans.variable} ${GeistMono.variable} antialiased`}>
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