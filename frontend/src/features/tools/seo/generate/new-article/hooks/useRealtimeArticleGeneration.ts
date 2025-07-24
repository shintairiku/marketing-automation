/**
 * Realtime Article Generation Hook
 * 
 * This hook integrates the useRealtimeGeneration hook with the existing
 * UI state management, providing a drop-in replacement for the WebSocket-based
 * article generation functionality.
 */

import { useState, useEffect, useCallback, useMemo } from 'react';
import { useRealtimeGeneration, GenerationParams, UserInputResponse } from './useRealtimeGeneration';

// Types compatible with existing UI components
export interface GenerationStep {
  id: string;
  title: string;
  status: 'pending' | 'in_progress' | 'completed' | 'error';
  message?: string;
  data?: any;
}

export interface PersonaOption {
  id: number;
  description: string;
}

export interface ThemeOption {
  title: string;
  description: string;
  keywords?: string[];
}

export interface GenerationState {
  currentStep: string;
  steps: GenerationStep[];
  personas?: PersonaOption[];
  themes?: ThemeOption[];
  researchPlan?: any;
  outline?: any;
  generatedContent?: string;
  currentSection?: {
    index: number;
    heading: string;
    content: string;
  };
  finalArticle?: {
    title: string;
    content: string;
  };
  articleId?: string;
  isWaitingForInput: boolean;
  inputType?: string;
  error?: string;
  researchProgress?: {
    currentQuery: number;
    totalQueries: number;
    query: string;
  };
  sectionsProgress?: {
    currentSection: number;
    totalSections: number;
    sectionHeading: string;
  };
  imageMode: boolean;
}

interface UseRealtimeArticleGenerationReturn {
  // State
  generationState: GenerationState;
  isConnected: boolean;
  isLoading: boolean;
  processId: string | null;
  
  // Actions
  startGeneration: (params: GenerationParams) => Promise<boolean>;
  selectPersona: (personaId: number) => Promise<boolean>;
  selectTheme: (themeIndex: number) => Promise<boolean>;
  approvePlan: (plan: any) => Promise<boolean>;
  approveOutline: (outline: any) => Promise<boolean>;
  regenerateCurrentStep: () => Promise<boolean>;
  disconnect: () => void;
  
  // Computed properties
  progressPercentage: number;
  currentStepTitle: string;
  canRegenerateStep: boolean;
}

// Step configuration matching the backend implementation
const STEP_CONFIG = {
  keyword_analyzing: { title: 'キーワード分析', order: 1 },
  persona_generating: { title: 'ペルソナ生成', order: 2 },
  theme_generating: { title: 'テーマ生成', order: 3 },
  research_planning: { title: 'リサーチ計画', order: 4 },
  researching: { title: 'リサーチ実行', order: 5 },
  outline_generating: { title: 'アウトライン生成', order: 6 },
  writing_sections: { title: '記事執筆', order: 7 },
  editing: { title: '編集・校正', order: 8 },
  finished: { title: '完了', order: 9 },
};

