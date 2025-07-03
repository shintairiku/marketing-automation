'use client';

import React from 'react';
import { BookOpen, Plus } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';

interface ContentSelectorDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectContent: (type: string) => void;
  position: number;
}

const contentTypes = [
  {
    id: 'table-of-contents',
    title: '目次を追加',
    description: '記事の見出しから自動で目次を生成します。見出しレベルをカスタマイズできます。',
    icon: BookOpen,
    color: 'from-blue-500 to-blue-600',
    hoverColor: 'hover:from-blue-600 hover:to-blue-700'
  },
  // 将来的に他のコンテンツタイプを追加予定
];

export default function ContentSelectorDialog({
  isOpen,
  onClose,
  onSelectContent,
  position
}: ContentSelectorDialogProps) {
  const handleSelectContent = (type: string) => {
    onSelectContent(type);
    onClose();
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
        <DialogHeader className="space-y-3">
          <DialogTitle className="text-xl font-semibold text-gray-900">
            コンテンツを追加
          </DialogTitle>
          <p className="text-sm text-gray-600">
            ブロック {position + 1} の前に追加するコンテンツを選択してください
          </p>
        </DialogHeader>

        <div className="grid gap-4 mt-6">
          {contentTypes.map((content) => {
            const IconComponent = content.icon;
            return (
              <Card
                key={content.id}
                className="cursor-pointer transition-all duration-200 hover:shadow-lg hover:scale-[1.02] border-gray-200"
                onClick={() => handleSelectContent(content.id)}
              >
                <CardHeader className="pb-3">
                  <div className="flex items-start gap-3">
                    <div 
                      className={`
                        flex items-center justify-center w-12 h-12 rounded-lg 
                        bg-gradient-to-br ${content.color} ${content.hoverColor}
                        transition-all duration-200 shadow-md
                      `}
                    >
                      <IconComponent className="w-6 h-6 text-white" />
                    </div>
                    <div className="flex-1">
                      <CardTitle className="text-lg font-semibold text-gray-900 mb-1">
                        {content.title}
                      </CardTitle>
                      <CardDescription className="text-sm text-gray-600 leading-relaxed">
                        {content.description}
                      </CardDescription>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="pt-0">
                  <div className="flex justify-end">
                    <Button size="sm" className="text-sm">
                      <Plus className="w-4 h-4 mr-2" />
                      追加
                    </Button>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>

        <div className="mt-6 p-4 bg-gray-50 rounded-lg border">
          <p className="text-xs text-gray-500 leading-relaxed">
            💡 その他のコンテンツタイプ（画像、引用、コードブロックなど）は今後のアップデートで追加予定です。
          </p>
        </div>
      </DialogContent>
    </Dialog>
  );
}