import { Metadata } from 'next';

import { SignIn } from '@clerk/nextjs';

export const metadata: Metadata = {
  title: 'サインイン - ブログAI',
  description: 'ブログAIアカウントにサインインします。',
};

export default function SignInPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-stone-50 p-4">
      <div className="w-full max-w-md">
        <SignIn path="/sign-in" routing="path" signUpUrl="/sign-up" afterSignInUrl="/blog/new" />
      </div>
    </div>
  );
}
