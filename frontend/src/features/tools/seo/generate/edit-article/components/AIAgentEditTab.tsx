'use client';

import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { AlertCircle, Bot, Check, ChevronDown, Plus, Send, X } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { useToast } from '@/hooks/use-toast';
import {
  type AgentRunTimelineEntry,
  type AgentSessionSummary,
  type ChatMessage,
  useAgentChat,
} from '@/hooks/useAgentChat';

import AgentRunProgress from './AgentRunProgress';
import AIAgentChatMessage from './AIAgentChatMessage';
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

interface ConversationBlock {
  key: string;
  userMessage: ChatMessage | null;
  assistantMessages: ChatMessage[];
  runEntry: AgentRunTimelineEntry | null;
}

const computeRunStatusLine = (runState: AgentRunTimelineEntry['runState']): string => {
  if (!runState) {
    return 'エージェントの進行状況を待機しています…';
  }

  const events = runState.events ?? [];
  const latestEvent = events.length > 0 ? events[events.length - 1] : null;

  switch (runState.status) {
    case 'running':
      return latestEvent?.message || 'AI が処理を進めています…';
    case 'completed':
      return '処理が完了しました';
    case 'failed':
      return runState.error ?? 'エージェント処理でエラーが発生しました';
    default:
      return latestEvent?.message || '待機中です';
  }
};

const RunProgressPanel = ({ entry }: { entry: AgentRunTimelineEntry }): JSX.Element | null => {
  const [open, setOpen] = useState(() => true);

  useEffect(() => {
    if (entry.runState?.status === 'running') {
      setOpen(true);
    }
  }, [entry.runState?.status]);

  const statusLine = useMemo(() => computeRunStatusLine(entry.runState), [entry.runState]);
  const isError = entry.runState?.status === 'failed';
  const showDetails = Boolean(entry.runState);

  return (
    <Collapsible open={open} onOpenChange={setOpen} className="w-full">
      <div className="rounded-2xl border border-slate-200 bg-white/95 shadow-sm">
        <div className="flex items-start gap-3 px-4 py-3">
          <div className="flex-1">
            <p className="text-xs font-semibold text-slate-700">AIエージェントの進行状況</p>
            <p className={`mt-0.5 text-[11px] ${isError ? 'text-red-600' : 'text-slate-500'}`}>{statusLine}</p>
          </div>
          <CollapsibleTrigger asChild>
            <button
              type="button"
              className="flex h-8 w-8 items-center justify-center rounded-full border border-slate-200 bg-white text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-700"
              aria-label="推論の進行状況を表示"
            >
              <ChevronDown className={`h-4 w-4 transition-transform ${open ? 'rotate-180' : ''}`} />
            </button>
          </CollapsibleTrigger>
        </div>
        {showDetails && (
          <CollapsibleContent>
            <div className="border-t border-slate-100 px-4 py-3">
              <AgentRunProgress runState={entry.runState} isLoading={entry.runState?.status === 'running'} />
            </div>
          </CollapsibleContent>
        )}
      </div>
    </Collapsible>
  );
};

