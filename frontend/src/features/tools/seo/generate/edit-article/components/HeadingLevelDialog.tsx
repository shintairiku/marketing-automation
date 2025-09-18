'use client';

import React from 'react';
import { Heading1, Heading2, Heading3, Heading4, Heading5, Heading6 } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';

interface HeadingLevelDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectHeading: (level: number) => void;
  position: number;
}

const headingLevels = [
  {
    level: 1,
    title: '見出し 1',
    description: '最大の見出し。記事のメインタイトルやページタイトルに使用します。',
    icon: Heading1,
    color: 'from-red-500 to-red-600',
    hoverColor: 'hover:from-red-600 hover:to-red-700',
    example: 'マーケティングオートメーションの完全ガイド'
  },
  {
    level: 2,
    title: '見出し 2',
    description: '大見出し。記事の主要なセクションに使用します。',
    icon: Heading2,
    color: 'from-orange-500 to-orange-600',
    hoverColor: 'hover:from-orange-600 hover:to-orange-700',
    example: 'マーケティングオートメーションとは何か'
  },
  {
    level: 3,
    title: '見出し 3',
    description: '中見出し。サブセクションや詳細な項目に使用します。',
    icon: Heading3,
    color: 'from-blue-500 to-blue-600',
    hoverColor: 'hover:from-blue-600 hover:to-blue-700',
    example: 'リードナーチャリングの基本'
  },
  {
    level: 4,
    title: '見出し 4',
    description: '小見出し。詳細な説明や細分化された項目に使用します。',
    icon: Heading4,
    color: 'from-indigo-500 to-indigo-600',
    hoverColor: 'hover:from-indigo-600 hover:to-indigo-700',
    example: 'メール配信のタイミング設定'
  },
  {
    level: 5,
    title: '見出し 5',
    description: '最小見出し。非常に具体的な項目や補足事項に使用します。',
    icon: Heading5,
    color: 'from-purple-500 to-purple-600',
    hoverColor: 'hover:from-purple-600 hover:to-purple-700',
    example: 'A/Bテストの設定方法'
  },
  {
    level: 6,
    title: '見出し 6',
    description: '最小レベルの見出し。詳細な補足や注記に使用します。',
    icon: Heading6,
    color: 'from-pink-500 to-pink-600',
    hoverColor: 'hover:from-pink-600 hover:to-pink-700',
    example: '注意事項とベストプラクティス'
  },
];

export default function HeadingLevelDialog({
  isOpen,
  onClose,
  onSelectHeading,
  position
}: HeadingLevelDialogProps) {
  const handleSelectHeading = (level: number) => {
    onSelectHeading(level);
    onClose();
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
        <DialogHeader className="space-y-3">
          <DialogTitle className="text-xl font-semibold text-gray-900">
            見出しレベルを選択
          </DialogTitle>
          <p className="text-sm text-gray-600">
            ブロック {position + 1} の前に追加する見出しのレベルを選択してください
          </p>
        </DialogHeader>

        <div className="grid gap-3 mt-6">
          {headingLevels.map((heading) => {
            const IconComponent = heading.icon;
            return (
              <Card
                key={heading.level}
                className="cursor-pointer transition-all duration-200 hover:shadow-lg hover:scale-[1.01] border-gray-200 group"
                onClick={() => handleSelectHeading(heading.level)}
              >
                <CardHeader className="pb-2">
                  <div className="flex items-start gap-3">
                    <div
                      className={`
                        flex items-center justify-center w-10 h-10 rounded-lg
                        bg-gradient-to-br ${heading.color} ${heading.hoverColor}
                        transition-all duration-200 shadow-md group-hover:shadow-lg
                      `}
                    >
                      <IconComponent className="w-5 h-5 text-white" />
                    </div>
                    <div className="flex-1">
                      <CardTitle className="text-base font-semibold text-gray-900 mb-1">
                        {heading.title}
                      </CardTitle>
                      <CardDescription className="text-xs text-gray-600 leading-relaxed">
                        {heading.description}
                      </CardDescription>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="pt-0">
                  <div className="bg-gray-50 rounded-md p-3 mb-3">
                    <p className="text-xs font-medium text-gray-500 mb-1">プレビュー例:</p>
                    <div
                      className={`
                        text-gray-900 font-semibold
                        ${heading.level === 1 ? 'text-2xl' : ''}
                        ${heading.level === 2 ? 'text-xl' : ''}
                        ${heading.level === 3 ? 'text-lg' : ''}
                        ${heading.level === 4 ? 'text-base' : ''}
                        ${heading.level === 5 ? 'text-sm' : ''}
                        ${heading.level === 6 ? 'text-xs' : ''}
                      `}
                    >
                      {heading.example}
                    </div>
                  </div>
                  <div className="flex justify-end">
                    <Button size="sm" className="text-sm">
                      H{heading.level}を追加
                    </Button>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>

        <div className="mt-6 p-4 bg-blue-50 rounded-lg border border-blue-200">
          <p className="text-xs text-blue-700 leading-relaxed">
            💡 <strong>SEOのヒント:</strong> 見出しは階層的に使用しましょう。H1は記事のメインタイトル、H2は大セクション、H3は小セクションという具合に、順序立てて使用することで検索エンジンが内容を理解しやすくなります。
          </p>
        </div>
      </DialogContent>
    </Dialog>
  );
}