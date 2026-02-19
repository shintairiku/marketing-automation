'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import {
  AlertCircle,
  CalendarPlus,
  CheckCircle,
  Clock,
  Crown,
  ExternalLink,
  Gift,
  Loader2,
  RefreshCw,
  Search,
  Shield,
  Sparkles,
  Trash2,
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

type SubscriptionStatus = 'trialing' | 'active' | 'past_due' | 'canceled' | 'expired' | 'none';

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
  trial_end: string | null;
}

// ステータスバッジのスタイル
const statusConfig: Record<
  SubscriptionStatus,
  { label: string; variant: 'default' | 'secondary' | 'destructive' | 'outline'; icon: typeof CheckCircle }
> = {
  trialing: { label: 'トライアル', variant: 'default', icon: Gift },
  active: { label: 'アクティブ', variant: 'default', icon: CheckCircle },
  past_due: { label: '支払い遅延', variant: 'destructive', icon: AlertCircle },
  canceled: { label: 'キャンセル済み', variant: 'secondary', icon: XCircle },
  expired: { label: '期限切れ', variant: 'destructive', icon: XCircle },
  none: { label: 'なし', variant: 'outline', icon: Clock },
};

// トライアル期間プリセット
const TRIAL_PRESETS = [
  { label: '7日間', days: 7 },
  { label: '14日間', days: 14 },
  { label: '30日間', days: 30 },
  { label: '60日間', days: 60 },
  { label: '90日間', days: 90 },
];

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

  // トライアル付与ダイアログ
  const [trialDialogOpen, setTrialDialogOpen] = useState(false);
  const [trialUser, setTrialUser] = useState<UserData | null>(null);
  const [trialDays, setTrialDays] = useState(30);
  const [customDays, setCustomDays] = useState('');
  const [trialLoading, setTrialLoading] = useState(false);
  const [trialMessage, setTrialMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // トライアル取り消し確認
  const [revokeDialogOpen, setRevokeDialogOpen] = useState(false);
  const [revokeUser, setRevokeUser] = useState<UserData | null>(null);
  const [revokeLoading, setRevokeLoading] = useState(false);

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

  // トライアル付与ダイアログを開く
  const openTrialDialog = (user: UserData) => {
    setTrialUser(user);
    setTrialDays(30);
    setCustomDays('');
    setTrialMessage(null);
    setTrialDialogOpen(true);
  };

  // トライアルを付与
  const grantTrial = async () => {
    if (!trialUser) return;

    const days = customDays ? parseInt(customDays, 10) : trialDays;
    if (!days || days < 1 || days > 730) {
      setTrialMessage({ type: 'error', text: '日数は1〜730の間で指定してください' });
      return;
    }

    setTrialLoading(true);
    setTrialMessage(null);

    try {
      const response = await fetch('/api/admin/free-trial', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: trialUser.id, days }),
      });

      const data = await response.json();

      if (!response.ok) {
        setTrialMessage({ type: 'error', text: data.error || 'エラーが発生しました' });
        return;
      }

      setTrialMessage({ type: 'success', text: data.message });
      await fetchUsers();

      // 2秒後にダイアログを閉じる
      setTimeout(() => {
        setTrialDialogOpen(false);
        setTrialUser(null);
        setTrialMessage(null);
      }, 2000);
    } catch {
      setTrialMessage({ type: 'error', text: 'ネットワークエラーが発生しました' });
    } finally {
      setTrialLoading(false);
    }
  };

  // トライアル取り消し
  const revokeTrial = async () => {
    if (!revokeUser) return;

    setRevokeLoading(true);
    try {
      const response = await fetch(`/api/admin/free-trial?user_id=${revokeUser.id}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        const data = await response.json();
        setError(data.error || 'トライアルの取り消しに失敗しました');
        return;
      }

      await fetchUsers();
      setRevokeDialogOpen(false);
      setRevokeUser(null);
    } catch {
      setError('ネットワークエラーが発生しました');
    } finally {
      setRevokeLoading(false);
    }
  };

  // 統計情報
  const stats = {
    total: users.length,
    active: users.filter((u) => u.subscription_status === 'active').length,
    trialing: users.filter((u) => u.subscription_status === 'trialing').length,
    privileged: users.filter((u) => u.is_privileged).length,
    none: users.filter((u) => u.subscription_status === 'none').length,
  };

  // 残り日数を計算
  const getRemainingDays = (trialEnd: string | null) => {
    if (!trialEnd) return null;
    const end = new Date(trialEnd);
    const now = new Date();
    const diff = Math.ceil((end.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
    return diff > 0 ? diff : 0;
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
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
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
              <Gift className="h-5 w-5 text-violet-500" />
              <div>
                <p className="text-2xl font-bold">{stats.trialing}</p>
                <p className="text-sm text-muted-foreground">トライアル中</p>
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
                <SelectItem value="trialing">トライアル</SelectItem>
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
                  <TableHead>特権</TableHead>
                  <TableHead>期間終了</TableHead>
                  <TableHead>登録日</TableHead>
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
                    const statusInfo = statusConfig[user.subscription_status] || statusConfig.none;
                    const StatusIcon = statusInfo.icon;
                    const remainingDays = user.subscription_status === 'trialing'
                      ? getRemainingDays(user.trial_end || user.current_period_end)
                      : null;

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
                          <div className="flex items-center gap-2">
                            <Badge
                              variant={statusInfo.variant}
                              className={`gap-1 ${user.subscription_status === 'trialing' ? 'bg-violet-500 hover:bg-violet-600' : ''}`}
                            >
                              <StatusIcon className="h-3 w-3" />
                              {statusInfo.label}
                            </Badge>
                            {remainingDays !== null && (
                              <span className="text-xs text-muted-foreground">
                                残り{remainingDays}日
                              </span>
                            )}
                          </div>
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
                            {/* トライアル付与/取り消しボタン */}
                            {user.subscription_status === 'trialing' ? (
                              <>
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  className="text-violet-600 hover:text-violet-700"
                                  onClick={() => openTrialDialog(user)}
                                >
                                  <CalendarPlus className="h-4 w-4 mr-1" />
                                  延長
                                </Button>
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  className="text-red-500 hover:text-red-600"
                                  onClick={() => { setRevokeUser(user); setRevokeDialogOpen(true); }}
                                >
                                  <Trash2 className="h-4 w-4 mr-1" />
                                  取消
                                </Button>
                              </>
                            ) : user.subscription_status === 'none' || user.subscription_status === 'expired' || user.subscription_status === 'canceled' ? (
                              <Button
                                variant="ghost"
                                size="sm"
                                className="text-violet-600 hover:text-violet-700"
                                onClick={() => openTrialDialog(user)}
                              >
                                <Sparkles className="h-4 w-4 mr-1" />
                                トライアル
                              </Button>
                            ) : null}
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
                  <SelectItem value="trialing">トライアル</SelectItem>
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

      {/* トライアル付与ダイアログ */}
      <Dialog open={trialDialogOpen} onOpenChange={setTrialDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Gift className="h-5 w-5 text-violet-500" />
              {trialUser?.subscription_status === 'trialing' ? 'トライアル延長' : '無料トライアル付与'}
            </DialogTitle>
            <DialogDescription>
              {trialUser?.email || trialUser?.full_name}
              {trialUser?.subscription_status === 'trialing' && (
                <span className="block mt-1 text-violet-600">
                  現在トライアル中 — 残り{getRemainingDays(trialUser?.trial_end || trialUser?.current_period_end || null)}日
                </span>
              )}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            {/* プリセット期間 */}
            <div className="space-y-2">
              <Label>期間を選択</Label>
              <div className="grid grid-cols-5 gap-2">
                {TRIAL_PRESETS.map((preset) => (
                  <Button
                    key={preset.days}
                    variant={trialDays === preset.days && !customDays ? 'default' : 'outline'}
                    size="sm"
                    onClick={() => { setTrialDays(preset.days); setCustomDays(''); }}
                    className={trialDays === preset.days && !customDays ? 'bg-violet-600 hover:bg-violet-700' : ''}
                  >
                    {preset.label}
                  </Button>
                ))}
              </div>
            </div>

            {/* カスタム日数 */}
            <div className="space-y-2">
              <Label htmlFor="custom-days">カスタム日数</Label>
              <div className="flex items-center gap-2">
                <Input
                  id="custom-days"
                  type="number"
                  min={1}
                  max={730}
                  placeholder="例: 45"
                  value={customDays}
                  onChange={(e) => setCustomDays(e.target.value)}
                  className="w-32"
                />
                <span className="text-sm text-muted-foreground">日間</span>
              </div>
            </div>

            {/* 付与内容サマリー */}
            <div className="rounded-lg bg-violet-50 p-3 space-y-1">
              <p className="text-sm font-medium text-violet-900">付与内容</p>
              <p className="text-sm text-violet-700">
                期間: {customDays ? parseInt(customDays, 10) || '—' : trialDays}日間
              </p>
              <p className="text-sm text-violet-700">
                終了日: {(() => {
                  const d = customDays ? parseInt(customDays, 10) : trialDays;
                  if (!d) return '—';
                  const end = new Date(Date.now() + d * 86400000);
                  return end.toLocaleDateString('ja-JP', { year: 'numeric', month: 'long', day: 'numeric' });
                })()}
              </p>
              <p className="text-xs text-violet-600 mt-2">
                クレジットカード不要。期間終了後は自動的にキャンセルされます。
              </p>
            </div>

            {/* メッセージ */}
            {trialMessage && (
              <div className={`rounded-lg p-3 text-sm ${
                trialMessage.type === 'success'
                  ? 'bg-green-50 text-green-800'
                  : 'bg-red-50 text-red-800'
              }`}>
                {trialMessage.text}
              </div>
            )}
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setTrialDialogOpen(false)}>
              キャンセル
            </Button>
            <Button
              onClick={grantTrial}
              disabled={trialLoading}
              className="bg-violet-600 hover:bg-violet-700"
            >
              {trialLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {trialUser?.subscription_status === 'trialing' ? 'トライアルを延長' : 'トライアルを付与'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* トライアル取り消し確認ダイアログ */}
      <Dialog open={revokeDialogOpen} onOpenChange={setRevokeDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle className="text-red-600">トライアルの取り消し</DialogTitle>
            <DialogDescription>
              {revokeUser?.email || revokeUser?.full_name} のトライアルを取り消しますか？
              この操作は元に戻せません。ユーザーは即座にアクセスを失います。
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setRevokeDialogOpen(false)}>
              キャンセル
            </Button>
            <Button
              variant="destructive"
              onClick={revokeTrial}
              disabled={revokeLoading}
            >
              {revokeLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              取り消す
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
