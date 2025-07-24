/**
 * Supabase Realtime-based article generation hook.
 * 
 * This hook replaces WebSocket communication with Supabase Realtime database sync,
 * providing real-time updates of article generation progress through database changes.
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { createClient } from '@supabase/supabase-js';
import { RealtimeChannel } from '@supabase/supabase-js';

// Types matching the backend implementation
export interface GenerationProcess {
  id: string;
  user_id: string;
  status: string;
  current_step: string;
  current_step_name: string;
  progress_percentage: number;
  is_waiting_for_input: boolean;
  input_type?: string;
  generated_content: any;
  process_metadata: any;
  last_activity_at: string;
}

export interface GenerationParams {
  initial_keywords: string[];
  image_mode: boolean;
  article_style: string;
  theme_count: number;
  target_audience: string;
  persona: string;
  company_info?: string;
  article_length?: number;
  research_query_count?: number;
  persona_count?: number;
}

export interface UserInputResponse {
  response_type: string;
  payload: any;
}

interface UseRealtimeGenerationReturn {
  // State
  processId: string | null;
  generationState: GenerationProcess | null;
  isConnected: boolean;
  error: string | null;
  isLoading: boolean;
  
  // Actions
  startGeneration: (params: GenerationParams) => Promise<boolean>;
  submitUserInput: (response: UserInputResponse) => Promise<boolean>;
  regenerateStep: () => Promise<boolean>;
  disconnect: () => void;
  
  // Computed properties for UI
  currentStepDisplay: string;
  progressPercentage: number;
  isWaitingForInput: boolean;
  inputType: string | null;
  userInputData: any;
  researchProgress: any;
  sectionsProgress: any;
  finalResults: any;
}

export const useRealtimeGeneration = (): UseRealtimeGenerationReturn => {
  // State
  const [processId, setProcessId] = useState<string | null>(null);
  const [generationState, setGenerationState] = useState<GenerationProcess | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  
  // Refs
  const supabaseRef = useRef<any>(null);
  const channelRef = useRef<RealtimeChannel | null>(null);
  
  // Initialize Supabase client
  useEffect(() => {
    const initSupabase = () => {
      try {
        const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
        const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
        
        if (!supabaseUrl || !supabaseAnonKey) {
          throw new Error('Supabase configuration missing');
        }
        
        supabaseRef.current = createClient(supabaseUrl, supabaseAnonKey, {
          realtime: {
            params: {
              eventsPerSecond: 10,
            },
          },
        });
      } catch (err) {
        console.error('Failed to initialize Supabase client:', err);
        setError('Failed to initialize real-time connection');
      }
    };
    
    initSupabase();
  }, []);
  
  // Subscribe to process updates
  const subscribeToProcess = useCallback((processId: string) => {
    if (!supabaseRef.current || channelRef.current) return;
    
    console.log(`Subscribing to process updates for ${processId}`);
    
    const channel = supabaseRef.current
      .channel(`process-${processId}`)
      .on(
        'postgres_changes',
        {
          event: '*',
          schema: 'public',
          table: 'generated_articles_state',
          filter: `id=eq.${processId}`
        },
        (payload: any) => {
          console.log('Received database change:', payload);
          
          if (payload.eventType === 'UPDATE' || payload.eventType === 'INSERT') {
            const newState = payload.new as GenerationProcess;
            setGenerationState(newState);
            
            // Clear any existing errors when receiving updates
            setError(null);
          }
        }
      )
      .subscribe((status: string) => {
        console.log('Subscription status:', status);
        
        if (status === 'SUBSCRIBED') {
          setIsConnected(true);
          setError(null);
        } else if (status === 'CHANNEL_ERROR') {
          setIsConnected(false);
          setError('Real-time connection error');
        } else if (status === 'TIMED_OUT') {
          setIsConnected(false);
          setError('Real-time connection timed out');
        }
      });
    
    channelRef.current = channel;
  }, []);
  
  // Unsubscribe from process updates
  const unsubscribeFromProcess = useCallback(() => {
    if (channelRef.current) {
      console.log('Unsubscribing from process updates');
      supabaseRef.current?.removeChannel(channelRef.current);
      channelRef.current = null;
      setIsConnected(false);
    }
  }, []);
  
  // Start generation
  const startGeneration = useCallback(async (params: GenerationParams): Promise<boolean> => {
    try {
      setIsLoading(true);
      setError(null);
      
      // Call the new REST API endpoint
      const response = await fetch('/api/articles/realtime/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(params),
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to start generation');
      }
      
      const result = await response.json();
      const newProcessId = result.process_id;
      
      console.log('Generation started:', result);
      
      // Set process ID and subscribe to updates
      setProcessId(newProcessId);
      subscribeToProcess(newProcessId);
      
      return true;
    } catch (err) {
      console.error('Failed to start generation:', err);
      setError(err instanceof Error ? err.message : 'Failed to start generation');
      return false;
    } finally {
      setIsLoading(false);
    }
  }, [subscribeToProcess]);
  
  // Submit user input
  const submitUserInput = useCallback(async (response: UserInputResponse): Promise<boolean> => {
    if (!processId) {
      setError('No active process');
      return false;
    }
    
    try {
      setIsLoading(true);
      setError(null);
      
      const apiResponse = await fetch(`/api/articles/realtime/${processId}/user-input`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(response),
      });
      
      if (!apiResponse.ok) {
        const errorData = await apiResponse.json();
        throw new Error(errorData.detail || 'Failed to submit user input');
      }
      
      console.log('User input submitted successfully');
      return true;
    } catch (err) {
      console.error('Failed to submit user input:', err);
      setError(err instanceof Error ? err.message : 'Failed to submit user input');
      return false;
    } finally {
      setIsLoading(false);
    }
  }, [processId]);
  
  // Regenerate step
  const regenerateStep = useCallback(async (): Promise<boolean> => {
    if (!processId) {
      setError('No active process');
      return false;
    }
    
    try {
      setIsLoading(true);
      setError(null);
      
      const response = await fetch(`/api/articles/realtime/${processId}/regenerate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to regenerate step');
      }
      
      console.log('Step regeneration started');
      return true;
    } catch (err) {
      console.error('Failed to regenerate step:', err);
      setError(err instanceof Error ? err.message : 'Failed to regenerate step');
      return false;
    } finally {
      setIsLoading(false);
    }
  }, [processId]);
  
  // Disconnect
  const disconnect = useCallback(() => {
    unsubscribeFromProcess();
    setProcessId(null);
    setGenerationState(null);
    setError(null);
  }, [unsubscribeFromProcess]);
  
  // Cleanup on unmount
  useEffect(() => {
    return () => {
      unsubscribeFromProcess();
    };
  }, [unsubscribeFromProcess]);
  
  // Computed properties
  const currentStepDisplay = generationState?.current_step_name || '';
  const progressPercentage = generationState?.progress_percentage || 0;
  const isWaitingForInput = generationState?.is_waiting_for_input || false;
  const inputType = generationState?.input_type || null;
  
  // Extract data from generated_content
  const userInputData = generationState?.generated_content?.user_input_request?.data;
  const researchProgress = generationState?.process_metadata?.research_progress;
  const sectionsProgress = generationState?.process_metadata?.sections_progress;
  const finalResults = generationState?.generated_content?.final_results;
  
  return {
    // State
    processId,
    generationState,
    isConnected,
    error,
    isLoading,
    
    // Actions
    startGeneration,
    submitUserInput,
    regenerateStep,
    disconnect,
    
    // Computed properties
    currentStepDisplay,
    progressPercentage,
    isWaitingForInput,
    inputType,
    userInputData,
    researchProgress,
    sectionsProgress,
    finalResults,
  };
};