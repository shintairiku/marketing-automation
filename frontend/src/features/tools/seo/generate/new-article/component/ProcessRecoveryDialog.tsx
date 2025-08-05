'use client';

import { useEffect, useState } from 'react';
import { AnimatePresence,motion } from 'framer-motion';
import { AlertCircle, CheckCircle, Clock, Play,RotateCcw, XCircle } from 'lucide-react';

import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface ProcessRecoveryDialogProps {
    processId: string;
    recoveryInfo?: {
        can_resume: boolean;
        resume_step: string;
        current_data: any;
        waiting_for_input: boolean;
        input_type: string;
        last_activity: string;
        status: string;
        error_message?: string;
    };
    onResume: () => void;
    onRestart: () => void;
    onCancel: () => void;
    isLoading?: boolean;
}

export default function ProcessRecoveryDialog({
    processId,
    recoveryInfo,
    onResume,
    onRestart,
    onCancel,
    isLoading = false
}: ProcessRecoveryDialogProps) {
    const [showDialog, setShowDialog] = useState(false);

    useEffect(() => {
        if (recoveryInfo) {
            setShowDialog(true);
        }
    }, [recoveryInfo]);

    if (!showDialog || !recoveryInfo) return null;

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'completed': return 'bg-green-100 text-green-800';
            case 'error': return 'bg-red-100 text-red-800';
            case 'user_input_required': return 'bg-blue-100 text-blue-800';
            case 'paused': return 'bg-yellow-100 text-yellow-800';
            case 'in_progress': return 'bg-orange-100 text-orange-800';
            default: return 'bg-gray-100 text-gray-800';
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

    const getLastActivityTimeAgo = (lastActivity: string) => {
        const now = new Date();
        const last = new Date(lastActivity);
        const diffMs = now.getTime() - last.getTime();
        const diffMins = Math.floor(diffMs / (1000 * 60));
        const diffHours = Math.floor(diffMins / 60);
        const diffDays = Math.floor(diffHours / 24);

        if (diffDays > 0) return `${diffDays}日前`;
        if (diffHours > 0) return `${diffHours}時間前`;
        if (diffMins > 0) return `${diffMins}分前`;
        return '数秒前';
    };

    return (
        <AnimatePresence>
            <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
            >
                <motion.div
                    initial={{ scale: 0.9, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    exit={{ scale: 0.9, opacity: 0 }}
                    className="w-full max-w-md"
                >
                    <Card>
                        <CardHeader>
                            <CardTitle className="flex items-center space-x-2">
                                <Clock className="h-5 w-5 text-blue-600" />
                                <span>進行中のプロセスが見つかりました</span>
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            {/* プロセス情報 */}
                            <div className="space-y-2">
                                <div className="flex items-center justify-between">
                                    <span className="text-sm text-gray-600">プロセスID:</span>
                                    <span className="text-sm font-mono">{processId.slice(0, 8)}...</span>
                                </div>
                                <div className="flex items-center justify-between">
                                    <span className="text-sm text-gray-600">ステータス:</span>
                                    <Badge className={getStatusColor(recoveryInfo.status)}>
                                        {recoveryInfo.status}
                                    </Badge>
                                </div>
                                <div className="flex items-center justify-between">
                                    <span className="text-sm text-gray-600">現在のステップ:</span>
                                    <span className="text-sm font-medium">
                                        {getStepDisplayName(recoveryInfo.resume_step)}
                                    </span>
                                </div>
                                <div className="flex items-center justify-between">
                                    <span className="text-sm text-gray-600">最終活動:</span>
                                    <span className="text-sm text-gray-800">
                                        {getLastActivityTimeAgo(recoveryInfo.last_activity)}
                                    </span>
                                </div>
                            </div>

                            {/* エラー表示 */}
                            {recoveryInfo.error_message && (
                                <Alert className="border-red-200 bg-red-50">
                                    <AlertCircle className="h-4 w-4 text-red-600" />
                                    <AlertDescription className="text-red-800 text-sm">
                                        エラー: {recoveryInfo.error_message}
                                    </AlertDescription>
                                </Alert>
                            )}

                            {/* ユーザー入力待ち状態 */}
                            {recoveryInfo.waiting_for_input && (
                                <Alert className="border-blue-200 bg-blue-50">
                                    <CheckCircle className="h-4 w-4 text-blue-600" />
                                    <AlertDescription className="text-blue-800 text-sm">
                                        ユーザーの入力待ち状態です。続行すると前回の状態から再開されます。
                                    </AlertDescription>
                                </Alert>
                            )}

                            {/* 復帰可能性の説明 */}
                            <div className="bg-gray-50 p-3 rounded-lg">
                                <p className="text-sm text-gray-700">
                                    {recoveryInfo.can_resume ? (
                                        <>
                                            <CheckCircle className="inline h-4 w-4 text-green-600 mr-1" />
                                            このプロセスは前回の状態から再開できます。
                                        </>
                                    ) : (
                                        <>
                                            <XCircle className="inline h-4 w-4 text-red-600 mr-1" />
                                            このプロセスは新しく開始する必要があります。
                                        </>
                                    )}
                                </p>
                            </div>

                            {/* アクションボタン */}
                            <div className="flex space-x-2 pt-2">
                                {recoveryInfo.can_resume && (
                                    <Button
                                        onClick={() => {
                                            setShowDialog(false);
                                            onResume();
                                        }}
                                        disabled={isLoading}
                                        className="flex-1 flex items-center justify-center space-x-2"
                                    >
                                        <Play className="h-4 w-4" />
                                        <span>続きから再開</span>
                                    </Button>
                                )}
                                <Button
                                    variant="outline"
                                    onClick={() => {
                                        setShowDialog(false);
                                        onRestart();
                                    }}
                                    disabled={isLoading}
                                    className="flex-1 flex items-center justify-center space-x-2"
                                >
                                    <RotateCcw className="h-4 w-4" />
                                    <span>新規作成</span>
                                </Button>
                            </div>

                            <Button
                                variant="ghost"
                                onClick={() => {
                                    setShowDialog(false);
                                    onCancel();
                                }}
                                disabled={isLoading}
                                className="w-full"
                            >
                                キャンセル
                            </Button>
                        </CardContent>
                    </Card>
                </motion.div>
            </motion.div>
        </AnimatePresence>
    );
}