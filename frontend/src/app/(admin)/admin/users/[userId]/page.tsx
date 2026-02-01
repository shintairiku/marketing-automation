'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import {
  AlertCircle,
  ArrowLeft,
  Building2,
  Calendar,
  CheckCircle,
  Clock,
  Copy,
  CreditCard,
  Crown,
  FileText,
  Loader2,
  RefreshCw,
  User,
  XCircle,
} from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Separator } from '@/components/ui/separator';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { cn } from '@/utils/cn';
import { useAuth } from '@clerk/nextjs';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type SubscriptionStatus = 'active' | 'past_due' | 'canceled' | 'expired' | 'none';

interface UserDetail {
  id: string;
  full_name: string | null;
  email: string | null;
  avatar_url: string | null;
  created_at: string | null;
  subscription_status: SubscriptionStatus;
  is_privileged: boolean;
  stripe_customer_id: string | null;
  stripe_subscription_id: string | null;
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
  plan_tier_id: string | null;
}

interface GenerationRecord {
  process_id: string;
  status: string;
  created_at: string | null;
  updated_at: string | null;
}

interface UserDetailResponse {
  user: UserDetail;
  usage: UsageInfo | null;
  generation_history: GenerationRecord[];
  organization_id: string | null;
  organization_name: string | null;
  addon_quantity: number;
  plan_tier_name: string | null;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const subscriptionStatusConfig: Record<
  SubscriptionStatus,
  { label: string; variant: 'default' | 'secondary' | 'destructive' | 'outline' }
> = {
  active: { label: 'アクティブ', variant: 'default' },
  past_due: { label: '支払い遅延', variant: 'destructive' },
  canceled: { label: 'キャンセル済み', variant: 'secondary' },
  expired: { label: '期限切れ', variant: 'destructive' },
  none: { label: 'なし', variant: 'outline' },
};

const generationStatusConfig: Record<
  string,
  { label: string; variant: 'default' | 'secondary' | 'destructive' | 'outline' }
> = {
  completed: { label: '完了', variant: 'default' },
  in_progress: { label: '進行中', variant: 'secondary' },
  failed: { label: '失敗', variant: 'destructive' },
  cancelled: { label: 'キャンセル', variant: 'outline' },
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function getApiBaseUrl(): string {
  const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8080';
  const USE_PROXY = process.env.NODE_ENV === 'production';
  return USE_PROXY ? '/api/proxy' : API_BASE_URL;
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return '-';
  return new Date(dateStr).toLocaleDateString('ja-JP');
}

function formatDateTime(dateStr: string | null): string {
  if (!dateStr) return '-';
  return new Date(dateStr).toLocaleString('ja-JP');
}

function truncateId(id: string, length = 16): string {
  if (id.length <= length) return id;
  return `${id.slice(0, length)}...`;
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard API may be unavailable
    }
  };

  return (
    <Button variant="ghost" size="icon" className="h-6 w-6" onClick={handleCopy}>
      {copied ? (
        <CheckCircle className="h-3 w-3 text-green-600" />
      ) : (
        <Copy className="h-3 w-3 text-muted-foreground" />
      )}
    </Button>
  );
}

function InfoRow({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex items-start justify-between gap-4 py-2">
      <span className="text-sm text-muted-foreground shrink-0">{label}</span>
      <div className="text-sm text-right">{children}</div>
    </div>
  );
}

function LoadingSkeleton() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-8 w-48" />
      <div className="flex items-center gap-4">
        <Skeleton className="h-16 w-16 rounded-full" />
        <div className="space-y-2">
          <Skeleton className="h-6 w-40" />
          <Skeleton className="h-4 w-60" />
        </div>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Skeleton className="h-64" />
        <Skeleton className="h-64" />
        <Skeleton className="h-40" />
      </div>
      <Skeleton className="h-72" />
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

