'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Clock, 
  Play, 
  AlertCircle, 
  CheckCircle, 
  XCircle, 
  RotateCcw,
  User,
  Target,
  Calendar,
  TrendingUp
} from 'lucide-react';

import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { ScrollArea } from '@/components/ui/scroll-area';

import { RecoverableProcess } from '@/hooks/useRecoverableProcesses';

interface RecoverableProcessesDialogProps {
  processes: RecoverableProcess[];
  isOpen: boolean;
  onResume: (processId: string) => void;
  onStartNew: () => void;
  onClose: () => void;
  isLoading?: boolean;
}

export default function RecoverableProcessesDialog({
  processes,
  isOpen,
  onResume,
  onStartNew,
  onClose,
  isLoading = false
}: RecoverableProcessesDialogProps) {
  const [selectedProcessId, setSelectedProcessId] = useState<string | null>(null);

  if (!isOpen || processes.length === 0) return null;

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'bg-green-100 text-green-800';
      case 'error': return 'bg-red-100 text-red-800';
      case 'user_input_required': return 'bg-blue-100 text-blue-800';
      case 'disconnected': return 'bg-yellow-100 text-yellow-800';
      case 'in_progress': return 'bg-orange-100 text-orange-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getStepDisplayName = (step: string) => {
    const stepNames: Record<string, string> = {
      'keyword_analyzing': 'キーワード分析',
      'keyword_analyzed': 'キーワード分析完了',
      'persona_generating': 'ペルソナ生成',
      'persona_generated': 'ペルソナ選択待ち',
      'theme_generating': 'テーマ提案',
      'theme_proposed': 'テーマ選択待ち',
      'research_planning': 'リサーチ計画',
      'research_plan_generated': 'リサーチ計画承認待ち',
      'researching': 'リサーチ実行',
      'research_synthesizing': 'リサーチ統合',
      'outline_generating': 'アウトライン作成',
      'outline_generated': 'アウトライン承認待ち',
      'writing_sections': '記事執筆',
      'editing': '編集・校正',
    };
    return stepNames[step] || step;
  };

  const formatTimeAgo = (seconds: number) => {
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);

    if (days > 0) return `${days}日前`;
    if (hours > 0) return `${hours}時間前`;
    if (minutes > 0) return `${minutes}分前`;
    return '数秒前';
  };

  const selectedProcess = processes.find(p => p.id === selectedProcessId);

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
          className="w-full max-w-2xl max-h-[90vh] flex flex-col"
        >
          <Card className="flex-1 overflow-hidden">
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <Clock className="h-5 w-5 text-blue-600" />
                <span>復帰可能なプロセスが見つかりました</span>
              </CardTitle>
              <p className="text-sm text-gray-600">
                {processes.length}件の復帰可能なプロセスがあります。続行するプロセスを選択してください。
              </p>
            </CardHeader>
            
            <CardContent className="flex-1 overflow-hidden space-y-4">
              {/* プロセス一覧 */}
              <ScrollArea className="h-64 pr-4">
                <div className="space-y-3">
                  {processes.map((process) => (
                    <motion.div
                      key={process.id}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      className={`border rounded-lg p-4 cursor-pointer transition-all ${
                        selectedProcessId === process.id
                          ? 'border-blue-500 bg-blue-50'
                          : 'border-gray-200 hover:border-gray-300'
                      }`}
                      onClick={() => setSelectedProcessId(process.id)}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1 space-y-2">
                          {/* プロセス基本情報 */}
                          <div className="flex items-center justify-between">
                            <div className="flex items-center space-x-2">
                              <Badge className={getStatusColor(process.status)}>
                                {process.status}
                              </Badge>
                              {process.auto_resume_possible && (
                                <Badge variant="outline" className="text-green-600 border-green-600">
                                  自動復帰可能
                                </Badge>
                              )}
                            </div>
                            <span className="text-xs text-gray-500">
                              {formatTimeAgo(process.time_since_last_activity)}
                            </span>
                          </div>

                          {/* キーワードと進捗 */}
                          <div className="flex items-center space-x-4 text-sm text-gray-600">
                            <div className="flex items-center space-x-1">
                              <Target className="h-3 w-3" />
                              <span>
                                {process.initial_keywords?.slice(0, 3).join(', ') || 'キーワード未設定'}
                                {process.initial_keywords && process.initial_keywords.length > 3 && '...'}
                              </span>
                            </div>
                            <div className="flex items-center space-x-1">
                              <TrendingUp className="h-3 w-3" />
                              <span>{process.progress_percentage}%</span>
                            </div>
                          </div>

                          {/* 現在のステップ */}
                          <div className="flex items-center space-x-2">
                            <span className="text-sm font-medium">
                              現在のステップ: {getStepDisplayName(process.current_step_name)}
                            </span>
                          </div>

                          {/* エラーメッセージ */}
                          {process.error_message && (
                            <div className="flex items-center space-x-2 text-red-600 text-sm">
                              <AlertCircle className="h-3 w-3" />
                              <span className="truncate">{process.error_message}</span>
                            </div>
                          )}
                        </div>

                        {/* 選択インジケーター */}
                        <div className="ml-4">
                          {selectedProcessId === process.id && (
                            <CheckCircle className="h-5 w-5 text-blue-600" />
                          )}
                        </div>
                      </div>
                    </motion.div>
                  ))}
                </div>
              </ScrollArea>

              {/* 選択されたプロセスの詳細 */}
              {selectedProcess && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  exit={{ opacity: 0, height: 0 }}
                >
                  <Separator />
                  <div className="bg-gray-50 p-4 rounded-lg space-y-3">
                    <h4 className="font-medium text-gray-900">プロセス詳細</h4>
                    
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <span className="text-gray-600">プロセスID:</span>
                        <span className="ml-2 font-mono">{selectedProcess.id.slice(0, 8)}...</span>
                      </div>
                      <div>
                        <span className="text-gray-600">作成日時:</span>
                        <span className="ml-2">
                          {new Date(selectedProcess.created_at).toLocaleDateString('ja-JP')}
                        </span>
                      </div>
                      {selectedProcess.target_age_group && (
                        <div>
                          <span className="text-gray-600">ターゲット年代:</span>
                          <span className="ml-2">{selectedProcess.target_age_group}</span>
                        </div>
                      )}
                      {selectedProcess.target_length && (
                        <div>
                          <span className="text-gray-600">目標文字数:</span>
                          <span className="ml-2">{selectedProcess.target_length.toLocaleString()}文字</span>
                        </div>
                      )}
                    </div>

                    {/* 復帰ガイダンス */}
                    {selectedProcess.recovery_notes && (
                      <Alert className="border-blue-200 bg-blue-50">
                        <AlertCircle className="h-4 w-4 text-blue-600" />
                        <AlertDescription className="text-blue-800 text-sm">
                          {selectedProcess.recovery_notes}
                        </AlertDescription>
                      </Alert>
                    )}
                  </div>
                </motion.div>
              )}

              {/* アクションボタン */}
              <div className="flex space-x-3 pt-4">
                <Button
                  onClick={() => selectedProcessId && onResume(selectedProcessId)}
                  disabled={!selectedProcessId || isLoading}
                  className="flex-1 flex items-center justify-center space-x-2"
                >
                  <Play className="h-4 w-4" />
                  <span>選択したプロセスを再開</span>
                </Button>
                
                <Button
                  variant="outline"
                  onClick={onStartNew}
                  disabled={isLoading}
                  className="flex items-center space-x-2"
                >
                  <RotateCcw className="h-4 w-4" />
                  <span>新規作成</span>
                </Button>
              </div>

              <Button
                variant="ghost"
                onClick={onClose}
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