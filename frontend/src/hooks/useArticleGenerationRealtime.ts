'use client';

import { useCallback, useState, useEffect } from 'react';
import { useAuth } from '@clerk/nextjs';
import { useSupabaseRealtime, ProcessEvent } from './useSupabaseRealtime';

// Import existing types from the current implementation
import { GenerationStep, GenerationState, PersonaData, ThemeData, ResearchProgress, SectionsProgress } from '@/features/tools/generate/seo/new-article/hooks/useArticleGeneration';

interface UseArticleGenerationRealtimeOptions {
  processId?: string;
  userId?: string;
  autoConnect?: boolean;
}

export const useArticleGenerationRealtime = ({ 
  processId, 
  userId,
  autoConnect = true 
}: UseArticleGenerationRealtimeOptions) => {
  const { getToken } = useAuth();
  
  // Generation state
  const [state, setState] = useState<GenerationState>({
    currentStep: 'start',
    steps: [
      { id: 'start', name: '開始', status: 'pending' },
      { id: 'keyword_analyzing', name: 'キーワード分析', status: 'pending' },
      { id: 'persona_generating', name: 'ペルソナ生成', status: 'pending' },
      { id: 'persona_generated', name: 'ペルソナ選択', status: 'pending' },
      { id: 'theme_generating', name: 'テーマ生成', status: 'pending' },
      { id: 'theme_proposed', name: 'テーマ選択', status: 'pending' },
      { id: 'research_planning', name: 'リサーチ計画', status: 'pending' },
      { id: 'research_plan_generated', name: '計画承認', status: 'pending' },
      { id: 'researching', name: 'リサーチ実行', status: 'pending' },
      { id: 'research_synthesizing', name: 'リサーチ要約', status: 'pending' },
      { id: 'outline_generating', name: 'アウトライン生成', status: 'pending' },
      { id: 'outline_generated', name: 'アウトライン承認', status: 'pending' },
      { id: 'writing_sections', name: 'セクション執筆', status: 'pending' },
      { id: 'editing', name: '編集', status: 'pending' },
      { id: 'completed', name: '完成', status: 'pending' },
    ],
    isWaitingForInput: false,
    personas: undefined,
    themes: undefined,
    researchPlan: undefined,
    outline: undefined,
    generatedContent: undefined,
    finalArticle: undefined,
    articleId: undefined,
    error: undefined,
    researchProgress: undefined,
    sectionsProgress: undefined,
    completedSections: [],
    imagePlaceholders: [],
  });

  // Connection state
  const [connectionState, setConnectionState] = useState({
    isInitializing: false,
    hasStarted: false,
  });

  const handleRealtimeEvent = useCallback((event: ProcessEvent) => {
    console.log('🔄 Processing realtime event:', event.event_type, event.event_data);

    setState(prev => {
      const newState = { ...prev };
      
      switch (event.event_type) {
        case 'generation_started':
          newState.currentStep = 'keyword_analyzing';
          updateStepStatus(newState, 'keyword_analyzing', 'in_progress');
          setConnectionState(s => ({ ...s, hasStarted: true }));
          break;

        case 'process_created':
        case 'process_state_updated':
        case 'status_changed':
        case 'step_changed':
          const processData = event.event_data;
          if (processData.current_step) {
            newState.currentStep = processData.current_step;
          }
          newState.isWaitingForInput = processData.is_waiting_for_input || false;
          newState.inputType = processData.input_type;
          
          // Update step statuses based on current step
          updateStepStatuses(newState, processData);
          break;

        case 'step_started':
          newState.currentStep = event.event_data.step_name;
          updateStepStatus(newState, event.event_data.step_name, 'in_progress');
          break;

        case 'step_completed':
          updateStepStatus(newState, event.event_data.step_name, 'completed');
          break;

        case 'user_input_required':
          newState.isWaitingForInput = true;
          newState.inputType = event.event_data.input_type;
          
          // Set specific data based on input type
          const inputData = event.event_data.data || {};
          switch (event.event_data.input_type) {
            case 'select_persona':
              newState.personas = inputData.personas;
              break;
            case 'select_theme':
              newState.themes = inputData.themes;
              break;
            case 'approve_plan':
              newState.researchPlan = inputData.plan;
              break;
            case 'approve_outline':
              newState.outline = inputData.outline;
              break;
          }
          break;

        case 'user_input_resolved':
          newState.isWaitingForInput = false;
          newState.inputType = undefined;
          break;

        case 'content_chunk_generated':
          // Handle streaming content (for backward compatibility)
          const chunkData = event.event_data;
          if (chunkData.html_content_chunk) {
            if (!newState.generatedContent) {
              newState.generatedContent = '';
            }
            newState.generatedContent += chunkData.html_content_chunk;
          }
          break;

        case 'generation_completed':
          newState.currentStep = 'completed';
          newState.finalArticle = {
            title: event.event_data.title || 'Generated Article',
            content: event.event_data.final_html_content || newState.generatedContent || '',
          };
          newState.articleId = event.event_data.article_id;
          newState.isWaitingForInput = false;
          newState.inputType = undefined;
          
          // Mark all steps as completed
          newState.steps = newState.steps.map(step => ({
            ...step,
            status: 'completed'
          }));
          break;

        case 'generation_error':
          newState.currentStep = 'error';
          newState.error = event.event_data.error_message;
          newState.isWaitingForInput = false;
          newState.inputType = undefined;
          
          // Mark current step as error
          if (event.event_data.step_name) {
            updateStepStatus(newState, event.event_data.step_name, 'error');
          }
          break;

        case 'generation_paused':
          newState.currentStep = 'paused';
          break;

        case 'generation_cancelled':
          newState.currentStep = 'cancelled';
          break;

        case 'research_progress':
          newState.researchProgress = {
            currentQuery: event.event_data.current_query,
            totalQueries: event.event_data.total_queries,
            query: event.event_data.query || ''
          };
          break;

        case 'section_progress':
          newState.sectionsProgress = {
            currentSection: event.event_data.current_section,
            totalSections: event.event_data.total_sections,
            sectionHeading: event.event_data.section_heading || ''
          };
          break;

        case 'image_placeholders_generated':
          newState.imagePlaceholders = event.event_data.placeholders || [];
          break;

        case 'section_completed':
          if (!newState.completedSections) {
            newState.completedSections = [];
          }
          
          const completedSection = {
            index: event.event_data.section_index,
            heading: event.event_data.section_heading,
            content: event.event_data.section_content,
            imagePlaceholders: event.event_data.image_placeholders || []
          };
          
          // Update or add completed section
          const existingIndex = newState.completedSections.findIndex(
            s => s.index === completedSection.index
          );
          
          if (existingIndex >= 0) {
            newState.completedSections[existingIndex] = completedSection;
          } else {
            newState.completedSections.push(completedSection);
          }
          
          // Update generated content
          newState.generatedContent = newState.completedSections
            .sort((a, b) => a.index - b.index)
            .map(section => section.content)
            .join('\n\n');
          break;

        default:
          console.log('Unhandled event type:', event.event_type);
          break;
      }

      return newState;
    });
  }, []);

  const updateStepStatus = (state: GenerationState, stepId: string, status: 'pending' | 'in_progress' | 'completed' | 'error') => {
    state.steps = state.steps.map(step => 
      step.id === stepId ? { ...step, status } : step
    );
  };

  const updateStepStatuses = (state: GenerationState, processData: any) => {
    const currentStep = processData.current_step;
    const currentStepIndex = state.steps.findIndex(s => s.id === currentStep);
    
    if (currentStepIndex >= 0) {
      state.steps = state.steps.map((step, index) => {
        if (step.id === currentStep) {
          return { ...step, status: 'in_progress' };
        } else if (index < currentStepIndex) {
          return { ...step, status: 'completed' };
        } else {
          return { ...step, status: 'pending' };
        }
      });
    }
  };

  const { isConnected, isConnecting, error: realtimeError, connect, disconnect } = useSupabaseRealtime({
    processId: processId || '',
    userId: userId || '',
    onEvent: handleRealtimeEvent,
    onError: (error) => {
      console.error('Realtime error:', error);
      setState(prev => ({ ...prev, error: error.message }));
    },
    autoConnect: autoConnect && !!processId,
  });

  // HTTP API functions
  const startArticleGeneration = useCallback(async (requestData: any) => {
    try {
      setConnectionState({ isInitializing: true, hasStarted: false });
      
      const response = await fetch('/api/proxy/articles/generation/start', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${await getToken()}`,
        },
        body: JSON.stringify(requestData),
      });

      if (!response.ok) {
        throw new Error(`Failed to start generation: ${response.statusText}`);
      }

      const result = await response.json();
      
      // Reset state for new generation
      setState(prev => ({
        ...prev,
        currentStep: 'start',
        steps: prev.steps.map(step => ({ ...step, status: 'pending', message: undefined })),
        personas: undefined,
        themes: undefined,
        researchPlan: undefined,
        outline: undefined,
        generatedContent: undefined,
        finalArticle: undefined,
        isWaitingForInput: false,
        inputType: undefined,
        error: undefined,
        researchProgress: undefined,
        sectionsProgress: undefined,
        completedSections: [],
        imagePlaceholders: [],
      }));

      setConnectionState({ isInitializing: false, hasStarted: false });
      
      return result;
    } catch (error) {
      console.error('Error starting generation:', error);
      setConnectionState({ isInitializing: false, hasStarted: false });
      setState(prev => ({ 
        ...prev, 
        error: error instanceof Error ? error.message : 'Failed to start generation' 
      }));
      throw error;
    }
  }, [getToken]);

  const submitUserInput = useCallback(async (inputData: any) => {
    if (!processId) {
      throw new Error('No process ID available');
    }

    try {
      const response = await fetch(`/api/proxy/articles/generation/${processId}/user-input`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${await getToken()}`,
        },
        body: JSON.stringify(inputData),
      });

      if (!response.ok) {
        throw new Error(`Failed to submit user input: ${response.statusText}`);
      }

      // Clear waiting state immediately (will be confirmed by realtime event)
      setState(prev => ({
        ...prev,
        isWaitingForInput: false,
        inputType: undefined,
      }));

      return await response.json();
    } catch (error) {
      console.error('Error submitting user input:', error);
      setState(prev => ({ 
        ...prev, 
        error: error instanceof Error ? error.message : 'Failed to submit input' 
      }));
      throw error;
    }
  }, [processId, getToken]);

  const selectPersona = useCallback(async (personaId: number) => {
    await submitUserInput({
      response_type: 'select_persona',
      payload: { selected_id: personaId },
    });
  }, [submitUserInput]);

  const selectTheme = useCallback(async (themeIndex: number) => {
    await submitUserInput({
      response_type: 'select_theme',
      payload: { selected_index: themeIndex },
    });
  }, [submitUserInput]);

  const approvePlan = useCallback(async (approved: boolean) => {
    await submitUserInput({
      response_type: 'approve_plan',
      payload: { approved },
    });
  }, [submitUserInput]);

  const approveOutline = useCallback(async (approved: boolean) => {
    await submitUserInput({
      response_type: 'approve_outline',  
      payload: { approved },
    });
  }, [submitUserInput]);

  const pauseGeneration = useCallback(async () => {
    if (!processId) return false;

    try {
      const response = await fetch(`/api/proxy/articles/generation/${processId}/pause`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${await getToken()}`,
        },
      });

      return response.ok;
    } catch (error) {
      console.error('Error pausing generation:', error);
      return false;
    }
  }, [processId, getToken]);

  const resumeGeneration = useCallback(async () => {
    if (!processId) return false;

    try {
      const response = await fetch(`/api/proxy/articles/generation/${processId}/resume`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${await getToken()}`,
        },
      });

      return response.ok;
    } catch (error) {
      console.error('Error resuming generation:', error);
      return false;
    }
  }, [processId, getToken]);

  const cancelGeneration = useCallback(async () => {
    if (!processId) return false;

    try {
      const response = await fetch(`/api/proxy/articles/generation/${processId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${await getToken()}`,
        },
      });

      return response.ok;
    } catch (error) {
      console.error('Error cancelling generation:', error);
      return false;
    }
  }, [processId, getToken]);

  return {
    // State
    state,
    connectionState,
    isConnected,
    isConnecting,
    error: realtimeError || state.error,

    // Actions
    connect,
    disconnect,
    startArticleGeneration,
    selectPersona,
    selectTheme,
    approvePlan,
    approveOutline,
    pauseGeneration,
    resumeGeneration,
    cancelGeneration,
  };
};