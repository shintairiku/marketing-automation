'use client';

import { memo,useEffect, useState } from 'react';
import { AnimatePresence,motion } from 'framer-motion';
import { 
  AlertCircle,
  BookOpen,
  Brain, 
  Check,
  Clock,
  Download,
  Edit3,
  ExternalLink,
  Eye,
  FileText, 
  Image,
  Lightbulb, 
  PenTool,
  Search, 
  Sparkles,
  Target,
  TrendingUp,
  Users, 
  Zap} from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { GenerationStep, ObservabilityState } from '@/types/article-generation';

import ArticlePreviewStyles from './ArticlePreviewStyles';
import CompletedArticleView from './CompletedArticleView';

interface CompactGenerationFlowProps {
  steps: GenerationStep[];
  currentStep: string;
  isConnected: boolean;
  isGenerating: boolean;
  progressPercentage: number;
  isWaitingForInput?: boolean;
  status?: string;
  finalArticle?: {
    title: string;
    content: string;
  };
  currentMessage?: string;
  generatedContent?: string;
  currentSection?: {
    index: number;
    heading: string;
    content: string;
  };
  outline?: any;
  researchProgress?: {
    currentQuery: number;
    totalQueries: number;
    query: string;
  };
  sectionsProgress?: {
    currentSection: number;
    totalSections: number;
    sectionHeading: string;
  };
  imageMode?: boolean;
  imagePlaceholders?: Array<{
    placeholder_id: string;
    description_jp: string;
    prompt_en: string;
    alt_text: string;
  }>;
  completedSections?: Array<{
    index: number;
    heading: string;
    content: string;
    imagePlaceholders?: Array<{
      placeholder_id: string;
      description_jp: string;
      prompt_en: string;
      alt_text: string;
    }>;
  }>;
  observability?: ObservabilityState;
}

const stepIcons = {
  keyword_analyzing: Target,
  persona_generating: Users,
  theme_generating: Lightbulb,
  research_planning: Search,
  researching: TrendingUp,
  outline_generating: BookOpen,
  writing_sections: PenTool,
  editing: Edit3,
};

