import { Metadata } from 'next';
import Link from 'next/link';

import { SignUp } from '@clerk/nextjs';

export const metadata: Metadata = {
  title: 'アカウント作成 - ブログAI',
  description: 'ブログAIの無料アカウントを作成して、AI記事生成を始めましょう。',
};

export default function SignUpPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-stone-50 p-4">
      <div className="w-full max-w-md space-y-4">
        <SignUp path="/sign-up" routing="path" signInUrl="/sign-in" afterSignUpUrl="/blog/new" />
        <p className="text-center text-xs text-stone-500 leading-relaxed">
          アカウントを作成することで、<Link href="/legal/terms" target="_blank" className="underline hover:text-stone-700">利用規約</Link>および<Link href="/legal/privacy" target="_blank" className="underline hover:text-stone-700">プライバシーポリシー</Link>に同意したものとみなされます。
        </p>
      </div>
    </div>
  );
}
