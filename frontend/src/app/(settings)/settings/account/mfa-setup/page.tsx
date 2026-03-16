'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { ArrowRight, CheckCircle, Loader2, ShieldCheck } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { useClerk, useUser } from '@clerk/nextjs';

export default function MfaSetupPage() {
  const { isLoaded, user } = useUser();
  const { openUserProfile } = useClerk();
  const router = useRouter();
  const [checking, setChecking] = useState(false);

  // MFA が既に有効なら /admin にリダイレクト
  useEffect(() => {
    if (isLoaded && user?.twoFactorEnabled) {
      router.push('/admin');
    }
  }, [isLoaded, user?.twoFactorEnabled, router]);

  const handleOpenMfaSettings = () => {
    openUserProfile();
  };

  const handleCheckAndProceed = async () => {
    setChecking(true);
    // ユーザー情報をリロードして最新の twoFactorEnabled を取得
    await user?.reload();
    if (user?.twoFactorEnabled) {
      router.push('/admin');
    } else {
      setChecking(false);
    }
  };

  if (!isLoaded) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (user?.twoFactorEnabled) {
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

  return (
    <div className="container mx-auto p-6 max-w-lg">
      <Card>
        <CardHeader className="text-center">
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-amber-50">
            <ShieldCheck className="h-8 w-8 text-amber-600" />
          </div>
          <CardTitle className="text-xl">二段階認証の設定が必要です</CardTitle>
          <CardDescription className="text-base">
            管理者ページにアクセスするには、アカウントの二段階認証（MFA）を有効にしてください。
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="space-y-3 text-sm text-muted-foreground">
            <div className="flex gap-3">
              <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground text-xs font-bold">1</span>
              <span>下のボタンからアカウント設定を開く</span>
            </div>
            <div className="flex gap-3">
              <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground text-xs font-bold">2</span>
              <span>「セキュリティ」から二段階認証を追加（認証アプリ推奨）</span>
            </div>
            <div className="flex gap-3">
              <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground text-xs font-bold">3</span>
              <span>設定完了後、このページに戻って「確認して管理画面へ」をクリック</span>
            </div>
          </div>

          <div className="space-y-3">
            <Button onClick={handleOpenMfaSettings} className="w-full" size="lg">
              <ShieldCheck className="mr-2 h-4 w-4" />
              アカウント設定を開く
            </Button>

            <Button
              onClick={handleCheckAndProceed}
              variant="outline"
              className="w-full"
              size="lg"
              disabled={checking}
            >
              {checking ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <CheckCircle className="mr-2 h-4 w-4" />
              )}
              確認して管理画面へ
            </Button>
          </div>

          <p className="text-xs text-center text-muted-foreground">
            二段階認証により、パスワードが漏洩しても管理者アカウントを保護できます。
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
