'use client';

/**
 * サブスクリプションガードコンポーネント
 *
 * サブスクリプションが有効でない場合、Pricingページにリダイレクト
 * @shintairiku.jp ユーザーは常にアクセス可能
 */

import { createContext, type ReactNode,useCallback, useContext, useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';

import { hasActiveAccess, hasActiveOrgAccess, isPrivilegedEmail, type OrgSubscription, type UserSubscription } from '@/lib/subscription';
import { useAuth, useUser } from '@clerk/nextjs';

// サブスクリプションコンテキスト
interface SubscriptionContextType {
  subscription: UserSubscription | null;
  orgSubscription: OrgSubscription | null;
  hasAccess: boolean;
  isLoading: boolean;
  refetch: () => Promise<void>;
}

const SubscriptionContext = createContext<SubscriptionContextType>({
  subscription: null,
  orgSubscription: null,
  hasAccess: false,
  isLoading: true,
  refetch: async () => {},
});

export function useSubscription() {
  return useContext(SubscriptionContext);
}

// サブスクリプションプロバイダー
export function SubscriptionProvider({ children }: { children: ReactNode }) {
  const { isLoaded: isAuthLoaded, userId } = useAuth();
  const { user } = useUser();
  const [subscription, setSubscription] = useState<UserSubscription | null>(null);
  const [orgSubscription, setOrgSubscription] = useState<OrgSubscription | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const fetchSubscription = useCallback(async () => {
    if (!userId) {
      setSubscription(null);
      setOrgSubscription(null);
      setIsLoading(false);
      return;
    }

    try {
      const response = await fetch('/api/subscription/status');
      if (response.ok) {
        const data = await response.json();
        setSubscription(data.subscription);
        setOrgSubscription(data.orgSubscription || null);
      }
    } catch (error) {
      console.error('Error fetching subscription:', error);
    } finally {
      setIsLoading(false);
    }
  }, [userId]);

  useEffect(() => {
    if (isAuthLoaded) {
      fetchSubscription();
    }
  }, [isAuthLoaded, fetchSubscription]);

  // アクセス権の判定（個人 OR 組織のいずれかで有効ならアクセス可）
  const userEmail = user?.primaryEmailAddress?.emailAddress;
  const hasAccess =
    isPrivilegedEmail(userEmail) ||        // @shintairiku.jp
    hasActiveAccess(subscription) ||       // 個人サブスクリプション
    hasActiveOrgAccess(orgSubscription);   // 組織サブスクリプション

  return (
    <SubscriptionContext.Provider
      value={{
        subscription,
        orgSubscription,
        hasAccess,
        isLoading: !isAuthLoaded || isLoading,
        refetch: fetchSubscription,
      }}
    >
      {children}
    </SubscriptionContext.Provider>
  );
}

// サブスクリプションガード
interface SubscriptionGuardProps {
  children: ReactNode;
  fallback?: ReactNode;
  redirectTo?: string;
}

export function SubscriptionGuard({
  children,
  fallback,
  redirectTo = '/pricing',
}: SubscriptionGuardProps) {
  const router = useRouter();
  const { hasAccess, isLoading } = useSubscription();

  useEffect(() => {
    if (!isLoading && !hasAccess) {
      router.push(redirectTo);
    }
  }, [isLoading, hasAccess, router, redirectTo]);

  // ローディング中
  if (isLoading) {
    return fallback || (
      <div className="flex items-center justify-center min-h-[200px]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    );
  }

  // アクセス権がない場合（リダイレクト待ち）
  if (!hasAccess) {
    return fallback || (
      <div className="flex items-center justify-center min-h-[200px]">
        <p className="text-muted-foreground">リダイレクト中...</p>
      </div>
    );
  }

  return <>{children}</>;
}

// アップグレード促進バナー
export function SubscriptionBanner() {
  const { subscription, orgSubscription, hasAccess, isLoading } = useSubscription();

  // ローディング中または特権ユーザーは表示しない
  if (isLoading || subscription?.is_privileged) {
    return null;
  }

  // 個人または組織のいずれかでアクティブならバナー不要
  if (hasAccess && (subscription?.status === 'active' || orgSubscription?.status === 'active')) {
    return null;
  }

  // 個人サブスクのキャンセル予定
  if (subscription?.cancel_at_period_end && subscription.current_period_end) {
    const endDate = new Date(subscription.current_period_end).toLocaleDateString('ja-JP');
    return (
      <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4 mb-4">
        <div className="flex">
          <div className="ml-3">
            <p className="text-sm text-yellow-700">
              サブスクリプションは {endDate} に終了します。
              <a href="/api/subscription/portal" className="font-medium underline ml-2">
                キャンセルを取り消す
              </a>
            </p>
          </div>
        </div>
      </div>
    );
  }

  // 組織サブスクのキャンセル予定
  if (orgSubscription?.cancel_at_period_end && orgSubscription.current_period_end) {
    const endDate = new Date(orgSubscription.current_period_end).toLocaleDateString('ja-JP');
    return (
      <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4 mb-4">
        <div className="flex">
          <div className="ml-3">
            <p className="text-sm text-yellow-700">
              チームプランは {endDate} に終了予定です。
            </p>
          </div>
        </div>
      </div>
    );
  }

  // 支払い遅延の場合（個人または組織）
  if (subscription?.status === 'past_due' || orgSubscription?.status === 'past_due') {
    return (
      <div className="bg-red-50 border-l-4 border-red-400 p-4 mb-4">
        <div className="flex">
          <div className="ml-3">
            <p className="text-sm text-red-700">
              お支払いに問題があります。サービスを継続するには支払い方法を更新してください。
              <a href="/api/subscription/portal" className="font-medium underline ml-2">
                支払い方法を更新
              </a>
            </p>
          </div>
        </div>
      </div>
    );
  }

  // サブスクリプションがない場合
  if (!hasAccess) {
    return (
      <div className="bg-blue-50 border-l-4 border-blue-400 p-4 mb-4">
        <div className="flex">
          <div className="ml-3">
            <p className="text-sm text-blue-700">
              すべての機能を利用するにはプランにご登録ください。
              <a href="/pricing" className="font-medium underline ml-2">
                プランを見る
              </a>
            </p>
          </div>
        </div>
      </div>
    );
  }

  return null;
}
