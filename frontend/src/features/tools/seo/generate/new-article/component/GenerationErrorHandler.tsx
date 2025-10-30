'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import { 
  AlertTriangle, 
  CheckCircle,
  HelpCircle,
  MessageCircle, 
  RefreshCw} from 'lucide-react';

import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface GenerationErrorHandlerProps {
  error: string;
  currentStep: string;
  onRetry: () => void;
  onCancel: () => void;
  isRetrying?: boolean;
}

export default function GenerationErrorHandler({
  error,
  currentStep,
  onRetry,
  onCancel,
  isRetrying = false
}: GenerationErrorHandlerProps) {
  const [showDetails, setShowDetails] = useState(false);

  const getErrorSuggestion = (error: string, step: string) => {
    if (error.includes('rate limit') || error.includes('429')) {
      return {
        title: 'API利用制限に達しました',
        suggestion: '少し時間をおいてから再試行してください。通常1-2分で制限が解除されます。',
        retryDelay: '2分後に自動で再試行',
        severity: 'warning' as const
      };
    }
    
    if (error.includes('network') || error.includes('connection')) {
      return {
        title: 'ネットワーク接続エラー',
        suggestion: 'インターネット接続を確認してから再試行してください。',
        retryDelay: '即座に再試行可能',
        severity: 'error' as const
      };
    }
    
    if (error.includes('authentication') || error.includes('401')) {
      return {
        title: '認証エラー',
        suggestion: 'ログインし直してから再試行してください。',
        retryDelay: 'ログイン後に再試行',
        severity: 'error' as const
      };
    }
    
    if (step.includes('research') && error.includes('no results')) {
      return {
        title: 'リサーチ結果が見つかりません',
        suggestion: 'キーワードを変更するか、より一般的な用語で再試行してください。',
        retryDelay: '即座に再試行可能',
        severity: 'warning' as const
      };
    }
    
    return {
      title: '予期しないエラーが発生しました',
      suggestion: 'しばらく時間をおいてから再試行してください。問題が続く場合はサポートにお問い合わせください。',
      retryDelay: '即座に再試行可能',
      severity: 'error' as const
    };
  };

  const errorInfo = getErrorSuggestion(error, currentStep);

  const getStepDisplayName = (step: string) => {
    const stepNames: Record<string, string> = {
      'keyword_analyzing': 'キーワード分析',
      'persona_generating': 'ペルソナ生成',
      'theme_generating': 'テーマ生成',
      'research_planning': 'リサーチ計画',
      'researching': 'リサーチ実行',
      'research_completed': 'リサーチ完了処理',
      'research_synthesizing': 'リサーチ統合',
      'outline_generating': 'アウトライン生成',
      'writing_sections': '記事執筆',
      'editing': '編集・校正',
    };
    return stepNames[step] || step;
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="w-full max-w-4xl mx-auto"
    >
      <Card className="border-2 border-red-200 bg-red-50/30 shadow-lg">
        <CardHeader className="bg-gradient-to-r from-red-50 to-orange-50 border-b border-red-200">
          <CardTitle className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-r from-red-500 to-orange-500 rounded-full flex items-center justify-center">
              <AlertTriangle className="w-5 h-5 text-white" />
            </div>
            <div>
              <h3 className="text-xl font-bold text-red-800">{errorInfo.title}</h3>
              <div className="flex items-center gap-2 mt-1">
                <Badge variant="outline" className="text-red-700 border-red-300">
                  {getStepDisplayName(currentStep)}で発生
                </Badge>
                <Badge 
                  variant={errorInfo.severity === 'error' ? 'destructive' : 'secondary'}
                  className="text-xs"
                >
                  {errorInfo.severity === 'error' ? 'エラー' : '警告'}
                </Badge>
              </div>
            </div>
          </CardTitle>
        </CardHeader>
        
        <CardContent className="p-6 space-y-6">
          {/* エラーメッセージと提案 */}
          <div className="space-y-4">
            <Alert className="border-orange-200 bg-orange-50">
              <HelpCircle className="h-4 w-4 text-orange-600" />
              <AlertDescription className="text-orange-800">
                <strong>解決方法：</strong> {errorInfo.suggestion}
              </AlertDescription>
            </Alert>
            
            <div className="bg-white rounded-lg p-4 border border-gray-200">
              <div className="flex items-center gap-2 mb-2">
                <CheckCircle className="w-4 h-4 text-green-600" />
                <span className="font-medium text-sm">再試行可能</span>
              </div>
              <p className="text-sm text-muted-foreground">{errorInfo.retryDelay}</p>
            </div>
          </div>

          {/* 詳細エラー情報 */}
          <div className="space-y-3">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowDetails(!showDetails)}
              className="text-red-600 hover:text-red-700"
            >
              {showDetails ? '詳細を隠す' : 'エラー詳細を表示'}
            </Button>
            
            {showDetails && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                className="bg-gray-100 rounded-lg p-4"
              >
                <p className="text-sm font-mono text-gray-700 break-all">
                  {error}
                </p>
              </motion.div>
            )}
          </div>

          {/* アクションボタン */}
          <div className="flex flex-col sm:flex-row gap-3 pt-4">
            <Button
              onClick={onRetry}
              disabled={isRetrying}
              className="flex items-center gap-2 flex-1"
            >
              {isRetrying ? (
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                >
                  <RefreshCw className="w-4 h-4" />
                </motion.div>
              ) : (
                <RefreshCw className="w-4 h-4" />
              )}
              {isRetrying ? '再試行中...' : '再試行する'}
            </Button>
            
            <Button
              variant="outline"
              onClick={onCancel}
              disabled={isRetrying}
              className="flex items-center gap-2 flex-1"
            >
              中止して最初に戻る
            </Button>
            
            <Button
              variant="ghost"
              size="sm"
              className="flex items-center gap-2"
              onClick={() => window.open('mailto:support@example.com', '_blank')}
            >
              <MessageCircle className="w-4 h-4" />
              サポートに連絡
            </Button>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
} 