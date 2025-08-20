'use client';

import { useCallback, useEffect, useRef, useState } from 'react';

import { supabase } from '@/libs/supabase/supabase-client';
import { useAuth } from '@clerk/nextjs';
import { RealtimeChannel } from '@supabase/supabase-js';

// Types for database records
interface GeneratedArticleState {
  id: string;
  user_id: string;
  organization_id?: string;
  status: string;
  current_step_name?: string;
  progress_percentage: number;
  is_waiting_for_input: boolean;
  input_type?: string;
  article_context?: any;
  process_metadata?: any;
  step_history?: any[];
  error_message?: string;
  created_at: string;
  updated_at: string;
  realtime_channel?: string;
  last_realtime_event?: any;
  executing_step?: string;
  background_task_id?: string;
  retry_count: number;
  user_input_timeout?: string;
  interaction_history?: any[];
}

// Data validation schema
interface DataValidationResult {
  isValid: boolean;
  errors: string[];
  warnings: string[];
}

// Connection state tracking
interface ConnectionMetrics {
  connectionAttempts: number;
  lastConnectionTime?: Date;
  totalDowntime: number;
  lastError?: string;
  dataConsistencyChecks: number;
}

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
  onDataSync?: (data: GeneratedArticleState) => void;
  onConnectionStateChange?: (isConnected: boolean, metrics: ConnectionMetrics) => void;
  autoConnect?: boolean;
  enableDataSync?: boolean;
  syncInterval?: number; // seconds
}

