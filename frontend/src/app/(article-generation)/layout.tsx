import { PropsWithChildren } from 'react';
// import { redirect } from 'next/navigation'; // 不要

// import { getSession } from '@/features/account/controllers/get-session'; // 不要

export default async function ArticleGenerationLayout({ children }: PropsWithChildren) {
  // ユーザーセッションを取得 // 不要
  // const session = await getSession(); // 不要

  // 認証されていない場合はログインページにリダイレクト // 不要
  // if (!session) { // 不要
  //   redirect('/login'); // 不要
  // } // 不要

  return <>{children}</>;
}
