'use client';

import { useState, useEffect, memo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Brain, 
  FileText, 
  Users, 
  Lightbulb, 
  Search, 
  BookOpen,
  Edit3,
  Check,
  Clock,
  AlertCircle,
  Play,
  Pause,
  RotateCcw,
  Eye,
  Download,
  Sparkles,
  Zap,
  Target,
  TrendingUp,
  PenTool
} from 'lucide-react';
import { GenerationStep } from '../hooks/useArticleGeneration';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';

interface CompactGenerationFlowProps {
  steps: GenerationStep[];
  currentStep: string;
  isConnected: boolean;
  isGenerating: boolean;
  onPause?: () => void;
  onResume?: () => void;
  onCancel?: () => void;
  progressPercentage: number;
  finalArticle?: {
    title: string;
    content: string;
  };
  currentMessage?: string;
}

const stepIcons = {
  keyword_analysis: Target,
  persona_generation: Users,
  theme_generation: Lightbulb,
  research_planning: Search,
  research_execution: TrendingUp,
  outline_generation: BookOpen,
  content_writing: PenTool,
  editing: Edit3,
};

const stepColors = {
  pending: 'bg-gray-100 text-gray-500',
  in_progress: 'bg-blue-100 text-blue-600 border-blue-300',
  completed: 'bg-green-100 text-green-600 border-green-300',
  error: 'bg-red-100 text-red-600 border-red-300',
};

