'use client';

import { useCallback, useEffect, useRef, useState } from 'react';

import { useAuth } from '@clerk/nextjs';

const RAW_API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000';
const API_BASE_URL = RAW_API_BASE_URL.replace(/\/+$/, '');
const USE_PROXY = process.env.NEXT_PUBLIC_USE_PROXY === 'true' || process.env.NODE_ENV === 'production';

const buildApiUrl = (path: string) => {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  return USE_PROXY ? `/api/proxy${normalizedPath}` : `${API_BASE_URL}${normalizedPath}`;
};

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface AgentSessionSummary {
  session_id: string;
  status: 'active' | 'paused' | 'closed';
  summary?: string;
  created_at?: string;
  last_activity_at?: string;
}

export interface AgentStreamEvent {
  eventId: string;
  sequence: number;
  eventType: string;
  message: string;
  createdAt: string | null;
  updatedAt?: string | null;
  payload?: Record<string, unknown>;
}

export interface AgentRunState {
  runId: string | null;
  status: 'idle' | 'running' | 'completed' | 'failed';
  startedAt: string | null;
  completedAt: string | null;
  error: string | null;
  events: AgentStreamEvent[];
}

interface UseAgentChatReturn {
  messages: ChatMessage[];
  loading: boolean;
  error: string | null;
  sessionId: string | null;
  runState: AgentRunState | null;
  initializeSession: () => Promise<void>;
  createSession: (articleId: string, resumeExisting?: boolean) => Promise<void>;
  startNewSession: () => Promise<void>;
  activateSession: (targetSessionId: string) => Promise<void>;
  sessions: AgentSessionSummary[];
  sendMessage: (message: string) => Promise<void>;
  getCurrentContent: () => Promise<string>;
  getDiff: () => Promise<{ original: string; current: string; has_changes: boolean }>;
  saveChanges: () => Promise<void>;
  discardChanges: () => Promise<void>;
  closeSession: () => Promise<void>;
  applyApprovedChanges: () => Promise<{ content: string; applied_count: number; applied_change_ids: string[] }>;
  extractPendingChanges: () => Promise<any[]>;
  getPendingChanges: () => Promise<any[]>;
  approveChange: (changeId: string) => Promise<boolean>;
  rejectChange: (changeId: string) => Promise<boolean>;
  clearPendingChanges: () => Promise<void>;
  getUnifiedDiffView: () => Promise<any>;
}

