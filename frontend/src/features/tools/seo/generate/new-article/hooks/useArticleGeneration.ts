'use client';

import { useCallback,useState } from 'react';
import { useAuth } from '@clerk/nextjs';

import { ClientResponseMessage,ServerEventMessage, useWebSocket } from './useWebSocket';

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
}

interface UseArticleGenerationOptions {
  processId?: string;
  userId?: string;
}

export const useArticleGeneration = ({ processId, userId }: UseArticleGenerationOptions) => {
  const { getToken } = useAuth();
  const [state, setState] = useState<GenerationState>({
    currentStep: 'start',
    steps: [
      { id: 'keyword_analyzing', title: 'キーワード分析', status: 'pending' },
      { id: 'persona_generating', title: 'ペルソナ生成', status: 'pending' },
      { id: 'theme_generating', title: 'テーマ提案', status: 'pending' },
      { id: 'research_planning', title: 'リサーチ計画', status: 'pending' },
      { id: 'researching', title: 'リサーチ実行', status: 'pending' },
      { id: 'outline_generating', title: 'アウトライン作成', status: 'pending' },
      { id: 'writing_sections', title: '記事執筆', status: 'pending' },
      { id: 'editing', title: '編集・校正', status: 'pending' },
    ],
    isWaitingForInput: false,
    articleId: undefined,
  });

  const handleMessage = useCallback((message: ServerEventMessage | any) => {
    // ハートビートメッセージを早期に処理
    if (message.type === 'heartbeat' || (typeof message === 'string' && message.includes('heartbeat'))) {
      return;
    }

    const { payload } = message as ServerEventMessage;

    // payloadが存在しない場合は処理をスキップ
    if (!payload) {
      return;
    }

    setState(prev => {
      const newState = { ...prev };

      // ステップ更新処理（stepフィールドが存在する場合のみ）
      if (payload.step) {
        newState.currentStep = payload.step;
        
        // ステップの状態を更新
        let mappedStep = payload.step;
        
        // research_synthesizing は researching として扱うが、要約フェーズであることを明示
        if (payload.step === 'research_synthesizing') {
          mappedStep = 'researching';
          // リサーチ要約中の表示
          newState.steps = newState.steps.map(step => {
            if (step.id === 'researching') {
              return { 
                ...step, 
                status: 'in_progress', 
                message: '要約レポートを作成中...' 
              };
            }
            return step;
          });
          // リサーチ進捗をクリア（要約フェーズでは不要）
          newState.researchProgress = undefined;
          return newState;
        }
        
        const currentStepIndex = newState.steps.findIndex(s => s.id === mappedStep);
        
        newState.steps = newState.steps.map((step, index) => {
          if (step.id === mappedStep) {
            // 現在のステップを実行中に
            return { ...step, status: 'in_progress', message: payload.message || '' };
          } else if (index < currentStepIndex) {
            // 前のステップを完了に
            return { ...step, status: 'completed' };
          } else {
            // 後のステップを待機中に
            return { ...step, status: 'pending' };
          }
        });
      }

      // UserInputRequestPayload 形式のメッセージ処理
      if (payload.request_type && payload.data) {
        newState.isWaitingForInput = true;
        
        // ユーザー入力待ちの際は、対応するステップを完了にする
        switch (payload.request_type) {
          case 'select_persona':
            newState.personas = payload.data.personas;
            newState.inputType = 'select_persona';
            newState.currentStep = 'persona_generated';
            // persona_generatingステップを完了に
            newState.steps = newState.steps.map(step => 
              step.id === 'persona_generating' ? { ...step, status: 'completed' } : step
            );
            break;
          case 'select_theme':
            newState.themes = payload.data.themes;
            newState.inputType = 'select_theme';
            newState.currentStep = 'theme_proposed';
            newState.steps = newState.steps.map(step => 
              step.id === 'theme_generating' ? { ...step, status: 'completed' } : step
            );
            break;
          case 'approve_plan':
            newState.researchPlan = payload.data.plan;
            newState.inputType = 'approve_plan';
            newState.currentStep = 'research_plan_generated';
            newState.steps = newState.steps.map(step => 
              step.id === 'research_planning' ? { ...step, status: 'completed' } : step
            );
            break;
          case 'approve_outline':
            newState.outline = payload.data.outline;
            newState.inputType = 'approve_outline';
            newState.currentStep = 'outline_generated';
            newState.steps = newState.steps.map(step => 
              step.id === 'outline_generating' ? { ...step, status: 'completed' } : step
            );
            break;
        }
      }

      // 従来の直接フィールド処理（後方互換性のため）
      if (payload.personas && !payload.request_type) {
        newState.personas = payload.personas;
        newState.isWaitingForInput = true;
        newState.inputType = 'select_persona';
        newState.currentStep = 'persona_generated';
        newState.steps = newState.steps.map(step => 
          step.id === 'persona_generating' ? { ...step, status: 'completed' } : step
        );
      }

      if (payload.themes && !payload.request_type) {
        newState.themes = payload.themes;
        newState.isWaitingForInput = true;
        newState.inputType = 'select_theme';
        newState.currentStep = 'theme_proposed';
        newState.steps = newState.steps.map(step => 
          step.id === 'theme_generating' ? { ...step, status: 'completed' } : step
        );
      }

      if (payload.plan && !payload.request_type) {
        newState.researchPlan = payload.plan;
        newState.isWaitingForInput = true;
        newState.inputType = 'approve_plan';
        newState.currentStep = 'research_plan_generated';
        newState.steps = newState.steps.map(step => 
          step.id === 'research_planning' ? { ...step, status: 'completed' } : step
        );
      }

      if (payload.outline && !payload.request_type) {
        newState.outline = payload.outline;
        newState.isWaitingForInput = true;
        newState.inputType = 'approve_outline';
        newState.currentStep = 'outline_generated';
        newState.steps = newState.steps.map(step => 
          step.id === 'outline_generating' ? { ...step, status: 'completed' } : step
        );
      }

      if (payload.html_content_chunk) {
        if (!newState.generatedContent) {
          newState.generatedContent = '';
        }
        newState.generatedContent += payload.html_content_chunk;
        
        // セクション情報を更新
        if (payload.section_index !== undefined && payload.heading) {
          newState.currentSection = {
            index: payload.section_index,
            heading: payload.heading,
            content: payload.html_content_chunk,
          };
        }
        
        // 記事執筆中はステップを実行中に
        if (newState.currentStep === 'writing_sections') {
          newState.steps = newState.steps.map(step => 
            step.id === 'writing_sections' ? { ...step, status: 'in_progress', message: `セクション ${(payload.section_index || 0) + 1} を執筆中...` } : step
          );
          
          // セクション進捗情報を更新
          if (payload.section_index !== undefined && newState.outline?.sections) {
            newState.sectionsProgress = {
              currentSection: payload.section_index + 1,
              totalSections: newState.outline.sections.length,
              sectionHeading: payload.heading || `セクション ${payload.section_index + 1}`
            };
          }
        }
      }

      if (payload.final_html_content) {
        newState.finalArticle = {
          title: payload.title || 'Generated Article',
          content: payload.final_html_content,
        };
        newState.currentStep = 'completed';
        // 全ステップを完了に
        newState.steps = newState.steps.map(step => ({
          ...step,
          status: 'completed',
          message: step.id === 'editing' ? '完了' : step.message
        }));
        // ユーザー入力待ち状態をクリア
        newState.isWaitingForInput = false;
        newState.inputType = undefined;

        // article_id があれば保存
        if (payload.article_id) {
          newState.articleId = payload.article_id as string;
        }
      }

      if (payload.error_message) {
        // エラーメッセージを設定
        newState.error = payload.error_message;
        newState.currentStep = 'error';
        
        // エラーが発生したステップをエラー状態に
        if (payload.step) {
          newState.steps = newState.steps.map(step => 
            step.id === payload.step ? { ...step, status: 'error', message: payload.error_message } : step
          );
        }
        
        // ユーザー入力待ちをクリア
        newState.isWaitingForInput = false;
        newState.inputType = undefined;
      }
      
      // 「finished」ステップの処理 - 実際に完了した場合のみ処理
      if (payload.step === 'finished') {
        console.log('useArticleGeneration: Processing finished step', { 
          generatedContent: !!newState.generatedContent, 
          finalArticle: !!newState.finalArticle,
          currentStep: newState.currentStep,
          errorMessage: payload.error_message
        });
        
        // エラーメッセージがある場合は完了にしない
        if (payload.error_message) {
          console.log('useArticleGeneration: Finished with error, not setting to completed');
          return newState;
        }
        
        // 実際に記事が生成されている場合のみ完了にする
        if (newState.finalArticle || (newState.generatedContent && newState.currentStep === 'completed')) {
          if (newState.generatedContent && !newState.finalArticle) {
            newState.finalArticle = {
              title: newState.outline?.title || payload.title || 'Generated Article',
              content: newState.generatedContent,
            };
            console.log('useArticleGeneration: Created finalArticle from generatedContent');
          }
          
          newState.currentStep = 'completed';
          // 全ステップを完了に
          newState.steps = newState.steps.map(step => ({
            ...step,
            status: 'completed',
            message: step.id === 'editing' ? 'スキップされました' : step.message
          }));
          newState.isWaitingForInput = false;
          newState.inputType = undefined;
        } else {
          console.log('useArticleGeneration: Finished but no final article, maintaining current state');
        }
        
        console.log('useArticleGeneration: Finished step processing complete', { 
          currentStep: newState.currentStep,
          finalArticle: !!newState.finalArticle,
          hasError: !!newState.error
        });

        // article_id が含まれていれば保存
        if (payload.article_id && typeof payload.article_id === 'string') {
          newState.articleId = payload.article_id;
        }
      }

      // 汎用的に article_id を受信した場合
      if (payload.article_id && typeof payload.article_id === 'string') {
        newState.articleId = payload.article_id;
      }

      // リサーチ進捗情報を処理
      if (payload.query_index !== undefined && payload.total_queries !== undefined) {
        newState.researchProgress = {
          currentQuery: payload.query_index + 1,
          totalQueries: payload.total_queries,
          query: payload.query || ''
        };
        
        // リサーチステップを実行中に
        if (newState.currentStep === 'researching' || newState.currentStep === 'research_synthesizing') {
          newState.steps = newState.steps.map(step => 
            step.id === 'researching' ? { 
              ...step, 
              status: 'in_progress', 
              message: `リサーチ中 (${(payload.query_index ?? 0) + 1}/${payload.total_queries ?? 0}): ${payload.query ?? ''}` 
            } : step
          );
        }
        
        // リサーチ完了判定
        if (payload.query_index + 1 === payload.total_queries) {
          // 最後のクエリの場合、次のメッセージでresearch_synthesizingに移行するため
          // ここでは進捗を維持
        }
      }
      
      // リサーチ進捗のクリア（要約フェーズ開始時）
      if (payload.step === 'research_synthesizing' && newState.researchProgress) {
        newState.researchProgress = undefined;
      }
      
      // リサーチ完了後のoutline_generatingへの遷移時に、researchingステップを完了にする
      if (payload.step === 'outline_generating') {
        newState.steps = newState.steps.map(step => {
          if (step.id === 'researching') {
            return { ...step, status: 'completed', message: '完了' };
          }
          return step;
        });
        // リサーチ関連の進捗情報をクリア
        newState.researchProgress = undefined;
      }

      return newState;
    });
  }, []);

  const { isConnected, isConnecting, error: wsError, connect, disconnect, sendMessage, startGeneration } = useWebSocket({
    processId,
    onMessage: handleMessage,
  });

  const selectPersona = useCallback((personaId: number) => {
    const message: ClientResponseMessage = {
      type: 'client_response',
      response_type: 'select_persona',
      payload: { selected_id: personaId },
    };
    sendMessage(message);
    setState(prev => ({ 
      ...prev, 
      isWaitingForInput: false, 
      inputType: undefined,
      currentStep: 'persona_selected'
    }));
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

  const editAndProceed = useCallback((editedContent: any, inputType: string) => {
    let responseType: string;
    let payload: any = editedContent;

    // 入力タイプに応じてレスポンスタイプとペイロードを設定
    switch (inputType) {
      case 'select_persona':
        responseType = 'edit_persona';
        payload = { edited_persona: editedContent };
        break;
      case 'select_theme':
        responseType = 'edit_theme';
        payload = { edited_theme: editedContent };
        break;
      case 'approve_plan':
        responseType = 'edit_plan';
        payload = { edited_plan: editedContent };
        break;
      case 'approve_outline':
        responseType = 'edit_outline';
        payload = { edited_outline: editedContent };
        break;
      default:
        responseType = 'edit_generic';
        break;
    }

    const message: ClientResponseMessage = {
      type: 'client_response',
      response_type: responseType as any,
      payload,
    };
    
    sendMessage(message);
    setState(prev => ({ ...prev, isWaitingForInput: false, inputType: undefined }));
  }, [sendMessage]);

  const startArticleGeneration = useCallback((requestData: any) => {
    setState(prev => ({
      ...prev,
      currentStep: 'start',
      steps: prev.steps.map(step => ({ ...step, status: 'pending', message: undefined })),
      personas: undefined,
      themes: undefined,
      researchPlan: undefined,
      outline: undefined,
      generatedContent: undefined,
      currentSection: undefined,
      finalArticle: undefined,
      isWaitingForInput: false,
      inputType: undefined,
      error: undefined,
      researchProgress: undefined,
      sectionsProgress: undefined,
    }));
    startGeneration(requestData);
  }, [startGeneration]);

  // プロセス状態の読み込み機能
  const loadProcessState = useCallback(async (): Promise<boolean> => {
    if (!processId || !userId) return false;

    try {
      const response = await fetch(`/api/articles/generation/${processId}`, {
        headers: {
          'Authorization': `Bearer ${await getToken()}`,
        },
      });

      if (!response.ok) {
        return false;
      }

      const processData = await response.json();
      
      // プロセス状態を復元
      const currentStep = processData.current_step_name || processData.status;
      const isUserInputStep = ['theme_proposed', 'persona_generated', 'research_plan_generated', 'outline_generated'].includes(currentStep);
      
      setState(prev => ({
        ...prev,
        currentStep: currentStep,
        articleId: processData.article_id,
        error: processData.error_message,
        isWaitingForInput: processData.is_waiting_for_input || isUserInputStep,
        inputType: processData.input_type || (isUserInputStep ? getInputTypeForStep(currentStep) : undefined),
        // generated_contentからの復元
        personas: processData.generated_content?.personas,
        themes: processData.generated_content?.themes,
        researchPlan: processData.generated_content?.research_plan,
        outline: processData.generated_content?.outline,
        generatedContent: processData.generated_content?.html_content,
        finalArticle: processData.generated_content?.final_article,
        // ステップ状態の復元
        steps: prev.steps.map(step => {
          const stepHistory = processData.step_history || [];
          const stepInfo = stepHistory.find((h: any) => h.step_name === step.id);
          
          if (stepInfo) {
            return {
              ...step,
              status: stepInfo.status,
              message: stepInfo.data?.message || step.message
            };
          }
          
          // デフォルトのステップ状態推定
          if (processData.current_step_name === step.id) {
            return { ...step, status: 'in_progress' };
          } else if (isStepCompleted(step.id, processData.current_step_name)) {
            return { ...step, status: 'completed' };
          }
          
          return step;
        }),
      }));

      return true;
    } catch (error) {
      console.error('Error loading process state:', error);
      return false;
    }
  }, [processId, userId]);

  // ステップに応じた入力タイプを決定するヘルパー関数
  const getInputTypeForStep = (step: string): string | undefined => {
    switch (step) {
      case 'theme_proposed': return 'select_theme';
      case 'persona_generated': return 'select_persona';
      case 'research_plan_generated': return 'approve_plan';
      case 'outline_generated': return 'approve_outline';
      default: return undefined;
    }
  };

  // ステップ完了判定のヘルパー関数
  const isStepCompleted = (stepId: string, currentStep: string): boolean => {
    const stepOrder = [
      'keyword_analyzing', 'persona_generating', 'theme_generating', 
      'research_planning', 'researching', 'outline_generating', 
      'writing_sections', 'editing'
    ];
    
    const stepIndex = stepOrder.indexOf(stepId);
    const currentIndex = stepOrder.indexOf(currentStep);
    
    return stepIndex < currentIndex;
  };

  // 新しい記事作成時の完全リセット
  const resetState = useCallback(() => {
    setState({
      currentStep: 'start',
      steps: [
        { id: 'keyword_analyzing', title: 'キーワード分析', status: 'pending' },
        { id: 'persona_generating', title: 'ペルソナ生成', status: 'pending' },
        { id: 'theme_generating', title: 'テーマ提案', status: 'pending' },
        { id: 'research_planning', title: 'リサーチ計画', status: 'pending' },
        { id: 'researching', title: 'リサーチ実行', status: 'pending' },
        { id: 'outline_generating', title: 'アウトライン作成', status: 'pending' },
        { id: 'writing_sections', title: '記事執筆', status: 'pending' },
        { id: 'editing', title: '編集・校正', status: 'pending' },
      ],
      isWaitingForInput: false,
      personas: undefined,
      themes: undefined,
      researchPlan: undefined,
      outline: undefined,
      generatedContent: undefined,
      currentSection: undefined,
      finalArticle: undefined,
      inputType: undefined,
      error: undefined,
      researchProgress: undefined,
      sectionsProgress: undefined,
    });
  }, []);

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
    editAndProceed,
    resetState,
    loadProcessState,
  };
};