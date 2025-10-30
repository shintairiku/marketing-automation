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

const createTimelineId = (): string => {
  const globalCrypto = typeof globalThis !== 'undefined' ? (globalThis.crypto as Crypto | undefined) : undefined;
  if (globalCrypto && typeof globalCrypto.randomUUID === 'function') {
    return globalCrypto.randomUUID();
  }
  return `run-${Date.now()}-${Math.random().toString(16).slice(2)}`;
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

export interface AgentRunTimelineEntry {
  id: string;
  triggerMessageIndex: number;
  userMessage: string;
  runId: string | null;
  runState: AgentRunState | null;
  createdAt: string;
}

interface UseAgentChatReturn {
  messages: ChatMessage[];
  loading: boolean;
  error: string | null;
  sessionId: string | null;
  runState: AgentRunState | null;
  runTimeline: AgentRunTimelineEntry[];
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
  const [runTimeline, setRunTimeline] = useState<AgentRunTimelineEntry[]>([]);
  const messagesRef = useRef<ChatMessage[]>([]);
  const activeRunEntryIdRef = useRef<string | null>(null);
  const runEntryIdByRunIdRef = useRef<Map<string, string>>(new Map());

  const cloneRunState = useCallback((state: AgentRunState | null): AgentRunState | null => {
    if (!state) return null;
    return {
      ...state,
      events: state.events.map((event) => ({
        ...event,
        payload: event.payload ? { ...event.payload } : undefined,
      })),
    };
  }, []);

  const setRunStateForEntry = useCallback(
    (entryId: string | null, clonedState: AgentRunState | null) => {
      if (!entryId) {
        return;
      }

      setRunTimeline((prev) => {
        let updated = false;
        const next = prev.map((entry) => {
          if (entry.id !== entryId) {
            return entry;
          }
          updated = true;
          const prevRunId = entry.runId;
          const nextRunId = clonedState?.runId ?? entry.runId ?? null;
          if (prevRunId && prevRunId !== nextRunId) {
            runEntryIdByRunIdRef.current.delete(prevRunId);
          }
          if (nextRunId) {
            runEntryIdByRunIdRef.current.set(nextRunId, entryId);
          }
          return {
            ...entry,
            runId: nextRunId,
            runState: clonedState,
          };
        });
        return updated ? next : prev;
      });
    },
    []
  );

  const applyRunStateUpdate = useCallback(
    (nextState: AgentRunState | null, options?: { resetActive?: boolean }) => {
      const clonedState = cloneRunState(nextState);
      setRunState(clonedState);

      let targetEntryId: string | null = null;
      const runId = nextState?.runId ?? null;
      if (runId) {
        targetEntryId = runEntryIdByRunIdRef.current.get(runId) ?? null;
      }
      if (!targetEntryId) {
        targetEntryId = activeRunEntryIdRef.current;
      }

      if (targetEntryId) {
        setRunStateForEntry(targetEntryId, clonedState);
      }

      const shouldResetActive =
        options?.resetActive ?? (!nextState || nextState.status === 'completed' || nextState.status === 'failed');
      if (shouldResetActive && targetEntryId && targetEntryId === activeRunEntryIdRef.current) {
        activeRunEntryIdRef.current = null;
      }
    },
    [cloneRunState, setRunStateForEntry]
  );

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
          .sort((a: AgentStreamEvent, b: AgentStreamEvent) => a.sequence - b.sequence)
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
        applyRunStateUpdate(updatedRunState);
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
    [articleId, getLastAssistantContent, normalizeMessages, normalizeRunState, applyRunStateUpdate]
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
      const normalizedMessages = normalizeMessages(data.messages);
      setMessages(normalizedMessages);

      const normalizedRunState = normalizeRunState(data.run_state);
      let seededEntries: AgentRunTimelineEntry[] = [];
      let seededActiveId: string | null = null;

      if (normalizedRunState && normalizedRunState.status !== 'idle') {
        let lastUserIndex = -1;
        for (let idx = normalizedMessages.length - 1; idx >= 0; idx -= 1) {
          if (normalizedMessages[idx].role === 'user') {
            lastUserIndex = idx;
            break;
          }
        }

          if (lastUserIndex >= 0) {
            const entryId = createTimelineId();
            seededEntries = [
              {
                id: entryId,
                triggerMessageIndex: lastUserIndex,
                userMessage: normalizedMessages[lastUserIndex]?.content ?? '',
                runId: normalizedRunState.runId,
                runState: cloneRunState(normalizedRunState),
                createdAt: new Date().toISOString(),
              },
            ];
            if (normalizedRunState.status === 'running') {
              seededActiveId = entryId;
            }
          }
      }

      runEntryIdByRunIdRef.current.clear();
      seededEntries.forEach((entry) => {
        if (entry.runId) {
          runEntryIdByRunIdRef.current.set(entry.runId, entry.id);
        }
      });
      setRunTimeline(seededEntries);
      activeRunEntryIdRef.current = seededActiveId;
      applyRunStateUpdate(normalizedRunState);
      await loadSessions();
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'エラーが発生しました';
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [getHeaders, normalizeMessages, normalizeRunState, cloneRunState, applyRunStateUpdate, loadSessions]);

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
        const normalizedMessages = normalizeMessages(data.messages);
        setMessages(normalizedMessages);

        const normalizedRunState = normalizeRunState(data.run_state);
        let seededEntries: AgentRunTimelineEntry[] = [];
        let seededActiveId: string | null = null;

        if (normalizedRunState && normalizedRunState.status !== 'idle') {
          let lastUserIndex = -1;
          for (let idx = normalizedMessages.length - 1; idx >= 0; idx -= 1) {
            if (normalizedMessages[idx].role === 'user') {
              lastUserIndex = idx;
              break;
            }
          }

          if (lastUserIndex >= 0) {
            const entryId = createTimelineId();
            seededEntries = [
              {
                id: entryId,
                triggerMessageIndex: lastUserIndex,
                userMessage: normalizedMessages[lastUserIndex]?.content ?? '',
                runId: normalizedRunState.runId,
                runState: cloneRunState(normalizedRunState),
                createdAt: new Date().toISOString(),
              },
            ];
            if (normalizedRunState.status === 'running') {
              seededActiveId = entryId;
            }
          }
        }

        runEntryIdByRunIdRef.current.clear();
        seededEntries.forEach((entry) => {
          if (entry.runId) {
            runEntryIdByRunIdRef.current.set(entry.runId, entry.id);
          }
        });
        setRunTimeline(seededEntries);
        activeRunEntryIdRef.current = seededActiveId;
        applyRunStateUpdate(normalizedRunState);
        await loadSessions();
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'エラーが発生しました';
        setError(errorMessage);
        throw err;
      } finally {
        setLoading(false);
      }
    },
    [articleId, getHeaders, normalizeMessages, normalizeRunState, cloneRunState, applyRunStateUpdate, loadSessions]
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
      const timelineId = createTimelineId();
      let timelineEntryAdded = false;

      try {
        setLoading(true);
        setError(null);

        // ユーザーメッセージを追加
        setMessages((prev) => [...prev, { role: 'user', content: message }]);

        const triggerIndex = previousMessagesSnapshot.length;
        activeRunEntryIdRef.current = timelineId;
        setRunTimeline((prev) => [
          ...prev,
          {
            id: timelineId,
            triggerMessageIndex: triggerIndex,
            userMessage: message,
            runId: null,
            runState: null,
            createdAt: new Date().toISOString(),
          },
        ]);
        timelineEntryAdded = true;
        applyRunStateUpdate(null, { resetActive: false });

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
          applyRunStateUpdate(normalizeRunState(data.run_state));
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
        if (timelineEntryAdded) {
          setRunTimeline((prev) => {
            const removed = prev.find((entry) => entry.id === timelineId);
            if (removed?.runId) {
              runEntryIdByRunIdRef.current.delete(removed.runId);
            }
            return prev.filter((entry) => entry.id !== timelineId);
          });
          if (activeRunEntryIdRef.current === timelineId) {
            activeRunEntryIdRef.current = null;
          }
        }
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
      applyRunStateUpdate,
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
    setRunTimeline([]);
    runEntryIdByRunIdRef.current.clear();
    activeRunEntryIdRef.current = null;
    applyRunStateUpdate(null);
  }, [sessionId, articleId, getHeaders, applyRunStateUpdate]);

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
    runTimeline,
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
