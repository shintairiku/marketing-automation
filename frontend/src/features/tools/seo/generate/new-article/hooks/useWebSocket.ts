'use client';

import { useCallback, useEffect, useRef, useState } from 'react';

export interface WebSocketMessage {
  type: 'server_event' | 'client_response';
  payload: any;
}

export interface ServerEventMessage extends WebSocketMessage {
  type: 'server_event';
  payload: {
    step?: string;
    message?: string;
    themes?: any[];
    personas?: any[];
    plan?: any;
    outline?: any;
    section_index?: number;
    heading?: string;
    html_content_chunk?: string;
    is_complete?: boolean;
    title?: string;
    final_html_content?: string;
    error_message?: string;
  };
}

export interface ClientResponseMessage extends WebSocketMessage {
  type: 'client_response';
  response_type: string;
  payload: any;
}

interface UseWebSocketOptions {
  processId?: string;
  userId?: string;
  onMessage?: (message: ServerEventMessage) => void;
  onError?: (error: Event) => void;
  onClose?: (event: CloseEvent) => void;
}

export const useWebSocket = ({
  processId,
  userId,
  onMessage,
  onError,
  onClose,
}: UseWebSocketOptions) => {
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    setIsConnecting(true);
    setError(null);

    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8008';
    const wsUrl = new URL(apiUrl.replace('http', 'ws') + '/articles/ws/generate');
    if (processId) wsUrl.searchParams.set('process_id', processId);
    if (userId) wsUrl.searchParams.set('user_id', userId);

    const ws = new WebSocket(wsUrl.toString());
    wsRef.current = ws;

    ws.onopen = () => {
      setIsConnected(true);
      setIsConnecting(false);
      setError(null);
    };

    ws.onmessage = (event) => {
      try {
        const message: ServerEventMessage = JSON.parse(event.data);
        onMessage?.(message);
      } catch (err) {
        console.error('Failed to parse WebSocket message:', err);
        setError('Failed to parse server message');
      }
    };

    ws.onerror = (event) => {
      setError('WebSocket connection error');
      setIsConnecting(false);
      onError?.(event);
    };

    ws.onclose = (event) => {
      setIsConnected(false);
      setIsConnecting(false);
      if (event.code !== 1000) {
        setError(`Connection closed unexpectedly: ${event.reason || 'Unknown reason'}`);
      }
      onClose?.(event);
    };
  }, [processId, userId, onMessage, onError, onClose]);

  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close(1000, 'User disconnected');
      wsRef.current = null;
    }
  }, []);

  const sendMessage = useCallback((message: ClientResponseMessage) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    } else {
      console.error('WebSocket is not connected');
      setError('Cannot send message: not connected');
    }
  }, []);

  const startGeneration = useCallback((requestData: any) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(requestData));
    } else {
      console.error('WebSocket is not connected');
      setError('Cannot start generation: not connected');
    }
  }, []);

  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  return {
    isConnected,
    isConnecting,
    error,
    connect,
    disconnect,
    sendMessage,
    startGeneration,
  };
};