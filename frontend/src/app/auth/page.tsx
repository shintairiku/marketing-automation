'use client';

import { useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';

import { useAuth } from '@clerk/nextjs';
import { LogIn, UserPlus } from 'lucide-react';

export default function AuthPage() {
  const { isLoaded, isSignedIn } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (isLoaded && isSignedIn) {
      router.replace('/blog/new');
    }
  }, [isLoaded, isSignedIn, router]);

  if (!isLoaded || isSignedIn) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-slate-900 to-slate-800">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-white" />
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gradient-to-br from-slate-900 to-slate-800 p-4">
      <div className="w-full max-w-md space-y-8 text-center">
        <div>
          <h1 className="text-3xl font-bold text-white">ブログAI</h1>
          <p className="mt-2 text-slate-400">
            AIでブログ記事を自動生成
          </p>
        </div>

        <div className="space-y-4">
          <Link
            href="/sign-in"
            className="flex w-full items-center justify-center gap-3 rounded-lg bg-white px-6 py-4 text-lg font-semibold text-slate-900 transition-colors hover:bg-slate-100"
          >
            <LogIn className="h-5 w-5" />
            ログイン
          </Link>

          <Link
            href="/sign-up"
            className="flex w-full items-center justify-center gap-3 rounded-lg border-2 border-slate-500 px-6 py-4 text-lg font-semibold text-white transition-colors hover:border-white hover:bg-white/10"
          >
            <UserPlus className="h-5 w-5" />
            新規登録
          </Link>
        </div>
      </div>
    </div>
  );
}