export const useSupabaseRealtime = ({
  processId,
  userId,
  onEvent,
  onError,
  onStatusChange,
  onDataSync,
  onConnectionStateChange,
  autoConnect = true,
  enableDataSync = false, // FORCE DISABLE: No polling allowed
  syncInterval = 0, // FORCE DISABLE: No periodic sync
}: UseSupabaseRealtimeOptions) => {
  // FORCE DISABLE POLLING - Database is single source of truth via Realtime
  console.log('🚫 Polling forced disabled - database is single source of truth');
  const actualEnableDataSync = false; // Force disabled - never poll
  const actualSyncInterval = 0; // Force disabled - no periodic sync
  const { getToken } = useAuth();
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastEventSequence, setLastEventSequence] = useState(0);
  const [currentData, setCurrentData] = useState<GeneratedArticleState | null>(null);
  const [isSyncing, setIsSyncing] = useState(false);
  const [lastSyncTime, setLastSyncTime] = useState<Date | null>(null);
  const [queuedActions, setQueuedActions] = useState<Array<() => Promise<void>>>([]);
  
  const channelRef = useRef<RealtimeChannel | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const syncIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;
  const isManuallyDisconnectedRef = useRef(false);
  const connectionMetrics = useRef<ConnectionMetrics>({
    connectionAttempts: 0,
    totalDowntime: 0,
    dataConsistencyChecks: 0,
  });

  // Data validation function
  const validateData = useCallback((data: any): DataValidationResult => {
    const errors: string[] = [];
    const warnings: string[] = [];

    if (!data) {
      errors.push('Data is null or undefined');
      return { isValid: false, errors, warnings };
    }

    // Required fields validation
    if (!data.id) errors.push('Missing process ID');
    if (!data.user_id) errors.push('Missing user ID in data');
    
    // Enhanced user ID validation with debugging
    if (!userId) {
      warnings.push(`No userId provided to validation function - authentication may not be ready`);
    } else if (data.user_id !== userId) {
      errors.push(`User ID mismatch: expected "${userId}" (length: ${userId.length}), got "${data.user_id}" (length: ${data.user_id?.length || 0})`);
    }

    // Status validation
    const validStatuses = ['pending', 'in_progress', 'completed', 'error', 'paused', 'cancelled', 'user_input_required'];
    if (data.status && !validStatuses.includes(data.status)) {
      warnings.push(`Unknown status: ${data.status}`);
    }

    // Progress validation
    if (typeof data.progress_percentage === 'number') {
      if (data.progress_percentage < 0 || data.progress_percentage > 100) {
        warnings.push(`Progress percentage out of range: ${data.progress_percentage}`);
      }
    }

    return { isValid: errors.length === 0, errors, warnings };
  }, [userId]);

  // Comprehensive data fetching via API proxy - FIXES RLS ISSUES
  const fetchProcessDataRef = useRef<(() => Promise<GeneratedArticleState | null>) | null>(null);
  
  const fetchProcessData = useCallback(async (): Promise<GeneratedArticleState | null> => {
    // Use current prop values instead of stale closure values
    if (!processId) {
      console.log('❌ [DEBUG] No processId provided');
      return null;
    }
    
    if (!userId) {
      console.log('❌ [DEBUG] No userId provided - authentication may not be ready');
      return null;
    }
    
    console.log('🔍 [DEBUG] fetchProcessData called with:', {
      processId: processId,
      userId: userId,
      hasUserId: !!userId,
      userIdLength: userId?.length || 0
    });

    try {
      setIsSyncing(true);
      connectionMetrics.current.dataConsistencyChecks++;

      console.log(`🔄 [INITIAL LOAD ONLY] Fetching process data via API proxy for: ${processId}`);
      
      // Use API proxy instead of direct Supabase access to avoid RLS issues
      const token = await getToken();
      console.log(`🔒 [FETCH] Using token for API call, length: ${token?.length || 0}, first 20 chars: ${token?.substring(0, 20) || 'none'}...`);
      
      const response = await fetch(`/api/proxy/articles/generation/${processId}`, {
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        credentials: 'include',
      });
      
      console.log(`📡 [FETCH] API response status: ${response.status} ${response.statusText}`);

      if (!response.ok) {
        throw new Error(`API call failed: ${response.status} ${response.statusText}`);
      }

      const data = await response.json();

      if (!data) {
        console.warn(`No process data found for ID: ${processId}`);
        return null;
      }

      // Validate fetched data using current values
      const validation = validateData(data);
      if (!validation.isValid) {
        console.error('Data validation failed:', validation.errors);
        throw new Error(`Invalid data: ${validation.errors.join(', ')}`);
      }

      if (validation.warnings.length > 0) {
        console.warn('Data validation warnings:', validation.warnings);
      }

      // Conflict resolution: compare with current data
      if (currentData && data.updated_at) {
        const fetchedTime = new Date(data.updated_at);
        const currentTime = currentData.updated_at ? new Date(currentData.updated_at) : new Date(0);
        
        if (fetchedTime < currentTime) {
          console.warn('Fetched data is older than current data - potential conflict');
          // In a real application, you might want to merge or ask user to resolve
        }
      }

      setCurrentData(data);
      setLastSyncTime(new Date());
      onDataSync?.(data);
      
      console.log('✅ Process data fetched and validated:', {
        id: data.id,
        status: data.status,
        currentStep: data.current_step_name,
        progress: data.progress_percentage,
        isWaitingForInput: data.is_waiting_for_input,
        updatedAt: data.updated_at,
        hasArticleContext: !!data.article_context,
        articleContextKeys: data.article_context ? Object.keys(data.article_context) : [],
        hasOutline: !!(data.article_context?.outline || data.article_context?.generated_outline)
      });

      return data;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch process data';
      console.error('Data fetch error:', errorMessage);
      setError(errorMessage);
      onError?.(err instanceof Error ? err : new Error(errorMessage));
      return null;
    } finally {
      setIsSyncing(false);
    }
  }, [processId, userId, getToken, validateData, onDataSync, currentData]); // Add dependencies for correct updates
  
  // Update the ref whenever dependencies would change
  useEffect(() => {
    fetchProcessDataRef.current = fetchProcessData;
  }, [fetchProcessData]);

  // Process queued actions when connection is restored - STABLE VERSION
  const processQueuedActionsRef = useRef<(() => Promise<void>) | null>(null);
  
  // Create stable reference that doesn't cause re-renders
  const processQueuedActions = useCallback(async () => {
    const currentActions = queuedActions;
    const currentConnected = isConnected;
    
    if (!currentConnected || currentActions.length === 0) return;

    console.log(`🔄 Processing ${currentActions.length} queued actions`);
    const actionsToProcess = [...currentActions];
    setQueuedActions([]);

    for (const action of actionsToProcess) {
      try {
        await action();
        console.log('✅ Queued action processed successfully');
      } catch (error) {
        console.error('❌ Queued action failed:', error);
        // Re-queue failed actions
        setQueuedActions(prev => [...prev, action]);
      }
    }
  }, []); // NO DEPENDENCIES - use current values directly
  
  // Update the ref whenever dependencies change
  useEffect(() => {
    processQueuedActionsRef.current = processQueuedActions;
  }, [processQueuedActions]);

  // Connection guard to prevent infinite loops
  const connectionInProgressRef = useRef(false);
  
  const connect: () => Promise<void> = useCallback(async () => {
    // LOOP PREVENTION: Check if connection is already in progress
    if (connectionInProgressRef.current || channelRef.current || !processId || isConnecting) {
      console.log('📡 Skipping connection - already connected/connecting or no process ID');
      return;
    }

    // Set connection guard
    connectionInProgressRef.current = true;
    setIsConnecting(true);
    setError(null);
    isManuallyDisconnectedRef.current = false;
    connectionMetrics.current.connectionAttempts++;
    
    const connectionStartTime = Date.now();

    try {
      console.log(`📡 Connecting to realtime for process: ${processId}`);
      // Set Realtime auth with Clerk JWT so RLS policies allow streaming
      try {
        const token = await getToken();
        if (token) {
          // Provide the JWT to Realtime so postgres_changes respects RLS
          (supabase as any).realtime.setAuth(token);
          // Explicitly (re)connect the realtime socket with auth
          if ((supabase as any).realtime?.isConnected() === false) {
            await (supabase as any).realtime.connect();
          }
          console.log('🔐 Realtime auth set with Clerk JWT');
        } else {
          console.warn('⚠️ No Clerk JWT available; realtime may be denied by RLS');
        }
      } catch (authErr) {
        console.warn('Failed to set Realtime auth token:', authErr);
      }

      // Subscribe to process events (Realtime uses existing auth)
      const channel = (supabase as any)
        .channel(`process_events:process_id=eq.${processId}`)
        .on(
          'postgres_changes',
          {
            event: 'INSERT',
            schema: 'public',
            table: 'process_events',
            filter: `process_id=eq.${processId}`,
          },
          (payload: any) => {
            const event = payload.new as ProcessEvent;
            console.log('📥 Realtime event received:', event);

            // Be tolerant to missing/zero sequence values from DB
            const currentSequence = lastEventSequence;
            const incomingSeq = typeof event.event_sequence === 'number' && event.event_sequence > 0
              ? event.event_sequence
              : currentSequence + 1;

            // Always forward the event; higher-level hook has robust de-duplication
            onEvent?.(event);

            // Track progress conservatively
            if (incomingSeq > currentSequence) {
              setLastEventSequence(incomingSeq);
            } else {
              console.warn('Out-of-order or duplicate event received:', event.event_sequence, 'last:', currentSequence);
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
          (payload: any) => {
            const processState = payload.new;
            console.log('📥 Process state row updated via postgres_changes:', processState);
            
            // Use unified ingestion instead of synthetic events
            onDataSync?.(processState);
          }
        )
        .subscribe(async (status: any, error?: any) => {
          console.log('📡 Realtime subscription status:', status);
          onStatusChange?.(status);
          
          if (status === 'SUBSCRIBED') {
            const connectionTime = Date.now() - connectionStartTime;
            connectionMetrics.current.lastConnectionTime = new Date();
            
            setIsConnected(true);
            setIsConnecting(false);
            setError(null);
            reconnectAttempts.current = 0;
            connectionInProgressRef.current = false; // Clear connection guard
            
            // SINGLE INITIAL DATA SYNC ONLY - No polling, database is single source of truth
            console.log('🔄 Starting initial data sync (one-time only)...');
            if (fetchProcessDataRef.current) {
              await fetchProcessDataRef.current();
            }
            
            // NO MISSED EVENTS FETCHING - Realtime will provide all updates
            
            // Process any queued actions - use current function
            if (processQueuedActionsRef.current) {
              processQueuedActionsRef.current();
            }
            
            // Update connection metrics and notify
            onConnectionStateChange?.(true, connectionMetrics.current);
            
            console.log(`✅ Realtime connected successfully in ${connectionTime}ms`);
          } else if (status === 'CHANNEL_ERROR' || status === 'TIMED_OUT') {
            const errorMessage = error?.message || `Subscription ${status.toLowerCase()}`;
            connectionMetrics.current.lastError = errorMessage;
            connectionMetrics.current.totalDowntime += Date.now() - connectionStartTime;
            
            setError(errorMessage);
            setIsConnecting(false);
            setIsConnected(false);
            connectionInProgressRef.current = false; // Clear connection guard
            onError?.(new Error(errorMessage));
            onConnectionStateChange?.(false, connectionMetrics.current);
            
            // Attempt to reconnect
            if (reconnectAttempts.current < maxReconnectAttempts) {
              scheduleReconnect();
            } else {
              console.error('❌ Max reconnection attempts reached');
            }
          } else if (status === 'CLOSED') {
            connectionMetrics.current.totalDowntime += Date.now() - connectionStartTime;
            
            setIsConnected(false);
            setIsConnecting(false);
            connectionInProgressRef.current = false; // Clear connection guard
            onConnectionStateChange?.(false, connectionMetrics.current);
            
            // Only attempt to reconnect if not manually disconnected
            if (!isManuallyDisconnectedRef.current && reconnectAttempts.current < maxReconnectAttempts) {
              scheduleReconnect();
            }
          }
        });

      channelRef.current = channel;

    } catch (err) {
      console.error('Failed to connect to realtime:', err);
      const errorMessage = err instanceof Error ? err.message : 'Connection failed';
      connectionMetrics.current.lastError = errorMessage;
      connectionMetrics.current.totalDowntime += Date.now() - connectionStartTime;
      
      setError(errorMessage);
      setIsConnecting(false);
      connectionInProgressRef.current = false; // Clear connection guard
      onError?.(err instanceof Error ? err : new Error(errorMessage));
      onConnectionStateChange?.(false, connectionMetrics.current);
      
      // Attempt to reconnect
      if (reconnectAttempts.current < maxReconnectAttempts) {
        scheduleReconnect();
      }
    }
  }, []); // NO DEPENDENCIES to prevent recreation

  // Reconnect scheduling with loop prevention
  const reconnectInProgressRef = useRef(false);
  
  const scheduleReconnect = useCallback(() => {
    if (isManuallyDisconnectedRef.current || reconnectInProgressRef.current) {
      console.log('📡 Skipping reconnect - manually disconnected or reconnect in progress');
      return;
    }
    
    reconnectInProgressRef.current = true;
    
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    
    const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 30000); // Exponential backoff, max 30s
    reconnectAttempts.current += 1;
    
    console.log(`📡 Scheduling reconnect attempt ${reconnectAttempts.current} in ${delay}ms`);
    
    reconnectTimeoutRef.current = setTimeout(() => {
      if (channelRef.current) {
        // Clear channel reference without triggering full disconnect to avoid recursive calls
        channelRef.current.unsubscribe();
        channelRef.current = null;
      }
      // Clear reconnect guard before attempting connection
      reconnectInProgressRef.current = false;
      // Use the callback directly instead of state dependency to avoid loops
      connect();
    }, delay);
  }, []); // NO DEPENDENCIES to prevent recreation

  const disconnect = useCallback(() => {
    // Set manual disconnect flag to prevent automatic reconnection
    isManuallyDisconnectedRef.current = true;
    
    // Clear all timeouts
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    
    if (syncIntervalRef.current) {
      clearInterval(syncIntervalRef.current);
      syncIntervalRef.current = null;
    }
    
    if (channelRef.current) {
      console.log('📡 Disconnecting from realtime');
      channelRef.current.unsubscribe();
      channelRef.current = null;
    }
    
    setIsConnected(false);
    setIsConnecting(false);
    reconnectAttempts.current = 0;
    
    // Notify about disconnection
    onConnectionStateChange?.(false, connectionMetrics.current);
  }, [onConnectionStateChange]);

  // DISABLED: No missed events fetching - Realtime provides all events
  const fetchMissedEvents = useCallback(async () => {
    console.log('🚫 fetchMissedEvents disabled - relying on Supabase Realtime only');
    // NO API POLLING - database is single source of truth via Realtime
    return;
  }, []);

  // Queue action for later execution if disconnected - STABLE VERSION
  const queueAction = useCallback(async (action: () => Promise<void>) => {
    const currentConnected = isConnected;
    const currentConnecting = isConnecting;
    
    if (currentConnected) {
      // Execute immediately if connected
      try {
        await action();
      } catch (error) {
        console.error('Action execution failed:', error);
        throw error;
      }
    } else {
      // Queue for later if disconnected
      console.log('📋 Queuing action due to disconnected state');
      setQueuedActions(prev => [...prev, action]);
      
      // Attempt to reconnect if not already trying
      if (!currentConnecting && !isManuallyDisconnectedRef.current && !connectionInProgressRef.current) {
        connect();
      }
    }
  }, []); // NO DEPENDENCIES - use current values directly

  // DISABLED: No periodic polling - database is single source of truth via Realtime
  // Setup periodic data sync if enabled
  useEffect(() => {
    // FORCING DISABLED: No periodic sync to ensure database is single source of truth
    console.log('🚫 Periodic data sync disabled - relying on Supabase Realtime only');
    return () => {
      if (syncIntervalRef.current) {
        clearInterval(syncIntervalRef.current);
        syncIntervalRef.current = null;
      }
    };
  }, []);

  // SINGLE useEffect for connection management - prevents double cleanup
  useEffect(() => {
    let shouldConnect = autoConnect && processId && !channelRef.current && !connectionInProgressRef.current;
    
    if (shouldConnect) {
      console.log('🔌 Auto-connecting on mount/processId change');
      connect();
    }
    
    // SINGLE cleanup function to prevent double disconnection
    return () => {
      console.log('🧹 Cleaning up connection on unmount/processId change');
      if (channelRef.current) {
        channelRef.current.unsubscribe();
        channelRef.current = null;
      }
      connectionInProgressRef.current = false;
      reconnectInProgressRef.current = false;
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
      if (syncIntervalRef.current) {
        clearInterval(syncIntervalRef.current);
        syncIntervalRef.current = null;
      }
      setIsConnected(false);
      setIsConnecting(false);
    };
  }, [autoConnect, processId]); // MINIMAL dependencies

  return {
    // Connection state
    isConnected,
    isConnecting,
    error,
    lastEventSequence,
    
    // Data state
    currentData,
    isSyncing,
    lastSyncTime,
    queuedActions: queuedActions.length,
    
    // Connection metrics
    connectionMetrics: connectionMetrics.current,
    
    // Methods
    connect,
    disconnect,
    fetchMissedEvents,
    fetchProcessData,
    queueAction,
    validateData,
    
    // Computed state  
    isDataStale: lastSyncTime ? (Date.now() - lastSyncTime.getTime()) > (actualSyncInterval * 1000 * 2) : true,
    canPerformActions: isConnected && !isSyncing && !error,
    reconnectAttempts: reconnectAttempts.current,
  };
};
