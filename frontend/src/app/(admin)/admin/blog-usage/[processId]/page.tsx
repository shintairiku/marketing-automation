'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import {
  ArrowLeft,
  ChevronDown,
  Clock,
  DollarSign,
  Hash,
  Loader2,
  MessageSquare,
  RefreshCw,
  Wrench,
  Zap,
} from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { cn } from '@/utils/cn';
import { useAuth } from '@clerk/nextjs';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface BlogTraceLlmCall {
  id: string;
  execution_id: string;
  call_sequence: number;
  api_type: string;
  model_name: string;
  provider: string;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  cached_tokens: number;
  reasoning_tokens: number;
  estimated_cost_usd: number;
  api_response_id?: string | null;
  called_at?: string | null;
  response_data: Record<string, unknown>;
}

interface BlogTraceToolCall {
  id: string;
  execution_id: string;
  call_sequence: number;
  tool_name: string;
  tool_function: string;
  status: string;
  input_parameters: Record<string, unknown>;
  output_data: Record<string, unknown>;
  execution_time_ms?: number | null;
  error_type?: string | null;
  error_message?: string | null;
  called_at?: string | null;
  completed_at?: string | null;
  tool_metadata: Record<string, unknown>;
}

interface BlogTraceEvent {
  id: string;
  execution_id?: string | null;
  event_sequence: number;
  source: string;
  event_type: string;
  event_name?: string | null;
  agent_name?: string | null;
  role?: string | null;
  message_text?: string | null;
  tool_name?: string | null;
  tool_call_id?: string | null;
  response_id?: string | null;
  model_name?: string | null;
  prompt_tokens: number;
  completion_tokens: number;
  cached_tokens: number;
  reasoning_tokens: number;
  total_tokens: number;
  input_payload: Record<string, unknown>;
  output_payload: Record<string, unknown>;
  event_metadata: Record<string, unknown>;
  created_at?: string | null;
}

interface BlogUsageTraceExecution {
  id: string;
  step_number: number;
  sub_step_number: number;
  status: string;
  llm_model?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  duration_ms?: number | null;
  input_tokens: number;
  output_tokens: number;
  cache_tokens: number;
  reasoning_tokens: number;
  llm_calls: BlogTraceLlmCall[];
  tool_calls: BlogTraceToolCall[];
}

interface BlogUsageTraceResponse {
  process_id: string;
  user_id?: string | null;
  user_email?: string | null;
  status?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  session_id?: string | null;
  session_status?: string | null;
  session_created_at?: string | null;
  session_completed_at?: string | null;
  initial_input: Record<string, unknown>;
  session_metadata: Record<string, unknown>;
  conversation_history: Array<Record<string, unknown>>;
  last_response_id?: string | null;
  total_tokens: number;
  input_tokens: number;
  output_tokens: number;
  cached_tokens: number;
  reasoning_tokens: number;
  estimated_cost_usd: number;
  executions: BlogUsageTraceExecution[];
  trace_events: BlogTraceEvent[];
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8080';
const USE_PROXY = process.env.NODE_ENV === 'production';
const baseURL = USE_PROXY ? '/api/proxy' : API_BASE_URL;

// ---------------------------------------------------------------------------
// Utility functions
// ---------------------------------------------------------------------------

function formatNumber(value: number): string {
  return new Intl.NumberFormat('ja-JP').format(value || 0);
}

function formatUsd(value: number, digits = 4): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: digits,
  }).format(value || 0);
}

