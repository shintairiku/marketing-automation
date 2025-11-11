# SEO記事生成ページの状態管理（State Management）仕様

## 概要

このドキュメントでは、SEO記事生成ページにおける包括的な状態管理システムについて詳細に解説します。`useArticleGenerationRealtime`フックを中心とした状態管理アーキテクチャ、Supabase Realtimeとの連携による状態同期、そして複雑な生成プロセスを効率的に管理する設計思想を説明します。

## 状態管理アーキテクチャ

### 1. 中央状態管理フック

**ファイル**: `/frontend/src/hooks/useArticleGenerationRealtime.ts`

#### 基本構造

```typescript
export const useArticleGenerationRealtime = ({ 
  processId, 
  userId,
  autoConnect = true 
}: UseArticleGenerationRealtimeOptions) => {
  // 生成状態
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

  // 接続状態
  const [connectionState, setConnectionState] = useState({
    isInitializing: false,
    hasStarted: false,
    isDataSynced: false,
  });

  // その他の状態管理
  // ...
}
```

### 2. 状態管理の型定義

**ファイル**: `/frontend/src/types/article-generation.ts`

#### GenerationState 詳細

```typescript
export interface GenerationState {
  // 基本プロセス情報
  currentStep: string;
  steps: GenerationStep[];
  
  // ユーザーインタラクション
  isWaitingForInput: boolean;
  inputType?: string;
  
  // 生成されたコンテンツ
  personas?: PersonaOption[];
  themes?: ThemeOption[];
  researchPlan?: any;
  outline?: any;
  generatedContent?: string;
  finalArticle?: {
    title: string;
    content: string;
  };
  articleId?: string;
  
  // 進捗情報
  researchProgress?: ResearchProgress;
  sectionsProgress?: SectionsProgress;
  completedSections?: CompletedSection[];
  
  // エラー処理
  error?: string;
  
  // 画像生成機能
  imageMode?: boolean;
  imagePlaceholders?: ImagePlaceholder[];

  // オブザーバビリティリンク
  observability?: {
    weave?: {
      traceId?: string;
      traceUrl?: string;
    }
  };
}

export interface GenerationStep {
  id: string;
  name?: string;
  title?: string;
  status: 'pending' | 'in_progress' | 'completed' | 'error';
  message?: string;
  data?: any;
}
```

#### 進捗追跡の型定義

```typescript
export interface ResearchProgress {
  currentQuery: number;
  totalQueries: number;
  query: string;
}

export interface SectionsProgress {
  currentSection: number;
  totalSections: number;
  sectionHeading: string;
}

export interface CompletedSection {
  index: number;
  heading: string;
  content: string;
  imagePlaceholders?: ImagePlaceholder[];
}
```

## リアルタイム状態同期

### 1. Supabase Realtimeとの統合

#### イベント処理システム

```typescript
// イベント重複防止とスレッドセーフな状態更新
const [lastProcessedEventId, setLastProcessedEventId] = useState<string>('');
const [lastProcessedState, setLastProcessedState] = useState<string>('');
const [lastProcessedTime, setLastProcessedTime] = useState<number>(0);
const [processedEventIds, setProcessedEventIds] = useState<Set<string>>(new Set());

const handleRealtimeEvent = useCallback((event: ProcessEvent) => {
  // グローバルイベント重複除去
  const eventKey = `${event.event_type}-${event.id || event.event_sequence}-${JSON.stringify(event.event_data).substring(0, 100)}`;
  
  if (processedEventIds.has(eventKey)) {
    console.log('⏭️  Skipping duplicate event (already processed):', event.event_type, eventKey.substring(0, 50));
    return;
  }
  
  console.log('🔄 Processing realtime event:', event.event_type, event.event_data);
  
  // 処理済みイベントに追加
  setProcessedEventIds(prev => new Set([...prev].slice(-100)).add(eventKey));
  
  // 状態更新処理
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
        
      case 'process_state_updated':
        // プロセス状態の包括的更新
        const processData = event.event_data;
        updateProcessState(newState, processData);
        break;
        
      // その他のイベント処理...
    }
    
    return newState;
  });
}, [processedEventIds]);
```

#### バックエンドステップのUIステップへのマッピング

