'use client';

import { useSubscription } from '@/components/subscription/subscription-guard';
import { cn } from '@/utils/cn';

interface UsageProgressBarProps {
  compact?: boolean;
  className?: string;
}

export function UsageProgressBar({ compact = false, className }: UsageProgressBarProps) {
  const { usage, subscription, isLoading } = useSubscription();

  // 特権ユーザーまたはローディング中は表示しない
  if (isLoading || subscription?.is_privileged || !usage) {
    return null;
  }

  const { articles_generated, total_limit, remaining } = usage;
  const percentage = total_limit > 0 ? Math.min(100, (articles_generated / total_limit) * 100) : 0;

  const getBarColor = () => {
    if (percentage >= 100) return 'bg-red-500';
    if (percentage >= 80) return 'bg-yellow-500';
    return 'bg-custom-orange';
  };

  const getTextColor = () => {
    if (percentage >= 100) return 'text-red-600';
    if (percentage >= 80) return 'text-yellow-600';
    return 'text-muted-foreground';
  };

  if (compact) {
    return (
      <div className={cn('flex items-center gap-2', className)}>
        <div className="h-1.5 w-16 rounded-full bg-muted overflow-hidden">
          <div
            className={cn('h-full rounded-full transition-all', getBarColor())}
            style={{ width: `${percentage}%` }}
          />
        </div>
        <span className={cn('text-xs', getTextColor())}>
          {articles_generated}/{total_limit}
        </span>
      </div>
    );
  }

  return (
    <div className={cn('space-y-2', className)}>
      <div className="flex items-center justify-between text-sm">
        <span className="text-muted-foreground">今月の記事生成</span>
        <span className={cn('font-medium', getTextColor())}>
          {articles_generated} / {total_limit} 記事
          {remaining > 0 && (
            <span className="text-muted-foreground font-normal ml-1">
              （残り{remaining}記事）
            </span>
          )}
        </span>
      </div>
      <div className="h-2 w-full rounded-full bg-muted overflow-hidden">
        <div
          className={cn('h-full rounded-full transition-all duration-500', getBarColor())}
          style={{ width: `${percentage}%` }}
        />
      </div>
      {percentage >= 100 && (
        <p className="text-xs text-red-600">
          月間上限に達しました。
          <a href="/settings/billing" className="underline ml-1">
            アドオンを追加
          </a>
          して上限を増やせます。
        </p>
      )}
      {percentage >= 80 && percentage < 100 && (
        <p className="text-xs text-yellow-600">
          上限の{Math.round(percentage)}%に達しています。
        </p>
      )}
    </div>
  );
}
