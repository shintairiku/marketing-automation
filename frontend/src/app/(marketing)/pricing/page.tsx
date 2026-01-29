'use client';

/**
 * Pricingページ
 *
 * 現在のプラン状態を表示し、適切なアクション（購入/アップグレード/管理）を提供
 * - 未契約 → 個人プラン or チームプランを購入
 * - 個人プラン契約中 → チームプランへアップグレード or 管理
 * - チームプラン契約中 → 管理（Stripe Customer Portal）
 * - @shintairiku.jp → 無料アクセス
 */

import { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import {
  Check,
  ExternalLink,
  Loader2,
  Settings,
  Sparkles,
  Users,
  Zap,
} from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
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
}

interface OrgSubscription {
  id: string;
  organization_id: string;
  status: string;
  quantity: number;
  current_period_end: string | null;
  cancel_at_period_end: boolean;
}

interface SubscriptionStatusResponse {
  subscription: UserSubscription;
  orgSubscription: OrgSubscription | null;
  hasAccess: boolean;
}

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

type PlanTab = 'individual' | 'team';

// ============================================
// メインコンポーネント
// ============================================
export default function PricingPage() {
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
  const [loadingStatus, setLoadingStatus] = useState(false);

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
    if (!isSignedIn) return;
    setLoadingStatus(true);
    fetch('/api/subscription/status')
      .then((res) => res.json())
      .then((data: SubscriptionStatusResponse) => setSubStatus(data))
      .catch((err) => console.error('Failed to fetch subscription status:', err))
      .finally(() => setLoadingStatus(false));
  }, [isSignedIn]);

  const userEmail = user?.primaryEmailAddress?.emailAddress;
  const isPrivileged = isPrivilegedEmail(userEmail);

  // 現在のプラン判定
  const hasIndividualPlan = subStatus?.subscription?.status === 'active';
  const hasTeamPlan = subStatus?.orgSubscription?.status === 'active';
  const hasAnyPlan = hasIndividualPlan || hasTeamPlan;

  // Stripe Customer Portalへ
  const handleManageSubscription = async () => {
    setIsLoading(true);
    try {
      const response = await fetch('/api/subscription/portal', { method: 'POST' });
      const data = await response.json();
      if (data.url) {
        window.location.href = data.url;
      }
    } catch (error) {
      console.error('Portal error:', error);
      setStatusMessage({ type: 'error', message: 'ポータルへのアクセスに失敗しました' });
    } finally {
      setIsLoading(false);
    }
  };

  // チェックアウトへ
  const handleCheckout = async (isTeam: boolean) => {
    if (!isSignedIn) {
      router.push('/sign-in?redirect_url=/pricing');
      return;
    }
    if (isPrivileged) {
      router.push('/blog/new');
      return;
    }

    setIsLoading(true);
    setStatusMessage(null);

    try {
      const body: Record<string, unknown> = {
        successUrl: `${window.location.origin}/pricing?subscription=success`,
        cancelUrl: `${window.location.origin}/pricing?subscription=canceled`,
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
    <div className="min-h-screen py-16 px-4">
      <div className="max-w-5xl mx-auto">
        {/* ヘッダー */}
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold mb-4">
            シンプルな料金プラン
          </h1>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            すべての機能が使える、わかりやすい月額プラン。
            いつでもキャンセル可能です。
          </p>
        </div>

        {/* ステータスメッセージ */}
        {statusMessage && (
          <div
            className={`mb-8 p-4 rounded-lg ${
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
          <div className="mb-8 p-4 rounded-lg bg-gradient-to-r from-purple-50 to-pink-50 border border-purple-200">
            <div className="flex items-center gap-2 text-purple-800">
              <Sparkles className="h-5 w-5" />
              <span className="font-semibold">
                @shintairiku.jp アカウントをお持ちのため、すべての機能を無料でご利用いただけます。
              </span>
            </div>
          </div>
        )}

        {/* 現在のプラン状態 */}
        {isSignedIn && !isPrivileged && (hasAnyPlan || loadingStatus) && (
          <div className="mb-8">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-lg">
                  <Settings className="h-5 w-5" />
                  現在のプラン
                </CardTitle>
              </CardHeader>
              <CardContent>
                {loadingStatus ? (
                  <div className="flex items-center gap-2 text-muted-foreground">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    読み込み中...
                  </div>
                ) : hasTeamPlan && subStatus?.orgSubscription ? (
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <Badge variant="default">チームプラン</Badge>
                        <Badge variant="secondary">{subStatus.orgSubscription.quantity}シート</Badge>
                      </div>
                      <p className="text-sm text-muted-foreground mt-1">
                        &yen;{(PRICE_PER_SEAT * subStatus.orgSubscription.quantity).toLocaleString()}/月
                        {subStatus.orgSubscription.current_period_end && (
                          <> ・ 次回更新: {new Date(subStatus.orgSubscription.current_period_end).toLocaleDateString('ja-JP')}</>
                        )}
                      </p>
                    </div>
                    <Button variant="outline" onClick={handleManageSubscription} disabled={isLoading} className="gap-1">
                      <ExternalLink className="h-4 w-4" />
                      管理
                    </Button>
                  </div>
                ) : hasIndividualPlan && subStatus?.subscription ? (
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <Badge variant="default">個人プラン</Badge>
                        {subStatus.subscription.cancel_at_period_end && (
                          <Badge variant="destructive">キャンセル予定</Badge>
                        )}
                      </div>
                      <p className="text-sm text-muted-foreground mt-1">
                        &yen;{PRICE_PER_SEAT.toLocaleString()}/月
                        {subStatus.subscription.current_period_end && (
                          <> ・ 次回更新: {new Date(subStatus.subscription.current_period_end).toLocaleDateString('ja-JP')}</>
                        )}
                      </p>
                    </div>
                    <Button variant="outline" onClick={handleManageSubscription} disabled={isLoading} className="gap-1">
                      <ExternalLink className="h-4 w-4" />
                      管理
                    </Button>
                  </div>
                ) : null}
              </CardContent>
            </Card>
          </div>
        )}

        {/* プラン切り替えタブ */}
        <div className="flex justify-center mb-8">
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

        {/* プランカード */}
        <div className="flex justify-center">
          {planTab === 'individual' ? (
            <Card className="w-full max-w-md border-2 border-primary shadow-lg">
              <CardHeader className="text-center pb-4">
                <div className="inline-flex items-center justify-center gap-2 bg-primary/10 text-primary px-3 py-1 rounded-full text-sm font-medium mb-4">
                  <Zap className="h-4 w-4" />
                  個人プラン
                </div>
                <CardTitle className="text-2xl">プロプラン</CardTitle>
                <CardDescription>
                  すべての機能にアクセス
                </CardDescription>
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
                {hasIndividualPlan ? (
                  <Button className="w-full h-12 text-lg" variant="outline" onClick={handleManageSubscription} disabled={isLoading}>
                    <Settings className="mr-2 h-5 w-5" />
                    サブスクリプションを管理
                  </Button>
                ) : (
                  <Button
                    className="w-full h-12 text-lg"
                    onClick={() => handleCheckout(false)}
                    disabled={isLoading || !isAuthLoaded || hasTeamPlan}
                  >
                    {isLoading ? (
                      <><Loader2 className="mr-2 h-5 w-5 animate-spin" />処理中...</>
                    ) : !isAuthLoaded ? (
                      <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                    ) : isSignedIn ? (
                      isPrivileged ? 'ダッシュボードへ' :
                      hasTeamPlan ? 'チームプラン契約中' :
                      '今すぐ始める'
                    ) : (
                      'ログインして始める'
                    )}
                  </Button>
                )}
              </CardFooter>
            </Card>
          ) : (
            <Card className="w-full max-w-md border-2 border-primary shadow-lg">
              <CardHeader className="text-center pb-4">
                <div className="inline-flex items-center justify-center gap-2 bg-primary/10 text-primary px-3 py-1 rounded-full text-sm font-medium mb-4">
                  <Users className="h-4 w-4" />
                  チームプラン
                </div>
                <CardTitle className="text-2xl">チームプロ</CardTitle>
                <CardDescription>
                  チーム全員でフル機能を活用
                </CardDescription>
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
                    disabled={hasTeamPlan}
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

                {/* 組織名（チームプラン未購入時のみ） */}
                {!hasTeamPlan && (
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
                )}

                {/* 個人プランからのアップグレード注意 */}
                {hasIndividualPlan && !hasTeamPlan && (
                  <div className="mb-6 p-3 rounded-lg bg-blue-50 border border-blue-200 text-sm text-blue-800">
                    現在の個人プランは、チームプラン購入後に自動的にキャンセルされます。
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
                {hasTeamPlan ? (
                  <Button className="w-full h-12 text-lg" variant="outline" onClick={handleManageSubscription} disabled={isLoading}>
                    <Settings className="mr-2 h-5 w-5" />
                    サブスクリプションを管理
                  </Button>
                ) : (
                  <Button
                    className="w-full h-12 text-lg"
                    onClick={() => handleCheckout(true)}
                    disabled={isLoading || !isAuthLoaded}
                  >
                    {isLoading ? (
                      <><Loader2 className="mr-2 h-5 w-5 animate-spin" />処理中...</>
                    ) : !isAuthLoaded ? (
                      <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                    ) : isSignedIn ? (
                      isPrivileged ? 'ダッシュボードへ' :
                      hasIndividualPlan ? '個人→チームにアップグレード' :
                      'チームプランを始める'
                    ) : (
                      'ログインして始める'
                    )}
                  </Button>
                )}
              </CardFooter>
            </Card>
          )}
        </div>

        {/* FAQ */}
        <div className="mt-12 text-center">
          <h2 className="text-xl font-semibold mb-4">よくある質問</h2>
          <div className="grid md:grid-cols-2 gap-6 text-left max-w-3xl mx-auto">
            <div className="p-4 bg-white rounded-lg shadow-sm">
              <h3 className="font-medium mb-2">キャンセルはいつでもできますか？</h3>
              <p className="text-sm text-muted-foreground">
                はい、いつでもキャンセル可能です。キャンセル後も請求期間終了まではサービスをご利用いただけます。
              </p>
            </div>
            <div className="p-4 bg-white rounded-lg shadow-sm">
              <h3 className="font-medium mb-2">チームプランのシート数は変更できますか？</h3>
              <p className="text-sm text-muted-foreground">
                はい、サブスクリプション管理画面からシート数を変更できます。料金は日割り計算されます。
              </p>
            </div>
            <div className="p-4 bg-white rounded-lg shadow-sm">
              <h3 className="font-medium mb-2">個人プランからチームプランへ変更できますか？</h3>
              <p className="text-sm text-muted-foreground">
                はい、チームプランを購入すると、個人プランは自動的にキャンセルされます。
              </p>
            </div>
            <div className="p-4 bg-white rounded-lg shadow-sm">
              <h3 className="font-medium mb-2">チームメンバーの招待方法は？</h3>
              <p className="text-sm text-muted-foreground">
                チームプラン購入後、設定画面のメンバー設定からメールアドレスで招待できます。招待メールが自動送信されます。
              </p>
            </div>
          </div>
        </div>

        {/* セキュリティバッジ */}
        <div className="mt-12 text-center">
          <p className="text-sm text-muted-foreground">
            安全な決済は{' '}
            <a href="https://stripe.com" target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">
              Stripe
            </a>
            {' '}によって処理されます
          </p>
        </div>
      </div>
    </div>
  );
}
