'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import { RealtimeChannel } from '@supabase/supabase-js';
import { supabase } from '@/libs/supabase/supabase-client';

export interface ProcessEvent {
  id: string;
  process_id: string;
  event_type: string;
  event_data: any;
  event_sequence: number;
  created_at: string;
}

interface UseSupabaseRealtimeOptions {
  processId: string;
  userId: string;
  onEvent?: (event: ProcessEvent) => void;
  onError?: (error: Error) => void;
  onStatusChange?: (status: string) => void;
  autoConnect?: boolean;
}

export const useSupabaseRealtime = ({
  processId,
  userId,
  onEvent,
  onError,
  onStatusChange,
  autoConnect = true,
}: UseSupabaseRealtimeOptions) => {
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastEventSequence, setLastEventSequence] = useState(0);
  
  const channelRef = useRef<RealtimeChannel | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;

  const connect = useCallback(async () => {
    if (channelRef.current || !processId) {
      return; // Already connected or no process ID
    }

    setIsConnecting(true);
    setError(null);

    try {
      console.log(`📡 Connecting to realtime for process: ${processId}`);

      // Subscribe to process events
      const channel = supabase
        .channel(`process_events:process_id=eq.${processId}`)
        .on(
          'postgres_changes',
          {
            event: 'INSERT',
            schema: 'public',
            table: 'process_events',
            filter: `process_id=eq.${processId}`,
          },
          (payload) => {
            const event = payload.new as ProcessEvent;
            console.log('📥 Realtime event received:', event);
            
            // Ensure event order and prevent duplicates
            if (event.event_sequence > lastEventSequence) {
              setLastEventSequence(event.event_sequence);
              onEvent?.(event);
            } else {
              console.warn('Out-of-order or duplicate event received:', event.event_sequence, 'last:', lastEventSequence);
            }
          }
        )
        .on(
          'postgres_changes',
          {
            event: 'UPDATE',
            schema: 'public',
            table: 'generated_articles_state',
            filter: `id=eq.${processId}`,
          },
          (payload) => {
            const processState = payload.new;
            console.log('📥 Process state updated:', processState);
            
            // Convert to event format for consistency
            const syntheticEvent: ProcessEvent = {
              id: `state_${Date.now()}`,
              process_id: processId,
              event_type: 'process_state_updated',
              event_data: processState,
              event_sequence: lastEventSequence + 1,
              created_at: new Date().toISOString(),
            };
            
            setLastEventSequence(syntheticEvent.event_sequence);
            onEvent?.(syntheticEvent);
          }
        )
        .subscribe((status, error) => {
          console.log('📡 Realtime subscription status:', status);
          onStatusChange?.(status);
          
          if (status === 'SUBSCRIBED') {
            setIsConnected(true);
            setIsConnecting(false);
            setError(null);
            reconnectAttempts.current = 0;
            
            // Fetch missed events after successful connection
            fetchMissedEvents();
          } else if (status === 'CHANNEL_ERROR' || status === 'TIMED_OUT') {
            const errorMessage = error?.message || `Subscription ${status.toLowerCase()}`;
            setError(errorMessage);
            setIsConnecting(false);
            setIsConnected(false);
            onError?.(new Error(errorMessage));
            
            // Attempt to reconnect
            if (reconnectAttempts.current < maxReconnectAttempts) {
              scheduleReconnect();
            }
          } else if (status === 'CLOSED') {
            setIsConnected(false);
            setIsConnecting(false);
            
            // Attempt to reconnect if not manually disconnected
            if (channelRef.current && reconnectAttempts.current < maxReconnectAttempts) {
              scheduleReconnect();
            }
          }
        });

      channelRef.current = channel;

    } catch (err) {
      console.error('Failed to connect to realtime:', err);
      const errorMessage = err instanceof Error ? err.message : 'Connection failed';
      setError(errorMessage);
      setIsConnecting(false);
      onError?.(err instanceof Error ? err : new Error(errorMessage));
      
      // Attempt to reconnect
      if (reconnectAttempts.current < maxReconnectAttempts) {
        scheduleReconnect();
      }
    }
  }, [processId, userId, onEvent, onError, onStatusChange, lastEventSequence]);

  const scheduleReconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    
    const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 30000); // Exponential backoff, max 30s
    reconnectAttempts.current += 1;
    
    console.log(`📡 Scheduling reconnect attempt ${reconnectAttempts.current} in ${delay}ms`);
    
    reconnectTimeoutRef.current = setTimeout(() => {
      if (channelRef.current) {
        disconnect();
      }
      connect();
    }, delay);
  }, [connect]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    
    if (channelRef.current) {
      console.log('📡 Disconnecting from realtime');
      channelRef.current.unsubscribe();
      channelRef.current = null;
    }
    
    setIsConnected(false);
    setIsConnecting(false);
    reconnectAttempts.current = 0;
  }, []);

  const fetchMissedEvents = useCallback(async () => {
    if (!processId) return;
    
    try {
      console.log(`📥 Fetching missed events since sequence ${lastEventSequence}`);
      
      const response = await fetch(
        `/api/proxy/articles/generation/${processId}/events?since_sequence=${lastEventSequence}&limit=50`,
        {
          headers: {
            'Content-Type': 'application/json',
          },
          credentials: 'include',
        }
      );

      if (response.ok) {
        const events: ProcessEvent[] = await response.json();
        console.log(`📥 Fetched ${events.length} missed events`);
        
        events.forEach(event => {
          if (event.event_sequence > lastEventSequence) {
            setLastEventSequence(event.event_sequence);
            onEvent?.(event);
          }
        });
      } else {
        console.warn('Failed to fetch missed events:', response.statusText);
      }
    } catch (err) {
      console.warn('Failed to fetch missed events:', err);
    }
  }, [processId, lastEventSequence, onEvent]);

  // Auto-connect on mount if enabled
  useEffect(() => {
    if (autoConnect && processId) {
      connect();
    }
    
    return () => {
      disconnect();
    };
  }, [autoConnect, processId, connect, disconnect]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  return {
    isConnected,
    isConnecting,
    error,
    lastEventSequence,
    connect,
    disconnect,
    fetchMissedEvents,
    reconnectAttempts: reconnectAttempts.current,
  };
};