// Clerkのユーザープロファイルページ (アカウント設定、サブスクリプション管理など)
import { Metadata } from 'next';

import { UserProfile } from '@clerk/nextjs';

export const metadata: Metadata = {
  title: 'アカウント設定 - ブログAI',
  description: 'アカウント情報、セキュリティ設定、サブスクリプションプランの管理を行います。',
};

export default function UserProfilePage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-start bg-background p-4 pt-10 md:pt-16">
      <div className="w-full max-w-4xl">
        <UserProfile path="/user-profile" routing="path">
          {/* Clerk UserProfileコンポーネントはサブスクリプション管理機能も内包できます */}
          {/* Stripe連携がClerk側で設定されていれば、ここに表示される可能性があります */}
          {/* 必要に応じて appearance プロパティでスタイルを調整できます */}
          {/* <UserProfile.Page label="サブスクリプション" url="subscriptions" labelIcon={<CreditCard />}>
            <YourCustomSubscriptionComponent />
          </UserProfile.Page> */}
        </UserProfile>
      </div>
    </div>
  );
} 