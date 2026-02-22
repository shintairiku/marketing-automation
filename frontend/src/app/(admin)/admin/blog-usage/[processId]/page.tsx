'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { ArrowLeft, Loader2, RefreshCw } from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
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
import { useAuth } from '@clerk/nextjs';

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

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8080';
const USE_PROXY = process.env.NODE_ENV === 'production';
const baseURL = USE_PROXY ? '/api/proxy' : API_BASE_URL;

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

function formatResponseId(id?: string | null): string {
  if (!id) return '-';
  if (id.length <= 30) return id;
  return `${id.slice(0, 20)}…${id.slice(-10)}`;
}

function shortenModel(name: string): string {
  return name
    .replace('litellm/gemini/', '')
    .replace('litellm/anthropic/', '')
    .replace('litellm/', '');
}

function toJsonPreview(value: unknown, max = 240): string {
  try {
    const text = JSON.stringify(value, null, 2);
    if (!text) return '-';
    return text.length > max ? `${text.slice(0, max)}…` : text;
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
          : '(arguments なし)';
    return `${name}(${argsText})`;
  }

  if (itemType === 'function_call_output') {
    const output = item.output;
    if (typeof output === 'string') return output;
    if (output !== undefined) return toJsonPreview(output, 320);
    return '(tool output なし)';
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

function toFullText(value: unknown): string {
  if (typeof value === 'string') return value;
  try {
    const text = JSON.stringify(value, null, 2);
    return text || '-';
  } catch {
    return String(value ?? '-');
  }
}

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
    setDetailViewer({
      title,
      content: toFullText(value),
    });
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
        throw new Error(`詳細トレースの取得に失敗しました (${response.status})`);
      }
      const json: BlogUsageTraceResponse = await response.json();
      setData(json);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'トレース取得に失敗しました');
    } finally {
      setLoading(false);
    }
  }, [getToken, processId]);

  useEffect(() => {
    fetchTrace();
  }, [fetchTrace]);

  const llmCalls = useMemo(() => {
    return (data?.executions || [])
      .flatMap((execution) => execution.llm_calls)
      .sort((a, b) => {
        const ta = a.called_at || '';
        const tb = b.called_at || '';
        if (ta === tb) return a.call_sequence - b.call_sequence;
        return ta > tb ? 1 : -1;
      });
  }, [data]);

  const toolCalls = useMemo(() => {
    return (data?.executions || [])
      .flatMap((execution) => execution.tool_calls)
      .sort((a, b) => {
        const ta = a.called_at || '';
        const tb = b.called_at || '';
        if (ta === tb) return a.call_sequence - b.call_sequence;
        return ta > tb ? 1 : -1;
      });
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

  if (loading) {
    return (
      <div className="space-y-5">
        <div className="flex items-center gap-2">
          <Skeleton className="h-8 w-48" />
        </div>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          {[...Array(5)].map((_, i) => (
            <Card key={i}><CardContent className="pt-4"><Skeleton className="h-6 w-full" /></CardContent></Card>
          ))}
        </div>
        <Skeleton className="h-[220px] rounded-xl" />
        <Skeleton className="h-[260px] rounded-xl" />
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Blog AI Trace Detail</h2>
          <p className="text-sm text-muted-foreground">process_id: {processId}</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" asChild>
            <Link href="/admin/blog-usage">
              <ArrowLeft className="h-4 w-4 mr-1.5" />
              一覧へ戻る
            </Link>
          </Button>
          <Button variant="outline" size="sm" onClick={fetchTrace}>
            <RefreshCw className="h-4 w-4 mr-1.5" />
            更新
          </Button>
        </div>
      </div>

      {error ? (
        <Card className="border-red-200">
          <CardContent className="pt-6">
            <p className="text-sm text-red-700">{error}</p>
          </CardContent>
        </Card>
      ) : data ? (
        <>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            <Card><CardContent className="pt-4"><p className="text-[11px] text-muted-foreground">ステータス</p><p className="text-sm font-medium">{data.status || '-'}</p></CardContent></Card>
            <Card><CardContent className="pt-4"><p className="text-[11px] text-muted-foreground">総トークン</p><p className="text-sm font-medium tabular-nums">{formatNumber(data.total_tokens)}</p></CardContent></Card>
            <Card><CardContent className="pt-4"><p className="text-[11px] text-muted-foreground">総コスト</p><p className="text-sm font-medium tabular-nums">{formatUsd(data.estimated_cost_usd)}</p></CardContent></Card>
            <Card><CardContent className="pt-4"><p className="text-[11px] text-muted-foreground">LLM Call数</p><p className="text-sm font-medium tabular-nums">{llmCalls.length}</p></CardContent></Card>
            <Card><CardContent className="pt-4"><p className="text-[11px] text-muted-foreground">Tool Call数</p><p className="text-sm font-medium tabular-nums">{toolCalls.length}</p></CardContent></Card>
          </div>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">会話履歴 ({data.conversation_history.length})</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 max-h-56 overflow-y-auto">
              {data.conversation_history.length === 0 ? (
                <p className="text-xs text-muted-foreground">会話履歴は保存されていません</p>
              ) : (
                data.conversation_history.map((item, idx) => {
                  const label = getConversationItemLabel(item, conversationToolNameByCallId);
                  const fullText = extractConversationText(item);
                  const preview =
                    fullText.length > 220 ? `${fullText.slice(0, 220)}…` : fullText;
                  const callId = typeof item.call_id === 'string' ? item.call_id : null;
                  return (
                    <div key={idx} className="rounded-md border p-2">
                      <div className="mb-1 flex items-center justify-between gap-2">
                        <p className="text-[11px] text-muted-foreground">
                          {label} #{idx + 1}
                        </p>
                        <Button
                          size="sm"
                          variant="outline"
                          className="h-6 px-2 text-[10px]"
                          onClick={() =>
                            openDetailViewer(
                              `会話履歴 #${idx + 1} (${label})`,
                              item
                            )
                          }
                        >
                          全文
                        </Button>
                      </div>
                      {callId ? (
                        <p className="mb-1 text-[10px] text-muted-foreground font-mono">
                          {callId}
                        </p>
                      ) : null}
                      <pre className="text-[11px] whitespace-pre-wrap break-words leading-5">
                        {preview}
                      </pre>
                    </div>
                  );
                })
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">レスポンス別トークン (LLM Calls)</CardTitle>
            </CardHeader>
            <CardContent className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="text-xs">日時</TableHead>
                    <TableHead className="text-xs">モデル</TableHead>
                    <TableHead className="text-xs text-right">Input</TableHead>
                    <TableHead className="text-xs text-right">Output</TableHead>
                    <TableHead className="text-xs text-right">Cached</TableHead>
                    <TableHead className="text-xs text-right">Reasoning</TableHead>
                    <TableHead className="text-xs text-right">Total</TableHead>
                    <TableHead className="text-xs text-right">Cost</TableHead>
                    <TableHead className="text-xs">Response ID</TableHead>
                    <TableHead className="text-xs text-right">詳細</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {llmCalls.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={10} className="text-xs text-center text-muted-foreground">
                        LLM callログがありません
                      </TableCell>
                    </TableRow>
                  ) : (
                    llmCalls.map((call) => (
                      <TableRow key={call.id}>
                        <TableCell className="text-xs whitespace-nowrap">{formatDate(call.called_at)}</TableCell>
                        <TableCell className="text-xs font-mono">{shortenModel(call.model_name)}</TableCell>
                        <TableCell className="text-xs text-right tabular-nums">{formatNumber(call.prompt_tokens)}</TableCell>
                        <TableCell className="text-xs text-right tabular-nums">{formatNumber(call.completion_tokens)}</TableCell>
                        <TableCell className="text-xs text-right tabular-nums">{formatNumber(call.cached_tokens)}</TableCell>
                        <TableCell className="text-xs text-right tabular-nums">{formatNumber(call.reasoning_tokens)}</TableCell>
                        <TableCell className="text-xs text-right tabular-nums font-medium">{formatNumber(call.total_tokens)}</TableCell>
                        <TableCell className="text-xs text-right tabular-nums">{formatUsd(call.estimated_cost_usd)}</TableCell>
                        <TableCell className="text-[11px] font-mono" title={call.api_response_id || '-'}>
                          {formatResponseId(call.api_response_id)}
                        </TableCell>
                        <TableCell className="text-right">
                          <Button
                            size="sm"
                            variant="outline"
                            className="h-6 px-2 text-[10px]"
                            onClick={() =>
                              openDetailViewer(`LLM Call #${call.call_sequence}`, {
                                id: call.id,
                                execution_id: call.execution_id,
                                model_name: call.model_name,
                                api_response_id: call.api_response_id,
                                prompt_tokens: call.prompt_tokens,
                                completion_tokens: call.completion_tokens,
                                cached_tokens: call.cached_tokens,
                                reasoning_tokens: call.reasoning_tokens,
                                total_tokens: call.total_tokens,
                                estimated_cost_usd: call.estimated_cost_usd,
                                response_data: call.response_data,
                              })
                            }
                          >
                            全文
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">ツール呼び出し詳細</CardTitle>
            </CardHeader>
            <CardContent className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="text-xs">日時</TableHead>
                    <TableHead className="text-xs">Tool</TableHead>
                    <TableHead className="text-xs">Status</TableHead>
                    <TableHead className="text-xs text-right">実行時間</TableHead>
                    <TableHead className="text-xs">入力</TableHead>
                    <TableHead className="text-xs">出力</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {toolCalls.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={6} className="text-xs text-center text-muted-foreground">
                        Tool callログがありません
                      </TableCell>
                    </TableRow>
                  ) : (
                    toolCalls.map((tool) => {
                      const inputPreview = toJsonPreview(tool.input_parameters, 180);
                      const outputPreview = toJsonPreview(tool.output_data, 180);
                      return (
                        <TableRow key={tool.id}>
                          <TableCell className="text-xs whitespace-nowrap">{formatDate(tool.called_at)}</TableCell>
                          <TableCell className="text-xs font-mono">{tool.tool_name}</TableCell>
                          <TableCell className="text-xs"><Badge variant="outline">{tool.status}</Badge></TableCell>
                          <TableCell className="text-xs text-right tabular-nums">{tool.execution_time_ms ? `${tool.execution_time_ms}ms` : '-'}</TableCell>
                          <TableCell className="text-[11px]">
                            <pre className="mb-1 whitespace-pre-wrap break-words">{inputPreview}</pre>
                            <Button
                              size="sm"
                              variant="outline"
                              className="h-6 px-2 text-[10px]"
                              onClick={() =>
                                openDetailViewer(
                                  `Tool Input: ${tool.tool_name} (#${tool.call_sequence})`,
                                  tool.input_parameters
                                )
                              }
                            >
                              全文
                            </Button>
                          </TableCell>
                          <TableCell className="text-[11px]">
                            <pre className="mb-1 whitespace-pre-wrap break-words">{outputPreview}</pre>
                            <Button
                              size="sm"
                              variant="outline"
                              className="h-6 px-2 text-[10px]"
                              onClick={() =>
                                openDetailViewer(
                                  `Tool Output: ${tool.tool_name} (#${tool.call_sequence})`,
                                  tool.output_data
                                )
                              }
                            >
                              全文
                            </Button>
                          </TableCell>
                        </TableRow>
                      );
                    })
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">時系列イベント ({data.trace_events.length})</CardTitle>
            </CardHeader>
            <CardContent className="overflow-x-auto max-h-[360px]">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="text-xs text-right">Seq</TableHead>
                    <TableHead className="text-xs">時刻</TableHead>
                    <TableHead className="text-xs">Event</TableHead>
                    <TableHead className="text-xs">Tool/Model</TableHead>
                    <TableHead className="text-xs text-right">Tokens</TableHead>
                    <TableHead className="text-xs">Message</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.trace_events.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={6} className="text-xs text-center text-muted-foreground">
                        追加トレースイベントはありません
                      </TableCell>
                    </TableRow>
                  ) : (
                    data.trace_events.map((ev) => {
                      const message = ev.message_text || toJsonPreview(ev.input_payload, 120);
                      const messagePreview =
                        message.length > 160 ? `${message.slice(0, 160)}…` : message;
                      const toolOrModel =
                        ev.tool_name || ev.model_name || ev.tool_call_id || '-';
                      return (
                        <TableRow key={ev.id}>
                          <TableCell className="text-xs text-right tabular-nums">{ev.event_sequence}</TableCell>
                          <TableCell className="text-xs whitespace-nowrap">{formatDate(ev.created_at)}</TableCell>
                          <TableCell className="text-xs font-mono">{ev.event_type}</TableCell>
                          <TableCell className="text-[11px]">{toolOrModel}</TableCell>
                          <TableCell className="text-xs text-right tabular-nums">
                            {ev.total_tokens > 0 ? formatNumber(ev.total_tokens) : '-'}
                          </TableCell>
                          <TableCell className="text-[11px]">
                            <pre className="mb-1 whitespace-pre-wrap break-words">
                              {messagePreview}
                            </pre>
                            <Button
                              size="sm"
                              variant="outline"
                              className="h-6 px-2 text-[10px]"
                              onClick={() =>
                                openDetailViewer(`Trace Event #${ev.event_sequence} (${ev.event_type})`, {
                                  message_text: ev.message_text,
                                  input_payload: ev.input_payload,
                                  output_payload: ev.output_payload,
                                  event_metadata: ev.event_metadata,
                                  tool_call_id: ev.tool_call_id,
                                  response_id: ev.response_id,
                                  model_name: ev.model_name,
                                })
                              }
                            >
                              全文
                            </Button>
                          </TableCell>
                        </TableRow>
                      );
                    })
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </>
      ) : (
        <Card>
          <CardContent className="py-12 text-center text-sm text-muted-foreground">
            データが見つかりません
          </CardContent>
        </Card>
      )}

      <Dialog open={!!detailViewer} onOpenChange={(open) => !open && setDetailViewer(null)}>
        <DialogContent className="max-w-5xl max-h-[85vh] overflow-hidden">
          <DialogHeader>
            <DialogTitle className="text-sm">
              {detailViewer?.title || '詳細'}
            </DialogTitle>
          </DialogHeader>
          <div className="rounded-md border p-3 max-h-[70vh] overflow-auto">
            <pre className="text-xs whitespace-pre-wrap break-words leading-5">
              {detailViewer?.content || '-'}
            </pre>
          </div>
        </DialogContent>
      </Dialog>

      {loading && (
        <div className="fixed bottom-4 right-4 rounded-md border bg-white px-3 py-2 text-xs text-muted-foreground shadow">
          <Loader2 className="inline h-3 w-3 animate-spin mr-1" /> 読み込み中
        </div>
      )}
    </div>
  );
}
