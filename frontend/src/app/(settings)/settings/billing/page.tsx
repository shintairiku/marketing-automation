'use client';

/**
 * 請求&プラン管理ページ
 *
 * 現在のプラン状態を表示し、適切なアクション（購入/アップグレード/管理）を提供
 * - 未契約 → 個人プラン or チームプランを購入
 * - 個人プラン契約中 → チームプランへアップグレード or 管理
 * - チームプラン契約中 → シート変更 / 管理（Stripe Customer Portal）
 * - @shintairiku.jp → 無料アクセス
 */

import { useCallback, useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import {
  AlertCircle,
  ArrowRight,
  Check,
  CheckCircle,
  Clock,
  CreditCard,
  Crown,
  ExternalLink,
  FileText,
  Gift,
  Loader2,
  Minus,
  Plus,
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
  CardFooter,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Progress } from '@/components/ui/progress';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
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
  trial_end: string | null;
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

interface UpgradePreview {
  amountDue: number;
  currency: string;
  lines: { description: string; amount: number; proration: boolean }[];
  currentQuantity: number;
  newQuantity: number;
  currentPeriodEnd: string | null;
  prorationDate: number;
}

type SubscriptionStatus = 'trialing' | 'active' | 'past_due' | 'canceled' | 'expired' | 'none';

// ============================================
// 定数
// ============================================
const PLAN_FEATURES = [
  'SEO最適化記事の無制限生成',
  'AI画像生成機能',
  'カスタムスタイルテンプレート',
  '会社情報の自動反映',
  'リアルタイム進捗表示',
  '優先サポート',
];

const TEAM_EXTRA_FEATURES = [
  'チームメンバーの招待・管理',
  'WordPress接続の組織共有',
  '組織レベルのアクセス管理',
];

const PRICE_PER_SEAT = 29800;

const statusConfig: Record<
  SubscriptionStatus,
  {
    label: string;
    description: string;
    variant: 'default' | 'secondary' | 'destructive' | 'outline';
    icon: typeof CheckCircle;
  }
> = {
  trialing: {
    label: '無料トライアル中',
    description: '無料トライアル期間中です。期間内はすべての機能をご利用いただけます。',
    variant: 'default',
    icon: Gift,
  },
  active: {
    label: 'アクティブ',
    description: 'サブスクリプションが有効です',
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

type PlanTab = 'individual' | 'team';

// ============================================
// メインコンポーネント
// ============================================
export default function BillingSettingsPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { isLoaded: isAuthLoaded, isSignedIn } = useAuth();
  const { user } = useUser();
  const [isLoading, setIsLoading] = useState(false);
  const [statusMessage, setStatusMessage] = useState<{ type: 'success' | 'error' | 'info'; message: string } | null>(null);
  const [planTab, setPlanTab] = useState<PlanTab>('individual');
  const [teamSeats, setTeamSeats] = useState(3);
  const [organizationName, setOrganizationName] = useState('');

  // 現在のサブスクリプション状態
  const [subStatus, setSubStatus] = useState<SubscriptionStatusResponse | null>(null);
  const [loadingStatus, setLoadingStatus] = useState(true);
  const [portalLoading, setPortalLoading] = useState(false);

  // アップグレード確認モーダル
  const [showUpgradeConfirm, setShowUpgradeConfirm] = useState(false);
  const [upgradePreview, setUpgradePreview] = useState<UpgradePreview | null>(null);
  const [loadingPreview, setLoadingPreview] = useState(false);
  const [upgrading, setUpgrading] = useState(false);

  // アドオン管理
  const [addonQuantity, setAddonQuantity] = useState(0);
  const [addonLoading, setAddonLoading] = useState(false);

  // シート変更モーダル
  const [showSeatChangeConfirm, setShowSeatChangeConfirm] = useState(false);
  const [seatChangePreview, setSeatChangePreview] = useState<UpgradePreview | null>(null);
  const [newSeatCount, setNewSeatCount] = useState(0);
  const [loadingSeatPreview, setLoadingSeatPreview] = useState(false);
  const [changingSeats, setChangingSeats] = useState(false);

  // URLパラメータからステータスメッセージを取得
  useEffect(() => {
    const subscription = searchParams.get('subscription');
    if (subscription === 'success') {
      setStatusMessage({
        type: 'success',
        message: 'サブスクリプションの購入が完了しました！',
      });
    } else if (subscription === 'canceled') {
      setStatusMessage({
        type: 'info',
        message: 'チェックアウトがキャンセルされました。いつでも再度お申し込みいただけます。',
      });
    } else if (subscription === 'error') {
      setStatusMessage({
        type: 'error',
        message: 'エラーが発生しました。しばらくしてから再度お試しください。',
      });
    }
  }, [searchParams]);

  // 現在のサブスク状態を取得
  useEffect(() => {
    if (!isAuthLoaded || !isSignedIn) return;
    setLoadingStatus(true);
    fetch('/api/subscription/status')
      .then((res) => res.json())
      .then((data: SubscriptionStatusResponse) => {
        setSubStatus(data);
        // アドオン数量を使用量情報から算出
        if (data.usage && data.usage.addon_articles_limit > 0) {
          setAddonQuantity(Math.round(data.usage.addon_articles_limit / 20));
        }
      })
      .catch((err) => console.error('Failed to fetch subscription status:', err))
      .finally(() => setLoadingStatus(false));
  }, [isAuthLoaded, isSignedIn]);

  const userEmail = user?.primaryEmailAddress?.emailAddress;
  const isPrivileged = isPrivilegedEmail(userEmail);

  // 現在のプラン判定
  const hasIndividualPlan = subStatus?.subscription?.status === 'active';
  const hasTeamPlan = subStatus?.orgSubscription?.status === 'active';
  const isTrialing = subStatus?.subscription?.status === 'trialing';
  const hasAnyPlan = hasIndividualPlan || hasTeamPlan || isTrialing;

  // ステータス表示用
  const currentStatus: SubscriptionStatus = hasTeamPlan
    ? (subStatus?.orgSubscription?.status as SubscriptionStatus) || 'none'
    : hasIndividualPlan
    ? (subStatus?.subscription?.status as SubscriptionStatus) || 'none'
    : (subStatus?.subscription?.status as SubscriptionStatus) || 'none';
  const currentStatusInfo = statusConfig[currentStatus] || statusConfig.none;
  const StatusIcon = currentStatusInfo.icon;

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
      setStatusMessage({
        type: 'error',
        message: err instanceof Error ? err.message : 'ポータルへのアクセスに失敗しました',
      });
      setPortalLoading(false);
    }
  };

  // アップグレードプレビューを取得してモーダル表示
  const handleUpgradePreview = useCallback(async () => {
    setLoadingPreview(true);
    setStatusMessage(null);

    try {
      const response = await fetch('/api/subscription/preview-upgrade', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ quantity: teamSeats }),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || 'プレビューの取得に失敗しました');
      }
      setUpgradePreview(data);
      setShowUpgradeConfirm(true);
    } catch (error) {
      console.error('Preview error:', error);
      setStatusMessage({
        type: 'error',
        message: error instanceof Error ? error.message : 'プレビューの取得に失敗しました',
      });
    } finally {
      setLoadingPreview(false);
    }
  }, [teamSeats]);

  // アップグレードを実行
  const handleConfirmUpgrade = async () => {
    setUpgrading(true);
    try {
      const response = await fetch('/api/subscription/upgrade-to-team', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          quantity: teamSeats,
          organizationName: organizationName.trim() || undefined,
        }),
      });
      const data = await response.json();
      if (!response.ok) {
        if (response.status === 402) {
          throw new Error('お支払いに失敗しました。支払い方法を更新してください。');
        }
        throw new Error(data.error || 'アップグレードに失敗しました');
      }
      setShowUpgradeConfirm(false);
      setUpgradePreview(null);
      setStatusMessage({
        type: 'success',
        message: `チームプラン（${teamSeats}シート）にアップグレードしました！`,
      });
      const statusRes = await fetch('/api/subscription/status');
      const statusData = await statusRes.json();
      setSubStatus(statusData);
    } catch (error) {
      console.error('Upgrade error:', error);
      setStatusMessage({
        type: 'error',
        message: error instanceof Error ? error.message : 'アップグレードに失敗しました',
      });
      setShowUpgradeConfirm(false);
    } finally {
      setUpgrading(false);
    }
  };

  // シート変更プレビュー
  const handleSeatChangePreview = useCallback(async (seats: number) => {
    setLoadingSeatPreview(true);
    setStatusMessage(null);
    setNewSeatCount(seats);

    try {
      const response = await fetch('/api/subscription/preview-upgrade', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ quantity: seats }),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || 'プレビューの取得に失敗しました');
      }
      setSeatChangePreview(data);
      setShowSeatChangeConfirm(true);
    } catch (error) {
      console.error('Seat preview error:', error);
      setStatusMessage({
        type: 'error',
        message: error instanceof Error ? error.message : 'プレビューの取得に失敗しました',
      });
    } finally {
      setLoadingSeatPreview(false);
    }
  }, []);

  // シート変更を実行
  const handleConfirmSeatChange = async () => {
    setChangingSeats(true);
    try {
      const response = await fetch('/api/subscription/update-seats', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ quantity: newSeatCount }),
      });
      const data = await response.json();
      if (!response.ok) {
        if (response.status === 402) {
          throw new Error('お支払いに失敗しました。支払い方法を更新してください。');
        }
        throw new Error(data.error || 'シート数の変更に失敗しました');
      }
      setShowSeatChangeConfirm(false);
      setSeatChangePreview(null);
      setStatusMessage({
        type: 'success',
        message: `シート数を${data.previousQuantity}から${data.newQuantity}に変更しました！`,
      });
      const statusRes = await fetch('/api/subscription/status');
      const statusData = await statusRes.json();
      setSubStatus(statusData);
    } catch (error) {
      console.error('Seat change error:', error);
      setStatusMessage({
        type: 'error',
        message: error instanceof Error ? error.message : 'シート数の変更に失敗しました',
      });
      setShowSeatChangeConfirm(false);
    } finally {
      setChangingSeats(false);
    }
  };

  // アドオン変更
  const handleAddonChange = async (quantity: number) => {
    setAddonLoading(true);
    setStatusMessage(null);
    try {
      const response = await fetch('/api/subscription/addon', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ quantity }),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || 'アドオンの変更に失敗しました');
      }
      setStatusMessage({
        type: 'success',
        message: quantity > 0
          ? `記事追加アドオン（${quantity}ユニット）を${data.addonQuantity > 0 ? '変更' : '追加'}しました`
          : 'アドオンを解除しました',
      });
      setAddonQuantity(quantity);
      const statusRes = await fetch('/api/subscription/status');
      const statusData = await statusRes.json();
      setSubStatus(statusData);
    } catch (error) {
      console.error('Addon error:', error);
      setStatusMessage({
        type: 'error',
        message: error instanceof Error ? error.message : 'アドオンの変更に失敗しました',
      });
    } finally {
      setAddonLoading(false);
    }
  };

  // チェックアウト
  const handleCheckout = async (isTeam: boolean) => {
    if (isPrivileged) {
      router.push('/blog/new');
      return;
    }

    // 個人プラン契約中 → チームへアップグレード: プレビューモーダルを表示
    if (isTeam && hasIndividualPlan) {
      handleUpgradePreview();
      return;
    }

    setIsLoading(true);
    setStatusMessage(null);

    try {
      const body: Record<string, unknown> = {
        successUrl: `${window.location.origin}/settings/billing?subscription=success`,
        cancelUrl: `${window.location.origin}/settings/billing?subscription=canceled`,
      };

      if (isTeam) {
        body.quantity = teamSeats;
        if (organizationName.trim()) {
          body.organizationName = organizationName.trim();
        }
      }

      const response = await fetch('/api/subscription/checkout', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || 'チェックアウトの作成に失敗しました');
      }
      if (data.url) {
        window.location.href = data.url;
      } else {
        throw new Error('チェックアウトURLが取得できませんでした');
      }
    } catch (error) {
      console.error('Checkout error:', error);
      setStatusMessage({
        type: 'error',
        message: error instanceof Error ? error.message : 'エラーが発生しました',
      });
      setIsLoading(false);
    }
  };

  const teamTotal = PRICE_PER_SEAT * teamSeats;

  return (
    <div className="container mx-auto p-6 space-y-6 max-w-4xl">
      {/* ヘッダー */}
      <div className="space-y-2">
        <h1 className="text-3xl font-bold">請求&プラン管理</h1>
        <p className="text-muted-foreground">
          プランの購入・変更、支払い方法、請求履歴を管理できます。
        </p>
      </div>

      {/* ステータスメッセージ */}
      {statusMessage && (
        <div
          className={`p-4 rounded-lg ${
            statusMessage.type === 'success'
              ? 'bg-green-50 border border-green-200 text-green-800'
              : statusMessage.type === 'error'
              ? 'bg-red-50 border border-red-200 text-red-800'
              : 'bg-blue-50 border border-blue-200 text-blue-800'
          }`}
        >
          {statusMessage.message}
        </div>
      )}

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
                  サブスクリプションのステータスと詳細
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
                      {hasTeamPlan && subStatus?.orgSubscription && (
                        <Badge variant="secondary" className="gap-1">
                          <Users className="h-3 w-3" />
                          チームプラン ({subStatus.orgSubscription.quantity}シート)
                        </Badge>
                      )}
                      {isTrialing && (
                        <Badge variant="secondary" className="gap-1 bg-violet-100 text-violet-800 hover:bg-violet-200">
                          <Gift className="h-3 w-3" />
                          無料トライアル
                        </Badge>
                      )}
                      {hasIndividualPlan && !hasTeamPlan && !isTrialing && (
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
                      {isTrialing
                        ? '無料トライアル期間中 — すべての機能をご利用いただけます'
                        : hasAnyPlan
                        ? hasTeamPlan
                          ? `¥${(PRICE_PER_SEAT * (subStatus?.orgSubscription?.quantity || 1)).toLocaleString()}/月`
                          : `¥${PRICE_PER_SEAT.toLocaleString()}/月`
                        : currentStatusInfo.description}
                    </p>
                  </div>

                  {hasAnyPlan && subStatus?.subscription?.stripe_customer_id && (
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

                {/* 期間情報 */}
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

                {/* トライアル期間情報 */}
                {isTrialing && subStatus?.subscription?.trial_end && (
                  <div className="pt-3 border-t">
                    <div className="p-3 rounded-lg bg-violet-50 border border-violet-200">
                      <div className="flex items-center gap-2 text-sm text-violet-800">
                        <Gift className="h-4 w-4" />
                        <span className="font-medium">無料トライアル中</span>
                      </div>
                      <p className="text-sm text-violet-700 mt-1">
                        トライアル終了日: {new Date(subStatus.subscription.trial_end).toLocaleDateString('ja-JP', {
                          year: 'numeric',
                          month: 'long',
                          day: 'numeric',
                        })}
                        {(() => {
                          const remaining = Math.ceil(
                            (new Date(subStatus.subscription.trial_end!).getTime() - Date.now()) / (1000 * 60 * 60 * 24)
                          );
                          return remaining > 0 ? ` (残り${remaining}日)` : ' (本日終了)';
                        })()}
                      </p>
                      <p className="text-xs text-violet-600 mt-1">
                        トライアル期間中はクレジットカードの登録不要ですべての機能をご利用いただけます。
                        期間終了後も引き続きご利用いただく場合は、プランをご購入ください。
                      </p>
                    </div>
                  </div>
                )}

                {/* シート数変更 (チームプラン) */}
                {hasTeamPlan && subStatus?.orgSubscription && (
                  <div className="flex items-center gap-3 pt-3 border-t">
                    <Label htmlFor="change-seats" className="text-sm whitespace-nowrap">
                      シート数変更:
                    </Label>
                    <Select
                      value={String(newSeatCount || subStatus.orgSubscription.quantity)}
                      onValueChange={(val) => setNewSeatCount(Number(val))}
                    >
                      <SelectTrigger id="change-seats" className="w-24">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {Array.from({ length: 49 }, (_, i) => i + 2).map((n) => (
                          <SelectItem key={n} value={String(n)}>
                            {n}人
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => handleSeatChangePreview(newSeatCount || subStatus.orgSubscription!.quantity)}
                      disabled={
                        loadingSeatPreview ||
                        !newSeatCount ||
                        newSeatCount === subStatus.orgSubscription.quantity
                      }
                    >
                      {loadingSeatPreview ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        '変更'
                      )}
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {/* 使用量 & アドオン管理セクション */}
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
                      <span>+ アドオン: {subStatus.usage.addon_articles_limit}記事</span>
                    )}
                  </div>
                  {subStatus.usage.remaining === 0 && (
                    <p className="text-sm text-red-600">
                      月間上限に達しました。アドオンを追加して上限を増やせます。
                    </p>
                  )}
                </div>

                {/* アドオン管理 */}
                <div className="pt-4 border-t space-y-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <h4 className="text-sm font-medium">記事追加アドオン</h4>
                      <p className="text-xs text-muted-foreground">
                        1ユニットあたり20記事を追加（月額リカーリング）
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <Button
                      variant="outline"
                      size="icon"
                      className="h-8 w-8"
                      disabled={addonLoading || addonQuantity <= 0}
                      onClick={() => {
                        const next = Math.max(0, addonQuantity - 1);
                        handleAddonChange(next);
                      }}
                    >
                      <Minus className="h-4 w-4" />
                    </Button>
                    <div className="text-center min-w-[80px]">
                      <span className="text-lg font-semibold">{addonQuantity}</span>
                      <span className="text-sm text-muted-foreground ml-1">ユニット</span>
                    </div>
                    <Button
                      variant="outline"
                      size="icon"
                      className="h-8 w-8"
                      disabled={addonLoading}
                      onClick={() => handleAddonChange(addonQuantity + 1)}
                    >
                      <Plus className="h-4 w-4" />
                    </Button>
                    {addonLoading && <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />}
                  </div>
                  {addonQuantity > 0 && (
                    <p className="text-xs text-muted-foreground">
                      +{addonQuantity * 20}記事/月が追加されます。次回請求に反映されます。
                    </p>
                  )}
                </div>
              </CardContent>
            </Card>
          )}

          {/* プラン選択セクション (未契約 or トライアル中 or 個人→チームアップグレード) */}
          {!isPrivileged && (!hasAnyPlan || isTrialing || (hasIndividualPlan && !hasTeamPlan)) && (
            <>
              <div className="space-y-2">
                <h2 className="text-xl font-semibold">
                  {hasIndividualPlan && !isTrialing ? 'チームプランへアップグレード' : isTrialing ? 'トライアル終了後のプランを選択' : 'プランを選択'}
                </h2>
                <p className="text-sm text-muted-foreground">
                  {hasIndividualPlan && !isTrialing
                    ? '個人プランからチームプランへ変更できます。未使用分は日割り計算で差し引かれます。'
                    : isTrialing
                    ? 'トライアル終了後も引き続きご利用いただくには、プランをご購入ください。'
                    : 'すべての機能が使える、わかりやすい月額プラン。いつでもキャンセル可能です。'}
                </p>
              </div>

              {/* プラン切り替えタブ */}
              {(!hasIndividualPlan || isTrialing) && (
                <div className="flex justify-center">
                  <div className="inline-flex rounded-lg bg-muted p-1">
                    <button
                      className={`px-6 py-2 rounded-md text-sm font-medium transition-colors ${
                        planTab === 'individual'
                          ? 'bg-background text-foreground shadow-sm'
                          : 'text-muted-foreground hover:text-foreground'
                      }`}
                      onClick={() => setPlanTab('individual')}
                    >
                      個人プラン
                    </button>
                    <button
                      className={`px-6 py-2 rounded-md text-sm font-medium transition-colors ${
                        planTab === 'team'
                          ? 'bg-background text-foreground shadow-sm'
                          : 'text-muted-foreground hover:text-foreground'
                      }`}
                      onClick={() => setPlanTab('team')}
                    >
                      <Users className="h-4 w-4 inline mr-1" />
                      チームプラン
                    </button>
                  </div>
                </div>
              )}

              {/* プランカード */}
              <div className="flex justify-center">
                {((hasIndividualPlan && !isTrialing) || planTab === 'team') ? (
                  /* チームプランカード */
                  <Card className="w-full max-w-md border-2 border-primary shadow-lg">
                    <CardHeader className="text-center pb-4">
                      <div className="inline-flex items-center justify-center gap-2 bg-primary/10 text-primary px-3 py-1 rounded-full text-sm font-medium mb-4">
                        <Users className="h-4 w-4" />
                        チームプラン
                      </div>
                      <CardTitle className="text-2xl">チームプロ</CardTitle>
                      <CardDescription>チーム全員でフル機能を活用</CardDescription>
                    </CardHeader>

                    <CardContent className="pb-6">
                      {/* シート数セレクター */}
                      <div className="mb-6">
                        <Label htmlFor="team-seats" className="text-sm font-medium mb-2 block">
                          シート数（メンバー数）
                        </Label>
                        <Select
                          value={String(teamSeats)}
                          onValueChange={(val) => setTeamSeats(Number(val))}
                        >
                          <SelectTrigger id="team-seats">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            {Array.from({ length: 49 }, (_, i) => i + 2).map((n) => (
                              <SelectItem key={n} value={String(n)}>
                                {n}人
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>

                      {/* 組織名 */}
                      <div className="mb-6">
                        <Label htmlFor="org-name" className="text-sm font-medium mb-2 block">
                          組織名（任意）
                        </Label>
                        <Input
                          id="org-name"
                          placeholder="例: 株式会社〇〇"
                          value={organizationName}
                          onChange={(e) => setOrganizationName(e.target.value)}
                        />
                      </div>

                      {/* 個人プランからのアップグレード注意 */}
                      {hasIndividualPlan && (
                        <div className="mb-6 p-3 rounded-lg bg-blue-50 border border-blue-200 text-sm text-blue-800">
                          個人プランの未使用分は日割り計算で差し引かれ、チームプランとの差額のみが請求されます。
                        </div>
                      )}

                      {/* 価格表示 */}
                      <div className="text-center mb-6 p-4 rounded-lg bg-muted/50">
                        <div className="text-sm text-muted-foreground mb-1">
                          &yen;{PRICE_PER_SEAT.toLocaleString()} &times; {teamSeats}シート
                        </div>
                        <div>
                          <span className="text-4xl font-bold">&yen;{teamTotal.toLocaleString()}</span>
                          <span className="text-muted-foreground">/月</span>
                        </div>
                        <p className="text-xs text-muted-foreground mt-1">
                          税込み価格・いつでもキャンセル可能
                        </p>
                      </div>

                      <ul className="space-y-3 text-left">
                        {PLAN_FEATURES.map((feature, index) => (
                          <li key={index} className="flex items-center gap-3">
                            <Check className="h-5 w-5 text-green-600 flex-shrink-0" />
                            <span className="text-sm">{feature}</span>
                          </li>
                        ))}
                        {TEAM_EXTRA_FEATURES.map((feature, index) => (
                          <li key={`team-${index}`} className="flex items-center gap-3">
                            <Check className="h-5 w-5 text-blue-600 flex-shrink-0" />
                            <span className="text-sm font-medium">{feature}</span>
                          </li>
                        ))}
                      </ul>
                    </CardContent>

                    <CardFooter>
                      <Button
                        className="w-full h-12 text-lg"
                        onClick={() => handleCheckout(true)}
                        disabled={isLoading || loadingPreview}
                      >
                        {isLoading || loadingPreview ? (
                          <><Loader2 className="mr-2 h-5 w-5 animate-spin" />処理中...</>
                        ) : hasIndividualPlan ? (
                          '個人→チームにアップグレード'
                        ) : (
                          'チームプランを始める'
                        )}
                      </Button>
                    </CardFooter>
                  </Card>
                ) : (
                  /* 個人プランカード */
                  <Card className="w-full max-w-md border-2 border-primary shadow-lg">
                    <CardHeader className="text-center pb-4">
                      <div className="inline-flex items-center justify-center gap-2 bg-primary/10 text-primary px-3 py-1 rounded-full text-sm font-medium mb-4">
                        <Zap className="h-4 w-4" />
                        個人プラン
                      </div>
                      <CardTitle className="text-2xl">プロプラン</CardTitle>
                      <CardDescription>すべての機能にアクセス</CardDescription>
                    </CardHeader>

                    <CardContent className="text-center pb-6">
                      <div className="mb-6">
                        <span className="text-5xl font-bold">&yen;{PRICE_PER_SEAT.toLocaleString()}</span>
                        <span className="text-muted-foreground">/月</span>
                      </div>
                      <p className="text-sm text-muted-foreground mb-6">
                        税込み価格・いつでもキャンセル可能
                      </p>

                      <ul className="space-y-3 text-left">
                        {PLAN_FEATURES.map((feature, index) => (
                          <li key={index} className="flex items-center gap-3">
                            <Check className="h-5 w-5 text-green-600 flex-shrink-0" />
                            <span className="text-sm">{feature}</span>
                          </li>
                        ))}
                      </ul>
                    </CardContent>

                    <CardFooter>
                      <Button
                        className="w-full h-12 text-lg"
                        onClick={() => handleCheckout(false)}
                        disabled={isLoading}
                      >
                        {isLoading ? (
                          <><Loader2 className="mr-2 h-5 w-5 animate-spin" />処理中...</>
                        ) : (
                          '今すぐ始める'
                        )}
                      </Button>
                    </CardFooter>
                  </Card>
                )}
              </div>
            </>
          )}

          {/* プラン管理（Stripe Portal） */}
          {!isPrivileged && hasAnyPlan && (
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

          {/* FAQ */}
          {!isPrivileged && (
            <div className="pt-4">
              <h2 className="text-lg font-semibold mb-4">よくある質問</h2>
              <div className="grid md:grid-cols-2 gap-4">
                <Card>
                  <CardContent className="pt-4">
                    <h3 className="font-medium mb-2">キャンセルはいつでもできますか？</h3>
                    <p className="text-sm text-muted-foreground">
                      はい、いつでもキャンセル可能です。キャンセル後も請求期間終了まではサービスをご利用いただけます。
                    </p>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="pt-4">
                    <h3 className="font-medium mb-2">チームプランのシート数は変更できますか？</h3>
                    <p className="text-sm text-muted-foreground">
                      はい、上記のシート数変更からいつでも変更できます。料金は日割り計算されます。
                    </p>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="pt-4">
                    <h3 className="font-medium mb-2">個人プランからチームプランへ変更できますか？</h3>
                    <p className="text-sm text-muted-foreground">
                      はい、ワンクリックでアップグレードできます。個人プランの未使用分は日割り計算で差し引かれます。
                    </p>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="pt-4">
                    <h3 className="font-medium mb-2">チームメンバーの招待方法は？</h3>
                    <p className="text-sm text-muted-foreground">
                      チームプラン購入後、メンバー設定からメールアドレスで招待できます。招待メールが自動送信されます。
                    </p>
                  </CardContent>
                </Card>
              </div>
            </div>
          )}

          {/* セキュリティ */}
          <div className="text-center pt-2 pb-4">
            <p className="text-sm text-muted-foreground">
              安全な決済は{' '}
              <a href="https://stripe.com" target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">
                Stripe
              </a>
              {' '}によって処理されます
            </p>
          </div>
        </>
      )}

      {/* アップグレード確認モーダル */}
      <Dialog open={showUpgradeConfirm} onOpenChange={(open) => {
        if (!upgrading) {
          setShowUpgradeConfirm(open);
          if (!open) setUpgradePreview(null);
        }
      }}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>チームプランへのアップグレード</DialogTitle>
            <DialogDescription>
              個人プランからチームプランへ変更します。以下の内容をご確認ください。
            </DialogDescription>
          </DialogHeader>

          {upgradePreview ? (
            <div className="space-y-4 py-2">
              <div className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
                <div className="text-sm">
                  <div className="text-muted-foreground">個人プラン（{upgradePreview.currentQuantity}シート）</div>
                </div>
                <ArrowRight className="h-4 w-4 text-muted-foreground mx-2" />
                <div className="text-sm font-medium">
                  <div>チームプラン（{upgradePreview.newQuantity}シート）</div>
                </div>
              </div>

              <div className="border rounded-lg divide-y">
                {upgradePreview.lines.map((line, i) => (
                  <div key={i} className="flex items-center justify-between px-3 py-2 text-sm">
                    <span className={`flex-1 ${line.proration ? 'text-muted-foreground' : ''}`}>
                      {line.description}
                    </span>
                    <span className={`font-mono ${line.amount < 0 ? 'text-green-600' : ''}`}>
                      {line.amount < 0 ? '-' : ''}&yen;{Math.abs(line.amount).toLocaleString()}
                    </span>
                  </div>
                ))}
              </div>

              <div className="flex items-center justify-between p-3 rounded-lg bg-primary/5 border border-primary/20">
                <span className="font-medium">今回の請求額</span>
                <span className="text-xl font-bold">
                  &yen;{upgradePreview.amountDue.toLocaleString()}
                </span>
              </div>

              {upgradePreview.currentPeriodEnd && (
                <p className="text-xs text-muted-foreground">
                  次回更新日: {new Date(upgradePreview.currentPeriodEnd).toLocaleDateString('ja-JP')} 以降は
                  &yen;{(PRICE_PER_SEAT * upgradePreview.newQuantity).toLocaleString()}/月で自動更新されます。
                </p>
              )}
            </div>
          ) : (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              <span className="ml-2 text-muted-foreground">料金を計算中...</span>
            </div>
          )}

          <DialogFooter className="gap-2 sm:gap-0">
            <Button
              variant="outline"
              onClick={() => {
                setShowUpgradeConfirm(false);
                setUpgradePreview(null);
              }}
              disabled={upgrading}
            >
              キャンセル
            </Button>
            <Button
              onClick={handleConfirmUpgrade}
              disabled={upgrading || !upgradePreview}
            >
              {upgrading ? (
                <><Loader2 className="mr-2 h-4 w-4 animate-spin" />処理中...</>
              ) : (
                'アップグレードを確定'
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* シート変更確認モーダル */}
      <Dialog open={showSeatChangeConfirm} onOpenChange={(open) => {
        if (!changingSeats) {
          setShowSeatChangeConfirm(open);
          if (!open) setSeatChangePreview(null);
        }
      }}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>シート数の変更</DialogTitle>
            <DialogDescription>
              チームプランのシート数を変更します。以下の内容をご確認ください。
            </DialogDescription>
          </DialogHeader>

          {seatChangePreview ? (
            <div className="space-y-4 py-2">
              <div className="flex items-center justify-between p-3 rounded-lg bg-muted/50">
                <div className="text-sm">
                  <div className="text-muted-foreground">{seatChangePreview.currentQuantity}シート</div>
                  <div className="text-xs text-muted-foreground">
                    &yen;{(PRICE_PER_SEAT * seatChangePreview.currentQuantity).toLocaleString()}/月
                  </div>
                </div>
                <ArrowRight className="h-4 w-4 text-muted-foreground mx-2" />
                <div className="text-sm font-medium">
                  <div>{seatChangePreview.newQuantity}シート</div>
                  <div className="text-xs text-muted-foreground">
                    &yen;{(PRICE_PER_SEAT * seatChangePreview.newQuantity).toLocaleString()}/月
                  </div>
                </div>
              </div>

              <div className="border rounded-lg divide-y">
                {seatChangePreview.lines.map((line, i) => (
                  <div key={i} className="flex items-center justify-between px-3 py-2 text-sm">
                    <span className={`flex-1 ${line.proration ? 'text-muted-foreground' : ''}`}>
                      {line.description}
                    </span>
                    <span className={`font-mono ${line.amount < 0 ? 'text-green-600' : ''}`}>
                      {line.amount < 0 ? '-' : ''}&yen;{Math.abs(line.amount).toLocaleString()}
                    </span>
                  </div>
                ))}
              </div>

              <div className="flex items-center justify-between p-3 rounded-lg bg-primary/5 border border-primary/20">
                <span className="font-medium">
                  {seatChangePreview.amountDue >= 0 ? '今回の請求額' : '今回のクレジット'}
                </span>
                <span className={`text-xl font-bold ${seatChangePreview.amountDue < 0 ? 'text-green-600' : ''}`}>
                  {seatChangePreview.amountDue < 0 ? '-' : ''}&yen;{Math.abs(seatChangePreview.amountDue).toLocaleString()}
                </span>
              </div>

              {seatChangePreview.newQuantity < seatChangePreview.currentQuantity && (
                <p className="text-xs text-muted-foreground">
                  シート削減分のクレジットは次回請求から差し引かれます。
                </p>
              )}

              {seatChangePreview.currentPeriodEnd && (
                <p className="text-xs text-muted-foreground">
                  次回更新日: {new Date(seatChangePreview.currentPeriodEnd).toLocaleDateString('ja-JP')} 以降は
                  &yen;{(PRICE_PER_SEAT * seatChangePreview.newQuantity).toLocaleString()}/月で自動更新されます。
                </p>
              )}
            </div>
          ) : (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              <span className="ml-2 text-muted-foreground">料金を計算中...</span>
            </div>
          )}

          <DialogFooter className="gap-2 sm:gap-0">
            <Button
              variant="outline"
              onClick={() => {
                setShowSeatChangeConfirm(false);
                setSeatChangePreview(null);
              }}
              disabled={changingSeats}
            >
              キャンセル
            </Button>
            <Button
              onClick={handleConfirmSeatChange}
              disabled={changingSeats || !seatChangePreview}
            >
              {changingSeats ? (
                <><Loader2 className="mr-2 h-4 w-4 animate-spin" />処理中...</>
              ) : (
                'シート数を変更'
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
