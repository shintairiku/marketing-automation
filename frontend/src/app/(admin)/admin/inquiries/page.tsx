'use client';

import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '@clerk/nextjs';
import {
  MessageSquare,
  Clock,
  ChevronDown,
  ChevronUp,
  Filter,
  RefreshCw,
  User,
  Mail,
} from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8080';
const USE_PROXY = process.env.NODE_ENV === 'production';
const API_BASE = USE_PROXY ? '/api/proxy' : API_BASE_URL;

interface Inquiry {
  id: string;
  user_id: string;
  user_email: string;
  user_name: string | null;
  category: string;
  subject: string;
  message: string;
  status: string;
  admin_notes: string | null;
  created_at: string;
  updated_at: string;
}

const CATEGORY_LABELS: Record<string, string> = {
  general: '一般',
  bug_report: '不具合',
  feature_request: '機能要望',
  billing: '支払い',
  other: 'その他',
};

const STATUS_OPTIONS = [
  { value: 'new', label: '新規', color: 'bg-blue-100 text-blue-700' },
  { value: 'in_progress', label: '対応中', color: 'bg-amber-100 text-amber-700' },
  { value: 'resolved', label: '解決済み', color: 'bg-emerald-100 text-emerald-700' },
  { value: 'closed', label: 'クローズ', color: 'bg-stone-100 text-stone-500' },
];

function getStatusStyle(status: string) {
  return STATUS_OPTIONS.find((s) => s.value === status) || STATUS_OPTIONS[0];
}