export const useRealtimeArticleGeneration = (): UseRealtimeArticleGenerationReturn => {
  const {
    processId,
    generationState: rawState,
    isConnected,
    error,
    isLoading,
    startGeneration: startRealtimeGeneration,
    submitUserInput,
    regenerateStep,
    disconnect,
    currentStepDisplay,
    progressPercentage,
    isWaitingForInput,
    inputType,
    userInputData,
    researchProgress,
    sectionsProgress,
    finalResults,
  } = useRealtimeGeneration();
  
  // Convert raw state to UI-compatible format
  const generationState: GenerationState = useMemo(() => {
    const currentStep = rawState?.current_step || 'keyword_analyzing';
    const imageMode = rawState?.process_metadata?.generation_params?.image_mode || false;
    
    // Generate steps based on current progress
    const steps: GenerationStep[] = Object.entries(STEP_CONFIG).map(([stepKey, config]) => {
      const isCurrentStep = stepKey === currentStep;
      const isCompleted = config.order < (STEP_CONFIG[currentStep as keyof typeof STEP_CONFIG]?.order || 1);
      const isError = rawState?.status === 'error' && isCurrentStep;
      
      let status: GenerationStep['status'] = 'pending';
      if (isError) {
        status = 'error';
      } else if (isCompleted) {
        status = 'completed';
      } else if (isCurrentStep) {
        status = rawState?.status === 'in_progress' ? 'in_progress' : 'pending';
      }
      
      return {
        id: stepKey,
        title: config.title,
        status,
        message: isCurrentStep ? currentStepDisplay : undefined,
      };
    });
    
    // Extract specific data for UI components
    let personas: PersonaOption[] | undefined;
    let themes: ThemeOption[] | undefined;
    let researchPlan: any;
    let outline: any;
    let currentSection: any;
    let finalArticle: any;
    let articleId: string | undefined;
    
    if (inputType === 'select_persona' && userInputData?.personas) {
      personas = userInputData.personas;
    }
    
    if (inputType === 'select_theme' && userInputData?.themes) {
      themes = userInputData.themes.map((theme: any, index: number) => ({
        title: theme.title || theme.id,
        description: theme.description,
        keywords: theme.keywords || [],
      }));
    }
    
    if (inputType === 'approve_plan' && userInputData?.plan) {
      researchPlan = userInputData.plan;
    }
    
    if (inputType === 'approve_outline' && userInputData?.outline) {
      outline = userInputData.outline;
    }
    
    // Handle section writing progress
    if (sectionsProgress) {
      const sectionsData = rawState?.generated_content?.sections || {};
      const currentSectionKey = `section_${sectionsProgress.currentSection}`;
      const sectionData = sectionsData[currentSectionKey];
      
      if (sectionData) {
        currentSection = {
          index: sectionsProgress.currentSection,
          heading: sectionData.heading,
          content: sectionData.content,
        };
      }
    }
    
    // Handle final results
    if (finalResults) {
      finalArticle = {
        title: finalResults.title,
        content: finalResults.final_html_content,
      };
      articleId = finalResults.article_id;
    }
    
    return {
      currentStep,
      steps,
      personas,
      themes,
      researchPlan,
      outline,
      generatedContent: currentSection?.content,
      currentSection,
      finalArticle,
      articleId,
      isWaitingForInput,
      inputType,
      error: error || (rawState?.process_metadata?.error?.message),
      researchProgress,
      sectionsProgress,
      imageMode,
    };
  }, [
    rawState,
    currentStepDisplay,
    isWaitingForInput,
    inputType,
    userInputData,
    researchProgress,
    sectionsProgress,
    finalResults,
    error,
  ]);
  
  // Action handlers
  const selectPersona = useCallback(async (personaId: number): Promise<boolean> => {
    const response: UserInputResponse = {
      response_type: 'select_persona',
      payload: { selected_id: personaId },
    };
    return await submitUserInput(response);
  }, [submitUserInput]);
  
  const selectTheme = useCallback(async (themeIndex: number): Promise<boolean> => {
    const response: UserInputResponse = {
      response_type: 'select_theme',
      payload: { selected_index: themeIndex },
    };
    return await submitUserInput(response);
  }, [submitUserInput]);
  
  const approvePlan = useCallback(async (plan: any): Promise<boolean> => {
    const response: UserInputResponse = {
      response_type: 'approve_plan',
      payload: { approved: true, plan },
    };
    return await submitUserInput(response);
  }, [submitUserInput]);
  
  const approveOutline = useCallback(async (outline: any): Promise<boolean> => {
    const response: UserInputResponse = {
      response_type: 'approve_outline',
      payload: { approved: true, outline },
    };
    return await submitUserInput(response);
  }, [submitUserInput]);
  
  // Computed properties
  const currentStepTitle = useMemo(() => {
    const currentStep = generationState.currentStep;
    return STEP_CONFIG[currentStep as keyof typeof STEP_CONFIG]?.title || currentStep;
  }, [generationState.currentStep]);
  
  const canRegenerateStep = useMemo(() => {
    return isWaitingForInput && !isLoading;
  }, [isWaitingForInput, isLoading]);
  
  return {
    // State
    generationState,
    isConnected,
    isLoading,
    processId,
    
    // Actions
    startGeneration: startRealtimeGeneration,
    selectPersona,
    selectTheme,
    approvePlan,
    approveOutline,
    regenerateCurrentStep: regenerateStep,
    disconnect,
    
    // Computed properties
    progressPercentage,
    currentStepTitle,
    canRegenerateStep,
  };
};