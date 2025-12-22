/**
 * 記事生成フロー設定
 * localStorage と環境変数を組み合わせてフロー設定を管理
 */

export type FlowType = 'outline_first' | 'research_first';


// フロー設定のメタデータ
export const FLOW_METADATA = {
  outline_first: {
    displayName: '構成先行フロー',
    shortName: '構成先行',
    description: 'テーマ選択後、すぐに記事構成を作成し、その後リサーチを行います',
    workflow: [
      'キーワード分析',
      'ペルソナ生成',
      'テーマ選択',
      '記事構成作成',
      'リサーチ実行',
      '本文執筆',
      '編集・校正'
    ],
    bestFor: [
      '効率的な記事作成が必要な場合',
      '記事の方向性が明確な場合',
      'スピードを重視する場合'
    ]
  },
  research_first: {
    displayName: 'リサーチ先行フロー',
    shortName: 'リサーチ先行',
    description: 'テーマ選択後、詳細なリサーチを先に行ってから記事構成を作成します',
    workflow: [
      'キーワード分析',
      'ペルソナ生成',
      'テーマ選択',
      'リサーチ実行',
      '記事構成作成',
      '本文執筆',
      '編集・校正'
    ],
    bestFor: [
      '質の高い記事が必要な場合',
      '新しいトピックを扱う場合',
      '競合調査を重視する場合'
    ]
  }
};

/**
 * デフォルトフロータイプを取得
 * @returns FlowType
 */
export function getDefaultFlowType(): FlowType {
  return 'research_first';
}

/**
 * 旧形式の互換性のための関数
 * @deprecated use flow_type parameter in other functions instead
 */
export function getUseReorderedFlow(): boolean {
  return false; // デフォルトでresearch_first（後方互換性のため保持）
}

/**
 * フローの表示名を取得
 * @param flowType フロータイプ (省略時はデフォルト)
 * @returns 表示名
 */
export function getFlowDisplayName(flowType?: FlowType): string {
  const type = flowType || getDefaultFlowType();
  return FLOW_METADATA[type].displayName;
}

/**
 * フローの説明を取得
 * @param flowType フロータイプ (省略時はデフォルト)
 * @returns 説明文
 */
export function getFlowDescription(flowType?: FlowType): string {
  const type = flowType || getDefaultFlowType();
  return FLOW_METADATA[type].description;
}

/**
 * ステップ遷移ヘルパー関数群
 */

/**
 * テーマ選択後の次ステップを取得
 * @param flowType フロータイプ（省略時はデフォルト）
 * @returns 'outline_generating' (outline_first) | 'researching' (research_first)
 */
export function getNextStepAfterTheme(flowType?: FlowType): string {
  const type = flowType || getDefaultFlowType();
  return type === 'outline_first' ? 'outline_generating' : 'researching';
}

/**
 * リサーチ完了後の次ステップを取得
 * @param flowType フロータイプ（省略時はデフォルト）
 * @returns 'writing_sections' (outline_first) | 'outline_generating' (research_first)
 */
export function getNextStepAfterResearch(flowType?: FlowType): string {
  const type = flowType || getDefaultFlowType();
  return type === 'outline_first' ? 'writing_sections' : 'outline_generating';
}

/**
 * アウトライン承認後の次ステップを取得
 * @param flowType フロータイプ（省略時はデフォルト）
 * @returns 'researching' (outline_first) | 'writing_sections' (research_first)
 */
export function getNextStepAfterOutline(flowType?: FlowType): string {
  const type = flowType || getDefaultFlowType();
  return type === 'outline_first' ? 'researching' : 'writing_sections';
}

/**
 * ユーザー向けメッセージヘルパー関数群
 */

/**
 * テーマ選択後のメッセージを取得
 * @param flowType フロータイプ（省略時はデフォルト）
 * @returns フロー設定に応じたメッセージ
 */
export function getThemeSelectionMessage(flowType?: FlowType): string {
  const type = flowType || getDefaultFlowType();
  return type === 'outline_first'
    ? "選択後、自動でアウトライン作成を開始します"
    : "選択後、自動でリサーチを開始します";
}

/**
 * アウトライン承認ボタンのメッセージを取得
 * @param flowType フロータイプ（省略時はデフォルト）
 * @returns フロー設定に応じたボタンテキスト
 */
export function getOutlineApprovalMessage(flowType?: FlowType): string {
  const type = flowType || getDefaultFlowType();
  return type === 'outline_first'
    ? "この構成でリサーチ開始"
    : "この構成で執筆開始";
}

/**
 * アウトライン生成時の思考メッセージを取得
 * @param flowType フロータイプ（省略時はデフォルト）
 * @returns フロー設定に応じた思考メッセージ
 */
export function getOutlineGenerationMessage(flowType?: FlowType): string {
  const type = flowType || getDefaultFlowType();
  return type === 'outline_first'
    ? 'テーマに基づいて記事構成を設計しています...'
    : 'リサーチ結果を基に記事構成を設計しています...';
}

/**
 * ステップ進捗計算ヘルパー関数
 */

/**
 * フロー設定に応じたステップ進捗マップを取得
 * @param flowType フロータイプ（省略時はデフォルト）
 * @returns ステップ名と進捗率のマップ
 */
export function getStepProgressMap(flowType?: FlowType, enableFinalEditing: boolean = true): Record<string, number> {
  const type = flowType || getDefaultFlowType();

  // Editing をスキップする場合は執筆を最終ステップとして扱う
  const editingStepValue = enableFinalEditing ? 100 : 100;
  const writingFinalValue = enableFinalEditing ? 85 : 100;

  if (type === 'outline_first') {
    // Outline-first Flow: Theme → Outline → Research → Writing → (Editing)
    return {
      'keyword_analyzing': 10,
      'persona_generating': 20,
      'theme_generating': 30,
      'outline_generating': 50,   // アウトラインが早い段階
      'researching': 70,           // リサーチが後の段階
      'writing_sections': writingFinalValue,
      ...(enableFinalEditing ? { 'editing': editingStepValue } : {}),
      'completed': 100,
    };
  } else {
    // Research-first Flow: Theme → Research → Outline → Writing → (Editing)
    return {
      'keyword_analyzing': 10,
      'persona_generating': 20,
      'theme_generating': 30,
      'researching': 50,           // リサーチが早い段階
      'outline_generating': 70,    // アウトラインが後の段階
      'writing_sections': writingFinalValue,
      ...(enableFinalEditing ? { 'editing': editingStepValue } : {}),
      'completed': 100,
    };
  }
}

/**
 * デバッグ用：現在の設定を確認
 * @param flowType フロータイプ（省略時はデフォルト）
 */
export function debugFlowConfig(flowType?: FlowType) {
  const type = flowType || getDefaultFlowType();
  console.log('🔍 Flow Configuration Debug:', {
    flowType: type,
    flowDisplayName: getFlowDisplayName(type),
    nextStepAfterTheme: getNextStepAfterTheme(type),
    nextStepAfterResearch: getNextStepAfterResearch(type),
    nextStepAfterOutline: getNextStepAfterOutline(type),
  });
}