export default memo(function CompactGenerationFlow({
  steps,
  currentStep,
  isConnected,
  isGenerating,
  onPause,
  onResume,
  onCancel,
  progressPercentage,
  finalArticle,
  currentMessage
}: CompactGenerationFlowProps) {
  const [isPreviewOpen, setIsPreviewOpen] = useState(false);
  const [isPaused, setIsPaused] = useState(false);

  const handlePause = () => {
    setIsPaused(!isPaused);
    if (isPaused) {
      onResume?.();
    } else {
      onPause?.();
    }
  };

  const currentStepData = steps.find(step => step.status === 'in_progress');
  const completedSteps = steps.filter(step => step.status === 'completed').length;

  return (
    <Card className="w-full max-w-5xl mx-auto overflow-hidden bg-gradient-to-br from-white to-blue-50/30 border-2 border-primary/10 shadow-xl">
      <CardContent className="p-0">
        {/* Header Section */}
        <div className="bg-gradient-to-r from-primary/5 to-secondary/5 p-6 border-b border-primary/10">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <motion.div
                animate={isGenerating ? { rotate: 360 } : {}}
                transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                className="w-10 h-10 bg-gradient-to-r from-primary to-secondary rounded-full flex items-center justify-center"
              >
                <Brain className="w-5 h-5 text-white" />
              </motion.div>
              <div>
                <h2 className="text-xl font-bold text-foreground">AI記事生成中</h2>
                <p className="text-sm text-muted-foreground">
                  {isConnected ? 'サーバー接続中' : '接続待機中'}
                </p>
              </div>
            </div>
            
            <div className="flex items-center gap-2">
              <Badge variant={isConnected ? "default" : "destructive"}>
                {isConnected ? '接続済み' : '未接続'}
              </Badge>
              {isGenerating && (
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handlePause}
                    className="flex items-center gap-2"
                  >
                    {isPaused ? <Play className="w-4 h-4" /> : <Pause className="w-4 h-4" />}
                    {isPaused ? '再開' : '一時停止'}
                  </Button>
                  <Button
                    variant="destructive"
                    size="sm"
                    onClick={onCancel}
                    className="flex items-center gap-2"
                  >
                    <RotateCcw className="w-4 h-4" />
                    中止
                  </Button>
                </div>
              )}
            </div>
          </div>

          {/* Progress Bar */}
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">進捗状況</span>
              <span className="font-medium text-foreground">{progressPercentage}%</span>
            </div>
            <Progress value={progressPercentage} className="h-3" />
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>{completedSteps}/{steps.length} ステップ完了</span>
              <span>推定残り時間: 3-5分</span>
            </div>
          </div>
        </div>

        {/* Steps Grid */}
        <div className="p-6">
          <div className="grid grid-cols-4 gap-4 mb-6">
            {steps.map((step, index) => {
              const Icon = stepIcons[step.id as keyof typeof stepIcons] || FileText;
              const isActive = step.status === 'in_progress';
              
              return (
                <motion.div
                  key={step.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.1 }}
                  className={`
                    relative p-4 rounded-xl border-2 transition-all duration-300
                    ${stepColors[step.status]}
                    ${isActive ? 'ring-4 ring-blue-200 shadow-lg scale-105' : ''}
                  `}
                >
                  <div className="flex flex-col items-center text-center space-y-2">
                    <div className={`
                      w-12 h-12 rounded-full flex items-center justify-center
                      ${step.status === 'completed' ? 'bg-green-500 text-white' :
                        step.status === 'in_progress' ? 'bg-blue-500 text-white' :
                        step.status === 'error' ? 'bg-red-500 text-white' :
                        'bg-gray-300 text-gray-600'}
                    `}>
                      {step.status === 'completed' ? (
                        <Check className="w-6 h-6" />
                      ) : step.status === 'in_progress' ? (
                        <motion.div
                          animate={{ rotate: 360 }}
                          transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                        >
                          <Icon className="w-6 h-6" />
                        </motion.div>
                      ) : step.status === 'error' ? (
                        <AlertCircle className="w-6 h-6" />
                      ) : (
                        <Icon className="w-6 h-6" />
                      )}
                    </div>
                    
                    <h3 className="font-medium text-sm leading-tight">
                      {step.title}
                    </h3>
                    
                    {step.status === 'in_progress' && (
                      <motion.div
                        animate={{ opacity: [0.5, 1, 0.5] }}
                        transition={{ duration: 1.5, repeat: Infinity }}
                        className="w-2 h-2 bg-blue-500 rounded-full"
                      />
                    )}
                  </div>
                  
                  {/* Step number */}
                  <div className="absolute -top-2 -left-2 w-6 h-6 bg-white border-2 border-primary/20 rounded-full flex items-center justify-center text-xs font-bold text-primary">
                    {index + 1}
                  </div>
                </motion.div>
              );
            })}
          </div>

          {/* Current Activity */}
          <AnimatePresence>
            {currentMessage && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                className="mb-6"
              >
                <Card className="border-2 border-primary/20 bg-gradient-to-r from-blue-50 to-purple-50">
                  <CardContent className="p-4">
                    <div className="flex items-center gap-3">
                      <motion.div
                        animate={{ rotate: 360 }}
                        transition={{ duration: 3, repeat: Infinity, ease: "linear" }}
                      >
                        <Sparkles className="w-5 h-5 text-primary" />
                      </motion.div>
                      <div className="flex-1">
                        <p className="text-sm font-medium text-primary mb-1">現在の処理</p>
                        <p className="text-foreground">{currentMessage}</p>
                      </div>
                      <motion.div
                        animate={{ scale: [1, 1.2, 1] }}
                        transition={{ duration: 1, repeat: Infinity }}
                      >
                        <Zap className="w-5 h-5 text-yellow-500" />
                      </motion.div>
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Result Preview */}
          <AnimatePresence>
            {finalArticle && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="space-y-4"
              >
                <div className="flex items-center justify-between">
                  <h3 className="text-lg font-semibold flex items-center gap-2">
                    <Check className="w-5 h-5 text-green-500" />
                    生成完了
                  </h3>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      onClick={() => setIsPreviewOpen(true)}
                      className="flex items-center gap-2"
                    >
                      <Eye className="w-4 h-4" />
                      プレビュー
                    </Button>
                    <Button
                      variant="default"
                      className="flex items-center gap-2"
                    >
                      <Download className="w-4 h-4" />
                      ダウンロード
                    </Button>
                  </div>
                </div>
                
                <Card className="border-2 border-green-200 bg-green-50/30">
                  <CardContent className="p-4">
                    <h4 className="font-semibold text-lg mb-2 text-green-800">
                      {finalArticle.title}
                    </h4>
                    <div 
                      className="prose prose-sm max-w-none text-gray-700 line-clamp-3"
                      dangerouslySetInnerHTML={{ 
                        __html: finalArticle.content.substring(0, 200) + '...' 
                      }}
                    />
                  </CardContent>
                </Card>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </CardContent>

      {/* Preview Modal */}
      <AnimatePresence>
        {isPreviewOpen && finalArticle && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50"
            onClick={() => setIsPreviewOpen(false)}
          >
            <motion.div
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.8, opacity: 0 }}
              className="bg-white rounded-lg max-w-4xl max-h-[90vh] overflow-hidden shadow-2xl"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="bg-gradient-to-r from-primary to-secondary text-white p-4 flex items-center justify-between">
                <h3 className="text-lg font-semibold">記事プレビュー</h3>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setIsPreviewOpen(false)}
                  className="text-white hover:bg-white/20"
                >
                  ✕
                </Button>
              </div>
              <div className="p-6 overflow-y-auto max-h-[calc(90vh-120px)]">
                <h1 className="text-2xl font-bold mb-6 text-foreground">
                  {finalArticle.title}
                </h1>
                <div 
                  className="prose prose-lg max-w-none"
                  dangerouslySetInnerHTML={{ __html: finalArticle.content }}
                />
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </Card>
  );
}); 