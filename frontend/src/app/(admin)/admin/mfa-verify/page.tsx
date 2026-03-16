'use client';

import { useEffect, useRef, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { KeyRound, Loader2, Lock, ShieldCheck } from 'lucide-react';

import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Input } from '@/components/ui/input';

export default function MfaVerifyPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const redirect = searchParams.get('redirect') || '/admin';

  const [code, setCode] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [useBackup, setUseBackup] = useState(false);
  const [locked, setLocked] = useState(false);
  const [lockMessage, setLockMessage] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.focus();
    }
  }, [useBackup]);

  const handleVerify = async () => {
    const trimmed = code.trim();
    if (trimmed.length < 6) return;

    setError('');
    setSubmitting(true);

    try {
      const res = await fetch('/api/admin/mfa/verify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code: trimmed }),
      });

      const data = await res.json();

      if (res.status === 429) {
        setLocked(true);
        setLockMessage(data.detail || '認証が一時的にロックされています');
        setSubmitting(false);
        return;
      }

      if (!res.ok) {
        setError(data.detail || '認証に失敗しました');
        setSubmitting(false);
        return;
      }

      if (data.success) {
        router.push(redirect);
      } else {
        setError(data.message || 'コードが正しくありません');
        setSubmitting(false);
      }
    } catch {
      setError('認証に失敗しました');
      setSubmitting(false);
    }
  };

  if (locked) {
    return (
      <div className="flex items-center justify-center min-h-[calc(100dvh-120px)]">
        <Card className="w-full max-w-md mx-4">
          <CardHeader className="text-center">
            <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-red-50">
              <Lock className="h-8 w-8 text-red-600" />
            </div>
            <CardTitle className="text-xl">アカウントロック</CardTitle>
            <CardDescription className="text-base">
              {lockMessage}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button
              variant="outline"
              className="w-full"
              onClick={() => router.push('/blog/new')}
            >
              アプリに戻る
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="flex items-center justify-center min-h-[calc(100dvh-120px)]">
      <Card className="w-full max-w-md mx-4">
        <CardHeader className="text-center">
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-amber-50">
            <ShieldCheck className="h-8 w-8 text-amber-600" />
          </div>
          <CardTitle className="text-xl">二段階認証</CardTitle>
          <CardDescription className="text-base">
            {useBackup
              ? 'バックアップコードを入力してください'
              : '認証アプリに表示されている6桁のコードを入力してください'}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <KeyRound className="h-5 w-5 text-muted-foreground shrink-0" />
              <Input
                ref={inputRef}
                type="text"
                inputMode={useBackup ? 'text' : 'numeric'}
                pattern={useBackup ? undefined : '[0-9]*'}
                maxLength={useBackup ? 8 : 6}
                placeholder={useBackup ? 'XXXXXXXX' : '000000'}
                value={code}
                onChange={(e) => {
                  const val = useBackup
                    ? e.target.value.toUpperCase()
                    : e.target.value.replace(/\D/g, '');
                  setCode(val);
                  setError('');
                }}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleVerify();
                }}
                className={`text-center text-2xl font-mono ${
                  useBackup ? 'tracking-[0.3em]' : 'tracking-[0.5em]'
                }`}
              />
            </div>
            {error && <p className="text-sm text-destructive">{error}</p>}
          </div>

          <Button
            onClick={handleVerify}
            disabled={
              submitting ||
              (useBackup ? code.length < 8 : code.length < 6)
            }
            className="w-full"
            size="lg"
          >
            {submitting ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <ShieldCheck className="mr-2 h-4 w-4" />
            )}
            認証
          </Button>

          <div className="text-center">
            <button
              type="button"
              className="text-sm text-muted-foreground hover:text-foreground underline-offset-4 hover:underline transition-colors"
              onClick={() => {
                setUseBackup(!useBackup);
                setCode('');
                setError('');
              }}
            >
              {useBackup
                ? '認証アプリのコードを使用'
                : 'バックアップコードを使用'}
            </button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
