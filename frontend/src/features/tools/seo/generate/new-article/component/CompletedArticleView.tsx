'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import { 
  AlertCircle,
  CheckCircle,
  Code, 
  Copy, 
  Download, 
  Eye, 
  RefreshCw, 
  Share2} from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

import ArticlePreviewStyles from './ArticlePreviewStyles';

interface CompletedArticleViewProps {
  article: {
    title: string;
    content: string;
  };
  onExport: () => void;
  onNewArticle: () => void;
}

export default function CompletedArticleView({ 
  article, 
  onExport, 
  onNewArticle 
}: CompletedArticleViewProps) {
  const [copied, setCopied] = useState(false);
  const [activeTab, setActiveTab] = useState('preview');

  const handleCopyHtml = async () => {
    try {
      if (!article.content) {
        throw new Error('記事内容が空です');
      }
      await navigator.clipboard.writeText(article.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
      // エラー時の処理（必要に応じてユーザーに通知）
    }
  };

  const wordCount = (article.content || '').replace(/<[^>]*>/g, '').length;
  const estimatedReadingTime = Math.max(1, Math.ceil(wordCount / 400));

  // 記事内容が無効な場合のフォールバック
  if (!article || !article.content) {
    console.log('CompletedArticleView: Invalid article data', { article });
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-7xl mx-auto"
      >
        <Card className="bg-gradient-to-r from-red-50 to-pink-50 border-red-200">
          <CardContent className="p-6 text-center">
            <div className="w-12 h-12 bg-red-500 rounded-full flex items-center justify-center mx-auto mb-4">
              <AlertCircle className="w-6 h-6 text-white" />
            </div>
            <h2 className="text-xl font-bold text-gray-900 mb-2">
              記事の表示に問題があります
            </h2>
            <p className="text-gray-600 mb-4">
              記事内容を正しく読み込むことができませんでした
            </p>
            <Button onClick={onNewArticle} className="flex items-center gap-2">
              <RefreshCw className="w-4 h-4" />
              新しい記事を作成
            </Button>
          </CardContent>
        </Card>
      </motion.div>
    );
  }
  
  console.log('CompletedArticleView: Rendering article', { 
    title: article.title, 
    contentLength: article.content?.length 
  });

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="w-full max-w-7xl mx-auto"
    >
      {/* ヘッダー */}
      <motion.div
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="mb-6"
      >
        <Card className="bg-gradient-to-r from-green-50 to-emerald-50 border-green-200">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <motion.div
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  transition={{ delay: 0.4, type: "spring", stiffness: 400 }}
                  className="w-12 h-12 bg-green-500 rounded-full flex items-center justify-center"
                >
                  <CheckCircle className="w-6 h-6 text-white" />
                </motion.div>
                <div>
                  <h1 className="text-2xl font-bold text-gray-900 mb-1">
                    記事生成完了！
                  </h1>
                  <p className="text-gray-600">
                    高品質な記事が正常に生成されました
                  </p>
                </div>
              </div>
              
              <div className="flex items-center gap-3">
                <div className="text-right">
                  <div className="text-sm text-gray-500">統計</div>
                  <div className="text-lg font-semibold text-gray-900">
                    {wordCount.toLocaleString()}文字 / {estimatedReadingTime}分
                  </div>
                </div>
                <Badge className="bg-green-100 text-green-800 border-green-200">
                  完成
                </Badge>
              </div>
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* アクションボタン */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
        className="mb-6 flex justify-center gap-4"
      >
        <Button
          onClick={onExport}
          className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700"
        >
          <Download className="w-4 h-4" />
          HTMLをダウンロード
        </Button>
        <Button
          onClick={handleCopyHtml}
          variant="outline"
          className="flex items-center gap-2"
        >
          {copied ? (
            <>
              <CheckCircle className="w-4 h-4 text-green-600" />
              コピー完了
            </>
          ) : (
            <>
              <Copy className="w-4 h-4" />
              HTMLをコピー
            </>
          )}
        </Button>
        <Button
          onClick={onNewArticle}
          variant="outline"
          className="flex items-center gap-2"
        >
          <RefreshCw className="w-4 h-4" />
          新しい記事を作成
        </Button>
      </motion.div>

      {/* タブ表示 */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.6 }}
      >
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full grid-cols-2 mb-6">
            <TabsTrigger value="preview" className="flex items-center gap-2">
              <Eye className="w-4 h-4" />
              プレビュー
            </TabsTrigger>
            <TabsTrigger value="html" className="flex items-center gap-2">
              <Code className="w-4 h-4" />
              HTMLコード
            </TabsTrigger>
          </TabsList>
          
          <TabsContent value="preview">
            <Card className="overflow-hidden">
              <CardContent className="p-0">
                <div className="bg-gradient-to-r from-gray-50 to-gray-100 p-4 border-b">
                  <h2 className="text-lg font-semibold text-gray-800 flex items-center gap-2">
                    <Eye className="w-5 h-5" />
                    記事プレビュー
                  </h2>
                  <p className="text-sm text-gray-600">実際のWebサイトでの表示イメージ</p>
                </div>
                <div className="p-6 bg-white min-h-screen">
                  <ArticlePreviewStyles isFullscreen={true}>
                    <h1>{article.title}</h1>
                    <div dangerouslySetInnerHTML={{ 
                      __html: article.content || '<p>記事内容がありません</p>' 
                    }} />
                  </ArticlePreviewStyles>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
          
          <TabsContent value="html">
            <Card>
              <CardContent className="p-0">
                <div className="bg-gradient-to-r from-gray-50 to-gray-100 p-4 border-b flex items-center justify-between">
                  <div>
                    <h2 className="text-lg font-semibold text-gray-800 flex items-center gap-2">
                      <Code className="w-5 h-5" />
                      生成されたHTMLコード
                    </h2>
                    <p className="text-sm text-gray-600">そのまま使用可能なHTMLコード</p>
                  </div>
                  <Button
                    onClick={handleCopyHtml}
                    variant="outline"
                    size="sm"
                    className="flex items-center gap-2"
                  >
                    {copied ? (
                      <>
                        <CheckCircle className="w-4 h-4 text-green-600" />
                        コピー完了
                      </>
                    ) : (
                      <>
                        <Copy className="w-4 h-4" />
                        コピー
                      </>
                    )}
                  </Button>
                </div>
                <div className="p-4">
                  <pre className="bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto text-sm">
                    <code>
                      {`<h1>${article.title || 'Untitled'}</h1>\n${article.content || '<p>No content available</p>'}`}
                    </code>
                  </pre>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </motion.div>
    </motion.div>
  );
}