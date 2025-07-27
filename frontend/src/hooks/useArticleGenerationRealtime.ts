'use client';

import { useCallback, useEffect,useState } from 'react';

// Import types from the new types file
import { 
  CompletedSection,
  GenerationState, 
  GenerationStep, 
  PersonaData, 
  ProcessData,
  ResearchProgress, 
  SectionsProgress,
  StepStatus,
  ThemeData} from '@/types/article-generation';
import { useAuth } from '@clerk/nextjs';

import { ProcessEvent,useSupabaseRealtime } from './useSupabaseRealtime';

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
    
    // Debug specific fields for UI updates
    if (event.event_type === 'process_state_updated') {
      const data = event.event_data;
      console.log('🎯 Process state debug:', {
        current_step_name: data.current_step_name,
        status: data.status,
        is_waiting_for_input: data.is_waiting_for_input,
        input_type: data.input_type,
        process_metadata: data.process_metadata,
        article_context_personas: data.article_context?.generated_detailed_personas,
        article_context_themes: data.article_context?.generated_themes,
        article_context_outline: data.article_context?.outline,
        article_context_research_plan: data.article_context?.research_plan,
        article_context_keys: data.article_context ? Object.keys(data.article_context) : []
      });
    }

    setState((prev: GenerationState) => {
      const newState = { ...prev };
      
      switch (event.event_type) {
        case 'generation_started':
          newState.currentStep = 'keyword_analyzing';
          updateStepStatus(newState, 'keyword_analyzing', 'in_progress');
          setConnectionState(s => ({ ...s, hasStarted: true }));
          break;

        case 'process_created':
        case 'process_state_updated':
        case 'process_updated':
        case 'status_changed':
        case 'step_changed':
          const processData = event.event_data;
          // Handle both current_step and current_step_name fields from backend
          const currentStep = processData.current_step || processData.current_step_name;
          if (currentStep) {
            newState.currentStep = currentStep;
          }
          newState.isWaitingForInput = processData.is_waiting_for_input || false;
          newState.inputType = processData.input_type;
          
          // Handle user input requirements from process metadata
          if (processData.status === 'user_input_required' && processData.process_metadata?.input_type) {
            newState.isWaitingForInput = true;
            newState.inputType = processData.process_metadata.input_type;
          }
          
          // Extract data from article_context if available
          if (processData.article_context) {
            const context = processData.article_context;
            
            // Always set data based on current step and available data, not just input type
            // Set personas if available
            if (context.generated_detailed_personas) {
              console.log('🧑 Setting personas from context:', context.generated_detailed_personas);
              // Transform backend persona format to expected frontend format
              newState.personas = context.generated_detailed_personas.map((persona: any, index: number) => ({
                id: index,
                description: persona.description || persona.persona_description || JSON.stringify(persona)
              }));
            }
            
            // Set themes if available
            if (context.generated_themes) {
              console.log('🎯 Setting themes from context:', context.generated_themes);
              newState.themes = context.generated_themes;
            }
            
            // Set research plan if available
            if (context.research_plan) {
              console.log('📋 Setting research plan from context:', context.research_plan);
              newState.researchPlan = context.research_plan;
            }
            
            // Set outline if available (check both outline and generated_outline keys)
            const outlineData = context.outline || context.generated_outline;
            if (outlineData) {
              console.log('📝 Setting outline from context:', outlineData);
              newState.outline = outlineData;
            }
          }
          
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
          newState.steps = newState.steps.map((step: GenerationStep) => ({
            ...step,
            status: 'completed' as StepStatus
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

        case 'research_synthesis_started':
          // Handle research synthesis started event
          console.log('🔬 Research synthesis started');
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
            (s: CompletedSection) => s.index === completedSection.index
          );
          
          if (existingIndex >= 0) {
            newState.completedSections[existingIndex] = completedSection;
          } else {
            newState.completedSections.push(completedSection);
          }
          
          // Update generated content
          newState.generatedContent = newState.completedSections
            .sort((a: CompletedSection, b: CompletedSection) => a.index - b.index)
            .map((section: CompletedSection) => section.content)
            .join('\n\n');
          break;

        default:
          console.log('Unhandled event type:', event.event_type);
          break;
      }

      console.log('🔄 State updated:', {
        currentStep: newState.currentStep,
        isWaitingForInput: newState.isWaitingForInput,
        inputType: newState.inputType,
        hasPersonas: !!newState.personas,
        personaCount: newState.personas?.length || 0,
        hasThemes: !!newState.themes,
        themeCount: newState.themes?.length || 0,
        hasResearchPlan: !!newState.researchPlan,
        hasOutline: !!newState.outline,
        outlineKeys: newState.outline ? Object.keys(newState.outline) : []
      });
      
      return newState;
    });
  }, []);

  const updateStepStatus = (state: GenerationState, stepId: string, status: StepStatus) => {
    state.steps = state.steps.map((step: GenerationStep) => 
      step.id === stepId ? { ...step, status } : step
    );
  };

  const updateStepStatuses = (state: GenerationState, processData: ProcessData) => {
    // Handle both current_step and current_step_name fields from backend
    const currentStep = processData.current_step || processData.current_step_name;
    const currentStepIndex = state.steps.findIndex((s: GenerationStep) => s.id === currentStep);
    
    console.log('📊 Updating step statuses:', { currentStep, currentStepIndex, status: processData.status });
    
    if (currentStepIndex >= 0) {
      state.steps = state.steps.map((step: GenerationStep, index: number) => {
        if (step.id === currentStep) {
          // If waiting for user input, mark current step as completed but waiting
          const status = processData.status === 'user_input_required' ? 'completed' : 'in_progress';
          return { ...step, status: status as StepStatus };
        } else if (index < currentStepIndex) {
          return { ...step, status: 'completed' as StepStatus };
        } else {
          return { ...step, status: 'pending' as StepStatus };
        }
      });
    }
  };

  const handleRealtimeError = useCallback((error: Error) => {
    console.error('Realtime error:', error);
    setState((prev: GenerationState) => ({ ...prev, error: error.message }));
  }, []);

  const { isConnected, isConnecting, error: realtimeError, connect, disconnect } = useSupabaseRealtime({
    processId: processId || '',
    userId: userId || '',
    onEvent: handleRealtimeEvent,
    onError: handleRealtimeError,
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
      setState((prev: GenerationState) => ({
        ...prev,
        currentStep: 'start',
        steps: prev.steps.map((step: GenerationStep) => ({ ...step, status: 'pending' as StepStatus, message: undefined })),
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
      setState((prev: GenerationState) => ({ 
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
      setState((prev: GenerationState) => ({
        ...prev,
        isWaitingForInput: false,
        inputType: undefined,
      }));

      return await response.json();
    } catch (error) {
      console.error('Error submitting user input:', error);
      setState((prev: GenerationState) => ({ 
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