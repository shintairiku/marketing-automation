'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import {
  Activity,
  AlertTriangle,
  ArrowDownRight,
  ArrowUpRight,
  CreditCard,
  FileText,
  Gift,
  Loader2,
  RefreshCw,
  TrendingUp,
  Users,
} from 'lucide-react';
import {
  Area,
  AreaChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Progress } from '@/components/ui/progress';
import { Skeleton } from '@/components/ui/skeleton';
import { cn } from '@/utils/cn';
import { useAuth } from '@clerk/nextjs';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface OverviewStats {
  total_users: number;
  new_users_this_month: number;
  active_subscribers: number;
  privileged_users: number;
  none_users: number;
  total_articles_this_month: number;
  articles_prev_month: number;
  estimated_mrr: number;
}

interface DailyCount {
  date: string;
  count: number;
}

interface GenerationTrend {
  daily: DailyCount[];
  total: number;
}

interface DistributionItem {
  status: string;
  count: number;
  label: string;
}

interface SubscriptionDistribution {
  distribution: DistributionItem[];
}

interface ActivityItem {
  type: string;
  user_id: string;
  user_email: string;
  description: string;
  timestamp: string;
}

interface ActivityResponse {
  activities: ActivityItem[];
}

interface UsageUser {
  user_id: string;
  email: string;
  articles_generated: number;
  total_limit: number;
  usage_percentage: number;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8080';
const USE_PROXY = process.env.NODE_ENV === 'production';
const baseURL = USE_PROXY ? '/api/proxy' : API_BASE_URL;

const CHART_COLORS = {
  orange: '#E5581C',
  amber: '#F59E0B',
  emerald: '#10B981',
  indigo: '#6366F1',
  violet: '#8B5CF6',
  slate: '#94A3B8',
};

const PIE_COLORS: Record<string, string> = {
  active: CHART_COLORS.emerald,
  none: CHART_COLORS.slate,
  privileged: CHART_COLORS.indigo,
  past_due: CHART_COLORS.amber,
  canceled: '#EF4444',
  trialing: CHART_COLORS.violet,
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatYen(amount: number): string {
  return new Intl.NumberFormat('ja-JP', {
    style: 'currency',
    currency: 'JPY',
    maximumFractionDigits: 0,
  }).format(amount);
}

function formatNumber(n: number): string {
  return new Intl.NumberFormat('ja-JP').format(n);
}

function formatShortDate(dateStr: string): string {
  const d = new Date(dateStr);
  return `${d.getMonth() + 1}/${d.getDate()}`;
}

function relativeTime(timestamp: string): string {
  const now = new Date();
  const then = new Date(timestamp);
  const diffMs = now.getTime() - then.getTime();
  const diffMin = Math.floor(diffMs / 60000);

  if (diffMin < 1) return 'たった今';
  if (diffMin < 60) return `${diffMin}分前`;
  const diffHour = Math.floor(diffMin / 60);
  if (diffHour < 24) return `${diffHour}時間前`;
  const diffDay = Math.floor(diffHour / 24);
  if (diffDay < 30) return `${diffDay}日前`;
  return `${Math.floor(diffDay / 30)}ヶ月前`;
}

function growthPercent(current: number, previous: number): number {
  if (previous === 0) return current > 0 ? 100 : 0;
  return Math.round(((current - previous) / previous) * 100);
}

function truncateEmail(email: string, maxLen = 28): string {
  if (email.length <= maxLen) return email;
  const [local, domain] = email.split('@');
  if (!domain) return email.slice(0, maxLen) + '...';
  const keep = maxLen - domain.length - 4;
  if (keep < 3) return email.slice(0, maxLen) + '...';
  return `${local.slice(0, keep)}...@${domain}`;
}

function activityIcon(type: string) {
  switch (type) {
    case 'generation':
      return <FileText className="h-4 w-4 text-custom-orange" />;
    case 'subscription':
      return <CreditCard className="h-4 w-4 text-emerald-500" />;
    case 'signup':
      return <Users className="h-4 w-4 text-indigo-500" />;
    default:
      return <Activity className="h-4 w-4 text-muted-foreground" />;
  }
}

// ---------------------------------------------------------------------------
// Custom hooks
// ---------------------------------------------------------------------------

function useAdminFetch<T>(path: string, getToken: () => Promise<string | null>) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const token = await getToken();
      const res = await fetch(`${baseURL}${path}`, {
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
      });
      if (!res.ok) {
        throw new Error(`API Error: ${res.status} ${res.statusText}`);
      }
      const json = await res.json();
      setData(json);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'データの取得に失敗しました');
    } finally {
      setLoading(false);
    }
  }, [path, getToken]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return { data, loading, error, refetch: fetchData };
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function KpiCardSkeleton() {
  return (
    <Card>
      <CardHeader className="pb-2">
        <Skeleton className="h-4 w-24" />
      </CardHeader>
      <CardContent>
        <Skeleton className="h-8 w-32 mb-2" />
        <Skeleton className="h-3 w-20" />
      </CardContent>
    </Card>
  );
}

