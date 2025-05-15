import { Metadata } from 'next';
import { redirect } from 'next/navigation';

import { UserProfile } from '@clerk/nextjs';
// import { getSession } from '@/features/account/controllers/get-session'; // Clerkで管理
// import { getSubscription } from '@/features/account/controllers/get-subscription'; // Clerk UserProfileで管理
// import { PricingCard } from '@/features/pricing/components/price-card'; // Clerk UserProfileで管理
// import { getProducts } from '@/features/pricing/controllers/get-products'; // Clerk UserProfileで管理
// import { Price, ProductWithPrices } from '@/features/pricing/types'; // Clerk UserProfileで管理

export const metadata: Metadata = {
  title: 'アカウント設定 - 新大陸',
  description: 'アカウント情報、セキュリティ設定、サブスクリプションプランの管理を行います。',
};

export default async function AccountPage() {
  // Clerkの<AuthLoading>, <SignedIn>, <SignedOut> や auth() で認証状態をハンドリングするため、
  // ここでのセッションチェックはClerkのmiddlewareやルート保護に委ねるのが一般的。
  // このページ自体を保護ルートに設定済み（middleware.ts参照）。

  // const [session, subscription, products] = await Promise.all([getSession(), getSubscription(), getProducts()]);
  // if (!session) {
  //   redirect('/sign-in'); // Clerkのmiddlewareがリダイレクトを処理
  // }
  // 上記のロジックはClerkのmiddlewareと<AuthLoading>等でカバーされる

  return (
    <section className='rounded-lg bg-background px-1 py-8 md:px-4 md:py-16'>
      {/*
        ClerkのUserProfileコンポーネントはアカウント管理とサブスクリプション管理を統合して提供できます。
        Stripe連携がClerkダッシュボードで正しく設定されていれば、
        サブスクリプションの表示や管理（プラン変更、支払い方法更新、キャンセルなど）もここに含まれます。
        既存の `manage-subscription/route.ts` は不要になる可能性が高いです。
      */}
      <UserProfile path="/account" routing="path">
        {/*
          カスタマイズ例:
          <UserProfile.Page label="マイプラン" url="subscription" labelIcon={<CreditCardIcon />}>
            <CustomSubscriptionManagementComponent />
          </UserProfile.Page>
          <UserProfile.Page label="請求履歴" url="billing" labelIcon={<ReceiptIcon />}>
            <CustomBillingHistoryComponent />
          </UserProfile.Page>
        */}
      </UserProfile>
    </section>
  );
}

// CardコンポーネントはClerk UserProfileが内部でUIを提供するため、このページでは直接使用しなくなります。
// function Card({
//   title,
//   footer,
//   children,
// }: PropsWithChildren<{
//   title: string;
//   footer?: ReactNode;
// }>) {
//   return (
//     <div className='m-auto w-full max-w-3xl rounded-md bg-muted'>
//       <div className='p-4'>
//         <h2 className='mb-1 text-xl font-semibold'>{title}</h2>
//         <div className='py-4'>{children}</div>
//       </div>
//       <div className='flex justify-end rounded-b-md border-t border-border p-4'>{footer}</div>
//     </div>
//   );
// }