```typescript
const mapBackendStepToUIStep = (backendStep: string, status?: string): string => {
  const stepMapping: Record<string, string> = {
    // 初期状態
    'start': 'keyword_analyzing',
    
    // キーワード分析フェーズ
    'keyword_analyzing': 'keyword_analyzing',
    'keyword_analyzed': 'persona_generating',
    
    // ペルソナ生成フェーズ
    'persona_generating': 'persona_generating',
    'persona_generated': 'persona_generating',
    'persona_selected': 'theme_generating',
    
    // テーマ生成フェーズ
    'theme_generating': 'theme_generating',
    'theme_proposed': 'theme_generating',
    'theme_selected': 'research_planning',
    
    // リサーチプランニングフェーズ
    'research_planning': 'research_planning',
    'research_plan_generated': 'research_planning',
    'research_plan_approved': 'researching',
    
    // リサーチ実行フェーズ
    'researching': 'researching',
    'research_synthesizing': 'researching',
    'research_report_generated': 'outline_generating',
    
    // アウトライン生成フェーズ
    'outline_generating': 'outline_generating',
    'outline_generated': 'outline_generating',
    'outline_approved': 'writing_sections',
    
    // 執筆フェーズ
    'writing_sections': 'writing_sections',
    'all_sections_completed': 'editing',
    
    // 編集フェーズ
    'editing': 'editing',
    'editing_completed': 'editing',
    
    // 最終状態
    'completed': 'editing',
    'error': 'keyword_analyzing',
  };
  
  return stepMapping[backendStep] || 'keyword_analyzing';
};
```

### 2. 状態の一貫性保証

#### 後退防止ロジック

```typescript
// ステップ進行の後退を防ぐメカニズム
const currentStepOrder = ['keyword_analyzing', 'persona_generating', 'theme_generating', 'research_planning', 'researching', 'outline_generating', 'writing_sections', 'editing'];
const currentIndex = currentStepOrder.indexOf(newState.currentStep);
const newIndex = currentStepOrder.indexOf(uiStep);

// 遅延完了イベントの処理
const isDelayedCompletionEvent = [
  'research_plan_generated', 
  'persona_generated',
  'theme_proposed'
].includes(backendStep) && newIndex < currentIndex;

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
}
```

#### 時間ベースの重複除去

```typescript
// 時間ベースの重複除去（最小500ms間隔）
if (event.event_type === 'process_state_updated') {
  const data = event.event_data;
  const now = Date.now();
  
  const stateFingerprint = `${data.current_step_name}-${data.status}-${data.is_waiting_for_input}-${data.input_type}`;
  
  const timeSinceLastProcess = now - lastProcessedTime;
  if (stateFingerprint === lastProcessedState && timeSinceLastProcess < 500) {
    console.log('⏭️  Skipping duplicate state update (throttled):', stateFingerprint, `${timeSinceLastProcess}ms ago`);
    return;
  }
  
  setLastProcessedState(stateFingerprint);
  setLastProcessedTime(now);
}
```

## コンテンツ状態管理

### 1. 段階的コンテンツの管理

#### ペルソナ状態の管理

```typescript
// ペルソナデータの設定と変換
if (context.generated_detailed_personas) {
  console.log('🧑 Setting personas from context:', context.generated_detailed_personas);
  newState.personas = context.generated_detailed_personas.map((persona: any, index: number) => ({
    id: index,
    description: persona.description || persona.persona_description || JSON.stringify(persona)
  }));
}
```

#### テーマ状態の管理

```typescript
// テーマデータの設定
if (context.generated_themes) {
  console.log('🎯 Setting themes from context:', context.generated_themes);
  newState.themes = context.generated_themes;
}
```

#### アウトライン状態の管理

```typescript
// アウトラインデータの設定（複数のキーを確認）
const outlineData = context.outline || context.generated_outline;
if (outlineData) {
  console.log('📝 Setting outline from context:', outlineData);
  newState.outline = outlineData;
}
```

### 2. セクション進捗の追跡

#### セクション完了の管理

```typescript
case 'section_completed':
  if (!newState.completedSections) {
    newState.completedSections = [];
  }
  
  const completedSection = {
    index: event.event_data.section_index + 1,
    heading: event.event_data.section_heading,
    content: event.event_data.section_content || '',
    imagePlaceholders: event.event_data.image_placeholders || []
  };
  
  // 既存セクションの更新または新規追加
  const existingIndex = newState.completedSections.findIndex(
    (s: CompletedSection) => s.index === completedSection.index
  );
  
  if (existingIndex >= 0) {
    newState.completedSections[existingIndex] = completedSection;
  } else {
    newState.completedSections.push(completedSection);
  }
  
  // 生成コンテンツの更新
  if (newState.completedSections.length > 0) {
    newState.generatedContent = newState.completedSections
      .sort((a: CompletedSection, b: CompletedSection) => a.index - b.index)
      .map((section: CompletedSection) => section.content)
      .filter(content => content.trim().length > 0)
      .join('\n\n');
  }
  break;
```

#### 全セクション完了の処理

