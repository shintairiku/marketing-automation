'use client';

import { useCallback,useEffect, useState } from 'react';
import {
  AlertTriangle,
  Loader2,
  Pencil,
  Plus,
  RefreshCw,
  Trash2,
} from 'lucide-react';

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
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
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { useAuth } from '@clerk/nextjs';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || '';
const USE_PROXY = process.env.NODE_ENV === 'production';
const API_BASE = USE_PROXY ? '/api/proxy' : API_BASE_URL;

interface PlanTier {
  id: string;
  name: string;
  stripe_price_id: string | null;
  monthly_article_limit: number;
  addon_unit_amount: number;
  price_amount: number;
  display_order: number;
  is_active: boolean;
  created_at: string | null;
  updated_at: string | null;
}

interface TierFormData {
  id: string;
  name: string;
  stripe_price_id: string;
  monthly_article_limit: number;
  addon_unit_amount: number;
  price_amount: number;
  display_order: number;
}

const defaultFormData: TierFormData = {
  id: '',
  name: '',
  stripe_price_id: '',
  monthly_article_limit: 30,
  addon_unit_amount: 20,
  price_amount: 0,
  display_order: 0,
};

export default function PlansPage() {
  const { getToken } = useAuth();
  const [tiers, setTiers] = useState<PlanTier[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Dialog states
  const [createOpen, setCreateOpen] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<PlanTier | null>(null);
  const [applyTarget, setApplyTarget] = useState<PlanTier | null>(null);
  const [applyResult, setApplyResult] = useState<string | null>(null);

  const [formData, setFormData] = useState<TierFormData>(defaultFormData);
  const [editingTier, setEditingTier] = useState<PlanTier | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const fetchTiers = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const token = await getToken();
      const res = await fetch(`${API_BASE}/admin/plan-tiers`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error(`Failed to fetch: ${res.status}`);
      const data = await res.json();
      setTiers(data.tiers || []);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to fetch tiers');
    } finally {
      setLoading(false);
    }
  }, [getToken]);

  useEffect(() => {
    fetchTiers();
  }, [fetchTiers]);

  const handleCreate = async () => {
    try {
      setSubmitting(true);
      setFormError(null);
      const token = await getToken();
      const res = await fetch(`${API_BASE}/admin/plan-tiers`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ...formData,
          stripe_price_id: formData.stripe_price_id || null,
        }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || `Error: ${res.status}`);
      }
      setCreateOpen(false);
      setFormData(defaultFormData);
      await fetchTiers();
    } catch (e) {
      setFormError(e instanceof Error ? e.message : 'Failed to create');
    } finally {
      setSubmitting(false);
    }
  };

  const handleEdit = async () => {
    if (!editingTier) return;
    try {
      setSubmitting(true);
      setFormError(null);
      const token = await getToken();

      const updateData: Record<string, unknown> = {};
      if (formData.name !== editingTier.name) updateData.name = formData.name;
      if (formData.stripe_price_id !== (editingTier.stripe_price_id || ''))
        updateData.stripe_price_id = formData.stripe_price_id || null;
      if (formData.monthly_article_limit !== editingTier.monthly_article_limit)
        updateData.monthly_article_limit = formData.monthly_article_limit;
      if (formData.addon_unit_amount !== editingTier.addon_unit_amount)
        updateData.addon_unit_amount = formData.addon_unit_amount;
      if (formData.price_amount !== editingTier.price_amount)
        updateData.price_amount = formData.price_amount;
      if (formData.display_order !== editingTier.display_order)
        updateData.display_order = formData.display_order;

      const res = await fetch(`${API_BASE}/admin/plan-tiers/${editingTier.id}`, {
        method: 'PATCH',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(updateData),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || `Error: ${res.status}`);
      }
      setEditOpen(false);
      setEditingTier(null);
      await fetchTiers();
    } catch (e) {
      setFormError(e instanceof Error ? e.message : 'Failed to update');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      setSubmitting(true);
      const token = await getToken();
      const res = await fetch(`${API_BASE}/admin/plan-tiers/${deleteTarget.id}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || `Error: ${res.status}`);
      }
      setDeleteTarget(null);
      await fetchTiers();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to delete');
      setDeleteTarget(null);
    } finally {
      setSubmitting(false);
    }
  };

  const handleApply = async () => {
    if (!applyTarget) return;
    try {
      setSubmitting(true);
      setApplyResult(null);
      const token = await getToken();
      const res = await fetch(`${API_BASE}/admin/plan-tiers/${applyTarget.id}/apply`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || `Error: ${res.status}`);
      }
      const result = await res.json();
      setApplyResult(result.message || `${result.updated_count}件更新しました`);
    } catch (e) {
      setApplyResult(e instanceof Error ? e.message : 'Failed to apply');
    } finally {
      setSubmitting(false);
    }
  };

  const openEditDialog = (tier: PlanTier) => {
    setEditingTier(tier);
    setFormData({
      id: tier.id,
      name: tier.name,
      stripe_price_id: tier.stripe_price_id || '',
      monthly_article_limit: tier.monthly_article_limit,
      addon_unit_amount: tier.addon_unit_amount,
      price_amount: tier.price_amount,
      display_order: tier.display_order,
    });
    setFormError(null);
    setEditOpen(true);
  };

  const handleToggleActive = async (tier: PlanTier) => {
    try {
      const token = await getToken();
      const res = await fetch(`${API_BASE}/admin/plan-tiers/${tier.id}`, {
        method: 'PATCH',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ is_active: !tier.is_active }),
      });
      if (!res.ok) throw new Error('Failed to toggle');
      await fetchTiers();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to toggle active');
    }
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('ja-JP', {
      style: 'currency',
      currency: 'JPY',
    }).format(amount);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-xl sm:text-2xl font-bold tracking-tight">プラン設定</h2>
          <p className="text-muted-foreground text-sm mt-1">
            プランティアの月間記事上限、アドオン単位、Stripe Price ID を管理します
          </p>
        </div>
        <Button className="self-start sm:self-auto shrink-0" onClick={() => { setFormData(defaultFormData); setFormError(null); setCreateOpen(true); }}>
          <Plus className="h-4 w-4 mr-2" />
          新規作成
        </Button>
      </div>

      {/* Info */}
      <div className="rounded-lg border bg-muted/50 p-4 text-sm text-muted-foreground space-y-1">
        <p>
          <strong>保存</strong>は plan_tiers テーブルの値のみ更新します。次回請求サイクルから新値が自動適用されます。
        </p>
        <p>
          <strong>即時反映</strong>で現在の請求期間の全ユーザーの使用量上限を強制更新します。
        </p>
        <p>
          Stripe Price ID は Stripe ダッシュボードで作成した Price の ID（例: price_xxxxx）を入力してください。
        </p>
        <p>
          月額料金は表示用です。Stripe の実際の課金額とは連動しません。
        </p>
      </div>

      {error && (
        <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-3 text-sm text-destructive flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 flex-shrink-0" />
          {error}
        </div>
      )}

      {/* Table */}
      <div className="rounded-lg border bg-white overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="min-w-[80px]">ID</TableHead>
              <TableHead className="min-w-[100px]">名前</TableHead>
              <TableHead className="min-w-[140px]">Stripe Price ID</TableHead>
              <TableHead className="text-right whitespace-nowrap">月間上限</TableHead>
              <TableHead className="text-right whitespace-nowrap">アドオン単位</TableHead>
              <TableHead className="text-right whitespace-nowrap">月額 (表示用)</TableHead>
              <TableHead className="text-center whitespace-nowrap">表示順</TableHead>
              <TableHead className="text-center">ステータス</TableHead>
              <TableHead className="text-right min-w-[160px]">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {tiers.length === 0 ? (
              <TableRow>
                <TableCell colSpan={9} className="text-center py-8 text-muted-foreground">
                  プランティアがまだ登録されていません
                </TableCell>
              </TableRow>
            ) : (
              tiers.map((tier) => (
                <TableRow key={tier.id}>
                  <TableCell className="font-mono text-sm">{tier.id}</TableCell>
                  <TableCell className="font-medium">{tier.name}</TableCell>
                  <TableCell className="font-mono text-xs text-muted-foreground max-w-[180px] truncate">
                    {tier.stripe_price_id || '-'}
                  </TableCell>
                  <TableCell className="text-right">{tier.monthly_article_limit}</TableCell>
                  <TableCell className="text-right">{tier.addon_unit_amount}</TableCell>
                  <TableCell className="text-right">{formatCurrency(tier.price_amount)}</TableCell>
                  <TableCell className="text-center">{tier.display_order}</TableCell>
                  <TableCell className="text-center">
                    <Badge
                      variant={tier.is_active ? 'default' : 'secondary'}
                      className="cursor-pointer"
                      onClick={() => handleToggleActive(tier)}
                    >
                      {tier.is_active ? '有効' : '無効'}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex items-center justify-end gap-1">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => openEditDialog(tier)}
                      >
                        <Pencil className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setDeleteTarget(tier)}
                      >
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => { setApplyResult(null); setApplyTarget(tier); }}
                      >
                        <RefreshCw className="h-4 w-4 mr-1" />
                        即時反映
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* Create Dialog */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>新規プランティア作成</DialogTitle>
            <DialogDescription>
              新しいプランティアを作成します。ID は一意で、後から変更できません。
            </DialogDescription>
          </DialogHeader>
          <TierForm
            formData={formData}
            onChange={setFormData}
            isNew
          />
          {formError && (
            <p className="text-sm text-destructive">{formError}</p>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateOpen(false)}>
              キャンセル
            </Button>
            <Button onClick={handleCreate} disabled={submitting || !formData.id || !formData.name}>
              {submitting && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              作成
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Dialog */}
      <Dialog open={editOpen} onOpenChange={setEditOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>プランティア編集: {editingTier?.id}</DialogTitle>
            <DialogDescription>
              プランティアの設定を変更します。変更後「即時反映」で現在のユーザーにも適用できます。
            </DialogDescription>
          </DialogHeader>
          <TierForm
            formData={formData}
            onChange={setFormData}
          />
          {formError && (
            <p className="text-sm text-destructive">{formError}</p>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditOpen(false)}>
              キャンセル
            </Button>
            <Button onClick={handleEdit} disabled={submitting}>
              {submitting && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              保存
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation */}
      <AlertDialog open={!!deleteTarget} onOpenChange={() => setDeleteTarget(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>プランティアの削除</AlertDialogTitle>
            <AlertDialogDescription>
              プランティア「{deleteTarget?.name}」（ID: {deleteTarget?.id}）を削除しますか？
              使用中のティアは削除できません。
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>キャンセル</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              削除
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Apply Confirmation */}
      <AlertDialog open={!!applyTarget} onOpenChange={() => { setApplyTarget(null); setApplyResult(null); }}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>全ユーザーに即時反映</AlertDialogTitle>
            <AlertDialogDescription>
              {applyResult ? (
                <span className="block mt-2 font-medium text-foreground">{applyResult}</span>
              ) : (
                <>
                  プランティア「{applyTarget?.name}」の現在の請求期間内の全ユーザーの上限が更新されます。
                  <br />
                  月間上限: {applyTarget?.monthly_article_limit}記事、アドオン単位: {applyTarget?.addon_unit_amount}記事
                </>
              )}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            {applyResult ? (
              <AlertDialogAction onClick={() => { setApplyTarget(null); setApplyResult(null); }}>
                閉じる
              </AlertDialogAction>
            ) : (
              <>
                <AlertDialogCancel>キャンセル</AlertDialogCancel>
                <AlertDialogAction onClick={handleApply} disabled={submitting}>
                  {submitting && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                  即時反映
                </AlertDialogAction>
              </>
            )}
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

// ============================================
// Tier Form Component
// ============================================
function TierForm({
  formData,
  onChange,
  isNew = false,
}: {
  formData: TierFormData;
  onChange: (data: TierFormData) => void;
  isNew?: boolean;
}) {
  return (
    <div className="grid gap-4 py-4">
      {isNew && (
        <div className="space-y-1.5">
          <Label htmlFor="tier-id">ID</Label>
          <Input
            id="tier-id"
            value={formData.id}
            onChange={(e) => onChange({ ...formData, id: e.target.value })}
            placeholder="例: default, pro, enterprise"
          />
        </div>
      )}
      <div className="space-y-1.5">
        <Label htmlFor="tier-name">名前</Label>
        <Input
          id="tier-name"
          value={formData.name}
          onChange={(e) => onChange({ ...formData, name: e.target.value })}
          placeholder="例: スタンダードプラン"
        />
      </div>
      <div className="space-y-1.5">
        <Label htmlFor="tier-price-id">Stripe Price ID</Label>
        <Input
          id="tier-price-id"
          value={formData.stripe_price_id}
          onChange={(e) => onChange({ ...formData, stripe_price_id: e.target.value })}
          placeholder="例: price_1Abc..."
          className="font-mono text-sm"
        />
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-1.5">
          <Label htmlFor="tier-limit">月間上限</Label>
          <Input
            id="tier-limit"
            type="number"
            value={formData.monthly_article_limit}
            onChange={(e) => onChange({ ...formData, monthly_article_limit: parseInt(e.target.value) || 0 })}
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="tier-addon">アドオン単位</Label>
          <Input
            id="tier-addon"
            type="number"
            value={formData.addon_unit_amount}
            onChange={(e) => onChange({ ...formData, addon_unit_amount: parseInt(e.target.value) || 0 })}
          />
        </div>
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-1.5">
          <Label htmlFor="tier-price">月額 (円)</Label>
          <Input
            id="tier-price"
            type="number"
            value={formData.price_amount}
            onChange={(e) => onChange({ ...formData, price_amount: parseInt(e.target.value) || 0 })}
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="tier-order">表示順</Label>
          <Input
            id="tier-order"
            type="number"
            value={formData.display_order}
            onChange={(e) => onChange({ ...formData, display_order: parseInt(e.target.value) || 0 })}
          />
        </div>
      </div>
    </div>
  );
}
