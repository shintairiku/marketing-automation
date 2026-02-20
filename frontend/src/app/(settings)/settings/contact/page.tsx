'use client';

import { useEffect, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { CheckCircle, Loader2, MessageSquare, Send } from 'lucide-react';

import { useSubscription } from '@/components/subscription/subscription-guard';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { useAuth, useUser } from '@clerk/nextjs';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8080';
const USE_PROXY = process.env.NODE_ENV === 'production';
const baseURL = USE_PROXY ? '/api/proxy' : API_BASE_URL;

const CATEGORIES = [
  { value: 'general', label: '一般的なお問い合わせ' },
  { value: 'bug_report', label: '不具合の報告' },
  { value: 'feature_request', label: '機能リクエスト' },
  { value: 'billing', label: '請求・お支払い' },
  { value: 'account', label: 'アカウント関連' },
  { value: 'article_limit_increase', label: '記事生成数の追加リクエスト' },
  { value: 'other', label: 'その他' },
];

export default function ContactPage() {
  const { getToken } = useAuth();
  const { user } = useUser();
  const searchParams = useSearchParams();
  const { usage } = useSubscription();

  const initialCategory = searchParams.get('category') || 'general';
  const isArticleLimitRequest = initialCategory === 'article_limit_increase';

  const [name, setName] = useState(
    () => [user?.firstName, user?.lastName].filter(Boolean).join(' ') || ''
  );
  const [email, setEmail] = useState(
    () => user?.primaryEmailAddress?.emailAddress || ''
  );
  const [category, setCategory] = useState(initialCategory);
  const [subject, setSubject] = useState(
    () => isArticleLimitRequest ? '記事生成数の追加リクエスト' : ''
  );
  const [message, setMessage] = useState(() => {
    if (isArticleLimitRequest && usage) {
      return `現在の使用状況:\n- 生成済み: ${usage.articles_generated}件\n- 上限: ${usage.total_limit}件\n\n追加で記事生成枠をリクエストします。`;
    }
    return '';
  });
  // usage データが後から届いたときに自動入力
  useEffect(() => {
    if (isArticleLimitRequest && usage && !message) {
      setMessage(`現在の使用状況:\n- 生成済み: ${usage.articles_generated}件\n- 上限: ${usage.total_limit}件\n\n追加で記事生成枠をリクエストします。`);
    }
  }, [usage, isArticleLimitRequest, message]);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState('');

  const canSubmit = name.trim() && email.trim() && subject.trim() && message.trim() && !isSubmitting;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!canSubmit) return;

    setIsSubmitting(true);
    setError('');

    try {
      const token = await getToken();
      const res = await fetch(`${baseURL}/contact/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          name: name.trim(),
          email: email.trim(),
          category,
          subject: subject.trim(),
          message: message.trim(),
        }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => null);
        throw new Error(data?.detail || 'お問い合わせの送信に失敗しました');
      }

      setSubmitted(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'お問い合わせの送信に失敗しました');
    } finally {
      setIsSubmitting(false);
    }
  }

  function handleReset() {
    setSubject('');
    setMessage('');
    setCategory('general');
    setSubmitted(false);
    setError('');
  }

  if (submitted) {
    return (
      <div className="container mx-auto p-6">
        <div className="mx-auto max-w-2xl">
          <Card>
            <CardContent className="flex flex-col items-center gap-4 py-12">
              <div className="flex h-16 w-16 items-center justify-center rounded-full bg-emerald-100">
                <CheckCircle className="h-8 w-8 text-emerald-600" />
              </div>
              <h2 className="text-xl font-bold">お問い合わせを送信しました</h2>
              <p className="text-center text-muted-foreground">
                お問い合わせいただきありがとうございます。
                <br />
                内容を確認の上、ご連絡いたします。
              </p>
              <Button variant="outline" onClick={handleReset} className="mt-4">
                新しいお問い合わせを作成
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="space-y-2">
        <h1 className="text-3xl font-bold">お問い合わせ</h1>
        <p className="text-muted-foreground">
          ご質問・ご要望・不具合のご報告などをお送りください。
        </p>
      </div>

      <div className="mx-auto max-w-2xl">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <MessageSquare className="h-5 w-5" />
              お問い合わせフォーム
            </CardTitle>
            <CardDescription>
              下記フォームに必要事項をご記入の上、送信してください。
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-5">
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="name">お名前 *</Label>
                  <Input
                    id="name"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="山田 太郎"
                    maxLength={100}
                    required
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="email">メールアドレス *</Label>
                  <Input
                    id="email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="example@example.com"
                    maxLength={255}
                    required
                  />
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="category">カテゴリ</Label>
                <Select value={category} onValueChange={setCategory}>
                  <SelectTrigger id="category">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {CATEGORIES.map((c) => (
                      <SelectItem key={c.value} value={c.value}>
                        {c.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="subject">件名 *</Label>
                <Input
                  id="subject"
                  value={subject}
                  onChange={(e) => setSubject(e.target.value)}
                  placeholder="お問い合わせの件名"
                  maxLength={200}
                  required
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="message">お問い合わせ内容 *</Label>
                <Textarea
                  id="message"
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  placeholder="お問い合わせ内容を詳しくご記入ください"
                  rows={6}
                  maxLength={5000}
                  required
                />
                <p className="text-xs text-muted-foreground text-right">
                  {message.length} / 5,000
                </p>
              </div>

              {error && (
                <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">
                  {error}
                </div>
              )}

              <Button type="submit" disabled={!canSubmit} className="w-full">
                {isSubmitting ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
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
      </div>
    </div>
  );
}
