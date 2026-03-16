'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import {
  AlertCircle,
  CheckCircle,
  Clock,
  Crown,
  ExternalLink,
  Loader2,
  RefreshCw,
  Search,
  Shield,
  User,
  XCircle,
} from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { useAuth } from '@clerk/nextjs';

type SubscriptionStatus = 'active' | 'past_due' | 'canceled' | 'expired' | 'none';
type UserRole = 'admin' | 'privileged' | null;

interface UserData {
  id: string;
  full_name: string | null;
  email: string | null;
  created_at: string | null;
  avatar_url: string | null;
  role: UserRole;
  subscription_status: SubscriptionStatus;
  is_privileged: boolean;
  stripe_customer_id: string | null;
  stripe_subscription_id: string | null;
  current_period_end: string | null;
  cancel_at_period_end: boolean;
}

// ステータスバッジのスタイル
const statusConfig: Record<
  SubscriptionStatus,
  { label: string; variant: 'default' | 'secondary' | 'destructive' | 'outline'; icon: typeof CheckCircle }
> = {
  active: { label: 'アクティブ', variant: 'default', icon: CheckCircle },
  past_due: { label: '支払い遅延', variant: 'destructive', icon: AlertCircle },
  canceled: { label: 'キャンセル済み', variant: 'secondary', icon: XCircle },
  expired: { label: '期限切れ', variant: 'destructive', icon: XCircle },
  none: { label: 'なし', variant: 'outline', icon: Clock },
};

// ロールの表示設定
const roleConfig: Record<string, { label: string; variant: 'default' | 'secondary' | 'outline'; className?: string }> = {
  admin: { label: '管理者', variant: 'default', className: 'bg-red-500 hover:bg-red-600' },
  privileged: { label: '特権', variant: 'default', className: 'bg-amber-500 hover:bg-amber-600' },
};

