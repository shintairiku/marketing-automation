'use client';

import { useCallback, useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { AlertCircle, CheckCircle, Info, RefreshCw } from 'lucide-react';

import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import ConnectionStatus from '@/components/ui/connection-status';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { type ActionResult,useArticleGenerationRealtime } from '@/hooks/useArticleGenerationRealtime';

interface EnhancedArticleGenerationProps {
  processId: string;
  userId: string;
  showDebugInfo?: boolean;
  enableConnectionStatus?: boolean;
}

export default function EnhancedArticleGeneration({
  processId,
  userId,
  showDebugInfo = false,
  enableConnectionStatus = true,
}: EnhancedArticleGenerationProps) {
  const [actionResults, setActionResults] = useState<Map<string, ActionResult>>(new Map());
  const [isPerformingAction, setIsPerformingAction] = useState(false);

  const {
    // State - ONLY from Supabase events
    state,
    connectionState,
    
    // Connection state
    isConnected,
    isConnecting,
    isSyncing,
    lastSyncTime,
    dataVersion,
    error,

    // Actions - All with connection awareness and queuing
    connect,
    disconnect,
    startArticleGeneration,
    selectPersona,
    selectTheme,
    approvePlan,
    approveOutline,
    refreshData,
    
    // Data integrity
    getPendingActionsSummary,
    pendingActionsCount,
    
    // Computed state based on Supabase Realtime connection - STRICT requirements
    isRealtimeReady,
    canPerformActions,
    isDataStale,
    
    // Debug information
    debugInfo
  } = useArticleGenerationRealtime({
    processId,
    userId,
    autoConnect: true
  });

  // Action handler with comprehensive result tracking
  const handleAction = useCallback(async (
    actionName: string, 
    actionFn: () => Promise<ActionResult>,
    description: string
  ) => {
    if (!canPerformActions) {
      console.warn(`Cannot perform ${actionName} - actions blocked`);
      return;
    }

    setIsPerformingAction(true);
    
    try {
      console.log(`🚀 Starting action: ${actionName} - ${description}`);
      const result = await actionFn();
      
      setActionResults(prev => new Map(prev.set(actionName, result)));
      
      if (result.success) {
        console.log(`✅ Action completed successfully: ${actionName}`);
      } else {
        console.error(`❌ Action failed: ${actionName}`, result.error);
      }
      
      return result;
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      const failureResult: ActionResult = { success: false, error: errorMessage };
      
      setActionResults(prev => new Map(prev.set(actionName, failureResult)));
      console.error(`❌ Action threw error: ${actionName}`, error);
      
      return failureResult;
    } finally {
      setIsPerformingAction(false);
    }
  }, [canPerformActions]);

  // Clear action results when connection state changes
  useEffect(() => {
    if (isConnected && actionResults.size > 0) {
      // Clear old results when reconnected
      setActionResults(new Map());
    }
  }, [isConnected, actionResults.size]);

  const renderPersonaSelection = () => {
    if (!state.personas || state.personas.length === 0) return null;

    return (
      <Card>
        <CardHeader>
          <CardTitle>ペルソナ選択</CardTitle>
          <CardDescription>
            記事のターゲットとなるペルソナを選択してください
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {state.personas.map((persona, index) => (
            <motion.div
              key={persona.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 }}
            >
              <Card className="cursor-pointer hover:bg-gray-50 transition-colors">
                <CardContent className="p-4">
                  <p className="text-sm">{persona.description}</p>
                  <Button
                    size="sm"
                    className="mt-2"
                    disabled={!canPerformActions || isPerformingAction}
                    onClick={() => handleAction(
                      'selectPersona',
                      () => selectPersona(persona.id),
                      `ペルソナ ${persona.id} を選択`
                    )}
                  >
                    {isPerformingAction ? (
                      <>
                        <RefreshCw className="w-3 h-3 mr-1 animate-spin" />
                        選択中...
                      </>
                    ) : (
                      'このペルソナを選択'
                    )}
                  </Button>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </CardContent>
      </Card>
    );
  };

  const renderThemeSelection = () => {
    if (!state.themes || state.themes.length === 0) return null;

    return (
      <Card>
        <CardHeader>
          <CardTitle>テーマ選択</CardTitle>
          <CardDescription>
            記事のテーマを選択してください
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {state.themes.map((theme, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 }}
            >
              <Card className="cursor-pointer hover:bg-gray-50 transition-colors">
                <CardContent className="p-4">
                  <h4 className="font-medium">{theme.title}</h4>
                  <p className="text-sm text-gray-600 mt-1">{theme.description}</p>
                  {theme.keywords && theme.keywords.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-2">
                      {theme.keywords.map((keyword, i) => (
                        <span
                          key={i}
                          className="bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded"
                        >
                          {keyword}
                        </span>
                      ))}
                    </div>
                  )}
                  <Button
                    size="sm"
                    className="mt-2"
                    disabled={!canPerformActions || isPerformingAction}
                    onClick={() => handleAction(
                      'selectTheme',
                      () => selectTheme(index),
                      `テーマ「${theme.title}」を選択`
                    )}
                  >
                    {isPerformingAction ? (
                      <>
                        <RefreshCw className="w-3 h-3 mr-1 animate-spin" />
                        選択中...
                      </>
                    ) : (
                      'このテーマを選択'
                    )}
                  </Button>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </CardContent>
      </Card>
    );
  };

  const renderResearchPlanApproval = () => {
    if (!state.researchPlan) return null;

    return (
      <Card>
        <CardHeader>
          <CardTitle>リサーチ計画の承認</CardTitle>
          <CardDescription>
            以下のリサーチ計画をご確認ください
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="bg-gray-50 p-4 rounded-lg">
            <pre className="text-sm whitespace-pre-wrap">
              {typeof state.researchPlan === 'string' 
                ? state.researchPlan 
                : JSON.stringify(state.researchPlan, null, 2)
              }
            </pre>
          </div>
          <div className="flex gap-2">
            <Button
              variant="default"
              disabled={!canPerformActions || isPerformingAction}
              onClick={() => handleAction(
                'approvePlan',
                () => approvePlan(true),
                'リサーチ計画を承認'
              )}
            >
              {isPerformingAction ? (
                <>
                  <RefreshCw className="w-3 h-3 mr-1 animate-spin" />
                  処理中...
                </>
              ) : (
                '承認する'
              )}
            </Button>
            <Button
              variant="outline"
              disabled={!canPerformActions || isPerformingAction}
              onClick={() => handleAction(
                'approvePlan',
                () => approvePlan(false),
                'リサーチ計画を却下'
              )}
            >
              却下する
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  };

  const renderOutlineApproval = () => {
    if (!state.outline) return null;

    const renderOutlineTree = (items: any[], depth = 0): JSX.Element[] | null => {
      if (!Array.isArray(items) || items.length === 0) return null;
      return items.map((item, index) => {
        const key = `outline-approval-${depth}-${index}`;
        const children = renderOutlineTree(item?.subsections || [], depth + 1);
        return (
          <div
            key={key}
            className={`space-y-1 ${depth > 0 ? 'border-l border-dashed border-gray-200 pl-3' : ''}`}
          >
            <div className="flex items-center gap-2">
              {typeof item?.level === 'number' && (
                <Badge variant="outline" className="bg-white text-blue-700">
                  H{item.level}
                </Badge>
              )}
              <h5 className="text-sm font-medium">{item?.heading || ''}</h5>
            </div>
            {item?.description && (
              <p className="ml-6 text-xs text-gray-500">{item.description}</p>
            )}
            {item?.estimated_chars && (
              <p className="ml-6 text-xs text-gray-400">約 {item.estimated_chars} 文字</p>
            )}
            {children && <div className="space-y-1">{children}</div>}
          </div>
        );
      });
    };

    return (
      <Card>
        <CardHeader>
          <CardTitle>アウトライン承認</CardTitle>
          <CardDescription>
            生成されたアウトラインをご確認ください
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="bg-gray-50 p-4 rounded-lg">
            <h4 className="font-medium">{state.outline.title}</h4>
            {state.outline.sections && (
              <div className="mt-3 space-y-2">
                {renderOutlineTree(state.outline.sections)}
              </div>
            )}
          </div>
          <div className="flex gap-2">
            <Button
              variant="default"
              disabled={!canPerformActions || isPerformingAction}
              onClick={() => handleAction(
                'approveOutline',
                () => approveOutline(true),
                'アウトラインを承認'
              )}
            >
              {isPerformingAction ? (
                <>
                  <RefreshCw className="w-3 h-3 mr-1 animate-spin" />
                  処理中...
                </>
              ) : (
                '承認する'
              )}
            </Button>
            <Button
              variant="outline"
              disabled={!canPerformActions || isPerformingAction}
              onClick={() => handleAction(
                'approveOutline',
                () => approveOutline(false),
                'アウトラインを却下'
              )}
            >
              却下する
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  };

  const renderActionResults = () => {
    if (actionResults.size === 0) return null;

    return (
      <Card>
        <CardHeader>
          <CardTitle>操作結果</CardTitle>
          <CardDescription>最近実行された操作の結果</CardDescription>
        </CardHeader>
        <CardContent className="space-y-2">
          {Array.from(actionResults.entries()).map(([action, result]) => (
            <Alert key={action} variant={result.success ? "default" : "destructive"}>
              {result.success ? (
                <CheckCircle className="h-4 w-4" />
              ) : (
                <AlertCircle className="h-4 w-4" />
              )}
              <AlertDescription>
                <strong>{action}:</strong> {result.success ? '成功' : result.error}
              </AlertDescription>
            </Alert>
          ))}
        </CardContent>
      </Card>
    );
  };

  return (
    <div className="space-y-6">
      {/* Connection Status */}
      {enableConnectionStatus && (
        <ConnectionStatus
          isConnected={isConnected}
          isConnecting={isConnecting}
          isSyncing={isSyncing}
          lastSyncTime={lastSyncTime}
          error={error}
          canPerformActions={canPerformActions}
          pendingActionsCount={pendingActionsCount}
          queuedActionsCount={debugInfo?.connectionMetrics?.queuedActions || 0}
          onRetry={connect}
          onRefresh={refreshData}
          debugMode={showDebugInfo}
          debugInfo={showDebugInfo ? debugInfo : undefined}
        />
      )}

      {/* Data Stale Warning */}
      {isDataStale && isConnected && (
        <Alert>
          <Info className="h-4 w-4" />
          <AlertDescription>
            データが古い可能性があります。最新の情報を取得するには更新ボタンをクリックしてください。
          </AlertDescription>
        </Alert>
      )}

      <Tabs defaultValue="generation" className="w-full">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="generation">記事生成</TabsTrigger>
          <TabsTrigger value="results">操作結果</TabsTrigger>
          {showDebugInfo && <TabsTrigger value="debug">デバッグ</TabsTrigger>}
        </TabsList>

        <TabsContent value="generation" className="space-y-6">
          {/* Current Step Display */}
          <Card>
            <CardHeader>
              <CardTitle>現在のステップ: {state.currentStep}</CardTitle>
              <CardDescription>
                待機中の入力: {state.isWaitingForInput ? 'あり' : 'なし'}
                {state.inputType && ` (${state.inputType})`}
              </CardDescription>
            </CardHeader>
          </Card>

          {/* Dynamic Content Based on Current State */}
          {state.inputType === 'select_persona' && renderPersonaSelection()}
          {state.inputType === 'select_theme' && renderThemeSelection()}
          {state.inputType === 'approve_plan' && renderResearchPlanApproval()}
          {state.inputType === 'approve_outline' && renderOutlineApproval()}

          {/* Generated Content Display */}
          {state.generatedContent && (
            <Card>
              <CardHeader>
                <CardTitle>生成された記事</CardTitle>
              </CardHeader>
              <CardContent>
                <div 
                  className="prose max-w-none"
                  dangerouslySetInnerHTML={{ __html: state.generatedContent }}
                />
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="results">
          {renderActionResults()}
        </TabsContent>

        {showDebugInfo && (
          <TabsContent value="debug">
            <Card>
              <CardHeader>
                <CardTitle>デバッグ情報</CardTitle>
                <CardDescription>開発者向け詳細情報</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div>
                    <h4 className="font-medium">接続状態</h4>
                    <pre className="text-xs bg-gray-100 p-2 rounded mt-1">
                      {JSON.stringify({
                        isConnected,
                        isConnecting,
                        isSyncing,
                        canPerformActions,
                        isRealtimeReady,
                        isDataStale,
                        lastSyncTime: lastSyncTime?.toISOString(),
                        dataVersion,
                        pendingActionsCount
                      }, null, 2)}
                    </pre>
                  </div>
                  
                  <div>
                    <h4 className="font-medium">生成状態</h4>
                    <pre className="text-xs bg-gray-100 p-2 rounded mt-1">
                      {JSON.stringify({
                        currentStep: state.currentStep,
                        isWaitingForInput: state.isWaitingForInput,
                        inputType: state.inputType,
                        hasPersonas: !!state.personas,
                        hasThemes: !!state.themes,
                        hasResearchPlan: !!state.researchPlan,
                        hasOutline: !!state.outline,
                        hasGeneratedContent: !!state.generatedContent,
                        error: state.error
                      }, null, 2)}
                    </pre>
                  </div>

                  {debugInfo && (
                    <div>
                      <h4 className="font-medium">詳細デバッグ情報</h4>
                      <pre className="text-xs bg-gray-100 p-2 rounded mt-1 max-h-96 overflow-auto">
                        {JSON.stringify(debugInfo, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        )}
      </Tabs>
    </div>
  );
}
