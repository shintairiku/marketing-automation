'use client';

import { useCallback, useEffect, useState } from 'react';

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

// Action result interface
interface ActionResult {
  success: boolean;
  error?: string;
  data?: any;
}

// Data sync result interface  
interface DataSyncResult {
  synced: boolean;
  conflicts: string[];
  resolved: boolean;
}

// Enhanced connection state interface
interface EnhancedConnectionState {
  isInitializing: boolean;
  hasStarted: boolean;
  isDataSynced: boolean;
  canPerformActions: boolean;
  queuedActionsCount: number;
}

export const useArticleGenerationRealtime = ({ 
  processId, 
  userId,
  autoConnect = true 
}: UseArticleGenerationRealtimeOptions) => {
  const { getToken } = useAuth();
  
  // Generation state
  const [state, setState] = useState<GenerationState>({
    currentStep: 'keyword_analyzing',
    steps: [
      { id: 'keyword_analyzing', name: 'キーワード分析', status: 'pending' },
      { id: 'persona_generating', name: 'ペルソナ生成', status: 'pending' },
      { id: 'theme_generating', name: 'テーマ提案', status: 'pending' },
      { id: 'research_planning', name: 'リサーチ計画', status: 'pending' },
      { id: 'researching', name: 'リサーチ実行（リサーチ要約）', status: 'pending' },
      { id: 'outline_generating', name: 'アウトライン作成', status: 'pending' },
      { id: 'writing_sections', name: '執筆', status: 'pending' },
      { id: 'editing', name: '編集・校正', status: 'pending' },
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
    isDataSynced: false,
  });

  // Action tracking state
  const [queuedActions, setQueuedActions] = useState(0);
  const [pendingActions, setPendingActions] = useState(new Set<string>());
  const [dataVersion, setDataVersion] = useState(0);
  
  // Event deduplication with time-based throttling
  const [lastProcessedEventId, setLastProcessedEventId] = useState<string>('');
  const [lastProcessedState, setLastProcessedState] = useState<string>('');
  const [lastProcessedTime, setLastProcessedTime] = useState<number>(0);
  const [processedEventIds, setProcessedEventIds] = useState<Set<string>>(new Set());

  // Helper function to map backend steps to UI steps with proper loading state handling
  const mapBackendStepToUIStep = (backendStep: string, status?: string): string => {
    const stepMapping: Record<string, string> = {
      // Initial state
      'start': 'keyword_analyzing',
      
      // Keyword Analysis Phase
      'keyword_analyzing': 'keyword_analyzing',
      'keyword_analyzed': 'persona_generating', // Auto-transition to persona loading
      
      // Persona Generation Phase
      'persona_generating': 'persona_generating',
      'persona_generated': 'persona_generating', // Keep as generating until selected
      'persona_selected': 'theme_generating', // Auto-transition to theme loading
      
      // Theme Generation Phase  
      'theme_generating': 'theme_generating',
      'theme_proposed': 'theme_generating', // Keep as generating until selected
      'theme_selected': 'research_planning', // Auto-transition to research planning loading
      
      // Research Planning Phase
      'research_planning': 'research_planning',
      'research_plan_generated': 'research_planning', // Show completed research planning (user approval UI)
      'research_plan_approved': 'researching', // Auto-transition to research execution loading
      
      // Research Execution Phase
      'researching': 'researching',
      'research_synthesizing': 'researching',
      'research_report_generated': 'outline_generating', // Auto-transition to outline generation
      
      // Outline Generation Phase
      'outline_generating': 'outline_generating',
      'outline_generated': 'outline_generating', // Show completed outline (user approval UI)
      'outline_approved': 'writing_sections', // Auto-transition to writing sections
      
      // Writing Sections Phase
      'writing_sections': 'writing_sections',
      'all_sections_completed': 'editing', // Auto-transition to editing loading
      
      // Editing Phase
      'editing': 'editing',
      'editing_completed': 'editing',
      
      // Final states
      'completed': 'editing',
      'error': 'keyword_analyzing',
      'paused': 'keyword_analyzing',
      'cancelled': 'keyword_analyzing',
    };
    
    // Handle special cases based on status
    if (status === 'user_input_required') {
      // Keep current step when waiting for user input
      const inputSteps = ['persona_generated', 'theme_proposed', 'research_plan_generated', 'outline_generated'];
      if (inputSteps.includes(backendStep)) {
        return stepMapping[backendStep] || 'keyword_analyzing';
      }
    }
    
    return stepMapping[backendStep] || 'keyword_analyzing';
  };

  // STABLE event handler that doesn't depend on changing functions
  const handleRealtimeEvent = useCallback((event: ProcessEvent) => {
    // GLOBAL event deduplication by event ID
    const eventKey = `${event.event_type}-${event.id || event.event_sequence}-${JSON.stringify(event.event_data).substring(0, 100)}`;
    
    if (processedEventIds.has(eventKey)) {
      console.log('⏭️  Skipping duplicate event (already processed):', event.event_type, eventKey.substring(0, 50));
      return;
    }
    
    console.log('🔄 Processing realtime event:', event.event_type, event.event_data);
    
    // Add to processed events
    setProcessedEventIds(prev => new Set([...prev].slice(-100)).add(eventKey)); // Keep last 100 events
    
    // Enhanced event deduplication for process_state_updated
    if (event.event_type === 'process_state_updated') {
      const data = event.event_data;
      const now = Date.now();
      
      // Create comprehensive state fingerprint
      const stateFingerprint = `${data.current_step_name}-${data.status}-${data.is_waiting_for_input}-${data.input_type}`;
      
      // Time-based throttling (minimum 500ms between same state updates)
      const timeSinceLastProcess = now - lastProcessedTime;
      if (stateFingerprint === lastProcessedState && timeSinceLastProcess < 500) {
        console.log('⏭️  Skipping duplicate state update (throttled):', stateFingerprint, `${timeSinceLastProcess}ms ago`);
        return;
      }
      
      // CRITICAL: Skip older events during mass replay to prevent state regression
      if (data.updated_at) {
        const eventTime = new Date(data.updated_at).getTime();
        const currentStateTime = lastProcessedTime;
        
        // Only allow events that are newer than our current state, with some tolerance for simultaneity
        if (eventTime < currentStateTime - 10000) { // 10 second tolerance
          console.log('⏭️  Skipping old event to prevent state regression:', {
            eventTime: new Date(eventTime).toISOString(),
            currentStateTime: new Date(currentStateTime).toISOString(),
            step: data.current_step_name,
            status: data.status
          });
          return;
        }
      }
      
      // Update deduplication state
      setLastProcessedState(stateFingerprint);
      setLastProcessedTime(now);
    }
    
    // Update data version for tracking
    setDataVersion(prev => prev + 1);
    
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
          newState.steps = newState.steps.map((step: GenerationStep) => 
            step.id === 'keyword_analyzing' ? { ...step, status: 'in_progress' as StepStatus } : step
          );
          setConnectionState(s => ({ ...s, hasStarted: true }));
          break;

        case 'process_created':
        case 'process_state_updated':
        case 'process_updated':
        case 'status_changed':
        case 'step_changed':
          const processData = event.event_data;
          
          // PRIORITY: For process_state_updated events, this represents the LATEST database state
          // We should prioritize this over any intermediate step events
          const isLatestDatabaseState = event.event_type === 'process_state_updated';
          // Handle both current_step and current_step_name fields from backend
          // CRITICAL: also fallback to article_context.current_step when root fields are missing
          const backendStep = processData.current_step 
            || processData.current_step_name 
            || processData.article_context?.current_step;
          if (backendStep) {
            const uiStep = mapBackendStepToUIStep(backendStep, processData.status);
            
            // CRITICAL FIX: Ensure step progression never goes backwards
            const currentStepOrder = ['keyword_analyzing', 'persona_generating', 'theme_generating', 'research_planning', 'researching', 'outline_generating', 'writing_sections', 'editing'];
            const currentIndex = currentStepOrder.indexOf(newState.currentStep);
            const newIndex = currentStepOrder.indexOf(uiStep);
            
            // Special handling for delayed completion events
            const isDelayedCompletionEvent = [
              'research_plan_generated', 
              'persona_generated',
              'theme_proposed'
            ].includes(backendStep) && newIndex < currentIndex;
            
            // Only update if the new step is forward progression OR it's the latest database state
            // Skip delayed completion events that would cause regression
            if (isDelayedCompletionEvent) {
              console.log('⏭️ Skipped delayed completion event (already progressed):', { 
                current: newState.currentStep, 
                backendStep,
                currentIndex, 
                newIndex,
                reason: 'delayed_completion'
              });
            } else if (isLatestDatabaseState || newIndex >= currentIndex || newState.currentStep === 'keyword_analyzing') {
              newState.currentStep = uiStep;
              console.log('✅ Step updated:', { from: newState.currentStep, to: uiStep, backendStep, isLatest: isLatestDatabaseState });
            } else {
              console.log('⏭️ Skipped backward step progression:', { 
                current: newState.currentStep, 
                attempted: uiStep, 
                backendStep,
                currentIndex, 
                newIndex 
              });
            }
            
            // Auto-progression logic: move to next step if current step is completed and not waiting for input
            if (!processData.is_waiting_for_input && processData.status !== 'user_input_required') {
              // Inline auto-progression to avoid function dependency
              const autoProgressSteps = [
                'keyword_analyzed',
                'persona_selected', 
                'theme_selected',
                'research_plan_approved',
                'research_report_generated',
                'outline_approved',
                'all_sections_completed'
              ];
              
              if (autoProgressSteps.includes(backendStep)) {
                const nextStepMap: Record<string, string> = {
                  'keyword_analyzed': 'persona_generating',
                  'persona_selected': 'theme_generating',
                  'theme_selected': 'research_planning', 
                  'research_plan_approved': 'researching',
                  'research_report_generated': 'outline_generating',
                  'outline_approved': 'writing_sections',
                  'all_sections_completed': 'editing'
                };
                
                const nextUIStep = nextStepMap[backendStep];
                if (nextUIStep) {
                  console.log('🔄 Auto-progressing step:', { backendStep, nextUIStep, status: processData.status });
                  newState.currentStep = nextUIStep;
                  // Inline updateStepStatus to avoid function dependency
                  newState.steps = newState.steps.map((step: GenerationStep) => 
                    step.id === nextUIStep ? { ...step, status: 'in_progress' as StepStatus } : step
                  );
                }
              }
            }
          }
          // Infer waiting state if field not present
          const waitingFromDb = processData.is_waiting_for_input;
          if (typeof waitingFromDb === 'boolean') {
            newState.isWaitingForInput = waitingFromDb;
          } else {
            const stepForWaiting = backendStep || processData.article_context?.current_step;
            const inputSteps = ['persona_generated', 'theme_proposed', 'research_plan_generated', 'outline_generated'];
            newState.isWaitingForInput = !!stepForWaiting && inputSteps.includes(stepForWaiting);
          }
          newState.inputType = processData.input_type;
          
          // Handle user input requirements from process metadata
          if (processData.status === 'user_input_required') {
            newState.isWaitingForInput = true;
            // Prioritize process_metadata.input_type, then fall back to root input_type
            newState.inputType = processData.process_metadata?.input_type || processData.input_type;
            
            // If no inputType is provided, infer from current_step_name
            if (!newState.inputType && processData.current_step_name) {
              const stepInputTypeMap: Record<string, string> = {
                'persona_generated': 'select_persona',
                'theme_proposed': 'select_theme', 
                'research_plan_generated': 'approve_plan',
                'outline_generated': 'approve_outline'
              };
              newState.inputType = stepInputTypeMap[processData.current_step_name];
              console.log('🔍 Inferred inputType from current_step_name:', processData.current_step_name, '->', newState.inputType);
            }
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
            console.log('🔍 [DEBUG] Outline data check:', {
              hasOutline: !!context.outline,
              hasGeneratedOutline: !!context.generated_outline,
              outlineValue: context.outline,
              generatedOutlineValue: context.generated_outline,
              finalOutlineData: outlineData
            });
            
            if (outlineData) {
              console.log('📝 Setting outline from context:', outlineData);
              newState.outline = outlineData;
            } else {
              console.warn('⚠️ No outline data found in context despite outline_generated state');
            }
            
            // Set generated content from context
            if (context.generated_sections_html && Array.isArray(context.generated_sections_html)) {
              console.log('📄 Setting generated sections from context:', context.generated_sections_html.length, 'sections');
              newState.generatedContent = context.generated_sections_html.join('\n\n');
              
              // Update completed sections
              newState.completedSections = context.generated_sections_html.map((content: string, index: number) => ({
                index: index + 1,
                heading: `Section ${index + 1}`,
                content: content,
                imagePlaceholders: []
              }));
            }
            
            // Set final article if available
            if (context.final_article_html) {
              console.log('📰 Setting final article from context');
              newState.finalArticle = {
                title: 'Generated Article',
                content: context.final_article_html
              };
              newState.generatedContent = context.final_article_html;
            }
            
            // Set sections progress if available
            if (context.current_section_index && context.generated_sections_html) {
              newState.sectionsProgress = {
                currentSection: context.current_section_index + 1,
                totalSections: context.generated_sections_html.length,
                sectionHeading: `Section ${context.current_section_index + 1}`
              };
            }
          }
          
          // Inline updateStepStatuses to avoid function dependency - ENHANCED with preservation logic
          const currentStepIndex = newState.steps.findIndex((s: GenerationStep) => s.id === newState.currentStep);
          
          if (currentStepIndex >= 0) {
            newState.steps = newState.steps.map((step: GenerationStep, index: number) => {
              if (step.id === newState.currentStep) {
                // Determine current step status based on process state
                let stepStatus: StepStatus = 'in_progress';
                
                if (processData.status === 'user_input_required') {
                  // If waiting for user input, mark as completed (user needs to take action)
                  stepStatus = 'completed';
                } else if (processData.status === 'error') {
                  stepStatus = 'error';
                } else if (processData.status === 'completed') {
                  stepStatus = 'completed';
                }
                
                return { ...step, status: stepStatus };
              } else if (index < currentStepIndex) {
                // PRESERVE existing completed steps - don't overwrite with simple linear logic
                // Only mark as completed if not already in a final state
                const existingStatus = step.status;
                if (existingStatus === 'completed' || existingStatus === 'error') {
                  return step; // Preserve existing final states
                }
                return { ...step, status: 'completed' as StepStatus };
              } else {
                // Future steps should be pending unless they have a specific state
                const existingStatus = step.status;
                if (existingStatus === 'completed' || existingStatus === 'error') {
                  return step; // Preserve existing final states
                }
                return { ...step, status: 'pending' as StepStatus };
              }
            });
          }
          
          // Loading state management based on process status
          if (processData.status === 'running' && !processData.is_waiting_for_input) {
            // Show loading state for current step
            const currentStep = newState.steps.find(s => s.id === newState.currentStep);
            if (currentStep) {
              newState.steps = newState.steps.map((step: GenerationStep) => 
                step.id === newState.currentStep ? { ...step, status: 'in_progress' as StepStatus } : step
              );
            }
          }
          break;

        // All other cases with inline step status updates
        case 'step_started':
          const startedStep = mapBackendStepToUIStep(event.event_data.step_name);
          newState.currentStep = startedStep;
          newState.steps = newState.steps.map((step: GenerationStep) => 
            step.id === startedStep ? { ...step, status: 'in_progress' as StepStatus } : step
          );
          console.log('🚀 Step started:', { backendStep: event.event_data.step_name, uiStep: startedStep });
          break;

        case 'step_completed':
          const completedStep = mapBackendStepToUIStep(event.event_data.step_name);
          newState.steps = newState.steps.map((step: GenerationStep) => 
            step.id === completedStep ? { ...step, status: 'completed' as StepStatus } : step
          );
          
          // Auto-progression: trigger next step loading state if applicable
          const progressionMap: Record<string, string | null> = {
            'keyword_analyzing': 'persona_generating',
            'persona_generating': null, // Waits for user selection
            'theme_generating': null, // Waits for user selection  
            'research_planning': null, // Waits for user approval
            'researching': 'outline_generating',
            'outline_generating': null, // Waits for user approval
            'writing_sections': 'editing',
            'editing': null, // Final step
          };
          
          const nextStep = progressionMap[completedStep] || null;
          if (nextStep && !newState.isWaitingForInput) {
            console.log('🔄 Auto-progressing from completed step:', { completedStep, nextStep });
            newState.currentStep = nextStep;
            newState.steps = newState.steps.map((step: GenerationStep) => 
              step.id === nextStep ? { ...step, status: 'in_progress' as StepStatus } : step
            );
          }
          console.log('✅ Step completed:', { backendStep: event.event_data.step_name, uiStep: completedStep, nextStep });
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
          const previousInputType = newState.inputType;
          newState.inputType = undefined;
          
          // Auto-progress to next step based on resolved input type
          if (previousInputType) {
            console.log('🔄 User input resolved, auto-progressing:', previousInputType);
            switch (previousInputType) {
              case 'select_persona':
                newState.currentStep = 'theme_generating';
                newState.steps = newState.steps.map((step: GenerationStep) => {
                  if (step.id === 'persona_generating') return { ...step, status: 'completed' as StepStatus };
                  if (step.id === 'theme_generating') return { ...step, status: 'in_progress' as StepStatus };
                  return step;
                });
                break;
              case 'select_theme':
                newState.currentStep = 'research_planning';
                newState.steps = newState.steps.map((step: GenerationStep) => {
                  if (step.id === 'theme_generating') return { ...step, status: 'completed' as StepStatus };
                  if (step.id === 'research_planning') return { ...step, status: 'in_progress' as StepStatus };
                  return step;
                });
                break;
              case 'approve_plan':
                newState.currentStep = 'researching';
                newState.steps = newState.steps.map((step: GenerationStep) => {
                  if (step.id === 'research_planning') return { ...step, status: 'completed' as StepStatus };
                  if (step.id === 'researching') return { ...step, status: 'in_progress' as StepStatus };
                  return step;
                });
                break;
              case 'approve_outline':
                newState.currentStep = 'writing_sections';
                newState.steps = newState.steps.map((step: GenerationStep) => {
                  if (step.id === 'outline_generating') return { ...step, status: 'completed' as StepStatus };
                  if (step.id === 'writing_sections') return { ...step, status: 'in_progress' as StepStatus };
                  return step;
                });
                break;
            }
          }
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
        case 'article_created':
        case 'article_saved':
          newState.currentStep = 'completed';
          
          // Set final article data
          const articleData = event.event_data;
          newState.finalArticle = {
            title: articleData.title || 'Generated Article',
            content: articleData.final_html_content || articleData.content || newState.generatedContent || '',
          };
          
          // Set article ID from various possible fields
          newState.articleId = articleData.article_id || articleData.id || event.event_data.article_id;
          
          newState.isWaitingForInput = false;
          newState.inputType = undefined;
          
          // Mark all steps as completed
          newState.steps = newState.steps.map((step: GenerationStep) => ({
            ...step,
            status: 'completed' as StepStatus
          }));
          
          console.log('🎉 Generation completed!', {
            articleId: newState.articleId,
            finalArticleLength: newState.finalArticle?.content?.length || 0
          });
          break;

        case 'generation_error':
          newState.currentStep = 'error';
          newState.error = event.event_data.error_message;
          newState.isWaitingForInput = false;
          newState.inputType = undefined;
          
          // Mark current step as error
          if (event.event_data.step_name) {
            const errorStepName = event.event_data.step_name;
            newState.steps = newState.steps.map((step: GenerationStep) => 
              step.id === errorStepName ? { ...step, status: 'error' as StepStatus } : step
            );
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
          console.log('🔬 Research synthesis started');
          break;

        case 'research_synthesis_completed':
          console.log('🔬 Research synthesis completed');
          newState.steps = newState.steps.map((step: GenerationStep) => 
            step.id === 'researching' ? { ...step, status: 'completed' as StepStatus } : step
          );
          break;

        case 'outline_generation_started':
          newState.currentStep = 'outline_generating';
          newState.steps = newState.steps.map((step: GenerationStep) => 
            step.id === 'outline_generating' ? { ...step, status: 'in_progress' as StepStatus } : step
          );
          console.log('📋 Outline generation started');
          break;

        case 'outline_generation_completed':
          console.log('📋 Outline generation completed');
          newState.steps = newState.steps.map((step: GenerationStep) => 
            step.id === 'outline_generating' ? { ...step, status: 'completed' as StepStatus } : step
          );
          break;

        case 'section_writing_started':
          newState.currentStep = 'writing_sections';
          newState.steps = newState.steps.map((step: GenerationStep) => 
            step.id === 'writing_sections' ? { ...step, status: 'in_progress' as StepStatus } : step
          );
          console.log('✍️ Section writing started');
          break;

        case 'section_writing_progress':
          newState.sectionsProgress = {
            currentSection: event.event_data.current_section || 1,
            totalSections: event.event_data.total_sections || 1,
            sectionHeading: event.event_data.section_heading || ''
          };
          console.log('✍️ Section writing progress:', newState.sectionsProgress);
          break;

        case 'editing_started':
          newState.currentStep = 'editing';
          newState.steps = newState.steps.map((step: GenerationStep) => 
            step.id === 'editing' ? { ...step, status: 'in_progress' as StepStatus } : step
          );
          console.log('✏️ Editing started');
          break;

        case 'section_completed':
          if (!newState.completedSections) {
            newState.completedSections = [];
          }
          
          const completedSection = {
            index: event.event_data.section_index + 1, // Convert to 1-based indexing for UI
            heading: event.event_data.section_heading,
            content: event.event_data.section_content || '', // Handle batch completion without content
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
          
          // Update sections progress
          if (event.event_data.completed_sections && event.event_data.total_sections) {
            newState.sectionsProgress = {
              currentSection: event.event_data.completed_sections,
              totalSections: event.event_data.total_sections,
              sectionHeading: event.event_data.section_heading || ''
            };
          }
          
          // Update generated content if available
          if (newState.completedSections.length > 0) {
            newState.generatedContent = newState.completedSections
              .sort((a: CompletedSection, b: CompletedSection) => a.index - b.index)
              .map((section: CompletedSection) => section.content)
              .filter(content => content.trim().length > 0) // Filter out empty sections
              .join('\n\n');
          }
          
          console.log('✅ Section completed (batch):', {
            sectionIndex: completedSection.index,
            heading: completedSection.heading,
            contentLength: completedSection.content.length,
            batchMode: event.event_data.batch_completion,
            progress: newState.sectionsProgress
          });
          break;

        case 'all_sections_completed':
          // Handle completion of all sections
          console.log('🎉 All sections completed!', {
            totalSections: event.event_data.total_sections,
            totalContentLength: event.event_data.total_content_length,
            totalPlaceholders: event.event_data.total_placeholders,
            imageMode: event.event_data.image_mode
          });
          
          // Update step statuses
          newState.steps = newState.steps.map((step: GenerationStep) => {
            if (step.id === 'writing_sections') return { ...step, status: 'completed' as StepStatus };
            if (step.id === 'editing') return { ...step, status: 'in_progress' as StepStatus };
            return step;
          });
          
          // Auto-progress to editing step with loading state
          console.log('🔄 Auto-progressing to editing step');
          newState.currentStep = 'editing';
          
          // Update sections progress to show completion
          if (event.event_data.total_sections) {
            newState.sectionsProgress = {
              currentSection: event.event_data.total_sections,
              totalSections: event.event_data.total_sections,
              sectionHeading: 'All sections completed'
            };
          }
          break;
          
        // New event handlers for better step transition handling with inline updates
        case 'keyword_analysis_completed':
          console.log('🎯 Keyword analysis completed - auto-progressing to persona generation');
          newState.steps = newState.steps.map((step: GenerationStep) => {
            if (step.id === 'keyword_analyzing') return { ...step, status: 'completed' as StepStatus };
            if (step.id === 'persona_generating') return { ...step, status: 'in_progress' as StepStatus };
            return step;
          });
          newState.currentStep = 'persona_generating';
          break;
          
        case 'persona_selection_completed':
          console.log('👥 Persona selected - auto-progressing to theme generation');
          newState.steps = newState.steps.map((step: GenerationStep) => {
            if (step.id === 'persona_generating') return { ...step, status: 'completed' as StepStatus };
            if (step.id === 'theme_generating') return { ...step, status: 'in_progress' as StepStatus };
            return step;
          });
          newState.currentStep = 'theme_generating';
          break;
          
        case 'theme_selection_completed':
          console.log('💡 Theme selected - auto-progressing to research planning');
          newState.steps = newState.steps.map((step: GenerationStep) => {
            if (step.id === 'theme_generating') return { ...step, status: 'completed' as StepStatus };
            if (step.id === 'research_planning') return { ...step, status: 'in_progress' as StepStatus };
            return step;
          });
          newState.currentStep = 'research_planning';
          break;
          
        case 'research_plan_approval_completed':
          console.log('📋 Research plan approved - auto-progressing to research execution');
          newState.steps = newState.steps.map((step: GenerationStep) => {
            if (step.id === 'research_planning') return { ...step, status: 'completed' as StepStatus };
            if (step.id === 'researching') return { ...step, status: 'in_progress' as StepStatus };
            return step;
          });
          newState.currentStep = 'researching';
          break;
          
        case 'outline_approval_completed':
          console.log('📝 Outline approved - auto-progressing to writing sections');
          newState.steps = newState.steps.map((step: GenerationStep) => {
            if (step.id === 'outline_generating') return { ...step, status: 'completed' as StepStatus };
            if (step.id === 'writing_sections') return { ...step, status: 'in_progress' as StepStatus };
            return step;
          });
          newState.currentStep = 'writing_sections';
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
        outlineKeys: newState.outline ? Object.keys(newState.outline) : [],
        hasGeneratedContent: !!newState.generatedContent,
        generatedContentLength: newState.generatedContent?.length || 0,
        hasFinalArticle: !!newState.finalArticle,
        completedSections: newState.completedSections?.length || 0,
        sectionsProgress: newState.sectionsProgress
      });
      
      return newState;
    });
  }, [lastProcessedState, lastProcessedTime, processedEventIds]); // Include deduplication state

  const handleRealtimeError = useCallback((error: Error) => {
    console.error('Realtime error:', error);
    setState((prev: GenerationState) => ({ ...prev, error: error.message }));
  }, []);

  const { 
    isConnected, 
    isConnecting, 
    error: realtimeError, 
    connect, 
    disconnect,
    fetchProcessData,
    isSyncing,
    lastSyncTime,
    currentData
  } = useSupabaseRealtime({
    processId: processId || '',
    userId: userId || '',
    onEvent: handleRealtimeEvent,
    onError: handleRealtimeError,
    // Only auto-connect when both processId and userId are available
    autoConnect: autoConnect && !!processId && !!userId,
  });

  // Debug logging for connection conditions
  useEffect(() => {
    console.log('🔍 [DEBUG] useArticleGenerationRealtime connection conditions:', {
      autoConnect,
      processId: !!processId,
      userId: !!userId,
      shouldConnect: autoConnect && !!processId && !!userId,
      actualProcessId: processId,
      actualUserId: userId
    });
  }, [autoConnect, processId, userId]);

  // Derived state for realtime capabilities
  const realtimeCanPerformActions = isConnected && !isConnecting && !realtimeError;

  // HTTP API functions
  const startArticleGeneration = useCallback(async (requestData: any) => {
    try {
      setConnectionState({ isInitializing: true, hasStarted: false, isDataSynced: false });
      
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
        currentStep: 'keyword_analyzing',
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

      setConnectionState({ isInitializing: false, hasStarted: false, isDataSynced: true });
      
      return result;
    } catch (error) {
      console.error('Error starting generation:', error);
      setConnectionState({ isInitializing: false, hasStarted: false, isDataSynced: false });
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

  const selectPersona = useCallback(async (personaId: number): Promise<ActionResult> => {
    // Only proceed if connected to Supabase Realtime
    if (!isConnected) {
      console.warn('Cannot select persona - not connected to realtime');
      setState((prev: GenerationState) => ({ 
        ...prev, 
        error: 'リアルタイム接続が切断されています。再接続してから再試行してください。' 
      }));
      return { success: false, error: 'リアルタイム接続が切断されています。再接続してから再試行してください。' };
    }
    
    // No optimistic updates - wait for backend confirmation via Supabase Realtime
    
    try {
      await submitUserInput({
        response_type: 'select_persona',
        payload: { selected_id: personaId },
      });
      // UI state will be updated by 'persona_selection_completed' realtime event
      return { success: true };
    } catch (error) {
      // Rollback on error
      setState((prev: GenerationState) => ({
        ...prev,
        isWaitingForInput: true,
        inputType: 'select_persona',
        error: error instanceof Error ? error.message : 'ペルソナ選択に失敗しました'
      }));
      return { success: false, error: error instanceof Error ? error.message : 'ペルソナ選択に失敗しました' };
    }
  }, [submitUserInput, isConnected]);

  const selectTheme = useCallback(async (themeIndex: number): Promise<ActionResult> => {
    // Only proceed if connected to Supabase Realtime
    if (!isConnected) {
      console.warn('Cannot select theme - not connected to realtime');
      setState((prev: GenerationState) => ({ 
        ...prev, 
        error: 'リアルタイム接続が切断されています。再接続してから再試行してください。' 
      }));
      return { success: false, error: 'リアルタイム接続が切断されています。再接続してから再試行してください。' };
    }
    
    // No optimistic updates - wait for backend confirmation via Supabase Realtime
    
    try {
      await submitUserInput({
        response_type: 'select_theme',
        payload: { selected_index: themeIndex },
      });
      // UI state will be updated by 'theme_selection_completed' realtime event
      return { success: true };
    } catch (error) {
      // Rollback on error
      setState((prev: GenerationState) => ({
        ...prev,
        isWaitingForInput: true,
        inputType: 'select_theme',
        error: error instanceof Error ? error.message : 'テーマ選択に失敗しました'
      }));
      return { success: false, error: error instanceof Error ? error.message : 'テーマ選択に失敗しました' };
    }
  }, [submitUserInput, isConnected]);

  const approvePlan = useCallback(async (approved: boolean): Promise<ActionResult> => {
    // Only proceed if connected to Supabase Realtime
    if (!isConnected) {
      console.warn('Cannot approve plan - not connected to realtime');
      setState((prev: GenerationState) => ({ 
        ...prev, 
        error: 'リアルタイム接続が切断されています。再接続してから再試行してください。' 
      }));
      return { success: false, error: 'リアルタイム接続が切断されています。再接続してから再試行してください。' };
    }
    
    // No optimistic updates - wait for backend confirmation via Supabase Realtime
    
    try {
      await submitUserInput({
        response_type: 'approve_plan',
        payload: { approved },
      });
      // UI state will be updated by 'research_plan_approval_completed' realtime event
      return { success: true };
    } catch (error) {
      // Rollback on error
      setState((prev: GenerationState) => ({
        ...prev,
        isWaitingForInput: true,
        inputType: 'approve_plan',
        error: error instanceof Error ? error.message : 'リサーチ計画承認に失敗しました'
      }));
      return { success: false, error: error instanceof Error ? error.message : 'リサーチ計画承認に失敗しました' };
    }
  }, [submitUserInput, isConnected]);

  const approveOutline = useCallback(async (approved: boolean): Promise<ActionResult> => {
    // Only proceed if connected to Supabase Realtime
    if (!isConnected) {
      console.warn('Cannot approve outline - not connected to realtime');
      setState((prev: GenerationState) => ({ 
        ...prev, 
        error: 'リアルタイム接続が切断されています。再接続してから再試行してください。' 
      }));
      return { success: false, error: 'リアルタイム接続が切断されています。再接続してから再試行してください。' };
    }
    
    // No optimistic updates - wait for backend confirmation via Supabase Realtime
    
    try {
      await submitUserInput({
        response_type: 'approve_outline',  
        payload: { approved },
      });
      // UI state will be updated by 'outline_approval_completed' realtime event
      return { success: true };
    } catch (error) {
      // Rollback on error
      setState((prev: GenerationState) => ({
        ...prev,
        isWaitingForInput: true,
        inputType: 'approve_outline',
        error: error instanceof Error ? error.message : 'アウトライン承認に失敗しました'
      }));
      return { success: false, error: error instanceof Error ? error.message : 'アウトライン承認に失敗しました' };
    }
  }, [submitUserInput, isConnected]);

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

  // Manual data refresh function - STABLE VERSION
  const refreshData = useCallback(async (): Promise<DataSyncResult> => {
    try {
      console.log('🔄 Manual data refresh requested');
      const freshData = await fetchProcessData();
      
      if (freshData) {
        // Handle data sync inline - create a synthetic event
        const syntheticEvent: ProcessEvent = {
          id: `refresh_${Date.now()}`,
          process_id: processId || '',
          event_type: 'process_state_updated',
          event_data: freshData,
          event_sequence: Date.now(),
          created_at: new Date().toISOString(),
        };
        handleRealtimeEvent(syntheticEvent);
        return { synced: true, conflicts: [], resolved: true };
      }
      
      return { synced: false, conflicts: ['No data returned'], resolved: false };
    } catch (error) {
      console.error('❌ Manual data refresh failed:', error);
      return { synced: false, conflicts: [error instanceof Error ? error.message : 'Unknown error'], resolved: false };
    }
  }, []); // NO DEPENDENCIES - use current values directly

  // Get pending actions summary
  const getPendingActionsSummary = useCallback(() => {
    return Array.from(pendingActions);
  }, [pendingActions]);

  // Update connection state when data sync status changes
  useEffect(() => {
    if (currentData) {
      setConnectionState(prev => ({ ...prev, isDataSynced: true }));
    }
  }, [currentData]);

  return {
    // State - ONLY from Supabase events
    state,
    connectionState: {
      ...connectionState,
      canPerformActions: realtimeCanPerformActions && connectionState.isDataSynced,
      queuedActionsCount: queuedActions
    } as EnhancedConnectionState,
    
    // Connection state
    isConnected,
    isConnecting,
    isSyncing,
    lastSyncTime,
    dataVersion,
    error: realtimeError || state.error,

    // Actions - All with connection awareness and queuing
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
    submitUserInput,
    refreshData,
    
    // Data integrity
    getPendingActionsSummary,
    pendingActionsCount: pendingActions.size,
    
    // Computed state based on Supabase Realtime connection - STRICT requirements
    isRealtimeReady: isConnected && !isConnecting && connectionState.isDataSynced,
    canPerformActions: realtimeCanPerformActions && connectionState.isDataSynced && !state.error && pendingActions.size === 0,
    isDataStale: lastSyncTime ? (Date.now() - lastSyncTime.getTime()) > 60000 : true, // 1 minute threshold
    
    // Debug information
    debugInfo: {
      currentData,
      dataVersion,
      pendingActions: Array.from(pendingActions.keys()),
      connectionMetrics: {
        isConnected,
        isConnecting,
        isSyncing,
        lastSyncTime,
        queuedActions
      }
    }
  };
};

// Export types for use in components
export type { ActionResult, DataSyncResult, EnhancedConnectionState };