function ChartSkeleton({ height = 300 }: { height?: number }) {
  return (
    <Card>
      <CardHeader>
        <Skeleton className="h-5 w-32" />
        <Skeleton className="h-3 w-48" />
      </CardHeader>
      <CardContent>
        <Skeleton className="w-full" style={{ height }} />
      </CardContent>
    </Card>
  );
}

function ListSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <Card>
      <CardHeader>
        <Skeleton className="h-5 w-40" />
      </CardHeader>
      <CardContent className="space-y-4">
        {Array.from({ length: rows }).map((_, i) => (
          <div key={i} className="flex items-center gap-3">
            <Skeleton className="h-8 w-8 rounded-full" />
            <div className="flex-1 space-y-1">
              <Skeleton className="h-3 w-3/4" />
              <Skeleton className="h-3 w-1/2" />
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

function ErrorCard({
  message,
  onRetry,
}: {
  message: string;
  onRetry: () => void;
}) {
  return (
    <Card className="border-destructive/50">
      <CardContent className="flex flex-col items-center justify-center py-10 text-center">
        <AlertTriangle className="h-8 w-8 text-destructive mb-3" />
        <p className="text-sm text-muted-foreground mb-4">{message}</p>
        <button
          onClick={onRetry}
          className="inline-flex items-center gap-2 rounded-md bg-custom-orange px-4 py-2 text-sm font-medium text-white hover:bg-custom-orange/90 transition-colors"
        >
          <RefreshCw className="h-4 w-4" />
          再試行
        </button>
      </CardContent>
    </Card>
  );
}

// ---------------------------------------------------------------------------
// Chart tooltip
// ---------------------------------------------------------------------------

function AreaChartTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: Array<{ value: number }>;
  label?: string;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border bg-background px-3 py-2 shadow-md">
      <p className="text-xs text-muted-foreground mb-1">{label}</p>
      <p className="text-sm font-semibold">
        {formatNumber(payload[0].value)} 件
      </p>
    </div>
  );
}

function PieChartTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: Array<{ name: string; value: number; payload: { label: string } }>;
}) {
  if (!active || !payload?.length) return null;
  const item = payload[0];
  return (
    <div className="rounded-lg border bg-background px-3 py-2 shadow-md">
      <p className="text-xs text-muted-foreground mb-1">
        {item.payload.label}
      </p>
      <p className="text-sm font-semibold">{formatNumber(item.value)} 人</p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page component
// ---------------------------------------------------------------------------

export default function AdminDashboardPage() {
  const { getToken } = useAuth();
  const [grantAmounts, setGrantAmounts] = useState<Record<string, number>>({});
  const [grantingUserId, setGrantingUserId] = useState<string | null>(null);

  const getTokenStable = useCallback(async () => {
    return getToken();
  }, [getToken]);

  const overview = useAdminFetch<OverviewStats>(
    '/admin/stats/overview',
    getTokenStable
  );
  const trend = useAdminFetch<GenerationTrend>(
    '/admin/stats/generation-trend?days=30',
    getTokenStable
  );
  const distribution = useAdminFetch<SubscriptionDistribution>(
    '/admin/stats/subscription-distribution',
    getTokenStable
  );
  const activity = useAdminFetch<ActivityResponse>(
    '/admin/activity/recent?limit=10',
    getTokenStable
  );
  const usage = useAdminFetch<UsageUser[]>(
    '/admin/usage/users',
    getTokenStable
  );

  const handleGrantArticles = useCallback(async (userId: string) => {
    const amount = grantAmounts[userId] || 5;
    if (amount <= 0) return;
    setGrantingUserId(userId);
    try {
      const token = await getToken();
      const res = await fetch(`${baseURL}/admin/users/${userId}/grant-articles`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ amount }),
      });
      if (!res.ok) throw new Error('Failed to grant articles');
      usage.refetch();
      setGrantAmounts((prev) => ({ ...prev, [userId]: 5 }));
    } catch (err) {
      console.error('Failed to grant articles:', err);
    } finally {
      setGrantingUserId(null);
    }
  }, [getToken, grantAmounts, usage]);

  const articleGrowth = useMemo(() => {
    if (!overview.data) return 0;
    return growthPercent(
      overview.data.total_articles_this_month,
      overview.data.articles_prev_month
    );
  }, [overview.data]);

  const highUsageUsers = useMemo(() => {
    if (!usage.data) return [];
    return usage.data
      .filter((u) => u.usage_percentage >= 70)
      .sort((a, b) => b.usage_percentage - a.usage_percentage);
  }, [usage.data]);

  const chartData = useMemo(() => {
    if (!trend.data?.daily) return [];
    return trend.data.daily.map((d) => ({
      ...d,
      label: formatShortDate(d.date),
    }));
  }, [trend.data]);

  const isAllLoading =
    overview.loading &&
    trend.loading &&
    distribution.loading &&
    activity.loading &&
    usage.loading;

  if (isAllLoading) {
    return (
      <div className="space-y-6 p-1">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            管理者ダッシュボード
          </h1>
          <p className="text-muted-foreground text-sm mt-1">
            システム全体の状況を確認できます
          </p>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <KpiCardSkeleton key={i} />
          ))}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="lg:col-span-2">
            <ChartSkeleton />
          </div>
          <ChartSkeleton height={250} />
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <ListSkeleton />
          <ListSkeleton />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 p-1">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            管理者ダッシュボード
          </h1>
          <p className="text-muted-foreground text-sm mt-1">
            システム全体の状況を確認できます
          </p>
        </div>
        <button
          onClick={() => {
            overview.refetch();
            trend.refetch();
            distribution.refetch();
            activity.refetch();
            usage.refetch();
          }}
          className="inline-flex items-center gap-2 rounded-md border px-3 py-2 text-sm font-medium hover:bg-accent transition-colors"
        >
          <RefreshCw className="h-4 w-4" />
          更新
        </button>
      </div>

      {/* KPI Cards */}
      {overview.error ? (
        <ErrorCard message={overview.error} onRetry={overview.refetch} />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Total Users */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardDescription className="text-sm font-medium">
                総ユーザー数
              </CardDescription>
              <Users className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {overview.data
                  ? formatNumber(overview.data.total_users)
                  : '--'}
              </div>
              {overview.data && overview.data.new_users_this_month > 0 && (
                <p className="text-xs text-muted-foreground mt-1 flex items-center gap-1">
                  <ArrowUpRight className="h-3 w-3 text-emerald-500" />
                  <span className="text-emerald-500 font-medium">
                    +{overview.data.new_users_this_month}
                  </span>
                  今月の新規
                </p>
              )}
            </CardContent>
          </Card>

          {/* Active Subscribers */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardDescription className="text-sm font-medium">
                有料会員
              </CardDescription>
              <CreditCard className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {overview.data
                  ? formatNumber(overview.data.active_subscribers)
                  : '--'}
              </div>
              {overview.data && (
                <p className="text-xs text-muted-foreground mt-1">
                  特権: {overview.data.privileged_users} / 未登録:{' '}
                  {overview.data.none_users}
                </p>
              )}
            </CardContent>
          </Card>

          {/* Monthly Articles */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardDescription className="text-sm font-medium">
                月間記事生成
              </CardDescription>
              <FileText className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {overview.data
                  ? formatNumber(overview.data.total_articles_this_month)
                  : '--'}
              </div>
              {overview.data && (
                <p
                  className={cn(
                    'text-xs mt-1 flex items-center gap-1',
                    articleGrowth >= 0 ? 'text-emerald-500' : 'text-red-500'
                  )}
                >
                  {articleGrowth >= 0 ? (
                    <ArrowUpRight className="h-3 w-3" />
                  ) : (
                    <ArrowDownRight className="h-3 w-3" />
                  )}
                  <span className="font-medium">
                    {articleGrowth >= 0 ? '+' : ''}
                    {articleGrowth}%
                  </span>
                  <span className="text-muted-foreground">前月比</span>
                </p>
              )}
            </CardContent>
          </Card>

          {/* Estimated MRR */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardDescription className="text-sm font-medium">
                推定MRR
              </CardDescription>
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {overview.data
                  ? formatYen(overview.data.estimated_mrr)
                  : '--'}
              </div>
              {overview.data && (
                <p className="text-xs text-muted-foreground mt-1">
                  月間定期収益
                </p>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Area Chart: Generation Trend */}
        <div className="lg:col-span-2">
          {trend.error ? (
            <ErrorCard message={trend.error} onRetry={trend.refetch} />
          ) : trend.loading ? (
            <ChartSkeleton />
          ) : (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">記事生成推移</CardTitle>
                <CardDescription>過去30日間の日別生成数</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-[300px] w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart
                      data={chartData}
                      margin={{ top: 5, right: 10, left: -10, bottom: 0 }}
                    >
                      <defs>
                        <linearGradient
                          id="colorCount"
                          x1="0"
                          y1="0"
                          x2="0"
                          y2="1"
                        >
                          <stop
                            offset="5%"
                            stopColor={CHART_COLORS.orange}
                            stopOpacity={0.3}
                          />
                          <stop
                            offset="95%"
                            stopColor={CHART_COLORS.orange}
                            stopOpacity={0}
                          />
                        </linearGradient>
                      </defs>
                      <CartesianGrid
                        strokeDasharray="3 3"
                        className="stroke-muted"
                      />
                      <XAxis
                        dataKey="label"
                        tick={{ fontSize: 11 }}
                        tickLine={false}
                        axisLine={false}
                        interval="preserveStartEnd"
                      />
                      <YAxis
                        tick={{ fontSize: 11 }}
                        tickLine={false}
                        axisLine={false}
                        allowDecimals={false}
                      />
                      <Tooltip
                        content={<AreaChartTooltip />}
                        cursor={{ stroke: CHART_COLORS.orange, strokeWidth: 1 }}
                      />
                      <Area
                        type="monotone"
                        dataKey="count"
                        stroke={CHART_COLORS.orange}
                        strokeWidth={2}
                        fill="url(#colorCount)"
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Pie Chart: Subscription Distribution */}
        <div>
          {distribution.error ? (
            <ErrorCard
              message={distribution.error}
              onRetry={distribution.refetch}
            />
          ) : distribution.loading ? (
            <ChartSkeleton height={250} />
          ) : (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">プラン分布</CardTitle>
                <CardDescription>ユーザーのサブスクリプション状態</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="h-[200px] w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={distribution.data?.distribution || []}
                        cx="50%"
                        cy="50%"
                        innerRadius={50}
                        outerRadius={80}
                        paddingAngle={3}
                        dataKey="count"
                        nameKey="label"
                      >
                        {(distribution.data?.distribution || []).map(
                          (entry) => (
                            <Cell
                              key={entry.status}
                              fill={
                                PIE_COLORS[entry.status] || CHART_COLORS.slate
                              }
                            />
                          )
                        )}
                      </Pie>
                      <Tooltip content={<PieChartTooltip />} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
                {/* Legend */}
                <div className="mt-2 space-y-1.5">
                  {(distribution.data?.distribution || []).map((item) => (
                    <div
                      key={item.status}
                      className="flex items-center justify-between text-sm"
                    >
                      <div className="flex items-center gap-2">
                        <span
                          className="inline-block h-2.5 w-2.5 rounded-full"
                          style={{
                            backgroundColor:
                              PIE_COLORS[item.status] || CHART_COLORS.slate,
                          }}
                        />
                        <span className="text-muted-foreground">
                          {item.label}
                        </span>
                      </div>
                      <span className="font-medium">
                        {formatNumber(item.count)}
                      </span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>

      {/* Bottom Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Recent Activity */}
        {activity.error ? (
          <ErrorCard message={activity.error} onRetry={activity.refetch} />
        ) : activity.loading ? (
          <ListSkeleton />
        ) : (
          <Card>
            <CardHeader>
              <CardTitle className="text-base">最近のアクティビティ</CardTitle>
              <CardDescription>直近の生成・操作ログ</CardDescription>
            </CardHeader>
            <CardContent>
              {!activity.data?.activities?.length ? (
                <p className="text-sm text-muted-foreground text-center py-8">
                  アクティビティはまだありません
                </p>
              ) : (
                <div className="space-y-4">
                  {activity.data.activities.map((item, idx) => (
                    <div key={idx} className="flex items-start gap-3">
                      <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-muted">
                        {activityIcon(item.type)}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm leading-tight">
                          {item.description}
                        </p>
                        <div className="flex items-center gap-2 mt-1">
                          <span className="text-xs text-muted-foreground truncate">
                            {truncateEmail(item.user_email)}
                          </span>
                          <span className="text-xs text-muted-foreground">
                            {relativeTime(item.timestamp)}
                          </span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* Users Near Limit */}
        {usage.error ? (
          <ErrorCard message={usage.error} onRetry={usage.refetch} />
        ) : usage.loading ? (
          <ListSkeleton />
        ) : (
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle className="text-base">上限に近いユーザー</CardTitle>
                <CardDescription>利用率70%以上のユーザー</CardDescription>
              </div>
              <Link
                href="/admin/users"
                className="text-xs font-medium text-custom-orange hover:text-custom-orange/80 transition-colors"
              >
                全ユーザー一覧 →
              </Link>
            </CardHeader>
            <CardContent>
              {highUsageUsers.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-8">
                  上限に近いユーザーはいません
                </p>
              ) : (
                <div className="space-y-4">
                  {highUsageUsers.slice(0, 8).map((user) => (
                    <div key={user.user_id} className="space-y-1.5">
                      <div className="flex items-center justify-between">
                        <Link
                          href={`/admin/users/${user.user_id}`}
                          className="text-sm truncate max-w-[180px] hover:text-custom-orange transition-colors"
                        >
                          {truncateEmail(user.email)}
                        </Link>
                        <div className="flex items-center gap-2">
                          <span className="text-xs text-muted-foreground">
                            {user.articles_generated}/{user.total_limit}
                          </span>
                          <Badge
                            variant={
                              user.usage_percentage >= 90
                                ? 'destructive'
                                : 'secondary'
                            }
                            className={cn(
                              'text-[10px] px-1.5 py-0',
                              user.usage_percentage >= 90
                                ? ''
                                : 'bg-amber-100 text-amber-700 border-amber-200'
                            )}
                          >
                            {Math.round(user.usage_percentage)}%
                          </Badge>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Progress
                          value={user.usage_percentage}
                          className="h-2 flex-1"
                        />
                        <div className="flex items-center gap-1 shrink-0">
                          <Input
                            type="number"
                            min={1}
                            max={100}
                            value={grantAmounts[user.user_id] ?? 5}
                            onChange={(e) =>
                              setGrantAmounts((prev) => ({
                                ...prev,
                                [user.user_id]: parseInt(e.target.value) || 0,
                              }))
                            }
                            className="h-6 w-12 text-xs px-1 text-center"
                          />
                          <Button
                            size="sm"
                            variant="ghost"
                            className="h-6 px-1.5 text-xs gap-0.5"
                            disabled={grantingUserId === user.user_id}
                            onClick={() => handleGrantArticles(user.user_id)}
                          >
                            {grantingUserId === user.user_id ? (
                              <Loader2 className="h-3 w-3 animate-spin" />
                            ) : (
                              <Gift className="h-3 w-3" />
                            )}
                            付与
                          </Button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
