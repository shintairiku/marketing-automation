'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { AnimatePresence,motion } from 'framer-motion';
import { AlertCircle, CheckCircle, Wifi, WifiOff } from 'lucide-react';

import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { useUser } from '@clerk/nextjs';

import CompactGenerationFlow from "../component/CompactGenerationFlow";
import CompactUserInteraction from "../component/CompactUserInteraction";
import GenerationErrorHandler from "../component/GenerationErrorHandler";
import { useArticleGenerationRealtime } from '@/hooks/useArticleGenerationRealtime';

import ExplainDialog from "./ExplainDialog";
import InputSection from "./InputSection";

export default function IndexPage() {
    const { user } = useUser();
    const router = useRouter();
    const [thinkingMessages, setThinkingMessages] = useState<string[]>([]);

    
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
        userId: user?.id,
        autoConnect: true,
    });

    // Supabase Realtime接続は自動で開始される（autoConnect: true）
    // useEffectでの手動接続は不要

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
        } else if (state.currentStep === 'completed') {
            messages.push('記事生成が完了しました！');
        } else if (state.currentStep === 'error' || state.steps.some((step: any) => step.status === 'error')) {
            messages.push('記事生成中にエラーが発生しました。再試行してください。');
        }
        
        setThinkingMessages(messages);
    }, [state.currentStep, state.researchProgress, state.sectionsProgress, state.steps]);

    // 生成完了後に編集ページへ遷移
    useEffect(() => {
        if (state.currentStep === 'completed' && state.articleId) {
            // 2 秒後に自動遷移（完了アニメーションが出る場合を考慮）
            const timer = setTimeout(() => {
                router.push(`/seo/generate/edit-article/${state.articleId}`);
            }, 2000);
            return () => clearTimeout(timer);
        }
    }, [state.currentStep, state.articleId, router]);

    const handleStartGeneration = (requestData: any) => {
        startArticleGeneration(requestData);
    };

    const getProgressPercentage = () => {
        // 8つのステップに基づく進捗計算
        const stepProgressMap = {
            'keyword_analyzing': 12.5,      // キーワード分析: 12.5%
            'persona_generating': 25,       // ペルソナ生成: 25%
            'theme_generating': 37.5,       // テーマ提案: 37.5%
            'research_planning': 50,        // リサーチ計画: 50%
            'researching': 62.5,            // リサーチ実行（リサーチ要約）: 62.5%
            'outline_generating': 75,       // アウトライン作成: 75%
            'writing_sections': 87.5,       // 執筆: 87.5%
            'editing': 100,                 // 編集・校正: 100%
        };
        
        // ユーザー入力待ちの場合は、現在のステップの進捗を返す
        const progress = stepProgressMap[state.currentStep as keyof typeof stepProgressMap];
        if (progress !== undefined) {
            return progress;
        }
        
        // フォールバック: ステップ配列から計算
        const currentStepIndex = state.steps.findIndex((step: any) => step.id === state.currentStep);
        if (currentStepIndex === -1) return 0;
        
        return ((currentStepIndex + 1) / state.steps.length) * 100;
    };

    const isGenerating = state.currentStep !== 'completed' && state.currentStep !== 'error';

    return (
        <div className="w-full max-w-7xl mx-auto space-y-6 p-4 min-h-screen">
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
                                Supabase Realtimeに接続されています
                            </AlertDescription></>
                        ) : (
                            <><WifiOff className="h-4 w-4 text-red-600" />
                            <AlertDescription className="text-red-800">
                                Supabase Realtimeに接続できません
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

            <ExplainDialog />
            
            {/* 入力セクション */}
            <AnimatePresence>
                {state.currentStep === 'start' && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                    >
                        <InputSection 
                            onStartGeneration={handleStartGeneration}
                            isConnected={isConnected}
                            isGenerating={isGenerating}
                        />
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
                        <GenerationErrorHandler
                            error={state.error}
                            currentStep={state.currentStep}
                            onRetry={() => {
                                // 前回の入力データで再試行
                                window.location.reload();
                            }}
                            onCancel={() => {
                                // 最初の状態に戻る
                                window.location.reload();
                            }}
                        />
                    </motion.div>
                )}
            </AnimatePresence>


        </div>
    );
}