function formatDate(value?: string | null): string {
  if (!value) return '-';
  return new Date(value).toLocaleDateString('ja-JP', {
    month: 'numeric',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function formatDuration(startStr?: string | null, endStr?: string | null): string {
  if (!startStr || !endStr) return '-';
  const ms = new Date(endStr).getTime() - new Date(startStr).getTime();
  if (ms < 0) return '-';
  const totalSeconds = Math.floor(ms / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  if (minutes === 0) return `${seconds}s`;
  return `${minutes}m ${seconds}s`;
}

function shortenModel(name: string): string {
  return name
    .replace('litellm/gemini/', '')
    .replace('litellm/anthropic/', '')
    .replace('litellm/', '');
}

function formatResponseId(id?: string | null): string {
  if (!id) return '-';
  if (id.length <= 30) return id;
  return `${id.slice(0, 20)}...${id.slice(-10)}`;
}

function toJsonPreview(value: unknown, max = 240): string {
  try {
    const text = JSON.stringify(value, null, 2);
    if (!text) return '-';
    return text.length > max ? `${text.slice(0, max)}...` : text;
  } catch {
    return String(value ?? '-');
  }
}

function toFullText(value: unknown): string {
  if (typeof value === 'string') return value;
  try {
    const text = JSON.stringify(value, null, 2);
    return text || '-';
  } catch {
    return String(value ?? '-');
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return !!value && typeof value === 'object' && !Array.isArray(value);
}

function extractTextFromContent(content: unknown): string | null {
  if (typeof content === 'string') return content;
  if (Array.isArray(content)) {
    const texts: string[] = [];
    content.forEach((part) => {
      if (!part || typeof part !== 'object') return;
      const textPart = (part as { text?: unknown }).text;
      if (typeof textPart === 'string' && textPart.trim().length > 0) {
        texts.push(textPart);
      }
    });
    if (texts.length > 0) return texts.join('\n');
  }
  return null;
}

function extractConversationText(item: Record<string, unknown>): string {
  const itemType = typeof item.type === 'string' ? item.type : undefined;
  const role = typeof item.role === 'string' ? item.role : undefined;

  const contentText = extractTextFromContent(item.content);
  if (contentText) return contentText;

  if (itemType === 'function_call') {
    const name = typeof item.name === 'string' ? item.name : 'unknown_tool';
    const args = item.arguments;
    const argsText =
      typeof args === 'string'
        ? args
        : args !== undefined
          ? toJsonPreview(args, 320)
          : '(arguments none)';
    return `${name}(${argsText})`;
  }

  if (itemType === 'function_call_output') {
    const output = item.output;
    if (typeof output === 'string') return output;
    if (output !== undefined) return toJsonPreview(output, 320);
    return '(tool output none)';
  }

  if (itemType === 'reasoning') {
    const summary = item.summary;
    if (typeof summary === 'string' && summary.trim()) return summary;
    if (Array.isArray(summary)) {
      const texts: string[] = [];
      summary.forEach((part) => {
        if (!isRecord(part)) return;
        const text = part.text;
        if (typeof text === 'string' && text.trim()) texts.push(text);
      });
      if (texts.length > 0) return texts.join('\n');
      return toJsonPreview(summary, 320);
    }
    return '(reasoning item)';
  }

  if (role) {
    const content = item.content;
    if (content !== undefined) return toJsonPreview(content, 220);
  }

  return toJsonPreview(item, 220);
}

function getConversationItemLabel(
  item: Record<string, unknown>,
  toolNameByCallId: Map<string, string>
): string {
  const role = typeof item.role === 'string' ? item.role : undefined;
  if (role) return role;

  const itemType = typeof item.type === 'string' ? item.type : undefined;
  if (!itemType) return 'unknown';

  if (itemType === 'function_call') {
    const name = typeof item.name === 'string' ? item.name : 'unknown_tool';
    return `tool_call:${name}`;
  }

  if (itemType === 'function_call_output') {
    const callId = typeof item.call_id === 'string' ? item.call_id : undefined;
    const toolName = callId ? toolNameByCallId.get(callId) : undefined;
    return toolName ? `tool_output:${toolName}` : 'tool_output';
  }

  return itemType;
}

function truncateStr(str: string, max: number): string {
  if (str.length <= max) return str;
  return str.slice(0, max) + '...';
}

function cacheHitColor(pct: number): string {
  if (pct >= 70) return 'text-emerald-600';
  if (pct >= 40) return 'text-amber-600';
  return 'text-red-500';
}

function cacheHitBg(pct: number): string {
  if (pct >= 70) return 'bg-emerald-500';
  if (pct >= 40) return 'bg-amber-500';
  return 'bg-red-400';
}

function statusBadgeClass(status?: string | null): string {
  switch (status) {
    case 'completed':
      return 'border-emerald-200 bg-emerald-50 text-emerald-700';
    case 'error':
    case 'failed':
      return 'border-red-200 bg-red-50 text-red-700';
    case 'in_progress':
      return 'border-amber-200 bg-amber-50 text-amber-700';
    default:
      return 'border-stone-200 bg-stone-50 text-stone-600';
  }
}

function toolStatusBadgeClass(status: string): string {
  switch (status) {
    case 'completed':
      return 'border-emerald-200 bg-emerald-50 text-emerald-700';
    case 'error':
    case 'failed':
      return 'border-red-200 bg-red-50 text-red-700';
    case 'running':
      return 'border-amber-200 bg-amber-50 text-amber-700';
    default:
      return '';
  }
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function MetricCard({
  icon,
  label,
  value,
  sub,
  className,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  sub?: string;
  className?: string;
}) {
  return (
    <Card className={cn('relative overflow-hidden', className)}>
      <CardContent className="p-4">
        <div className="flex items-start justify-between">
          <div className="min-w-0 flex-1">
            <p className="text-[11px] font-medium text-stone-500 uppercase tracking-wider">
              {label}
            </p>
            <p className="mt-1 text-xl font-semibold tabular-nums text-stone-900 truncate">
              {value}
            </p>
            {sub && (
              <p className="mt-0.5 text-[11px] text-stone-400 truncate">{sub}</p>
            )}
          </div>
          <div className="ml-3 flex-shrink-0 rounded-lg bg-stone-100 p-2 text-stone-400">
            {icon}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function CacheBar({
  index,
  pct,
  tokens,
}: {
  index: number;
  pct: number;
  tokens: number;
}) {
  const clampedPct = Math.min(100, Math.max(0, pct));
  return (
    <div className="flex items-center gap-3 py-1">
      <span className="w-6 text-right text-xs font-medium text-stone-500 tabular-nums">
        #{index}
      </span>
      <div className="flex-1 h-5 rounded-full bg-stone-100 overflow-hidden relative">
        <div
          className={cn('h-full rounded-full transition-all', cacheHitBg(pct))}
          style={{ width: `${clampedPct}%` }}
        />
        {clampedPct > 12 && (
          <span className="absolute inset-0 flex items-center pl-2 text-[10px] font-medium text-white mix-blend-difference">
            {pct.toFixed(1)}%
          </span>
        )}
      </div>
      <span
        className={cn(
          'w-14 text-right text-xs font-semibold tabular-nums',
          cacheHitColor(pct)
        )}
      >
        {pct.toFixed(1)}%
      </span>
      <span className="w-20 text-right text-[11px] text-stone-400 tabular-nums">
        {formatNumber(tokens)}
      </span>
    </div>
  );
}

function ExpandableToolCard({
  tool,
  index,
  onViewFull,
}: {
  tool: BlogTraceToolCall;
  index: number;
  onViewFull: (title: string, value: unknown) => void;
}) {
  const [open, setOpen] = useState(false);
  const durationStr = tool.execution_time_ms
    ? tool.execution_time_ms > 1000
      ? `${(tool.execution_time_ms / 1000).toFixed(1)}s`
      : `${tool.execution_time_ms}ms`
    : null;

  return (
    <div className="rounded-lg border border-stone-200 bg-white overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center gap-3 px-4 py-3 text-left hover:bg-stone-50 transition-colors"
      >
        <span className="text-xs font-medium text-stone-400 tabular-nums w-5">
          {index}
        </span>
        <code className="text-xs font-medium text-stone-800 flex-1 truncate">
          {tool.tool_name}
        </code>
        <Badge
          variant="outline"
          className={cn('text-[10px] px-1.5 py-0', toolStatusBadgeClass(tool.status))}
        >
          {tool.status}
        </Badge>
        {durationStr && (
          <span className="text-[11px] text-stone-400 tabular-nums">{durationStr}</span>
        )}
        <ChevronDown
          className={cn(
            'h-3.5 w-3.5 text-stone-400 transition-transform',
            open && 'rotate-180'
          )}
        />
      </button>
      {open && (
        <div className="border-t border-stone-100 px-4 py-3 space-y-3">
          <div>
            <div className="flex items-center justify-between mb-1">
              <p className="text-[10px] font-medium text-stone-500 uppercase tracking-wider">
                Input
              </p>
              <button
                onClick={() =>
                  onViewFull(`Tool Input: ${tool.tool_name}`, tool.input_parameters)
                }
                className="text-[10px] text-stone-400 hover:text-stone-600 underline"
              >
                Full JSON
              </button>
            </div>
            <pre className="text-[11px] text-stone-600 whitespace-pre-wrap break-words bg-stone-50 rounded p-2 max-h-40 overflow-auto leading-relaxed">
              {toJsonPreview(tool.input_parameters, 600)}
            </pre>
          </div>
          <div>
            <div className="flex items-center justify-between mb-1">
              <p className="text-[10px] font-medium text-stone-500 uppercase tracking-wider">
                Output
              </p>
              <button
                onClick={() =>
                  onViewFull(`Tool Output: ${tool.tool_name}`, tool.output_data)
                }
                className="text-[10px] text-stone-400 hover:text-stone-600 underline"
              >
                Full JSON
              </button>
            </div>
            <pre className="text-[11px] text-stone-600 whitespace-pre-wrap break-words bg-stone-50 rounded p-2 max-h-40 overflow-auto leading-relaxed">
              {toJsonPreview(tool.output_data, 600)}
            </pre>
          </div>
          {tool.error_message && (
            <div>
              <p className="text-[10px] font-medium text-red-500 uppercase tracking-wider mb-1">
                Error
              </p>
              <p className="text-[11px] text-red-600 bg-red-50 rounded p-2">
                {tool.error_message}
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function ExpandableLlmRow({
  call,
  index,
  onViewFull,
}: {
  call: BlogTraceLlmCall;
  index: number;
  onViewFull: (title: string, value: unknown) => void;
}) {
  const [open, setOpen] = useState(false);
  const cacheRate =
    call.prompt_tokens > 0
      ? (call.cached_tokens / call.prompt_tokens) * 100
      : 0;

  return (
    <>
      <TableRow
        className="cursor-pointer hover:bg-stone-50 transition-colors"
        onClick={() => setOpen(!open)}
      >
        <TableCell className="text-xs tabular-nums text-stone-500 font-medium">
          #{index}
        </TableCell>
        <TableCell className="text-xs font-mono text-stone-700">
          {shortenModel(call.model_name)}
        </TableCell>
        <TableCell className="text-xs text-right tabular-nums">
          {formatNumber(call.prompt_tokens)}
        </TableCell>
        <TableCell className="text-xs text-right tabular-nums">
          {formatNumber(call.cached_tokens)}
        </TableCell>
        <TableCell className="text-xs text-right tabular-nums">
          {formatNumber(call.completion_tokens)}
        </TableCell>
        <TableCell className="text-xs text-right tabular-nums">
          {call.reasoning_tokens > 0 ? formatNumber(call.reasoning_tokens) : '-'}
        </TableCell>
        <TableCell className="text-xs text-right tabular-nums font-semibold">
          {formatNumber(call.total_tokens)}
        </TableCell>
        <TableCell className="text-xs text-right tabular-nums font-medium">
          {formatUsd(call.estimated_cost_usd)}
        </TableCell>
        <TableCell className="text-xs text-right tabular-nums">
          <span className={cn('font-semibold', cacheHitColor(cacheRate))}>
            {cacheRate.toFixed(1)}%
          </span>
        </TableCell>
        <TableCell className="text-right">
          <ChevronDown
            className={cn(
              'inline h-3.5 w-3.5 text-stone-400 transition-transform',
              open && 'rotate-180'
            )}
          />
        </TableCell>
      </TableRow>
      {open && (
        <TableRow className="bg-stone-50/50">
          <TableCell colSpan={10} className="p-4">
            <div className="space-y-2">
              <div className="flex items-center gap-4 text-[11px] text-stone-500">
                <span>
                  <span className="font-medium text-stone-600">Response ID: </span>
                  <code className="text-stone-500" title={call.api_response_id || '-'}>
                    {formatResponseId(call.api_response_id)}
                  </code>
                </span>
                <span>
                  <span className="font-medium text-stone-600">Time: </span>
                  {formatDate(call.called_at)}
                </span>
              </div>
              {Object.keys(call.response_data).length > 0 && (
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <p className="text-[10px] font-medium text-stone-500 uppercase tracking-wider">
                      Response Data
                    </p>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onViewFull(`LLM Call #${index} Response Data`, {
                          id: call.id,
                          model_name: call.model_name,
                          api_response_id: call.api_response_id,
                          tokens: {
                            prompt: call.prompt_tokens,
                            completion: call.completion_tokens,
                            cached: call.cached_tokens,
                            reasoning: call.reasoning_tokens,
                            total: call.total_tokens,
                          },
                          response_data: call.response_data,
                        });
                      }}
                      className="text-[10px] text-stone-400 hover:text-stone-600 underline"
                    >
                      Full JSON
                    </button>
                  </div>
                  <pre className="text-[11px] text-stone-600 whitespace-pre-wrap break-words bg-white border border-stone-100 rounded p-2 max-h-40 overflow-auto leading-relaxed">
                    {toJsonPreview(call.response_data, 800)}
                  </pre>
                </div>
              )}
            </div>
          </TableCell>
        </TableRow>
      )}
    </>
  );
}

function ConversationBubble({
  item,
  index,
  label,
  toolNameByCallId,
  onViewFull,
}: {
  item: Record<string, unknown>;
  index: number;
  label: string;
  toolNameByCallId: Map<string, string>;
  onViewFull: (title: string, value: unknown) => void;
}) {
  const text = extractConversationText(item);
  const preview = text.length > 300 ? text.slice(0, 300) + '...' : text;
  const role = typeof item.role === 'string' ? item.role : undefined;
  const itemType = typeof item.type === 'string' ? item.type : undefined;

  const isUser = role === 'user';
  const isAssistant = role === 'assistant';
  const isToolCall = itemType === 'function_call';
  const isToolOutput = itemType === 'function_call_output';
  const isReasoning = itemType === 'reasoning';

  // Ignore types used in getConversationItemLabel
  void toolNameByCallId;

  let bgClass = 'bg-white border-stone-200';
  let labelColor = 'text-stone-500';
  let alignment = 'items-start';

  if (isUser) {
    bgClass = 'bg-blue-50 border-blue-200';
    labelColor = 'text-blue-600';
    alignment = 'items-end';
  } else if (isAssistant) {
    bgClass = 'bg-stone-50 border-stone-200';
    labelColor = 'text-stone-600';
  } else if (isToolCall) {
    bgClass = 'bg-amber-50/60 border-amber-200';
    labelColor = 'text-amber-700';
  } else if (isToolOutput) {
    bgClass = 'bg-stone-50 border-stone-200';
    labelColor = 'text-stone-500';
  } else if (isReasoning) {
    bgClass = 'bg-purple-50/40 border-purple-200';
    labelColor = 'text-purple-500';
  }

  return (
    <div className={cn('flex flex-col', alignment)}>
      <div
        className={cn(
          'rounded-lg border px-3 py-2 max-w-[90%]',
          bgClass
        )}
      >
        <div className="flex items-center justify-between gap-2 mb-1">
          <p className={cn('text-[10px] font-semibold uppercase tracking-wider', labelColor)}>
            {label}
            <span className="text-stone-400 font-normal ml-1">#{index + 1}</span>
          </p>
          <button
            onClick={() => onViewFull(`Conversation #${index + 1} (${label})`, item)}
            className="text-[10px] text-stone-400 hover:text-stone-600 underline flex-shrink-0"
          >
            JSON
          </button>
        </div>
        <pre
          className={cn(
            'text-[11px] whitespace-pre-wrap break-words leading-relaxed',
            isReasoning && 'italic text-stone-500',
            isToolCall && 'font-mono',
            isToolOutput && 'font-mono text-stone-500',
            !isReasoning && !isToolCall && !isToolOutput && 'text-stone-700'
          )}
        >
          {preview}
        </pre>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Loading skeleton
// ---------------------------------------------------------------------------

function PageSkeleton() {
  return (
    <div className="space-y-6 p-1">
      {/* Header skeleton */}
      <div className="space-y-2">
        <Skeleton className="h-4 w-28" />
        <Skeleton className="h-7 w-96 max-w-full" />
        <div className="flex gap-2">
          <Skeleton className="h-5 w-20" />
          <Skeleton className="h-5 w-32" />
          <Skeleton className="h-5 w-24" />
        </div>
      </div>
      {/* Metric cards skeleton */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <Card key={i}>
            <CardContent className="p-4">
              <Skeleton className="h-3 w-16 mb-2" />
              <Skeleton className="h-6 w-full" />
            </CardContent>
          </Card>
        ))}
      </div>
      {/* Cache bars skeleton */}
      <Card>
        <CardContent className="p-5">
          <Skeleton className="h-4 w-44 mb-4" />
          <div className="space-y-2">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-5 w-full" />
            ))}
          </div>
        </CardContent>
      </Card>
      {/* Table skeleton */}
      <Card>
        <CardContent className="p-5">
          <Skeleton className="h-4 w-32 mb-4" />
          <Skeleton className="h-40 w-full" />
        </CardContent>
      </Card>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function AdminBlogUsageDetailPage() {
  const { getToken } = useAuth();
  const params = useParams();
  const processId = String(params.processId || '');

  const [data, setData] = useState<BlogUsageTraceResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [detailViewer, setDetailViewer] = useState<{
    title: string;
    content: string;
  } | null>(null);

  const openDetailViewer = useCallback((title: string, value: unknown) => {
    setDetailViewer({ title, content: toFullText(value) });
  }, []);

  const fetchTrace = useCallback(async () => {
    if (!processId) return;
    setLoading(true);
    setError(null);
    try {
      const token = await getToken();
      const response = await fetch(
        `${baseURL}/admin/usage/blog/${processId}/trace`,
        {
          headers: {
            'Content-Type': 'application/json',
            ...(token && { Authorization: `Bearer ${token}` }),
          },
        }
      );
      if (!response.ok) {
        throw new Error(`Failed to fetch trace (${response.status})`);
      }
      const json: BlogUsageTraceResponse = await response.json();
      setData(json);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Trace fetch failed');
    } finally {
      setLoading(false);
    }
  }, [getToken, processId]);

  useEffect(() => {
    fetchTrace();
  }, [fetchTrace]);

  // Derived data -------------------------------------------------------

  const llmCalls = useMemo(() => {
    return (data?.executions || [])
      .flatMap((ex) => ex.llm_calls)
      .sort((a, b) => {
        const ta = a.called_at || '';
        const tb = b.called_at || '';
        if (ta === tb) return a.call_sequence - b.call_sequence;
        return ta > tb ? 1 : -1;
      });
  }, [data]);

  const toolCalls = useMemo(() => {
    return (data?.executions || [])
      .flatMap((ex) => ex.tool_calls)
      .sort((a, b) => {
        const ta = a.called_at || '';
        const tb = b.called_at || '';
        if (ta === tb) return a.call_sequence - b.call_sequence;
        return ta > tb ? 1 : -1;
      });
  }, [data]);

  const overallCacheRate = useMemo(() => {
    if (!data || data.input_tokens === 0) return 0;
    return (data.cached_tokens / data.input_tokens) * 100;
  }, [data]);

  const sessionDuration = useMemo(() => {
    return formatDuration(data?.session_created_at, data?.session_completed_at);
  }, [data]);

  const userPrompt = useMemo(() => {
    const raw = data?.initial_input?.user_prompt;
    if (typeof raw === 'string') return raw;
    return '';
  }, [data]);

  const conversationToolNameByCallId = useMemo(() => {
    const map = new Map<string, string>();
    (data?.conversation_history || []).forEach((item) => {
      if (!item || typeof item !== 'object') return;
      const type = typeof item.type === 'string' ? item.type : undefined;
      const callId = typeof item.call_id === 'string' ? item.call_id : undefined;
      const name = typeof item.name === 'string' ? item.name : undefined;
      if (type === 'function_call' && callId && name) {
        map.set(callId, name);
      }
    });
    return map;
  }, [data]);

  // Render -------------------------------------------------------------

  if (loading) {
    return <PageSkeleton />;
  }

  if (error) {
    return (
      <div className="space-y-4 p-1">
        <Link
          href="/admin/blog-usage"
          className="inline-flex items-center text-xs text-stone-500 hover:text-stone-700 transition-colors"
        >
          <ArrowLeft className="h-3 w-3 mr-1" />
          Blog Usage
        </Link>
        <Card className="border-red-200 bg-red-50/50">
          <CardContent className="py-10 text-center">
            <p className="text-sm text-red-700 mb-4">{error}</p>
            <Button variant="outline" size="sm" onClick={fetchTrace}>
              <RefreshCw className="h-3.5 w-3.5 mr-1.5" />
              Retry
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="space-y-4 p-1">
        <Link
          href="/admin/blog-usage"
          className="inline-flex items-center text-xs text-stone-500 hover:text-stone-700 transition-colors"
        >
          <ArrowLeft className="h-3 w-3 mr-1" />
          Blog Usage
        </Link>
        <Card>
          <CardContent className="py-12 text-center text-sm text-stone-500">
            No data found for this process.
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6 p-1">
      {/* ---- Header ---- */}
      <div>
        <Link
          href="/admin/blog-usage"
          className="inline-flex items-center text-xs text-stone-500 hover:text-stone-700 transition-colors mb-3"
        >
          <ArrowLeft className="h-3 w-3 mr-1" />
          Blog Usage
        </Link>

        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0 flex-1">
            <h1 className="text-lg font-bold text-stone-900 leading-tight sm:text-xl">
              {userPrompt ? truncateStr(userPrompt, 80) : `Process ${processId.slice(0, 8)}...`}
            </h1>
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <Badge
                variant="outline"
                className={cn('text-[11px]', statusBadgeClass(data.status))}
              >
                {data.status || 'unknown'}
              </Badge>
              <span className="text-[11px] text-stone-400">
                {formatDate(data.created_at)}
              </span>
              {data.user_email && (
                <span className="text-[11px] text-stone-400">
                  {data.user_email}
                </span>
              )}
              {sessionDuration !== '-' && (
                <span className="text-[11px] text-stone-400 flex items-center gap-0.5">
                  <Clock className="h-3 w-3" />
                  {sessionDuration}
                </span>
              )}
            </div>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={fetchTrace}
            className="flex-shrink-0"
          >
            <RefreshCw className="h-3.5 w-3.5 mr-1.5" />
            Refresh
          </Button>
        </div>
      </div>

      {/* ---- Metric cards ---- */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        <MetricCard
          icon={<DollarSign className="h-4 w-4" />}
          label="Total Cost"
          value={formatUsd(data.estimated_cost_usd)}
          className="col-span-2 md:col-span-1"
        />
        <MetricCard
          icon={<Hash className="h-4 w-4" />}
          label="Total Tokens"
          value={formatNumber(data.total_tokens)}
          sub={`In: ${formatNumber(data.input_tokens)} / Out: ${formatNumber(data.output_tokens)}`}
        />
        <MetricCard
          icon={<Zap className="h-4 w-4" />}
          label="Cache Hit"
          value={`${overallCacheRate.toFixed(1)}%`}
          sub={`${formatNumber(data.cached_tokens)} cached`}
        />
        <MetricCard
          icon={<MessageSquare className="h-4 w-4" />}
          label="LLM Calls"
          value={String(llmCalls.length)}
        />
        <MetricCard
          icon={<Wrench className="h-4 w-4" />}
          label="Tool Calls"
          value={String(toolCalls.length)}
        />
        <MetricCard
          icon={<Clock className="h-4 w-4" />}
          label="Duration"
          value={sessionDuration}
        />
      </div>

      {/* ---- Cache Performance ---- */}
      {llmCalls.length > 0 && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-semibold text-stone-800">
              Cache Performance
            </CardTitle>
          </CardHeader>
          <CardContent className="pb-4">
            <div className="space-y-0.5">
              {llmCalls.map((call, i) => {
                const pct =
                  call.prompt_tokens > 0
                    ? (call.cached_tokens / call.prompt_tokens) * 100
                    : 0;
                return (
                  <CacheBar
                    key={call.id}
                    index={i + 1}
                    pct={pct}
                    tokens={call.total_tokens}
                  />
                );
              })}
            </div>
            {/* Overall bar */}
            <div className="mt-3 pt-3 border-t border-stone-100">
              <div className="flex items-center justify-between text-xs">
                <span className="font-medium text-stone-600">Overall</span>
                <span className={cn('font-bold', cacheHitColor(overallCacheRate))}>
                  {overallCacheRate.toFixed(1)}%
                </span>
              </div>
              <div className="mt-1.5 h-2 rounded-full bg-stone-100 overflow-hidden">
                <div
                  className={cn('h-full rounded-full', cacheHitBg(overallCacheRate))}
                  style={{ width: `${Math.min(100, overallCacheRate)}%` }}
                />
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* ---- LLM Calls ---- */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-semibold text-stone-800">
            LLM Calls ({llmCalls.length})
          </CardTitle>
        </CardHeader>
        <CardContent className="overflow-x-auto pb-3">
          {llmCalls.length === 0 ? (
            <p className="text-xs text-stone-400 text-center py-6">
              No LLM call logs
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="text-[11px] w-10">#</TableHead>
                  <TableHead className="text-[11px]">Model</TableHead>
                  <TableHead className="text-[11px] text-right">Input</TableHead>
                  <TableHead className="text-[11px] text-right">Cached</TableHead>
                  <TableHead className="text-[11px] text-right">Output</TableHead>
                  <TableHead className="text-[11px] text-right">Reasoning</TableHead>
                  <TableHead className="text-[11px] text-right">Total</TableHead>
                  <TableHead className="text-[11px] text-right">Cost</TableHead>
                  <TableHead className="text-[11px] text-right">Cache%</TableHead>
                  <TableHead className="text-[11px] w-8" />
                </TableRow>
              </TableHeader>
              <TableBody>
                {llmCalls.map((call, i) => (
                  <ExpandableLlmRow
                    key={call.id}
                    call={call}
                    index={i + 1}
                    onViewFull={openDetailViewer}
                  />
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* ---- Tool Calls ---- */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-semibold text-stone-800">
            Tool Calls ({toolCalls.length})
          </CardTitle>
        </CardHeader>
        <CardContent className="pb-3">
          {toolCalls.length === 0 ? (
            <p className="text-xs text-stone-400 text-center py-6">
              No tool call logs
            </p>
          ) : (
            <div className="space-y-2">
              {toolCalls.map((tool, i) => (
                <ExpandableToolCard
                  key={tool.id}
                  tool={tool}
                  index={i + 1}
                  onViewFull={openDetailViewer}
                />
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* ---- Conversation History (Collapsible, default closed) ---- */}
      <Collapsible defaultOpen={false}>
        <Card>
          <CardHeader className="pb-0">
            <CollapsibleTrigger className="flex w-full items-center justify-between py-1 group">
              <CardTitle className="text-sm font-semibold text-stone-800">
                Conversation History ({data.conversation_history.length})
              </CardTitle>
              <ChevronDown className="h-4 w-4 text-stone-400 transition-transform group-data-[state=open]:rotate-180" />
            </CollapsibleTrigger>
          </CardHeader>
          <CollapsibleContent>
            <CardContent className="pt-4 pb-4">
              {data.conversation_history.length === 0 ? (
                <p className="text-xs text-stone-400 text-center py-6">
                  No conversation history saved
                </p>
              ) : (
                <div className="space-y-2 max-h-[500px] overflow-y-auto pr-1">
                  {data.conversation_history.map((item, idx) => {
                    const label = getConversationItemLabel(
                      item,
                      conversationToolNameByCallId
                    );
                    return (
                      <ConversationBubble
                        key={idx}
                        item={item}
                        index={idx}
                        label={label}
                        toolNameByCallId={conversationToolNameByCallId}
                        onViewFull={openDetailViewer}
                      />
                    );
                  })}
                </div>
              )}
            </CardContent>
          </CollapsibleContent>
        </Card>
      </Collapsible>

      {/* ---- Raw Events (Collapsible, default closed) ---- */}
      <Collapsible defaultOpen={false}>
        <Card>
          <CardHeader className="pb-0">
            <CollapsibleTrigger className="flex w-full items-center justify-between py-1 group">
              <CardTitle className="text-sm font-semibold text-stone-800">
                Raw Events ({data.trace_events.length})
              </CardTitle>
              <ChevronDown className="h-4 w-4 text-stone-400 transition-transform group-data-[state=open]:rotate-180" />
            </CollapsibleTrigger>
          </CardHeader>
          <CollapsibleContent>
            <CardContent className="pt-4 pb-3 overflow-x-auto">
              {data.trace_events.length === 0 ? (
                <p className="text-xs text-stone-400 text-center py-6">
                  No trace events
                </p>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="text-[11px] text-right w-12">Seq</TableHead>
                      <TableHead className="text-[11px]">Event</TableHead>
                      <TableHead className="text-[11px]">Tool / Model</TableHead>
                      <TableHead className="text-[11px] text-right">Tokens</TableHead>
                      <TableHead className="text-[11px]">Time</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {data.trace_events.map((ev) => {
                      const toolOrModel =
                        ev.tool_name || (ev.model_name ? shortenModel(ev.model_name) : null) || '-';
                      return (
                        <TableRow key={ev.id}>
                          <TableCell className="text-xs text-right tabular-nums text-stone-500">
                            {ev.event_sequence}
                          </TableCell>
                          <TableCell className="text-xs font-mono text-stone-700">
                            {ev.event_type}
                          </TableCell>
                          <TableCell className="text-[11px] text-stone-500 truncate max-w-[160px]">
                            {toolOrModel}
                          </TableCell>
                          <TableCell className="text-xs text-right tabular-nums">
                            {ev.total_tokens > 0 ? formatNumber(ev.total_tokens) : '-'}
                          </TableCell>
                          <TableCell className="text-[11px] text-stone-400 whitespace-nowrap">
                            {formatDate(ev.created_at)}
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </CollapsibleContent>
        </Card>
      </Collapsible>

      {/* ---- Full-text Dialog ---- */}
      <Dialog
        open={!!detailViewer}
        onOpenChange={(open) => !open && setDetailViewer(null)}
      >
        <DialogContent className="max-w-4xl max-h-[85vh] overflow-hidden">
          <DialogHeader>
            <DialogTitle className="text-sm font-semibold text-stone-800">
              {detailViewer?.title || 'Detail'}
            </DialogTitle>
          </DialogHeader>
          <div className="rounded-lg border border-stone-200 bg-stone-50 p-4 max-h-[70vh] overflow-auto">
            <pre className="text-xs text-stone-700 whitespace-pre-wrap break-words leading-relaxed">
              {detailViewer?.content || '-'}
            </pre>
          </div>
        </DialogContent>
      </Dialog>

      {/* ---- Loading indicator ---- */}
      {loading && (
        <div className="fixed bottom-4 right-4 rounded-lg border bg-white px-3 py-2 text-xs text-stone-500 shadow-sm">
          <Loader2 className="inline h-3 w-3 animate-spin mr-1.5" />
          Loading...
        </div>
      )}
    </div>
  );
}
