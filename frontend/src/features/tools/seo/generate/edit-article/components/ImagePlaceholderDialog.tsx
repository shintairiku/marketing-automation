'use client';

import React, { useState } from 'react';
import { Image } from 'lucide-react';

import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Textarea } from '@/components/ui/textarea';

interface ImagePlaceholderDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onAddImagePlaceholder: (description: string, position: number) => void;
  position: number;
}

export default function ImagePlaceholderDialog({
  isOpen,
  onClose,
  onAddImagePlaceholder,
  position
}: ImagePlaceholderDialogProps) {
  const [description, setDescription] = useState('');

  const handleAdd = () => {
    if (description.trim()) {
      onAddImagePlaceholder(description.trim(), position);
      setDescription('');
      onClose();
    }
  };

  const handleClose = () => {
    setDescription('');
    onClose();
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && e.ctrlKey) {
      handleAdd();
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="max-w-md">
        <DialogHeader className="space-y-3">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-blue-500 to-blue-600">
              <Image className="h-5 w-5 text-white" aria-hidden="true" />
            </div>
            <div>
              <DialogTitle className="text-lg font-semibold text-gray-900">
                画像プレースホルダーを追加
              </DialogTitle>
              <p className="text-sm text-gray-600">
                ブロック {position + 1} の前に追加
              </p>
            </div>
          </div>
        </DialogHeader>

        <div className="space-y-4">
          <div>
            <label htmlFor="image-description" className="block text-sm font-medium text-gray-700 mb-2">
              画像の説明
            </label>
            <Textarea
              id="image-description"
              placeholder="例：商品の特徴を示すグラフ、ユーザーが作業している様子、サービスの利用画面のスクリーンショット..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              onKeyDown={handleKeyPress}
              rows={4}
              className="resize-none"
              autoFocus
            />
          </div>

          <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
            <p className="text-xs text-blue-700 leading-relaxed">
              💡 プレースホルダーを追加後、画像をアップロードしたり、AI で生成したりできます。詳細な説明を入力することで、より適切な画像を生成できます。
            </p>
          </div>
        </div>

        <DialogFooter className="gap-2">
          <Button variant="outline" onClick={handleClose}>
            キャンセル
          </Button>
          <Button
            onClick={handleAdd}
            disabled={!description.trim()}
            className="min-w-[80px]"
          >
            追加
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}