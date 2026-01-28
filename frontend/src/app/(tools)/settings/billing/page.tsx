"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  AlertCircle,
  CheckCircle,
  Clock,
  CreditCard,
  Crown,
  ExternalLink,
  Loader2,
  XCircle,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useAuth } from "@clerk/nextjs";

type SubscriptionStatus =
  | "active"
  | "past_due"
  | "canceled"
  | "expired"
  | "none";

interface SubscriptionData {
  user_id: string;
  email: string | null;
  stripe_customer_id: string | null;
  stripe_subscription_id: string | null;
  status: SubscriptionStatus;
  current_period_end: string | null;
  cancel_at_period_end: boolean;
  is_privileged: boolean;
}

interface SubscriptionResponse {
  subscription: SubscriptionData;
  hasAccess: boolean;
}

const statusConfig: Record<
  SubscriptionStatus,
  {
    label: string;
    description: string;
    variant: "default" | "secondary" | "destructive" | "outline";
    icon: typeof CheckCircle;
  }
> = {
  active: {
    label: "アクティブ",
    description: "サブスクリプションが有効です",
    variant: "default",
    icon: CheckCircle,
  },
  past_due: {
    label: "支払い遅延",
    description: "お支払いが確認できていません。カード情報をご確認ください。",
    variant: "destructive",
    icon: AlertCircle,
  },
  canceled: {
    label: "キャンセル済み",
    description: "サブスクリプションはキャンセルされています",
    variant: "secondary",
    icon: XCircle,
  },
  expired: {
    label: "期限切れ",
    description: "サブスクリプションの有効期限が切れています",
    variant: "destructive",
    icon: XCircle,
  },
  none: {
    label: "未登録",
    description: "サブスクリプションに登録されていません",
    variant: "outline",
    icon: Clock,
  },
};

export default function BillingSettingsPage() {
  const router = useRouter();
  const { isLoaded, isSignedIn } = useAuth();
  const [subscription, setSubscription] = useState<SubscriptionData | null>(
    null
  );
  const [hasAccess, setHasAccess] = useState(false);
  const [loading, setLoading] = useState(true);
  const [portalLoading, setPortalLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchSubscription = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await fetch("/api/subscription/status");
      if (!response.ok) throw new Error("取得に失敗しました");
      const data: SubscriptionResponse = await response.json();
      setSubscription(data.subscription);
      setHasAccess(data.hasAccess);
    } catch (err) {
      setError(err instanceof Error ? err.message : "エラーが発生しました");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (isLoaded && isSignedIn) {
      fetchSubscription();
    }
  }, [isLoaded, isSignedIn, fetchSubscription]);

  const openCustomerPortal = async () => {
    setPortalLoading(true);
    try {
      const response = await fetch("/api/subscription/portal", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          returnUrl: `${window.location.origin}/settings/billing`,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "ポータルの作成に失敗しました");
      }

      if (data.url) {
        window.location.href = data.url;
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "エラーが発生しました");
      setPortalLoading(false);
    }
  };

  const status = subscription?.status || "none";
  const statusInfo = statusConfig[status] || statusConfig.none;
  const StatusIcon = statusInfo.icon;

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="space-y-2">
        <h1 className="text-3xl font-bold">請求&契約設定</h1>
        <p className="text-muted-foreground">
          プランの管理、支払い方法、請求履歴を確認できます。
        </p>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : error ? (
        <Card className="border-destructive">
          <CardContent className="pt-6">
            <div className="flex items-center gap-2 text-destructive">
              <AlertCircle className="h-5 w-5" />
              <span>{error}</span>
            </div>
          </CardContent>
        </Card>
      ) : (
        <>
          {/* 現在のプラン */}
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
                  <div className="flex items-center gap-2">
                    <Badge variant={statusInfo.variant} className="gap-1">
                      <StatusIcon className="h-3 w-3" />
                      {statusInfo.label}
                    </Badge>
                    {subscription?.is_privileged && (
                      <Badge
                        variant="default"
                        className="gap-1 bg-amber-500 hover:bg-amber-600"
                      >
                        <Crown className="h-3 w-3" />
                        特権ユーザー
                      </Badge>
                    )}
                    {hasAccess && (
                      <Badge variant="outline" className="gap-1 text-green-600 border-green-600">
                        <CheckCircle className="h-3 w-3" />
                        アクセス有効
                      </Badge>
                    )}
                  </div>
                  <p className="text-sm text-muted-foreground">
                    {subscription?.is_privileged
                      ? "特権ユーザーとして全機能にアクセスできます"
                      : statusInfo.description}
                  </p>
                </div>
              </div>

              {/* 期間情報 */}
              {subscription?.current_period_end && (
                <div className="pt-4 border-t">
                  <div className="flex items-center gap-2 text-sm">
                    <Clock className="h-4 w-4 text-muted-foreground" />
                    <span className="text-muted-foreground">
                      {subscription.cancel_at_period_end
                        ? "キャンセル予定日: "
                        : "次回請求日: "}
                    </span>
                    <span className="font-medium">
                      {new Date(
                        subscription.current_period_end
                      ).toLocaleDateString("ja-JP", {
                        year: "numeric",
                        month: "long",
                        day: "numeric",
                      })}
                    </span>
                  </div>
                  {subscription.cancel_at_period_end && (
                    <p className="text-sm text-muted-foreground mt-1">
                      この日までサービスをご利用いただけます。
                    </p>
                  )}
                </div>
              )}

            </CardContent>
          </Card>

          {/* アクション */}
          <Card>
            <CardHeader>
              <CardTitle>プラン管理</CardTitle>
              <CardDescription>
                サブスクリプションの管理、支払い方法の変更、請求履歴の確認
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {subscription?.stripe_customer_id ? (
                <Button onClick={openCustomerPortal} disabled={portalLoading}>
                  {portalLoading ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <ExternalLink className="mr-2 h-4 w-4" />
                  )}
                  カスタマーポータルを開く
                </Button>
              ) : subscription?.is_privileged ? (
                <p className="text-sm text-muted-foreground">
                  特権ユーザーのため、サブスクリプションの管理は不要です。
                </p>
              ) : (
                <Button onClick={() => router.push("/pricing")}>
                  プランに登録する
                </Button>
              )}

              <p className="text-xs text-muted-foreground">
                カスタマーポータルでは、支払い方法の変更、請求履歴の確認、サブスクリプションのキャンセルが行えます。
              </p>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
