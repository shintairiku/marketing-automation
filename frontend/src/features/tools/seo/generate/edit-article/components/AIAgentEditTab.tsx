'use client';

import React, { useCallback, useEffect, useRef, useState } from 'react';
import { AlertCircle, Bot, Check, Loader2, Send, X } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Textarea } from '@/components/ui/textarea';
import { useToast } from '@/hooks/use-toast';
import { useAgentChat } from '@/hooks/useAgentChat';

import UnifiedDiffViewer from './UnifiedDiffViewer';

interface AIAgentEditTabProps {
  articleId: string;
  onSave?: () => void;
}

interface UnifiedDiffLine {
  type: 'unchanged' | 'change';
  content?: string;
  line_number?: number;
  change_id?: string;
  old_lines?: string[];
  new_lines?: string[];
  approved?: boolean;
}

export default function AIAgentEditTab({ articleId, onSave }: AIAgentEditTabProps) {
  const {
    messages,
    loading,
    error,
    sessionId,
    createSession,
    sendMessage,
    extractPendingChanges,
    approveChange,
    rejectChange,
    applyApprovedChanges,
    clearPendingChanges,
    getUnifiedDiffView,
    closeSession,
  } = useAgentChat(articleId);

  const { toast } = useToast();
  const [userInput, setUserInput] = useState('');
  const [diffLines, setDiffLines] = useState<UnifiedDiffLine[]>([]);
  const [hasChanges, setHasChanges] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // セッション作成（マウント時のみ）
  useEffect(() => {
    let mounted = true;

    const initSession = async () => {
      if (!sessionId && mounted) {
        try {
          await createSession(articleId);
        } catch (err: any) {
          if (mounted) {
            toast({
              title: 'エラー',
              description: `セッションの作成に失敗しました: ${err.message}`,
              variant: 'destructive',
            });
          }
        }
      }
    };

    initSession();

    return () => {
      mounted = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // アンマウント時のクリーンアップ
  useEffect(() => {
    return () => {
      if (sessionId) {
        closeSession();
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // セッション作成後に記事全体を初期表示
  useEffect(() => {
    const loadInitialArticle = async () => {
      if (sessionId && diffLines.length === 0 && !hasChanges) {
        try {
          const diffView = await getUnifiedDiffView();
          if (diffView.lines) {
            setDiffLines(diffView.lines);
          }
        } catch (err) {
          console.error('Failed to load initial article:', err);
        }
      }
    };

    loadInitialArticle();
  }, [sessionId, diffLines.length, hasChanges, getUnifiedDiffView]);

  // メッセージ自動スクロール
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // 統合差分ビューを更新
  const updateDiffView = useCallback(async () => {
    if (!sessionId) return;

    try {
      const diffView = await getUnifiedDiffView();
      if (diffView.lines) {
        setDiffLines(diffView.lines);
        setHasChanges(diffView.has_changes || false);
      }
    } catch (err) {
      console.error('Failed to get unified diff view:', err);
    }
  }, [sessionId, getUnifiedDiffView]);

  // メッセージ送信後に変更を抽出して差分ビュー更新
  useEffect(() => {
    const extractChanges = async () => {
      if (sessionId && messages.length > 0 && messages[messages.length - 1].role === 'assistant') {
        try {
          const changes = await extractPendingChanges();
          if (changes && changes.length > 0) {
            // 統合差分ビューを更新
            await updateDiffView();
            toast({
              title: '変更が検出されました',
              description: `${changes.length}件の変更があります。各変更を確認して承認してください。`,
            });
          }
        } catch (err) {
          console.error('Failed to extract changes:', err);
        }
      }
    };

    extractChanges();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [messages]);

  const handleSendMessage = async () => {
    if (!userInput.trim() || loading) return;

    const message = userInput;
    setUserInput('');

    try {
      await sendMessage(message);
    } catch (err) {
      toast({
        title: 'エラー',
        description: `メッセージの送信に失敗しました`,
        variant: 'destructive',
      });
    }
  };

  const handleApprove = useCallback(async (changeId: string) => {
    try {
      await approveChange(changeId);
      await updateDiffView();
      toast({
        title: '成功',
        description: '変更を承認しました',
      });
    } catch (err) {
      toast({
        title: 'エラー',
        description: '変更の承認に失敗しました',
        variant: 'destructive',
      });
    }
  }, [approveChange, updateDiffView, toast]);

  const handleReject = useCallback(async (changeId: string) => {
    try {
      await rejectChange(changeId);
      await updateDiffView();
      toast({
        title: '成功',
        description: '変更を拒否しました',
      });
    } catch (err) {
      toast({
        title: 'エラー',
        description: '変更の拒否に失敗しました',
        variant: 'destructive',
      });
    }
  }, [rejectChange, updateDiffView, toast]);

  const handleApproveAll = useCallback(async () => {
    try {
      const changesToApprove = diffLines.filter((line) => line.type === 'change' && !line.approved && line.change_id);
      await Promise.all(changesToApprove.map((line) => approveChange(line.change_id!)));
      await updateDiffView();
      toast({
        title: '成功',
        description: 'すべての変更を承認しました',
      });
    } catch (err) {
      toast({
        title: 'エラー',
        description: 'すべての変更の承認に失敗しました',
        variant: 'destructive',
      });
    }
  }, [diffLines, approveChange, updateDiffView, toast]);

  const handleRejectAll = useCallback(async () => {
    try {
      await clearPendingChanges();
      setDiffLines([]);
      setHasChanges(false);
      toast({
        title: '成功',
        description: 'すべての変更を拒否しました',
      });
    } catch (err) {
      toast({
        title: 'エラー',
        description: 'すべての変更の拒否に失敗しました',
        variant: 'destructive',
      });
    }
  }, [clearPendingChanges, toast]);

  const handleApplyChanges = useCallback(async () => {
    try {
      const result = await applyApprovedChanges();
      await updateDiffView();
      toast({
        title: '成功',
        description:
          result.applied_count > 0
            ? `${result.applied_count}件の変更を保存しました`
            : '適用する承認済みの変更はありませんでした',
      });
      onSave?.();
    } catch (err) {
      toast({
        title: 'エラー',
        description: '変更の適用に失敗しました',
        variant: 'destructive',
      });
    }
  }, [applyApprovedChanges, updateDiffView, toast, onSave]);

  const hasApprovedChanges = diffLines.some((line) => line.type === 'change' && line.approved);
  const allApproved = diffLines.filter((line) => line.type === 'change').every((line) => line.approved);

  return (
    <div className="flex w-full flex-col gap-5 lg:flex-row lg:gap-6 min-h-[calc(100vh-220px)] lg:h-[calc(100vh-220px)]">
      {/* 左側: 統合差分ビュー */}
      <Card className="flex-1 min-h-0 flex flex-col border border-slate-200/70 bg-white/95 p-4 md:p-5 shadow-xl backdrop-blur-sm">
        <div className="mb-5 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <h3 className="text-lg font-semibold text-slate-900">記事プレビュー（変更確認）</h3>
            <p className="text-sm text-slate-500">
              変更箇所は赤/緑でハイライトされます。必要に応じて承認または拒否を選択してください。
            </p>
          </div>

          {hasChanges && (
            <div className="flex flex-wrap items-center gap-2">
              <Button variant="outline" size="sm" onClick={handleRejectAll}>
                <X className="h-4 w-4 mr-1" />
                すべて拒否
              </Button>
              <Button variant="outline" size="sm" onClick={handleApproveAll} disabled={allApproved}>
                <Check className="h-4 w-4 mr-1" />
                すべて承認
              </Button>
              <Button size="sm" onClick={handleApplyChanges} disabled={!hasApprovedChanges}>
                変更を適用
              </Button>
            </div>
          )}
        </div>

        <div className="flex-1 min-h-0 overflow-hidden rounded-xl border border-slate-100 bg-white/95">
          {diffLines.length > 0 ? (
            <UnifiedDiffViewer
              lines={diffLines}
              onApprove={handleApprove}
              onReject={handleReject}
            />
          ) : (
            <div className="flex h-full flex-col items-center justify-center gap-3 px-6 text-center text-slate-500">
              <Bot className="h-16 w-16 text-slate-300" />
              <div className="space-y-1">
                <p className="text-base font-medium text-slate-700">AIエージェント編集</p>
                <p className="text-sm leading-relaxed">
                  右側のチャットから編集内容を指示してください。
                  <br />
                  変更が提案されると、ここにプレビューと差分が表示されます。
                </p>
              </div>
            </div>
          )}
        </div>
      </Card>

      {/* 右側: チャット */}
      <Card className="flex w-full min-h-[420px] max-w-full flex-col border border-slate-200/70 bg-white/95 p-4 md:p-6 shadow-xl backdrop-blur-sm lg:w-[460px] lg:max-w-[520px] xl:w-[520px]">
        <div className="mb-3 flex items-center gap-2 text-slate-800 md:mb-4">
          <Bot className="h-6 w-6 text-blue-600" />
          <h3 className="text-lg font-semibold">AIエージェントチャット</h3>
        </div>

        <div className="flex-1 min-h-0 overflow-hidden rounded-xl border border-slate-100 bg-white">
          <ScrollArea className="h-full">
            <div className="space-y-4 px-4 py-4 md:py-5">
              {messages.map((msg, idx) => (
                <div
                  key={idx}
                  className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-[82%] rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-sm ${
                      msg.role === 'user'
                        ? 'bg-blue-600 text-white'
                        : 'bg-slate-100 text-slate-900'
                    }`}
                  >
                    <div className="whitespace-pre-wrap">{msg.content}</div>
                  </div>
                </div>
              ))}

              {loading && (
                <div className="flex justify-start text-slate-500">
                  <div className="flex items-center gap-2 rounded-2xl bg-slate-100 px-4 py-3 text-sm">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    処理中...
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>
          </ScrollArea>
        </div>

        <div className="mt-4 border-t border-slate-100 pt-4">
          {error && (
            <div className="mb-3 flex items-center gap-2 rounded-lg border border-red-100 bg-red-50 px-3 py-2 text-sm text-red-600">
              <AlertCircle className="h-4 w-4" />
              <span>{error}</span>
            </div>
          )}

          <div className="flex flex-col gap-2">
            <Textarea
              value={userInput}
              onChange={(e) => setUserInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSendMessage();
                }
              }}
              placeholder="例: 「この見出しをもっと分かりやすくして」「誤字脱字をチェックして」"
              className="min-h-[80px] flex-1 resize-none border-slate-200 focus-visible:ring-blue-500"
              disabled={loading || !sessionId}
            />
            <div className="flex items-center justify-between text-xs text-slate-500">
              <span>Shift+Enter で改行、Enter で送信</span>
              <Button
                onClick={handleSendMessage}
                disabled={loading || !userInput.trim() || !sessionId}
                className="px-4"
              >
                <Send className="h-4 w-4" />
                <span className="ml-2">送信</span>
              </Button>
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
}
