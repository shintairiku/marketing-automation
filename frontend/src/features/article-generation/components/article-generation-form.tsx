'use client';

import { useState } from 'react';
import { IoDocumentText } from 'react-icons/io5';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Textarea } from '@/components/ui/textarea';
import { toast } from '@/components/ui/use-toast';
import { ArticleGenerationFormData } from '@/features/article-generation/types';

interface ArticleGenerationFormProps {
  onSubmit: (formData: ArticleGenerationFormData) => Promise<void>;
  isLoading?: boolean;
}

export function ArticleGenerationForm({ onSubmit, isLoading = false }: ArticleGenerationFormProps) {
  const [activeTab, setActiveTab] = useState('basic');
  const [formData, setFormData] = useState<ArticleGenerationFormData>({
    mainKeywords: '',
    articleTheme: '',
    tone: 'professional',
  });

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>
  ) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    // 基本的な入力バリデーション
    if (!formData.mainKeywords.trim() || !formData.articleTheme.trim()) {
      toast({
        variant: 'destructive',
        description: 'メインキーワードと記事テーマは必須項目です。',
      });
      return;
    }
    
    try {
      await onSubmit(formData);
    } catch (error) {
      toast({
        variant: 'destructive',
        description: '記事生成中にエラーが発生しました。もう一度お試しください。',
      });
    }
  };

  return (
    <form onSubmit={handleSubmit} className="w-full space-y-6">
      <div className="space-y-4">
        <div>
          <label htmlFor="mainKeywords" className="block text-sm font-medium mb-1">
            メインキーワード <span className="text-red-500">*</span>
          </label>
          <Input
            id="mainKeywords"
            name="mainKeywords"
            placeholder="例: SEO対策, コンテンツマーケティング（複数の場合はカンマで区切ってください）"
            value={formData.mainKeywords}
            onChange={handleChange}
            disabled={isLoading}
            required
          />
        </div>

        <div>
          <label htmlFor="articleTheme" className="block text-sm font-medium mb-1">
            記事テーマ・概要 <span className="text-red-500">*</span>
          </label>
          <Textarea
            id="articleTheme"
            name="articleTheme"
            placeholder="記事のテーマや書きたい内容の概要を入力してください"
            rows={4}
            value={formData.articleTheme}
            onChange={handleChange}
            disabled={isLoading}
            required
          />
        </div>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="mt-6">
          <TabsList className="w-full">
            <TabsTrigger value="basic" className="flex-1">基本設定</TabsTrigger>
            <TabsTrigger value="advanced" className="flex-1">詳細設定（オプション）</TabsTrigger>
          </TabsList>
          
          <TabsContent value="basic" className="mt-4 space-y-4">
            <div>
              <label htmlFor="tone" className="block text-sm font-medium mb-1">
                文体
              </label>
              <select
                id="tone"
                name="tone"
                className="flex h-9 w-full rounded-md bg-background px-3 py-1 text-sm transition-colors placeholder:text-muted-foreground disabled:cursor-not-allowed disabled:opacity-50 border border-border"
                value={formData.tone}
                onChange={handleChange}
                disabled={isLoading}
              >
                <option value="formal">フォーマル（丁寧語）</option>
                <option value="professional">プロフェッショナル（専門的）</option>
                <option value="casual">カジュアル（親しみやすい）</option>
                <option value="friendly">フレンドリー（砕けた表現）</option>
              </select>
            </div>
            
            <div>
              <label htmlFor="targetAudience" className="block text-sm font-medium mb-1">
                ターゲット読者層
              </label>
              <Input
                id="targetAudience"
                name="targetAudience"
                placeholder="例: 20代女性、Webマーケティング初心者、経営者など"
                value={formData.targetAudience || ''}
                onChange={handleChange}
                disabled={isLoading}
              />
            </div>
          </TabsContent>
          
          <TabsContent value="advanced" className="mt-4 space-y-4">
            <div>
              <label htmlFor="excludeKeywords" className="block text-sm font-medium mb-1">
                除外キーワード
              </label>
              <Input
                id="excludeKeywords"
                name="excludeKeywords"
                placeholder="記事に含めたくないキーワードをカンマ区切りで入力"
                value={formData.excludeKeywords || ''}
                onChange={handleChange}
                disabled={isLoading}
              />
            </div>
            
            <div>
              <label htmlFor="referenceUrls" className="block text-sm font-medium mb-1">
                参考URL
              </label>
              <Textarea
                id="referenceUrls"
                name="referenceUrls"
                placeholder="参考にしたいWebページのURLを入力してください（1行に1つのURL）"
                rows={3}
                value={formData.referenceUrls || ''}
                onChange={handleChange}
                disabled={isLoading}
              />
            </div>
            
            <div>
              <label htmlFor="companyInfo" className="block text-sm font-medium mb-1">
                会社・サービス情報
              </label>
              <Textarea
                id="companyInfo"
                name="companyInfo"
                placeholder="記事に含めたい自社の情報やサービス詳細があれば入力してください"
                rows={3}
                value={formData.companyInfo || ''}
                onChange={handleChange}
                disabled={isLoading}
              />
            </div>
          </TabsContent>
        </Tabs>
      </div>

      <Button 
        type="submit" 
        className="w-full" 
        disabled={isLoading} 
        variant="sexy"
      >
        <IoDocumentText className="mr-2" size={20} />
        {isLoading ? '記事生成中...' : '記事を生成する'}
      </Button>
    </form>
  );
}