export default function AdminUsersPage() {
  const { getToken } = useAuth();
  const [users, setUsers] = useState<UserData[]>([]);
  const [filteredUsers, setFilteredUsers] = useState<UserData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<SubscriptionStatus | 'all'>('all');

  // 編集用のダイアログ状態
  const [editingUser, setEditingUser] = useState<UserData | null>(null);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [updating, setUpdating] = useState(false);
  const [editForm, setEditForm] = useState({
    role: 'none' as 'admin' | 'privileged' | 'none',
  });

  const fetchUsers = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const token = await getToken();

      const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8080';
      const USE_PROXY = process.env.NODE_ENV === 'production';
      const baseURL = USE_PROXY ? '/api/proxy' : API_BASE_URL;

      const response = await fetch(`${baseURL}/admin/users`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          ...(token && { Authorization: `Bearer ${token}` }),
        },
      });

      if (!response.ok) {
        throw new Error('ユーザー一覧の取得に失敗しました');
      }

      const data = await response.json();
      setUsers(data.users || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'エラーが発生しました');
    } finally {
      setLoading(false);
    }
  }, [getToken]);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  // フィルタリング
  useEffect(() => {
    let result = users;

    // 検索クエリでフィルタ
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      result = result.filter(
        (user) =>
          user.email?.toLowerCase().includes(query) ||
          user.full_name?.toLowerCase().includes(query) ||
          user.id.toLowerCase().includes(query)
      );
    }

    // ステータスでフィルタ
    if (statusFilter !== 'all') {
      result = result.filter((user) => user.subscription_status === statusFilter);
    }

    setFilteredUsers(result);
  }, [users, searchQuery, statusFilter]);

  // ユーザー編集ダイアログを開く
  const openEditDialog = (user: UserData) => {
    setEditingUser(user);
    setEditForm({
      role: user.role || 'none',
    });
    setEditDialogOpen(true);
  };

  // ユーザー情報を更新
  const updateUser = async () => {
    if (!editingUser) return;

    setUpdating(true);
    try {
      const token = await getToken();
      const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8080';
      const USE_PROXY = process.env.NODE_ENV === 'production';
      const baseURL = USE_PROXY ? '/api/proxy' : API_BASE_URL;

      // ロール変更
      const currentRole = editingUser.role || 'none';
      if (editForm.role !== currentRole) {
        const roleResponse = await fetch(
          `${baseURL}/admin/users/${editingUser.id}/role`,
          {
            method: 'PATCH',
            headers: {
              'Content-Type': 'application/json',
              ...(token && { Authorization: `Bearer ${token}` }),
            },
            body: JSON.stringify({
              role: editForm.role === 'none' ? null : editForm.role,
            }),
          }
        );

        if (!roleResponse.ok) {
          const errorData = await roleResponse.json().catch(() => ({}));
          throw new Error(errorData.detail || 'ロールの更新に失敗しました');
        }
      }

      // リストを再読み込み
      await fetchUsers();
      setEditDialogOpen(false);
      setEditingUser(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : '更新に失敗しました');
    } finally {
      setUpdating(false);
    }
  };

  // 統計情報
  const stats = {
    total: users.length,
    active: users.filter((u) => u.subscription_status === 'active').length,
    admin: users.filter((u) => u.role === 'admin').length,
    privileged: users.filter((u) => u.role === 'privileged').length,
    none: users.filter((u) => u.subscription_status === 'none').length,
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold">ユーザー管理</h1>
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold">ユーザー管理</h1>
        <Card className="border-destructive">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-destructive">
              <AlertCircle className="h-5 w-5" />
              エラー
            </CardTitle>
            <CardDescription>{error}</CardDescription>
          </CardHeader>
          <CardContent>
            <Button onClick={fetchUsers} variant="outline">
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
      {/* ヘッダー */}
      <div className="flex items-center justify-between gap-3">
        <h1 className="text-xl sm:text-2xl font-bold">ユーザー管理</h1>
        <Button onClick={fetchUsers} variant="outline" size="sm" className="shrink-0">
          <RefreshCw className="mr-2 h-4 w-4" />
          更新
        </Button>
      </div>

      {/* 統計カード */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-2">
              <User className="h-5 w-5 text-muted-foreground" />
              <div>
                <p className="text-2xl font-bold">{stats.total}</p>
                <p className="text-sm text-muted-foreground">総ユーザー数</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-2">
              <CheckCircle className="h-5 w-5 text-green-600" />
              <div>
                <p className="text-2xl font-bold">{stats.active}</p>
                <p className="text-sm text-muted-foreground">有料会員</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-2">
              <Shield className="h-5 w-5 text-red-500" />
              <div>
                <p className="text-2xl font-bold">{stats.admin}</p>
                <p className="text-sm text-muted-foreground">管理者</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-2">
              <Crown className="h-5 w-5 text-amber-500" />
              <div>
                <p className="text-2xl font-bold">{stats.privileged}</p>
                <p className="text-sm text-muted-foreground">特権</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* フィルター */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col md:flex-row gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="名前、メールアドレス、IDで検索..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10"
              />
            </div>
            <Select
              value={statusFilter}
              onValueChange={(v) => setStatusFilter(v as SubscriptionStatus | 'all')}
            >
              <SelectTrigger className="w-full md:w-48">
                <SelectValue placeholder="ステータスで絞り込み" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">すべてのステータス</SelectItem>
                <SelectItem value="active">アクティブ</SelectItem>
                <SelectItem value="past_due">支払い遅延</SelectItem>
                <SelectItem value="canceled">キャンセル済み</SelectItem>
                <SelectItem value="expired">期限切れ</SelectItem>
                <SelectItem value="none">なし</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* ユーザーテーブル */}
      <Card>
        <CardHeader>
          <CardTitle>登録ユーザー</CardTitle>
          <CardDescription>
            {filteredUsers.length} / {users.length} 件を表示
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="min-w-[160px]">ユーザー</TableHead>
                  <TableHead className="min-w-[140px]">メールアドレス</TableHead>
                  <TableHead>ステータス</TableHead>
                  <TableHead>ロール</TableHead>
                  <TableHead className="whitespace-nowrap">期間終了</TableHead>
                  <TableHead className="whitespace-nowrap">登録日</TableHead>
                  <TableHead className="text-right">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredUsers.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center text-muted-foreground py-8">
                      ユーザーが見つかりません
                    </TableCell>
                  </TableRow>
                ) : (
                  filteredUsers.map((user) => {
                    const statusInfo = statusConfig[user.subscription_status];
                    const StatusIcon = statusInfo.icon;
                    const roleInfo = user.role ? roleConfig[user.role] : null;

                    return (
                      <TableRow key={user.id}>
                        <TableCell>
                          <div className="flex items-center gap-3">
                            {user.avatar_url ? (
                              // eslint-disable-next-line @next/next/no-img-element
                              <img
                                src={user.avatar_url}
                                alt=""
                                className="h-8 w-8 rounded-full"
                              />
                            ) : (
                              <div className="h-8 w-8 rounded-full bg-muted flex items-center justify-center">
                                <User className="h-4 w-4 text-muted-foreground" />
                              </div>
                            )}
                            <div>
                              <p className="font-medium">{user.full_name || '-'}</p>
                              <p className="text-xs text-muted-foreground font-mono">
                                {user.id.slice(0, 12)}...
                              </p>
                            </div>
                          </div>
                        </TableCell>
                        <TableCell>
                          <span className="text-sm">{user.email || '-'}</span>
                        </TableCell>
                        <TableCell>
                          <Badge variant={statusInfo.variant} className="gap-1">
                            <StatusIcon className="h-3 w-3" />
                            {statusInfo.label}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          {roleInfo ? (
                            <Badge variant={roleInfo.variant} className={`gap-1 ${roleInfo.className || ''}`}>
                              {user.role === 'admin' ? <Shield className="h-3 w-3" /> : <Crown className="h-3 w-3" />}
                              {roleInfo.label}
                            </Badge>
                          ) : (
                            <span className="text-sm text-muted-foreground">-</span>
                          )}
                        </TableCell>
                        <TableCell>
                          {user.current_period_end ? (
                            <span className="text-sm">
                              {new Date(user.current_period_end).toLocaleDateString('ja-JP')}
                            </span>
                          ) : (
                            <span className="text-sm text-muted-foreground">-</span>
                          )}
                        </TableCell>
                        <TableCell>
                          {user.created_at ? (
                            <span className="text-sm">
                              {new Date(user.created_at).toLocaleDateString('ja-JP')}
                            </span>
                          ) : (
                            <span className="text-sm text-muted-foreground">-</span>
                          )}
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex items-center justify-end gap-1">
                            <Link href={`/admin/users/${user.id}`}>
                              <Button variant="ghost" size="sm">
                                <ExternalLink className="h-4 w-4 mr-1" />
                                詳細
                              </Button>
                            </Link>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => openEditDialog(user)}
                            >
                              <Shield className="h-4 w-4 mr-1" />
                              編集
                            </Button>
                          </div>
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

      {/* ロール編集ダイアログ */}
      <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>ロール設定</DialogTitle>
            <DialogDescription>
              {editingUser?.full_name || editingUser?.email || editingUser?.id}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="user_role">ロール</Label>
              <Select
                value={editForm.role}
                onValueChange={(v) =>
                  setEditForm({ role: v as 'admin' | 'privileged' | 'none' })
                }
              >
                <SelectTrigger id="user_role">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="admin">管理者 — 管理画面にアクセス可能 + 全機能利用可</SelectItem>
                  <SelectItem value="privileged">特権 — 全機能利用可（管理画面アクセスなし）</SelectItem>
                  <SelectItem value="none">一般ユーザー</SelectItem>
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                変更は Clerk に即時反映されます。ユーザーの次回アクセス時（最大60秒）に適用されます。
              </p>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setEditDialogOpen(false)}>
              キャンセル
            </Button>
            <Button onClick={updateUser} disabled={updating}>
              {updating && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              保存
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
