'use client';

import { useCallback, useEffect, useState } from 'react';
import {
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Clock,
  Eye,
  Loader2,
  Mail,
  MessageSquare,
  RefreshCw,
} from 'lucide-react';

import { useAuth } from '@clerk/nextjs';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { cn } from '@/utils/cn';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8080';
const USE_PROXY = process.env.NODE_ENV === 'production';
const API_BASE = USE_PROXY ? '/api/proxy' : API_BASE_URL;

interface Inquiry {
  id: string;
  user_id: string;
  name: string;
  email: string;
  category: string;
  subject: string;
  message: string;
  status: string;
  admin_note: string | null;
  created_at: string;
  updated_at: string;
}

const CATEGORY_LABELS: Record<string, string> = {
  general: '一般',
  bug_report: '不具合',
  feature_request: '機能リクエスト',
  billing: '請求',
  account: 'アカウント',
  other: 'その他',
};

const STATUS_CONFIG: Record<string, { label: string; color: string; icon: typeof Clock }> = {
  new: { label: '新規', color: 'bg-blue-100 text-blue-800', icon: Mail },
  read: { label: '確認済み', color: 'bg-amber-100 text-amber-800', icon: Eye },
  replied: { label: '対応済み', color: 'bg-emerald-100 text-emerald-800', icon: CheckCircle2 },
};

