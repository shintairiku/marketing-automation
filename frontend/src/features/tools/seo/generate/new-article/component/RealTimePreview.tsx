'use client';

import { useState, useEffect, useRef, memo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Eye, 
  EyeOff, 
  Maximize2, 
  Minimize2, 
  FileText, 
  Clock, 
  TrendingUp,
  BarChart3,
  Target,
  Sparkles
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import ArticlePreviewStyles from './ArticlePreviewStyles';

interface RealTimePreviewProps {
  isVisible: boolean;
  onToggle: () => void;
  generatedContent?: string;
  currentSection?: {
    index: number;
    heading: string;
    content: string;
  };
  outline?: any;
  isGenerating: boolean;
  currentStep?: string;
}

export default memo(function RealTimePreview({
  isVisible,
  onToggle,
  generatedContent = '',
  currentSection,
  outline,
  isGenerating,
  currentStep
}: RealTimePreviewProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [wordCount, setWordCount] = useState(0);
  const [estimatedReadingTime, setEstimatedReadingTime] = useState(0);
  const previewRef = useRef<HTMLDivElement>(null);

  // 文字数と読了時間を計算
  useEffect(() => {
    if (generatedContent) {
      const text = generatedContent.replace(/<[^>]*>/g, ''); // HTMLタグを除去
      const words = text.length;
      setWordCount(words);
      setEstimatedReadingTime(Math.ceil(words / 400)); // 日本語の読了速度を400文字/分と仮定
    }
  }, [generatedContent]);

  // 新しいコンテンツが追加されたらスクロール
  useEffect(() => {
    if (previewRef.current && currentSection) {
      previewRef.current.scrollTop = previewRef.current.scrollHeight;
    }
  }, [currentSection]);

  if (!isVisible) {
    return (
      <motion.div
        initial={{ x: 300 }}
        animate={{ x: 0 }}
        className="fixed right-4 top-1/2 transform -translate-y-1/2 z-40"
      >
        <Button
          onClick={onToggle}
          variant="default"
          size="lg"
          className="rounded-full shadow-lg bg-gradient-to-r from-primary to-secondary hover:shadow-xl"
        >
          <Eye className="w-5 h-5 mr-2" />
          プレビュー表示
        </Button>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, x: 400 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 400 }}
      className={`
        fixed right-4 top-4 z-40 
        ${isExpanded 
          ? 'inset-4 max-w-none' 
          : 'w-96 max-h-[calc(100vh-2rem)]'
        }
      `}
    >
      <Card className="h-full flex flex-col bg-white/95 backdrop-blur-lg border-2 border-primary/20 shadow-2xl">
        <CardHeader className="bg-gradient-to-r from-primary/5 to-secondary/5 border-b border-primary/10 flex-shrink-0">
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <div className="w-8 h-8 bg-gradient-to-r from-primary to-secondary rounded-full flex items-center justify-center">
                {isGenerating ? (
                  <motion.div
                    animate={{ rotate: 360 }}
                    transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                  >
                    <Sparkles className="w-4 h-4 text-white" />
                  </motion.div>
                ) : (
                  <FileText className="w-4 h-4 text-white" />
                )}
              </div>
              <span className="text-lg font-bold">リアルタイムプレビュー</span>
            </CardTitle>
            
            <div className="flex gap-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setIsExpanded(!isExpanded)}
                className="p-2"
              >
                {isExpanded ? (
                  <Minimize2 className="w-4 h-4" />
                ) : (
                  <Maximize2 className="w-4 h-4" />
                )}
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={onToggle}
                className="p-2"
              >
                <EyeOff className="w-4 h-4" />
              </Button>
            </div>
          </div>
          
          {/* 統計情報 */}
          <div className="flex flex-wrap gap-2 mt-3">
            <Badge variant="outline" className="flex items-center gap-1">
              <FileText className="w-3 h-3" />
              {wordCount}文字
            </Badge>
            <Badge variant="outline" className="flex items-center gap-1">
              <Clock className="w-3 h-3" />
              約{estimatedReadingTime}分
            </Badge>
            {currentSection && (
              <Badge variant="outline" className="flex items-center gap-1">
                <Target className="w-3 h-3" />
                セクション {currentSection.index + 1}
              </Badge>
            )}
          </div>
        </CardHeader>

        <CardContent className="flex-1 p-0 overflow-hidden">
          <Tabs defaultValue="content" className="h-full flex flex-col">
            <TabsList className="grid w-full grid-cols-2 m-4 mb-0">
              <TabsTrigger value="content">記事内容</TabsTrigger>
              <TabsTrigger value="outline">構成</TabsTrigger>
            </TabsList>
            
            <TabsContent value="content" className="flex-1 m-4 mt-2 overflow-hidden">
              <div 
                ref={previewRef}
                className="h-full overflow-y-auto p-4 bg-white rounded-lg border"
              >
                {generatedContent ? (
                  <ArticlePreviewStyles>
                    <div
                      dangerouslySetInnerHTML={{ __html: generatedContent }}
                      className="animate-in fade-in duration-500"
                    />
                  </ArticlePreviewStyles>
                ) : (
                  <div className="flex flex-col items-center justify-center h-full text-center text-muted-foreground">
                    <FileText className="w-12 h-12 mb-4 opacity-50" />
                    <p className="text-sm">記事生成が開始されるとここにプレビューが表示されます</p>
                  </div>
                )}
                
                {/* 現在生成中のセクション */}
                <AnimatePresence>
                  {isGenerating && currentSection && (
                    <motion.div
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -20 }}
                      className="mt-6 p-4 bg-blue-50 border-l-4 border-blue-400 rounded-r-lg"
                    >
                      <div className="flex items-center gap-2 mb-2">
                        <motion.div
                          animate={{ rotate: 360 }}
                          transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                        >
                          <Sparkles className="w-4 h-4 text-blue-600" />
                        </motion.div>
                        <span className="text-sm font-medium text-blue-800">
                          生成中: {currentSection.heading}
                        </span>
                      </div>
                      {currentSection.content && (
                        <div className="text-sm text-blue-700">
                          {currentSection.content}
                        </div>
                      )}
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            </TabsContent>
            
            <TabsContent value="outline" className="flex-1 m-4 mt-2 overflow-hidden">
              <div className="h-full overflow-y-auto p-4 bg-white rounded-lg border">
                {outline ? (
                  <div className="space-y-4">
                    <div className="pb-4 border-b">
                      <h3 className="font-semibold text-lg mb-2">{outline.title}</h3>
                      <p className="text-sm text-muted-foreground">{outline.description}</p>
                    </div>
                    
                    {outline.sections?.map((section: any, index: number) => (
                      <motion.div
                        key={index}
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: index * 0.1 }}
                        className={`
                          p-3 rounded-lg border-l-4 transition-all
                          ${currentSection?.index === index 
                            ? 'bg-blue-50 border-blue-400' 
                            : 'bg-gray-50 border-gray-300'
                          }
                        `}
                      >
                        <div className="flex items-start gap-3">
                          <Badge variant="outline" className="mt-1">
                            {index + 1}
                          </Badge>
                          <div className="flex-1">
                            <h4 className="font-medium mb-1">{section.heading}</h4>
                            <p className="text-sm text-muted-foreground">
                              {section.description}
                            </p>
                          </div>
                          {currentSection?.index === index && (
                            <motion.div
                              animate={{ scale: [1, 1.2, 1] }}
                              transition={{ duration: 1, repeat: Infinity }}
                              className="w-2 h-2 bg-blue-500 rounded-full mt-2"
                            />
                          )}
                        </div>
                      </motion.div>
                    ))}
                  </div>
                ) : (
                  <div className="flex flex-col items-center justify-center h-full text-center text-muted-foreground">
                    <BarChart3 className="w-12 h-12 mb-4 opacity-50" />
                    <p className="text-sm">アウトライン生成後にここに構成が表示されます</p>
                  </div>
                )}
              </div>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
    </motion.div>
  );
}); 