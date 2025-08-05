'use client';

import { motion } from 'framer-motion';
import { CheckCircle, Clock, FileText, Sparkles } from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { ScrollArea } from '@/components/ui/scroll-area';
import { CompletedSection, SectionsProgress } from '@/types/article-generation';

interface BatchSectionProgressProps {
  completedSections: CompletedSection[];
  sectionsProgress?: SectionsProgress;
  totalSections: number;
  isActive: boolean;
}

export default function BatchSectionProgress({
  completedSections,
  sectionsProgress,
  totalSections,
  isActive
}: BatchSectionProgressProps) {
  const completedCount = completedSections.length;
  const progressPercentage = totalSections > 0 ? (completedCount / totalSections) * 100 : 0;
  
  const getSectionStatus = (index: number) => {
    if (completedSections.some(section => section.index === index + 1)) {
      return 'completed';
    }
    if (sectionsProgress && sectionsProgress.currentSection === index + 1) {
      return 'in_progress';
    }
    return 'pending';
  };

  const getSectionIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'in_progress':
        return <Sparkles className="w-4 h-4 text-blue-500 animate-pulse" />;
      default:
        return <Clock className="w-4 h-4 text-gray-400" />;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'completed':
        return <Badge className="bg-green-100 text-green-800 border-green-200">完了</Badge>;
      case 'in_progress':
        return <Badge className="bg-blue-100 text-blue-800 border-blue-200">執筆中</Badge>;
      default:
        return <Badge variant="outline" className="text-gray-500">待機中</Badge>;
    }
  };

  const getCompletedSection = (index: number) => {
    return completedSections.find(section => section.index === index + 1);
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="w-full"
    >
      <Card className="h-fit">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="w-5 h-5 text-blue-500" />
            セクション進捗 (バッチ処理)
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Overall Progress */}
          <div className="space-y-2">
            <div className="flex justify-between items-center">
              <span className="text-sm font-medium">全体進捗</span>
              <span className="text-sm text-gray-600">
                {completedCount} / {totalSections} セクション完了
              </span>
            </div>
            <Progress value={progressPercentage} className="w-full" />
            <p className="text-xs text-gray-500 text-center">
              {Math.round(progressPercentage)}% 完了
            </p>
          </div>

          {/* Current Status */}
          {isActive && sectionsProgress && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="bg-blue-50 border border-blue-200 rounded-lg p-3"
            >
              <div className="flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-blue-500 animate-pulse" />
                <span className="text-sm font-medium text-blue-800">
                  現在の作業: {sectionsProgress.sectionHeading}
                </span>
              </div>
              <p className="text-xs text-blue-600 mt-1">
                バッチ処理で高品質なコンテンツを生成中...
              </p>
            </motion.div>
          )}

          {/* Section List */}
          <ScrollArea className="h-64">
            <div className="space-y-2">
              {Array.from({ length: totalSections }, (_, index) => {
                const status = getSectionStatus(index);
                const completedSection = getCompletedSection(index);
                const sectionTitle = completedSection?.heading || 
                  (sectionsProgress?.currentSection === index + 1 ? sectionsProgress.sectionHeading : null) ||
                  `セクション ${index + 1}`;

                return (
                  <motion.div
                    key={index}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: index * 0.1 }}
                    className={`p-3 rounded-lg border transition-all ${
                      status === 'completed' 
                        ? 'bg-green-50 border-green-200' 
                        : status === 'in_progress'
                        ? 'bg-blue-50 border-blue-200'
                        : 'bg-gray-50 border-gray-200'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        {getSectionIcon(status)}
                        <div>
                          <h4 className="font-medium text-sm">{sectionTitle}</h4>
                          {completedSection && (
                            <p className="text-xs text-gray-600">
                              {completedSection.content.length.toLocaleString()}文字 
                              {completedSection.imagePlaceholders && completedSection.imagePlaceholders.length > 0 && (
                                <span className="ml-1">
                                  • {completedSection.imagePlaceholders.length}画像
                                </span>
                              )}
                            </p>
                          )}
                        </div>
                      </div>
                      {getStatusBadge(status)}
                    </div>

                    {/* Show preview of completed content */}
                    {status === 'completed' && completedSection && (
                      <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        className="mt-2 pt-2 border-t border-gray-200"
                      >
                        <div className="text-xs text-gray-600 bg-white rounded p-2 max-h-16 overflow-hidden">
                          {completedSection.content.replace(/<[^>]*>/g, '').slice(0, 100)}
                          {completedSection.content.length > 100 && '...'}
                        </div>
                      </motion.div>
                    )}
                  </motion.div>
                );
              })}
            </div>
          </ScrollArea>

          {/* Batch Processing Info */}
          <div className="bg-gray-50 rounded-lg p-3">
            <div className="flex items-center gap-2 mb-1">
              <Sparkles className="w-4 h-4 text-purple-500" />
              <span className="text-sm font-medium text-gray-800">バッチ処理の特長</span>
            </div>
            <ul className="text-xs text-gray-600 space-y-1">
              <li>• 各セクションを一度に完全生成</li>
              <li>• より一貫性のある高品質なコンテンツ</li>
              <li>• 効率的な処理によるスピード向上</li>
            </ul>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}