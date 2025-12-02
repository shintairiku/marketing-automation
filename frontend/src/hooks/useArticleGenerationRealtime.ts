'use client';

import { useCallback, useEffect, useRef, useState } from 'react';

import { normalizeOutline } from '@/features/tools/seo/generate/utils/normalize-outline';
import {
  CompletedSection,
  GenerationState,
  GenerationStep,
  PersonaData,
  ProcessData,
  ResearchProgress,
  SectionsProgress,
  StepStatus,
  ThemeData,
} from '@/types/article-generation';
import {
  FlowType,
  getNextStepAfterOutline,
  getNextStepAfterResearch,
  getNextStepAfterTheme,
} from '@/utils/flow-config';
import { useAuth } from '@clerk/nextjs';

import { ProcessEvent, useSupabaseRealtime } from './useSupabaseRealtime';

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
  
  // Generation state - with debouncing for stable UI
  // ステップ順序は動的に更新されるため、初期値はresearch_firstを使用
  const getInitialSteps = useCallback((flowType: string = 'research_first', enableFinalEditing: boolean = true): GenerationStep[] => {
    const isOutlineFirst = flowType === 'outline_first';

    const baseSteps = isOutlineFirst ? [
      { id: 'keyword_analyzing', name: 'キーワード分析', status: 'pending' },
      { id: 'persona_generating', name: 'ペルソナ生成', status: 'pending' },
      { id: 'theme_generating', name: 'テーマ提案', status: 'pending' },
      { id: 'outline_generating', name: 'アウトライン作成', status: 'pending' },
      { id: 'researching', name: 'リサーチ実行', status: 'pending' },
      { id: 'writing_sections', name: '執筆', status: 'pending' },
      { id: 'editing', name: '編集・校正', status: 'pending' },
    ] : [
      { id: 'keyword_analyzing', name: 'キーワード分析', status: 'pending' },
      { id: 'persona_generating', name: 'ペルソナ生成', status: 'pending' },
      { id: 'theme_generating', name: 'テーマ提案', status: 'pending' },
      { id: 'researching', name: 'リサーチ実行', status: 'pending' },
      { id: 'outline_generating', name: 'アウトライン作成', status: 'pending' },
      { id: 'writing_sections', name: '執筆', status: 'pending' },
      { id: 'editing', name: '編集・校正', status: 'pending' },
    ];

    return enableFinalEditing ? baseSteps : baseSteps.filter(step => step.id !== 'editing');
  }, []);
  
  // フック初期化時はデフォルトのresearch_firstで初期化
  // 実際のflowTypeはバックエンドから受信時やユーザー操作時に動的更新される
  const [state, setState] = useState<GenerationState>({
    currentStep: 'start',
    status: 'pending', // Initialize with pending status
    flowType: undefined,
    enableFinalEditing: true,
    steps: [],
    isInitialized: false,
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

  // Atomic state validation to prevent inconsistent states
  const validateAndSanitizeState = useCallback((newState: GenerationState): GenerationState => {
    // Ensure UI input type consistency with current step and available data
    const sanitizedState = { ...newState };
    
    // Step-based input type validation to prevent cross-step contamination
    const validStepInputTypes: Record<string, string[]> = {
      'persona_generating': ['select_persona'],
      'theme_generating': ['select_theme'],
      // 注意(legacy-flow): 統合前のリサーチ計画承認待ちに対応
      'researching': ['approve_plan'],
      'outline_generating': ['approve_outline'],
    };
    
    // Clear input state if it doesn't match the current step
    if (sanitizedState.isWaitingForInput && sanitizedState.inputType && sanitizedState.currentStep) {
      const validInputsForStep = validStepInputTypes[sanitizedState.currentStep];
      if (validInputsForStep && !validInputsForStep.includes(sanitizedState.inputType)) {
        console.log('🔒 Clearing mismatched input type for step:', {
          currentStep: sanitizedState.currentStep,
          inputType: sanitizedState.inputType,
          validInputs: validInputsForStep
        });
        sanitizedState.isWaitingForInput = false;
        sanitizedState.inputType = undefined;
      }
    }
    
    // Clear invalid input types based on available data and current step
    if (sanitizedState.isWaitingForInput && sanitizedState.inputType) {
      switch (sanitizedState.inputType) {
        case 'select_persona':
          if (!sanitizedState.personas || sanitizedState.personas.length === 0 || sanitizedState.currentStep !== 'persona_generating') {
            console.log('🔒 Clearing invalid persona selection state:', {
              hasPersonas: !!sanitizedState.personas,
              personaCount: sanitizedState.personas?.length || 0,
              currentStep: sanitizedState.currentStep
            });
            sanitizedState.isWaitingForInput = false;
            sanitizedState.inputType = undefined;
          }
          break;
          
        case 'select_theme':
          if (!sanitizedState.themes || sanitizedState.themes.length === 0 || sanitizedState.currentStep !== 'theme_generating') {
            console.log('🔒 Clearing invalid theme selection state:', {
              hasThemes: !!sanitizedState.themes,
              themeCount: sanitizedState.themes?.length || 0,
              currentStep: sanitizedState.currentStep
            });
            sanitizedState.isWaitingForInput = false;
            sanitizedState.inputType = undefined;
          }
          break;
        
        case 'approve_plan':
          // 注意(legacy-flow): リサーチ計画が存在しない、またはステップが一致しない場合は待機状態を解除
          if (!sanitizedState.researchPlan || sanitizedState.currentStep !== 'researching') {
            console.log('🔒 Clearing invalid plan approval state:', {
              hasResearchPlan: !!sanitizedState.researchPlan,
              currentStep: sanitizedState.currentStep
            });
            sanitizedState.isWaitingForInput = false;
            sanitizedState.inputType = undefined;
          }
          break;
          
        case 'approve_outline':
          // More lenient check: only clear if we're clearly not in outline phase
          // Allow outline_generating step even if outline data hasn't loaded yet (it may come from Realtime)
          if (sanitizedState.currentStep !== 'outline_generating') {
            console.log('🔒 Clearing outline approval state due to wrong step:', {
              hasOutline: !!sanitizedState.outline,
              currentStep: sanitizedState.currentStep
            });
            sanitizedState.isWaitingForInput = false;
            sanitizedState.inputType = undefined;
          } else if (!sanitizedState.outline) {
            console.log('⚠️ Outline approval state without outline data - keeping state for data loading:', {
              currentStep: sanitizedState.currentStep,
              isWaitingForInput: sanitizedState.isWaitingForInput
            });
            // Keep the waiting state - outline data may be loading via Realtime
          }
          break;
      }
    }
    
    // Clear input state if we're in a non-interactive step
    // Note: outline_generating is removed as it requires user approval for the generated outline
    const nonInteractiveSteps = ['keyword_analyzing', 'researching', 'research_completed', 'writing_sections', 'editing', 'completed', 'error'];
    if (nonInteractiveSteps.includes(sanitizedState.currentStep) && sanitizedState.isWaitingForInput) {
      // 注意(legacy-flow): リサーチ計画承認待ちの場合は待機状態を維持する
      if (!(sanitizedState.currentStep === 'researching' && sanitizedState.inputType === 'approve_plan')) {
        console.log('🔒 Clearing input state for non-interactive step:', sanitizedState.currentStep);
        sanitizedState.isWaitingForInput = false;
        sanitizedState.inputType = undefined;
      }
    }
    
    return sanitizedState;
  }, []);

  // Atomic state setter with validation
  const setValidatedState = useCallback((stateUpdater: (prev: GenerationState) => GenerationState) => {
    setState(prev => {
      const newState = stateUpdater(prev);
      const validatedState = validateAndSanitizeState(newState);
      
      // Log state transitions for debugging
      if (newState.currentStep !== prev.currentStep || 
          newState.inputType !== prev.inputType || 
          newState.isWaitingForInput !== prev.isWaitingForInput) {
        console.log('🔄 Atomic state transition:', {
          step: `${prev.currentStep} → ${validatedState.currentStep}`,
          input: `${prev.inputType || 'none'} → ${validatedState.inputType || 'none'}`,
          waiting: `${prev.isWaitingForInput} → ${validatedState.isWaitingForInput}`,
          sanitized: newState !== validatedState
        });
      }
      
      return validatedState;
    });
  }, [validateAndSanitizeState]);

  // Helper function to map backend steps to UI steps with proper loading state handling
  const mapBackendStepToUIStep = useCallback((backendStep: string, status?: string, enableFinalEditing: boolean = true): string => {
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
      'theme_selected': 'theme_generating', // Keep as generating, actual transition handled in ingestProcessData
      // 注意(legacy-flow): 旧リサーチ計画承認待ちステップは研究フェーズの一部として扱う
      'research_plan_generated': 'researching',
      
      // Research Execution Phase (Integrated)
      'researching': 'researching', // Unified research step
      'research_completed': 'researching', // Keep as researching, actual transition handled in ingestProcessData
      
      // Outline Generation Phase
      'outline_generating': 'outline_generating',
      'outline_generated': 'outline_generating', // Show completed outline (user approval UI)
      'outline_approved': 'writing_sections', // Auto-transition to writing sections
      
      // Writing Sections Phase
      'writing_sections': 'writing_sections',
      'all_sections_completed': enableFinalEditing ? 'editing' : 'writing_sections', // Auto-transition to editing loading
      
      // Editing Phase
      'editing': enableFinalEditing ? 'editing' : 'writing_sections',
      'editing_completed': enableFinalEditing ? 'editing' : 'writing_sections',
      
      // Final states
      'completed': 'completed',
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
  }, []);

  // SINGLE INGESTION FUNCTION for all data sources (sync/event/row)
  const ingestProcessData = useCallback((data: any, source: 'sync'|'event'|'row') => {
    console.log(`📥 Ingesting process data from ${source}:`, data);
    
    setValidatedState(prev => {
      const next = { ...prev };
      const ctx = data.article_context || {};
      const previousFlowType = next.flowType;
      const flowTypeFromData = ctx.flow_type || previousFlowType || 'research_first';
      const flowTypeChanged = flowTypeFromData !== previousFlowType;
      const previousSteps = next.steps;

      // 最終編集フラグ（バックエンド優先）
      const enableFinalEditingFromData =
        ctx.enable_final_editing ??
        ctx.enableFinalEditing ??
        data.enable_final_editing ??
        data.process_metadata?.enable_final_editing;
      const resolvedEnableFinalEditing =
        enableFinalEditingFromData !== undefined
          ? Boolean(enableFinalEditingFromData)
          : (next.enableFinalEditing ?? true);
      const enableFinalEditingChanged = resolvedEnableFinalEditing !== next.enableFinalEditing;

      next.enableFinalEditing = resolvedEnableFinalEditing;

      next.flowType = flowTypeFromData;

      if (!previousSteps || previousSteps.length === 0) {
        next.steps = getInitialSteps(flowTypeFromData, resolvedEnableFinalEditing);
      } else if (flowTypeChanged || enableFinalEditingChanged) {
        const reorderedSteps = getInitialSteps(flowTypeFromData, resolvedEnableFinalEditing);
        next.steps = reorderedSteps.map(newStep => {
          const existingStep = previousSteps.find(s => s.id === newStep.id);
          return existingStep ? { ...newStep, status: existingStep.status } : newStep;
        });
        console.log('🔀 Flow or editing setting changed. Reordered steps for:', {
          flowType: flowTypeFromData,
          enableFinalEditing: resolvedEnableFinalEditing
        });
      }

      // Status & waiting state - CRITICAL for UI display
      next.status = data.status;
      next.isWaitingForInput = data.status === 'user_input_required' || !!data.is_waiting_for_input;
      next.inputType = data.input_type || data.process_metadata?.input_type;
      
      console.log(`🔍 Status ingestion: status=${data.status}, isWaiting=${next.isWaitingForInput}, inputType=${next.inputType}`);

      // Backend step -> UI step mapping
      const backendStep = data.current_step || data.current_step_name || data.article_context?.current_step;
      if (backendStep) {
        const uiStep = mapBackendStepToUIStep(backendStep, data.status, resolvedEnableFinalEditing);
        next.currentStep = uiStep;
        console.log(`🔍 Step mapping: ${backendStep} -> ${uiStep} (waiting: ${next.isWaitingForInput})`);

        // Progressive step completion: mark current step AND all previous steps as completed
        // フローを決定するロジックを追加
        const stepOrderResearchFirst = resolvedEnableFinalEditing
          ? ['keyword_analyzing', 'persona_generating', 'theme_generating', 'researching', 'outline_generating', 'writing_sections', 'editing', 'completed']
          : ['keyword_analyzing', 'persona_generating', 'theme_generating', 'researching', 'outline_generating', 'writing_sections', 'completed'];
        const stepOrderOutlineFirst = resolvedEnableFinalEditing
          ? ['keyword_analyzing', 'persona_generating', 'theme_generating', 'outline_generating', 'researching', 'writing_sections', 'editing', 'completed']
          : ['keyword_analyzing', 'persona_generating', 'theme_generating', 'outline_generating', 'researching', 'writing_sections', 'completed'];

        // Determine which flow we're using based on current context
        const flowType = next.flowType || flowTypeFromData;
        const isOutlineFirst = flowType === 'outline_first';

        console.log('🔍 Flow determination:', {
          flowType,
          isOutlineFirst,
          source: ctx.flow_type ? 'backend_context' : 'fallback'
        });

        const stepOrder = isOutlineFirst ? stepOrderOutlineFirst : stepOrderResearchFirst;
        const currentStepIndex = stepOrder.indexOf(uiStep);

        console.log(`🎯 Progressive step completion: current="${uiStep}" (index=${currentStepIndex}), waiting=${next.isWaitingForInput}`);

        next.steps = next.steps.map((s, index) => {
          const prevStatus = s.status;
          let newStatus: StepStatus;
          
          if (index < currentStepIndex) {
            // All previous steps should be completed
            newStatus = 'completed';
          } else if (s.id === uiStep) {
            // Current step status based on process state
            newStatus = next.isWaitingForInput ? 'completed' : (
              data.status === 'error' ? 'error' : 
              data.status === 'completed' ? 'completed' : 'in_progress'
            );
          } else {
            // Future steps remain pending unless they have specific error states
            newStatus = s.status === 'error' ? 'error' : 'pending';
          }
          
          if (prevStatus !== newStatus) {
            console.log(`  📝 Step ${s.id}: ${prevStatus} -> ${newStatus}`);
          }
          
          return { ...s, status: newStatus };
        });
      }

      // Context data (preserve existing, don't overwrite)
      if (!next.personas && ctx.generated_detailed_personas) {
        console.log('👥 Setting personas from context:', ctx.generated_detailed_personas);
        next.personas = ctx.generated_detailed_personas.map((p: any, i: number) => ({
          id: i,
          description: p.description || p.persona_description || JSON.stringify(p)
        }));
      }
      
      if (!next.themes && ctx.generated_themes) {
        console.log('🎯 Setting themes from context:', ctx.generated_themes);
        next.themes = ctx.generated_themes;
      }
      
      if (!next.researchPlan && ctx.research_plan) {
        console.log('📋 Setting research plan from context:', ctx.research_plan);
        next.researchPlan = ctx.research_plan;
      }
      
      // CRITICAL: Outline data handling
      const outline = ctx.outline || ctx.generated_outline;
      if (!next.outline && outline) {
        const normalizedOutline = normalizeOutline(outline);
        if (normalizedOutline) {
          if (process.env.NODE_ENV !== 'production') {
            console.log('📝 Setting normalized outline from context:', {
              originalTopLevel: outline?.top_level_heading,
              normalizedTopLevel: normalizedOutline.top_level_heading,
            });
          }
          next.outline = normalizedOutline;
        } else {
          next.outline = outline;
        }
      }
      
      if (!next.isInitialized && next.steps.length > 0) {
        next.isInitialized = true;
      }

      return next;
    });
  }, [setValidatedState, mapBackendStepToUIStep, getInitialSteps]);

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

  // Data sync callback using unified ingestion
  const handleDataSync = useCallback((data: any) => {
    console.log('🔄 Data sync received:', data);
    ingestProcessData(data, 'sync');
  }, [ingestProcessData]);

  // SIMPLIFIED event handler that uses unified ingestion
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
    if (event.event_type === 'process_state_updated' || 
        event.event_type === 'process_created' ||
        event.event_type === 'process_updated' ||
        event.event_type === 'status_changed' ||
        event.event_type === 'step_changed') {
      // Use unified ingestion for all process state events
      ingestProcessData(event.event_data, 'event');
      return;
    }
    
    // Update data version for tracking
    setDataVersion(prev => prev + 1);

    // Handle non-process-state events with direct state updates
    setValidatedState((prev: GenerationState) => {
      const newState = { ...prev };
      
      switch (event.event_type) {
        case 'generation_started':
          newState.currentStep = 'keyword_analyzing';
          newState.steps = newState.steps.map((step: GenerationStep) => 
            step.id === 'keyword_analyzing' ? { ...step, status: 'in_progress' as StepStatus } : step
          );
          setConnectionState(s => ({ ...s, hasStarted: true }));
          break;

        // Process state events are handled by ingestProcessData above
        // These cases are removed to prevent duplicate handling

        // All other cases with inline step status updates
        case 'step_started':
          const startedStep = mapBackendStepToUIStep(event.event_data.step_name, undefined, newState.enableFinalEditing ?? true);
          newState.currentStep = startedStep;
          newState.steps = newState.steps.map((step: GenerationStep) => 
            step.id === startedStep ? { ...step, status: 'in_progress' as StepStatus } : step
          );
          console.log('🚀 Step started:', { backendStep: event.event_data.step_name, uiStep: startedStep });
          break;

        case 'step_completed':
          const completedStep = mapBackendStepToUIStep(event.event_data.step_name, undefined, newState.enableFinalEditing ?? true);
          newState.steps = newState.steps.map((step: GenerationStep) => 
            step.id === completedStep ? { ...step, status: 'completed' as StepStatus } : step
          );
          
          // Auto-progression: trigger next step loading state if applicable
          const flowTypeForProgression = (newState.flowType || 'research_first') as FlowType;
          const progressionMap: Record<string, string | null> = {
            'keyword_analyzing': 'persona_generating',
            'persona_generating': null, // Waits for user selection
            'theme_generating': null, // Waits for user selection  
            'researching': getNextStepAfterResearch(flowTypeForProgression),
            'outline_generating': null, // Waits for user approval
            'writing_sections': (newState.enableFinalEditing ?? true) ? 'editing' : null,
            'editing': null, // Final step
          };
          
          const nextStep = progressionMap[completedStep] || null;
          if (nextStep && !newState.isWaitingForInput) {
            console.log('🔄 Auto-progressing from completed step:', { completedStep, nextStep, flowType: flowTypeForProgression });
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
            case 'approve_outline': {
              const normalizedOutline = normalizeOutline(inputData.outline);
              newState.outline = normalizedOutline ?? inputData.outline ?? null;
              break;
            }
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
                // 現在の状態からflowTypeを取得
                const currentFlowType = newState.flowType || 'research_first';
                const nextStepAfterTheme = getNextStepAfterTheme(currentFlowType);
                console.log(`🔀 Theme selection: using flow type ${currentFlowType}, next step: ${nextStepAfterTheme}`);
                newState.currentStep = nextStepAfterTheme;
                newState.steps = newState.steps.map((step: GenerationStep) => {
                  if (step.id === 'theme_generating') return { ...step, status: 'completed' as StepStatus };
                  if (step.id === nextStepAfterTheme) return { ...step, status: 'in_progress' as StepStatus };
                  return step;
                });
                break;
              case 'approve_plan':
                // 注意(legacy-flow): 計画承認後は研究ステップを開始（もしくは再開）する
                newState.currentStep = 'researching';
                newState.steps = newState.steps.map((step: GenerationStep) => {
                  if (step.id === 'researching') return { ...step, status: 'in_progress' as StepStatus };
                  return step;
                });
                break;
              case 'approve_outline':
                // 現在の状態からflowTypeを取得
                const currentFlowTypeOutline = newState.flowType || 'research_first';
                const nextStepAfterOutline = getNextStepAfterOutline(currentFlowTypeOutline);
                console.log(`🔀 Outline approval: using flow type ${currentFlowTypeOutline}, next step: ${nextStepAfterOutline}`);
                newState.currentStep = nextStepAfterOutline;
                newState.steps = newState.steps.map((step: GenerationStep) => {
                  if (step.id === 'outline_generating') return { ...step, status: 'completed' as StepStatus };
                  if (step.id === nextStepAfterOutline) return { ...step, status: 'in_progress' as StepStatus };
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
            const errorStepName = mapBackendStepToUIStep(event.event_data.step_name, undefined, newState.enableFinalEditing ?? true);
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
          // Only log the event - state changes will come from process_state_updated
          console.log('📋 Outline generation started');
          break;

        case 'outline_generation_completed':
          console.log('📋 Outline generation completed');
          newState.steps = newState.steps.map((step: GenerationStep) => 
            step.id === 'outline_generating' ? { ...step, status: 'completed' as StepStatus } : step
          );
          break;

        case 'section_writing_started':
          // Forward-only: don't regress from later steps
          if (!['editing', 'completed'].includes(newState.currentStep)) {
            const from = newState.currentStep;
            newState.currentStep = 'writing_sections';
            console.log('✍️ Section writing started; step set:', { from, to: 'writing_sections' });
          }
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
          if (newState.enableFinalEditing === false) {
            // 編集をスキップする設定の場合は無視し、執筆完了として扱う
            newState.currentStep = 'writing_sections';
            newState.steps = newState.steps.map((step: GenerationStep) => 
              step.id === 'writing_sections' ? { ...step, status: 'completed' as StepStatus } : step
            );
            break;
          }

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
              .filter(content => typeof content === 'string' && content.trim().length > 0)
              .join('\n\n');
          }

          // Keep step as writing until all completed
          if (!['editing', 'completed'].includes(newState.currentStep)) {
            newState.currentStep = 'writing_sections';
          }
          newState.steps = newState.steps.map((step: GenerationStep) => 
            step.id === 'writing_sections' ? { ...step, status: 'in_progress' as StepStatus } : step
          );
          
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
            if (step.id === 'editing' && (newState.enableFinalEditing ?? true)) return { ...step, status: 'in_progress' as StepStatus };
            return step;
          });

          if (newState.enableFinalEditing ?? true) {
            // Auto-progress to editing step with loading state
            console.log('🔄 Auto-progressing to editing step');
            newState.currentStep = 'editing';
          } else {
            // 編集なしの場合は執筆完了を最終ステップとして扱う
            newState.currentStep = 'writing_sections';
          }
          
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
          // Clear user input waiting state
          newState.isWaitingForInput = false;
          newState.inputType = undefined;
          break;
          
        case 'theme_selection_completed':
          // 現在の状態からflowTypeを取得
          const flowTypeTheme = newState.flowType || 'research_first';
          const nextAfterTheme = getNextStepAfterTheme(flowTypeTheme);
          console.log(`💡 Theme selected - auto-progressing to ${nextAfterTheme} (flow: ${flowTypeTheme})`);
          newState.steps = newState.steps.map((step: GenerationStep) => {
            if (step.id === 'theme_generating') return { ...step, status: 'completed' as StepStatus };
            if (step.id === nextAfterTheme) return { ...step, status: 'in_progress' as StepStatus };
            return step;
          });
          newState.currentStep = nextAfterTheme;
          // Clear user input waiting state
          newState.isWaitingForInput = false;
          newState.inputType = undefined;
          break;
          
        // research_plan_approval_completed removed: integrated research no longer requires plan approval
          
        case 'outline_approval_completed':
          // 現在の状態からflowTypeを取得
          const flowTypeOutline = newState.flowType || 'research_first';
          const nextAfterOutline = getNextStepAfterOutline(flowTypeOutline);
          console.log(`📝 Outline approved - auto-progressing to ${nextAfterOutline} (flow: ${flowTypeOutline})`);
          newState.steps = newState.steps.map((step: GenerationStep) => {
            if (step.id === 'outline_generating') return { ...step, status: 'completed' as StepStatus };
            if (step.id === nextAfterOutline) return { ...step, status: 'in_progress' as StepStatus };
            return step;
          });
          newState.currentStep = nextAfterOutline;
          // Clear user input waiting state
          newState.isWaitingForInput = false;
          newState.inputType = undefined;
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
  }, [ingestProcessData, mapBackendStepToUIStep, setValidatedState, processedEventIds]); // Include deduplication state

  const handleRealtimeError = useCallback((error: Error) => {
    console.error('Realtime error:', error);
    setValidatedState((prev: GenerationState) => ({ ...prev, error: error.message }));
  }, [setValidatedState]);

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
    onDataSync: handleDataSync, // Wire up the data sync callback
    // Only auto-connect when both processId and userId are available
    autoConnect: autoConnect && !!processId && !!userId,
    // FORCE DISABLE POLLING - Database is single source of truth via Realtime
    enableDataSync: false,
    syncInterval: 0,
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
      
      // Reset state for new generation with correct flow type
      const flowType = requestData.flow_type || 'research_first';
      const enableFinalEditing = requestData.enable_final_editing ?? true;
      const newSteps = getInitialSteps(flowType, enableFinalEditing);

      setValidatedState((prev: GenerationState) => ({
        ...prev,
        currentStep: 'keyword_analyzing',
        status: 'pending', // Reset status for new generation
        flowType: flowType, // Set flow type from request
        enableFinalEditing,
        steps: newSteps.map((step: GenerationStep) => ({ ...step, status: 'pending' as StepStatus, message: undefined })),
        isInitialized: true,
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
      setValidatedState((prev: GenerationState) => ({ 
        ...prev, 
        error: error instanceof Error ? error.message : 'Failed to start generation' 
      }));
      throw error;
    }
  }, [getToken, setValidatedState, getInitialSteps]);

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

      // Note: We don't immediately clear isWaitingForInput here to avoid 
      // intermediate states that cause UI flashing. The state will be updated
      // consistently when the realtime event arrives from the backend.

      return await response.json();
    } catch (error) {
      console.error('Error submitting user input:', error);
      setValidatedState((prev: GenerationState) => ({ 
        ...prev, 
        error: error instanceof Error ? error.message : 'Failed to submit input' 
      }));
      throw error;
    }
  }, [processId, getToken, setValidatedState]);

  const selectPersona = useCallback(async (personaId: number): Promise<ActionResult> => {
    // Only proceed if connected to Supabase Realtime
    if (!isConnected) {
      console.warn('Cannot select persona - not connected to realtime');
      setValidatedState((prev: GenerationState) => ({ 
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
      // Handle timing race condition where process has already moved to next step
      if (error instanceof Error && error.message.includes('Bad Request')) {
        console.warn('Persona selection failed - likely due to timing race condition, checking current process state');
        
        try {
          // Refresh process state to check if it has moved to the next step
          const freshData = await fetchProcessData();
          
          // If process is now in theme selection or later, treat as success
          const currentStep = freshData?.current_step_name;
          if (currentStep === 'theme_selection' || 
              currentStep === 'researching' || 
              currentStep === 'outline_generation' || 
              currentStep === 'section_writing' || 
              currentStep === 'editing' || 
              currentStep === 'completed') {
            console.log('Process has already progressed beyond persona selection - treating selection as successful');
            return { success: true };
          }
        } catch (refreshError) {
          console.error('Failed to refresh process state:', refreshError);
        }
      }
      
      // Rollback on error
      setValidatedState((prev: GenerationState) => ({
        ...prev,
        isWaitingForInput: true,
        inputType: 'select_persona',
        error: error instanceof Error ? error.message : 'ペルソナ選択に失敗しました'
      }));
      return { success: false, error: error instanceof Error ? error.message : 'ペルソナ選択に失敗しました' };
    }
  }, [submitUserInput, isConnected, fetchProcessData, setValidatedState]);

  const selectTheme = useCallback(async (themeIndex: number): Promise<ActionResult> => {
    // Only proceed if connected to Supabase Realtime
    if (!isConnected) {
      console.warn('Cannot select theme - not connected to realtime');
      setValidatedState((prev: GenerationState) => ({ 
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
      // Handle timing race condition where process has already moved to next step
      if (error instanceof Error && error.message.includes('Bad Request')) {
        console.warn('Theme selection failed - likely due to timing race condition, checking current process state');
        
        try {
          // Refresh process state to check if it has moved to the next step
          const freshData = await fetchProcessData();
          
          // If process is now in research execution or later, treat as success
          const currentStep = freshData?.current_step_name;
          if (currentStep === 'researching' || 
              currentStep === 'outline_generation' || 
              currentStep === 'section_writing' || 
              currentStep === 'editing' || 
              currentStep === 'completed') {
            console.log('Process has already progressed beyond theme selection - treating selection as successful');
            return { success: true };
          }
        } catch (refreshError) {
          console.error('Failed to refresh process state:', refreshError);
        }
      }
      
      // Rollback on error
      setValidatedState((prev: GenerationState) => ({
        ...prev,
        isWaitingForInput: true,
        inputType: 'select_theme',
        error: error instanceof Error ? error.message : 'テーマ選択に失敗しました'
      }));
      return { success: false, error: error instanceof Error ? error.message : 'テーマ選択に失敗しました' };
    }
  }, [submitUserInput, isConnected, fetchProcessData, setValidatedState]);

  const approvePlan = useCallback(async (approved: boolean): Promise<ActionResult> => {
    // Only proceed if connected to Supabase Realtime
    if (!isConnected) {
      console.warn('Cannot approve plan - not connected to realtime');
      setValidatedState((prev: GenerationState) => ({ 
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
      // Handle timing race condition where process has already moved to next step
      if (error instanceof Error && error.message.includes('Bad Request')) {
        console.warn('Plan approval failed - likely due to timing race condition, checking current process state');
        
        try {
          // Refresh process state to check if it has moved to the next step
          const freshData = await fetchProcessData();
          
          // If process is now in outline generation or later, treat as success
          const currentStep = freshData?.current_step_name;
          if (currentStep === 'outline_generation' || 
              currentStep === 'section_writing' || 
              currentStep === 'editing' || 
              currentStep === 'completed') {
            console.log('Process has already progressed beyond plan approval - treating approval as successful');
            return { success: true };
          }
        } catch (refreshError) {
          console.error('Failed to refresh process state:', refreshError);
        }
      }
      
      // Rollback on error
      setValidatedState((prev: GenerationState) => ({
        ...prev,
        isWaitingForInput: true,
        inputType: 'approve_plan',
        error: error instanceof Error ? error.message : 'リサーチ計画承認に失敗しました'
      }));
      return { success: false, error: error instanceof Error ? error.message : 'リサーチ計画承認に失敗しました' };
    }
  }, [submitUserInput, isConnected, fetchProcessData, setValidatedState]);

  const approveOutline = useCallback(async (approved: boolean): Promise<ActionResult> => {
    // Only proceed if connected to Supabase Realtime
    if (!isConnected) {
      console.warn('Cannot approve outline - not connected to realtime');
      setValidatedState((prev: GenerationState) => ({ 
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
      // Handle timing race condition where process has already moved to next step
      if (error instanceof Error && error.message.includes('Bad Request')) {
        console.warn('Outline approval failed - likely due to timing race condition, checking current process state');
        
        try {
          // Refresh process state to check if it has moved to the next step
          const freshData = await fetchProcessData();
          
          // If process is now in section writing or later, treat as success
          const currentStep = freshData?.current_step_name;
          if (currentStep === 'section_writing' || 
              currentStep === 'editing' || 
              currentStep === 'completed') {
            console.log('Process has already progressed to section writing - treating approval as successful');
            return { success: true };
          }
        } catch (refreshError) {
          console.error('Failed to refresh process state:', refreshError);
        }
      }
      
      // Rollback on error
      setValidatedState((prev: GenerationState) => ({
        ...prev,
        isWaitingForInput: true,
        inputType: 'approve_outline',
        error: error instanceof Error ? error.message : 'アウトライン承認に失敗しました'
      }));
      return { success: false, error: error instanceof Error ? error.message : 'アウトライン承認に失敗しました' };
    }
  }, [submitUserInput, isConnected, fetchProcessData, setValidatedState]);

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
  }, [fetchProcessData, handleRealtimeEvent, processId]); // Add required dependencies

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
    // State - Atomic validated state
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
