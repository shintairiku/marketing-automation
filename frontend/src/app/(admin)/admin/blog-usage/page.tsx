'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { Activity, Loader2, RefreshCw } from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { useAuth } from '@clerk/nextjs';

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

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8080';
const USE_PROXY = process.env.NODE_ENV === 'production';
const baseURL = USE_PROXY ? '/api/proxy' : API_BASE_URL;

function truncateId(id: string, length = 12): string {
  if (!id) return '-';
  if (id.length <= length) return id;
  return `${id.slice(0, length)}...`;
}

function formatNumber(value: number): string {
  return new Intl.NumberFormat('ja-JP').format(value || 0);
}

function formatUsd(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 6,
  }).format(value || 0);
}

function formatDate(value?: string | null): string {
  if (!value) return '-';
  return new Date(value).toLocaleString('ja-JP');
}

export default function AdminBlogUsagePage() {
  const { getToken } = useAuth();
  const [items, setItems] = useState<BlogUsageItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const token = await getToken();
      const response = await fetch(`${baseURL}/admin/usage/blog?limit=100`, {
        headers: {
          'Content-Type': 'application/json',
          ...(token && { Authorization: `Bearer ${token}` }),
        },
      });
      if (!response.ok) {
        throw new Error('Blog usage の取得に失敗しました');
      }
      const data: BlogUsageItem[] = await response.json();
      setItems(data || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'エラーが発生しました');
    } finally {
      setLoading(false);
    }
  }, [getToken]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const totalTokens = useMemo(
    () => items.reduce((sum, item) => sum + (item.total_tokens || 0), 0),
    [items]
  );
  const totalCost = useMemo(
    () => items.reduce((sum, item) => sum + (item.estimated_cost_usd || 0), 0),
    [items]
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Blog AI 記事別 Usage</h2>
          <p className="text-sm text-muted-foreground">
            Blog AI のプロセス単位でトークン使用量とコストを確認できます。
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={fetchData}>
          <RefreshCw className="h-4 w-4 mr-2" />
          更新
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground">
              合計トークン
            </CardTitle>
          </CardHeader>
          <CardContent className="text-2xl font-semibold">
            {formatNumber(totalTokens)}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground">
              推定コスト合計
            </CardTitle>
          </CardHeader>
          <CardContent className="text-2xl font-semibold">
            {formatUsd(totalCost)}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground">
              プロセス数
            </CardTitle>
          </CardHeader>
          <CardContent className="text-2xl font-semibold">
            {formatNumber(items.length)}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 text-base">
            <Activity className="h-4 w-4" />
            記事別 Usage 一覧
          </CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex items-center justify-center py-10 text-muted-foreground">
              <Loader2 className="h-5 w-5 animate-spin mr-2" />
              読み込み中...
            </div>
          ) : error ? (
            <div className="text-sm text-red-500">{error}</div>
          ) : items.length === 0 ? (
            <div className="text-sm text-muted-foreground py-6 text-center">
              データがありません
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>作成日時</TableHead>
                  <TableHead>プロセスID</TableHead>
                  <TableHead>ユーザー</TableHead>
                  <TableHead>ステータス</TableHead>
                  <TableHead>入力/出力/総計</TableHead>
                  <TableHead>キャッシュ/推論</TableHead>
                  <TableHead>推定コスト</TableHead>
                  <TableHead>ツール回数</TableHead>
                  <TableHead>モデル</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map((item) => (
                  <TableRow key={item.process_id}>
                    <TableCell className="text-xs">
                      {formatDate(item.created_at)}
                    </TableCell>
                    <TableCell className="font-mono text-xs">
                      {truncateId(item.process_id)}
                    </TableCell>
                    <TableCell className="text-xs">
                      {item.user_email || truncateId(item.user_id)}
                    </TableCell>
                    <TableCell>
                      <Badge variant="secondary" className="text-xs">
                        {item.status || '-'}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-xs">
                      {formatNumber(item.input_tokens)} / {formatNumber(item.output_tokens)} /{' '}
                      {formatNumber(item.total_tokens)}
                    </TableCell>
                    <TableCell className="text-xs">
                      {formatNumber(item.cached_tokens)} / {formatNumber(item.reasoning_tokens)}
                    </TableCell>
                    <TableCell className="text-xs">
                      {item.estimated_cost_usd ? formatUsd(item.estimated_cost_usd) : '-'}
                    </TableCell>
                    <TableCell className="text-xs">
                      {formatNumber(item.tool_calls)}
                    </TableCell>
                    <TableCell className="text-xs">
                      {item.models && item.models.length > 0 ? item.models.join(', ') : '-'}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
