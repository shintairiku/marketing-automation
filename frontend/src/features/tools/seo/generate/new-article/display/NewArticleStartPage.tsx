'use client';

import { useEffect,useState } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import { AlertCircle, Loader2 } from 'lucide-react';

import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { useAuth, useUser } from '@clerk/nextjs';

import ExplainDialog from "./ExplainDialog";
import InputSection from "./InputSection";

export default function NewArticleStartPage() {
    const { user } = useUser();
    const { getToken } = useAuth();
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
            console.log('📦 Request data being sent:', requestData);
            
            // Start generation process using the correct API endpoint
            const response = await fetch('/api/proxy/articles/generation/start', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${await getToken()}`,
                },
                body: JSON.stringify({
                    ...requestData,
                    user_id: user.id,
                }),
            });

            if (!response.ok) {
                throw new Error('記事生成プロセスの開始に失敗しました');
            }

            const { process_id } = await response.json();
            console.log('✅ Generation process started with ID:', process_id);
            
            // Redirect to generation process page
            router.push(`/seo/generate/new-article/${process_id}`);
        } catch (err) {
            console.error('Error starting generation process:', err);
            setError(err instanceof Error ? err.message : '記事生成プロセスの開始に失敗しました');
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
                <h1 className="text-3xl font-bold text-gray-900 font-sans">
                    新規SEO記事作成
                </h1>
                <p className="text-lg text-gray-600">
                    AI を活用して高品質なSEO記事を自動生成します。*マークは必須項目です。
                </p>
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
                    isGenerating={isCreating}
                />
            </motion.div>

            {/* ローディング状態 */}
            {isCreating && (
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
                >
                    <div className="bg-white p-6 rounded-lg shadow-lg flex items-center space-x-3">
                        <Loader2 className="h-6 w-6 animate-spin text-blue-600" />
                        <span className="text-lg font-medium">記事生成プロセスを開始しています...</span>
                    </div>
                </motion.div>
            )}

        </div>
    );
}