export default function AIAgentEditTab({ articleId, onSave }: AIAgentEditTabProps) {
  const {
    messages,
    loading,
    error,
    sessionId,
    runTimeline,
    initializeSession,
    startNewSession,
    activateSession,
    sessions,
    sendMessage,
    extractPendingChanges,
    approveChange,
    rejectChange,
    applyApprovedChanges,
    clearPendingChanges,
    getUnifiedDiffView,
  } = useAgentChat(articleId);

  const { toast } = useToast();
  const [userInput, setUserInput] = useState('');
  const [diffLines, setDiffLines] = useState<UnifiedDiffLine[]>([]);
  const [hasChanges, setHasChanges] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const activeSession = useMemo(
    () => sessions.find((session) => session.session_id === sessionId),
    [sessions, sessionId]
  );

  const formatSessionLabel = useCallback((session: AgentSessionSummary) => {
      const timestamp = session.last_activity_at
        ? new Date(session.last_activity_at).toLocaleString('ja-JP', {
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
          })
        : '';
      const prefix = session.status === 'active' ? 'アクティブ' : '履歴';
      const summary = session.summary ? session.summary : '（メッセージなし）';
      return `${prefix}${timestamp ? `・${timestamp}` : ''}｜${summary}`;
  }, []);

  const timelineByTriggerIndex = useMemo(() => {
    const map = new Map<number, AgentRunTimelineEntry>();
    runTimeline.forEach((entry) => {
      map.set(entry.triggerMessageIndex, entry);
    });
    return map;
  }, [runTimeline]);

  const conversationBlocks = useMemo<ConversationBlock[]>(() => {
    const blocks: ConversationBlock[] = [];
    let index = 0;

    while (index < messages.length) {
      const message = messages[index];
      if (message.role === 'user') {
        const runEntry = timelineByTriggerIndex.get(index) ?? null;
        const assistantMessages: ChatMessage[] = [];
        let pointer = index + 1;
        while (pointer < messages.length && messages[pointer].role === 'assistant') {
          assistantMessages.push(messages[pointer]);
          pointer += 1;
        }

        blocks.push({
          key: runEntry?.id ?? `user-${index}`,
          userMessage: message,
          assistantMessages,
          runEntry,
        });
        index = pointer;
      } else {
        const assistantMessages: ChatMessage[] = [];
        let pointer = index;
        while (pointer < messages.length && messages[pointer].role === 'assistant') {
          assistantMessages.push(messages[pointer]);
          pointer += 1;
        }

        if (assistantMessages.length > 0) {
          blocks.push({
            key: `assistant-${index}`,
            userMessage: null,
            assistantMessages,
            runEntry: null,
          });
        }

        index = pointer;
      }
    }

    return blocks;
  }, [messages, timelineByTriggerIndex]);

  const handleSessionSelect = useCallback(
    async (value: string) => {
      if (!value || value === sessionId) return;
      try {
        setDiffLines([]);
        setHasChanges(false);
        await activateSession(value);
      } catch (err) {
        toast({
          title: 'エラー',
          description: 'セッションの切り替えに失敗しました',
          variant: 'destructive',
        });
      }
    },
    [activateSession, sessionId, toast]
  );

  const handleStartNewSession = useCallback(async () => {
    try {
      setDiffLines([]);
      setHasChanges(false);
      await startNewSession();
    } catch (err) {
      toast({
        title: 'エラー',
        description: '新しい会話の開始に失敗しました',
        variant: 'destructive',
      });
    }
  }, [startNewSession, toast]);

  // セッション作成（マウント時のみ）
  useEffect(() => {
    let mounted = true;

    const initSession = async () => {
      if (!sessionId && mounted) {
        try {
          await initializeSession();
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

        <div className="mb-4 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <Select
            value={sessionId ?? undefined}
            onValueChange={handleSessionSelect}
            disabled={loading || sessions.length === 0}
          >
            <SelectTrigger className="w-full md:w-72">
              <SelectValue placeholder="会話を選択" />
            </SelectTrigger>
            <SelectContent>
              {sessions.length > 0 ? (
                sessions.map((session) => (
                  <SelectItem key={session.session_id} value={session.session_id}>
                    {formatSessionLabel(session)}
                  </SelectItem>
                ))
              ) : (
                <SelectItem value="__empty" disabled>
                  会話履歴はまだありません
                </SelectItem>
              )}
            </SelectContent>
          </Select>

          <Button
            variant="outline"
            size="sm"
            onClick={handleStartNewSession}
            disabled={loading}
            className="md:w-auto"
          >
            <Plus className="h-4 w-4 mr-2" />
            新しい会話
          </Button>
        </div>

        {activeSession && (
          <p className="mb-3 text-xs text-slate-500 line-clamp-2 md:mb-4">
            {activeSession.summary || '（メッセージなし）'}
          </p>
        )}

        <div className="flex-1 min-h-0 overflow-hidden rounded-2xl border border-slate-100 bg-gradient-to-b from-white via-white to-slate-50">
          <ScrollArea className="h-full pr-1">
            <div className="flex flex-col gap-6 px-4 py-5">
              {conversationBlocks.length === 0 && !loading && (
                <div className="flex flex-col items-center justify-center gap-3 rounded-2xl border border-dashed border-slate-200 bg-white/90 px-6 py-10 text-center text-sm text-slate-500">
                  <Bot className="h-8 w-8 text-slate-300" />
                  <div className="space-y-1">
                    <p className="font-semibold text-slate-700">AIエージェントと会話を始めましょう</p>
                    <p className="text-xs leading-relaxed text-slate-500">
                      指示を送ると、提案内容がこちらにチャット形式で表示されます。
                    </p>
                  </div>
                </div>
              )}

              {conversationBlocks.map((block, blockIdx) => (
                <div key={`${block.key}-${blockIdx}`} className="flex flex-col gap-3">
                  {block.userMessage && (
                    <AIAgentChatMessage
                      key={`${block.key}-user`}
                      role="user"
                      content={block.userMessage.content}
                    />
                  )}

                  {block.userMessage && block.runEntry && (
                    <RunProgressPanel entry={block.runEntry} />
                  )}

                  {block.assistantMessages.map((msg, msgIdx) => (
                    <AIAgentChatMessage
                      key={`${block.key}-assistant-${msgIdx}`}
                      role="assistant"
                      content={msg.content}
                    />
                  ))}
                </div>
              ))}

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
