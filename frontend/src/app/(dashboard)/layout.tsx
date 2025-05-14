import { PropsWithChildren } from 'react';
import { redirect } from 'next/navigation';

import { getSession } from '@/features/account/controllers/get-session';

import { DashboardClient } from './dashboard-client';

export default async function DashboardLayout({ children }: PropsWithChildren) {
  // ユーザーセッションを取得
  const session = await getSession();

  // 認証されていない場合はログインページにリダイレクト
  if (!session) {
    redirect('/login');
  }

  return <DashboardClient>{children}</DashboardClient>;
}