export default function AdminUserDetailPage() {
  const params = useParams();
  const userId = params.userId as string;
  const { getToken } = useAuth();

  const [data, setData] = useState<UserDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchUserDetail = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const token = await getToken();
      const baseURL = getApiBaseUrl();

      const response = await fetch(`${baseURL}/admin/users/${userId}/detail`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          ...(token && { Authorization: `Bearer ${token}` }),
        },
      });

      if (!response.ok) {
        if (response.status === 404) {
          throw new Error('ユーザーが見つかりませんでした');
        }
        throw new Error('ユーザー情報の取得に失敗しました');
      }

      const json: UserDetailResponse = await response.json();
      setData(json);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'エラーが発生しました');
    } finally {
      setLoading(false);
    }
  }, [getToken, userId]);

  useEffect(() => {
    fetchUserDetail();
  }, [fetchUserDetail]);

  // -- Loading state --------------------------------------------------------
  if (loading) {
    return (
      <div className="space-y-6">
        <Link
          href="/admin/users"
          className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          ユーザー一覧に戻る
        </Link>
        <LoadingSkeleton />
      </div>
    );
  }

  // -- Error state ----------------------------------------------------------
  if (error || !data) {
    return (
      <div className="space-y-6">
        <Link
          href="/admin/users"
          className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          ユーザー一覧に戻る
        </Link>
        <Card className="border-destructive">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-destructive">
              <AlertCircle className="h-5 w-5" />
              エラー
            </CardTitle>
            <CardDescription>{error || 'データの取得に失敗しました'}</CardDescription>
          </CardHeader>
          <CardContent>
            <Button onClick={fetchUserDetail} variant="outline">
              <RefreshCw className="mr-2 h-4 w-4" />
              再読み込み
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  const { user, usage, generation_history, organization_id, organization_name, addon_quantity, plan_tier_name } = data;
  const statusInfo = subscriptionStatusConfig[user.subscription_status];
  const usagePercent = usage && usage.total_limit > 0
    ? Math.min(Math.round((usage.articles_generated / usage.total_limit) * 100), 100)
    : 0;

  return (
    <div className="space-y-6">
      {/* Back navigation */}
      <Link
        href="/admin/users"
        className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors"
      >
        <ArrowLeft className="h-4 w-4" />
        ユーザー一覧に戻る
      </Link>

      {/* User header */}
      <div className="flex flex-col sm:flex-row items-start gap-4">
        {user.avatar_url ? (
          <img
            src={user.avatar_url}
            alt=""
            className="h-16 w-16 rounded-full object-cover shrink-0"
          />
        ) : (
          <div className="h-16 w-16 rounded-full bg-muted flex items-center justify-center shrink-0">
            <User className="h-8 w-8 text-muted-foreground" />
          </div>
        )}
        <div className="space-y-1 min-w-0">
          <h1 className="text-2xl font-bold truncate">
            {user.full_name || '名前未設定'}
          </h1>
          <p className="text-sm text-muted-foreground">{user.email || 'メール未設定'}</p>
          <p className="text-xs font-mono text-muted-foreground truncate">
            ID: {user.id}
          </p>
          <div className="flex flex-wrap items-center gap-2 pt-1">
            <Badge variant={statusInfo.variant}>{statusInfo.label}</Badge>
            {user.is_privileged && (
              <Badge variant="default" className="gap-1 bg-amber-500 hover:bg-amber-600">
                <Crown className="h-3 w-3" />
                特権
              </Badge>
            )}
            {user.created_at && (
              <span className="text-xs text-muted-foreground flex items-center gap-1">
                <Calendar className="h-3 w-3" />
                {formatDate(user.created_at)} 登録
              </span>
            )}
          </div>
        </div>
      </div>

      <Separator />

      {/* Info cards grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Subscription card */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base">
              <CreditCard className="h-4 w-4" />
              サブスクリプション情報
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-0">
            <InfoRow label="プラン">
              <span className="font-medium">{plan_tier_name || '未設定'}</span>
            </InfoRow>
            <Separator />
            <InfoRow label="ステータス">
              <Badge variant={statusInfo.variant}>{statusInfo.label}</Badge>
            </InfoRow>
            <Separator />
            <InfoRow label="Stripe Customer ID">
              {user.stripe_customer_id ? (
                <span className="inline-flex items-center gap-1">
                  <code className="text-xs font-mono bg-muted px-1.5 py-0.5 rounded">
                    {truncateId(user.stripe_customer_id)}
                  </code>
                  <CopyButton text={user.stripe_customer_id} />
                </span>
              ) : (
                <span className="text-muted-foreground">-</span>
              )}
            </InfoRow>
            <Separator />
            <InfoRow label="Stripe Subscription ID">
              {user.stripe_subscription_id ? (
                <span className="inline-flex items-center gap-1">
                  <code className="text-xs font-mono bg-muted px-1.5 py-0.5 rounded">
                    {truncateId(user.stripe_subscription_id)}
                  </code>
                  <CopyButton text={user.stripe_subscription_id} />
                </span>
              ) : (
                <span className="text-muted-foreground">-</span>
              )}
            </InfoRow>
            <Separator />
            <InfoRow label="請求期間終了">
              {formatDate(user.current_period_end)}
            </InfoRow>
            <Separator />
            <InfoRow label="期末キャンセル">
              {user.cancel_at_period_end ? (
                <Badge variant="destructive" className="text-xs">はい</Badge>
              ) : (
                <span className="text-muted-foreground">いいえ</span>
              )}
            </InfoRow>
            <Separator />
            <InfoRow label="アドオン数量">
              {addon_quantity > 0 ? (
                <span className="font-medium">{addon_quantity} 件</span>
              ) : (
                <span className="text-muted-foreground">0 件</span>
              )}
            </InfoRow>
          </CardContent>
        </Card>

        {/* Usage card */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base">
              <FileText className="h-4 w-4" />
              使用量情報
            </CardTitle>
          </CardHeader>
          <CardContent>
            {usage ? (
              <div className="space-y-4">
                {/* Progress bar */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">記事生成</span>
                    <span className="font-medium">
                      {usage.articles_generated} / {usage.total_limit}
                    </span>
                  </div>
                  <Progress
                    value={usagePercent}
                    className={cn(
                      'h-2',
                      usagePercent >= 90 && '[&>div]:bg-red-500',
                      usagePercent >= 70 && usagePercent < 90 && '[&>div]:bg-amber-500'
                    )}
                  />
                  <p className="text-xs text-muted-foreground text-right">
                    残り {usage.remaining} 件
                  </p>
                </div>

                <Separator />

                <InfoRow label="生成済み記事数">
                  <span className="font-medium">{usage.articles_generated} 件</span>
                </InfoRow>
                <Separator />
                <InfoRow label="基本上限">
                  {usage.articles_limit} 件
                </InfoRow>
                <Separator />
                <InfoRow label="アドオン上限">
                  {usage.addon_articles_limit} 件
                </InfoRow>
                <Separator />
                <InfoRow label="請求期間">
                  {usage.billing_period_start && usage.billing_period_end ? (
                    <span>
                      {formatDate(usage.billing_period_start)} ~ {formatDate(usage.billing_period_end)}
                    </span>
                  ) : (
                    <span className="text-muted-foreground">-</span>
                  )}
                </InfoRow>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center py-8 text-muted-foreground">
                <Clock className="h-8 w-8 mb-2" />
                <p className="text-sm">使用量データなし</p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Organization card */}
        <Card className="md:col-span-2 lg:col-span-1">
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center gap-2 text-base">
              <Building2 className="h-4 w-4" />
              組織情報
            </CardTitle>
          </CardHeader>
          <CardContent>
            {organization_id ? (
              <div className="space-y-0">
                <InfoRow label="組織名">
                  <span className="font-medium">{organization_name || '-'}</span>
                </InfoRow>
                <Separator />
                <InfoRow label="組織ID">
                  <span className="inline-flex items-center gap-1">
                    <code className="text-xs font-mono bg-muted px-1.5 py-0.5 rounded">
                      {truncateId(organization_id)}
                    </code>
                    <CopyButton text={organization_id} />
                  </span>
                </InfoRow>
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center py-8 text-muted-foreground">
                <Building2 className="h-8 w-8 mb-2" />
                <p className="text-sm">組織に未所属</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Generation history table */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <FileText className="h-4 w-4" />
            ブログ生成履歴 (直近20件)
          </CardTitle>
          <CardDescription>
            {generation_history.length} 件の生成履歴
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>プロセスID</TableHead>
                  <TableHead>ステータス</TableHead>
                  <TableHead>作成日時</TableHead>
                  <TableHead>更新日時</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {generation_history.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={4} className="text-center text-muted-foreground py-8">
                      生成履歴がありません
                    </TableCell>
                  </TableRow>
                ) : (
                  generation_history.map((record) => {
                    const genStatus = generationStatusConfig[record.status] || {
                      label: record.status,
                      variant: 'outline' as const,
                    };

                    return (
                      <TableRow key={record.process_id}>
                        <TableCell>
                          <code className="text-xs font-mono bg-muted px-1.5 py-0.5 rounded">
                            {truncateId(record.process_id, 12)}
                          </code>
                        </TableCell>
                        <TableCell>
                          <Badge variant={genStatus.variant}>{genStatus.label}</Badge>
                        </TableCell>
                        <TableCell className="text-sm">
                          {formatDateTime(record.created_at)}
                        </TableCell>
                        <TableCell className="text-sm">
                          {formatDateTime(record.updated_at)}
                        </TableCell>
                      </TableRow>
                    );
                  })
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
