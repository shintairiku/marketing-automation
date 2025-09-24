'use client';

import React, { useState } from 'react';
import { Brain, Plus } from 'lucide-react';

import { cn } from '@/utils/cn';

interface BlockInsertButtonProps {
  onInsertContent: (type: string, position: number) => void;
  onAIGenerate?: (position: number) => void; // AI生成用のコールバック
  position: number; // ブロック間の位置（0番目のブロックの前、1番目のブロックの前など）
  className?: string;
}

export default function BlockInsertButton({
  onInsertContent,
  onAIGenerate,
  position,
  className
}: BlockInsertButtonProps) {
  const [isVisible, setIsVisible] = useState(false);
  const [hoveredButton, setHoveredButton] = useState<string | null>(null);

  return (
    <div
      className={cn(
        'relative my-1 flex w-full items-center justify-center py-2',
        className
      )}
      data-interactive="true"
      onMouseEnter={() => setIsVisible(true)}
      onMouseLeave={() => {
        setIsVisible(false);
        setHoveredButton(null);
      }}
    >
      <span className="pointer-events-none absolute inset-x-0 top-1/2 -translate-y-1/2">
        <span className="mx-auto block h-px w-full max-w-3xl bg-gradient-to-r from-transparent via-slate-200 to-transparent" />
      </span>

      <div className="relative z-10 flex items-center gap-2">
        <button
          className={cn(
            'flex h-6 w-6 items-center justify-center rounded-full border border-slate-200 bg-white shadow-sm transition-all',
            'focus:outline-none focus:ring-2 focus:ring-purple-500/70 focus:ring-offset-2',
            isVisible ? 'opacity-100 translate-y-0' : 'pointer-events-none translate-y-1 opacity-0'
          )}
          onMouseEnter={() => setHoveredButton('add')}
          onMouseLeave={() => setHoveredButton(null)}
          onClick={() => onInsertContent('selector', position)}
          title="コンテンツを追加"
        >
          <Plus className={cn('h-3.5 w-3.5 text-slate-500 transition-colors', hoveredButton === 'add' ? 'text-purple-500' : '')} />
        </button>

        {onAIGenerate && (
          <button
            className={cn(
              'hidden sm:flex h-6 items-center gap-1 rounded-full border border-purple-200 bg-gradient-to-r from-purple-500/90 via-purple-500 to-purple-500 text-white shadow-sm transition-all',
              'px-3 text-xs font-medium hover:from-purple-500 hover:to-purple-600 focus:outline-none focus:ring-2 focus:ring-purple-500/70 focus:ring-offset-2',
              isVisible ? 'opacity-100 translate-y-0' : 'pointer-events-none translate-y-1 opacity-0'
            )}
            onMouseEnter={() => setHoveredButton('ai')}
            onMouseLeave={() => setHoveredButton(null)}
            onClick={() => onAIGenerate(position)}
            title="AIでコンテンツを生成"
          >
            <Brain className="h-3.5 w-3.5" />
            <span>AI</span>
          </button>
        )}
      </div>
    </div>
  );
}
