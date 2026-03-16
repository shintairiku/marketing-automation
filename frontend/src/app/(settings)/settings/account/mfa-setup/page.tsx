'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  ArrowRight,
  CheckCircle,
  ClipboardCopy,
  KeyRound,
  Loader2,
  ShieldCheck,
} from 'lucide-react';
import { QRCodeSVG } from 'qrcode.react';

import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Input } from '@/components/ui/input';

type PageState =
  | 'loading'
  | 'already_setup'
  | 'setup_qr'
  | 'confirm_code'
  | 'done';

interface SetupData {
  secret_uri: string;
  backup_codes: string[];
}

export default function MfaSetupPage() {
  const router = useRouter();
  const [state, setState] = useState<PageState>('loading');
  const [setupData, setSetupData] = useState<SetupData | null>(null);
  const [code, setCode] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [copied, setCopied] = useState(false);
  const [copiedKey, setCopiedKey] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const checkStatus = useCallback(async () => {
    try {
      const res = await fetch('/api/admin/mfa/status');
      if (!res.ok) {
        setState('setup_qr');
        return;
      }
      const data = await res.json();
      if (data.is_confirmed) {
        setState('already_setup');
      } else {
        // セットアップ開始
        await initSetup();
      }
    } catch {
      // ステータス取得失敗 → セットアップ開始
      await initSetup();
    }
  }, []);

  const initSetup = async () => {
    try {
      const res = await fetch('/api/admin/mfa/setup', { method: 'POST' });
      if (!res.ok) {
        const data = await res.json();
        setError(data.detail || 'セットアップの開始に失敗しました');
        setState('setup_qr');
        return;
      }
      const data = await res.json();
      setSetupData(data);
      setState('setup_qr');
    } catch {
      setError('セットアップの開始に失敗しました');
      setState('setup_qr');
    }
  };

  useEffect(() => {
    checkStatus();
  }, [checkStatus]);

  useEffect(() => {
    if (state === 'confirm_code' && inputRef.current) {
      inputRef.current.focus();
    }
  }, [state]);

  const handleConfirm = async () => {
    if (code.length < 6) return;
    setError('');
    setSubmitting(true);
    try {
      const res = await fetch('/api/admin/mfa/confirm', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code }),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data.detail || 'コードが正しくありません');
        setSubmitting(false);
        return;
      }
      setState('done');
    } catch {
      setError('確認に失敗しました');
      setSubmitting(false);
    }
  };

  const copyBackupCodes = () => {
    if (!setupData) return;
    navigator.clipboard.writeText(setupData.backup_codes.join('\n'));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const copyManualKey = () => {
    if (!setupData) return;
    // URI から secret を抽出
    const match = setupData.secret_uri.match(/secret=([^&]+)/);
    if (match) {
      navigator.clipboard.writeText(match[1]);
      setCopiedKey(true);
      setTimeout(() => setCopiedKey(false), 2000);
    }
  };

  // ---- Render States ----

  if (state === 'loading') {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (state === 'already_setup') {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center space-y-3">
          <CheckCircle className="h-12 w-12 text-emerald-500 mx-auto" />
          <p className="text-lg font-medium">二段階認証は設定済みです</p>
          <Button onClick={() => router.push('/admin')}>
            管理画面へ
            <ArrowRight className="ml-2 h-4 w-4" />
          </Button>
        </div>
      </div>
    );
  }

  if (state === 'done') {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center space-y-3">
          <CheckCircle className="h-12 w-12 text-emerald-500 mx-auto" />
          <p className="text-lg font-medium">二段階認証の設定が完了しました</p>
          <p className="text-sm text-muted-foreground">
            次回から管理画面アクセス時に認証コードの入力が必要です
          </p>
          <Button onClick={() => router.push('/admin')}>
            管理画面へ
            <ArrowRight className="ml-2 h-4 w-4" />
          </Button>
        </div>
      </div>
    );
  }

  // setup_qr or confirm_code
  return (
    <div className="container mx-auto p-6 max-w-lg">
      <Card>
        <CardHeader className="text-center">
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-amber-50">
            <ShieldCheck className="h-8 w-8 text-amber-600" />
          </div>
          <CardTitle className="text-xl">二段階認証の設定</CardTitle>
          <CardDescription className="text-base">
            管理者ページにアクセスするには、二段階認証（TOTP）の設定が必要です。
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* QR Code Section */}
          {setupData && state === 'setup_qr' && (
            <>
              <div className="space-y-3">
                <p className="text-sm font-medium">
                  1.
                  認証アプリ（Google Authenticator、Authy等）で以下のQRコードをスキャンしてください
                </p>
                <div className="flex justify-center p-4 bg-white rounded-lg border">
                  <QRCodeSVG
                    value={setupData.secret_uri}
                    size={200}
                    level="M"
                  />
                </div>

                {/* Manual Key */}
                <div className="space-y-1">
                  <p className="text-xs text-muted-foreground">
                    QRコードをスキャンできない場合は、以下のキーを手動で入力してください
                  </p>
                  <div className="flex items-center gap-2">
                    <code className="flex-1 text-xs bg-muted px-3 py-2 rounded font-mono break-all">
                      {setupData.secret_uri.match(/secret=([^&]+)/)?.[1] ||
                        ''}
                    </code>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={copyManualKey}
                      className="shrink-0"
                    >
                      {copiedKey ? (
                        <CheckCircle className="h-4 w-4 text-emerald-500" />
                      ) : (
                        <ClipboardCopy className="h-4 w-4" />
                      )}
                    </Button>
                  </div>
                </div>
              </div>

              {/* Backup Codes */}
              <div className="space-y-3">
                <p className="text-sm font-medium">
                  2.
                  バックアップコードを安全な場所に保存してください
                </p>
                <p className="text-xs text-muted-foreground">
                  認証アプリにアクセスできなくなった場合、バックアップコードで認証できます。
                  このコードは再表示できません。
                </p>
                <div className="bg-muted rounded-lg p-4">
                  <div className="grid grid-cols-2 gap-2 font-mono text-sm">
                    {setupData.backup_codes.map((c, i) => (
                      <div
                        key={i}
                        className="bg-background rounded px-2 py-1 text-center"
                      >
                        {c}
                      </div>
                    ))}
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={copyBackupCodes}
                    className="w-full mt-3"
                  >
                    {copied ? (
                      <>
                        <CheckCircle className="mr-2 h-4 w-4 text-emerald-500" />
                        コピーしました
                      </>
                    ) : (
                      <>
                        <ClipboardCopy className="mr-2 h-4 w-4" />
                        バックアップコードをコピー
                      </>
                    )}
                  </Button>
                </div>
              </div>

              <Button
                onClick={() => setState('confirm_code')}
                className="w-full"
                size="lg"
              >
                次へ：コードを入力して確認
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </>
          )}

          {/* Confirm Code Section */}
          {state === 'confirm_code' && (
            <div className="space-y-4">
              <p className="text-sm font-medium">
                3. 認証アプリに表示されている6桁のコードを入力してください
              </p>
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <KeyRound className="h-5 w-5 text-muted-foreground shrink-0" />
                  <Input
                    ref={inputRef}
                    type="text"
                    inputMode="numeric"
                    pattern="[0-9]*"
                    maxLength={6}
                    placeholder="000000"
                    value={code}
                    onChange={(e) => {
                      const val = e.target.value.replace(/\D/g, '');
                      setCode(val);
                      setError('');
                    }}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') handleConfirm();
                    }}
                    className="text-center text-2xl tracking-[0.5em] font-mono"
                  />
                </div>
                {error && (
                  <p className="text-sm text-destructive">{error}</p>
                )}
              </div>

              <div className="flex gap-2">
                <Button
                  variant="outline"
                  onClick={() => {
                    setState('setup_qr');
                    setCode('');
                    setError('');
                  }}
                >
                  戻る
                </Button>
                <Button
                  onClick={handleConfirm}
                  disabled={code.length < 6 || submitting}
                  className="flex-1"
                  size="lg"
                >
                  {submitting ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <ShieldCheck className="mr-2 h-4 w-4" />
                  )}
                  設定を完了
                </Button>
              </div>
            </div>
          )}

          {/* Error for setup_qr with no data */}
          {state === 'setup_qr' && !setupData && error && (
            <div className="space-y-3">
              <p className="text-sm text-destructive">{error}</p>
              <Button onClick={initSetup} variant="outline" className="w-full">
                再試行
              </Button>
            </div>
          )}

          <p className="text-xs text-center text-muted-foreground">
            二段階認証により、パスワードが漏洩しても管理者アカウントを保護できます。
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
