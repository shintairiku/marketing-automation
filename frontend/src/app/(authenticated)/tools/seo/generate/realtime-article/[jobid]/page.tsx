/**
 * Realtime Article Generation Page
 * 
 * This page demonstrates the new Supabase Realtime-based article generation
 * that replaces WebSocket communication. It provides the same functionality
 * as the original WebSocket version but uses REST API + Realtime database sync.
 */

'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useAuth } from '@clerk/nextjs';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { AlertCircle, CheckCircle, Clock, RefreshCw } from 'lucide-react';
import { useRealtimeArticleGeneration } from '@/features/tools/seo/generate/new-article/hooks/useRealtimeArticleGeneration';

export default function RealtimeArticleGenerationPage() {
  const params = useParams();
  const router = useRouter();
  const { isLoaded, isSignedIn } = useAuth();
  const jobId = params.jobid as string;
  
  const {
    generationState,
    isConnected,
    isLoading,
    processId,
    startGeneration,
    selectPersona,
    selectTheme,
    approvePlan,
    approveOutline,
    regenerateCurrentStep,
    disconnect,
    progressPercentage,
    currentStepTitle,
    canRegenerateStep,
  } = useRealtimeArticleGeneration();
  
  const [isInitialized, setIsInitialized] = useState(false);
  
  // Initialize generation if we have a job ID but no process
  useEffect(() => {
    if (!isLoaded || !isSignedIn) return;
    
    if (jobId && !processId && !isInitialized) {
      setIsInitialized(true);
      
      // For demo purposes, start with sample parameters
      // In a real app, these would come from URL params or localStorage
      const sampleParams = {
        initial_keywords: ['札幌', '注文住宅'],
        image_mode: false,
        article_style: 'informative',
        theme_count: 3,
        target_audience: '30代夫婦',
        persona: '子育て世代',
        company_info: 'サンプル工務店',
      };
      
      startGeneration(sampleParams);
    }
  }, [isLoaded, isSignedIn, jobId, processId, isInitialized, startGeneration]);
  
  // Handle authentication redirect
  if (!isLoaded) {
    return <div className="flex justify-center items-center min-h-screen">読み込み中...</div>;
  }
  
  if (!isSignedIn) {
    router.push('/sign-in');
    return null;
  }
  
  // Connection status indicator
  const ConnectionStatus = () => (
    <div className="flex items-center gap-2 mb-4">
      <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
      <span className="text-sm text-gray-600">
        {isConnected ? 'リアルタイム接続中' : '接続中...'}
      </span>
    </div>
  );
  
  // Progress section
  const ProgressSection = () => (
    <Card className="mb-6">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Clock className="w-5 h-5" />
          記事生成進捗
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          <div>
            <div className="flex justify-between items-center mb-2">
              <span className="text-sm font-medium">{currentStepTitle}</span>
              <span className="text-sm text-gray-500">{progressPercentage}%</span>
            </div>
            <Progress value={progressPercentage} className="w-full" />
          </div>
          
          {generationState.error && (
            <div className="flex items-center gap-2 p-3 bg-red-50 border border-red-200 rounded-md">
              <AlertCircle className="w-4 h-4 text-red-500" />
              <span className="text-sm text-red-700">{generationState.error}</span>
            </div>
          )}
          
          {canRegenerateStep && (
            <Button
              onClick={regenerateCurrentStep}
              disabled={isLoading}
              variant="outline"
              size="sm"
              className="flex items-center gap-2"
            >
              <RefreshCw className="w-4 h-4" />
              再生成
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
  
  // Steps visualization
  const StepsSection = () => (
    <Card className="mb-6">
      <CardHeader>
        <CardTitle>生成ステップ</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {generationState.steps.map((step) => (
            <div key={step.id} className="flex items-center gap-3">
              {step.status === 'completed' && (
                <CheckCircle className="w-5 h-5 text-green-500" />
              )}
              {step.status === 'in_progress' && (
                <div className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
              )}
              {step.status === 'error' && (
                <AlertCircle className="w-5 h-5 text-red-500" />
              )}
              {step.status === 'pending' && (
                <div className="w-5 h-5 border-2 border-gray-300 rounded-full" />
              )}
              
              <span className="flex-1">{step.title}</span>
              
              <Badge variant={
                step.status === 'completed' ? 'default' :
                step.status === 'in_progress' ? 'secondary' :
                step.status === 'error' ? 'destructive' : 'outline'
              }>
                {step.status === 'completed' ? '完了' :
                 step.status === 'in_progress' ? '実行中' :
                 step.status === 'error' ? 'エラー' : '待機中'}
              </Badge>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
  
  // User input section
  const UserInputSection = () => {
    if (!generationState.isWaitingForInput) return null;
    
    return (
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>ユーザー入力が必要です</CardTitle>
        </CardHeader>
        <CardContent>
          {generationState.inputType === 'select_persona' && generationState.personas && (
            <div className="space-y-3">
              <p className="text-sm text-gray-600 mb-4">以下のペルソナから選択してください：</p>
              {generationState.personas.map((persona) => (
                <Button
                  key={persona.id}
                  onClick={() => selectPersona(persona.id)}
                  disabled={isLoading}
                  variant="outline"
                  className="w-full text-left justify-start h-auto p-4"
                >
                  <div>
                    <div className="font-medium">ペルソナ {persona.id + 1}</div>
                    <div className="text-sm text-gray-600 mt-1">{persona.description}</div>
                  </div>
                </Button>
              ))}
            </div>
          )}
          
          {generationState.inputType === 'select_theme' && generationState.themes && (
            <div className="space-y-3">
              <p className="text-sm text-gray-600 mb-4">以下のテーマから選択してください：</p>
              {generationState.themes.map((theme, index) => (
                <Button
                  key={index}
                  onClick={() => selectTheme(index)}
                  disabled={isLoading}
                  variant="outline"
                  className="w-full text-left justify-start h-auto p-4"
                >
                  <div>
                    <div className="font-medium">{theme.title}</div>
                    <div className="text-sm text-gray-600 mt-1">{theme.description}</div>
                  </div>
                </Button>
              ))}
            </div>
          )}
          
          {generationState.inputType === 'approve_plan' && generationState.researchPlan && (
            <div className="space-y-4">
              <p className="text-sm text-gray-600">リサーチ計画を確認してください：</p>
              <div className="bg-gray-50 p-4 rounded-md">
                <pre className="text-sm">{JSON.stringify(generationState.researchPlan, null, 2)}</pre>
              </div>
              <Button
                onClick={() => approvePlan(generationState.researchPlan)}
                disabled={isLoading}
                className="w-full"
              >
                承認する
              </Button>
            </div>
          )}
          
          {generationState.inputType === 'approve_outline' && generationState.outline && (
            <div className="space-y-4">
              <p className="text-sm text-gray-600">アウトラインを確認してください：</p>
              <div className="bg-gray-50 p-4 rounded-md">
                <pre className="text-sm">{JSON.stringify(generationState.outline, null, 2)}</pre>
              </div>
              <Button
                onClick={() => approveOutline(generationState.outline)}
                disabled={isLoading}
                className="w-full"
              >
                承認する
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    );
  };
  
  // Research progress section
  const ResearchProgressSection = () => {
    if (!generationState.researchProgress) return null;
    
    const { currentQuery, totalQueries, query } = generationState.researchProgress;
    
    return (
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>リサーチ進捗</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-sm">進捗</span>
              <span className="text-sm text-gray-500">{currentQuery} / {totalQueries}</span>
            </div>
            <Progress value={(currentQuery / totalQueries) * 100} />
            <p className="text-sm text-gray-600">現在のクエリ: {query}</p>
          </div>
        </CardContent>
      </Card>
    );
  };
  
  // Section writing progress
  const SectionProgressSection = () => {
    if (!generationState.sectionsProgress) return null;
    
    const { currentSection, totalSections, sectionHeading } = generationState.sectionsProgress;
    
    return (
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>記事執筆進捗</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-sm">セクション</span>
              <span className="text-sm text-gray-500">{currentSection} / {totalSections}</span>
            </div>
            <Progress value={(currentSection / totalSections) * 100} />
            <p className="text-sm text-gray-600">現在のセクション: {sectionHeading}</p>
            
            {generationState.currentSection && (
              <div className="mt-4 p-4 bg-gray-50 rounded-md">
                <div className="prose prose-sm max-w-none">
                  <div dangerouslySetInnerHTML={{ __html: generationState.currentSection.content }} />
                </div>
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    );
  };
  
  // Final result section
  const FinalResultSection = () => {
    if (!generationState.finalArticle) return null;
    
    return (
      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <CheckCircle className="w-5 h-5 text-green-500" />
            記事生成完了
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <h3 className="text-lg font-semibold">{generationState.finalArticle.title}</h3>
            <div className="prose prose-sm max-w-none bg-gray-50 p-4 rounded-md">
              <div dangerouslySetInnerHTML={{ __html: generationState.finalArticle.content }} />
            </div>
            {generationState.articleId && (
              <Button
                onClick={() => router.push(`/tools/seo/articles/${generationState.articleId}`)}
                className="w-full"
              >
                記事を表示
              </Button>
            )}
          </div>
        </CardContent>
      </Card>
    );
  };
  
  return (
    <div className="container mx-auto p-6 max-w-4xl">
      <div className="mb-6">
        <h1 className="text-2xl font-bold mb-2">Realtime記事生成</h1>
        <p className="text-gray-600">
          Supabase Realtimeを使用した新しい記事生成システムです。
          リアルタイムでの進捗更新とユーザーインタラクションを提供します。
        </p>
      </div>
      
      <ConnectionStatus />
      <ProgressSection />
      <StepsSection />
      <UserInputSection />
      <ResearchProgressSection />
      <SectionProgressSection />
      <FinalResultSection />
      
      {/* Debug info */}
      {process.env.NODE_ENV === 'development' && (
        <Card className="mt-6">
          <CardHeader>
            <CardTitle>デバッグ情報</CardTitle>
          </CardHeader>
          <CardContent>
            <pre className="text-xs bg-gray-100 p-4 rounded overflow-auto">
              {JSON.stringify({
                processId,
                isConnected,
                isLoading,
                currentStep: generationState.currentStep,
                isWaitingForInput: generationState.isWaitingForInput,
                inputType: generationState.inputType,
              }, null, 2)}
            </pre>
          </CardContent>
        </Card>
      )}
    </div>
  );
}