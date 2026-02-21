'use client';

import { useCallback, useEffect, useRef, useState } from 'react';

// ---------- Types ----------

interface BeforeInstallPromptEvent extends Event {
  prompt(): Promise<{ outcome: 'accepted' | 'dismissed' }>;
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>;
}

export type Platform = 'ios' | 'android' | 'desktop';
export type Browser = 'safari' | 'chrome' | 'edge' | 'firefox' | 'samsung' | 'other';

export interface InstallPromptState {
  /** beforeinstallprompt が使える (Chrome/Edge) */
  canPrompt: boolean;
  /** 既にスタンドアロンモードで動作中 */
  isInstalled: boolean;
  /** ユーザーのプラットフォーム */
  platform: Platform;
  /** ユーザーのブラウザ */
  browser: Browser;
  /** Chrome/Edge: ネイティブインストールプロンプトを表示 */
  promptInstall: () => Promise<boolean>;
}

// ---------- Detection Helpers ----------

function detectPlatform(): Platform {
  if (typeof navigator === 'undefined') return 'desktop';
  const ua = navigator.userAgent;
  // iPadOS returns 'MacIntel' but has touch
  if (
    /iPad|iPhone|iPod/.test(ua) ||
    (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1)
  ) {
    return 'ios';
  }
  if (/Android/.test(ua)) return 'android';
  return 'desktop';
}

function detectBrowser(): Browser {
  if (typeof navigator === 'undefined') return 'other';
  const ua = navigator.userAgent;
  // Order matters: Edge UA includes "Chrome", Samsung Internet includes "Chrome"
  if (/SamsungBrowser/.test(ua)) return 'samsung';
  if (/Edg\//.test(ua)) return 'edge';
  if (/CriOS|Chrome/.test(ua)) return 'chrome';
  if (/FxiOS|Firefox/.test(ua)) return 'firefox';
  if (/Safari/.test(ua)) return 'safari';
  return 'other';
}

function checkIsInstalled(): boolean {
  if (typeof window === 'undefined') return false;
  // CSS media query: standalone mode
  if (window.matchMedia('(display-mode: standalone)').matches) return true;
  // iOS Safari standalone
  if ((navigator as unknown as Record<string, unknown>).standalone === true) return true;
  return false;
}

// ---------- Hook ----------

export function useInstallPrompt(): InstallPromptState {
  const [canPrompt, setCanPrompt] = useState(false);
  const [isInstalled, setIsInstalled] = useState(false);
  const deferredPromptRef = useRef<BeforeInstallPromptEvent | null>(null);
  const [platform] = useState<Platform>(() => detectPlatform());
  const [browser] = useState<Browser>(() => detectBrowser());

  useEffect(() => {
    if (checkIsInstalled()) {
      setIsInstalled(true);
      return;
    }

    const handleBeforeInstall = (e: Event) => {
      e.preventDefault();
      deferredPromptRef.current = e as BeforeInstallPromptEvent;
      setCanPrompt(true);
    };

    const handleAppInstalled = () => {
      setIsInstalled(true);
      setCanPrompt(false);
      deferredPromptRef.current = null;
    };

    window.addEventListener('beforeinstallprompt', handleBeforeInstall);
    window.addEventListener('appinstalled', handleAppInstalled);

    // display-mode の変更を監視（インストール後に遷移する場合）
    const mql = window.matchMedia('(display-mode: standalone)');
    const handleDisplayChange = (e: MediaQueryListEvent) => {
      if (e.matches) {
        setIsInstalled(true);
        setCanPrompt(false);
      }
    };
    mql.addEventListener('change', handleDisplayChange);

    return () => {
      window.removeEventListener('beforeinstallprompt', handleBeforeInstall);
      window.removeEventListener('appinstalled', handleAppInstalled);
      mql.removeEventListener('change', handleDisplayChange);
    };
  }, []);

  const promptInstall = useCallback(async () => {
    const prompt = deferredPromptRef.current;
    if (!prompt) return false;
    try {
      const result = await prompt.prompt();
      deferredPromptRef.current = null;
      setCanPrompt(false);
      return result.outcome === 'accepted';
    } catch {
      return false;
    }
  }, []);

  return { canPrompt, isInstalled, platform, browser, promptInstall };
}
