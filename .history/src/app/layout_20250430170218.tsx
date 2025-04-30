import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: '新大陸 - AI搭載SEO記事自動生成サービス',
  description: 'AIを活用したSEO記事自動生成サービス。高品質なSEO記事を数分で作成。チャットベースの編集機能で簡単修正。',
};

import { ClientLayout } from './client-layout';

export default function RootLayout({ 
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return <ClientLayout>{children}</ClientLayout>;
}
