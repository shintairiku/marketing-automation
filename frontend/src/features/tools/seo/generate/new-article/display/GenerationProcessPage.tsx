'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { AnimatePresence, motion } from 'framer-motion';
import { AlertCircle, CheckCircle, Wifi, WifiOff, ArrowLeft } from 'lucide-react';

import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { useUser } from '@clerk/nextjs';

import CompactGenerationFlow from "../component/CompactGenerationFlow";
import CompactUserInteraction from "../component/CompactUserInteraction";
import GenerationErrorHandler from "../component/GenerationErrorHandler";
import ProcessRecoveryDialog from "../component/ProcessRecoveryDialog";
import ErrorRecoveryActions from "../component/ErrorRecoveryActions";
import { useArticleGeneration } from '../hooks/useArticleGeneration';

interface GenerationProcessPageProps {
    jobId: string;
}

export default function GenerationProcessPage({ jobId }: GenerationProcessPageProps) {
    const { user } = useUser();
    const router = useRouter();
    const [thinkingMessages, setThinkingMessages] = useState<string[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [recoveryInfo, setRecoveryInfo] = useState<any>(null);
    const [showRecoveryDialog, setShowRecoveryDialog] = useState(false);
    const [retryCount, setRetryCount] = useState(0);

    const {
        state,
        isConnected,
        isConnecting,
        error,
        connect,
        disconnect,
        startArticleGeneration,
        selectPersona,
        selectTheme,
        approvePlan,
        approveOutline,
        regenerate,
        editAndProceed,
        loadProcessState,
    } = useArticleGeneration({
        processId: jobId,
        userId: user?.id,
    });

    // プロセス状態の読み込み
    useEffect(() => {
        const loadProcess = async () => {
            if (!user?.id || !jobId) return;
            
            setIsLoading(true);
            try {
                // まずプロセス情報を直接取得
                const response = await fetch(`/api/articles/generation/${jobId}`);
                if (!response.ok) {
                    router.push('/seo/generate/new-article');
                    return;
                }

                const processData = await response.json();
                
                // 復帰可能かチェック
                if (processData.recovery_info?.can_resume && 
                    ['user_input_required', 'paused', 'error'].includes(processData.status)) {
                    setRecoveryInfo({
                        can_resume: processData.recovery_info.can_resume,
                        resume_step: processData.current_step_name || processData.status,
                        current_data: processData.generated_content,
                        waiting_for_input: processData.is_waiting_for_input,
                        input_type: processData.input_type,
                        last_activity: processData.last_activity_at,
                        status: processData.status,
                        error_message: processData.error_message,
                    });
                    setShowRecoveryDialog(true);
                    setIsLoading(false);
                    return;
                }

                // 通常の状態読み込み
                const success = await loadProcessState();
                if (!success) {
                    router.push('/seo/generate/new-article');
                    return;
                }
                
                // プロセス状態が読み込まれたら接続を試行
                // しかし、復帰ダイアログが表示される場合があるので条件を確認
                if (processData.status === 'in_progress' && 
                    !['user_input_required', 'paused', 'error'].includes(processData.status)) {
                    setTimeout(() => {
                        connect();
                    }, 100);
                }
            } catch (err) {
                console.error('Error loading process:', err);
                router.push('/seo/generate/new-article');
            } finally {
                setIsLoading(false);
            }
        };

        loadProcess();
    }, [user?.id, jobId, loadProcessState, connect, router]);

    // 思考メッセージの更新
    useEffect(() => {
        const messages = [];
        
        if (state.currentStep === 'keyword_analyzing') {
            messages.push('キーワードを分析し、競合記事を調査しています...');
        } else if (state.currentStep === 'persona_generating') {
            messages.push('ターゲットペルソナの詳細プロファイルを生成しています...');
        } else if (state.currentStep === 'theme_generating') {
            messages.push('SEO効果の高い記事テーマを考案しています...');
        } else if (state.currentStep === 'research_planning') {
            messages.push('記事の信頼性を高めるリサーチ計画を策定しています...');
        } else if (state.currentStep === 'researching') {
            if (state.researchProgress) {
                messages.push(`Web上から最新の情報を収集・分析しています... (${state.researchProgress.currentQuery}/${state.researchProgress.totalQueries})`);
            } else {
                messages.push('Web上から最新の情報を収集・分析しています...');
            }
        } else if (state.currentStep === 'research_synthesizing') {
            messages.push('収集した情報を整理し、記事に活用できる形にまとめています...');
        } else if (state.currentStep === 'outline_generating') {
            messages.push('読者に価値を提供する記事構成を設計しています...');
        } else if (state.currentStep === 'writing_sections') {
            if (state.sectionsProgress) {
                messages.push(`専門性と読みやすさを両立した記事を執筆しています... (${state.sectionsProgress.currentSection}/${state.sectionsProgress.totalSections})`);
            } else {
                messages.push('専門性と読みやすさを両立した記事を執筆しています...');
            }
        } else if (state.currentStep === 'editing') {
            messages.push('記事全体を校正し、最終調整を行っています...');
        } else if (state.currentStep === 'error' || state.error || state.steps.some(step => step.status === 'error')) {
            messages.push('記事生成中にエラーが発生しました。再試行してください。');
        } else if (state.currentStep === 'completed') {
            messages.push('記事生成が完了しました！');
        }
        
        setThinkingMessages(messages);
    }, [state.currentStep, state.researchProgress, state.sectionsProgress, state.steps]);

    // 生成完了後に編集ページへ遷移（エラー状態でない場合のみ）
    useEffect(() => {
        if (state.currentStep === 'completed' && state.articleId && !state.error && !state.steps.some(step => step.status === 'error')) {
            const timer = setTimeout(() => {
                router.push(`/seo/generate/edit-article/${state.articleId}`);
            }, 2000);
            return () => clearTimeout(timer);
        }
    }, [state.currentStep, state.articleId, state.error, state.steps, router]);

    const getProgressPercentage = () => {
        const stepOrder = [
            'start', 'keyword_analyzing', 'keyword_analyzed', 'persona_generating', 'persona_generated',
            'theme_generating', 'theme_proposed', 'research_planning', 'research_plan_generated',
            'researching', 'research_synthesizing', 'outline_generating', 'outline_generated',
            'writing_sections', 'editing', 'completed'
        ];
        
        if (state.currentStep === 'completed') {
            return 100;
        }
        
        const currentStepIndex = stepOrder.indexOf(state.currentStep);
        if (currentStepIndex === -1) return 0;
        
        const completedSteps = state.steps.filter(step => step.status === 'completed').length;
        const inProgressSteps = state.steps.filter(step => step.status === 'in_progress').length;
        
        const totalProgress = completedSteps + (inProgressSteps * 0.5);
        const percentage = Math.round((totalProgress / state.steps.length) * 100);
        
        return state.currentStep === 'completed' ? 100 : Math.min(percentage, 95);
    };

    const isGenerating = state.currentStep !== 'start' && state.currentStep !== 'completed' && state.currentStep !== 'error';

    // 復帰ダイアログのハンドラー
    const handleResume = async () => {
        // ローディング状態を表示
        setThinkingMessages(['プロセスを復帰中...']);
        
        const success = await loadProcessState();
        if (success) {
            // 状態読み込み後にWebSocket接続
            setTimeout(() => {
                connect();
            }, 200);
            
            // 復帰成功をユーザーに示す
            setThinkingMessages(['プロセスが正常に復帰されました。']);
            
            // 2秒後に通常の状態表示に戻す
            setTimeout(() => {
                setThinkingMessages([]);
            }, 2000);
        } else {
            // 読み込み失敗時のエラー表示
            setThinkingMessages(['プロセスの復帰に失敗しました。新規作成をお試しください。']);
        }
    };

    const handleRestart = () => {
        router.push('/seo/generate/new-article');
    };

    const handleCancelRecovery = () => {
        router.push('/seo/generate/new-article');
    };

    // エラー処理のハンドラー
    const handleRetry = async () => {
        setRetryCount(prev => prev + 1);
        try {
            if (isConnected) {
                // WebSocket経由でリトライ
                // TODO: WebSocketにリトライメッセージを送信
            } else {
                // 接続を再試行
                connect();
            }
        } catch (err) {
            console.error('Retry failed:', err);
        }
    };

    const handleRestartFromError = () => {
        router.push('/seo/generate/new-article');
    };

    if (isLoading) {
        return (
            <div className="w-full max-w-7xl mx-auto space-y-6 p-4 min-h-screen flex items-center justify-center">
                <div className="text-center space-y-4">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
                    <p className="text-lg text-gray-600">プロセス情報を読み込んでいます...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="w-full max-w-7xl mx-auto space-y-6 p-4 min-h-screen">
            {/* ヘッダー */}
            <motion.div
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex items-center justify-between"
            >
                <div className="flex items-center space-x-4">
                    <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => router.push('/seo/generate/new-article')}
                        className="flex items-center space-x-2"
                    >
                        <ArrowLeft className="h-4 w-4" />
                        <span>新規作成に戻る</span>
                    </Button>
                    <div className="h-6 w-px bg-gray-300" />
                    <div>
                        <h1 className="text-xl font-semibold text-gray-900">記事生成プロセス</h1>
                        <p className="text-sm text-gray-500">ID: {jobId}</p>
                    </div>
                </div>
            </motion.div>

            {/* 接続状態表示 */}
            <motion.div
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
            >
                <Alert className={isConnected ? 'border-green-200 bg-green-50' : 'border-red-200 bg-red-50'}>
                    <div className="flex items-center gap-2">
                        {isConnected ? (
                            <><Wifi className="h-4 w-4 text-green-600" />
                            <AlertDescription className="text-green-800">
                                サーバーに接続されています
                            </AlertDescription></>
                        ) : (
                            <><WifiOff className="h-4 w-4 text-red-600" />
                            <AlertDescription className="text-red-800">
                                サーバーに接続できません
                                <Button 
                                    variant="ghost" 
                                    size="sm" 
                                    onClick={connect}
                                    className="ml-2 text-red-800 hover:text-red-900"
                                >
                                    再接続
                                </Button>
                            </AlertDescription></>
                        )}
                    </div>
                </Alert>
            </motion.div>

            {/* エラー表示 */}
            <AnimatePresence>
                {error && (
                    <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                    >
                        <Alert className="border-red-200 bg-red-50">
                            <AlertCircle className="h-4 w-4 text-red-600" />
                            <AlertDescription className="text-red-800">
                                {error}
                            </AlertDescription>
                        </Alert>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* メイン生成フロー */}
            <AnimatePresence>
                {state.currentStep !== 'start' && (
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -20 }}
                        className="space-y-6"
                    >
                        {/* コンパクト生成フロー */}
                        <CompactGenerationFlow
                            steps={state.steps}
                            currentStep={state.currentStep}
                            isConnected={isConnected}
                            isGenerating={isGenerating}
                            progressPercentage={getProgressPercentage()}
                            finalArticle={state.finalArticle}
                            currentMessage={thinkingMessages[0]}
                            generatedContent={state.generatedContent}
                            currentSection={state.currentSection}
                            outline={state.outline}
                            researchProgress={state.researchProgress}
                            sectionsProgress={state.sectionsProgress}
                        />

                        {/* ユーザーインタラクション */}
                        <AnimatePresence>
                            {state.isWaitingForInput && (
                                <motion.div
                                    initial={{ opacity: 0, y: 20 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    exit={{ opacity: 0, y: -20 }}
                                >
                                    <CompactUserInteraction
                                        type={state.inputType as any}
                                        personas={state.personas}
                                        themes={state.themes}
                                        researchPlan={state.researchPlan}
                                        outline={state.outline}
                                        onSelect={(index) => {
                                            if (state.inputType === 'select_persona') {
                                                selectPersona(index);
                                            } else if (state.inputType === 'select_theme') {
                                                selectTheme(index);
                                            }
                                        }}
                                        onApprove={(approved) => {
                                            if (state.inputType === 'approve_plan') {
                                                approvePlan(approved);
                                            } else if (state.inputType === 'approve_outline') {
                                                approveOutline(approved);
                                            }
                                        }}
                                        onRegenerate={regenerate}
                                        onEditAndProceed={(editedContent) => {
                                            if (state.inputType) {
                                                editAndProceed(editedContent, state.inputType);
                                            }
                                        }}
                                        isWaiting={false}
                                    />
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* エラー処理 */}
            <AnimatePresence>
                {state.currentStep === 'error' && state.error && (
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -20 }}
                    >
                        <ErrorRecoveryActions
                            error={state.error}
                            currentStep={state.currentStep}
                            processId={jobId}
                            onRetry={handleRetry}
                            onRestart={handleRestartFromError}
                            retryCount={retryCount}
                            maxRetries={3}
                        />
                    </motion.div>
                )}
            </AnimatePresence>

            {/* プロセス復帰ダイアログ */}
            <ProcessRecoveryDialog
                processId={jobId}
                recoveryInfo={recoveryInfo}
                onResume={handleResume}
                onRestart={handleRestart}
                onCancel={handleCancelRecovery}
                isLoading={isLoading}
            />
        </div>
    );
}