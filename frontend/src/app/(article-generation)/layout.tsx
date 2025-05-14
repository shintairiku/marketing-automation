import { PropsWithChildren } from 'react';
import { redirect } from 'next/navigation';

import { getSession } from '@/features/account/controllers/get-session';

export default async function ArticleGenerationLayout({ children }: PropsWithChildren) {
  // ユーザーセッションを取得
  const session = await getSession();

  // 認証されていない場合はログインページにリダイレクト
  if (!session) {
    redirect('/login');
  }

  return <>{children}</>;
}
