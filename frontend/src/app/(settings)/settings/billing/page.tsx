'use client';

/**
 * 請求&プラン管理ページ
 *
 * フリープランの使用状況を表示し、上限到達時はお問い合わせへ誘導
 * - フリープラン → 使用量表示 + お問い合わせリンク
 * - 有料プラン契約中（既存）→ Stripe管理ポータル
 * - @shintairiku.jp → 無料アクセス
 */

import { useEffect, useState } from 'react';
import Link from 'next/link';
import {
  AlertCircle,
  CheckCircle,
  Clock,
  CreditCard,
  Crown,
  ExternalLink,
  FileText,
  Loader2,
  Mail,
  Settings,
  Sparkles,
  Users,
  XCircle,
  Zap,
} from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { isPrivilegedEmail } from '@/lib/subscription';
import { useAuth, useUser } from '@clerk/nextjs';

// ============================================
// 型定義
// ============================================
interface UserSubscription {
  user_id: string;
  stripe_customer_id: string | null;
  stripe_subscription_id: string | null;
  status: string;
  current_period_end: string | null;
  cancel_at_period_end: boolean;
  is_privileged: boolean;
  email: string | null;
}

interface OrgSubscription {
  id: string;
  organization_id: string;
  status: string;
  quantity: number;
  current_period_end: string | null;
  cancel_at_period_end: boolean;
}

interface UsageInfo {
  articles_generated: number;
  articles_limit: number;
  addon_articles_limit: number;
  total_limit: number;
  remaining: number;
  billing_period_start: string | null;
  billing_period_end: string | null;
  plan_tier: string | null;
}

interface SubscriptionStatusResponse {
  subscription: UserSubscription;
  orgSubscription: OrgSubscription | null;
  hasAccess: boolean;
  usage: UsageInfo | null;
}

type SubscriptionStatus = 'active' | 'past_due' | 'canceled' | 'expired' | 'none';

// ============================================
// 定数
// ============================================
const statusConfig: Record<
  SubscriptionStatus,
  {
    label: string;
    description: string;
    variant: 'default' | 'secondary' | 'destructive' | 'outline';
    icon: typeof CheckCircle;
  }
> = {
  active: {
    label: 'アクティブ',
    description: 'プランが有効です',
    variant: 'default',
    icon: CheckCircle,
  },
  past_due: {
    label: '支払い遅延',
    description: 'お支払いが確認できていません。カード情報をご確認ください。',
    variant: 'destructive',
    icon: AlertCircle,
  },
  canceled: {
    label: 'キャンセル済み',
    description: 'サブスクリプションはキャンセルされています',
    variant: 'secondary',
    icon: XCircle,
  },
  expired: {
    label: '期限切れ',
    description: 'サブスクリプションの有効期限が切れています',
    variant: 'destructive',
    icon: XCircle,
  },
  none: {
    label: '未登録',
    description: 'サブスクリプションに登録されていません',
    variant: 'outline',
    icon: Clock,
  },
};