export function useAgentChat(articleId: string): UseAgentChatReturn {
  const { getToken } = useAuth();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [sessions, setSessions] = useState<AgentSessionSummary[]>([]);
  const [runState, setRunState] = useState<AgentRunState | null>(null);
  const messagesRef = useRef<ChatMessage[]>([]);

  useEffect(() => {
    messagesRef.current = messages;
  }, [messages]);

  const getHeaders = useCallback(async () => {
    const token = await getToken();
    return {
      'Content-Type': 'application/json',
      ...(token && { Authorization: `Bearer ${token}` }),
    };
  }, [getToken]);

  const normalizeMessages = useCallback((rawMessages?: any[]): ChatMessage[] => {
    if (!rawMessages || !Array.isArray(rawMessages)) {
      return [];
    }

    return rawMessages
      .map((msg) => {
        const role = msg?.role === 'assistant' ? 'assistant' : msg?.role === 'user' ? 'user' : null;
        if (!role) {
          return null;
        }
        return {
          role,
          content: typeof msg?.content === 'string' ? msg.content : '',
        } as ChatMessage;
      })
      .filter((msg): msg is ChatMessage => msg !== null);
  }, []);

  const normalizeRunState = useCallback((rawState: any): AgentRunState | null => {
    if (!rawState || typeof rawState !== 'object') {
      return null;
    }

    const events: AgentStreamEvent[] = Array.isArray(rawState.events)
      ? rawState.events
          .map((event: any) => {
            if (!event || typeof event !== 'object') {
              return null;
            }
            const sequence = typeof event.sequence === 'number' ? event.sequence : Number(event.sequence ?? 0);
            const eventType = typeof event.event_type === 'string' ? event.event_type : '';
            const fallbackId = `${eventType || 'event'}-${sequence}`;
            const eventId = typeof event.event_id === 'string' && event.event_id.length > 0 ? event.event_id : fallbackId;
            return {
              eventId,
              sequence,
              eventType,
              message: typeof event.message === 'string' ? event.message : '',
              createdAt: typeof event.created_at === 'string' ? event.created_at : null,
              updatedAt: typeof event.updated_at === 'string' ? event.updated_at : null,
              payload: event.payload && typeof event.payload === 'object' ? event.payload : undefined,
            } as AgentStreamEvent;
          })
          .filter((evt: AgentStreamEvent | null): evt is AgentStreamEvent => evt !== null)
          .sort((a, b) => a.sequence - b.sequence)
      : [];

    const status = rawState.status;
    const normalizedStatus: AgentRunState['status'] =
      status === 'running' || status === 'completed' || status === 'failed' || status === 'idle'
        ? status
        : 'idle';

    return {
      runId: rawState.run_id ?? null,
      status: normalizedStatus,
      startedAt: rawState.started_at ?? null,
      completedAt: rawState.completed_at ?? null,
      error: rawState.error ?? null,
      events,
    };
  }, []);

  const getLastAssistantContent = useCallback((chat: ChatMessage[]): string | null => {
    for (let i = chat.length - 1; i >= 0; i -= 1) {
      if (chat[i].role === 'assistant') {
        return chat[i].content ?? '';
      }
    }
    return null;
  }, []);

  const pollForAssistantResponse = useCallback(
    async (
      headers: Record<string, string>,
      previousMessagesSnapshot: ChatMessage[],
      previousAssistantContent: string | null
    ): Promise<ChatMessage[]> => {
      const pollIntervalMs = Number(process.env.NEXT_PUBLIC_AGENT_POLL_INTERVAL_MS ?? '1500');
      const maxWaitMs = Number(process.env.NEXT_PUBLIC_AGENT_MAX_WAIT_MS ?? '1200000');
      const deadline = Date.now() + maxWaitMs;

      while (Date.now() < deadline) {
        await new Promise((resolve) => setTimeout(resolve, pollIntervalMs));

        const detailResponse = await fetch(buildApiUrl(`/articles/${articleId}/agent/session`), {
          headers,
        });

        if (!detailResponse.ok) {
          // セッションがまだ準備されていない場合や一時的なエラーはリトライ
          if (detailResponse.status === 404 || detailResponse.status >= 500) {
            continue;
          }
          throw new Error('Failed to fetch agent session detail');
        }

        const detailData = await detailResponse.json();
        const updatedRunState = normalizeRunState(detailData?.run_state);
        setRunState(updatedRunState);
        if (updatedRunState?.status === 'failed') {
          const reason = updatedRunState.error || 'エージェント処理でエラーが発生しました';
          throw new Error(reason);
        }
        const normalized = normalizeMessages(detailData?.messages);
        if (normalized.length === 0) {
          continue;
        }

        const latestAssistantContent = getLastAssistantContent(normalized);
        const lastMessage = normalized[normalized.length - 1];
        const hasNewAssistant =
          lastMessage.role === 'assistant' &&
          latestAssistantContent !== null &&
          (latestAssistantContent !== previousAssistantContent ||
            normalized.length > previousMessagesSnapshot.length);

        if (hasNewAssistant) {
          return normalized;
        }
      }

      throw new Error('Agent response timeout');
    },
    [articleId, getLastAssistantContent, normalizeMessages, normalizeRunState]
  );

  const loadSessions = useCallback(async (): Promise<AgentSessionSummary[]> => {
    try {
      const headers = await getHeaders();
      const response = await fetch(buildApiUrl(`/articles/${articleId}/agent/sessions`), {
        headers,
      });

      if (!response.ok) {
        throw new Error('Failed to load agent sessions');
      }

      const data = (await response.json()) as AgentSessionSummary[];
      setSessions(data);
      return data;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'エラーが発生しました';
      setError(errorMessage);
      throw err;
    }
  }, [articleId, getHeaders]);

  const createSession = useCallback(async (aid: string, resumeExisting: boolean = true) => {
    try {
      setLoading(true);
      setError(null);

      const headers = await getHeaders();

      const response = await fetch(buildApiUrl(`/articles/${aid}/agent/session`), {
        method: 'POST',
        headers,
        body: JSON.stringify({ resume_existing: resumeExisting }),
      });

      if (!response.ok) {
        throw new Error('Failed to create agent session');
      }

      const data = await response.json();
      setSessionId(data.session_id);
      setMessages(normalizeMessages(data.messages));
      setRunState(normalizeRunState(data.run_state));
      await loadSessions();
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'エラーが発生しました';
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [getHeaders, normalizeMessages, normalizeRunState, loadSessions]);

  const activateSession = useCallback(
    async (targetSessionId: string) => {
      if (!targetSessionId) return;
      try {
        setLoading(true);
        setError(null);
        const headers = await getHeaders();
        const response = await fetch(
          buildApiUrl(`/articles/${articleId}/agent/session/${targetSessionId}/activate`),
          {
            method: 'POST',
            headers,
          }
        );

        if (!response.ok) {
          throw new Error('Failed to activate agent session');
        }

        const data = await response.json();
        setSessionId(data.session_id);
        setMessages(normalizeMessages(data.messages));
        setRunState(normalizeRunState(data.run_state));
        await loadSessions();
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'エラーが発生しました';
        setError(errorMessage);
        throw err;
      } finally {
        setLoading(false);
      }
    },
    [articleId, getHeaders, normalizeMessages, normalizeRunState, loadSessions]
  );

  const startNewSession = useCallback(async () => {
    await createSession(articleId, false);
  }, [articleId, createSession]);

  const initializeSession = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const list = await loadSessions();
      const active = list.find((session) => session.status === 'active');
      if (active) {
        await activateSession(active.session_id);
      } else if (list.length > 0) {
        await activateSession(list[0].session_id);
      } else {
        await createSession(articleId, false);
      }
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('エラーが発生しました');
      }
      throw err;
    } finally {
      setLoading(false);
    }
  }, [articleId, loadSessions, activateSession, createSession]);

  const sendMessage = useCallback(
    async (message: string) => {
      if (!sessionId) {
        throw new Error('Session not initialized');
      }

      const previousMessagesSnapshot = [...messagesRef.current];
      const previousAssistantContent = getLastAssistantContent(previousMessagesSnapshot);

      try {
        setLoading(true);
        setError(null);

        // ユーザーメッセージを追加
        setMessages((prev) => [...prev, { role: 'user', content: message }]);

        const headers = await getHeaders();

        const response = await fetch(buildApiUrl(`/articles/${articleId}/agent/session/${sessionId}/chat`), {
          method: 'POST',
          headers,
          body: JSON.stringify({ message }),
        });

        let data: any = null;
        const isJson = response.headers.get('content-type')?.includes('application/json');
        if (isJson) {
          try {
            data = await response.json();
          } catch {
            data = null;
          }
        }

        if (data?.run_state) {
          setRunState(normalizeRunState(data.run_state));
        }

        if (response.status === 202) {
          const updatedHistory = await pollForAssistantResponse(
            headers,
            previousMessagesSnapshot,
            previousAssistantContent
          );
          setMessages(updatedHistory);
        } else if (!response.ok) {
          throw new Error('Failed to send message');
        } else {
          const updatedHistory = normalizeMessages(data?.conversation_history);
          if (updatedHistory.length > 0) {
            setMessages(updatedHistory);
          } else {
            setMessages((prev) => [...prev, { role: 'assistant', content: data?.message ?? '' }]);
          }
        }
        void loadSessions().catch(() => undefined);
      } catch (err) {
        setMessages(previousMessagesSnapshot);
        const errorMessage = err instanceof Error ? err.message : 'エラーが発生しました';
        setError(errorMessage);
        throw err;
      } finally {
        setLoading(false);
      }
    },
    [
      sessionId,
      articleId,
      getHeaders,
      normalizeMessages,
      loadSessions,
      pollForAssistantResponse,
      getLastAssistantContent,
      normalizeRunState,
    ]
  );

  const getCurrentContent = useCallback(async () => {
    if (!sessionId) {
      throw new Error('Session not initialized');
    }

    const headers = await getHeaders();

    const response = await fetch(buildApiUrl(`/articles/${articleId}/agent/session/${sessionId}/content`), {
      headers,
    });

    if (!response.ok) {
      throw new Error('Failed to get current content');
    }

    const data = await response.json();
    return data.content;
  }, [sessionId, articleId, getHeaders]);

  const getDiff = useCallback(async () => {
    if (!sessionId) {
      throw new Error('Session not initialized');
    }

    const headers = await getHeaders();

    const response = await fetch(buildApiUrl(`/articles/${articleId}/agent/session/${sessionId}/diff`), {
      headers,
    });

    if (!response.ok) {
      throw new Error('Failed to get diff');
    }

    const data = await response.json();
    return {
      original: data.original,
      current: data.current,
      has_changes: data.has_changes,
    };
  }, [sessionId, articleId, getHeaders]);

  const saveChanges = useCallback(async () => {
    if (!sessionId) {
      throw new Error('Session not initialized');
    }

    const headers = await getHeaders();

    const response = await fetch(buildApiUrl(`/articles/${articleId}/agent/session/${sessionId}/save`), {
      method: 'POST',
      headers,
    });

    if (!response.ok) {
      throw new Error('Failed to save changes');
    }
  }, [sessionId, articleId, getHeaders]);

  const discardChanges = useCallback(async () => {
    if (!sessionId) {
      throw new Error('Session not initialized');
    }

    const headers = await getHeaders();

    const response = await fetch(buildApiUrl(`/articles/${articleId}/agent/session/${sessionId}/discard`), {
      method: 'POST',
      headers,
    });

    if (!response.ok) {
      throw new Error('Failed to discard changes');
    }
  }, [sessionId, articleId, getHeaders]);

  const closeSession = useCallback(async () => {
    if (!sessionId) {
      return;
    }

    const headers = await getHeaders();

    await fetch(buildApiUrl(`/articles/${articleId}/agent/session/${sessionId}`), {
      method: 'DELETE',
      headers,
    });

    setSessionId(null);
    setMessages([]);
    setRunState(null);
  }, [sessionId, articleId, getHeaders]);

  // === Change Approval Flow ===

  const extractPendingChanges = useCallback(async () => {
    if (!sessionId) {
      throw new Error('Session not initialized');
    }

    const headers = await getHeaders();

    const response = await fetch(buildApiUrl(`/articles/${articleId}/agent/session/${sessionId}/extract-changes`), {
      method: 'POST',
      headers,
    });

    if (!response.ok) {
      throw new Error('Failed to extract pending changes');
    }

    const data = await response.json();
    return data.changes;
  }, [sessionId, articleId, getHeaders]);

  const getPendingChanges = useCallback(async () => {
    if (!sessionId) {
      throw new Error('Session not initialized');
    }

    const headers = await getHeaders();

    const response = await fetch(buildApiUrl(`/articles/${articleId}/agent/session/${sessionId}/pending-changes`), {
      headers,
    });

    if (!response.ok) {
      throw new Error('Failed to get pending changes');
    }

    const data = await response.json();
    return data.changes;
  }, [sessionId, articleId, getHeaders]);

  const approveChange = useCallback(async (changeId: string) => {
    if (!sessionId) {
      throw new Error('Session not initialized');
    }

    const headers = await getHeaders();

    const response = await fetch(buildApiUrl(`/articles/${articleId}/agent/session/${sessionId}/changes/${changeId}/approve`), {
      method: 'POST',
      headers,
    });

    if (!response.ok) {
      throw new Error('Failed to approve change');
    }

    const data = await response.json();
    return data.success;
  }, [sessionId, articleId, getHeaders]);

  const rejectChange = useCallback(async (changeId: string) => {
    if (!sessionId) {
      throw new Error('Session not initialized');
    }

    const headers = await getHeaders();

    const response = await fetch(buildApiUrl(`/articles/${articleId}/agent/session/${sessionId}/changes/${changeId}/reject`), {
      method: 'POST',
      headers,
    });

    if (!response.ok) {
      throw new Error('Failed to reject change');
    }

    const data = await response.json();
    return data.success;
  }, [sessionId, articleId, getHeaders]);

  const applyApprovedChanges = useCallback(async () => {
    if (!sessionId) {
      throw new Error('Session not initialized');
    }

    const headers = await getHeaders();

    const response = await fetch(buildApiUrl(`/articles/${articleId}/agent/session/${sessionId}/apply-approved`), {
      method: 'POST',
      headers,
    });

    if (!response.ok) {
      throw new Error('Failed to apply approved changes');
    }

    const data = await response.json();
    return {
      content: data.content as string,
      applied_count: Number(data.applied_count ?? 0),
      applied_change_ids: (data.applied_change_ids as string[]) || [],
    };
  }, [sessionId, articleId, getHeaders]);

  const clearPendingChanges = useCallback(async () => {
    if (!sessionId) {
      throw new Error('Session not initialized');
    }

    const headers = await getHeaders();

    const response = await fetch(buildApiUrl(`/articles/${articleId}/agent/session/${sessionId}/clear-changes`), {
      method: 'POST',
      headers,
    });

    if (!response.ok) {
      throw new Error('Failed to clear pending changes');
    }
  }, [sessionId, articleId, getHeaders]);

  const getUnifiedDiffView = useCallback(async () => {
    if (!sessionId) {
      throw new Error('Session not initialized');
    }

    const headers = await getHeaders();

    const response = await fetch(buildApiUrl(`/articles/${articleId}/agent/session/${sessionId}/unified-diff`), {
      headers,
    });

    if (!response.ok) {
      throw new Error('Failed to get unified diff view');
    }

    const data = await response.json();
    return data;
  }, [sessionId, articleId, getHeaders]);

  return {
    messages,
    loading,
    error,
    sessionId,
    runState,
    initializeSession,
    createSession,
    startNewSession,
    activateSession,
    sessions,
    sendMessage,
    getCurrentContent,
    getDiff,
    saveChanges,
    discardChanges,
    closeSession,
    // Change approval methods
    extractPendingChanges,
    getPendingChanges,
    approveChange,
    rejectChange,
    applyApprovedChanges,
    clearPendingChanges,
    getUnifiedDiffView,
  };
}
