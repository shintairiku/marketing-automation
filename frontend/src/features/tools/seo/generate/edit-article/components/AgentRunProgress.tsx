'use client';

import React, { useMemo } from 'react';
import { Bot, CheckCircle2, Loader2, MessageSquare, Search, Sparkles, Wrench, XCircle } from 'lucide-react';

import type { AgentRunState, AgentStreamEvent } from '@/hooks/useAgentChat';
import { cn } from '@/utils/cn';

interface AgentRunProgressProps {
  runState: AgentRunState | null;
  isLoading?: boolean;
}

const formatTimestamp = (iso: string | null | undefined): string | null => {
  if (!iso) return null;
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return null;
  }
  return date.toLocaleTimeString('ja-JP', { hour: '2-digit', minute: '2-digit' });
};

const describeEvent = (event: AgentStreamEvent): string => {
  const payload = event.payload ?? {};
  const toolName = typeof payload.tool_name === 'string' ? payload.tool_name : undefined;

  switch (event.eventType) {
    case 'run_started':
      return 'エージェントを起動しています';
    case 'response_created':
      return 'モデルへのリクエストを初期化しました';
    case 'in_progress':
      return '応答を生成しています…';
    case 'text_delta':
      return event.message || '回答を構築しています…';
    case 'text_delta_done':
      return 'テキストの組み立てが完了しました';
    case 'tool_called':
      return toolName ? `${toolName} を実行中です` : 'ツールを実行しています';
    case 'tool_output':
      return toolName ? `${toolName} の結果を取得しました` : 'ツールの結果を取得しました';
    case 'tool_web_search_searching':
      return 'Web検索を開始しました';
    case 'tool_web_search_in_progress':
      return 'Web検索の候補を評価しています';
    case 'tool_web_search_completed':
      return 'Web検索が完了しました';
    case 'tool_arguments_delta':
      return toolName ? `${toolName} の指示を作成しています…` : 'ツールの引数を作成しています…';
    case 'tool_arguments_ready':
      return toolName ? `${toolName} の指示が確定しました` : 'ツールの引数が確定しました';
    case 'reasoning':
      return event.message || '推論内容を整理しています';
    case 'assistant_message':
      return '回答文をまとめています';
    case 'agent_updated':
      return event.message || 'エージェントを切り替えました';
    case 'response_completed':
      return 'モデルの応答が確定しました';
    case 'run_completed':
      return '処理が完了しました';
    case 'run_failed':
      return event.message || '処理でエラーが発生しました';
    default:
      return event.message || '処理の進行中…';
  }
};

const eventIcon = (eventType: string): React.ReactNode => {
  switch (eventType) {
    case 'tool_called':
    case 'tool_output':
    case 'tool_arguments_delta':
    case 'tool_arguments_ready':
      return <Wrench className="h-3.5 w-3.5 text-indigo-500" />;
    case 'tool_web_search_searching':
    case 'tool_web_search_in_progress':
    case 'tool_web_search_completed':
      return <Search className="h-3.5 w-3.5 text-sky-500" />;
    case 'reasoning':
      return <Sparkles className="h-3.5 w-3.5 text-purple-500" />;
    case 'assistant_message':
    case 'text_delta':
    case 'text_delta_done':
      return <MessageSquare className="h-3.5 w-3.5 text-emerald-500" />;
    default:
      return <Bot className="h-3.5 w-3.5 text-blue-500" />;
  }
};

const headerIcon = (status: AgentRunState['status'], isLoading?: boolean): React.ReactNode => {
  if (status === 'failed') {
    return <XCircle className="h-4.5 w-4.5 text-red-500" />;
  }
  if (status === 'completed') {
    return <CheckCircle2 className="h-4.5 w-4.5 text-emerald-500" />;
  }
  if (isLoading || status === 'running') {
    return <Loader2 className="h-4.5 w-4.5 animate-spin text-blue-500" />;
  }
  return <Sparkles className="h-4.5 w-4.5 text-slate-400" />;
};

export default function AgentRunProgress({ runState, isLoading }: AgentRunProgressProps) {
  const eventsToDisplay = useMemo(() => {
    const sourceEvents = runState?.events ?? [];
    return sourceEvents.slice(Math.max(sourceEvents.length - 6, 0));
  }, [runState]);

  if (!runState) {
    return null;
  }

  const latestEvent = eventsToDisplay.length > 0 ? eventsToDisplay[eventsToDisplay.length - 1] : null;

  let statusLine = '';
  switch (runState.status) {
    case 'running':
      statusLine = latestEvent ? describeEvent(latestEvent) : 'AI が処理を進めています…';
      break;
    case 'completed':
      statusLine = '処理が完了しました';
      break;
    case 'failed':
      statusLine = runState.error ?? 'エージェント処理でエラーが発生しました';
      break;
    default:
      statusLine = latestEvent ? describeEvent(latestEvent) : '待機中です';
      break;
  }

  const showEvents = eventsToDisplay.length > 0;

  return (
    <div className="w-full rounded-2xl border border-slate-200 bg-white/95 px-4 py-3 shadow-sm">
      <div className="flex items-start gap-3">
        <div className="mt-0.5 flex h-9 w-9 items-center justify-center rounded-full bg-slate-100">
          {headerIcon(runState.status, isLoading)}
        </div>
        <div className="flex-1">
          <div className="flex flex-col gap-0.5">
            <p className="text-sm font-semibold text-slate-800">AIエージェントの進行状況</p>
            <p className={cn('text-xs', runState.status === 'failed' ? 'text-red-600' : 'text-slate-500')}>
              {statusLine}
            </p>
          </div>

          {showEvents && (
            <ul className="mt-3 space-y-2">
              {eventsToDisplay.map((event) => {
                const timestamp = formatTimestamp(event.createdAt ?? null);
                const isLatest = latestEvent?.eventId === event.eventId;
                return (
                  <li
                    key={`${event.eventId}-${event.sequence}`}
                    className={cn(
                      'flex items-start gap-2 rounded-xl border border-transparent px-2 py-1.5 transition-colors',
                      isLatest && runState.status === 'running' ? 'border-slate-200 bg-slate-50' : undefined
                    )}
                  >
                    <div className="mt-0.5 flex h-5 w-5 items-center justify-center rounded-full bg-slate-100">
                      {eventIcon(event.eventType)}
                    </div>
                    <div className="flex-1">
                      <p className="text-sm text-slate-700">{describeEvent(event)}</p>
                      {timestamp && <p className="text-[11px] text-slate-400">{timestamp}</p>}
                    </div>
                  </li>
                );
              })}
            </ul>
          )}

          {runState.status === 'failed' && runState.error && (
            <div className="mt-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-600">
              {runState.error}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
