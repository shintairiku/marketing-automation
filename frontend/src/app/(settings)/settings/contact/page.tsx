'use client';

import { useState, useEffect } from 'react';
import { useAuth } from '@clerk/nextjs';
import { Send, CheckCircle2, Clock, MessageSquare, ChevronDown } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
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
const baseURL = USE_PROXY ? '/api/proxy' : API_BASE_URL;

interface Inquiry {
  id: string;
  category: string;
  subject: string;
  message: string;
  status: string;
  admin_notes: string | null;
  created_at: string;
}

const CATEGORY_OPTIONS = [
  { value: 'general', label: '一般的なお問い合わせ' },
  { value: 'bug_report', label: '不具合報告' },
  { value: 'feature_request', label: '機能要望' },
  { value: 'billing', label: 'お支払いについて' },
  { value: 'other', label: 'その他' },
];

const STATUS_LABELS: Record<string, { label: string; color: string }> = {
  new: { label: '受付済み', color: 'bg-blue-100 text-blue-700' },
  in_progress: { label: '対応中', color: 'bg-amber-100 text-amber-700' },
  resolved: { label: '解決済み', color: 'bg-emerald-100 text-emerald-700' },
  closed: { label: 'クローズ', color: 'bg-stone-100 text-stone-500' },
};

export default function ContactPage() {
  const { getToken } = useAuth();
  const [category, setCategory] = useState('general');
  const [subject, setSubject] = useState('');
  const [message, setMessage] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState('');

  const [history, setHistory] = useState<Inquiry[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(true);
  const [showHistory, setShowHistory] = useState(false);

  const fetchHistory = async () => {
    try {
      const token = await getToken();
      const res = await fetch(`${baseURL}/contact/my`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setHistory(data.inquiries || []);
      }
    } catch {
      // silent
    } finally {
      setLoadingHistory(false);
    }
  };

  useEffect(() => {
    fetchHistory();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!subject.trim() || !message.trim()) return;

    setSubmitting(true);
    setError('');
    setSuccess(false);

    try {
      const token = await getToken();
      const res = await fetch(`${baseURL}/contact`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ category, subject, message }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || '送信に失敗しました');
      }

      setSuccess(true);
      setSubject('');
      setMessage('');
      setCategory('general');
      fetchHistory();
    } catch (err) {
      setError(err instanceof Error ? err.message : '送信に失敗しました');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="container mx-auto max-w-2xl p-6 space-y-6">
      <div className="space-y-1">
        <h1 className="text-2xl font-bold">お問い合わせ</h1>
        <p className="text-sm text-muted-foreground">
          ご質問・ご要望・不具合報告などお気軽にお寄せください。
        </p>
      </div>

      {/* 送信フォーム */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">お問い合わせフォーム</CardTitle>
          <CardDescription>内容を確認の上、担当者よりご連絡いたします。</CardDescription>
        </CardHeader>
        <CardContent>
          {success && (
            <div className="mb-4 flex items-center gap-2 rounded-lg bg-emerald-50 p-3 text-sm text-emerald-700">
              <CheckCircle2 className="h-4 w-4 shrink-0" />
              お問い合わせを受け付けました。ご連絡までしばらくお待ちください。
            </div>
          )}
          {error && (
            <div className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="category">カテゴリ</Label>
              <Select value={category} onValueChange={setCategory}>
                <SelectTrigger id="category">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {CATEGORY_OPTIONS.map((opt) => (
                    <SelectItem key={opt.value} value={opt.value}>
                      {opt.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="subject">件名</Label>
              <Input
                id="subject"
                placeholder="お問い合わせの件名を入力してください"
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                maxLength={200}
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="message">お問い合わせ内容</Label>
              <Textarea
                id="message"
                placeholder="お問い合わせ内容を詳しくご記入ください"
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                rows={6}
                maxLength={5000}
                required
              />
              <p className="text-xs text-muted-foreground text-right">
                {message.length} / 5000
              </p>
            </div>

            <Button type="submit" disabled={submitting || !subject.trim() || !message.trim()}>
              {submitting ? (
                <>
                  <span className="mr-2 h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
                  送信中...
                </>
              ) : (
                <>
                  <Send className="mr-2 h-4 w-4" />
                  送信する
                </>
              )}
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* お問い合わせ履歴 */}
      {!loadingHistory && history.length > 0 && (
        <Card>
          <button
            type="button"
            className="flex w-full items-center justify-between px-6 py-4"
            onClick={() => setShowHistory(!showHistory)}
          >
            <div className="flex items-center gap-2">
              <MessageSquare className="h-5 w-5 text-muted-foreground" />
              <span className="font-semibold">お問い合わせ履歴</span>
              <span className="text-xs text-muted-foreground">({history.length}件)</span>
            </div>
            <ChevronDown
              className={`h-4 w-4 text-muted-foreground transition-transform ${showHistory ? 'rotate-180' : ''}`}
            />
          </button>
          {showHistory && (
            <CardContent className="pt-0">
              <div className="divide-y">
                {history.map((item) => {
                  const st = STATUS_LABELS[item.status] || STATUS_LABELS.new;
                  const catLabel =
                    CATEGORY_OPTIONS.find((c) => c.value === item.category)?.label || item.category;
                  return (
                    <div key={item.id} className="py-3 space-y-1">
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-medium text-sm truncate">{item.subject}</span>
                        <span className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${st.color}`}>
                          {st.label}
                        </span>
                      </div>
                      <div className="flex items-center gap-2 text-xs text-muted-foreground">
                        <span>{catLabel}</span>
                        <span>·</span>
                        <Clock className="h-3 w-3" />
                        <span>{new Date(item.created_at).toLocaleDateString('ja-JP')}</span>
                      </div>
                      {item.admin_notes && (
                        <div className="mt-1 rounded bg-blue-50 p-2 text-xs text-blue-700">
                          <span className="font-medium">返信: </span>{item.admin_notes}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </CardContent>
          )}
        </Card>
      )}
    </div>
  );
}