```typescript
case 'all_sections_completed':
  console.log('🎉 All sections completed!', {
    totalSections: event.event_data.total_sections,
    totalContentLength: event.event_data.total_content_length,
    totalPlaceholders: event.event_data.total_placeholders,
    imageMode: event.event_data.image_mode
  });
  
  // ステップ状態の更新
  newState.steps = newState.steps.map((step: GenerationStep) => {
    if (step.id === 'writing_sections') return { ...step, status: 'completed' as StepStatus };
    if (step.id === 'editing') return { ...step, status: 'in_progress' as StepStatus };
    return step;
  });
  
  // 自動的に編集ステップに進行
  newState.currentStep = 'editing';
  break;
```

## ユーザーインタラクション状態

### 1. 入力待ち状態の管理

#### 入力タイプによる状態切り替え

```typescript
// ユーザー入力要求の処理
if (processData.status === 'user_input_required') {
  newState.isWaitingForInput = true;
  // process_metadataのinput_typeを優先、rootのinput_typeをフォールバック
  newState.inputType = processData.process_metadata?.input_type || processData.input_type;
}

// 入力タイプに基づく状態設定
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
```

#### 入力解決後の自動進行

```typescript
case 'user_input_resolved':
  newState.isWaitingForInput = false;
  const previousInputType = newState.inputType;
  newState.inputType = undefined;
  
  // 入力タイプに基づく自動進行
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
      // その他の入力タイプ...
    }
  }
  break;
```

### 2. アクション実行の状態管理

#### 楽観的更新の回避

```typescript
const selectPersona = useCallback(async (personaId: number): Promise<ActionResult> => {
  // リアルタイム接続の確認
  if (!isConnected) {
    console.warn('Cannot select persona - not connected to realtime');
    setState((prev: GenerationState) => ({ 
      ...prev, 
      error: 'リアルタイム接続が切断されています。再接続してから再試行してください。' 
    }));
    return { success: false, error: 'リアルタイム接続が切断されています。再接続してから再試行してください。' };
  }
  
  try {
    await submitUserInput({
      response_type: 'select_persona',
      payload: { selected_id: personaId },
    });
    // UI状態は'persona_selection_completed'リアルタイムイベントで更新
    return { success: true };
  } catch (error) {
    // エラー時のロールバック
    setState((prev: GenerationState) => ({
      ...prev,
      isWaitingForInput: true,
      inputType: 'select_persona',
      error: error instanceof Error ? error.message : 'ペルソナ選択に失敗しました'
    }));
    return { success: false, error: error instanceof Error ? error.message : 'ペルソナ選択に失敗しました' };
  }
}, [submitUserInput, isConnected]);
```

## エラー状態管理

### 1. エラーハンドリング戦略

#### 包括的エラー処理

```typescript
case 'generation_error':
  newState.currentStep = 'error';
  newState.error = event.event_data.error_message;
  newState.isWaitingForInput = false;
  newState.inputType = undefined;
  
  // 特定ステップのエラーマーク
  if (event.event_data.step_name) {
    const errorStepName = event.event_data.step_name;
    newState.steps = newState.steps.map((step: GenerationStep) => 
      step.id === errorStepName ? { ...step, status: 'error' as StepStatus } : step
    );
  }
  break;
```

#### リアルタイムエラーの処理

```typescript
const handleRealtimeError = useCallback((error: Error) => {
  console.error('Realtime error:', error);
  setState((prev: GenerationState) => ({ ...prev, error: error.message }));
}, []);
```

### 2. 復旧メカニズム

#### プロセス復旧処理

```typescript
const handleResume = async () => {
  setThinkingMessages(['プロセスを復帰中...']);
  setShowRecoveryDialog(false);
  
  try {
    // Supabase Realtimeが自動的に状態を同期
    if (!isConnected && !isConnecting) {
      connect();
    }
    
    setThinkingMessages(['プロセスが正常に復帰されました。リアルタイム更新を開始します。']);
    
    setTimeout(() => {
      setThinkingMessages([]);
    }, 2000);
    
  } catch (err) {
    console.error('Resume error:', err);
    setThinkingMessages(['プロセスの復帰に失敗しました。新規作成をお試しください。']);
  }
};
```

## パフォーマンス最適化

### 1. メモ化とキャッシュ

#### ステップ状態の最適化

