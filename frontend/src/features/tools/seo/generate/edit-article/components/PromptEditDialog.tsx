'use client';

import React, { useEffect, useState } from 'react';
import { Edit3, Save, X } from 'lucide-react';

import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Textarea } from '@/components/ui/textarea';

interface PromptEditDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (newPrompt: string) => Promise<void>;
  initialPrompt: string;
  placeholderId: string;
  isSaving?: boolean;
}

export default function PromptEditDialog({
  isOpen,
  onClose,
  onSave,
  initialPrompt,
  placeholderId,
  isSaving = false
}: PromptEditDialogProps) {
  const [prompt, setPrompt] = useState(initialPrompt);
  const [hasChanged, setHasChanged] = useState(false);

  useEffect(() => {
    if (isOpen) {
      setPrompt(initialPrompt);
      setHasChanged(false);
    }
  }, [isOpen, initialPrompt]);

  const handlePromptChange = (newPrompt: string) => {
    setPrompt(newPrompt);
    setHasChanged(newPrompt !== initialPrompt);
  };

  const handleSave = async () => {
    if (hasChanged && prompt.trim()) {
      await onSave(prompt.trim());
      onClose();
    }
  };

  const handleClose = () => {
    if (!isSaving) {
      onClose();
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && e.ctrlKey && !isSaving) {
      handleSave();
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-hidden">
        <DialogHeader className="space-y-3">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-purple-500 to-purple-600">
              <Edit3 className="h-5 w-5 text-white" aria-hidden="true" />
            </div>
            <div>
              <DialogTitle className="text-lg font-semibold text-gray-900">
                生成プロンプトを編集
              </DialogTitle>
              <DialogDescription className="text-sm text-gray-600">
                プレースホルダー ID: {placeholderId}
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>

        <div className="space-y-4 overflow-y-auto">
          <div>
            <label htmlFor="prompt-edit" className="block text-sm font-medium text-gray-700 mb-2">
              生成プロンプト（英語）
            </label>
            <Textarea
              id="prompt-edit"
              placeholder="画像生成に使用する詳細なプロンプトを英語で入力してください..."
              value={prompt}
              onChange={(e) => handlePromptChange(e.target.value)}
              onKeyDown={handleKeyPress}
              rows={8}
              className="resize-none font-mono text-sm"
              autoFocus
              disabled={isSaving}
            />
            <div className="mt-2 flex justify-between text-xs text-gray-500">
              <span>{prompt.length} 文字</span>
              <span>Ctrl+Enter で保存</span>
            </div>
          </div>

          <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
            <p className="text-xs text-blue-700 leading-relaxed">
              💡 詳細で具体的なプロンプトを書くことで、より適切な画像が生成されます。
              例：「modern office workspace with a person working on a laptop, clean minimalist design, natural lighting, professional atmosphere」
            </p>
          </div>

          {hasChanged && (
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-3">
              <p className="text-xs text-amber-700">
                ⚠️ 変更が保存されていません。「保存」ボタンを押して変更を確定してください。
              </p>
            </div>
          )}
        </div>

        <DialogFooter className="gap-2">
          <Button
            variant="outline"
            onClick={handleClose}
            disabled={isSaving}
          >
            <X className="w-4 h-4 mr-2" />
            キャンセル
          </Button>
          <Button
            onClick={handleSave}
            disabled={!hasChanged || !prompt.trim() || isSaving}
            className="min-w-[100px]"
          >
            {isSaving ? (
              <>
                <div className="mr-2 h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                保存中...
              </>
            ) : (
              <>
                <Save className="w-4 h-4 mr-2" />
                保存
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}