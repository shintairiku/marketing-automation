'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import {
  Activity,
  ArrowUpDown,
  ChevronDown,
  Database,
  DollarSign,
  Eye,
  FileText,
  Hash,
  Info,
  RefreshCw,
  TrendingUp,
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
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import { Progress } from '@/components/ui/progress';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { useAuth } from '@clerk/nextjs';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface BlogUsageItem {
  process_id: string;
  user_id: string;
  user_email?: string | null;
  status?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  total_tokens: number;
  input_tokens: number;
  output_tokens: number;
  cached_tokens: number;
  reasoning_tokens: number;
  estimated_cost_usd: number;
  tool_calls: number;
  models: string[];
}


// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8080';
const USE_PROXY = process.env.NODE_ENV === 'production';
const baseURL = USE_PROXY ? '/api/proxy' : API_BASE_URL;

const CHART_COLORS = [
  '#E5581C', '#FFA726', '#66BB6A', '#42A5F5',
  '#AB47BC', '#78909C', '#EC407A', '#26A69A',
];

const MODEL_PRICING_REF = [
  { category: 'GPT-5', model: 'gpt-5', input: 1.25, cached: 0.125, output: 10.00 },
  { category: 'GPT-5', model: 'gpt-5.1', input: 1.25, cached: 0.125, output: 10.00 },
  { category: 'GPT-5', model: 'gpt-5.2', input: 1.75, cached: 0.175, output: 14.00 },
  { category: 'GPT-5', model: 'gpt-5-mini', input: 0.25, cached: 0.025, output: 2.00 },
  { category: 'GPT-5', model: 'gpt-5-nano', input: 0.05, cached: 0.005, output: 0.40 },
  { category: 'GPT-4.1', model: 'gpt-4.1', input: 2.00, cached: 0.50, output: 8.00 },
  { category: 'GPT-4.1', model: 'gpt-4.1-mini', input: 0.40, cached: 0.10, output: 1.60 },
  { category: 'GPT-4.1', model: 'gpt-4.1-nano', input: 0.10, cached: 0.025, output: 0.40 },
  { category: 'GPT-4o', model: 'gpt-4o', input: 2.50, cached: 1.25, output: 10.00 },
  { category: 'GPT-4o', model: 'gpt-4o-mini', input: 0.15, cached: 0.075, output: 0.60 },
  { category: 'Gemini', model: 'gemini-2.5-pro', input: 1.25, cached: 0.125, output: 10.00 },
  { category: 'Anthropic', model: 'claude-4-sonnet', input: 3.00, cached: 0.30, output: 15.00 },
];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatNumber(value: number): string {
  return new Intl.NumberFormat('ja-JP').format(value || 0);
}

function formatUsd(value: number, digits = 4): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: digits,
  }).format(value || 0);
}

