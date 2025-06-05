'use client';

import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useUser } from '@clerk/nextjs';

import AiThinkingBox from "../component/AiThinkingBox";
import GenerationSteps from "../component/GenerationSteps";
import PersonaSelection from "../component/PersonaSelection";
import ThemeSelection from "../component/ThemeSelection";
import ContentGeneration from "../component/ContentGeneration";
import InputSection from "./InputSection";
import ExplainDialog from "./ExplainDialog";
import { useArticleGeneration } from '../hooks/useArticleGeneration';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
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
            messages.push('Web上から最新の情報を収集・分析しています...');
        } else if (state.currentStep === 'research_synthesizing') {
            messages.push('収集した情報を整理し、記事に活用できる形にまとめています...');
        } else if (state.currentStep === 'outline_generating') {
            messages.push('読者に価値を提供する記事構成を設計しています...');
        } else if (state.currentStep === 'writing_sections') {
            messages.push('専門性と読みやすさを両立した記事を執筆しています...');
        } else if (state.currentStep === 'editing') {
            messages.push('記事全体を校正し、最終調整を行っています...');
        }
        
        setThinkingMessages(messages);
    }, [state.currentStep]);

    const handleStartGeneration = (requestData: any) => {
        startArticleGeneration(requestData);
    };

    const getProgressPercentage = () => {
        const completed = state.steps.filter(step => step.status === 'completed').length;
        return Math.round((completed / state.steps.length) * 100);
    };

    return (
        <div className="w-full max-w-7xl mx-auto space-y-8 p-4">
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
                            isGenerating={state.currentStep !== 'start' && state.currentStep !== 'completed' && state.currentStep !== 'error'}
                        />
                    </motion.div>
                )}
            </AnimatePresence>

            {/* 生成ステップ表示 */}
            <AnimatePresence>
                {state.currentStep !== 'start' && (
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -20 }}
                    >
                        <GenerationSteps 
                            steps={state.steps}
                            currentStep={state.currentStep}
                        />
                    </motion.div>
                )}
            </AnimatePresence>

            {/* AI思考過程表示 */}
            <AiThinkingBox 
                messages={thinkingMessages}
                isActive={!state.isWaitingForInput && state.currentStep !== 'start' && state.currentStep !== 'completed' && state.currentStep !== 'error'}
            />

            {/* ペルソナ選択 */}
            <AnimatePresence>
                {state.isWaitingForInput && state.inputType === 'select_persona' && state.personas && (
                    <PersonaSelection
                        personas={state.personas}
                        onSelect={selectPersona}
                        onRegenerate={regenerate}
                        isWaiting={false}
                    />
                )}
            </AnimatePresence>

            {/* テーマ選択 */}
            <AnimatePresence>
                {state.isWaitingForInput && state.inputType === 'select_theme' && state.themes && (
                    <ThemeSelection
                        themes={state.themes}
                        onSelect={selectTheme}
                        onRegenerate={regenerate}
                        isWaiting={false}
                    />
                )}
            </AnimatePresence>

            {/* リサーチ計画承認 */}
            <AnimatePresence>
                {state.isWaitingForInput && state.inputType === 'approve_plan' && state.researchPlan && (
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="w-full max-w-4xl mx-auto"
                    >
                        <Card>
                            <CardHeader>
                                <CardTitle>リサーチ計画の確認</CardTitle>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                <div className="prose prose-sm max-w-none">
                                    <h3>{state.researchPlan.topic}</h3>
                                    <ul>
                                        {state.researchPlan.queries?.map((query: any, index: number) => (
                                            <li key={index}>
                                                <strong>{query.query}</strong> - {query.focus}
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                                <div className="flex gap-4">
                                    <Button onClick={() => approvePlan(true)}>
                                        承認して続行
                                    </Button>
                                    <Button variant="outline" onClick={() => approvePlan(false)}>
                                        再生成
                                    </Button>
                                </div>
                            </CardContent>
                        </Card>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* アウトライン承認 */}
            <AnimatePresence>
                {state.isWaitingForInput && state.inputType === 'approve_outline' && state.outline && (
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="w-full max-w-4xl mx-auto"
                    >
                        <Card>
                            <CardHeader>
                                <CardTitle>アウトラインの確認</CardTitle>
                            </CardHeader>
                            <CardContent className="space-y-4">
                                <div className="space-y-3">
                                    <h3 className="text-lg font-bold">{state.outline.title}</h3>
                                    <p className="text-sm text-gray-600">{state.outline.suggested_tone}</p>
                                    <div className="space-y-2">
                                        {state.outline.sections?.map((section: any, index: number) => (
                                            <div key={index} className="pl-4 border-l-2 border-gray-200">
                                                <h4 className="font-medium">{section.heading}</h4>
                                                {section.estimated_chars && (
                                                    <p className="text-sm text-gray-500">
                                                        約 {section.estimated_chars} 文字
                                                    </p>
                                                )}
                                            </div>
                                        ))}
                                    </div>
                                </div>
                                <div className="flex gap-4">
                                    <Button onClick={() => approveOutline(true)}>
                                        承認して続行
                                    </Button>
                                    <Button variant="outline" onClick={() => approveOutline(false)}>
                                        再生成
                                    </Button>
                                </div>
                            </CardContent>
                        </Card>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* コンテンツ生成表示 */}
            <AnimatePresence>
                {(['outline_generation', 'writing_sections', 'editing'].includes(state.currentStep)) && (
                    <ContentGeneration
                        currentStep={state.currentStep}
                        generatedContent={state.generatedContent}
                        outline={state.outline}
                        progress={getProgressPercentage()}
                    />
                )}
            </AnimatePresence>

            {/* 完成記事表示 */}
            <AnimatePresence>
                {state.finalArticle && (
                    <motion.div
                        initial={{ opacity: 0, scale: 0.95 }}
                        animate={{ opacity: 1, scale: 1 }}
                        className="w-full max-w-4xl mx-auto"
                    >
                        <Card className="border-2 border-green-200 bg-green-50">
                            <CardHeader>
                                <CardTitle className="flex items-center gap-2 text-green-800">
                                    <CheckCircle className="w-6 h-6" />
                                    記事生成完了！
                                </CardTitle>
                            </CardHeader>
                            <CardContent>
                                <div className="space-y-4">
                                    <h2 className="text-2xl font-bold">{state.finalArticle.title}</h2>
                                    <div 
                                        className="prose prose-lg max-w-none"
                                        dangerouslySetInnerHTML={{ __html: state.finalArticle.content }}
                                    />
                                </div>
                            </CardContent>
                        </Card>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    )
}