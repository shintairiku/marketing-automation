'use client';

import { motion } from 'framer-motion';
import { Brain, FileText, Sparkles } from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { CompletedSection, SectionsProgress } from '@/types/article-generation';

import BatchSectionProgress from './BatchSectionProgress';

interface ContentGenerationProps {
  currentStep: string;
  generatedContent?: string;
  outline?: any;
  progress: number;
  completedSections?: CompletedSection[];
  sectionsProgress?: SectionsProgress;
  showBatchProgress?: boolean;
}

export default function ContentGeneration({ 
  currentStep, 
  generatedContent, 
  outline,
  progress,
  completedSections = [],
  sectionsProgress,
  showBatchProgress = false
}: ContentGenerationProps) {
  const getStepIcon = (step: string) => {
    switch (step) {
      case 'outline_generation':
        return <FileText className="w-5 h-5" />;
      case 'content_writing':
        return <Brain className="w-5 h-5" />;
      case 'editing':
        return <Sparkles className="w-5 h-5" />;
      default:
        return <FileText className="w-5 h-5" />;
    }
  };

  const getStepTitle = (step: string) => {
    switch (step) {
      case 'outline_generation':
        return 'アウトライン生成中...';
      case 'content_writing':
        return '記事本文を執筆中...';
      case 'editing':
        return '最終編集・校正中...';
      default:
        return '処理中...';
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="w-full max-w-6xl mx-auto space-y-6"
    >
      {/* プログレスヘッダー */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            {getStepIcon(currentStep)}
            {getStepTitle(currentStep)}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Progress value={progress} className="w-full" />
          <p className="text-sm text-gray-600 mt-2">
            {progress}% 完了
          </p>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* アウトライン表示 or バッチ進捗表示 */}
        {showBatchProgress && currentStep === 'writing_sections' && outline?.sections ? (
          <BatchSectionProgress
            completedSections={completedSections}
            sectionsProgress={sectionsProgress}
            totalSections={outline.sections.length}
            isActive={currentStep === 'writing_sections'}
          />
        ) : outline ? (
          <Card className="h-fit">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FileText className="w-5 h-5 text-blue-500" />
                アウトライン
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <h3 className="font-medium text-lg">{outline.title}</h3>
                <Badge variant="outline">{outline.suggested_tone}</Badge>
                <Separator />
                <ScrollArea className="h-64">
                  <div className="space-y-2">
                    {outline.sections?.map((section: any, index: number) => (
                      <div key={index} className="pl-2 border-l-2 border-gray-200">
                        <h4 className="font-medium text-sm">{section.heading}</h4>
                        {section.estimated_chars && (
                          <p className="text-xs text-gray-500">
                            約 {section.estimated_chars} 文字
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                </ScrollArea>
              </div>
            </CardContent>
          </Card>
        ) : null}

        {/* 生成中コンテンツ */}
        <Card className="h-fit">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Brain className="w-5 h-5 text-green-500" />
              生成中の記事
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-96">
              {generatedContent ? (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="prose prose-sm max-w-none"
                  dangerouslySetInnerHTML={{ __html: generatedContent }}
                />
              ) : (
                <div className="flex items-center justify-center h-full text-gray-500">
                  <motion.div
                    animate={{ opacity: [0.5, 1, 0.5] }}
                    transition={{ duration: 1.5, repeat: Infinity }}
                    className="text-center"
                  >
                    <Brain className="w-8 h-8 mx-auto mb-2" />
                    <p>記事を生成中です...</p>
                  </motion.div>
                </div>
              )}
            </ScrollArea>
          </CardContent>
        </Card>
      </div>
    </motion.div>
  );
}