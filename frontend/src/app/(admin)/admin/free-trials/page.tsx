'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import {
  AlertCircle,
  Calendar,
  Gift,
  Loader2,
  RefreshCw,
  XCircle,
} from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
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

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface FreeTrialGrant {
  id: string;
  user_id: string;
  stripe_coupon_id: string;
  duration_months: number;
  status: 'pending' | 'active' | 'expired' | 'revoked';
  granted_by: string;
  note: string | null;
  created_at: string;
  used_at: string | null;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatDate(dateStr: string | null): string {
  if (!dateStr) return '-';
  return new Date(dateStr).toLocaleDateString('ja-JP');
}

function formatDateTime(dateStr: string | null): string {
  if (!dateStr) return '-';
  return new Date(dateStr).toLocaleString('ja-JP');
}

function truncateId(id: string, length = 12): string {
  if (id.length <= length) return id;
  return `${id.slice(0, length)}...`;
}

const statusConfig: Record<
  FreeTrialGrant['status'],
  { label: string; variant: 'default' | 'secondary' | 'destructive' | 'outline' }
> = {
  pending: { label: '未使用', variant: 'secondary' },
  active: { label: '利用中', variant: 'default' },
  expired: { label: '期限切れ', variant: 'outline' },
  revoked: { label: '取り消し', variant: 'destructive' },
};

// ---------------------------------------------------------------------------
// Filter tabs
// ---------------------------------------------------------------------------

type FilterStatus = 'all' | FreeTrialGrant['status'];

const filterTabs: { value: FilterStatus; label: string }[] = [
  { value: 'all', label: 'すべて' },
  { value: 'pending', label: '未使用' },
  { value: 'active', label: '利用中' },
  { value: 'expired', label: '期限切れ' },
  { value: 'revoked', label: '取り消し' },
];

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

export default function FreeTrialsPage() {
  const [grants, setGrants] = useState<FreeTrialGrant[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<FilterStatus>('all');

  const fetchGrants = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await fetch('/api/admin/free-trials');
      if (!res.ok) throw new Error('取得に失敗しました');
      const json = await res.json();
      setGrants(json.grants || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'エラーが発生しました');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchGrants();
  }, [fetchGrants]);

  const handleRevoke = async (grantId: string) => {
    try {
      const res = await fetch(`/api/admin/free-trials/${grantId}`, {
        method: 'DELETE',
      });
      if (res.ok || res.status === 204) {
        await fetchGrants();
      }
    } catch {
      // ignore
    }
  };

  const filteredGrants = filter === 'all'
    ? grants
    : grants.filter((g) => g.status === filter);

  const countByStatus = {
    all: grants.length,
    pending: grants.filter((g) => g.status === 'pending').length,
    active: grants.filter((g) => g.status === 'active').length,
    expired: grants.filter((g) => g.status === 'expired').length,
    revoked: grants.filter((g) => g.status === 'revoked').length,
  };

  // -- Loading state --
  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-3">
          <Gift className="h-6 w-6" />
          <h1 className="text-2xl font-bold">フリートライアル管理</h1>
        </div>
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-12 w-full" />
          ))}
        </div>
      </div>
    );
  }

  // -- Error state --
  if (error) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-3">
          <Gift className="h-6 w-6" />
          <h1 className="text-2xl font-bold">フリートライアル管理</h1>
        </div>
        <Card className="border-destructive">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-destructive">
              <AlertCircle className="h-5 w-5" />
              エラー
            </CardTitle>
            <CardDescription>{error}</CardDescription>
          </CardHeader>
          <CardContent>
            <Button onClick={fetchGrants} variant="outline">
              <RefreshCw className="mr-2 h-4 w-4" />
              再読み込み
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Gift className="h-6 w-6" />
          <div>
            <h1 className="text-2xl font-bold">フリートライアル管理</h1>
            <p className="text-sm text-muted-foreground">
              {grants.length} 件の付与履歴
            </p>
          </div>
        </div>
        <Button variant="outline" size="sm" onClick={fetchGrants}>
          <RefreshCw className="mr-2 h-4 w-4" />
          更新
        </Button>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold">{countByStatus.pending}</div>
            <p className="text-xs text-muted-foreground">未使用</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold text-green-600">{countByStatus.active}</div>
            <p className="text-xs text-muted-foreground">利用中</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold text-muted-foreground">{countByStatus.expired}</div>
            <p className="text-xs text-muted-foreground">期限切れ</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="text-2xl font-bold text-red-500">{countByStatus.revoked}</div>
            <p className="text-xs text-muted-foreground">取り消し</p>
          </CardContent>
        </Card>
      </div>

      {/* Filter tabs */}
      <div className="flex gap-1 border-b">
        {filterTabs.map((tab) => (
          <button
            key={tab.value}
            className={cn(
              'px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px',
              filter === tab.value
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            )}
            onClick={() => setFilter(tab.value)}
          >
            {tab.label}
            {countByStatus[tab.value] > 0 && (
              <span className="ml-1.5 text-xs text-muted-foreground">
                ({countByStatus[tab.value]})
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Grants table */}
      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>ユーザーID</TableHead>
                  <TableHead>期間</TableHead>
                  <TableHead>ステータス</TableHead>
                  <TableHead>付与日</TableHead>
                  <TableHead>使用日</TableHead>
                  <TableHead>メモ</TableHead>
                  <TableHead className="w-[60px]"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredGrants.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center text-muted-foreground py-12">
                      <Gift className="h-8 w-8 mx-auto mb-2 opacity-50" />
                      <p>該当するトライアルがありません</p>
                    </TableCell>
                  </TableRow>
                ) : (
                  filteredGrants.map((grant) => {
                    const config = statusConfig[grant.status];
                    return (
                      <TableRow key={grant.id}>
                        <TableCell>
                          <Link
                            href={`/admin/users/${grant.user_id}`}
                            className="text-sm font-mono hover:underline text-primary"
                          >
                            {truncateId(grant.user_id)}
                          </Link>
                        </TableCell>
                        <TableCell>
                          <span className="text-sm font-medium">
                            {grant.duration_months}ヶ月
                          </span>
                        </TableCell>
                        <TableCell>
                          <Badge variant={config.variant}>{config.label}</Badge>
                        </TableCell>
                        <TableCell className="text-sm text-muted-foreground">
                          <span className="flex items-center gap-1">
                            <Calendar className="h-3 w-3" />
                            {formatDate(grant.created_at)}
                          </span>
                        </TableCell>
                        <TableCell className="text-sm text-muted-foreground">
                          {grant.used_at ? formatDateTime(grant.used_at) : '-'}
                        </TableCell>
                        <TableCell className="text-sm text-muted-foreground max-w-[200px] truncate">
                          {grant.note || '-'}
                        </TableCell>
                        <TableCell>
                          {grant.status === 'pending' && (
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-8 w-8 text-red-500 hover:text-red-700 hover:bg-red-50"
                              onClick={() => handleRevoke(grant.id)}
                            >
                              <XCircle className="h-4 w-4" />
                            </Button>
                          )}
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