```typescript
// ステップ状態の保存ロジック
const updateStepStatuses = useCallback((steps: GenerationStep[], currentStep: string, processData: any) => {
  const currentStepIndex = steps.findIndex((s: GenerationStep) => s.id === currentStep);
  
  if (currentStepIndex >= 0) {
    return steps.map((step: GenerationStep, index: number) => {
      if (step.id === currentStep) {
        let stepStatus: StepStatus = 'in_progress';
        
        if (processData.status === 'user_input_required') {
          stepStatus = 'completed';
        } else if (processData.status === 'error') {
          stepStatus = 'error';
        } else if (processData.status === 'completed') {
          stepStatus = 'completed';
        }
        
        return { ...step, status: stepStatus };
      } else if (index < currentStepIndex) {
        // 既存の最終状態を保持
        const existingStatus = step.status;
        if (existingStatus === 'completed' || existingStatus === 'error') {
          return step;
        }
        return { ...step, status: 'completed' as StepStatus };
      } else {
        // 未来のステップの状態保持
        const existingStatus = step.status;
        if (existingStatus === 'completed' || existingStatus === 'error') {
          return step;
        }
        return { ...step, status: 'pending' as StepStatus };
      }
    });
  }
  
  return steps;
}, []);
```

### 2. レンダリング最適化

#### 条件付きレンダリング

```typescript
// デバッグ情報の条件付き表示
const debugInfo = useMemo(() => ({
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
}), [currentData, dataVersion, pendingActions, isConnected, isConnecting, isSyncing, lastSyncTime, queuedActions]);
```

#### 計算されたプロパティ

```typescript
// 計算されたステータス
const isRealtimeReady = useMemo(() => 
  isConnected && !isConnecting && connectionState.isDataSynced, 
  [isConnected, isConnecting, connectionState.isDataSynced]
);

const canPerformActions = useMemo(() => 
  realtimeCanPerformActions && connectionState.isDataSynced && !state.error && pendingActions.size === 0,
  [realtimeCanPerformActions, connectionState.isDataSynced, state.error, pendingActions.size]
);

const isDataStale = useMemo(() => 
  lastSyncTime ? (Date.now() - lastSyncTime.getTime()) > 60000 : true,
  [lastSyncTime]
);
```

## データ整合性とバージョン管理

### 1. データバージョンの追跡

```typescript
const [dataVersion, setDataVersion] = useState(0);

// イベント処理時にバージョンを更新
setDataVersion(prev => prev + 1);
```

### 2. 競合状態の解決

```typescript
// 競合解決：フェッチしたデータと現在のデータの比較
if (currentCurrentData && data.updated_at) {
  const fetchedTime = new Date(data.updated_at);
  const currentTime = currentCurrentData.updated_at ? new Date(currentCurrentData.updated_at) : new Date(0);
  
  if (fetchedTime < currentTime) {
    console.warn('Fetched data is older than current data - potential conflict');
    // 実際のアプリケーションでは、マージまたはユーザーに解決を求める
  }
}
```

## テスト可能性

### 1. モックとスタブ

```typescript
// テスト用のモック状態
export const mockGenerationState: GenerationState = {
  currentStep: 'keyword_analyzing',
  steps: [
    { id: 'keyword_analyzing', name: 'キーワード分析', status: 'in_progress' },
    // ... その他のステップ
  ],
  isWaitingForInput: false,
  error: undefined,
  // ... その他のプロパティ
};

// テスト用のアクション関数
export const mockActions = {
  selectPersona: jest.fn(),
  selectTheme: jest.fn(),
  approvePlan: jest.fn(),
  approveOutline: jest.fn(),
};
```

### 2. 状態遷移のテスト

```typescript
describe('状態遷移テスト', () => {
  test('ペルソナ選択後にテーマ生成ステップに進む', () => {
    const initialState = mockGenerationState;
    const event = {
      event_type: 'persona_selection_completed',
      event_data: { selected_persona_id: 1 }
    };
    
    const newState = processEvent(initialState, event);
    
    expect(newState.currentStep).toBe('theme_generating');
    expect(newState.steps.find(s => s.id === 'persona_generating')?.status).toBe('completed');
    expect(newState.steps.find(s => s.id === 'theme_generating')?.status).toBe('in_progress');
  });
});
```

## 結論

このSEO記事生成ページの状態管理システムにより、以下の特徴を実現しています：

1. **リアルタイム同期**: Supabase Realtimeとの堅牢な統合
2. **一貫性保証**: 重複イベント処理と後退防止メカニズム
3. **エラー耐性**: 包括的なエラーハンドリングと復旧機能
4. **パフォーマンス**: 最適化されたレンダリングとメモリ使用
5. **テスト可能性**: モックとテストフレンドリーな設計
6. **保守性**: 明確な責任分離と拡張可能なアーキテクチャ

この設計により、複雑な記事生成プロセスを効率的かつ信頼性高く管理し、優れたユーザー体験を提供します。
