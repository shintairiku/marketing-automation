import { Metadata } from 'next';

import { SignUp } from '@clerk/nextjs';

export const metadata: Metadata = {
  title: 'アカウント作成 - 新大陸',
  description: '新大陸の無料アカウントを作成して、AI記事生成を始めましょう。',
};

export default function SignUpPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gradient-to-br from-slate-900 to-slate-800 p-4">
      <div className="w-full max-w-md">
        <SignUp path="/sign-up" routing="path" signInUrl="/sign-in" afterSignUpUrl="/blog/new" />
      </div>
    </div>
  );
} 