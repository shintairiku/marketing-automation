/**
 * 記事生成フロー設定
 * 環境変数からフロー設定を読み込み、boolean型で返却
 */

/**
 * reordered flowが有効かどうかを取得
 * @returns true: reordered flow, false: classic flow
 */
export function getUseReorderedFlow(): boolean {
  // 複数の方法で環境変数を取得を試行
  const envValue = process.env.NEXT_PUBLIC_USE_REORDERED_FLOW || 
                   (typeof window !== 'undefined' && (window as any).__NEXT_DATA__?.props?.pageProps?.env?.NEXT_PUBLIC_USE_REORDERED_FLOW);
  
  // デバッグ用ログ
  if (typeof window === 'undefined') {
    console.log('🔍 [SSR] Flow config check:', {
      envValue,
      processEnv: process.env.NEXT_PUBLIC_USE_REORDERED_FLOW,
    });
  }
  
  // 未設定の場合はtrue (reordered flowをデフォルトに)
  if (!envValue) {
    console.log('⚠️ Environment variable not found, defaulting to reordered flow');
    return true;
  }
  
  // "true" (大文字小文字問わず) の場合のみtrue
  const result = envValue.toLowerCase() === 'true';
  console.log('🔍 Flow configuration result:', { envValue, result });
  return result;
}

/**
 * 現在のフロー名を取得
 * @returns "reordered" | "classic"
 */
export function getCurrentFlowName(): 'reordered' | 'classic' {
  return getUseReorderedFlow() ? 'reordered' : 'classic';
}

/**
 * フロー設定のデバッグ情報を取得
 */
export function getFlowDebugInfo() {
  return {
    envValue: process.env.NEXT_PUBLIC_USE_REORDERED_FLOW,
    useReorderedFlow: getUseReorderedFlow(),
    flowName: getCurrentFlowName(),
  };
}

/**
 * ステップ遷移ヘルパー関数群
 */

/**
 * テーマ選択後の次ステップを取得
 * @returns 'outline_generating' (reordered) | 'researching' (classic)
 */
export function getNextStepAfterTheme(): string {
  return getUseReorderedFlow() ? 'outline_generating' : 'researching';
}

/**
 * リサーチ完了後の次ステップを取得
 * @returns 'writing_sections' (reordered) | 'outline_generating' (classic)
 */
export function getNextStepAfterResearch(): string {
  return getUseReorderedFlow() ? 'writing_sections' : 'outline_generating';
}

/**
 * アウトライン承認後の次ステップを取得
 * @returns 'researching' (reordered) | 'writing_sections' (classic)
 */
export function getNextStepAfterOutline(): string {
  return getUseReorderedFlow() ? 'researching' : 'writing_sections';
}

/**
 * ユーザー向けメッセージヘルパー関数群
 */

/**
 * テーマ選択後のメッセージを取得
 * @returns フロー設定に応じたメッセージ
 */
export function getThemeSelectionMessage(): string {
  return getUseReorderedFlow()
    ? "選択後、自動でアウトライン作成を開始します"
    : "選択後、自動でリサーチを開始します";
}

/**
 * アウトライン承認ボタンのメッセージを取得
 * @returns フロー設定に応じたボタンテキスト
 */
export function getOutlineApprovalMessage(): string {
  return getUseReorderedFlow()
    ? "この構成でリサーチ開始"
    : "この構成で執筆開始";
}

/**
 * アウトライン生成時の思考メッセージを取得
 * @returns フロー設定に応じた思考メッセージ
 */
export function getOutlineGenerationMessage(): string {
  return getUseReorderedFlow()
    ? 'テーマに基づいて記事構成を設計しています...'
    : 'リサーチ結果を基に記事構成を設計しています...';
}

/**
 * ステップ進捗計算ヘルパー関数
 */

/**
 * フロー設定に応じたステップ進捗マップを取得
 * @returns ステップ名と進捗率のマップ
 */
export function getStepProgressMap(): Record<string, number> {
  if (getUseReorderedFlow()) {
    // Reordered Flow: Theme → Outline → Research → Writing → Editing
    return {
      'keyword_analyzing': 10,
      'persona_generating': 20,
      'theme_generating': 30,
      'outline_generating': 50,   // アウトラインが早い段階
      'researching': 70,           // リサーチが後の段階
      'writing_sections': 85,
      'editing': 100,
    };
  } else {
    // Classic Flow: Theme → Research → Outline → Writing → Editing
    return {
      'keyword_analyzing': 10,
      'persona_generating': 20,
      'theme_generating': 30,
      'researching': 50,           // リサーチが早い段階
      'outline_generating': 70,    // アウトラインが後の段階
      'writing_sections': 85,
      'editing': 100,
    };
  }
}

/**
 * デバッグ用：現在の設定を確認
 */
export function debugFlowConfig() {
  console.log('🔍 Flow Configuration Debug:', {
    envValue: process.env.NEXT_PUBLIC_USE_REORDERED_FLOW,
    useReorderedFlow: getUseReorderedFlow(),
    flowName: getCurrentFlowName(),
    nextStepAfterTheme: getNextStepAfterTheme(),
    nextStepAfterResearch: getNextStepAfterResearch(),
    nextStepAfterOutline: getNextStepAfterOutline(),
  });
}