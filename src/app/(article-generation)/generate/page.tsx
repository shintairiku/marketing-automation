'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';

import { Container } from '@/components/container';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog';
import { toast } from '@/components/ui/use-toast';
import { ArticleGenerationForm } from '@/features/article-generation/components/article-generation-form';
import { ArticleOutlineEditor } from '@/features/article-generation/components/article-outline-editor';
import { ArticleOutlineSelector } from '@/features/article-generation/components/article-outline-selector';
import { ArticlePreview } from '@/features/article-generation/components/article-preview';
import { ArticleGenerationFormData, ArticleOutline, ArticleSection, GeneratedArticle } from '@/features/article-generation/types';

// 画面の状態を管理するための列挙型
type GenerationStep = 'form' | 'outline-selection' | 'preview';

export default function GenerateArticlePage() {
  const router = useRouter();
  const [currentStep, setCurrentStep] = useState<GenerationStep>('form');
  const [isLoading, setIsLoading] = useState(false);
  const [generationData, setGenerationData] = useState<ArticleGenerationFormData | null>(null);
  const [outlines, setOutlines] = useState<ArticleOutline[]>([]);
  const [selectedOutline, setSelectedOutline] = useState<ArticleOutline | null>(null);
  const [generatedArticle, setGeneratedArticle] = useState<GeneratedArticle | null>(null);
  const [isEditorOpen, setIsEditorOpen] = useState(false);
  const [editingOutline, setEditingOutline] = useState<ArticleOutline | null>(null);

  // ダミーデータ生成関数
  const generateDummyOutlines = (formData: ArticleGenerationFormData): ArticleOutline[] => {
    // ダミーデータの生成（本番では実際のAIからの応答を使用）
    return [
      {
        id: '1',
        title: `${formData.mainKeywords}の完全ガイド: 初心者から上級者まで`,
        sections: [
          { id: '1-1', level: 'h2', title: `${formData.mainKeywords}とは何か？基本的な解説` },
          { id: '1-2', level: 'h2', title: `${formData.mainKeywords}の主要なメリット` },
          { id: '1-3', level: 'h3', title: '時間効率の向上' },
          { id: '1-4', level: 'h3', title: 'コスト削減のポテンシャル' },
          { id: '1-5', level: 'h2', title: `${formData.mainKeywords}の実践的な活用法` },
          { id: '1-6', level: 'h2', title: '専門家が教える上級テクニック' },
          { id: '1-7', level: 'h2', title: 'まとめ：次のステップと参考リソース' },
        ],
      },
      {
        id: '2',
        title: `${formData.mainKeywords}の最新トレンドと成功事例`,
        sections: [
          { id: '2-1', level: 'h2', title: `${formData.mainKeywords}市場の現状分析` },
          { id: '2-2', level: 'h2', title: '2025年に注目すべき主要トレンド' },
          { id: '2-3', level: 'h2', title: '成功企業の事例研究' },
          { id: '2-4', level: 'h3', title: '事例1: グローバル企業の戦略' },
          { id: '2-5', level: 'h3', title: '事例2: スタートアップの革新的アプローチ' },
          { id: '2-6', level: 'h2', title: `${formData.mainKeywords}導入のステップバイステップガイド` },
          { id: '2-7', level: 'h2', title: '将来の展望と結論' },
        ],
      },
    ];
  };

  const generateDummyArticle = (outline: ArticleOutline): GeneratedArticle => {
    // 記事の中身をダミーデータで生成
    const sectionsWithContent: ArticleSection[] = outline.sections.map((section) => ({
      ...section,
      content: `このセクションでは「${section.title}」について詳しく解説します。\n\nこれは生成AIによって書かれたサンプルコンテンツです。実際の実装では、ここにLLMが生成した高品質なコンテンツが入ります。\n\nこのコンテンツは単なるプレースホルダーであり、実際のプロダクトでは各セクションごとに詳細で情報価値の高いコンテンツが生成されます。`,
    }));

    return {
      id: `article-${Date.now()}`,
      title: outline.title,
      metaDescription: `${outline.title}に関する完全ガイド。この記事では、${outline.sections[0].title}から${
        outline.sections[outline.sections.length - 1].title
      }まで詳しく解説します。`,
      sections: sectionsWithContent,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      status: 'draft',
    };
  };

  // フォーム送信時の処理
  const handleFormSubmit = async (formData: ArticleGenerationFormData) => {
    setIsLoading(true);
    setGenerationData(formData);

    try {
      // 通常はここでAPIを呼び出して構成案を生成
      // 今回はダミーデータを使用
      await new Promise((resolve) => setTimeout(resolve, 2000)); // API呼び出し時間をシミュレート
      const dummyOutlines = generateDummyOutlines(formData);
      setOutlines(dummyOutlines);
      setCurrentStep('outline-selection');
    } catch (error) {
      toast({
        variant: 'destructive',
        description: '記事構成の生成中にエラーが発生しました。もう一度お試しください。',
      });
    } finally {
      setIsLoading(false);
    }
  };

  // 構成案選択時の処理
  const handleOutlineSelect = async (outline: ArticleOutline) => {
    setSelectedOutline(outline);
    setIsLoading(true);

    try {
      // 通常はここでAPIを呼び出して記事本文を生成
      // 今回はダミーデータを使用
      await new Promise((resolve) => setTimeout(resolve, 3000)); // API呼び出し時間をシミュレート
      const dummyArticle = generateDummyArticle(outline);
      setGeneratedArticle(dummyArticle);
      setCurrentStep('preview');
    } catch (error) {
      toast({
        variant: 'destructive',
        description: '記事生成中にエラーが発生しました。もう一度お試しください。',
      });
    } finally {
      setIsLoading(false);
    }
  };

  // 構成案編集モーダルを開く
  const handleOutlineEdit = (outline: ArticleOutline) => {
    setEditingOutline(outline);
    setIsEditorOpen(true);
  };

  // 構成案の保存処理
  const handleOutlineSave = (updatedOutline: ArticleOutline) => {
    setOutlines((prevOutlines) =>
      prevOutlines.map((o) => (o.id === updatedOutline.id ? updatedOutline : o))
    );
    setIsEditorOpen(false);
  };

  // チャット編集画面への遷移
  const handleStartChat = () => {
    if (generatedArticle) {
      // 通常は記事IDをURLパラメータに含めて遷移
      localStorage.setItem('draftArticle', JSON.stringify(generatedArticle));
      router.push('/edit');
    }
  };

  return (
    <Container className="py-10">
      <div className="mx-auto max-w-4xl">
        {currentStep === 'form' && (
          <div className="space-y-6">
            <h1 className="text-2xl font-bold">記事生成</h1>
            <p className="text-gray-400">
              以下のフォームに記事生成に必要な情報を入力してください。AIが最適化された記事構成を提案します。
            </p>
            <div className="rounded-lg border border-gray-700 bg-black p-6">
              <ArticleGenerationForm onSubmit={handleFormSubmit} isLoading={isLoading} />
            </div>
          </div>
        )}

        {currentStep === 'outline-selection' && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h1 className="text-2xl font-bold">記事構成案を選択</h1>
              <Button variant="outline" onClick={() => setCurrentStep('form')}>
                入力内容を修正
              </Button>
            </div>
            <p className="text-gray-400">
              AIが生成した構成案から最適なものを選択してください。また、必要に応じて編集もできます。
            </p>
            <div className="rounded-lg border border-gray-700 bg-black p-6">
              <ArticleOutlineSelector
                outlines={outlines}
                onSelect={handleOutlineSelect}
                onEdit={handleOutlineEdit}
                isLoading={isLoading}
              />
            </div>
          </div>
        )}

        {currentStep === 'preview' && generatedArticle && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h1 className="text-2xl font-bold">生成された記事</h1>
              <div className="flex gap-2">
                <Button variant="outline" onClick={() => setCurrentStep('outline-selection')}>
                  構成を変更
                </Button>
                <Button variant="outline" onClick={() => setCurrentStep('form')}>
                  最初からやり直す
                </Button>
              </div>
            </div>
            <p className="text-gray-400">
              生成された記事プレビューです。このまま保存するか、チャットベースの編集機能で内容を調整できます。
            </p>
            <div className="rounded-lg border border-gray-700 bg-black p-6">
              <ArticlePreview article={generatedArticle} onStartChat={handleStartChat} />
            </div>
          </div>
        )}
      </div>

      <Dialog open={isEditorOpen} onOpenChange={setIsEditorOpen}>
        <DialogContent className="max-w-2xl sm:max-w-[600px]">
          <DialogTitle>記事構成を編集</DialogTitle>
          {editingOutline && (
            <ArticleOutlineEditor
              outline={editingOutline}
              onSave={handleOutlineSave}
              onCancel={() => setIsEditorOpen(false)}
            />
          )}
        </DialogContent>
      </Dialog>
    </Container>
  );
}
