'use client';

import { useEffect } from 'react';
import Image from 'next/image';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { LogIn, UserPlus } from 'lucide-react';

import { useAuth } from '@clerk/nextjs';

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
      <div className="flex min-h-screen items-center justify-center bg-stone-50">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-stone-400" />
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-stone-50 p-4">
      <div className="w-full max-w-md space-y-8 text-center">
        <div className="flex flex-col items-center">
          <Image src="/logo.png" alt="ブログAI" width={240} height={68} className="mb-3" />
          <p className="text-stone-500">
            AIでブログ記事を自動生成
          </p>
        </div>

        <div className="space-y-4">
          <Link
            href="/sign-in"
            className="flex w-full items-center justify-center gap-3 rounded-lg bg-stone-900 px-6 py-4 text-lg font-semibold text-white transition-colors hover:bg-stone-800"
          >
            <LogIn className="h-5 w-5" />
            ログイン
          </Link>

          <Link
            href="/sign-up"
            className="flex w-full items-center justify-center gap-3 rounded-lg border-2 border-stone-300 px-6 py-4 text-lg font-semibold text-stone-700 transition-colors hover:border-stone-400 hover:bg-stone-100"
          >
            <UserPlus className="h-5 w-5" />
            新規登録
          </Link>
        </div>

        <div className="pt-4 flex items-center justify-center gap-3 text-xs text-stone-400">
          <Link href="/legal/terms" className="hover:text-stone-600 transition-colors">
            利用規約
          </Link>
          <span className="text-stone-300">|</span>
          <Link href="/legal/privacy" className="hover:text-stone-600 transition-colors">
            プライバシーポリシー
          </Link>
        </div>
      </div>
    </div>
  );
}
