'use client';

import { useState } from 'react';
import Link from 'next/link';
import { IoArrowBack, IoCheckmarkCircle, IoSave } from 'react-icons/io5';

import { Button } from '@/components/ui/button';
import { toast } from '@/components/ui/use-toast';
import { ArticleChatEditor } from '@/features/article-editing/components/article-chat-editor';
import { ArticlePreview } from '@/features/article-generation/components/article-preview';
import { GeneratedArticle } from '@/features/article-generation/types';

interface ArticleEditPageProps {
  article: GeneratedArticle;
  onSave: (article: GeneratedArticle) => Promise<void>;
}

export function ArticleEditPage({ article: initialArticle, onSave }: ArticleEditPageProps) {
  const [article, setArticle] = useState<GeneratedArticle>(initialArticle);
  const [isSaving, setIsSaving] = useState(false);
  const [isEditing, setIsEditing] = useState(false);

  const handleArticleUpdate = (updatedArticle: GeneratedArticle) => {
    setArticle(updatedArticle);
  };

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await onSave(article);
      toast({
        description: '記事が保存されました',
      });
    } catch (error) {
      toast({
        variant: 'destructive',
        description: '記事の保存中にエラーが発生しました',
      });
    } finally {
      setIsSaving(false);
    }
  };

  const handleChatStart = () => {
    setIsEditing(true);
  };

  return (
    <div className="w-full space-y-8">
      <div className="flex items-center justify-between">
        <Link href="/dashboard" passHref>
          <Button variant="ghost" size="sm">
            <IoArrowBack className="mr-2" size={18} /> ダッシュボードに戻る
          </Button>
        </Link>

        <Button
          variant="secondary"
          onClick={handleSave}
          disabled={isSaving}
          className="flex items-center"
        >
          {isSaving ? (
            'Saving...'
          ) : (
            <>
              <IoSave className="mr-2" size={18} /> 記事を保存
            </>
          )}
        </Button>
      </div>

      {isEditing ? (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <div className="lg:order-2">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-xl font-semibold">プレビュー</h2>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setIsEditing(false)}
                className="flex items-center"
              >
                <IoCheckmarkCircle className="mr-2" size={16} /> 編集を完了
              </Button>
            </div>
            <div className="h-[700px] overflow-y-auto rounded-md border border-gray-700 p-4">
              <ArticlePreview article={article} onStartChat={() => setIsEditing(true)} />
            </div>
          </div>
          <div className="lg:order-1">
            <div className="mb-4">
              <h2 className="text-xl font-semibold">チャットで編集</h2>
            </div>
            <div className="h-[700px]">
              <ArticleChatEditor article={article} onArticleUpdate={handleArticleUpdate} />
            </div>
          </div>
        </div>
      ) : (
        <ArticlePreview article={article} onStartChat={handleChatStart} />
      )}
    </div>
  );
}
