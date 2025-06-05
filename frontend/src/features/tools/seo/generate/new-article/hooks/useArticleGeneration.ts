'use client';

import { useState, useCallback } from 'react';
import { useWebSocket, ServerEventMessage, ClientResponseMessage } from './useWebSocket';

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
  keywords: string[];
}

export interface GenerationState {
  currentStep: string;
  steps: GenerationStep[];
  personas?: PersonaOption[];
  themes?: ThemeOption[];
  researchPlan?: any;
  outline?: any;
  generatedContent?: string;
  finalArticle?: {
    title: string;
    content: string;
  };
  isWaitingForInput: boolean;
  inputType?: string;
  error?: string;
}

interface UseArticleGenerationOptions {
  processId?: string;
  userId?: string;
}

export const useArticleGeneration = ({ processId, userId }: UseArticleGenerationOptions) => {
  const [state, setState] = useState<GenerationState>({
    currentStep: 'start',
    steps: [
      { id: 'keyword_analysis', title: 'キーワード分析', status: 'pending' },
      { id: 'persona_generation', title: 'ペルソナ生成', status: 'pending' },
      { id: 'theme_generation', title: 'テーマ提案', status: 'pending' },
      { id: 'research_planning', title: 'リサーチ計画', status: 'pending' },
      { id: 'research_execution', title: 'リサーチ実行', status: 'pending' },
      { id: 'outline_generation', title: 'アウトライン作成', status: 'pending' },
      { id: 'content_writing', title: '記事執筆', status: 'pending' },
      { id: 'editing', title: '編集・校正', status: 'pending' },
    ],
    isWaitingForInput: false,
  });

  const handleMessage = useCallback((message: ServerEventMessage) => {
    const { payload } = message;

    setState(prev => {
      const newState = { ...prev };

      // ステップ更新
      if (payload.step) {
        newState.currentStep = payload.step;
        
        // ステップの状態を更新
        newState.steps = newState.steps.map(step => {
          if (step.id === payload.step) {
            return { ...step, status: 'in_progress', message: payload.message };
          } else if (newState.steps.find(s => s.id === payload.step)?.id === step.id) {
            // 前のステップを完了にする
            const currentIndex = newState.steps.findIndex(s => s.id === payload.step);
            const stepIndex = newState.steps.findIndex(s => s.id === step.id);
            if (stepIndex < currentIndex) {
              return { ...step, status: 'completed' };
            }
          }
          return step;
        });
      }

      // 特定のイベントタイプに応じた処理
      if (payload.personas) {
        newState.personas = payload.personas;
        newState.isWaitingForInput = true;
        newState.inputType = 'select_persona';
      }

      if (payload.themes) {
        newState.themes = payload.themes;
        newState.isWaitingForInput = true;
        newState.inputType = 'select_theme';
      }

      if (payload.plan) {
        newState.researchPlan = payload.plan;
        newState.isWaitingForInput = true;
        newState.inputType = 'approve_plan';
      }

      if (payload.outline) {
        newState.outline = payload.outline;
        newState.isWaitingForInput = true;
        newState.inputType = 'approve_outline';
      }

      if (payload.html_content_chunk) {
        if (!newState.generatedContent) {
          newState.generatedContent = '';
        }
        newState.generatedContent += payload.html_content_chunk;
      }

      if (payload.final_html_content) {
        newState.finalArticle = {
          title: payload.title || 'Generated Article',
          content: payload.final_html_content,
        };
        newState.currentStep = 'completed';
        newState.steps = newState.steps.map(step => ({
          ...step,
          status: 'completed',
        }));
      }

      if (payload.error_message) {
        newState.error = payload.error_message;
        newState.currentStep = 'error';
      }

      return newState;
    });
  }, []);

  const { isConnected, isConnecting, error: wsError, connect, disconnect, sendMessage, startGeneration } = useWebSocket({
    processId,
    userId,
    onMessage: handleMessage,
  });

  const selectPersona = useCallback((personaId: number) => {
    const message: ClientResponseMessage = {
      type: 'client_response',
      response_type: 'select_persona',
      payload: { selected_id: personaId },
    };
    sendMessage(message);
    setState(prev => ({ ...prev, isWaitingForInput: false, inputType: undefined }));
  }, [sendMessage]);

  const selectTheme = useCallback((themeIndex: number) => {
    const message: ClientResponseMessage = {
      type: 'client_response',
      response_type: 'select_theme',
      payload: { selected_index: themeIndex },
    };
    sendMessage(message);
    setState(prev => ({ ...prev, isWaitingForInput: false, inputType: undefined }));
  }, [sendMessage]);

  const approvePlan = useCallback((approved: boolean) => {
    const message: ClientResponseMessage = {
      type: 'client_response',
      response_type: 'approve_plan',
      payload: { approved },
    };
    sendMessage(message);
    setState(prev => ({ ...prev, isWaitingForInput: false, inputType: undefined }));
  }, [sendMessage]);

  const approveOutline = useCallback((approved: boolean) => {
    const message: ClientResponseMessage = {
      type: 'client_response',
      response_type: 'approve_outline',
      payload: { approved },
    };
    sendMessage(message);
    setState(prev => ({ ...prev, isWaitingForInput: false, inputType: undefined }));
  }, [sendMessage]);

  const regenerate = useCallback(() => {
    const message: ClientResponseMessage = {
      type: 'client_response',
      response_type: 'regenerate',
      payload: {},
    };
    sendMessage(message);
    setState(prev => ({ ...prev, isWaitingForInput: false, inputType: undefined }));
  }, [sendMessage]);

  const startArticleGeneration = useCallback((requestData: any) => {
    setState(prev => ({
      ...prev,
      currentStep: 'start',
      steps: prev.steps.map(step => ({ ...step, status: 'pending' })),
      personas: undefined,
      themes: undefined,
      researchPlan: undefined,
      outline: undefined,
      generatedContent: undefined,
      finalArticle: undefined,
      isWaitingForInput: false,
      inputType: undefined,
      error: undefined,
    }));
    startGeneration(requestData);
  }, [startGeneration]);

  return {
    // State
    state,
    isConnected,
    isConnecting,
    error: wsError || state.error,

    // Actions
    connect,
    disconnect,
    startArticleGeneration,
    selectPersona,
    selectTheme,
    approvePlan,
    approveOutline,
    regenerate,
  };
};