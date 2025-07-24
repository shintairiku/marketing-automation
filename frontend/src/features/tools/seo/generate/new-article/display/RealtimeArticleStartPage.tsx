'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import { AlertCircle, Loader2, Zap } from 'lucide-react';

import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useUser } from '@clerk/nextjs';

import ExplainDialog from "./ExplainDialog";
import InputSection from "./InputSection";

export default function RealtimeArticleStartPage() {
    const { user } = useUser();
    const router = useRouter();
    const [isCreating, setIsCreating] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleStartGeneration = async (requestData: any) => {
        if (!user?.id) {
            setError('ユーザー認証が必要です');
            return;
        }

        setIsCreating(true);
        setError(null);

        try {
            // Use Supabase Realtime-based generation
            const response = await fetch('/api/articles/realtime/generate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    initial_keywords: requestData.initial_keywords || [],
                    image_mode: requestData.image_mode || false,
                    article_style: requestData.article_style || 'informative',
                    theme_count: requestData.theme_count || 3,
                    target_audience: requestData.target_audience || '',
                    persona: requestData.persona || '',
                    company_info: requestData.company_info,
                    article_length: requestData.article_length,
                    research_query_count: requestData.research_query_count,
                    persona_count: requestData.persona_count,
                }),
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || '記事生成の開始に失敗しました');
            }

            const { process_id } = await response.json();
            
            // Redirect to realtime generation process page
            router.push(`/tools/seo/generate/realtime-article/${process_id}`);
        } catch (err) {
            console.error('Error creating generation process:', err);
            setError(err instanceof Error ? err.message : '記事生成プロセスの作成に失敗しました');
        } finally {
            setIsCreating(false);
        }
    };

    return (
        <div className="w-full max-w-7xl mx-auto space-y-6 p-4 min-h-screen">
            {/* タイトルセクション */}
            <motion.div
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
                className="text-center space-y-4"
            >
                <div className="flex items-center justify-center gap-3">
                    <Zap className="w-8 h-8 text-blue-600" />
                    <h1 className="text-3xl font-bold text-gray-900">
                        Realtime SEO記事生成
                    </h1>
                    <Badge variant="secondary" className="bg-blue-100 text-blue-800">
                        Beta
                    </Badge>
                </div>
                <p className="text-lg text-gray-600">
                    Supabase Realtimeを活用した新しい記事生成システム
                </p>
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 max-w-2xl mx-auto">
                    <h3 className="font-semibold text-blue-900 mb-2">新機能の特徴</h3>
                    <ul className="text-sm text-blue-800 space-y-1 text-left">
                        <li>• リアルタイムでの進捗同期</li>
                        <li>• 接続切断による処理中断の回避</li>
                        <li>• 複数タブでの同時監視対応</li>
                        <li>• 堅牢なエラーハンドリング</li>
                        <li>• Cloud Tasksによるバックグラウンド処理</li>
                    </ul>
                </div>
            </motion.div>

            {/* エラー表示 */}
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

            <ExplainDialog />
            
            {/* 入力セクション */}
            <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
            >
                <InputSection 
                    onStartGeneration={handleStartGeneration}
                    isConnected={true} // Always true for start page
                    isLoading={isCreating}
                />
            </motion.div>

            {/* 読み込み中の表示 */}
            {isCreating && (
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
                >
                    <div className="bg-white rounded-lg p-6 max-w-sm mx-4 text-center">
                        <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4 text-blue-600" />
                        <h3 className="text-lg font-semibold mb-2">記事生成を開始しています</h3>
                        <p className="text-gray-600 text-sm">
                            Supabase Realtimeでの進捗監視ページに移動します...
                        </p>
                    </div>
                </motion.div>
            )}

            {/* フッター */}
            <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="text-center text-sm text-gray-500 border-t pt-6"
            >
                <p>
                    従来のWebSocket版は{' '}
                    <button
                        onClick={() => router.push('/seo/generate/new-article')}
                        className="text-blue-600 hover:underline"
                    >
                        こちら
                    </button>
                    {' '}からご利用いただけます
                </p>
            </motion.div>
        </div>
    );
}