// ============================================
// メインコンポーネント
// ============================================
export default function BillingSettingsPage() {
  const { isLoaded: isAuthLoaded, isSignedIn } = useAuth();
  const { user } = useUser();

  // 現在のサブスクリプション状態
  const [subStatus, setSubStatus] = useState<SubscriptionStatusResponse | null>(null);
  const [loadingStatus, setLoadingStatus] = useState(true);
  const [portalLoading, setPortalLoading] = useState(false);

  // 現在のサブスク状態を取得
  useEffect(() => {
    if (!isAuthLoaded || !isSignedIn) return;
    setLoadingStatus(true);
    fetch('/api/subscription/status')
      .then((res) => res.json())
      .then((data: SubscriptionStatusResponse) => {
        setSubStatus(data);
      })
      .catch((err) => console.error('Failed to fetch subscription status:', err))
      .finally(() => setLoadingStatus(false));
  }, [isAuthLoaded, isSignedIn]);

  const userEmail = user?.primaryEmailAddress?.emailAddress;
  const isPrivileged = isPrivilegedEmail(userEmail);

  // 現在のプラン判定
  const hasIndividualPlan = subStatus?.subscription?.status === 'active' && subStatus?.subscription?.stripe_subscription_id;
  const hasTeamPlan = subStatus?.orgSubscription?.status === 'active';
  const hasStripeSubscription = hasIndividualPlan || hasTeamPlan;

  // ステータス表示用
  const currentStatus: SubscriptionStatus = hasTeamPlan
    ? (subStatus?.orgSubscription?.status as SubscriptionStatus) || 'none'
    : (subStatus?.subscription?.status as SubscriptionStatus) || 'none';
  const currentStatusInfo = statusConfig[currentStatus] || statusConfig.none;
  const StatusIcon = currentStatusInfo.icon;

  // フリープランかどうか
  const isFreePlan = subStatus?.subscription?.status === 'active' && !subStatus?.subscription?.stripe_subscription_id;

  // Stripe Customer Portal
  const openCustomerPortal = async () => {
    setPortalLoading(true);
    try {
      const response = await fetch('/api/subscription/portal', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          returnUrl: `${window.location.origin}/settings/billing`,
        }),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || 'ポータルの作成に失敗しました');
      }
      if (data.url) {
        window.location.href = data.url;
      }
    } catch (err) {
      console.error('Portal error:', err);
      setPortalLoading(false);
    }
  };

  return (
    <div className="container mx-auto p-6 space-y-6 max-w-4xl">
      {/* ヘッダー */}
      <div className="space-y-2">
        <h1 className="text-3xl font-bold">プラン&利用状況</h1>
        <p className="text-muted-foreground">
          現在のプランと記事生成の利用状況を確認できます。
        </p>
      </div>

      {/* 特権ユーザー向けメッセージ */}
      {isAuthLoaded && isSignedIn && isPrivileged && (
        <div className="p-4 rounded-lg bg-gradient-to-r from-purple-50 to-pink-50 border border-purple-200">
          <div className="flex items-center gap-2 text-purple-800">
            <Sparkles className="h-5 w-5" />
            <span className="font-semibold">
              @shintairiku.jp アカウントをお持ちのため、すべての機能を無料でご利用いただけます。
            </span>
          </div>
        </div>
      )}

      {loadingStatus ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : (
        <>
          {/* 現在のプラン状態カード */}
          {!isPrivileged && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <CreditCard className="h-5 w-5" />
                  現在のプラン
                </CardTitle>
                <CardDescription>
                  プランのステータスと詳細
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <Badge variant={currentStatusInfo.variant} className="gap-1">
                        <StatusIcon className="h-3 w-3" />
                        {currentStatusInfo.label}
                      </Badge>
                      {isFreePlan && (
                        <Badge variant="secondary" className="gap-1">
                          <Zap className="h-3 w-3" />
                          フリープラン
                        </Badge>
                      )}
                      {hasTeamPlan && subStatus?.orgSubscription && (
                        <Badge variant="secondary" className="gap-1">
                          <Users className="h-3 w-3" />
                          チームプラン ({subStatus.orgSubscription.quantity}シート)
                        </Badge>
                      )}
                      {hasIndividualPlan && !hasTeamPlan && (
                        <Badge variant="secondary" className="gap-1">
                          <Zap className="h-3 w-3" />
                          個人プラン
                        </Badge>
                      )}
                      {subStatus?.subscription?.is_privileged && (
                        <Badge variant="default" className="gap-1 bg-amber-500 hover:bg-amber-600">
                          <Crown className="h-3 w-3" />
                          特権ユーザー
                        </Badge>
                      )}
                    </div>
                    <p className="text-sm text-muted-foreground">
                      {isFreePlan
                        ? '毎月無料で記事を生成できるプランです'
                        : currentStatusInfo.description}
                    </p>
                  </div>

                  {hasStripeSubscription && subStatus?.subscription?.stripe_customer_id && (
                    <Button
                      variant="outline"
                      onClick={openCustomerPortal}
                      disabled={portalLoading}
                      className="gap-1"
                    >
                      {portalLoading ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <ExternalLink className="h-4 w-4" />
                      )}
                      管理ポータル
                    </Button>
                  )}
                </div>

                {/* 期間情報 (有料プラン) */}
                {hasTeamPlan && subStatus?.orgSubscription?.current_period_end && (
                  <div className="pt-3 border-t">
                    <div className="flex items-center gap-2 text-sm">
                      <Clock className="h-4 w-4 text-muted-foreground" />
                      <span className="text-muted-foreground">
                        {subStatus.orgSubscription.cancel_at_period_end ? 'キャンセル予定日: ' : '次回請求日: '}
                      </span>
                      <span className="font-medium">
                        {new Date(subStatus.orgSubscription.current_period_end).toLocaleDateString('ja-JP', {
                          year: 'numeric',
                          month: 'long',
                          day: 'numeric',
                        })}
                      </span>
                    </div>
                  </div>
                )}
                {hasIndividualPlan && !hasTeamPlan && subStatus?.subscription?.current_period_end && (
                  <div className="pt-3 border-t">
                    <div className="flex items-center gap-2 text-sm">
                      <Clock className="h-4 w-4 text-muted-foreground" />
                      <span className="text-muted-foreground">
                        {subStatus.subscription.cancel_at_period_end ? 'キャンセル予定日: ' : '次回請求日: '}
                      </span>
                      <span className="font-medium">
                        {new Date(subStatus.subscription.current_period_end).toLocaleDateString('ja-JP', {
                          year: 'numeric',
                          month: 'long',
                          day: 'numeric',
                        })}
                      </span>
                    </div>
                    {subStatus.subscription.cancel_at_period_end && (
                      <p className="text-sm text-muted-foreground mt-1">
                        この日までサービスをご利用いただけます。
                      </p>
                    )}
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {/* 使用量セクション */}
          {!isPrivileged && subStatus?.usage && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <FileText className="h-5 w-5" />
                  今月の記事生成
                </CardTitle>
                <CardDescription>
                  Blog AIの月間記事生成数と上限
                  {subStatus.usage.billing_period_end && (
                    <> (請求期間: ~{new Date(subStatus.usage.billing_period_end).toLocaleDateString('ja-JP')})</>
                  )}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* 使用量プログレスバー */}
                <div className="space-y-3">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">使用量</span>
                    <span className="font-medium">
                      {subStatus.usage.articles_generated} / {subStatus.usage.total_limit} 記事
                      {subStatus.usage.remaining > 0 && (
                        <span className="text-muted-foreground font-normal ml-1">
                          (残り{subStatus.usage.remaining}記事)
                        </span>
                      )}
                    </span>
                  </div>
                  <Progress
                    value={subStatus.usage.total_limit > 0
                      ? Math.min(100, (subStatus.usage.articles_generated / subStatus.usage.total_limit) * 100)
                      : 0}
                    className="h-3"
                  />
                  <div className="flex items-center justify-between text-xs text-muted-foreground">
                    <span>プラン上限: {subStatus.usage.articles_limit}記事</span>
                    {subStatus.usage.addon_articles_limit > 0 && (
                      <span>+ 追加記事: {subStatus.usage.addon_articles_limit}記事</span>
                    )}
                  </div>
                </div>

                {/* 上限到達時のお問い合わせ誘導 */}
                {subStatus.usage.remaining === 0 && (
                  <div className="p-4 rounded-lg bg-amber-50 border border-amber-200">
                    <div className="flex items-start gap-3">
                      <AlertCircle className="h-5 w-5 text-amber-600 mt-0.5 flex-shrink-0" />
                      <div className="space-y-2">
                        <p className="text-sm font-medium text-amber-800">
                          月間の記事生成上限に達しました
                        </p>
                        <p className="text-sm text-amber-700">
                          追加の記事生成をご希望の場合は、お問い合わせください。
                        </p>
                        <Button asChild variant="outline" size="sm" className="gap-1.5">
                          <Link href="/settings/contact">
                            <Mail className="h-4 w-4" />
                            お問い合わせ
                          </Link>
                        </Button>
                      </div>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {/* サブスクリプション管理（有料プランのStripe契約がある場合のみ） */}
          {!isPrivileged && hasStripeSubscription && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Settings className="h-5 w-5" />
                  サブスクリプション管理
                </CardTitle>
                <CardDescription>
                  支払い方法の変更、請求履歴の確認、サブスクリプションのキャンセル
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Button onClick={openCustomerPortal} disabled={portalLoading}>
                  {portalLoading ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <ExternalLink className="mr-2 h-4 w-4" />
                  )}
                  カスタマーポータルを開く
                </Button>
                <p className="text-xs text-muted-foreground mt-3">
                  カスタマーポータルでは、支払い方法の変更、請求履歴の確認、サブスクリプションのキャンセルが行えます。
                </p>
              </CardContent>
            </Card>
          )}

          {/* お問い合わせセクション */}
          {!isPrivileged && (
            <Card>
              <CardContent className="pt-6">
                <div className="flex items-start gap-4">
                  <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center flex-shrink-0">
                    <Mail className="h-5 w-5 text-blue-600" />
                  </div>
                  <div className="space-y-2">
                    <h3 className="font-medium">ご質問・ご要望はございますか？</h3>
                    <p className="text-sm text-muted-foreground">
                      追加記事の付与やプランに関するご質問など、お気軽にお問い合わせください。
                    </p>
                    <Button asChild variant="outline" size="sm" className="gap-1.5">
                      <Link href="/settings/contact">
                        <Mail className="h-4 w-4" />
                        お問い合わせページへ
                      </Link>
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
