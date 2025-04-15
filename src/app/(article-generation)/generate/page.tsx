'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { 
  IoArrowBack, 
  IoCheckmarkCircle, 
  IoDocumentText,
  IoHelpCircleOutline, 
  IoInformationCircle,
  IoSparkles
} from 'react-icons/io5';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from '@/components/ui/card';
import { Dialog, DialogContent, DialogTitle } from '@/components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { toast } from '@/components/ui/use-toast';
import { ArticleGenerationForm } from '@/features/article-generation/components/article-generation-form';
import { ArticleOutlineEditor } from '@/features/article-generation/components/article-outline-editor';
import { ArticleOutlineSelector } from '@/features/article-generation/components/article-outline-selector';
import { ArticlePreview } from '@/features/article-generation/components/article-preview';
import { ArticleGenerationFormData, ArticleOutline, ArticleSection, GeneratedArticle } from '@/features/article-generation/types';

// 画面の状態を管理するための列挙型
type GenerationStep = 'form' | 'outline-selection' | 'preview';

export default function ImprovedGenerateArticlePage() {
  const router = useRouter();
  const [currentStep, setCurrentStep] = useState<GenerationStep>('form');
  const [activeTab, setActiveTab] = useState('outline-selection');
  const [isLoading, setIsLoading] = useState(false);
  const [generationData, setGenerationData] = useState<ArticleGenerationFormData | null>(null);
  const [outlines, setOutlines] = useState<ArticleOutline[]>([]);
  const [selectedOutline, setSelectedOutline] = useState<ArticleOutline | null>(null);
  const [generatedArticle, setGeneratedArticle] = useState<GeneratedArticle | null>(null);
  const [isEditorOpen, setIsEditorOpen] = useState(false);
  const [editingOutline, setEditingOutline] = useState<ArticleOutline | null>(null);
  const [showTips, setShowTips] = useState(false);

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
      {
        id: '3',
        title: `初心者のための${formData.mainKeywords}入門：基礎から応用まで`,
        sections: [
          { id: '3-1', level: 'h2', title: `${formData.mainKeywords}を学ぶ前に知っておくべきこと` },
          { id: '3-2', level: 'h2', title: `${formData.mainKeywords}の基本原則と考え方` },
          { id: '3-3', level: 'h2', title: `簡単に始められる${formData.mainKeywords}の実践方法` },
          { id: '3-4', level: 'h3', title: 'ステップ1: 基礎を固める' },
          { id: '3-5', level: 'h3', title: 'ステップ2: 実践的なアプローチ' },
          { id: '3-6', level: 'h2', title: `${formData.mainKeywords}についてよくある質問と回答` },
          { id: '3-7', level: 'h2', title: `${formData.mainKeywords}の次のステップ：中級レベルへ` },
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
      setActiveTab('outline-selection');
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

  // 進捗表示
  const renderProgressIndicator = () => {
    return (
      <div className="mb-6">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center">
            <div className={`flex h-8 w-8 items-center justify-center rounded-full border ${
              currentStep === 'form' ? 'border-indigo-500 bg-indigo-500' : 'border-gray-600 bg-gray-800'
            } text-white`}>
              1
            </div>
            <div className={`h-0.5 w-12 ${
              currentStep === 'form' ? 'bg-gray-600' : 'bg-indigo-500'
            }`}></div>
            <div className={`flex h-8 w-8 items-center justify-center rounded-full border ${
              currentStep === 'outline-selection' ? 'border-indigo-500 bg-indigo-500' : 
                currentStep === 'preview' ? 'border-indigo-500 bg-indigo-500' : 'border-gray-600 bg-gray-800'
            } text-white`}>
              2
            </div>
            <div className={`h-0.5 w-12 ${
              currentStep === 'preview' ? 'bg-indigo-500' : 'bg-gray-600'
            }`}></div>
            <div className={`flex h-8 w-8 items-center justify-center rounded-full border ${
              currentStep === 'preview' ? 'border-indigo-500 bg-indigo-500' : 'border-gray-600 bg-gray-800'
            } text-white`}>
              3
            </div>
          </div>
          <div>
            <Button variant="ghost" size="sm" onClick={() => setShowTips(!showTips)}>
              <IoHelpCircleOutline className="mr-1" size={16} />
              ヒントを{showTips ? '隠す' : '表示'}
            </Button>
          </div>
        </div>
        <div className="flex justify-between text-xs text-gray-400 px-1">
          <span>情報入力</span>
          <span>構成選択</span>
          <span>記事プレビュー</span>
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-6">
      {/* ヘッダー */}
      <div className="flex items-center justify-between">
        <div className="flex items-center">
          <Button 
            variant="ghost" 
            size="sm" 
            onClick={() => router.push('/dashboard')}
            className="mr-3"
          >
            <IoArrowBack size={18} />
          </Button>
          <div>
            <h1 className="text-2xl font-bold">{currentStep === 'form' ? '記事生成' : 
                                                  currentStep === 'outline-selection' ? '記事構成選択' : 
                                                  '記事プレビュー'}</h1>
            <p className="text-sm text-gray-400">
              {currentStep === 'form' ? '記事情報を入力してAIに最適な構成を提案してもらいましょう' : 
                currentStep === 'outline-selection' ? '提案された構成から最適なものを選択するか、編集してください' : 
                '生成された記事をプレビューし、必要に応じて編集できます'}
            </p>
          </div>
        </div>
      </div>

      {/* 進捗インジケーター */}
      {renderProgressIndicator()}

      {/* ヒント表示エリア */}
      {showTips && (
        <Card className="bg-indigo-950/20 border-indigo-800/50">
          <CardContent className="p-4">
            <div className="flex items-start">
              <IoInformationCircle className="text-indigo-400 mt-1 mr-2 flex-shrink-0" size={20} />
              <div>
                <h3 className="font-medium text-indigo-300">
                  {currentStep === 'form' ? '入力のヒント' : 
                  currentStep === 'outline-selection' ? '構成選択のヒント' : 
                  'プレビューのヒント'}
                </h3>
                <p className="text-sm text-indigo-200/70 mt-1">
                  {currentStep === 'form' ? 
                    'できるだけ具体的なキーワードと記事の概要を入力すると、より質の高い構成が生成されます。ターゲット読者層や文体も指定すると、さらに最適化されます。' : 
                  currentStep === 'outline-selection' ? 
                    'AIが提案した構成から最適なものを選びましょう。必要に応じて「編集」ボタンで構成を調整できます。見出しの構造（H2, H3）を適切に設定すると、記事の階層構造が明確になります。' : 
                    'プレビューで記事内容を確認し、「チャットで編集」機能を使うと、AIアシスタントと会話形式で記事を調整できます。特定のセクションの追加説明や文章の調整など、自然言語での指示が可能です。'}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* メインコンテンツエリア */}
      <Card className="bg-zinc-900/50 border-zinc-800">
        {currentStep === 'form' && (
          <CardContent className="p-6">
            <ArticleGenerationForm onSubmit={handleFormSubmit} isLoading={isLoading} />
          </CardContent>
        )}

        {currentStep === 'outline-selection' && (
          <CardContent className="p-0">
            <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
              <TabsList className="w-full rounded-none border-b border-zinc-800">
                <TabsTrigger value="outline-selection" className="flex-1 rounded-none">
                  <IoSparkles className="mr-2" size={16} />
                  提案された構成
                </TabsTrigger>
                <TabsTrigger value="input-review" className="flex-1 rounded-none">
                  <IoDocumentText className="mr-2" size={16} />
                  入力内容確認
                </TabsTrigger>
              </TabsList>
              
              <TabsContent value="outline-selection" className="p-6">
                <ArticleOutlineSelector
                  outlines={outlines}
                  onSelect={handleOutlineSelect}
                  onEdit={handleOutlineEdit}
                  isLoading={isLoading}
                />
              </TabsContent>
              
              <TabsContent value="input-review" className="p-6">
                {generationData && (
                  <div className="space-y-6">
                    <div>
                      <h3 className="text-lg font-semibold mb-2">入力内容確認</h3>
                      <p className="text-gray-400 mb-4">以下の入力情報に基づいて記事構成が生成されました。内容を修正する場合は「入力内容を修正」ボタンをクリックしてください。</p>
                      
                      <div className="space-y-4 rounded-md border border-zinc-800 p-4">
                        <div>
                          <p className="text-sm font-medium text-gray-400">メインキーワード</p>
                          <p className="mt-1">{generationData.mainKeywords}</p>
                        </div>
                        
                        <div>
                          <p className="text-sm font-medium text-gray-400">記事テーマ・概要</p>
                          <p className="mt-1">{generationData.articleTheme}</p>
                        </div>
                        
                        {generationData.targetAudience && (
                          <div>
                            <p className="text-sm font-medium text-gray-400">ターゲット読者層</p>
                            <p className="mt-1">{generationData.targetAudience}</p>
                          </div>
                        )}
                        
                        {generationData.tone && (
                          <div>
                            <p className="text-sm font-medium text-gray-400">文体</p>
                            <p className="mt-1">
                              {generationData.tone === 'formal' ? 'フォーマル（丁寧語）' :
                               generationData.tone === 'professional' ? 'プロフェッショナル（専門的）' :
                               generationData.tone === 'casual' ? 'カジュアル（親しみやすい）' : 'フレンドリー（砕けた表現）'}
                            </p>
                          </div>
                        )}
                      </div>
                    </div>
                    
                    <div className="flex justify-end">
                      <Button 
                        variant="outline" 
                        onClick={() => setCurrentStep('form')}
                      >
                        入力内容を修正
                      </Button>
                    </div>
                  </div>
                )}
              </TabsContent>
            </Tabs>
          </CardContent>
        )}

        {currentStep === 'preview' && generatedArticle && (
          <CardContent className="p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-semibold">生成された記事</h2>
              <div className="flex gap-2">
                <Button 
                  variant="outline" 
                  onClick={() => setCurrentStep('outline-selection')}
                >
                  構成を変更
                </Button>
                <Button 
                  variant="ghost" 
                  onClick={() => setCurrentStep('form')}
                >
                  最初からやり直す
                </Button>
              </div>
            </div>
            
            <div className="flex items-center justify-center rounded-md border border-green-500/20 bg-green-900/10 p-3 mb-6">
              <IoCheckmarkCircle className="text-green-500 mr-2" size={20} />
              <p className="text-green-300">記事が正常に生成されました！内容を確認し、必要に応じて編集できます。</p>
            </div>
            
            <ArticlePreview article={generatedArticle} onStartChat={handleStartChat} />
            
            <div className="mt-6 flex justify-end">
              <Button variant="sexy" onClick={handleStartChat}>
                チャットで編集を開始
              </Button>
            </div>
          </CardContent>
        )}
      </Card>

      {/* 構成編集モーダル */}
      <Dialog open={isEditorOpen} onOpenChange={setIsEditorOpen}>
        <DialogContent className="max-w-2xl">
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
    </div>
  );
}