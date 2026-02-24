'use client';

import { useEffect, useState } from 'react';
import Image from 'next/image';
import {
  Check,
  Chrome,
  Download,
  Globe,
  Monitor,
  MonitorSmartphone,
  Share,
  Smartphone,
  SquarePlus,
} from 'lucide-react';

import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {
  type Browser,
  type Platform,
  useInstallPrompt,
} from '@/hooks/useInstallPrompt';

// ---------- Step component ----------

function Step({
  number,
  children,
}: {
  number: number;
  children: React.ReactNode;
}) {
  return (
    <div className="flex gap-3">
      <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-stone-100 text-sm font-semibold text-stone-700">
        {number}
      </div>
      <div className="pt-0.5 text-sm leading-relaxed text-stone-600">
        {children}
      </div>
    </div>
  );
}

// ---------- Platform-specific instruction cards ----------

function IOSSafariInstructions() {
  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center gap-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-50">
            <Smartphone className="h-5 w-5 text-blue-600" />
          </div>
          <div>
            <CardTitle className="text-base">
              iPhone / iPad にインストール
            </CardTitle>
            <CardDescription className="text-xs">
              Safari ブラウザで操作してください
            </CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
          iOS では Safari からのみインストールできます。Chrome や他のブラウザでは
          この機能は利用できません。
        </div>
        <div className="space-y-3">
          <Step number={1}>
            画面下部の{' '}
            <span className="inline-flex items-center gap-1 rounded bg-stone-100 px-1.5 py-0.5 font-medium text-stone-800">
              <Share className="h-3.5 w-3.5" />
              共有ボタン
            </span>{' '}
            をタップ
          </Step>
          <Step number={2}>
            メニューを下にスクロールして{' '}
            <span className="inline-flex items-center gap-1 rounded bg-stone-100 px-1.5 py-0.5 font-medium text-stone-800">
              <SquarePlus className="h-3.5 w-3.5" />
              ホーム画面に追加
            </span>{' '}
            をタップ
          </Step>
          <Step number={3}>
            右上の{' '}
            <span className="font-medium text-stone-800">「追加」</span>{' '}
            をタップして完了
          </Step>
        </div>
        <div className="rounded-lg bg-stone-50 px-3 py-2 text-xs text-stone-500">
          インストール後はホーム画面のアイコンからアプリとして起動できます。
          ブラウザのUIは表示されず、フルスクリーンでご利用いただけます。
        </div>
      </CardContent>
    </Card>
  );
}

function IOSNonSafariInstructions({ browser }: { browser: Browser }) {
  const browserName =
    browser === 'chrome'
      ? 'Chrome'
      : browser === 'edge'
        ? 'Edge'
        : browser === 'firefox'
          ? 'Firefox'
          : 'このブラウザ';

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center gap-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-amber-50">
            <Globe className="h-5 w-5 text-amber-600" />
          </div>
          <div>
            <CardTitle className="text-base">Safari で開いてください</CardTitle>
            <CardDescription className="text-xs">
              {browserName}{' '}
              ではインストールできません
            </CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-800">
          iOS では Safari ブラウザからのみアプリをインストールできます。{browserName}{' '}
          ではインストール機能が利用できません。
        </div>
        <div className="space-y-3">
          <Step number={1}>
            Safari で{' '}
            <span className="font-mono text-xs font-medium text-stone-800">
              {typeof window !== 'undefined' ? window.location.origin : 'このサイト'}
            </span>{' '}
            を開く
          </Step>
          <Step number={2}>
            このページの手順に従ってインストール
          </Step>
        </div>
      </CardContent>
    </Card>
  );
}

