'use client';

import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';

import { createSupabaseClient } from '@/libs/supabase/supabase-client';
import { useOrganization, useOrganizationList, useUser } from '@clerk/nextjs';

export interface OrganizationContextType {
  // Clerk組織情報
  currentOrganization: any;
  isPersonalContext: boolean;
  organizationList: any[];
  
  // Supabase組織データ
  organizationData: any;
  subscriptionData: any;
  membershipData: any;
  
  // 状態管理
  isLoading: boolean;
  error: string | null;
  
  // アクション
  switchOrganization: (orgId: string | null) => Promise<void>;
  refreshOrganizationData: () => Promise<void>;
}

const OrganizationContext = createContext<OrganizationContextType | null>(null);

export function useOrganizationContext() {
  const context = useContext(OrganizationContext);
  if (!context) {
    throw new Error('useOrganizationContext must be used within OrganizationProvider');
  }
  return context;
}

export function OrganizationProvider({ children }: { children: React.ReactNode }) {
  const { organization: currentOrganization } = useOrganization();
  const { userMemberships, setActive } = useOrganizationList();
  const { user } = useUser();
  
  const [organizationData, setOrganizationData] = useState<any>(null);
  const [subscriptionData, setSubscriptionData] = useState<any>(null);
  const [membershipData, setMembershipData] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const isPersonalContext = !currentOrganization;

  // 組織リストを取得（userMembershipsから組織情報を抽出）
  const organizationList = userMemberships?.data?.map(membership => membership.organization) || [];

  // 組織データを取得する関数
  const fetchOrganizationData = useCallback(async () => {
    if (!user) return;

    setIsLoading(true);
    setError(null);

    try {
      const supabase = createSupabaseClient();
      
      if (currentOrganization) {
        // 組織コンテキストの場合
        const orgId = currentOrganization.id;
        
        // 組織情報を取得
        const { data: orgData, error: orgError } = await supabase
          .from('organizations')
          .select(`
            *,
            organization_settings(*),
            unified_subscriptions(*)
          `)
          .eq('id', orgId)
          .single();

        if (orgError) {
          console.error('Organization data fetch error:', orgError);
          setError('組織情報の取得に失敗しました');
        } else {
          setOrganizationData(orgData);
          setSubscriptionData(orgData.unified_subscriptions?.[0] || null);
        }

        // メンバーシップ情報を取得
        const { data: membershipData, error: membershipError } = await supabase
          .from('organization_memberships')
          .select('*')
          .eq('organization_id', orgId)
          .eq('user_id', user.id)
          .eq('status', 'active')
          .single();

        if (membershipError) {
          console.error('Membership data fetch error:', membershipError);
        } else {
          setMembershipData(membershipData);
        }
      } else {
        // 個人コンテキストの場合
        const { data: personalSubscription, error: subError } = await supabase
          .from('unified_subscriptions')
          .select('*')
          .eq('user_id', user.id)
          .eq('subscription_type', 'individual')
          .single();

        if (subError && subError.code !== 'PGRST116') { // "not found" エラー以外
          console.error('Personal subscription fetch error:', subError);
          setError('個人サブスクリプション情報の取得に失敗しました');
        } else {
          setSubscriptionData(personalSubscription || null);
        }

        setOrganizationData(null);
        setMembershipData(null);
      }
    } catch (err) {
      console.error('Data fetch error:', err);
      setError('データの取得中にエラーが発生しました');
    } finally {
      setIsLoading(false);
    }
  }, [user, currentOrganization]);

  // 組織切り替え
  const switchOrganization = async (orgId: string | null) => {
    if (!setActive) return;

    try {
      setIsLoading(true);
      if (orgId) {
        await setActive({ organization: orgId });
      } else {
        await setActive({ organization: null });
      }
      // データは useEffect で自動的に再取得される
    } catch (err) {
      console.error('Organization switch error:', err);
      setError('組織の切り替えに失敗しました');
    }
  };

  // 組織データのリフレッシュ
  const refreshOrganizationData = async () => {
    await fetchOrganizationData();
  };

  // 組織変更時のデータ取得
  useEffect(() => {
    if (user) {
      fetchOrganizationData();
    }
  }, [fetchOrganizationData, user]);

  const contextValue: OrganizationContextType = {
    currentOrganization,
    isPersonalContext,
    organizationList,
    organizationData,
    subscriptionData,
    membershipData,
    isLoading,
    error,
    switchOrganization,
    refreshOrganizationData,
  };

  return React.createElement(
    OrganizationContext.Provider,
    { value: contextValue },
    children
  );
}

// 組織のロールチェック用のヘルパー
export function useOrganizationRole() {
  const { membershipData, isPersonalContext } = useOrganizationContext();
  
  const isOwner = !isPersonalContext && membershipData?.role === 'owner';
  const isAdmin = !isPersonalContext && ['owner', 'admin'].includes(membershipData?.role);
  const isMember = !isPersonalContext && membershipData?.role;
  
  return {
    isOwner,
    isAdmin, 
    isMember,
    role: membershipData?.role || null,
  };
}

// サブスクリプション状態チェック用のヘルパー
export function useSubscriptionStatus() {
  const { subscriptionData, isPersonalContext } = useOrganizationContext();
  
  const hasActiveSubscription = subscriptionData && 
    ['active', 'trialing'].includes(subscriptionData.status);
  
  const isTrialing = subscriptionData?.status === 'trialing';
  const isPastDue = subscriptionData?.status === 'past_due';
  const isCanceled = subscriptionData?.status === 'canceled';
  
  const articleLimit = subscriptionData?.monthly_article_limit || 5; // デフォルト5記事
  const articlesUsed = subscriptionData?.monthly_articles_used || 0;
  const articlesRemaining = Math.max(0, articleLimit - articlesUsed);
  
  return {
    hasActiveSubscription,
    isTrialing,
    isPastDue,
    isCanceled,
    articleLimit,
    articlesUsed,
    articlesRemaining,
    subscriptionData,
  };
}