function formatDate(iso: string) {
  const d = new Date(iso);
  return d.toLocaleDateString('ja-JP', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export default function AdminInquiriesPage() {
  const { getToken } = useAuth();
  const [inquiries, setInquiries] = useState<Inquiry[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [updatingId, setUpdatingId] = useState<string | null>(null);
  const [adminNotes, setAdminNotes] = useState<Record<string, string>>({});

  const fetchInquiries = useCallback(async () => {
    try {
      const token = await getToken();
      const params = new URLSearchParams();
      if (statusFilter !== 'all') params.set('status_filter', statusFilter);
      params.set('limit', '100');

      const res = await fetch(`${API_BASE}/contact/admin/list?${params}`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (!res.ok) throw new Error('Failed to fetch');
      const data = await res.json();
      setInquiries(data.inquiries);
      setTotal(data.total);
    } catch (err) {
      console.error('Failed to fetch inquiries:', err);
    } finally {
      setLoading(false);
    }
  }, [getToken, statusFilter]);

  useEffect(() => {
    setLoading(true);
    fetchInquiries();
  }, [fetchInquiries]);

  async function updateStatus(id: string, newStatus: string) {
    setUpdatingId(id);
    try {
      const token = await getToken();
      const body: Record<string, string> = { status: newStatus };
      const note = adminNotes[id];
      if (note !== undefined) {
        body.admin_note = note;
      }

      const res = await fetch(`${API_BASE}/contact/admin/${id}/status`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(body),
      });

      if (!res.ok) throw new Error('Failed to update');
      const updated = await res.json();

      setInquiries((prev) =>
        prev.map((inq) => (inq.id === id ? updated : inq))
      );
    } catch (err) {
      console.error('Failed to update inquiry:', err);
    } finally {
      setUpdatingId(null);
    }
  }

  const statusCounts = inquiries.reduce<Record<string, number>>((acc, inq) => {
    acc[inq.status] = (acc[inq.status] || 0) + 1;
    return acc;
  }, {});

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">お問い合わせ管理</h2>
          <p className="text-sm text-muted-foreground">
            ユーザーからのお問い合わせを確認・対応します（全{total}件）
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={() => fetchInquiries()}>
          <RefreshCw className="mr-2 h-4 w-4" />
          更新
        </Button>
      </div>

      {/* Status summary cards */}
      <div className="grid grid-cols-3 gap-4">
        {(['new', 'read', 'replied'] as const).map((s) => {
          const cfg = STATUS_CONFIG[s];
          const Icon = cfg.icon;
          return (
            <Card
              key={s}
              className={cn(
                'cursor-pointer transition-shadow hover:shadow-md',
                statusFilter === s && 'ring-2 ring-primary'
              )}
              onClick={() => setStatusFilter(statusFilter === s ? 'all' : s)}
            >
              <CardContent className="flex items-center gap-3 p-4">
                <div className={cn('flex h-10 w-10 items-center justify-center rounded-lg', cfg.color)}>
                  <Icon className="h-5 w-5" />
                </div>
                <div>
                  <p className="text-2xl font-bold">{statusCounts[s] || 0}</p>
                  <p className="text-xs text-muted-foreground">{cfg.label}</p>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Filter */}
      <div className="flex items-center gap-3">
        <span className="text-sm text-muted-foreground">フィルタ:</span>
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-40">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">すべて</SelectItem>
            <SelectItem value="new">新規</SelectItem>
            <SelectItem value="read">確認済み</SelectItem>
            <SelectItem value="replied">対応済み</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Inquiry list */}
      {loading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      ) : inquiries.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-12">
            <MessageSquare className="h-10 w-10 text-muted-foreground/40" />
            <p className="text-muted-foreground">お問い合わせはありません</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {inquiries.map((inq) => {
            const isExpanded = expandedId === inq.id;
            const statusCfg = STATUS_CONFIG[inq.status] || STATUS_CONFIG.new;

            return (
              <Card key={inq.id} className="overflow-hidden">
                {/* Summary row */}
                <button
                  className="flex w-full items-center gap-4 px-5 py-4 text-left hover:bg-muted/30 transition-colors"
                  onClick={() => setExpandedId(isExpanded ? null : inq.id)}
                >
                  <Badge className={cn('shrink-0 text-xs', statusCfg.color)} variant="secondary">
                    {statusCfg.label}
                  </Badge>
                  <Badge variant="outline" className="shrink-0 text-xs">
                    {CATEGORY_LABELS[inq.category] || inq.category}
                  </Badge>
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-medium">{inq.subject}</p>
                    <p className="truncate text-xs text-muted-foreground">
                      {inq.name} ({inq.email})
                    </p>
                  </div>
                  <span className="shrink-0 text-xs text-muted-foreground">
                    {formatDate(inq.created_at)}
                  </span>
                  {isExpanded ? (
                    <ChevronUp className="h-4 w-4 shrink-0 text-muted-foreground" />
                  ) : (
                    <ChevronDown className="h-4 w-4 shrink-0 text-muted-foreground" />
                  )}
                </button>

                {/* Detail panel */}
                {isExpanded && (
                  <div className="border-t bg-muted/10 px-5 py-4 space-y-4">
                    <div className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm">
                      <div>
                        <span className="text-muted-foreground">送信者:</span>{' '}
                        <span className="font-medium">{inq.name}</span>
                      </div>
                      <div>
                        <span className="text-muted-foreground">メール:</span>{' '}
                        <a href={`mailto:${inq.email}`} className="text-blue-600 hover:underline">
                          {inq.email}
                        </a>
                      </div>
                      <div>
                        <span className="text-muted-foreground">ユーザーID:</span>{' '}
                        <span className="font-mono text-xs">{inq.user_id}</span>
                      </div>
                      <div>
                        <span className="text-muted-foreground">送信日時:</span>{' '}
                        {formatDate(inq.created_at)}
                      </div>
                    </div>

                    <div>
                      <p className="mb-1 text-sm font-medium text-muted-foreground">お問い合わせ内容</p>
                      <div className="whitespace-pre-wrap rounded-lg bg-white p-4 text-sm border">
                        {inq.message}
                      </div>
                    </div>

                    {/* Admin note */}
                    <div>
                      <p className="mb-1 text-sm font-medium text-muted-foreground">管理者メモ</p>
                      <Textarea
                        value={adminNotes[inq.id] ?? inq.admin_note ?? ''}
                        onChange={(e) =>
                          setAdminNotes((prev) => ({ ...prev, [inq.id]: e.target.value }))
                        }
                        placeholder="対応メモを記録（内部用）"
                        rows={3}
                      />
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-2">
                      {inq.status === 'new' && (
                        <Button
                          size="sm"
                          variant="outline"
                          disabled={updatingId === inq.id}
                          onClick={() => updateStatus(inq.id, 'read')}
                        >
                          {updatingId === inq.id ? (
                            <Loader2 className="mr-1 h-3 w-3 animate-spin" />
                          ) : (
                            <Eye className="mr-1 h-3 w-3" />
                          )}
                          確認済みにする
                        </Button>
                      )}
                      {(inq.status === 'new' || inq.status === 'read') && (
                        <Button
                          size="sm"
                          disabled={updatingId === inq.id}
                          onClick={() => updateStatus(inq.id, 'replied')}
                        >
                          {updatingId === inq.id ? (
                            <Loader2 className="mr-1 h-3 w-3 animate-spin" />
                          ) : (
                            <CheckCircle2 className="mr-1 h-3 w-3" />
                          )}
                          対応済みにする
                        </Button>
                      )}
                      {inq.status === 'replied' && (
                        <Button
                          size="sm"
                          variant="outline"
                          disabled={updatingId === inq.id}
                          onClick={() => updateStatus(inq.id, 'read')}
                        >
                          確認済みに戻す
                        </Button>
                      )}
                      {/* Save note only button */}
                      {adminNotes[inq.id] !== undefined &&
                        adminNotes[inq.id] !== (inq.admin_note ?? '') && (
                          <Button
                            size="sm"
                            variant="ghost"
                            disabled={updatingId === inq.id}
                            onClick={() => updateStatus(inq.id, inq.status)}
                          >
                            メモを保存
                          </Button>
                        )}
                    </div>
                  </div>
                )}
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
