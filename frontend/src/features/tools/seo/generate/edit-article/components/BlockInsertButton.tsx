'use client';

import React, { useState } from 'react';
import { Brain,Plus } from 'lucide-react';

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
        "relative w-full h-6 flex items-center justify-center group",
        "transition-all duration-200 ease-in-out",
        className
      )}
      onMouseEnter={() => setIsVisible(true)}
      onMouseLeave={() => {
        setIsVisible(false);
        setHoveredButton(null);
      }}
    >
      {/* ホバー時に表示される水平線 */}
      <div
        className={cn(
          "absolute inset-0 flex items-center transition-opacity duration-200",
          isVisible ? "opacity-100" : "opacity-0"
        )}
      >
        <div className="w-full h-px bg-gray-300" />
      </div>

      {/* ボタンコンテナ */}
      <div className="relative z-10 flex items-center gap-2">
        {/* 追加ボタン */}
        <button
          className={cn(
            "flex items-center justify-center",
            "w-8 h-8 rounded-full border transition-all duration-200",
            "focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2",
            isVisible || hoveredButton === 'add'
              ? "opacity-100 scale-100 bg-white border-gray-300 shadow-sm hover:border-blue-400 hover:shadow-md"
              : "opacity-0 scale-75 bg-transparent border-transparent"
          )}
          onMouseEnter={() => setHoveredButton('add')}
          onMouseLeave={() => setHoveredButton(null)}
          onClick={() => onInsertContent('selector', position)}
          title="コンテンツを追加"
        >
          <Plus
            className={cn(
              "w-4 h-4 transition-colors duration-200",
              hoveredButton === 'add' ? "text-blue-600" : "text-gray-600"
            )}
          />
        </button>

        {/* AIボタン */}
        {onAIGenerate && (
          <button
            className={cn(
              "flex items-center justify-center",
              "w-8 h-8 rounded-full border transition-all duration-200",
              "focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2",
              isVisible || hoveredButton === 'ai'
                ? "opacity-100 scale-100 bg-gradient-to-br from-purple-500 to-purple-600 border-purple-400 shadow-sm hover:from-purple-600 hover:to-purple-700 hover:shadow-md"
                : "opacity-0 scale-75 bg-transparent border-transparent"
            )}
            onMouseEnter={() => setHoveredButton('ai')}
            onMouseLeave={() => setHoveredButton(null)}
            onClick={() => onAIGenerate(position)}
            title="AIでコンテンツを生成"
          >
            <Brain
              className={cn(
                "w-4 h-4 transition-colors duration-200",
                hoveredButton === 'ai' || isVisible ? "text-white" : "text-purple-600"
              )}
            />
          </button>
        )}
      </div>
    </div>
  );
}