function formatDate(value?: string | null): string {
  if (!value) return '-';
  return new Date(value).toLocaleDateString('ja-JP', {
    month: 'numeric',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function truncateId(id: string, length = 8): string {
  if (!id) return '-';
  return id.length <= length ? id : `${id.slice(0, length)}…`;
}

function shortenModel(name: string): string {
  return name
    .replace('litellm/gemini/', '')
    .replace('litellm/anthropic/', '')
    .replace('litellm/', '');
}

function getStatusStyle(status?: string | null): string {
  switch (status) {
    case 'completed':
      return 'bg-emerald-50 text-emerald-700 border-emerald-200';
    case 'failed':
    case 'error':
      return 'bg-red-50 text-red-700 border-red-200';
    case 'in_progress':
    case 'pending':
      return 'bg-blue-50 text-blue-700 border-blue-200';
    case 'cancelled':
      return 'bg-stone-100 text-stone-500 border-stone-200';
    default:
      return 'bg-stone-100 text-stone-500 border-stone-200';
  }
}

function getCostStyle(cost: number): string {
  if (cost > 1.0) return 'bg-red-50 text-red-700 border-red-200';
  if (cost > 0.3) return 'bg-amber-50 text-amber-700 border-amber-200';
  return 'bg-emerald-50 text-emerald-700 border-emerald-200';
}

// ---------------------------------------------------------------------------
// Custom Tooltips
// ---------------------------------------------------------------------------

function CostTrendTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="rounded-lg border bg-white px-3 py-2 shadow-md text-xs">
      <p className="font-medium text-stone-700 mb-1">{label}</p>
      <p className="text-stone-500">コスト: <span className="font-semibold text-stone-800">{formatUsd(d.cost)}</span></p>
      <p className="text-stone-500">トークン: {formatNumber(d.tokens)}</p>
      <p className="text-stone-500">記事数: {d.count}</p>
    </div>
  );
}

function ModelCostTooltip({ active, payload }: any) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="rounded-lg border bg-white px-3 py-2 shadow-md text-xs">
      <p className="font-medium text-stone-700 mb-1">{d.model}</p>
      <p className="text-stone-500">コスト: <span className="font-semibold text-stone-800">{formatUsd(d.cost)}</span></p>
      <p className="text-stone-500">トークン: {formatNumber(d.tokens)}</p>
      <p className="text-stone-500">使用回数: {d.count}回</p>
      <p className="text-stone-500">割合: {d.percentage.toFixed(1)}%</p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function AdminBlogUsagePage() {
  const { getToken } = useAuth();
  const [items, setItems] = useState<BlogUsageItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [days, setDays] = useState('30');
  const [sortKey, setSortKey] = useState<'created_at' | 'estimated_cost_usd' | 'total_tokens'>('created_at');
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');
  const [pricingOpen, setPricingOpen] = useState(false);

  // ---- Fetch ----
  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const token = await getToken();
      const response = await fetch(
        `${baseURL}/admin/usage/blog?limit=500&days=${days}`,
        {
          headers: {
            'Content-Type': 'application/json',
            ...(token && { Authorization: `Bearer ${token}` }),
          },
        }
      );
      if (!response.ok) throw new Error('Blog usage の取得に失敗しました');
      const data: BlogUsageItem[] = await response.json();
      setItems(data || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'エラーが発生しました');
    } finally {
      setLoading(false);
    }
  }, [getToken, days]);


  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // ---- KPI Stats ----
  const stats = useMemo(() => {
    const totalCost = items.reduce((s, i) => s + (i.estimated_cost_usd || 0), 0);
    const totalTokens = items.reduce((s, i) => s + (i.total_tokens || 0), 0);
    const totalInput = items.reduce((s, i) => s + (i.input_tokens || 0), 0);
    const totalCached = items.reduce((s, i) => s + (i.cached_tokens || 0), 0);
    const count = items.length;
    const avgCost = count > 0 ? totalCost / count : 0;
    const cacheRate = (totalInput + totalCached) > 0
      ? (totalCached / (totalInput + totalCached)) * 100
      : 0;
    return { totalCost, totalTokens, avgCost, cacheRate, count, totalCached };
  }, [items]);

  // ---- Daily Trend ----
  const dailyTrend = useMemo(() => {
    const map = new Map<string, { cost: number; tokens: number; count: number }>();
    items.forEach((item) => {
      if (!item.created_at) return;
      const date = new Date(item.created_at).toLocaleDateString('ja-JP', {
        month: 'numeric',
        day: 'numeric',
      });
      const dateKey = item.created_at.split('T')[0];
      const existing = map.get(dateKey) || { cost: 0, tokens: 0, count: 0, label: date };
      map.set(dateKey, {
        cost: existing.cost + (item.estimated_cost_usd || 0),
        tokens: existing.tokens + (item.total_tokens || 0),
        count: existing.count + 1,
      });
    });
    return Array.from(map.entries())
      .map(([dateKey, data]) => ({
        date: new Date(dateKey).toLocaleDateString('ja-JP', { month: 'numeric', day: 'numeric' }),
        ...data,
      }))
      .sort((a, b) => a.date.localeCompare(b.date));
  }, [items]);

  // ---- Model Breakdown ----
  const modelBreakdown = useMemo(() => {
    const map = new Map<string, { cost: number; tokens: number; count: number }>();
    items.forEach((item) => {
      const models = item.models?.length ? item.models : ['unknown'];
      const share = 1 / models.length;
      models.forEach((m) => {
        const existing = map.get(m) || { cost: 0, tokens: 0, count: 0 };
        map.set(m, {
          cost: existing.cost + (item.estimated_cost_usd || 0) * share,
          tokens: existing.tokens + (item.total_tokens || 0) * share,
          count: existing.count + 1,
        });
      });
    });
    const total = Array.from(map.values()).reduce((s, v) => s + v.cost, 0);
    return Array.from(map.entries())
      .map(([model, data]) => ({
        model: shortenModel(model),
        ...data,
        percentage: total > 0 ? (data.cost / total) * 100 : 0,
      }))
      .sort((a, b) => b.cost - a.cost);
  }, [items]);

  // ---- User Breakdown ----
  const userBreakdown = useMemo(() => {
    const map = new Map<string, { email: string; cost: number; tokens: number; count: number }>();
    items.forEach((item) => {
      const existing = map.get(item.user_id) || {
        email: item.user_email || truncateId(item.user_id),
        cost: 0,
        tokens: 0,
        count: 0,
      };
      map.set(item.user_id, {
        email: existing.email,
        cost: existing.cost + (item.estimated_cost_usd || 0),
        tokens: existing.tokens + (item.total_tokens || 0),
        count: existing.count + 1,
      });
    });
    const total = Array.from(map.values()).reduce((s, v) => s + v.cost, 0);
    return Array.from(map.entries())
      .map(([userId, data]) => ({
        userId,
        ...data,
        avgCost: data.count > 0 ? data.cost / data.count : 0,
        percentage: total > 0 ? (data.cost / total) * 100 : 0,
      }))
      .sort((a, b) => b.cost - a.cost)
      .slice(0, 10);
  }, [items]);

  // ---- Sorted Items ----
  const sortedItems = useMemo(() => {
    return [...items].sort((a, b) => {
      const av = a[sortKey] ?? '';
      const bv = b[sortKey] ?? '';
      if (sortDir === 'asc') return av > bv ? 1 : -1;
      return av < bv ? 1 : -1;
    });
  }, [items, sortKey, sortDir]);


  const handleSort = (key: typeof sortKey) => {
    if (sortKey === key) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      setSortDir('desc');
    }
  };

  const renderSortIcon = (key: typeof sortKey) => (
    <ArrowUpDown className={`inline w-3 h-3 ml-1 ${sortKey === key ? 'text-stone-800' : 'text-stone-300'}`} />
  );

  // ---- Pie chart label ----
  const renderPieLabel = ({ model, percentage, cx, x }: any) => {
    if (percentage < 5) return null;
    return (
      <text
        x={x}
        y={0}
        textAnchor={x > cx ? 'start' : 'end'}
        dominantBaseline="central"
        className="text-[11px] fill-stone-600"
      >
        {model} ({percentage.toFixed(0)}%)
      </text>
    );
  };

  // ===========================================================================
  // Loading
  // ===========================================================================
  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <Skeleton className="h-8 w-64" />
          <Skeleton className="h-9 w-24" />
        </div>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          {[...Array(5)].map((_, i) => (
            <Card key={i}><CardHeader className="pb-2"><Skeleton className="h-4 w-20" /></CardHeader><CardContent><Skeleton className="h-7 w-full" /></CardContent></Card>
          ))}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Skeleton className="h-[300px] rounded-xl" />
          <Skeleton className="h-[300px] rounded-xl" />
        </div>
        <Skeleton className="h-[200px] rounded-xl" />
      </div>
    );
  }

  // ===========================================================================
  // Error
  // ===========================================================================
  if (error) {
    return (
      <Card className="border-red-200">
        <CardContent className="pt-6">
          <div className="flex items-center gap-2 text-red-600 mb-2">
            <Activity className="h-5 w-5" />
            <p className="font-semibold">データ取得エラー</p>
          </div>
          <p className="text-sm text-muted-foreground">{error}</p>
          <Button onClick={fetchData} variant="outline" size="sm" className="mt-4">
            <RefreshCw className="h-4 w-4 mr-2" />
            再試行
          </Button>
        </CardContent>
      </Card>
    );
  }

  // ===========================================================================
  // Main Render
  // ===========================================================================
  return (
    <div className="space-y-6">
      {/* ---- Header ---- */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Blog AI Usage</h2>
          <p className="text-sm text-muted-foreground">
            コスト・トークン使用量・モデル別分析
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Select value={days} onValueChange={setDays}>
            <SelectTrigger className="w-[120px] h-9">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="7">7日間</SelectItem>
              <SelectItem value="30">30日間</SelectItem>
              <SelectItem value="90">90日間</SelectItem>
              <SelectItem value="365">全期間</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="outline" size="sm" onClick={fetchData} className="h-9">
            <RefreshCw className="h-4 w-4 mr-1.5" />
            更新
          </Button>
        </div>
      </div>

      {/* ---- KPI Cards ---- */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-xs font-medium text-muted-foreground">総コスト</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-xl font-bold tabular-nums">{formatUsd(stats.totalCost)}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-xs font-medium text-muted-foreground">総トークン</CardTitle>
            <Hash className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-xl font-bold tabular-nums">{formatNumber(stats.totalTokens)}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-xs font-medium text-muted-foreground">平均/記事</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-xl font-bold tabular-nums">{formatUsd(stats.avgCost)}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-xs font-medium text-muted-foreground">キャッシュ率</CardTitle>
            <Database className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-xl font-bold tabular-nums">{stats.cacheRate.toFixed(1)}%</div>
            <Progress value={stats.cacheRate} className="mt-1.5 h-1.5" />
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-xs font-medium text-muted-foreground">記事数</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-xl font-bold tabular-nums">{formatNumber(stats.count)}</div>
          </CardContent>
        </Card>
      </div>

      {/* ---- Charts ---- */}
      {items.length > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Daily Cost Trend */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">日別コスト推移</CardTitle>
            </CardHeader>
            <CardContent>
              {dailyTrend.length > 1 ? (
                <ResponsiveContainer width="100%" height={260}>
                  <AreaChart data={dailyTrend} margin={{ top: 5, right: 5, left: -10, bottom: 0 }}>
                    <defs>
                      <linearGradient id="costGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#E5581C" stopOpacity={0.25} />
                        <stop offset="95%" stopColor="#E5581C" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e5e5" />
                    <XAxis dataKey="date" tick={{ fontSize: 11 }} stroke="#a3a3a3" />
                    <YAxis tick={{ fontSize: 11 }} stroke="#a3a3a3" tickFormatter={(v: number) => `$${v.toFixed(2)}`} />
                    <Tooltip content={<CostTrendTooltip />} />
                    <Area
                      type="monotone"
                      dataKey="cost"
                      stroke="#E5581C"
                      strokeWidth={2}
                      fillOpacity={1}
                      fill="url(#costGrad)"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex items-center justify-center h-[260px] text-sm text-muted-foreground">
                  データが不足しています
                </div>
              )}
            </CardContent>
          </Card>

          {/* Model Cost Distribution */}
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">モデル別コスト配分</CardTitle>
            </CardHeader>
            <CardContent>
              {modelBreakdown.length > 0 ? (
                <div className="flex flex-col lg:flex-row items-center gap-4">
                  <ResponsiveContainer width="100%" height={260}>
                    <PieChart>
                      <Pie
                        data={modelBreakdown}
                        cx="50%"
                        cy="50%"
                        innerRadius={55}
                        outerRadius={95}
                        paddingAngle={2}
                        dataKey="cost"
                        label={renderPieLabel}
                      >
                        {modelBreakdown.map((_, index) => (
                          <Cell key={index} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip content={<ModelCostTooltip />} />
                    </PieChart>
                  </ResponsiveContainer>
                  {/* Legend */}
                  <div className="flex flex-wrap lg:flex-col gap-1.5 text-xs min-w-[140px]">
                    {modelBreakdown.slice(0, 8).map((entry, i) => (
                      <div key={entry.model} className="flex items-center gap-1.5">
                        <span
                          className="w-2.5 h-2.5 rounded-sm flex-shrink-0"
                          style={{ backgroundColor: CHART_COLORS[i % CHART_COLORS.length] }}
                        />
                        <span className="text-stone-600 truncate">{entry.model}</span>
                        <span className="text-stone-400 ml-auto tabular-nums">{formatUsd(entry.cost, 2)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="flex items-center justify-center h-[260px] text-sm text-muted-foreground">
                  データがありません
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {/* ---- User Breakdown ---- */}
      {userBreakdown.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">ユーザー別コスト (Top 10)</CardTitle>
          </CardHeader>
          <CardContent className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="text-xs">ユーザー</TableHead>
                  <TableHead className="text-xs text-right">記事数</TableHead>
                  <TableHead className="text-xs text-right">総コスト</TableHead>
                  <TableHead className="text-xs text-right">平均/記事</TableHead>
                  <TableHead className="text-xs w-[180px]">コスト割合</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {userBreakdown.map((user) => (
                  <TableRow key={user.userId}>
                    <TableCell className="text-xs font-medium">{user.email}</TableCell>
                    <TableCell className="text-xs text-right tabular-nums">{user.count}</TableCell>
                    <TableCell className="text-xs text-right tabular-nums font-medium">{formatUsd(user.cost)}</TableCell>
                    <TableCell className="text-xs text-right tabular-nums">{formatUsd(user.avgCost)}</TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <Progress value={user.percentage} className="h-1.5 flex-1" />
                        <span className="text-[11px] text-muted-foreground tabular-nums w-10 text-right">
                          {user.percentage.toFixed(0)}%
                        </span>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* ---- Model Pricing Reference ---- */}
      <Collapsible open={pricingOpen} onOpenChange={setPricingOpen}>
        <Card>
          <CollapsibleTrigger asChild>
            <button
              type="button"
              className="w-full flex items-center justify-between px-6 py-4 text-left hover:bg-muted/50 transition-colors"
            >
              <div className="flex items-center gap-2">
                <Info className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm font-medium">モデル料金リファレンス (per 1M tokens)</span>
              </div>
              <ChevronDown
                className={`h-4 w-4 text-muted-foreground transition-transform ${
                  pricingOpen ? 'rotate-180' : ''
                }`}
              />
            </button>
          </CollapsibleTrigger>
          <CollapsibleContent>
            <div className="px-6 pb-4 overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="text-xs">カテゴリ</TableHead>
                    <TableHead className="text-xs">モデル</TableHead>
                    <TableHead className="text-xs text-right">Input</TableHead>
                    <TableHead className="text-xs text-right">Cached</TableHead>
                    <TableHead className="text-xs text-right">Output</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {MODEL_PRICING_REF.map((row) => (
                    <TableRow key={row.model}>
                      <TableCell className="text-xs text-muted-foreground">{row.category}</TableCell>
                      <TableCell className="text-xs font-mono">{row.model}</TableCell>
                      <TableCell className="text-xs text-right tabular-nums">${row.input.toFixed(2)}</TableCell>
                      <TableCell className="text-xs text-right tabular-nums">${row.cached.toFixed(3)}</TableCell>
                      <TableCell className="text-xs text-right tabular-nums">${row.output.toFixed(2)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              <p className="text-[11px] text-muted-foreground mt-3">
                最終更新: 2026-02 — 公式価格は OpenAI / Google AI / Anthropic の各 Pricing ページを参照
              </p>
            </div>
          </CollapsibleContent>
        </Card>
      </Collapsible>

      {/* ---- Article Usage Table ---- */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 text-sm font-medium">
            <Activity className="h-4 w-4" />
            記事別 Usage 一覧
            <span className="text-xs text-muted-foreground font-normal">({items.length}件)</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          {items.length === 0 ? (
            <div className="text-sm text-muted-foreground py-10 text-center">
              この期間のデータはありません
            </div>
          ) : (
            <div className="overflow-x-auto -mx-6">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead
                      className="text-xs cursor-pointer hover:text-stone-800 select-none"
                      onClick={() => handleSort('created_at')}
                    >
                      日時{renderSortIcon('created_at')}
                    </TableHead>
                    <TableHead className="text-xs">ユーザー</TableHead>
                    <TableHead className="text-xs">ステータス</TableHead>
                    <TableHead
                      className="text-xs text-right cursor-pointer hover:text-stone-800 select-none"
                      onClick={() => handleSort('estimated_cost_usd')}
                    >
                      コスト{renderSortIcon('estimated_cost_usd')}
                    </TableHead>
                    <TableHead
                      className="text-xs text-right cursor-pointer hover:text-stone-800 select-none"
                      onClick={() => handleSort('total_tokens')}
                    >
                      トークン{renderSortIcon('total_tokens')}
                    </TableHead>
                    <TableHead className="text-xs text-right">入力/出力</TableHead>
                    <TableHead className="text-xs text-right">キャッシュ</TableHead>
                    <TableHead className="text-xs text-right">ツール</TableHead>
                    <TableHead className="text-xs">モデル</TableHead>
                    <TableHead className="text-xs text-right">詳細</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {sortedItems.map((item) => (
                    <TableRow key={item.process_id}>
                      <TableCell className="text-xs text-muted-foreground whitespace-nowrap">
                        {formatDate(item.created_at)}
                      </TableCell>
                      <TableCell className="text-xs max-w-[120px] truncate">
                        {item.user_email || truncateId(item.user_id)}
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant="outline"
                          className={`text-[10px] px-1.5 py-0 ${getStatusStyle(item.status)}`}
                        >
                          {item.status || '-'}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right">
                        <Badge
                          variant="outline"
                          className={`text-[10px] px-1.5 py-0 tabular-nums font-medium ${getCostStyle(item.estimated_cost_usd)}`}
                        >
                          {formatUsd(item.estimated_cost_usd)}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-xs text-right tabular-nums">
                        {formatNumber(item.total_tokens)}
                      </TableCell>
                      <TableCell className="text-xs text-right tabular-nums text-muted-foreground">
                        {formatNumber(item.input_tokens)}/{formatNumber(item.output_tokens)}
                      </TableCell>
                      <TableCell className="text-xs text-right tabular-nums text-muted-foreground">
                        {formatNumber(item.cached_tokens)}
                      </TableCell>
                      <TableCell className="text-xs text-right tabular-nums text-muted-foreground">
                        {item.tool_calls || 0}
                      </TableCell>
                      <TableCell className="text-xs max-w-[160px]">
                        <div className="flex flex-wrap gap-1">
                          {(item.models || []).map((m, i) => (
                            <span
                              key={i}
                              className="inline-block px-1.5 py-0.5 rounded bg-stone-100 text-stone-600 text-[10px] font-mono leading-none"
                            >
                              {shortenModel(m)}
                            </span>
                          ))}
                        </div>
                      </TableCell>
                      <TableCell className="text-right">
                        <Button size="sm" variant="outline" className="h-7 px-2 text-[11px]" asChild>
                          <Link href={`/admin/blog-usage/${item.process_id}`}>
                            <Eye className="h-3 w-3 mr-1" />
                            詳細
                          </Link>
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

    </div>
  );
}
