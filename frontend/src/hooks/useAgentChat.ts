'use client';

import { useCallback, useState } from 'react';

import { useAuth } from '@clerk/nextjs';

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

interface UseAgentChatReturn {
  messages: ChatMessage[];
  loading: boolean;
  error: string | null;
  sessionId: string | null;
  createSession: (articleId: string) => Promise<void>;
  sendMessage: (message: string) => Promise<void>;
  getCurrentContent: () => Promise<string>;
  getDiff: () => Promise<{ original: string; current: string; has_changes: boolean }>;
  saveChanges: () => Promise<void>;
  discardChanges: () => Promise<void>;
  closeSession: () => Promise<void>;
  applyApprovedChanges: () => Promise<{ content: string; applied_count: number; applied_change_ids: string[] }>;
}

export function useAgentChat(articleId: string): UseAgentChatReturn {
  const { getToken } = useAuth();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);

  const getHeaders = useCallback(async () => {
    const token = await getToken();
    return {
      'Content-Type': 'application/json',
      ...(token && { Authorization: `Bearer ${token}` }),
    };
  }, [getToken]);

  const createSession = useCallback(async (aid: string) => {
    try {
      setLoading(true);
      setError(null);

      const headers = await getHeaders();

      const response = await fetch(`/api/proxy/articles/${aid}/agent/session`, {
        method: 'POST',
        headers,
        body: JSON.stringify({}),
      });

      if (!response.ok) {
        throw new Error('Failed to create agent session');
      }

      const data = await response.json();
      setSessionId(data.session_id);

      // 初期メッセージ
      setMessages([
        {
          role: 'assistant',
          content: 'こんにちは！記事の編集をお手伝いします。どのような編集をご希望ですか？',
        },
      ]);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'エラーが発生しました';
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [getHeaders]);

  const sendMessage = useCallback(
    async (message: string) => {
      if (!sessionId) {
        throw new Error('Session not initialized');
      }

      try {
        setLoading(true);
        setError(null);

        // ユーザーメッセージを追加
        setMessages((prev) => [...prev, { role: 'user', content: message }]);

        const headers = await getHeaders();

        const response = await fetch(`/api/proxy/articles/${articleId}/agent/session/${sessionId}/chat`, {
          method: 'POST',
          headers,
          body: JSON.stringify({ message }),
        });

        if (!response.ok) {
          throw new Error('Failed to send message');
        }

        const data = await response.json();

        // アシスタントメッセージを追加
        setMessages((prev) => [...prev, { role: 'assistant', content: data.message }]);
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'エラーが発生しました';
        setError(errorMessage);
        throw err;
      } finally {
        setLoading(false);
      }
    },
    [sessionId, articleId, getHeaders]
  );

  const getCurrentContent = useCallback(async () => {
    if (!sessionId) {
      throw new Error('Session not initialized');
    }

    const headers = await getHeaders();

    const response = await fetch(`/api/proxy/articles/${articleId}/agent/session/${sessionId}/content`, {
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

    const response = await fetch(`/api/proxy/articles/${articleId}/agent/session/${sessionId}/diff`, {
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

    const response = await fetch(`/api/proxy/articles/${articleId}/agent/session/${sessionId}/save`, {
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

    const response = await fetch(`/api/proxy/articles/${articleId}/agent/session/${sessionId}/discard`, {
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

    await fetch(`/api/proxy/articles/${articleId}/agent/session/${sessionId}`, {
      method: 'DELETE',
      headers,
    });

    setSessionId(null);
    setMessages([]);
  }, [sessionId, articleId, getHeaders]);

  // === Change Approval Flow ===

  const extractPendingChanges = useCallback(async () => {
    if (!sessionId) {
      throw new Error('Session not initialized');
    }

    const headers = await getHeaders();

    const response = await fetch(`/api/proxy/articles/${articleId}/agent/session/${sessionId}/extract-changes`, {
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

    const response = await fetch(`/api/proxy/articles/${articleId}/agent/session/${sessionId}/pending-changes`, {
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

    const response = await fetch(`/api/proxy/articles/${articleId}/agent/session/${sessionId}/changes/${changeId}/approve`, {
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

    const response = await fetch(`/api/proxy/articles/${articleId}/agent/session/${sessionId}/changes/${changeId}/reject`, {
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

    const response = await fetch(`/api/proxy/articles/${articleId}/agent/session/${sessionId}/apply-approved`, {
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

    const response = await fetch(`/api/proxy/articles/${articleId}/agent/session/${sessionId}/clear-changes`, {
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

    const response = await fetch(`/api/proxy/articles/${articleId}/agent/session/${sessionId}/unified-diff`, {
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
    createSession,
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
