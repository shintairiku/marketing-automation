'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { AnimatePresence, motion } from 'framer-motion';
import { AlertCircle, ArrowLeft,CheckCircle } from 'lucide-react';

import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { useArticleGenerationRealtime } from '@/hooks/useArticleGenerationRealtime';
import { useUser } from '@clerk/nextjs';

import CompactGenerationFlow from "../component/CompactGenerationFlow";
import CompactUserInteraction from "../component/CompactUserInteraction";
import ErrorRecoveryActions from "../component/ErrorRecoveryActions";
import GenerationErrorHandler from "../component/GenerationErrorHandler";
import ProcessRecoveryDialog from "../component/ProcessRecoveryDialog";

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
        pauseGeneration,
        resumeGeneration,
        cancelGeneration,
    } = useArticleGenerationRealtime({
        processId: jobId,
        userId: user?.id,
    });

    // プロセス状態の読み込み
    useEffect(() => {
        const loadProcess = async () => {
            if (!user?.id || !jobId) return;
            
            setIsLoading(true);
            try {
                // プロセス情報を直接取得（新しいAPIエンドポイントを使用）
                const response = await fetch(`/api/proxy/articles/generation/${jobId}`, {
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    credentials: 'include',
                });
                
                if (!response.ok) {
                    router.push('/seo/generate/new-article');
                    return;
                }

                const processData = await response.json();
                console.log('📥 Process data loaded:', processData);
                
                // Debug article_context structure for outline debugging
                if (processData.article_context) {
                    console.log('🔍 Article context keys:', Object.keys(processData.article_context));
                    console.log('🔍 Article context outline:', processData.article_context.outline);
                    console.log('🔍 Article context research_plan:', processData.article_context.research_plan);
                    console.log('🔍 Current step name:', processData.current_step_name);
                    console.log('🔍 Status:', processData.status);
                    console.log('🔍 Process metadata:', processData.process_metadata);
                }
                
                // 復帰可能かチェック
                if (processData.can_resume && 
                    ['user_input_required', 'paused', 'error'].includes(processData.status)) {
                    setRecoveryInfo({
                        can_resume: processData.can_resume,
                        resume_step: processData.current_step || processData.status,
                        current_data: processData.context,
                        waiting_for_input: processData.is_waiting_for_input,
                        input_type: processData.input_type,
                        last_activity: processData.updated_at,
                        status: processData.status,
                        error_message: processData.error_message,
                    });
                    setShowRecoveryDialog(true);
                }
                
                // Supabase Realtime接続は自動的に開始される（useArticleGenerationRealtimeのautoConnect=true）
                
            } catch (err) {
                console.error('Error loading process:', err);
                router.push('/seo/generate/new-article');
            } finally {
                setIsLoading(false);
            }
        };

        loadProcess();
    }, [user?.id, jobId, router]);

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
        } else if (state.currentStep === 'error' || state.error || state.steps.some((step: any) => step.status === 'error')) {
            messages.push('記事生成中にエラーが発生しました。再試行してください。');
        } else if (state.currentStep === 'completed') {
            messages.push('記事生成が完了しました！');
        }
        
        setThinkingMessages(messages);
    }, [state.currentStep, state.researchProgress, state.sectionsProgress, state.steps, state.error]);

    // 生成完了後に編集ページへ遷移（エラー状態でない場合のみ）
    useEffect(() => {
        if (state.currentStep === 'completed' && state.articleId && !state.error && !state.steps.some((step: any) => step.status === 'error')) {
            const timer = setTimeout(() => {
                router.push(`/seo/generate/edit-article/${state.articleId}`);
            }, 2000);
            return () => clearTimeout(timer);
        }
    }, [state.currentStep, state.articleId, state.error, state.steps, router]);

    const getProgressPercentage = () => {
        // ユーザー入力待ちの場合は、実際の進捗を計算
        if (state.isWaitingForInput) {
            // ユーザー入力待ちステップごとの進捗を定義
            const inputStepProgress = {
                'persona_generated': 20,    // ペルソナ生成完了 -> 20%
                'theme_proposed': 25,       // テーマ提案完了 -> 25%
                'research_plan_generated': 40, // リサーチ計画完了 -> 40%
                'outline_generated': 65,    // アウトライン完了 -> 65%
            };
            
            return inputStepProgress[state.currentStep as keyof typeof inputStepProgress] || 0;
        }
        
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
        
        // 各ステップの進捗を手動で定義
        const stepProgressMap = {
            'start': 0,
            'keyword_analyzing': 5,
            'keyword_analyzed': 10,
            'persona_generating': 15,
            'persona_generated': 20,
            'theme_generating': 20,
            'theme_proposed': 25,
            'research_planning': 30,
            'research_plan_generated': 40,
            'researching': 50,
            'research_synthesizing': 60,
            'outline_generating': 60,
            'outline_generated': 65,
            'writing_sections': 80,
            'editing': 90,
            'completed': 100
        };
        
        return stepProgressMap[state.currentStep as keyof typeof stepProgressMap] || 0;
    };

    const isGenerating = state.currentStep !== 'start' && state.currentStep !== 'completed' && state.currentStep !== 'error';

    // 復帰ダイアログのハンドラー
    const handleResume = async () => {
        // ローディング状態を表示
        setThinkingMessages(['プロセスを復帰中...']);
        setShowRecoveryDialog(false);
        
        try {
            // Supabase Realtimeが自動的に状態を同期するため、接続を確認するだけ
            if (!isConnected && !isConnecting) {
                connect();
            }
            
            // 復帰成功をユーザーに示す
            setThinkingMessages(['プロセスが正常に復帰されました。リアルタイム更新を開始します。']);
            
            // 2秒後に通常の状態表示に戻す
            setTimeout(() => {
                setThinkingMessages([]);
            }, 2000);
            
        } catch (err) {
            console.error('Resume error:', err);
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
            if (!isConnected && !isConnecting) {
                // Supabase Realtime接続を再試行
                connect();
            } else {
                // 既に接続済みの場合、プロセス再開APIを呼び出し
                if (resumeGeneration) {
                    await resumeGeneration();
                }
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
                            imageMode={state.imageMode}
                            imagePlaceholders={state.imagePlaceholders}
                            completedSections={state.completedSections}
                        />

                        {/* ユーザーインタラクション */}
                        <AnimatePresence>
                            {state.isWaitingForInput && (
                                <motion.div
                                    initial={{ opacity: 0, y: 20 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    exit={{ opacity: 0, y: -20 }}
                                >
                                    {(() => {
                                        console.log('🎭 CompactUserInteraction props:', {
                                            type: state.inputType,
                                            hasPersonas: !!state.personas,
                                            hasThemes: !!state.themes,
                                            hasResearchPlan: !!state.researchPlan,
                                            hasOutline: !!state.outline,
                                            outlineContent: state.outline,
                                            isWaitingForInput: state.isWaitingForInput
                                        });
                                        return null;
                                    })()}
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
                                        onRegenerate={() => {
                                            // TODO: Implement regenerate with HTTP API
                                            console.log('Regenerate not yet implemented for Supabase Realtime');
                                        }}
                                        onEditAndProceed={(editedContent) => {
                                            // TODO: Implement editAndProceed with HTTP API
                                            console.log('EditAndProceed not yet implemented for Supabase Realtime', { editedContent, inputType: state.inputType });
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