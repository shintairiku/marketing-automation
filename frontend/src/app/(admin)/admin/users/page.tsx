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
  Plus,
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
import { Switch } from '@/components/ui/switch';
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

interface UserData {
  id: string;
  full_name: string | null;
  email: string | null;
  created_at: string | null;
  avatar_url: string | null;
  subscription_status: SubscriptionStatus;
  is_privileged: boolean;
  stripe_customer_id: string | null;
  stripe_subscription_id: string | null;
  current_period_end: string | null;
  cancel_at_period_end: boolean;
  plan_tier_id: string | null;
  addon_articles_limit: number;
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
    is_privileged: false,
    subscription_status: 'none' as SubscriptionStatus,
  });

  // 追加記事付与ダイアログ
  const [grantDialogOpen, setGrantDialogOpen] = useState(false);
  const [grantUser, setGrantUser] = useState<UserData | null>(null);
  const [grantArticles, setGrantArticles] = useState('');
  const [grantLoading, setGrantLoading] = useState(false);
  const [grantMessage, setGrantMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

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

    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      result = result.filter(
        (user) =>
          user.email?.toLowerCase().includes(query) ||
          user.full_name?.toLowerCase().includes(query) ||
          user.id.toLowerCase().includes(query)
      );
    }

    if (statusFilter !== 'all') {
      result = result.filter((user) => user.subscription_status === statusFilter);
    }

    setFilteredUsers(result);
  }, [users, searchQuery, statusFilter]);

  // ユーザー編集ダイアログを開く
  const openEditDialog = (user: UserData) => {
    setEditingUser(user);
    setEditForm({
      is_privileged: user.is_privileged,
      subscription_status: user.subscription_status,
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

      if (editForm.is_privileged !== editingUser.is_privileged) {
        const privilegeResponse = await fetch(
          `${baseURL}/admin/users/${editingUser.id}/privilege`,
          {
            method: 'PATCH',
            headers: {
              'Content-Type': 'application/json',
              ...(token && { Authorization: `Bearer ${token}` }),
            },
            body: JSON.stringify({ is_privileged: editForm.is_privileged }),
          }
        );

        if (!privilegeResponse.ok) {
          throw new Error('特権ステータスの更新に失敗しました');
        }
      }

      if (editForm.subscription_status !== editingUser.subscription_status) {
        const subscriptionResponse = await fetch(
          `${baseURL}/admin/users/${editingUser.id}/subscription`,
          {
            method: 'PATCH',
            headers: {
              'Content-Type': 'application/json',
              ...(token && { Authorization: `Bearer ${token}` }),
            },
            body: JSON.stringify({ status: editForm.subscription_status }),
          }
        );

        if (!subscriptionResponse.ok) {
          throw new Error('サブスクリプションステータスの更新に失敗しました');
        }
      }

      await fetchUsers();
      setEditDialogOpen(false);
      setEditingUser(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : '更新に失敗しました');
    } finally {
      setUpdating(false);
    }
  };

  // 追加記事付与ダイアログを開く
  const openGrantDialog = (user: UserData) => {
    setGrantUser(user);
    setGrantArticles(String(user.addon_articles_limit || 0));
    setGrantMessage(null);
    setGrantDialogOpen(true);
  };

  // 追加記事を付与
  const grantAdditionalArticles = async () => {
    if (!grantUser) return;

    const articles = parseInt(grantArticles, 10);
    if (isNaN(articles) || articles < 0) {
      setGrantMessage({ type: 'error', text: '0以上の数値を入力してください' });
      return;
    }

    setGrantLoading(true);
    setGrantMessage(null);

    try {
      const response = await fetch('/api/admin/grant-articles', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: grantUser.id, additional_articles: articles }),
      });

      const data = await response.json();

      if (!response.ok) {
        setGrantMessage({ type: 'error', text: data.error || 'エラーが発生しました' });
        return;
      }

      setGrantMessage({ type: 'success', text: data.message });
      await fetchUsers();

      setTimeout(() => {
        setGrantDialogOpen(false);
        setGrantUser(null);
        setGrantMessage(null);
      }, 1500);
    } catch {
      setGrantMessage({ type: 'error', text: 'ネットワークエラーが発生しました' });
    } finally {
      setGrantLoading(false);
    }
  };

  // 統計情報
  const stats = {
    total: users.length,
    active: users.filter((u) => u.subscription_status === 'active').length,
    privileged: users.filter((u) => u.is_privileged).length,
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
            <Button onClick={() => { setError(null); fetchUsers(); }} variant="outline">
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
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">ユーザー管理</h1>
        <Button onClick={fetchUsers} variant="outline" size="sm">
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
                <p className="text-sm text-muted-foreground">アクティブ</p>
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
                <p className="text-sm text-muted-foreground">特権ユーザー</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-2">
              <Clock className="h-5 w-5 text-muted-foreground" />
              <div>
                <p className="text-2xl font-bold">{stats.none}</p>
                <p className="text-sm text-muted-foreground">未登録</p>
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
                  <TableHead className="w-[200px]">ユーザー</TableHead>
                  <TableHead>メールアドレス</TableHead>
                  <TableHead>ステータス</TableHead>
                  <TableHead>プラン</TableHead>
                  <TableHead>特権</TableHead>
                  <TableHead>追加記事</TableHead>
                  <TableHead>登録日</TableHead>
                  <TableHead className="text-right">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredUsers.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={8} className="text-center text-muted-foreground py-8">
                      ユーザーが見つかりません
                    </TableCell>
                  </TableRow>
                ) : (
                  filteredUsers.map((user) => {
                    const statusInfo = statusConfig[user.subscription_status] || statusConfig.none;
                    const StatusIcon = statusInfo.icon;

                    return (
                      <TableRow key={user.id}>
                        <TableCell>
                          <div className="flex items-center gap-3">
                            {user.avatar_url ? (
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
                          <span className="text-sm text-muted-foreground">
                            {user.plan_tier_id === 'free' ? 'フリー' : user.plan_tier_id || '-'}
                          </span>
                        </TableCell>
                        <TableCell>
                          {user.is_privileged ? (
                            <Badge variant="default" className="gap-1 bg-amber-500 hover:bg-amber-600">
                              <Crown className="h-3 w-3" />
                              特権
                            </Badge>
                          ) : (
                            <span className="text-sm text-muted-foreground">-</span>
                          )}
                        </TableCell>
                        <TableCell>
                          {user.addon_articles_limit > 0 ? (
                            <Badge variant="secondary" className="gap-1">
                              +{user.addon_articles_limit}記事
                            </Badge>
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
                            <Button
                              variant="ghost"
                              size="sm"
                              className="text-emerald-600 hover:text-emerald-700"
                              onClick={() => openGrantDialog(user)}
                            >
                              <Plus className="h-4 w-4 mr-1" />
                              追加記事
                            </Button>
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

      {/* 編集ダイアログ */}
      <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>ユーザー設定の編集</DialogTitle>
            <DialogDescription>
              {editingUser?.email || editingUser?.full_name || editingUser?.id}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-6 py-4">
            {/* 特権ユーザー設定 */}
            <div className="flex items-center justify-between">
              <div className="space-y-1">
                <Label htmlFor="is_privileged" className="flex items-center gap-2">
                  <Crown className="h-4 w-4 text-amber-500" />
                  特権ユーザー
                </Label>
                <p className="text-sm text-muted-foreground">
                  特権ユーザーはサブスクリプションなしで全機能にアクセスできます
                </p>
              </div>
              <Switch
                id="is_privileged"
                checked={editForm.is_privileged}
                onCheckedChange={(checked) =>
                  setEditForm((prev) => ({ ...prev, is_privileged: checked }))
                }
              />
            </div>

            {/* サブスクリプションステータス */}
            <div className="space-y-2">
              <Label htmlFor="subscription_status">サブスクリプションステータス</Label>
              <Select
                value={editForm.subscription_status}
                onValueChange={(v) =>
                  setEditForm((prev) => ({
                    ...prev,
                    subscription_status: v as SubscriptionStatus,
                  }))
                }
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="active">アクティブ</SelectItem>
                  <SelectItem value="past_due">支払い遅延</SelectItem>
                  <SelectItem value="canceled">キャンセル済み</SelectItem>
                  <SelectItem value="expired">期限切れ</SelectItem>
                  <SelectItem value="none">なし</SelectItem>
                </SelectContent>
              </Select>
              <p className="text-sm text-muted-foreground">
                手動でステータスを変更できます。通常はStripe Webhookで自動更新されます。
              </p>
            </div>

            {/* Stripe情報（読み取り専用） */}
            {editingUser?.stripe_customer_id && (
              <div className="space-y-2 pt-4 border-t">
                <Label className="text-muted-foreground">Stripe情報</Label>
                <div className="text-sm space-y-1">
                  <p>
                    <span className="text-muted-foreground">顧客ID: </span>
                    <code className="bg-muted px-1 rounded">
                      {editingUser.stripe_customer_id}
                    </code>
                  </p>
                  {editingUser.stripe_subscription_id && (
                    <p>
                      <span className="text-muted-foreground">サブスクリプションID: </span>
                      <code className="bg-muted px-1 rounded">
                        {editingUser.stripe_subscription_id}
                      </code>
                    </p>
                  )}
                </div>
              </div>
            )}
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

      {/* 追加記事付与ダイアログ */}
      <Dialog open={grantDialogOpen} onOpenChange={setGrantDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Plus className="h-5 w-5 text-emerald-500" />
              追加記事の付与
            </DialogTitle>
            <DialogDescription>
              {grantUser?.email || grantUser?.full_name}
              {grantUser && grantUser.addon_articles_limit > 0 && (
                <span className="block mt-1 text-emerald-600">
                  現在の追加記事: {grantUser.addon_articles_limit}記事
                </span>
              )}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="grant-articles">追加記事数</Label>
              <div className="flex items-center gap-2">
                <Input
                  id="grant-articles"
                  type="number"
                  min={0}
                  max={1000}
                  placeholder="例: 10"
                  value={grantArticles}
                  onChange={(e) => setGrantArticles(e.target.value)}
                  className="w-32"
                />
                <span className="text-sm text-muted-foreground">記事</span>
              </div>
              <p className="text-xs text-muted-foreground">
                0を指定すると追加記事を解除します。この値は今月の追加上限として設定されます。
              </p>
            </div>

            {/* プリセットボタン */}
            <div className="flex flex-wrap gap-2">
              {[5, 10, 20, 50].map((n) => (
                <Button
                  key={n}
                  variant={grantArticles === String(n) ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setGrantArticles(String(n))}
                  className={grantArticles === String(n) ? 'bg-emerald-600 hover:bg-emerald-700' : ''}
                >
                  {n}記事
                </Button>
              ))}
              <Button
                variant={grantArticles === '0' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setGrantArticles('0')}
                className={grantArticles === '0' ? 'bg-stone-600 hover:bg-stone-700' : ''}
              >
                解除
              </Button>
            </div>

            {/* サマリー */}
            <div className="rounded-lg bg-emerald-50 p-3 space-y-1">
              <p className="text-sm font-medium text-emerald-900">付与内容</p>
              <p className="text-sm text-emerald-700">
                プラン上限: 10記事/月 + 追加: {grantArticles || 0}記事
              </p>
              <p className="text-sm text-emerald-700 font-medium">
                合計: {10 + (parseInt(grantArticles, 10) || 0)}記事/月
              </p>
              <p className="text-xs text-emerald-600 mt-2">
                Stripeでの課金は発生しません。管理者による手動付与です。
              </p>
            </div>

            {/* メッセージ */}
            {grantMessage && (
              <div className={`rounded-lg p-3 text-sm ${
                grantMessage.type === 'success'
                  ? 'bg-green-50 text-green-800'
                  : 'bg-red-50 text-red-800'
              }`}>
                {grantMessage.text}
              </div>
            )}
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setGrantDialogOpen(false)}>
              キャンセル
            </Button>
            <Button
              onClick={grantAdditionalArticles}
              disabled={grantLoading}
              className="bg-emerald-600 hover:bg-emerald-700"
            >
              {grantLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              追加記事を付与
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
