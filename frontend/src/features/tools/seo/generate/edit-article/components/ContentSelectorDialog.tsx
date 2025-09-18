'use client';

import React from 'react';
import { BookOpen, Heading1, Heading2, Heading3, List, ListOrdered, Plus, Type } from 'lucide-react';

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
    id: 'paragraph',
    title: '段落',
    description: '通常のテキスト段落を追加します。',
    icon: Type,
    color: 'from-gray-500 to-gray-600',
    hoverColor: 'hover:from-gray-600 hover:to-gray-700'
  },
  {
    id: 'heading',
    title: '見出し',
    description: '見出しを追加します。H1からH6までのレベルを選択できます。',
    icon: Heading1,
    color: 'from-purple-500 to-purple-600',
    hoverColor: 'hover:from-purple-600 hover:to-purple-700'
  },
  {
    id: 'unordered-list',
    title: '箇条書きリスト',
    description: 'ビュレットポイント形式のリストを追加します。',
    icon: List,
    color: 'from-green-500 to-green-600',
    hoverColor: 'hover:from-green-600 hover:to-green-700'
  },
  {
    id: 'ordered-list',
    title: '番号付きリスト',
    description: '順番を示す番号付きのリストを追加します。',
    icon: ListOrdered,
    color: 'from-orange-500 to-orange-600',
    hoverColor: 'hover:from-orange-600 hover:to-orange-700'
  },
  {
    id: 'table-of-contents',
    title: '目次を追加',
    description: '記事の見出しから自動で目次を生成します。見出しレベルをカスタマイズできます。',
    icon: BookOpen,
    color: 'from-teal-500 to-teal-600',
    hoverColor: 'hover:from-teal-600 hover:to-teal-700'
  },
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