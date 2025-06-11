'use client';

import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useUser } from '@clerk/nextjs';

import CompactGenerationFlow from "../component/CompactGenerationFlow";
import CompactUserInteraction from "../component/CompactUserInteraction";
import GenerationErrorHandler from "../component/GenerationErrorHandler";
import InputSection from "./InputSection";
import ExplainDialog from "./ExplainDialog";
import { useArticleGeneration } from '../hooks/useArticleGeneration';
import { Card, CardContent } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { AlertCircle, CheckCircle, Wifi, WifiOff } from 'lucide-react';
import { Button } from '@/components/ui/button';

export default function IndexPage() {
    const { user } = useUser();
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
        regenerate,
        editAndProceed,
    } = useArticleGeneration({
        userId: user?.id,
    });

    // WebSocket接続を自動で開始
    useEffect(() => {
        if (user?.id && !isConnected && !isConnecting) {
            connect();
        }
    }, [user?.id, isConnected, isConnecting, connect]);

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
        } else if (state.currentStep === 'error' || state.steps.some(step => step.status === 'error')) {
            messages.push('記事生成中にエラーが発生しました。再試行してください。');
        }
        
        setThinkingMessages(messages);
    }, [state.currentStep, state.researchProgress, state.sectionsProgress, state.steps]);

    const handleStartGeneration = (requestData: any) => {
        startArticleGeneration(requestData);
    };

    const getProgressPercentage = () => {
        const stepOrder = [
            'start', 'keyword_analyzing', 'keyword_analyzed', 'persona_generating', 'persona_generated',
            'theme_generating', 'theme_proposed', 'research_planning', 'research_plan_generated',
            'researching', 'research_synthesizing', 'outline_generating', 'outline_generated',
            'writing_sections', 'editing', 'completed'
        ];
        
        // 完了状態の場合は100%
        if (state.currentStep === 'completed') {
            return 100;
        }
        
        const currentStepIndex = stepOrder.indexOf(state.currentStep);
        if (currentStepIndex === -1) return 0;
        
        // 完了したステップ数を計算
        const completedSteps = state.steps.filter(step => step.status === 'completed').length;
        const inProgressSteps = state.steps.filter(step => step.status === 'in_progress').length;
        
        // 実行中のステップは50%の重みを付ける
        const totalProgress = completedSteps + (inProgressSteps * 0.5);
        const percentage = Math.round((totalProgress / state.steps.length) * 100);
        
        // 完了前は最大95%まで、完了時は100%
        return state.currentStep === 'completed' ? 100 : Math.min(percentage, 95);
    };

    const isGenerating = state.currentStep !== 'start' && state.currentStep !== 'completed' && state.currentStep !== 'error';

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
                                サーバーに接続されています（開発用）
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