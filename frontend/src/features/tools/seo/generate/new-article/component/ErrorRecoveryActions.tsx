'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import { AlertTriangle, RotateCcw, Bug, HelpCircle, ExternalLink } from 'lucide-react';

import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';

interface ErrorRecoveryActionsProps {
    error: string;
    currentStep: string;
    processId?: string;
    onRetry: () => void;
    onRestart: () => void;
    onContactSupport?: () => void;
    canRetry?: boolean;
    retryCount?: number;
    maxRetries?: number;
}

export default function ErrorRecoveryActions({
    error,
    currentStep,
    processId,
    onRetry,
    onRestart,
    onContactSupport,
    canRetry = true,
    retryCount = 0,
    maxRetries = 3
}: ErrorRecoveryActionsProps) {
    const [showDetails, setShowDetails] = useState(false);
    const [isRetrying, setIsRetrying] = useState(false);

    const getErrorSeverity = (error: string) => {
        const lowerError = error.toLowerCase();
        if (lowerError.includes('authentication') || lowerError.includes('unauthorized')) {
            return 'auth';
        } else if (lowerError.includes('network') || lowerError.includes('connection')) {
            return 'network';
        } else if (lowerError.includes('validation') || lowerError.includes('invalid')) {
            return 'validation';
        } else if (lowerError.includes('timeout') || lowerError.includes('timed out')) {
            return 'timeout';
        }
        return 'unknown';
    };

    const getErrorAdvice = (severity: string) => {
        switch (severity) {
            case 'auth':
                return 'ログインセッションが期限切れの可能性があります。ページを更新してログインし直してください。';
            case 'network':
                return 'インターネット接続を確認し、しばらく待ってからもう一度お試しください。';
            case 'validation':
                return '入力内容に問題がある可能性があります。入力項目を確認してください。';
            case 'timeout':
                return 'サーバーの応答が遅い可能性があります。しばらく待ってからもう一度お試しください。';
            default:
                return '一時的な問題の可能性があります。しばらく待ってからもう一度お試しください。';
        }
    };

    const getStepDisplayName = (step: string) => {
        const stepNames: Record<string, string> = {
            'keyword_analyzing': 'キーワード分析',
            'persona_generating': 'ペルソナ生成',
            'theme_generating': 'テーマ提案',
            'research_planning': 'リサーチ計画',
            'researching': 'リサーチ実行',
            'outline_generating': 'アウトライン作成',
            'writing_sections': '記事執筆',
            'editing': '編集・校正',
        };
        return stepNames[step] || step;
    };

    const handleRetry = async () => {
        setIsRetrying(true);
        try {
            await onRetry();
        } finally {
            setIsRetrying(false);
        }
    };

    const severity = getErrorSeverity(error);
    const advice = getErrorAdvice(severity);
    const canStillRetry = canRetry && retryCount < maxRetries;

    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="w-full max-w-2xl mx-auto"
        >
            <Card className="border-red-200">
                <CardHeader>
                    <CardTitle className="flex items-center space-x-2 text-red-800">
                        <AlertTriangle className="h-5 w-5" />
                        <span>記事生成でエラーが発生しました</span>
                    </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                    {/* エラー情報 */}
                    <Alert className="border-red-200 bg-red-50">
                        <AlertTriangle className="h-4 w-4 text-red-600" />
                        <AlertDescription className="text-red-800">
                            <div className="space-y-2">
                                <div>
                                    <strong>発生ステップ:</strong> {getStepDisplayName(currentStep)}
                                </div>
                                <div>
                                    <strong>エラー内容:</strong> {error}
                                </div>
                                {processId && (
                                    <div>
                                        <strong>プロセスID:</strong> {processId.slice(0, 8)}...
                                    </div>
                                )}
                            </div>
                        </AlertDescription>
                    </Alert>

                    {/* アドバイス */}
                    <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                        <div className="flex items-start space-x-2">
                            <HelpCircle className="h-5 w-5 text-blue-600 mt-0.5 flex-shrink-0" />
                            <div>
                                <h4 className="font-medium text-blue-900 mb-1">推奨される対処法</h4>
                                <p className="text-blue-800 text-sm">{advice}</p>
                            </div>
                        </div>
                    </div>

                    {/* リトライ情報 */}
                    {retryCount > 0 && (
                        <div className="bg-gray-50 border border-gray-200 rounded-lg p-3">
                            <p className="text-sm text-gray-700">
                                <strong>再試行回数:</strong> {retryCount} / {maxRetries}
                            </p>
                        </div>
                    )}

                    {/* アクションボタン */}
                    <div className="flex space-x-3">
                        {canStillRetry && (
                            <Button
                                onClick={handleRetry}
                                disabled={isRetrying}
                                className="flex items-center space-x-2"
                            >
                                <RotateCcw className={`h-4 w-4 ${isRetrying ? 'animate-spin' : ''}`} />
                                <span>再試行</span>
                            </Button>
                        )}
                        
                        <Button
                            variant="outline"
                            onClick={onRestart}
                            className="flex items-center space-x-2"
                        >
                            <RotateCcw className="h-4 w-4" />
                            <span>新規作成</span>
                        </Button>

                        {onContactSupport && (
                            <Button
                                variant="ghost"
                                onClick={onContactSupport}
                                className="flex items-center space-x-2"
                            >
                                <ExternalLink className="h-4 w-4" />
                                <span>サポートに連絡</span>
                            </Button>
                        )}
                    </div>

                    {/* 詳細情報 */}
                    <Collapsible open={showDetails} onOpenChange={setShowDetails}>
                        <CollapsibleTrigger asChild>
                            <Button variant="ghost" size="sm" className="w-full">
                                <Bug className="h-4 w-4 mr-2" />
                                {showDetails ? '技術詳細を非表示' : '技術詳細を表示'}
                            </Button>
                        </CollapsibleTrigger>
                        <CollapsibleContent className="mt-3">
                            <div className="bg-gray-100 border rounded-lg p-3">
                                <div className="space-y-2 text-sm">
                                    <div>
                                        <strong>タイムスタンプ:</strong> {new Date().toLocaleString()}
                                    </div>
                                    <div>
                                        <strong>エラータイプ:</strong> {severity}
                                    </div>
                                    <div>
                                        <strong>ユーザーエージェント:</strong> {navigator.userAgent}
                                    </div>
                                    {processId && (
                                        <div>
                                            <strong>完全プロセスID:</strong> {processId}
                                        </div>
                                    )}
                                    <div>
                                        <strong>現在URL:</strong> {window.location.href}
                                    </div>
                                </div>
                            </div>
                        </CollapsibleContent>
                    </Collapsible>

                    {/* 最大リトライ到達の警告 */}
                    {!canStillRetry && retryCount >= maxRetries && (
                        <Alert className="border-orange-200 bg-orange-50">
                            <AlertTriangle className="h-4 w-4 text-orange-600" />
                            <AlertDescription className="text-orange-800">
                                最大再試行回数に達しました。問題が解決しない場合は、新規作成するかサポートにお問い合わせください。
                            </AlertDescription>
                        </Alert>
                    )}
                </CardContent>
            </Card>
        </motion.div>
    );
}