function AndroidChromeInstructions({
  canPrompt,
  onInstall,
  installing,
}: {
  canPrompt: boolean;
  onInstall: () => void;
  installing: boolean;
}) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center gap-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-emerald-50">
            <Smartphone className="h-5 w-5 text-emerald-600" />
          </div>
          <div>
            <CardTitle className="text-base">
              Android にインストール
            </CardTitle>
            <CardDescription className="text-xs">
              Chrome / Edge ブラウザ
            </CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {canPrompt ? (
          <>
            <p className="text-sm text-stone-600">
              下のボタンをタップするとインストールダイアログが表示されます。
            </p>
            <Button
              onClick={onInstall}
              disabled={installing}
              className="w-full bg-emerald-600 hover:bg-emerald-700"
              size="lg"
            >
              {installing ? (
                'インストール中...'
              ) : (
                <>
                  <Download className="mr-2 h-4 w-4" />
                  アプリをインストール
                </>
              )}
            </Button>
          </>
        ) : (
          <>
            <div className="rounded-lg border border-stone-200 bg-stone-50 px-3 py-2 text-xs text-stone-600">
              インストールプロンプトが準備中です。下記の手動手順でもインストールできます。
            </div>
            <div className="space-y-3">
              <Step number={1}>
                ブラウザの右上{' '}
                <span className="font-medium text-stone-800">
                  「︙」メニュー
                </span>{' '}
                をタップ
              </Step>
              <Step number={2}>
                <span className="inline-flex items-center gap-1 rounded bg-stone-100 px-1.5 py-0.5 font-medium text-stone-800">
                  <Download className="h-3.5 w-3.5" />
                  アプリをインストール
                </span>{' '}
                または{' '}
                <span className="font-medium text-stone-800">
                  「ホーム画面に追加」
                </span>{' '}
                をタップ
              </Step>
              <Step number={3}>
                確認ダイアログで{' '}
                <span className="font-medium text-stone-800">
                  「インストール」
                </span>{' '}
                をタップ
              </Step>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}

function DesktopInstructions({
  canPrompt,
  onInstall,
  installing,
  browser,
}: {
  canPrompt: boolean;
  onInstall: () => void;
  installing: boolean;
  browser: Browser;
}) {
  const isChromium = browser === 'chrome' || browser === 'edge';

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center gap-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-violet-50">
            <Monitor className="h-5 w-5 text-violet-600" />
          </div>
          <div>
            <CardTitle className="text-base">PC にインストール</CardTitle>
            <CardDescription className="text-xs">
              {browser === 'chrome'
                ? 'Google Chrome'
                : browser === 'edge'
                  ? 'Microsoft Edge'
                  : 'ブラウザ'}
            </CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {canPrompt ? (
          <>
            <p className="text-sm text-stone-600">
              下のボタンをクリックするとインストールダイアログが表示されます。
            </p>
            <Button
              onClick={onInstall}
              disabled={installing}
              className="w-full bg-violet-600 hover:bg-violet-700"
              size="lg"
            >
              {installing ? (
                'インストール中...'
              ) : (
                <>
                  <Download className="mr-2 h-4 w-4" />
                  アプリをインストール
                </>
              )}
            </Button>
          </>
        ) : isChromium ? (
          <div className="space-y-3">
            <Step number={1}>
              アドレスバー右側の{' '}
              <span className="inline-flex items-center gap-1 rounded bg-stone-100 px-1.5 py-0.5 font-medium text-stone-800">
                <Download className="h-3.5 w-3.5" />
                インストールアイコン
              </span>{' '}
              をクリック
            </Step>
            <Step number={2}>
              確認ダイアログで{' '}
              <span className="font-medium text-stone-800">
                「インストール」
              </span>{' '}
              をクリック
            </Step>
          </div>
        ) : (
          <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">
            {browser === 'safari'
              ? 'Safari (macOS) ではメニューバー →「ファイル」→「Dockに追加」からインストールできます。'
              : browser === 'firefox'
                ? 'Firefox は PWA インストールに対応していません。Chrome または Edge をお使いください。'
                : 'Chrome または Edge でこのページを開いてインストールしてください。'}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ---------- Already installed ----------

function AlreadyInstalledCard() {
  return (
    <Card className="border-emerald-200 bg-emerald-50">
      <CardContent className="flex items-center gap-3 pt-6">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-emerald-100">
          <Check className="h-5 w-5 text-emerald-600" />
        </div>
        <div>
          <p className="font-medium text-emerald-800">インストール済み</p>
          <p className="text-sm text-emerald-600">
            BlogAI はすでにアプリとしてインストールされています。
            ホーム画面またはアプリランチャーから起動できます。
          </p>
        </div>
      </CardContent>
    </Card>
  );
}

// ---------- Benefits ----------

function BenefitsSection() {
  const benefits = [
    {
      icon: MonitorSmartphone,
      title: 'アプリとして動作',
      description:
        'ブラウザのURLバーやタブが非表示になり、フルスクリーンで快適に操作',
    },
    {
      icon: Download,
      title: 'ホーム画面から起動',
      description:
        'スマホのホーム画面やPCのDockにアイコンを追加、ワンタップで即アクセス',
    },
    {
      icon: Chrome,
      title: 'インストール不要',
      description:
        'App Store / Google Play は不要。ブラウザから直接インストール、容量も最小限',
    },
  ];

  return (
    <div className="grid gap-3 sm:grid-cols-3">
      {benefits.map((b) => (
        <div
          key={b.title}
          className="rounded-lg border border-stone-200 bg-white p-3"
        >
          <div className="mb-2 flex h-8 w-8 items-center justify-center rounded-lg bg-stone-100">
            <b.icon className="h-4 w-4 text-stone-600" />
          </div>
          <p className="text-sm font-medium text-stone-800">{b.title}</p>
          <p className="mt-0.5 text-xs text-stone-500">{b.description}</p>
        </div>
      ))}
    </div>
  );
}

// ---------- Main Page ----------

export default function InstallPage() {
  const { canPrompt, isInstalled, platform, browser, promptInstall } =
    useInstallPrompt();
  const [installing, setInstalling] = useState(false);
  const [justInstalled, setJustInstalled] = useState(false);
  // SSRではplatformが不確定なのでクライアントマウント後にのみ表示
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (isInstalled) {
      setJustInstalled(true);
    }
  }, [isInstalled]);

  const handleInstall = async () => {
    setInstalling(true);
    try {
      const accepted = await promptInstall();
      if (accepted) {
        setJustInstalled(true);
      }
    } finally {
      setInstalling(false);
    }
  };

  // SSR/ハイドレーション中はスケルトン
  if (!mounted) {
    return (
      <div className="mx-auto max-w-2xl px-4 py-6">
        <div className="mb-6">
          <div className="h-7 w-48 animate-pulse rounded bg-stone-200" />
          <div className="mt-2 h-4 w-72 animate-pulse rounded bg-stone-100" />
        </div>
        <div className="h-64 animate-pulse rounded-lg bg-stone-100" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl px-4 py-6">
      {/* Header */}
      <div className="mb-6 flex items-center gap-3">
        <Image
          src="/icon.png"
          alt="BlogAI"
          width={40}
          height={40}
          className="rounded-xl"
        />
        <div>
          <h1 className="text-lg font-bold text-stone-900">
            アプリをインストール
          </h1>
          <p className="text-sm text-stone-500">
            BlogAI をお使いのデバイスにインストール
          </p>
        </div>
      </div>

      <div className="space-y-4">
        {/* Already installed */}
        {(isInstalled || justInstalled) && <AlreadyInstalledCard />}

        {/* Platform-specific instructions */}
        {!isInstalled && !justInstalled && (
          <>
            {platform === 'ios' && browser === 'safari' && (
              <IOSSafariInstructions />
            )}
            {platform === 'ios' && browser !== 'safari' && (
              <IOSNonSafariInstructions browser={browser} />
            )}
            {platform === 'android' && (
              <AndroidChromeInstructions
                canPrompt={canPrompt}
                onInstall={handleInstall}
                installing={installing}
              />
            )}
            {platform === 'desktop' && (
              <DesktopInstructions
                canPrompt={canPrompt}
                onInstall={handleInstall}
                installing={installing}
                browser={browser}
              />
            )}
          </>
        )}

        {/* Benefits */}
        <div className="pt-2">
          <h2 className="mb-3 text-sm font-semibold text-stone-700">
            インストールのメリット
          </h2>
          <BenefitsSection />
        </div>
      </div>
    </div>
  );
}
