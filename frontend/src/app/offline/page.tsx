'use client';

import { RefreshCw, WifiOff } from 'lucide-react';

export default function OfflinePage() {
  return (
    <div className="flex min-h-dvh items-center justify-center bg-gradient-to-b from-stone-50 to-stone-100 px-4">
      <div className="text-center">
        <div className="mx-auto mb-6 flex h-20 w-20 items-center justify-center rounded-full bg-stone-200">
          <WifiOff className="h-10 w-10 text-stone-500" />
        </div>
        <h1 className="mb-2 text-2xl font-bold text-stone-900">
          オフラインです
        </h1>
        <p className="mb-8 text-stone-600">
          インターネット接続を確認してから、もう一度お試しください。
        </p>
        <button
          onClick={() => window.location.reload()}
          className="inline-flex items-center gap-2 rounded-lg bg-custom-orange px-6 py-3 text-sm font-medium text-white transition-colors hover:bg-custom-orange/90"
        >
          <RefreshCw className="h-4 w-4" />
          再読み込み
        </button>
      </div>
    </div>
  );
}