const stepColors: Record<string, string> = {
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
  progressPercentage,
  isWaitingForInput,
  status,
  finalArticle,
  currentMessage,
  generatedContent,
  currentSection,
  outline,
  researchProgress,
  sectionsProgress,
  imageMode,
  imagePlaceholders,
  completedSections,
  observability,
}: CompactGenerationFlowProps) {
  const [showCompletionAnimation, setShowCompletionAnimation] = useState(false);
  const [hideProcessCards, setHideProcessCards] = useState(false);
  const weaveTraceUrl = observability?.weave?.traceUrl || observability?.weave?.projectUrl;
  const weaveTraceId = observability?.weave?.traceId;

  // プレビュー表示が必要かどうかを判定
  const shouldShowPreview = currentStep === 'writing_sections' || currentStep === 'editing' || currentStep === 'completed';
  
  // 完了アニメーションのトリガー
  useEffect(() => {
    console.log('CompactGenerationFlow: checking completion animation trigger', { 
      currentStep, 
      progressPercentage, 
      finalArticle: !!finalArticle,
      showCompletionAnimation,
      hideProcessCards 
    });
    
    // 実際に完了している場合のみアニメーションを表示
    if (currentStep === 'completed' && finalArticle && progressPercentage === 100) {
      console.log('CompactGenerationFlow: Starting completion animation');
      setShowCompletionAnimation(true);
      // 2秒後に完了アニメーションを隠し、すぐにプロセスカードも隠して記事を表示
      const timer = setTimeout(() => {
        console.log('CompactGenerationFlow: Hiding completion animation and process cards');
        setShowCompletionAnimation(false);
        setHideProcessCards(true);
      }, 2000);
      
      // クリーンアップ関数でタイマーをクリア
      return () => clearTimeout(timer);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentStep, progressPercentage, finalArticle]);
  
  // リセット機能（新しい記事生成時）
  useEffect(() => {
    if (currentStep === 'keyword_analyzing') {
      console.log('CompactGenerationFlow: Resetting animation states');
      setShowCompletionAnimation(false);
      setHideProcessCards(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentStep]);
  
  // finalArticleが存在する場合、即座にプロセスカードを隠す（アニメーション無しで）
  useEffect(() => {
    if (finalArticle && currentStep === 'completed' && !showCompletionAnimation) {
      console.log('CompactGenerationFlow: Immediately hiding process cards');
      setHideProcessCards(true);
    }
  }, [finalArticle, currentStep, showCompletionAnimation]);
  
  // 文字数と読了時間を計算
  const [wordCount, setWordCount] = useState(0);
  const [estimatedReadingTime, setEstimatedReadingTime] = useState(0);

  useEffect(() => {
    if (generatedContent) {
      const text = generatedContent.replace(/<[^>]*>/g, ''); // HTMLタグを除去
      const words = text.length;
      setWordCount(words);
      setEstimatedReadingTime(Math.ceil(words / 400)); // 日本語の読了速度を400文字/分と仮定
    }
  }, [generatedContent]);

  return (
    <div className="w-full max-w-6xl mx-auto space-y-4">
      {/* Compact Header Section */}
      <Card className="bg-gradient-to-r from-blue-50 via-purple-50 to-pink-50 border-blue-200 shadow-lg">
        <CardContent className="p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-3">
              <motion.div
                animate={isGenerating ? { 
                  rotate: 360,
                  scale: [1, 1.1, 1] 
                } : {}}
                transition={{ 
                  rotate: { duration: 3, repeat: Infinity, ease: "linear" },
                  scale: { duration: 2, repeat: Infinity }
                }}
                className="w-12 h-12 bg-gradient-to-br from-blue-500 via-purple-500 to-pink-500 rounded-full flex items-center justify-center shadow-lg"
              >
                <Brain className="w-6 h-6 text-white" />
              </motion.div>
              <div>
                <h2 className="text-lg font-bold text-foreground flex items-center gap-2">
                  AI記事生成
                  <motion.div
                    animate={{ opacity: [0.5, 1, 0.5] }}
                    transition={{ duration: 1.5, repeat: Infinity }}
                  >
                    <Zap className="w-4 h-4 text-yellow-500" />
                  </motion.div>
                  {/* 画像モード表示バッジ */}
                  {imageMode && (
                    <motion.div
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      transition={{ type: "spring", stiffness: 400, damping: 17 }}
                    >
                      <Badge className="bg-purple-100 text-purple-800 border-purple-200 shadow-sm">
                        {/* eslint-disable-next-line jsx-a11y/alt-text */}
                        <Image className="w-3 h-3 mr-1" aria-hidden="true" />
                        画像モード
                      </Badge>
                    </motion.div>
                  )}
                </h2>
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  {/* 接続状態表示を削除 */}
                  {/* 画像プレースホルダー数表示 */}
                  {imageMode && imagePlaceholders && imagePlaceholders.length > 0 && (
                    <div className="text-xs text-purple-600 bg-purple-50 px-2 py-0.5 rounded-full">
                      📸 {imagePlaceholders.length} 個のプレースホルダー
                    </div>
                  )}
                </div>
              </div>
            </div>
            
          </div>
          { (weaveTraceUrl || weaveTraceId) && (
            <div className="flex items-center gap-2">
              {weaveTraceId && (
                <Badge variant="outline" className="font-mono text-[11px]">
                  Trace {weaveTraceId.slice(0, 8)}
                </Badge>
              )}
              {weaveTraceUrl && (
                <Button variant="outline" size="sm" asChild>
                  <a href={weaveTraceUrl} target="_blank" rel="noreferrer">
                    <ExternalLink className="w-3.5 h-3.5 mr-1" />
                    Weave Trace
                  </a>
                </Button>
              )}
            </div>
          )}

          {/* Compact Progress Section */}
          <div className="space-y-2">
            <div className="flex justify-between items-center">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-foreground">{progressPercentage}%</span>
                <span className="text-xs text-muted-foreground">完了</span>
              </div>
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <Clock className="w-3 h-3" />
                <span>{isGenerating ? `残り ${Math.max(1, Math.round((100 - progressPercentage) / 20))}-${Math.max(2, Math.round((100 - progressPercentage) / 15))}分` : '完了'}</span>
              </div>
            </div>
            <div className="relative">
              <Progress value={progressPercentage} className="h-2" />
              <motion.div
                className="absolute top-0 left-0 h-2 bg-gradient-to-r from-blue-500 to-purple-500 rounded-full"
                style={{ width: `${progressPercentage}%` }}
                animate={{ 
                  boxShadow: [
                    '0 0 0 rgba(59, 130, 246, 0.5)',
                    '0 0 20px rgba(59, 130, 246, 0.8)',
                    '0 0 0 rgba(59, 130, 246, 0.5)'
                  ]
                }}
                transition={{ duration: 2, repeat: Infinity }}
              />
            </div>
          </div>

          {/* Current Activity - Compact */}
          <AnimatePresence>
            {currentMessage && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                className="mt-3"
              >
                <div className="flex items-center gap-2 bg-white/70 backdrop-blur-sm p-2 rounded-lg border border-blue-200/50">
                  <motion.div
                    animate={{ 
                      rotate: 360,
                      scale: [1, 1.2, 1]
                    }}
                    transition={{ 
                      rotate: { duration: 3, repeat: Infinity, ease: "linear" },
                      scale: { duration: 1.5, repeat: Infinity }
                    }}
                  >
                    <Sparkles className="w-4 h-4 text-blue-500" />
                  </motion.div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-foreground truncate">{currentMessage}</p>
                    {/* リサーチ進捗表示 - researchingステップでのみ表示 */}
                    {researchProgress && currentStep === 'researching' && (
                      <div className="text-xs text-blue-600 mt-1">
                        リサーチ {researchProgress.currentQuery}/{researchProgress.totalQueries}: {researchProgress.query.slice(0, 50)}...
                      </div>
                    )}
                    {/* セクション執筆進捗表示 - writing_sectionsステップでのみ表示 */}
                    {sectionsProgress && currentStep === 'writing_sections' && (
                      <div className="text-xs text-purple-600 mt-1">
                        セクション {sectionsProgress.currentSection}/{sectionsProgress.totalSections}: {sectionsProgress.sectionHeading}
                      </div>
                    )}
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </CardContent>
      </Card>

      {/* Main Content Area */}
      <AnimatePresence>
        {!hideProcessCards && (
          <motion.div 
            className={`grid gap-4 ${shouldShowPreview ? 'grid-cols-2' : 'grid-cols-1'}`}
            exit={{ 
              opacity: 0, 
              y: -50, 
              transition: { duration: 0.8, ease: "easeInOut" } 
            }}
          >
        
        {/* Left Column: Steps Grid */}
        <div className="space-y-4">
          <div className="grid grid-cols-4 gap-2">
            {steps.map((step, index) => {
              const Icon = stepIcons[step.id as keyof typeof stepIcons] || FileText;
              // Don't show spinner if waiting for user input or status is user_input_required
              const isActive = step.status === 'in_progress' && !isWaitingForInput && status !== 'user_input_required';
              
              return (
                <motion.div
                  key={step.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.1 }}
                  className={`
                    relative p-2 rounded-lg border transition-all duration-500
                    ${stepColors[step.status]}
                    ${isActive ? 'ring-2 ring-blue-400 shadow-xl shadow-blue-200/50 scale-105 bg-gradient-to-br from-blue-50 to-blue-100' : ''}
                    hover:shadow-md cursor-pointer
                  `}
                >
                  <div className="flex flex-col items-center text-center space-y-1">
                    <div className={`
                      w-8 h-8 rounded-full flex items-center justify-center transition-all duration-300
                      ${step.status === 'completed' ? 'bg-green-500 text-white shadow-lg shadow-green-200' :
                        step.status === 'in_progress' ? 'bg-blue-500 text-white shadow-lg shadow-blue-200' :
                        step.status === 'error' ? 'bg-red-500 text-white shadow-lg shadow-red-200' :
                        'bg-gray-300 text-gray-600'}
                    `}>
                      {step.status === 'completed' ? (
                        <motion.div
                          initial={{ scale: 0 }}
                          animate={{ scale: 1 }}
                          transition={{ type: "spring", stiffness: 400, damping: 17 }}
                        >
                          <Check className="w-4 h-4" />
                        </motion.div>
                      ) : step.status === 'in_progress' && !isWaitingForInput && status !== 'user_input_required' ? (
                        <motion.div
                          animate={{ rotate: 360 }}
                          transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                        >
                          <Icon className="w-4 h-4" />
                        </motion.div>
                      ) : step.status === 'in_progress' ? (
                        // Show static icon when waiting for input (approval state)
                        <Icon className="w-4 h-4" />
                      ) : step.status === 'error' ? (
                        <motion.div
                          animate={{ x: [0, -1, 1, -1, 1, 0] }}
                          transition={{ duration: 0.5, repeat: Infinity, repeatDelay: 2 }}
                        >
                          <AlertCircle className="w-4 h-4" />
                        </motion.div>
                      ) : (
                        <Icon className="w-4 h-4" />
                      )}
                    </div>
                    
                    <h3 className={`font-medium text-xs leading-tight transition-colors duration-300 ${
                      isActive ? 'text-blue-700' : ''
                    }`}>
                      {step.name || step.title}
                    </h3>
                    
                    {step.status === 'in_progress' && !isWaitingForInput && status !== 'user_input_required' && (
                      <motion.div
                        animate={{ 
                          scale: [1, 1.2, 1],
                          opacity: [0.6, 1, 0.6] 
                        }}
                        transition={{ duration: 1.5, repeat: Infinity }}
                        className="w-1.5 h-1.5 bg-blue-500 rounded-full"
                      />
                    )}
                  </div>
                  
                  {/* Step number */}
                  <div className="absolute -top-1 -left-1 w-4 h-4 bg-white border border-primary/30 rounded-full flex items-center justify-center text-xs font-bold text-primary shadow-sm">
                    {index + 1}
                  </div>
                  
                  {/* Glow effect for active step */}
                  {isActive && (
                    <motion.div
                      className="absolute inset-0 rounded-lg bg-blue-400/20 blur-sm -z-10"
                      animate={{ 
                        opacity: [0.3, 0.6, 0.3],
                        scale: [1, 1.05, 1]
                      }}
                      transition={{ duration: 2, repeat: Infinity }}
                    />
                  )}
                </motion.div>
              );
            })}
          </div>
        </div>

        {/* Right Column: Article Preview */}
        {shouldShowPreview && (
          <div className="space-y-3">
            <Card className="h-full shadow-lg border-gray-200">
              <CardContent className="p-3 h-full">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <Eye className="w-4 h-4 text-gray-600" />
                    <h3 className="text-base font-semibold text-gray-800">リアルタイムプレビュー</h3>
                  </div>
                  {currentStep === 'completed' && finalArticle && (
                    <motion.div
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      transition={{ type: "spring", stiffness: 400, damping: 17 }}
                    >
                      <Badge className="bg-green-100 text-green-800 border-green-200 shadow-sm">
                        <Check className="w-3 h-3 mr-1" />
                        完成
                      </Badge>
                    </motion.div>
                  )}
                </div>

                {/* Compact Statistics */}
                {(generatedContent || finalArticle) && (
                  <div className="grid grid-cols-2 gap-2 mb-3">
                    <motion.div 
                      className="text-center p-2 bg-gradient-to-br from-blue-50 to-blue-100 rounded-lg border border-blue-200"
                      whileHover={{ scale: 1.02 }}
                    >
                      <div className="text-lg font-bold text-blue-600">{wordCount.toLocaleString()}</div>
                      <div className="text-xs text-blue-600">文字</div>
                    </motion.div>
                    <motion.div 
                      className="text-center p-2 bg-gradient-to-br from-purple-50 to-purple-100 rounded-lg border border-purple-200"
                      whileHover={{ scale: 1.02 }}
                    >
                      <div className="text-lg font-bold text-purple-600">{estimatedReadingTime}</div>
                      <div className="text-xs text-purple-600">読了時間（分）</div>
                      <div className="text-xs text-purple-400 mt-1">※400文字/分で計算</div>
                    </motion.div>
                  </div>
                )}

                {/* Preview Content */}
                <div className="relative">
                  <div className="overflow-y-auto max-h-[400px] border rounded-lg p-3 bg-white shadow-inner">
                    {currentStep === 'completed' && finalArticle ? (
                      <motion.div 
                        className="space-y-3"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ duration: 0.5 }}
                      >
                        <h2 className="text-lg font-bold text-gray-900 border-b pb-2">
                          {finalArticle.title}
                        </h2>
                        <ArticlePreviewStyles>
                          <div 
                            dangerouslySetInnerHTML={{ 
                              __html: finalArticle.content || '<p>記事の内容を読み込み中...</p>' 
                            }} 
                          />
                        </ArticlePreviewStyles>
                      </motion.div>
                    ) : imageMode && completedSections && completedSections.length > 0 ? (
                      /* 画像モード：セクション別表示 */
                      (() => {
                        console.log('🎨 Rendering image mode sections:', {
                          imageMode,
                          completedSectionsCount: completedSections?.length,
                          completedSections: completedSections?.map(s => ({ index: s.index, heading: s.heading?.substring(0, 50) }))
                        });
                        return (
                          <div className="space-y-3">
                            <div className="flex items-center space-x-2 text-sm text-gray-600 pb-2 border-b bg-purple-50/50 rounded p-2">
                              <motion.div 
                                className="w-2 h-2 bg-purple-500 rounded-full"
                                animate={{ 
                                  scale: [1, 1.3, 1],
                                  opacity: [0.7, 1, 0.7]
                                }}
                                transition={{ duration: 1.5, repeat: Infinity }}
                              />
                              <span className="font-medium">画像モード進行中...</span>
                              <motion.div
                                initial={{ scale: 0 }}
                                animate={{ scale: 1 }}
                                transition={{ type: "spring", stiffness: 400, damping: 17 }}
                              >
                                <Badge className="bg-purple-100 text-purple-800 border-purple-200 shadow-sm">
                                  {/* eslint-disable-next-line jsx-a11y/alt-text */}
                                  <Image className="w-3 h-3 mr-1" aria-hidden="true" />
                                  {completedSections.length} セクション完了
                                </Badge>
                              </motion.div>
                            </div>
                        
                        <div className="space-y-4">
                          {completedSections
                            .sort((a, b) => a.index - b.index)
                            .map((section, index) => (
                              <motion.div
                                key={section.index}
                                initial={{ opacity: 0, y: 20 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ duration: 0.5, delay: index * 0.1 }}
                                className="border border-green-200 bg-green-50/50 rounded-lg p-4"
                              >
                                <div className="flex items-center justify-between mb-3">
                                  <h3 className="font-semibold text-gray-800 text-base">{section.heading}</h3>
                                  <Badge variant="secondary" className="text-xs bg-green-100 text-green-700 border-green-300">
                                    <Check className="w-3 h-3 mr-1" />
                                    完了
                                  </Badge>
                                </div>
                                
                                {/* 画像プレースホルダー情報 */}
                                {section.imagePlaceholders && section.imagePlaceholders.length > 0 && (
                                  <div className="mb-3 text-xs text-purple-600 bg-purple-50 rounded px-2 py-1 border border-purple-200">
                                    {/* eslint-disable-next-line jsx-a11y/alt-text */}
                                    <Image className="w-3 h-3 inline mr-1" aria-hidden="true" />
                                    画像プレースホルダー {section.imagePlaceholders.length}個含む
                                  </div>
                                )}
                                
                                <ArticlePreviewStyles>
                                  <div 
                                    dangerouslySetInnerHTML={{ __html: section.content }}
                                    className="prose prose-sm max-w-none"
                                  />
                                </ArticlePreviewStyles>
                              </motion.div>
                            ))}
                        </div>
                          </div>
                        );
                      })()
                    ) : generatedContent ? (
                      /* 通常モード：ストリーミング表示 */
                      <div className="space-y-3">
                        <div className="flex items-center space-x-2 text-sm text-gray-600 pb-2 border-b bg-blue-50/50 rounded p-2">
                          <motion.div 
                            className="w-2 h-2 bg-blue-500 rounded-full"
                            animate={{ 
                              scale: [1, 1.3, 1],
                              opacity: [0.7, 1, 0.7]
                            }}
                            transition={{ duration: 1.5, repeat: Infinity }}
                          />
                          <span className="font-medium">生成中...</span>
                          {currentSection && (
                            <span className="text-blue-600 font-medium text-xs bg-blue-100 px-2 py-1 rounded-full">
                              {currentSection.heading}
                            </span>
                          )}
                        </div>
                        
                        <ArticlePreviewStyles>
                          <motion.div 
                            dangerouslySetInnerHTML={{ 
                              __html: generatedContent || '<p>記事を生成中...</p>' 
                            }}
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            transition={{ duration: 0.3 }}
                          />
                        </ArticlePreviewStyles>
                      </div>
                    ) : imageMode && currentStep === 'writing_sections' ? (
                      /* 画像モード：セクション生成中でまだ完了したセクションがない場合 */
                      <div className="space-y-3">
                        <div className="flex items-center space-x-2 text-sm text-gray-600 pb-2 border-b bg-purple-50/50 rounded p-2">
                          <motion.div 
                            className="w-2 h-2 bg-purple-500 rounded-full"
                            animate={{ 
                              scale: [1, 1.3, 1],
                              opacity: [0.7, 1, 0.7]
                            }}
                            transition={{ duration: 1.5, repeat: Infinity }}
                          />
                          <span className="font-medium">画像モードでセクション生成中...</span>
                          {currentSection && (
                            <span className="text-purple-600 font-medium text-xs bg-purple-100 px-2 py-1 rounded-full">
                              {currentSection.heading}
                            </span>
                          )}
                          <motion.div
                            initial={{ scale: 0 }}
                            animate={{ scale: 1 }}
                            transition={{ type: "spring", stiffness: 400, damping: 17 }}
                          >
                            <Badge className="bg-purple-100 text-purple-800 border-purple-200 shadow-sm">
                              {/* eslint-disable-next-line jsx-a11y/alt-text */}
                              <Image className="w-3 h-3 mr-1" aria-hidden="true" />
                              画像モード
                            </Badge>
                          </motion.div>
                        </div>
                        
                        <div className="flex items-center justify-center h-32 text-purple-600">
                          <motion.div 
                            className="text-center"
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ duration: 0.5 }}
                          >
                            <motion.div
                              animate={{ rotate: [0, 10, -10, 0] }}
                              transition={{ duration: 3, repeat: Infinity }}
                            >
                              <BookOpen className="w-10 h-10 mx-auto mb-2 text-purple-400" />
                            </motion.div>
                            <p className="text-sm">セクション生成中...</p>
                            <p className="text-xs text-purple-500 mt-1">完了したセクションは順次表示されます</p>
                          </motion.div>
                        </div>
                      </div>
                    ) : steps.some(step => step.status === 'error') ? (
                      <div className="flex items-center justify-center h-32 text-red-500">
                        <motion.div 
                          className="text-center"
                          initial={{ opacity: 0, y: 10 }}
                          animate={{ opacity: 1, y: 0 }}
                          transition={{ duration: 0.5 }}
                        >
                          <AlertCircle className="w-10 h-10 mx-auto mb-2 text-red-400" />
                          <p className="text-sm">記事生成でエラーが発生しました</p>
                        </motion.div>
                      </div>
                    ) : (
                      <div className="flex items-center justify-center h-32 text-gray-500">
                        <motion.div 
                          className="text-center"
                          initial={{ opacity: 0, y: 10 }}
                          animate={{ opacity: 1, y: 0 }}
                          transition={{ duration: 0.5 }}
                        >
                          <motion.div
                            animate={{ rotate: [0, 10, -10, 0] }}
                            transition={{ duration: 3, repeat: Infinity }}
                          >
                            <BookOpen className="w-10 h-10 mx-auto mb-2 text-gray-300" />
                          </motion.div>
                          <p className="text-sm">記事生成の準備中...</p>
                        </motion.div>
                      </div>
                    )}
                  </div>
                  
                  {/* Scroll indicator */}
                  {generatedContent && (
                    <motion.div
                      className="absolute bottom-2 right-2 bg-blue-500 text-white text-xs px-2 py-1 rounded-full shadow-lg"
                      animate={{ opacity: [0.7, 1, 0.7] }}
                      transition={{ duration: 2, repeat: Infinity }}
                    >
                      更新中
                    </motion.div>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>
        )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* 完了アニメーション */}
      <AnimatePresence>
        {showCompletionAnimation && (
          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
          >
            <motion.div
              initial={{ y: 50, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ delay: 0.2 }}
              className="bg-white rounded-2xl p-8 shadow-2xl text-center max-w-md mx-4"
            >
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ 
                  delay: 0.4, 
                  type: "spring", 
                  stiffness: 400, 
                  damping: 17 
                }}
                className="w-20 h-20 bg-green-500 rounded-full flex items-center justify-center mx-auto mb-4"
              >
                <Check className="w-10 h-10 text-white" />
              </motion.div>
              <motion.h2
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.6 }}
                className="text-2xl font-bold text-gray-900 mb-2"
              >
                🎉 記事生成完了！
              </motion.h2>
              <motion.p
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.8 }}
                className="text-gray-600 mb-4"
              >
                高品質な記事が正常に生成されました
              </motion.p>
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 1 }}
                className="space-y-2"
              >
                <div className="text-sm text-gray-500 mb-2">進捗: 100%</div>
                <motion.div
                  className="w-full bg-gray-200 rounded-full h-3 overflow-hidden"
                  initial={{ scale: 0.8 }}
                  animate={{ scale: 1 }}
                  transition={{ delay: 1.2 }}
                >
                  <motion.div
                    className="h-full bg-gradient-to-r from-green-400 to-green-600 rounded-full"
                    initial={{ width: 0 }}
                    animate={{ width: '100%' }}
                    transition={{ delay: 1.4, duration: 0.8, ease: "easeInOut" }}
                  />
                </motion.div>
                <motion.p
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 2.2 }}
                  className="text-xs text-gray-600 text-center"
                >
                  記事プレビューを準備しています...
                </motion.p>
              </motion.div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* 完成記事の全面プレビュー */}
      <AnimatePresence>
        {hideProcessCards && finalArticle && (
          <motion.div
            initial={{ opacity: 0, y: 50 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, ease: "easeInOut" }}
            className="w-full"
          >
            <CompletedArticleView 
              article={finalArticle}
              onExport={() => {
                // エクスポート機能の実装
                const element = document.createElement('a');
                const file = new Blob([finalArticle.content], { type: 'text/html' });
                element.href = URL.createObjectURL(file);
                element.download = `${finalArticle.title.replace(/[^a-zA-Z0-9]/g, '_')}.html`;
                document.body.appendChild(element);
                element.click();
                document.body.removeChild(element);
              }}
              onNewArticle={() => {
                window.location.reload();
              }}
            />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}); 
