'use client';

/**
 * Pricingページ
 *
 * 個人プランとチームプランの切り替え
 * - 個人プラン: 月額サブスクリプション（1シート）
 * - チームプラン: シート数選択可能（2〜50）
 * - @shintairiku.jp ユーザーは無料アクセス
 */

import { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Check, Loader2, Sparkles, Users, Zap } from 'lucide-react';

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

  // URLパラメータからステータスメッセージを取得
  useEffect(() => {
    const subscription = searchParams.get('subscription');
    if (subscription === 'canceled') {
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

  // ユーザーのメールアドレス
  const userEmail = user?.primaryEmailAddress?.emailAddress;
  const isPrivileged = isPrivilegedEmail(userEmail);

  // チェックアウトへ進む
  const handleCheckout = async (isTeam: boolean) => {
    if (!isSignedIn) {
      router.push('/sign-in?redirect_url=/pricing');
      return;
    }

    if (isPrivileged) {
      router.push('/dashboard');
      return;
    }

    setIsLoading(true);
    setStatusMessage(null);

    try {
      const body: Record<string, unknown> = {
        successUrl: `${window.location.origin}/dashboard?subscription=success`,
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
        headers: {
          'Content-Type': 'application/json',
        },
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
                <Button
                  className="w-full h-12 text-lg"
                  onClick={() => handleCheckout(false)}
                  disabled={isLoading || !isAuthLoaded}
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                      処理中...
                    </>
                  ) : !isAuthLoaded ? (
                    <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                  ) : isSignedIn ? (
                    isPrivileged ? (
                      'ダッシュボードへ'
                    ) : (
                      '今すぐ始める'
                    )
                  ) : (
                    'ログインして始める'
                  )}
                </Button>
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
                  disabled={isLoading || !isAuthLoaded}
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                      処理中...
                    </>
                  ) : !isAuthLoaded ? (
                    <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                  ) : isSignedIn ? (
                    isPrivileged ? (
                      'ダッシュボードへ'
                    ) : (
                      'チームプランを始める'
                    )
                  ) : (
                    'ログインして始める'
                  )}
                </Button>
              </CardFooter>
            </Card>
          )}
        </div>

        {/* 追加情報 */}
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
                はい、いつでもシート数を増減できます。変更はすぐに反映され、料金は日割り計算されます。
              </p>
            </div>
            <div className="p-4 bg-white rounded-lg shadow-sm">
              <h3 className="font-medium mb-2">支払い方法は何がありますか？</h3>
              <p className="text-sm text-muted-foreground">
                クレジットカード（Visa、Mastercard、American Express、JCB）でお支払いいただけます。
              </p>
            </div>
            <div className="p-4 bg-white rounded-lg shadow-sm">
              <h3 className="font-medium mb-2">チームメンバーの招待方法は？</h3>
              <p className="text-sm text-muted-foreground">
                チームプラン購入後、設定画面からメールアドレスを入力して招待できます。招待メールが自動送信されます。
              </p>
            </div>
          </div>
        </div>

        {/* セキュリティバッジ */}
        <div className="mt-12 text-center">
          <p className="text-sm text-muted-foreground">
            安全な決済は{' '}
            <a
              href="https://stripe.com"
              target="_blank"
              rel="noopener noreferrer"
              className="text-primary hover:underline"
            >
              Stripe
            </a>
            {' '}によって処理されます
          </p>
        </div>
      </div>
    </div>
  );
}