export default function AdminInquiriesPage() {
  const { getToken } = useAuth();
  const [inquiries, setInquiries] = useState<Inquiry[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [expandedId, setExpandedId] = useState<string | null>(null);

  // Status update state
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editStatus, setEditStatus] = useState('');
  const [editNotes, setEditNotes] = useState('');
  const [saving, setSaving] = useState(false);

  const fetchInquiries = useCallback(async () => {
    setLoading(true);
    try {
      const token = await getToken();
      const params = new URLSearchParams({ limit: '200', offset: '0' });
      if (statusFilter !== 'all') params.set('status', statusFilter);

      const res = await fetch(`${API_BASE}/contact/admin?${params}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setInquiries(data.inquiries || []);
        setTotal(data.total || 0);
      }
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  }, [getToken, statusFilter]);

  useEffect(() => {
    fetchInquiries();
  }, [fetchInquiries]);

  const handleStatusUpdate = async (inquiryId: string) => {
    setSaving(true);
    try {
      const token = await getToken();
      const body: Record<string, string> = { status: editStatus };
      if (editNotes.trim()) body.admin_notes = editNotes;

      const res = await fetch(`${API_BASE}/contact/admin/${inquiryId}/status`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(body),
      });

      if (res.ok) {
        const updated = await res.json();
        setInquiries((prev) => prev.map((i) => (i.id === inquiryId ? updated : i)));
        setEditingId(null);
      }
    } catch {
      // silent
    } finally {
      setSaving(false);
    }
  };

  const startEditing = (inquiry: Inquiry) => {
    setEditingId(inquiry.id);
    setEditStatus(inquiry.status);
    setEditNotes(inquiry.admin_notes || '');
  };

  // Count by status
  const statusCounts = inquiries.reduce<Record<string, number>>((acc, i) => {
    acc[i.status] = (acc[i.status] || 0) + 1;
    return acc;
  }, {});

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">お問い合わせ管理</h1>
          <p className="text-sm text-muted-foreground mt-1">
            ユーザーからのお問い合わせを確認・対応します
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={fetchInquiries} disabled={loading}>
          <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
          更新
        </Button>
      </div>

      {/* KPI cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {STATUS_OPTIONS.map((st) => (
          <Card key={st.value} className="cursor-pointer hover:shadow-sm transition-shadow"
            onClick={() => setStatusFilter(st.value === statusFilter ? 'all' : st.value)}
          >
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${st.color}`}>
                  {st.label}
                </span>
                <span className="text-2xl font-bold">{statusCounts[st.value] || 0}</span>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Filter */}
      <div className="flex items-center gap-3">
        <Filter className="h-4 w-4 text-muted-foreground" />
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-40">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">すべて ({total})</SelectItem>
            {STATUS_OPTIONS.map((st) => (
              <SelectItem key={st.value} value={st.value}>
                {st.label} ({statusCounts[st.value] || 0})
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Inquiry list */}
      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-20 rounded-lg bg-muted animate-pulse" />
          ))}
        </div>
      ) : inquiries.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12 text-muted-foreground">
            <MessageSquare className="h-10 w-10 mb-2" />
            <p>お問い合わせはありません</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-2">
          {inquiries.map((inquiry) => {
            const st = getStatusStyle(inquiry.status);
            const catLabel = CATEGORY_LABELS[inquiry.category] || inquiry.category;
            const isExpanded = expandedId === inquiry.id;
            const isEditing = editingId === inquiry.id;

            return (
              <Card key={inquiry.id} className="overflow-hidden">
                <button
                  type="button"
                  className="w-full text-left px-4 py-3"
                  onClick={() => setExpandedId(isExpanded ? null : inquiry.id)}
                >
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-3 min-w-0">
                      <span className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${st.color}`}>
                        {st.label}
                      </span>
                      <span className="text-xs text-muted-foreground shrink-0 rounded bg-muted px-1.5 py-0.5">
                        {catLabel}
                      </span>
                      <span className="font-medium text-sm truncate">{inquiry.subject}</span>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <span className="text-xs text-muted-foreground">
                        {new Date(inquiry.created_at).toLocaleDateString('ja-JP')}
                      </span>
                      {isExpanded ? (
                        <ChevronUp className="h-4 w-4 text-muted-foreground" />
                      ) : (
                        <ChevronDown className="h-4 w-4 text-muted-foreground" />
                      )}
                    </div>
                  </div>
                </button>

                {isExpanded && (
                  <CardContent className="pt-0 pb-4 space-y-4">
                    {/* User info */}
                    <div className="flex items-center gap-4 text-sm text-muted-foreground bg-muted/50 rounded-lg p-3">
                      <div className="flex items-center gap-1.5">
                        <User className="h-3.5 w-3.5" />
                        <span>{inquiry.user_name || '名前未設定'}</span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <Mail className="h-3.5 w-3.5" />
                        <span>{inquiry.user_email}</span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <Clock className="h-3.5 w-3.5" />
                        <span>{new Date(inquiry.created_at).toLocaleString('ja-JP')}</span>
                      </div>
                    </div>

                    {/* Message */}
                    <div className="whitespace-pre-wrap text-sm bg-white border rounded-lg p-4">
                      {inquiry.message}
                    </div>

                    {/* Admin notes (display) */}
                    {inquiry.admin_notes && !isEditing && (
                      <div className="rounded-lg bg-blue-50 p-3 text-sm text-blue-700">
                        <span className="font-medium">管理者メモ: </span>
                        {inquiry.admin_notes}
                      </div>
                    )}

                    {/* Edit controls */}
                    {isEditing ? (
                      <div className="space-y-3 border rounded-lg p-4 bg-muted/30">
                        <div className="flex items-center gap-3">
                          <span className="text-sm font-medium shrink-0">ステータス</span>
                          <Select value={editStatus} onValueChange={setEditStatus}>
                            <SelectTrigger className="w-40">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              {STATUS_OPTIONS.map((s) => (
                                <SelectItem key={s.value} value={s.value}>
                                  {s.label}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>
                        <div className="space-y-1.5">
                          <span className="text-sm font-medium">管理者メモ</span>
                          <Textarea
                            value={editNotes}
                            onChange={(e) => setEditNotes(e.target.value)}
                            placeholder="対応内容やメモを記入（ユーザーに表示されます）"
                            rows={3}
                            maxLength={2000}
                          />
                        </div>
                        <div className="flex gap-2">
                          <Button
                            size="sm"
                            onClick={() => handleStatusUpdate(inquiry.id)}
                            disabled={saving}
                          >
                            {saving ? '保存中...' : '保存'}
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => setEditingId(null)}
                          >
                            キャンセル
                          </Button>
                        </div>
                      </div>
                    ) : (
                      <Button size="sm" variant="outline" onClick={() => startEditing(inquiry)}>
                        ステータスを変更
                      </Button>
                    )}
                  </CardContent>
                )}
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
