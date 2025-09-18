'use client';

import React, { useRef, useState } from 'react';
import { Brain, Loader2, Paperclip, Send, X } from 'lucide-react';

import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Textarea } from '@/components/ui/textarea';
import { useToast } from '@/hooks/use-toast';
import { cn } from '@/utils/cn';

interface AIContentGenerationDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onGenerate: (blocks: Array<{
    type: 'heading' | 'paragraph';
    content: string;
    level?: number;
  }>) => void;
  position: number;
  getToken: () => Promise<string | null>;
  articleId?: string;
  articleHtml?: string;
}

interface AttachedFile {
  file: File;
  id: string;
  preview?: string;
}

export default function AIContentGenerationDialog({
  isOpen,
  onClose,
  onGenerate,
  position,
  getToken,
  articleId,
  articleHtml
}: AIContentGenerationDialogProps) {
  const [textInput, setTextInput] = useState('');
  const [includeHeading, setIncludeHeading] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [attachedFiles, setAttachedFiles] = useState<AttachedFile[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const { toast } = useToast();

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (!files) return;

    Array.from(files).forEach(file => {
      if (file.size > 10 * 1024 * 1024) { // 10MB limit
        toast({
          title: "ファイルサイズエラー",
          description: `${file.name}は10MB以下にしてください。`,
          variant: "destructive",
        });
        return;
      }

      const id = `file-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
      const attachedFile: AttachedFile = {
        file,
        id
      };

      // 画像ファイルの場合はプレビューを作成
      if (file.type.startsWith('image/')) {
        const reader = new FileReader();
        reader.onload = (e) => {
          attachedFile.preview = e.target?.result as string;
          setAttachedFiles(prev => [...prev, attachedFile]);
        };
        reader.readAsDataURL(file);
      } else {
        setAttachedFiles(prev => [...prev, attachedFile]);
      }
    });

    // ファイル入力をリセット
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const removeFile = (fileId: string) => {
    setAttachedFiles(prev => prev.filter(f => f.id !== fileId));
  };

  const handleGenerate = async () => {
    try {
      setIsGenerating(true);

      if (!textInput.trim() && attachedFiles.length === 0) {
        toast({
          title: "入力エラー",
          description: "テキストを入力するか、ファイルを添付してください。",
          variant: "destructive",
        });
        return;
      }

      if (attachedFiles.length > 1) {
        toast({
          title: "添付数エラー",
          description: "ファイルは1件まで添付できます。",
          variant: "destructive",
        });
        return;
      }

      // 単一添付ファイルがある場合はアップロードAPIを利用
      if (attachedFiles.length === 1) {
        const formData = new FormData();
        formData.append('file', attachedFiles[0].file);
        formData.append('include_heading', includeHeading.toString());
        if (textInput.trim()) {
          formData.append('user_instruction', textInput);
        }
        if (articleId) {
          formData.append('article_id', articleId);
        }
        if (position !== undefined) {
          formData.append('insert_position', position.toString());
        }
        if (articleHtml) {
          formData.append('article_html', articleHtml);
        }

        const token = await getToken();
        const headers: HeadersInit = {};
        if (token) {
          headers.Authorization = `Bearer ${token}`;
        }

        const response = await fetch('/api/proxy/articles/ai-content-generation/upload', {
          method: 'POST',
          headers,
          body: formData,
        });

        if (!response.ok) {
          throw new Error(`API Error: ${response.status}`);
        }

        const result = await response.json();
        if (result.success && result.blocks?.length > 0) {
          processGenerationResult(result.blocks);
        } else {
          throw new Error(result.error || 'コンテンツ生成に失敗しました');
        }
      } else {
        // テキスト入力のみの場合
        const requestData = {
          input_type: 'text',
          content: textInput,
          include_heading: includeHeading,
          article_id: articleId,
          insert_position: position,
          article_html: articleHtml
        };

        const token = await getToken();
        const headers: HeadersInit = {
          'Content-Type': 'application/json',
        };
        if (token) {
          headers.Authorization = `Bearer ${token}`;
        }

        const response = await fetch('/api/proxy/articles/ai-content-generation', {
          method: 'POST',
          headers,
          body: JSON.stringify(requestData),
        });

        if (!response.ok) {
          throw new Error(`API Error: ${response.status}`);
        }

        const result = await response.json();
        if (result.success && result.blocks?.length > 0) {
          processGenerationResult(result.blocks);
        } else {
          throw new Error(result.error || 'コンテンツ生成に失敗しました');
        }
      }

    } catch (error) {
      console.error('AI content generation error:', error);
      toast({
        title: "生成エラー",
        description: error instanceof Error ? error.message : "コンテンツ生成に失敗しました。",
        variant: "destructive",
      });
    } finally {
      setIsGenerating(false);
    }
  };

  const processGenerationResult = (blocks: any[]) => {
    // ブロックデータを変換
    const processedBlocks = blocks.map((block: any) => ({
      type: (block.type === 'heading' ? 'heading' : 'paragraph') as 'heading' | 'paragraph',
      content: String(block.content || ''),
      level: block.level as number | undefined
    }));

    onGenerate(processedBlocks);
    onClose();

    toast({
      title: "コンテンツ生成完了",
      description: `${processedBlocks.length}個のブロックを生成しました。`,
      variant: "default",
    });

    // フォームリセット
    setTextInput('');
    setIncludeHeading(false);
    setAttachedFiles([]);
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-hidden">
        <DialogHeader className="space-y-3 pb-4 border-b">
          <DialogTitle className="text-xl font-semibold text-gray-900 flex items-center gap-2">
            <Brain className="w-6 h-6 text-purple-600" />
            AIコンテンツ生成
          </DialogTitle>
          <DialogDescription className="text-sm text-gray-600">
            ブロック {position + 1} の前に追加するコンテンツをAIで生成します
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col h-[60vh]">
          {/* メッセージ表示エリア */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-50 rounded-lg">
            {/* 添付ファイル表示 */}
            {attachedFiles.length > 0 && (
              <div className="space-y-2">
                {attachedFiles.map((attachedFile) => (
                  <div
                    key={attachedFile.id}
                    className="flex items-center gap-3 p-3 bg-white rounded-lg border border-gray-200"
                  >
                    {attachedFile.preview ? (
                      <img
                        src={attachedFile.preview}
                        alt={attachedFile.file.name}
                        className="w-12 h-12 rounded object-cover"
                      />
                    ) : (
                      <div className="w-12 h-12 bg-gray-200 rounded flex items-center justify-center">
                        <Paperclip className="w-6 h-6 text-gray-500" />
                      </div>
                    )}
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 truncate">
                        {attachedFile.file.name}
                      </p>
                      <p className="text-xs text-gray-500">
                        {(attachedFile.file.size / 1024 / 1024).toFixed(2)} MB
                      </p>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => removeFile(attachedFile.id)}
                      className="text-gray-400 hover:text-red-500"
                    >
                      <X className="w-4 h-4" />
                    </Button>
                  </div>
                ))}
              </div>
            )}

            {/* 空の状態 */}
            {attachedFiles.length === 0 && !textInput && (
              <div className="flex items-center justify-center h-full text-gray-500">
                <div className="text-center">
                  <Brain className="w-12 h-12 mx-auto mb-3 text-gray-300" />
                  <p className="text-sm">
                    テキストを入力するか、ファイルを添付してコンテンツを生成しましょう
                  </p>
                </div>
              </div>
            )}
          </div>

          {/* オプション設定 */}
          <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg my-4">
            <div className="flex items-center justify-between">
              <div>
                <Label htmlFor="include-heading" className="text-sm font-medium text-blue-800">
                  見出しを含める
                </Label>
                <p className="text-xs text-blue-600 mt-1">
                  見出しブロック + 段落ブロックを生成します
                </p>
              </div>
              <Switch
                id="include-heading"
                checked={includeHeading}
                onCheckedChange={setIncludeHeading}
              />
            </div>
          </div>

          {/* 入力エリア */}
          <div className="border rounded-lg bg-white">
            {/* ツールバー */}
            <div className="flex items-center gap-2 p-3 border-b bg-gray-50">
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => fileInputRef.current?.click()}
                className="text-gray-600 hover:text-gray-800"
              >
                <Paperclip className="w-4 h-4" />
              </Button>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*,text/*,.pdf,.doc,.docx"
                onChange={handleFileSelect}
                className="hidden"
                multiple
              />
              <span className="text-xs text-gray-500">
                画像、テキストファイル、PDF対応
              </span>
            </div>

            {/* テキスト入力 */}
            <div className="relative">
              <Textarea
                placeholder="コンテンツの内容やURLを入力してください。URLを含めると自動的にWeb検索を行います..."
                value={textInput}
                onChange={(e) => setTextInput(e.target.value)}
                className="min-h-[100px] border-0 resize-none focus:ring-0 focus:outline-none rounded-none"
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
                    e.preventDefault();
                    handleGenerate();
                  }
                }}
              />

              {/* 送信ボタン */}
              <div className="absolute bottom-3 right-3">
                <Button
                  onClick={handleGenerate}
                  disabled={isGenerating || (!textInput.trim() && attachedFiles.length === 0)}
                  className="bg-purple-600 hover:bg-purple-700 text-white rounded-full w-8 h-8 p-0"
                >
                  {isGenerating ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Send className="w-4 h-4" />
                  )}
                </Button>
              </div>
            </div>

            {/* ヒント */}
            <div className="px-3 pb-3">
              <p className="text-xs text-gray-500">
                💡 Cmd/Ctrl + Enter で送信 | URL含有時は自動でWeb検索
              </p>
            </div>
          </div>
        </div>

        {/* パワードバイ */}
        <div className="mt-4 p-3 bg-gradient-to-r from-purple-50 to-blue-50 rounded-lg border border-purple-200">
          <p className="text-xs text-purple-700 text-center">
            🚀 <strong>Powered by OpenAI GPT-5</strong> with Web Search - 最新情報も活用
          </p>
        </div>
      </DialogContent>
    </Dialog>
  );
}
